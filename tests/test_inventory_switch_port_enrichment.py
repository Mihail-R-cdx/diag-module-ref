import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.equipment_inventory import (
    RECORD_FIELDS,
    RECORD_FIELDS_V1,
    RECORD_FIELDS_V3,
    SCHEMA_VERSION_V1,
    SCHEMA_VERSION_V2,
    SCHEMA_VERSION_V3,
    EquipmentInventoryLoadError,
    EquipmentInventoryMetadata,
    EquipmentRecord,
    InventoryLoadFailure,
    compute_snapshot_id,
    inventory_from_document,
    load_equipment_inventory,
)
from tools import import_equipment_inventory as importer
from tools.import_equipment_inventory import (
    EVIDENCE_COLUMNS,
    NETWORK_COLUMNS,
    NETWORK_WORKSHEET,
    NETWORK_XLSX_ENV,
    SOURCE_COLUMNS,
    import_equipment_inventory,
    resolve_converter_paths,
)
from tests.test_equipment_inventory import source_row, write_xlsx, write_xlsx_sheets


NETWORK_HEADERS = [
    NETWORK_COLUMNS["mac_address"],
    NETWORK_COLUMNS["switch_ip_address"],
    NETWORK_COLUMNS["switch_port"],
    "IP устройства",
    "Помещение",
    "Производитель",
    "Модель",
    "Корректная запись",
]


def network_row(
    mac,
    *,
    switch_ip="198.51.100.1",
    port="Gi1/0/1",
    device_ip="192.0.2.200",
    room="Ignored Room",
    manufacturer="Ignored Manufacturer",
    model="Ignored Model",
    correct="Нет",
):
    return {
        NETWORK_COLUMNS["mac_address"]: mac,
        NETWORK_COLUMNS["switch_ip_address"]: switch_ip,
        NETWORK_COLUMNS["switch_port"]: port,
        "IP устройства": device_ip,
        "Помещение": room,
        "Производитель": manufacturer,
        "Модель": model,
        "Корректная запись": correct,
    }


def primary_row(index, mac, *, record_id=None, ip=None, room_id=None, model="TE20"):
    return source_row(
        record_id or f"RID-{index}",
        room_id=room_id or f"ROOM-{index}",
        room_name=f"Synthetic Room {index}",
        source_model=f"Synthetic Source {index}",
        source_type="Video Conference",
        ip=ip or f"192.0.2.{index}",
        mac=mac,
        serial=f"SER-{index}",
        manufacturer="Huawei",
        model=model,
        controller=None,
    )


def write_network_xlsx(path, rows, *, headers=NETWORK_HEADERS, include_changes=True):
    sheets = [(NETWORK_WORKSHEET, rows, headers)]
    if include_changes:
        sheets.append(
            (
                "Изменения",
                [
                    network_row(
                        "00:11:22:33:44:01",
                        switch_ip="198.51.100.254",
                        port="SHOULD-NOT-BE-USED",
                        correct="Да",
                    )
                ],
                headers,
            )
        )
    write_xlsx_sheets(path, sheets)


def snapshot_document(records, *, schema_version=SCHEMA_VERSION_V3):
    fields = {
        SCHEMA_VERSION_V1: RECORD_FIELDS_V1,
        SCHEMA_VERSION_V2: RECORD_FIELDS,
        SCHEMA_VERSION_V3: RECORD_FIELDS_V3,
    }[schema_version]
    record_dicts = [
        {field: getattr(record, field) for field in fields}
        for record in sorted(records, key=lambda item: item.record_id)
    ]
    return {
        "schema_version": schema_version,
        "snapshot_id": compute_snapshot_id(record_dicts, schema_version=schema_version),
        "records": record_dicts,
    }


def runtime_record(record_id, *, mac="00:11:22:33:44:55", switch_ip=None, switch_port=None):
    return EquipmentRecord(
        record_id=record_id,
        source_model="Synthetic",
        diagnostic_model="Huawei TE20",
        ip_address="192.0.2.10",
        mac_address=mac,
        serial_number="SER",
        room_id="ROOM-1",
        room_name="Room One",
        device_kind="video_codec",
        room_vip=True,
        switch_ip_address=switch_ip,
        switch_port=switch_port,
    )


class SwitchPortSchemaRuntimeTests(unittest.TestCase):
    def test_schema_v1_v2_adapt_switch_fields_and_schema_v3_exposes_them(self):
        v1 = inventory_from_document(snapshot_document([runtime_record("RID-1")], schema_version=SCHEMA_VERSION_V1))
        self.assertIsNone(v1.records[0].room_vip)
        self.assertIsNone(v1.records[0].switch_ip_address)
        self.assertIsNone(v1.records[0].switch_port)

        v2 = inventory_from_document(snapshot_document([runtime_record("RID-1")], schema_version=SCHEMA_VERSION_V2))
        self.assertTrue(v2.records[0].room_vip)
        self.assertIsNone(v2.records[0].switch_ip_address)
        self.assertIsNone(v2.records[0].switch_port)

        v3 = inventory_from_document(
            snapshot_document(
                [runtime_record("RID-1", switch_ip="198.51.100.10", switch_port="Gi1/0/10")],
                schema_version=SCHEMA_VERSION_V3,
            )
        )
        self.assertEqual(SCHEMA_VERSION_V3, v3.metadata.schema_version)
        self.assertEqual("198.51.100.10", v3.records[0].switch_ip_address)
        self.assertEqual("Gi1/0/10", v3.records[0].switch_port)

    def test_hybrid_and_future_schema_are_rejected_and_switch_fields_affect_v3_identity(self):
        v2 = snapshot_document([runtime_record("RID-1")], schema_version=SCHEMA_VERSION_V2)
        hybrid = copy.deepcopy(v2)
        hybrid["records"][0]["switch_ip_address"] = "198.51.100.10"
        hybrid["records"][0]["switch_port"] = "Gi1/0/10"
        hybrid["snapshot_id"] = compute_snapshot_id(hybrid["records"], schema_version=SCHEMA_VERSION_V2)
        with self.assertRaises(EquipmentInventoryLoadError) as error:
            inventory_from_document(hybrid)
        self.assertEqual(InventoryLoadFailure.INVALID_SNAPSHOT, error.exception.category)

        future = {"schema_version": 4, "snapshot_id": "sha256:" + "0" * 64, "records": []}
        with self.assertRaises(EquipmentInventoryLoadError) as error:
            inventory_from_document(future)
        self.assertEqual(InventoryLoadFailure.UNSUPPORTED_SCHEMA, error.exception.category)

        base = snapshot_document(
            [runtime_record("RID-1", switch_ip="198.51.100.10", switch_port="Gi1/0/10")],
            schema_version=SCHEMA_VERSION_V3,
        )
        changed_ip = copy.deepcopy(base)
        changed_ip["records"][0]["switch_ip_address"] = "198.51.100.11"
        changed_port = copy.deepcopy(base)
        changed_port["records"][0]["switch_port"] = "Gi1/0/11"
        self.assertNotEqual(base["snapshot_id"], compute_snapshot_id(changed_ip["records"], schema_version=SCHEMA_VERSION_V3))
        self.assertNotEqual(base["snapshot_id"], compute_snapshot_id(changed_port["records"], schema_version=SCHEMA_VERSION_V3))

    def test_schema_v3_queries_ignore_switch_fields(self):
        inventory = inventory_from_document(
            snapshot_document(
                [
                    runtime_record("RID-1", switch_ip="198.51.100.10", switch_port="Gi1/0/10"),
                    runtime_record("RID-2", mac="00:11:22:33:44:56", switch_ip="198.51.100.10", switch_port="Gi1/0/11"),
                ],
                schema_version=SCHEMA_VERSION_V3,
            )
        )
        self.assertEqual(("RID-1", "RID-2"), tuple(record.record_id for record in inventory.find_by_ip("192.0.2.10")))
        self.assertEqual(("RID-1", "RID-2"), tuple(record.record_id for record in inventory.find_room_equipment("ROOM-1")))
        self.assertEqual(("RID-1", "RID-2"), tuple(record.record_id for record in inventory.find_by_room_and_kind("ROOM-1", "video_codec")))
        self.assertFalse(hasattr(inventory, "find_by_switch_ip"))
        self.assertFalse(hasattr(inventory, "find_by_switch_port"))


class SwitchPortImporterTests(unittest.TestCase):
    def test_one_source_mode_still_publishes_schema_v2_without_switch_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            write_xlsx(source, [primary_row(1, "00:11:22:33:44:01")])

            result = import_equipment_inventory(source, output_path=output, generated_at="2026-08-02T00:00:00Z")
            document = json.loads(output.read_text(encoding="utf-8"))

        self.assertTrue(result.published)
        self.assertEqual(SCHEMA_VERSION_V2, document["schema_version"])
        self.assertNotIn("switch_ip_address", document["records"][0])
        self.assertEqual(compute_snapshot_id(document["records"], schema_version=SCHEMA_VERSION_V2), document["snapshot_id"])

    def test_public_network_configuration_surfaces_resolve_and_publish_schema_v3(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            network = Path(directory) / "network.xlsx"
            write_xlsx(source, [primary_row(1, "00:11:22:33:44:01")])
            write_network_xlsx(network, [network_row("00-11-22-33-44-01")])

            direct_output = Path(directory) / "direct.json"
            direct = import_equipment_inventory(source, network_source_path=network, output_path=direct_output)

            env_output = Path(directory) / "env.json"
            with patch.dict(os.environ, {NETWORK_XLSX_ENV: str(network)}):
                env_result = import_equipment_inventory(source, output_path=env_output)

            module_output = Path(directory) / "module.json"
            with patch.object(importer, "NETWORK_XLSX_PATH", network):
                module_result = import_equipment_inventory(source, output_path=module_output)

            resolved = resolve_converter_paths(
                source_override=source,
                output_override=Path(directory) / "resolved.json",
                network_override=network,
                env={},
            )

            cli_output = Path(directory) / "cli.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/import_equipment_inventory.py",
                    str(source),
                    "--network-source",
                    str(network),
                    "--output",
                    str(cli_output),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )
            schema_versions = [
                json.loads(output.read_text(encoding="utf-8"))["schema_version"]
                for output in (direct_output, env_output, module_output, cli_output)
            ]

        self.assertTrue(direct.published)
        self.assertTrue(env_result.published)
        self.assertTrue(module_result.published)
        self.assertEqual(network.resolve(), resolved.network_xlsx_path)
        self.assertEqual(0, completed.returncode, completed.stderr + completed.stdout)
        self.assertEqual([SCHEMA_VERSION_V3] * 4, schema_versions)

    def test_valid_two_source_run_uses_exact_sheet_headers_and_ignores_non_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            network = Path(directory) / "network.xlsx"
            output = Path(directory) / "snapshot.json"
            write_xlsx(
                source,
                [
                    primary_row(1, "00:11:22:33:44:01", ip="192.0.2.10", room_id="ROOM-A"),
                    primary_row(2, "00:11:22:33:44:02", ip="192.0.2.20", room_id="ROOM-B"),
                ],
            )
            write_network_xlsx(
                network,
                [
                    network_row("0011.2233.4401", switch_ip="198.51.100.10", port=" Gi1/0/10 ", correct="Нет"),
                    network_row(
                        "00:11:22:33:44:99",
                        switch_ip="198.51.100.99",
                        port="Gi1/0/99",
                        device_ip="192.0.2.20",
                        room="ROOM-B",
                        manufacturer="Huawei",
                        model="TE20",
                    ),
                ],
            )

            result = import_equipment_inventory(source, network_source_path=network, output_path=output)
            inventory = load_equipment_inventory(output)
            document = json.loads(output.read_text(encoding="utf-8"))
            by_id = {record.record_id: record for record in inventory.records}

        self.assertTrue(result.published, [issue.to_dict() for issue in result.issues])
        self.assertEqual(SCHEMA_VERSION_V3, inventory.metadata.schema_version)
        self.assertEqual(NETWORK_WORKSHEET, result.network_worksheet)
        self.assertEqual(2, result.network_source_row_count)
        self.assertEqual(2, result.distinct_network_mac_count)
        self.assertEqual("198.51.100.10", by_id["RID-1"].switch_ip_address)
        self.assertEqual("Gi1/0/10", by_id["RID-1"].switch_port)
        self.assertIsNone(by_id["RID-2"].switch_ip_address)
        self.assertIsNone(by_id["RID-2"].switch_port)
        self.assertIn("NETWORK_MAC_NOT_IN_INVENTORY", {issue.code for issue in result.issues})
        self.assertEqual(2, document["source_row_count"])

    def test_reconciliation_issue_table_is_non_fatal_and_preserves_publishability(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            network = Path(directory) / "network.xlsx"
            output = Path(directory) / "snapshot.json"
            primary_rows = [
                primary_row(1, "00:11:22:33:44:01"),
                primary_row(2, "00:11:22:33:44:02"),
                primary_row(3, "00:11:22:33:44:03"),
                primary_row(4, "00:11:22:33:44:04"),
                primary_row(5, "00:11:22:33:44:05"),
                primary_row(6, "00:11:22:33:44:06"),
                primary_row(7, "00:11:22:33:44:07"),
                primary_row(8, "00:11:22:33:44:08", record_id="RID-8A"),
                primary_row(9, "00:11:22:33:44:08", record_id="RID-8B"),
            ]
            network_rows = [
                network_row("00-11-22-33-44-01", switch_ip="198.51.100.1", port="Gi1/0/1"),
                network_row("00:11:22:33:44:01", switch_ip=None, port=None),
                network_row("00:11:22:33:44:02", switch_ip="198.51.100.2", port=None),
                network_row("00:11:22:33:44:03", switch_ip=None, port="Gi1/0/3"),
                network_row("00:11:22:33:44:04", switch_ip="bad-ip", port="Gi1/0/4"),
                network_row("00:11:22:33:44:05", switch_ip=None, port=None),
                network_row("00:11:22:33:44:06", switch_ip="198.51.100.6", port="Gi1/0/6"),
                network_row("00-11-22-33-44-06", switch_ip="198.51.100.6", port="Gi1/0/6"),
                network_row("00:11:22:33:44:07", switch_ip="198.51.100.7", port="Gi1/0/7A"),
                network_row("00:11:22:33:44:07", switch_ip="198.51.100.7", port="Gi1/0/7B"),
                network_row("00:11:22:33:44:08", switch_ip="198.51.100.8", port="Gi1/0/8"),
                network_row("00:11:22:33:44:09", switch_ip="198.51.100.9", port="Gi1/0/9"),
                network_row("bad-mac", switch_ip="198.51.100.10", port="Gi1/0/10"),
                network_row("00:11:22:33:44:10", switch_ip="bad-ip", port=None),
            ]
            write_xlsx(source, primary_rows)
            write_network_xlsx(network, network_rows)

            result = import_equipment_inventory(source, network_source_path=network, output_path=output)
            inventory = load_equipment_inventory(output)
            by_id = {record.record_id: record for record in inventory.records}
            codes = {issue.code for issue in result.issues}

        self.assertTrue(result.published, [issue.to_dict() for issue in result.issues])
        self.assertEqual(SCHEMA_VERSION_V3, inventory.metadata.schema_version)
        self.assertEqual(("198.51.100.1", "Gi1/0/1"), (by_id["RID-1"].switch_ip_address, by_id["RID-1"].switch_port))
        self.assertEqual(("198.51.100.2", None), (by_id["RID-2"].switch_ip_address, by_id["RID-2"].switch_port))
        self.assertEqual((None, "Gi1/0/3"), (by_id["RID-3"].switch_ip_address, by_id["RID-3"].switch_port))
        self.assertEqual((None, "Gi1/0/4"), (by_id["RID-4"].switch_ip_address, by_id["RID-4"].switch_port))
        self.assertEqual((None, None), (by_id["RID-5"].switch_ip_address, by_id["RID-5"].switch_port))
        self.assertEqual(("198.51.100.6", "Gi1/0/6"), (by_id["RID-6"].switch_ip_address, by_id["RID-6"].switch_port))
        self.assertEqual((None, None), (by_id["RID-7"].switch_ip_address, by_id["RID-7"].switch_port))
        self.assertEqual((None, None), (by_id["RID-8A"].switch_ip_address, by_id["RID-8A"].switch_port))
        self.assertEqual((None, None), (by_id["RID-8B"].switch_ip_address, by_id["RID-8B"].switch_port))
        self.assertTrue(
            {
                "EMPTY_SWITCH_CONNECTION",
                "MISSING_SWITCH_PORT",
                "MISSING_SWITCH_IP",
                "INVALID_SWITCH_IP",
                "INVALID_NETWORK_MAC",
                "DUPLICATE_SWITCH_CONNECTION_SOURCE",
                "AMBIGUOUS_SWITCH_CONNECTION",
                "AMBIGUOUS_INVENTORY_MAC_FOR_SWITCH",
                "NETWORK_MAC_NOT_IN_INVENTORY",
            }.issubset(codes)
        )
        self.assertEqual(5, result.enriched_record_count)
        self.assertEqual(2, result.empty_connection_row_count)
        self.assertEqual(1, result.duplicate_connection_count)
        self.assertGreaterEqual(result.ambiguity_count, 2)
        self.assertEqual(2, result.unmatched_network_mac_count)
        self.assertEqual((), result.fatal_issues)

    def test_fatal_network_structure_preserves_previous_output(self):
        cases = [
            ("missing_sheet", [("NotDevices", [], NETWORK_HEADERS)], "NETWORK_WORKSHEET_MISSING"),
            (
                "ambiguous_sheet",
                [(NETWORK_WORKSHEET, [], NETWORK_HEADERS), (NETWORK_WORKSHEET, [], NETWORK_HEADERS)],
                "NETWORK_WORKSHEET_AMBIGUOUS",
            ),
            (
                "missing_header",
                [(NETWORK_WORKSHEET, [network_row("00:11:22:33:44:01")], [header for header in NETWORK_HEADERS if header != NETWORK_COLUMNS["switch_port"]])],
                "NETWORK_HEADER_MISSING",
            ),
            (
                "ambiguous_header",
                [(NETWORK_WORKSHEET, [network_row("00:11:22:33:44:01")], NETWORK_HEADERS + [NETWORK_COLUMNS["mac_address"]])],
                "NETWORK_HEADER_AMBIGUOUS",
            ),
        ]
        for name, sheets, expected_code in cases:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as directory:
                    source = Path(directory) / "inventory.xlsx"
                    network = Path(directory) / "network.xlsx"
                    output = Path(directory) / "snapshot.json"
                    output.write_text("previous-output", encoding="utf-8")
                    write_xlsx(source, [primary_row(1, "00:11:22:33:44:01")])
                    write_xlsx_sheets(network, sheets)

                    result = import_equipment_inventory(source, network_source_path=network, output_path=output)

                    self.assertFalse(result.published)
                    self.assertEqual("previous-output", output.read_text(encoding="utf-8"))
                    self.assertEqual((expected_code,), tuple(issue.code for issue in result.fatal_issues))

    def test_network_workbook_unreadable_preserves_previous_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            output.write_text("previous-output", encoding="utf-8")
            write_xlsx(source, [primary_row(1, "00:11:22:33:44:01")])

            result = import_equipment_inventory(
                source,
                network_source_path=Path(directory) / "missing-network.xlsx",
                output_path=output,
            )

            self.assertFalse(result.published)
            self.assertEqual("previous-output", output.read_text(encoding="utf-8"))
            self.assertEqual(("NETWORK_WORKBOOK_UNREADABLE",), tuple(issue.code for issue in result.fatal_issues))


if __name__ == "__main__":
    unittest.main()
