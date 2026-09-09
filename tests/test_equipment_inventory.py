import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

from core.equipment_inventory import (
    RECORD_FIELDS,
    RECORD_FIELDS_V1,
    RECORD_FIELDS_V3,
    RECORD_FIELDS_V4,
    SCHEMA_VERSION,
    SCHEMA_VERSION_V1,
    SCHEMA_VERSION_V2,
    SCHEMA_VERSION_V3,
    SCHEMA_VERSION_V4,
    EquipmentInventoryLoadError,
    EquipmentRecord,
    InventoryLoadFailure,
    application_root,
    compute_snapshot_id,
    default_snapshot_path,
    inventory_from_document,
    load_equipment_inventory,
    record_to_dict,
)
from tools.import_equipment_inventory import (
    ConverterConfigurationError,
    ConverterOperation,
    ConverterStage,
    EVIDENCE_COLUMNS,
    NETWORK_COLUMNS,
    NETWORK_WORKSHEET,
    OUTPUT_JSON_ENV,
    SOURCE_COLUMNS,
    SOURCE_XLSX_ENV,
    SourceFileRole,
    capture_output_precondition,
    import_equipment_inventory,
    preflight_combined_sources,
    preflight_network_source,
    preflight_primary_source,
    resolve_converter_paths,
)
from core.interactive_session import _default_handler_factory
from gui.diagnostic_dispatch import DiagnosticActionPurpose, ModelResolutionStatus, resolve_exact_model_for_ip
from handlers.huawei.te40 import HuaweiTE40Handler


HEADERS = [
    SOURCE_COLUMNS["room_id"],
    SOURCE_COLUMNS["room_name"],
    SOURCE_COLUMNS["room_address"],
    SOURCE_COLUMNS["record_id"],
    SOURCE_COLUMNS["device_kind"],
    SOURCE_COLUMNS["source_model"],
    SOURCE_COLUMNS["room_vip"],
    EVIDENCE_COLUMNS["controller_record_id"],
    EVIDENCE_COLUMNS["model"],
    EVIDENCE_COLUMNS["manufacturer"],
    SOURCE_COLUMNS["ip_address"],
    SOURCE_COLUMNS["mac_address"],
    SOURCE_COLUMNS["serial_number"],
]
NETWORK_HEADERS = [
    NETWORK_COLUMNS["mac_address"],
    NETWORK_COLUMNS["switch_ip_address"],
    NETWORK_COLUMNS["switch_port"],
    "Корректная запись",
]


def record(record_id, *, ip_address=None, mac_address=None, serial_number=None, room_id=None, room_name=None, room_address=None, device_kind="other", source_model=None, diagnostic_model=None, room_vip=None):
    return EquipmentRecord(
        record_id=record_id,
        source_model=source_model,
        diagnostic_model=diagnostic_model,
        ip_address=ip_address,
        mac_address=mac_address,
        serial_number=serial_number,
        room_id=room_id,
        room_name=room_name,
        device_kind=device_kind,
        room_vip=room_vip,
        room_address=room_address,
    )


def snapshot_document(records, *, schema_version=SCHEMA_VERSION, **metadata):
    ordered = tuple(sorted(records, key=lambda item: item.record_id))
    fields = {
        SCHEMA_VERSION_V1: RECORD_FIELDS_V1,
        SCHEMA_VERSION_V2: RECORD_FIELDS,
        SCHEMA_VERSION_V3: RECORD_FIELDS_V3,
        SCHEMA_VERSION_V4: RECORD_FIELDS_V4,
    }[schema_version]
    record_dicts = [
        {field: getattr(item, field) for field in fields}
        for item in ordered
    ]
    document = {
        "schema_version": schema_version,
        "snapshot_id": compute_snapshot_id(record_dicts, schema_version=schema_version),
        "records": record_dicts,
    }
    document.update(metadata)
    return document


def write_snapshot(path, records, **metadata):
    document = snapshot_document(records, **metadata)
    Path(path).write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return document


def source_row(record_id, *, room_id="ROOM-1", room_name="Room One", room_address="Building 1", source_model=None, source_type="Video Conference", room_vip=None, ip="192.0.2.10", mac="00-11-22-33-44-55", serial="SER-1", manufacturer="Huawei", model="TE20", controller="CTRL-1"):
    return {
        SOURCE_COLUMNS["room_id"]: room_id,
        SOURCE_COLUMNS["room_name"]: room_name,
        SOURCE_COLUMNS["room_address"]: room_address,
        SOURCE_COLUMNS["record_id"]: record_id,
        SOURCE_COLUMNS["device_kind"]: source_type,
        SOURCE_COLUMNS["source_model"]: source_model,
        SOURCE_COLUMNS["room_vip"]: room_vip,
        EVIDENCE_COLUMNS["controller_record_id"]: controller,
        EVIDENCE_COLUMNS["model"]: model,
        EVIDENCE_COLUMNS["manufacturer"]: manufacturer,
        SOURCE_COLUMNS["ip_address"]: ip,
        SOURCE_COLUMNS["mac_address"]: mac,
        SOURCE_COLUMNS["serial_number"]: serial,
    }


def _column_name(index):
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _sheet_xml(rows, headers=HEADERS, header_row=1):
    def cell(reference, value):
        if value is None:
            return f'<c r="{reference}"/>'
        if isinstance(value, bool):
            return f'<c r="{reference}" t="b"><v>{1 if value else 0}</v></c>'
        text = str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f'<c r="{reference}" t="inlineStr"><is><t>{text}</t></is></c>'

    sheet_rows = []
    all_rows = [dict(zip(headers, headers))]
    all_rows.extend(rows)
    for row_index, row in enumerate(all_rows, start=header_row):
        cells = [cell(f"{_column_name(col_index)}{row_index}", row.get(header)) for col_index, header in enumerate(headers, start=1)]
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    end_column = _column_name(len(headers))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<dimension ref="A{header_row}:{end_column}{header_row + len(all_rows) - 1}"/>
<sheetData>{''.join(sheet_rows)}</sheetData>
</worksheet>"""


def write_xlsx(path, rows, headers=HEADERS):
    write_xlsx_sheets(path, [("SyntheticInventory", rows, headers)])


def write_xlsx_sheets(path, sheets, active_index=0):
    sheet_overrides = "\n".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index, _sheet in enumerate(sheets, start=1)
    )
    sheet_entries = "\n".join(
        f'<sheet name="{sheet[0]}" sheetId="{index}" r:id="rId{index}"/>'
        for index, sheet in enumerate(sheets, start=1)
    )
    rel_entries = "\n".join(
        f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
        for index, _sheet in enumerate(sheets, start=1)
    )

    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", f"""<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
{sheet_overrides}
</Types>""")
        archive.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""")
        archive.writestr("xl/workbook.xml", f"""<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<bookViews><workbookView activeTab="{active_index}"/></bookViews>
<sheets>{sheet_entries}</sheets>
</workbook>""")
        archive.writestr("xl/_rels/workbook.xml.rels", f"""<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{rel_entries}
</Relationships>""")
        for index, sheet in enumerate(sheets, start=1):
            if len(sheet) == 4:
                _name, sheet_rows, sheet_headers, header_row = sheet
            else:
                _name, sheet_rows, sheet_headers = sheet
                header_row = 1
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _sheet_xml(sheet_rows, sheet_headers, header_row))


def network_row(mac, *, switch_ip="198.51.100.10", port="Gi1/0/10", correct="Нет"):
    return {
        NETWORK_COLUMNS["mac_address"]: mac,
        NETWORK_COLUMNS["switch_ip_address"]: switch_ip,
        NETWORK_COLUMNS["switch_port"]: port,
        "Корректная запись": correct,
    }


def write_network_xlsx(path, rows, *, headers=NETWORK_HEADERS):
    write_xlsx_sheets(
        path,
        [
            (NETWORK_WORKSHEET, rows, headers),
            ("Изменения", [network_row("00:11:22:33:44:ff", port="IGNORED")], headers),
        ],
    )


def issue_codes_by_record(issues):
    codes = {}
    for issue in issues:
        if issue.record_id is not None:
            codes.setdefault(issue.record_id, set()).add(issue.code)
    return codes


class EquipmentInventoryRuntimeTests(unittest.TestCase):
    def test_loads_snapshot_and_preserves_zero_one_many_queries(self):
        records = [
            record("RID-1", ip_address="192.0.2.10", room_id="ROOM-1", room_name="Room One", device_kind="pdu"),
            record("RID-2", ip_address="192.0.2.10", room_id="ROOM-1", room_name="Room One", device_kind="video_codec"),
            record("RID-3", ip_address="192.0.2.30", room_id="ROOM-1", room_name="Room One", device_kind="video_codec"),
            record("RID-4", ip_address="192.0.2.40", room_id="ROOM-2", room_name="Room Two", device_kind="pdu"),
        ]
        inventory = inventory_from_document(snapshot_document(records, generated_at="2026-07-23T00:00:00Z", source_row_count=3))
        self.assertEqual((), inventory.find_by_ip("192.0.2.99"))
        self.assertEqual(("RID-4",), tuple(item.record_id for item in inventory.find_by_ip("192.0.2.40")))
        self.assertEqual(("RID-1", "RID-2"), tuple(item.record_id for item in inventory.find_by_ip("192.0.2.10")))
        self.assertEqual((), inventory.find_room_equipment("ROOM-404"))
        self.assertEqual(("RID-4",), tuple(item.record_id for item in inventory.find_room_equipment("ROOM-2")))
        self.assertEqual(("RID-1", "RID-2", "RID-3"), tuple(item.record_id for item in inventory.find_room_equipment("ROOM-1")))
        self.assertEqual(("RID-1",), tuple(item.record_id for item in inventory.find_by_room_and_kind("ROOM-1", "pdu")))
        self.assertEqual(("RID-2", "RID-3"), tuple(item.record_id for item in inventory.find_by_room_and_kind("ROOM-1", "video_codec")))
        self.assertEqual((), inventory.find_by_room_and_kind("ROOM-404", "video_codec"))
        self.assertFalse(hasattr(inventory, "find_by_mac"))
        self.assertNotIn("NOT_FOUND", repr(inventory.find_by_ip("192.0.2.99")))
        with self.assertRaises(AttributeError):
            inventory.records[0].record_id = "changed"

    def test_rejects_invalid_schema_shapes_and_declared_digest_mismatch(self):
        valid = snapshot_document([record("RID-1", mac_address="00:11:22:33:44:55", serial_number="SER-1", device_kind="pdu")])
        changed = copy.deepcopy(valid)
        changed["records"][0]["serial_number"] = "SER-2"
        with self.assertRaises(EquipmentInventoryLoadError) as error:
            inventory_from_document(changed)
        self.assertEqual(InventoryLoadFailure.INVALID_SNAPSHOT, error.exception.category)
        for mutation in (
            lambda doc: doc["records"][0].update({"unexpected": "value"}),
            lambda doc: doc["records"][0].update({"ip_address": "999.1.1.1"}),
            lambda doc: doc["records"][0].update({"mac_address": "bad-mac"}),
            lambda doc: doc["records"][0].update({"device_kind": "codec"}),
            lambda doc: doc["records"][0].update({"diagnostic_model": "Completely Unsupported Device"}),
        ):
            invalid = copy.deepcopy(valid)
            mutation(invalid)
            invalid["snapshot_id"] = compute_snapshot_id(invalid["records"])
            with self.assertRaises(EquipmentInventoryLoadError) as error:
                inventory_from_document(invalid)
            self.assertEqual(InventoryLoadFailure.INVALID_SNAPSHOT, error.exception.category)

    def test_rejects_invalid_root_metadata(self):
        valid = snapshot_document([record("RID-1", diagnostic_model="Huawei TE20")], generated_at="2026-07-23T00:00:00Z")
        invalid_schema = copy.deepcopy(valid)
        invalid_schema["schema_version"] = True
        with self.assertRaises(EquipmentInventoryLoadError) as error:
            inventory_from_document(invalid_schema)
        self.assertEqual(InventoryLoadFailure.UNSUPPORTED_SCHEMA, error.exception.category)

        invalid_generated_at = copy.deepcopy(valid)
        invalid_generated_at["generated_at"] = "nonsense"
        with self.assertRaises(EquipmentInventoryLoadError) as error:
            inventory_from_document(invalid_generated_at)
        self.assertEqual(InventoryLoadFailure.INVALID_SNAPSHOT, error.exception.category)

    def test_schema_v1_loads_with_room_vip_none_and_schema_v2_validates_vip(self):
        v1_document = snapshot_document(
            [record("RID-1", room_vip=True)],
            schema_version=SCHEMA_VERSION_V1,
        )
        inventory = inventory_from_document(v1_document)
        self.assertEqual(SCHEMA_VERSION_V1, inventory.metadata.schema_version)
        self.assertIsNone(inventory.records[0].room_vip)

        v2_document = snapshot_document(
            [record("RID-1", room_vip=True)],
            schema_version=SCHEMA_VERSION_V2,
        )
        inventory = inventory_from_document(v2_document)
        self.assertTrue(inventory.records[0].room_vip)

        invalid = copy.deepcopy(v2_document)
        invalid["records"][0]["room_vip"] = "true"
        invalid["snapshot_id"] = compute_snapshot_id(
            invalid["records"],
            schema_version=SCHEMA_VERSION_V2,
        )
        with self.assertRaises(EquipmentInventoryLoadError) as error:
            inventory_from_document(invalid)
        self.assertEqual(InventoryLoadFailure.INVALID_SNAPSHOT, error.exception.category)

    def test_load_failure_categories_and_default_path_resolution(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            with self.assertRaises(EquipmentInventoryLoadError) as error:
                load_equipment_inventory(missing)
            self.assertEqual(InventoryLoadFailure.NOT_FOUND, error.exception.category)

            invalid_json = Path(directory) / "invalid.json"
            invalid_json.write_text("{", encoding="utf-8")
            with self.assertRaises(EquipmentInventoryLoadError) as error:
                load_equipment_inventory(invalid_json)
            self.assertEqual(InventoryLoadFailure.INVALID_FORMAT, error.exception.category)

            invalid_utf8 = Path(directory) / "invalid_utf8.json"
            invalid_utf8.write_bytes(b"\xff\xfe\xfa")
            with self.assertRaises(EquipmentInventoryLoadError) as error:
                load_equipment_inventory(invalid_utf8)
            self.assertEqual(InventoryLoadFailure.INVALID_FORMAT, error.exception.category)

            unsupported = Path(directory) / "unsupported.json"
            unsupported.write_text(json.dumps({"schema_version": 5, "snapshot_id": "sha256:" + "0" * 64, "records": []}), encoding="utf-8")
            with self.assertRaises(EquipmentInventoryLoadError) as error:
                load_equipment_inventory(unsupported)
            self.assertEqual(InventoryLoadFailure.UNSUPPORTED_SCHEMA, error.exception.category)

            unreadable = Path(directory) / "unreadable.json"
            unreadable.write_text("{}", encoding="utf-8")
            with patch.object(Path, "read_bytes", side_effect=PermissionError("synthetic")):
                with self.assertRaises(EquipmentInventoryLoadError) as error:
                    load_equipment_inventory(unreadable)
            self.assertEqual(InventoryLoadFailure.UNREADABLE, error.exception.category)

        self.assertEqual(application_root() / "equipment_inventory.local.json", default_snapshot_path())

    def test_runtime_does_not_import_spreadsheet_dependency(self):
        sys.modules.pop("openpyxl", None)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            write_snapshot(path, [record("RID-1")])
            script = f"""
import builtins
original_import = builtins.__import__
def reject_spreadsheet_import(name, *args, **kwargs):
    if name == "openpyxl" or name.startswith("openpyxl."):
        raise AssertionError("runtime inventory attempted to import openpyxl")
    return original_import(name, *args, **kwargs)
builtins.__import__ = reject_spreadsheet_import
from core.equipment_inventory import load_equipment_inventory
load_equipment_inventory({str(path)!r})
"""
            subprocess.run([sys.executable, "-c", script], check=True, cwd=application_root())
        self.assertNotIn("openpyxl", sys.modules)


class EquipmentInventoryImporterTests(unittest.TestCase):
    def test_te50_component_recognition_kind_consistency_and_dispatch_composition(self):
        cases = (
            ("RID-TE50-1", "TE50", None, "Video Conference", "Huawei TE50"),
            ("RID-TE50-2", "TE 50", None, "Video Conference", "Huawei TE50"),
            ("RID-TE50-3", "TE-50", None, "Video Conference", "Huawei TE50"),
            ("RID-TE50-4", "Huawei TE50", None, "Video Conference", "Huawei TE50"),
            ("RID-TE50-5", "Huawei_TE.50", None, "Video Conference", "Huawei TE50"),
            ("RID-TE50-NAME", None, "Huawei_TE.50", "Video Conference", "Huawei TE50"),
            ("RID-TE40", "TE40", None, "Video Conference", "Huawei TE40"),
            ("RID-TE500", "TE500", None, "Video Conference", None),
            ("RID-TE501", "TE501", None, "Video Conference", None),
            ("RID-TE60", "TE60", None, "Video Conference", None),
            ("RID-AMBIGUOUS", "TE40 / TE50", None, "Video Conference", None),
            ("RID-TE50-KIND", "TE50", None, "Other", "Huawei TE50"),
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            write_xlsx(source, [
                source_row(
                    record_id,
                    room_id=f"ROOM-{index}",
                    room_name=f"Room {index}",
                    model=model,
                    source_model=source_model,
                    source_type=source_type,
                    manufacturer=None,
                    ip=f"192.0.2.{100 + index}",
                    mac=f"00:11:22:33:aa:{index:02x}",
                    serial=f"TE-{index}",
                    controller=None,
                )
                for index, (record_id, model, source_model, source_type, _expected) in enumerate(cases, start=1)
            ])
            result = import_equipment_inventory(source, output_path=output)
            imported = load_equipment_inventory(output)

        self.assertTrue(result.published, [issue.to_dict() for issue in result.issues])
        by_id = {item.record_id: item for item in imported.records}
        issues = issue_codes_by_record(result.issues)
        for record_id, _model, _name, _kind, expected in cases:
            with self.subTest(record_id=record_id):
                self.assertEqual(expected, by_id[record_id].diagnostic_model)
        self.assertEqual("other", by_id["RID-TE50-KIND"].device_kind)
        self.assertIn("KNOWN_MODEL_TYPE_MISMATCH", issues["RID-TE50-KIND"])
        self.assertEqual({"AMBIGUOUS_DIAGNOSTIC_MODEL"}, issues["RID-AMBIGUOUS"] & {"AMBIGUOUS_DIAGNOSTIC_MODEL", "UNMAPPED_DIAGNOSTIC_MODEL"})
        self.assertEqual({"UNMAPPED_DIAGNOSTIC_MODEL"}, issues["RID-TE500"] & {"AMBIGUOUS_DIAGNOSTIC_MODEL", "UNMAPPED_DIAGNOSTIC_MODEL"})
        self.assertEqual({"UNMAPPED_DIAGNOSTIC_MODEL"}, issues["RID-TE501"] & {"AMBIGUOUS_DIAGNOSTIC_MODEL", "UNMAPPED_DIAGNOSTIC_MODEL"})

        te50 = by_id["RID-TE50-1"]
        resolved = resolve_exact_model_for_ip(
            purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
            normalized_ip=te50.ip_address,
            inventory=imported,
        )
        self.assertEqual(ModelResolutionStatus.RESOLVED, resolved.status)
        self.assertEqual("Huawei TE50", resolved.entry.diagnostic_model)
        self.assertEqual("codec", resolved.entry.screen_key)
        handler = _default_handler_factory("Huawei TE50", {"ip_address": te50.ip_address})
        self.assertIsInstance(handler, HuaweiTE40Handler)
    def test_importer_maps_source_columns_and_nullable_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            write_xlsx(source, [
                source_row("RID-1", room_id=" ROOM-1 ", room_name=" Room One ", source_type="БРП", ip="192.0.2.10", mac="001122334455", serial="  SER-1  ", manufacturer="Aten", model="PE8208AV"),
                source_row("RID-2", room_id=None, room_name="Display Only", source_type="Other", ip="999.1.1.1", mac="not-a-mac", serial=None, manufacturer=None, model=None, controller=None),
            ])
            result = import_equipment_inventory(source, output_path=output, generated_at="2026-07-23T00:00:00Z")
            self.assertTrue(result.published)
            inventory = load_equipment_inventory(output)
            self.assertEqual("SyntheticInventory", result.worksheet)
            self.assertEqual(1, result.header_row)
            self.assertEqual(2, result.source_row_count)
            self.assertEqual(("RID-1",), tuple(item.record_id for item in inventory.find_by_room_and_kind("ROOM-1", "pdu")))
            second = inventory.records[1]
            self.assertIsNone(second.ip_address)
            self.assertIsNone(second.mac_address)
            self.assertIsNone(second.serial_number)
            self.assertIsNone(second.room_id)
            codes = {issue.code for issue in result.issues}
            self.assertIn("INVALID_IP", codes)
            self.assertIn("INVALID_MAC", codes)
            self.assertIn("ROOM_NAME_WITHOUT_ROOM_ID", codes)
            self.assertEqual(set(RECORD_FIELDS_V4), set(json.loads(output.read_text(encoding="utf-8"))["records"][0]))

    def test_importer_maps_room_vip_closed_source_values(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            write_xlsx(source, [
                source_row("RID-1", room_id="ROOM-1", room_vip=True, ip="192.0.2.1", mac="00:11:22:33:44:51", serial="SER-1"),
                source_row("RID-2", room_id="ROOM-2", room_vip=False, ip="192.0.2.2", mac="00:11:22:33:44:52", serial="SER-2"),
                source_row("RID-3", room_id="ROOM-3", room_vip=" ИСТИНА ", ip="192.0.2.3", mac="00:11:22:33:44:53", serial="SER-3"),
                source_row("RID-4", room_id="ROOM-4", room_vip="ложь", ip="192.0.2.4", mac="00:11:22:33:44:54", serial="SER-4"),
                source_row("RID-5", room_id="ROOM-5", room_vip=None, ip="192.0.2.5", mac="00:11:22:33:44:55", serial="SER-5"),
                source_row("RID-6", room_id="ROOM-6", room_vip="true", ip="192.0.2.6", mac="00:11:22:33:44:56", serial="SER-6"),
                source_row("RID-7", room_id="ROOM-7", room_vip=1, ip="192.0.2.7", mac="00:11:22:33:44:57", serial="SER-7"),
            ])
            result = import_equipment_inventory(source, output_path=output)
            inventory = load_equipment_inventory(output)

        self.assertTrue(result.published)
        self.assertEqual(
            (True, False, True, False, None, None, None),
            tuple(record.room_vip for record in inventory.records),
        )
        self.assertEqual(
            2,
            sum(1 for issue in result.issues if issue.code == "INVALID_ROOM_VIP"),
        )

    def test_importer_reports_room_vip_conflict_only_for_true_plus_false(self):
        cases = {
            "all_null": ([None, None], False),
            "true_plus_null": ([True, None], False),
            "false_plus_null": ([False, None], False),
            "repeated_true": ([True, True], False),
            "repeated_false": ([False, False], False),
            "true_plus_false": ([True, False], True),
        }
        for name, (values, expects_conflict) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "inventory.xlsx"
                output = Path(directory) / "snapshot.json"
                write_xlsx(source, [
                    source_row("RID-1", room_id="ROOM-1", room_vip=values[0], ip="192.0.2.10", mac="00:11:22:33:44:55", serial="SER-1"),
                    source_row("RID-2", room_id="ROOM-1", room_vip=values[1], ip="192.0.2.11", mac="00:11:22:33:44:56", serial="SER-2"),
                ])
                result = import_equipment_inventory(source, output_path=output)
                self.assertTrue(result.published)
                codes = {issue.code for issue in result.issues}
                self.assertFalse("ROOM_VIP_CONFLICT" in codes)

    def test_importer_requires_exact_room_vip_header_without_legacy_vip_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            headers = [
                "VIP" if header == SOURCE_COLUMNS["room_vip"] else header
                for header in HEADERS
            ]
            write_xlsx(source, [source_row("RID-1", room_vip=True)], headers=headers)
            result = import_equipment_inventory(source, output_path=output)
        self.assertFalse(result.published)
        self.assertEqual(("SOURCE_STRUCTURE_MISSING",), tuple(issue.code for issue in result.fatal_issues))

    def test_converter_path_resolution_uses_cli_env_and_default_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            env_output = Path(directory) / "env.json"
            cli_source = Path(directory) / "cli.xlsx"
            cli_output = Path(directory) / "cli.json"

            paths = resolve_converter_paths(
                env={
                    SOURCE_XLSX_ENV: str(source),
                    OUTPUT_JSON_ENV: str(env_output),
                }
            )
            self.assertEqual(source.resolve(strict=False), paths.source_xlsx_path)
            self.assertEqual(env_output.resolve(strict=False), paths.output_json_path)

            paths = resolve_converter_paths(
                source_override=cli_source,
                output_override=cli_output,
                env={
                    SOURCE_XLSX_ENV: str(source),
                    OUTPUT_JSON_ENV: str(env_output),
                },
            )
            self.assertEqual(cli_source.resolve(strict=False), paths.source_xlsx_path)
            self.assertEqual(cli_output.resolve(strict=False), paths.output_json_path)

            paths = resolve_converter_paths(
                source_override=cli_source,
                env={},
            )
            self.assertEqual(default_snapshot_path().resolve(strict=False), paths.output_json_path)

        with self.assertRaises(ConverterConfigurationError):
            resolve_converter_paths(env={})

    def test_identity_failures_are_fatal_without_fallback_and_preserve_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            previous = write_snapshot(output, [record("PREVIOUS")])
            previous_text = output.read_text(encoding="utf-8")
            write_xlsx(source, [
                source_row(None),
                source_row("RID-1"),
                source_row("RID-1", ip="192.0.2.11"),
            ])
            result = import_equipment_inventory(source, output_path=output)
            self.assertFalse(result.published)
            self.assertEqual(previous_text, output.read_text(encoding="utf-8"))
            self.assertEqual({"MISSING_RECORD_ID", "DUPLICATE_RECORD_ID"}, {issue.code for issue in result.fatal_issues})
            self.assertEqual(previous["snapshot_id"], load_equipment_inventory(output).metadata.snapshot_id)

    def test_source_mapping_authority_and_consistency_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            write_xlsx(source, [
                source_row("RID-1", room_id="ROOM-1", room_name="Room Alpha", room_address="Address Alpha", source_model="Source Name", source_type="Unexpected", room_vip=True, manufacturer="Huawei", model="TE20", ip="192.0.2.9"),
                source_row("RID-2", room_id="ROOM-1", room_name="Room Beta", room_address="Address Beta", source_type="БРП", room_vip=False, manufacturer="Aten", model="PE8208AV", ip="192.0.2.10", mac="00:11:22:33:44:55", serial="SER-DUP"),
                source_row("RID-3", room_id="ROOM-2", room_name="Room Alpha", source_type="БРП", manufacturer="Aten", model="PE8208AV", ip="192.0.2.10", mac="00-11-22-33-44-55", serial="SER-DUP"),
                source_row("RID-4", room_id="ROOM-1", room_name="Room Beta", source_type="Video Conference", manufacturer="Huawei", model="TE20", ip="192.0.2.44", mac="66:77:88:99:aa:bb", controller="CTRL-A"),
                source_row("RID-5", room_id="ROOM-1", room_name="Room Beta", source_type="БРП", manufacturer="Aten", model="PE8208AV", ip="192.0.2.45", mac="66:77:88:99:aa:bc", controller="CTRL-B"),
                source_row("RID-6", room_id="ROOM-1", room_name="Room Beta", source_type="Video Conference", manufacturer="Huawei", model="TE20", ip="192.0.2.46", mac="66:77:88:99:aa:bd", controller="CTRL-B"),
                source_row("RID-7", room_id="ROOM-3", room_name="Room Gamma", source_model="Huawei TE40", source_type="Video Conference", manufacturer="Huawei", model="TE40", ip="192.0.2.47", mac="66:77:88:99:aa:be", serial="SER-TE40", controller="RID-7"),
            ])
            result = import_equipment_inventory(source, output_path=output)
            inventory = load_equipment_inventory(output)
            self.assertTrue(result.published)
            first = inventory.records[0]
            self.assertEqual("RID-1", first.record_id)
            self.assertEqual("Source Name", first.source_model)
            self.assertEqual("other", first.device_kind)
            self.assertEqual("Huawei TE20", first.diagnostic_model)
            self.assertEqual("Huawei TE40", inventory.records[-1].diagnostic_model)
            self.assertEqual(("RID-2", "RID-3"), tuple(item.record_id for item in inventory.find_by_ip("192.0.2.10")))
            self.assertEqual(("RID-2", "RID-5"), tuple(item.record_id for item in inventory.find_by_room_and_kind("ROOM-1", "pdu")))
            self.assertEqual(("RID-4", "RID-6"), tuple(item.record_id for item in inventory.find_by_room_and_kind("ROOM-1", "video_codec")))
            codes = {issue.code for issue in result.issues}
            self.assertIn("KNOWN_MODEL_TYPE_MISMATCH", codes)
            self.assertIn("SOURCE_MODEL_EVIDENCE_MISMATCH", codes)
            self.assertNotIn("ROOM_ID_NAME_CONFLICT", codes)
            self.assertNotIn("ROOM_VIP_CONFLICT", codes)
            self.assertNotIn("ROOM_ADDRESS_CONFLICT", codes)
            self.assertIn("ROOM_NAME_REUSED", codes)
            self.assertIn("DUPLICATE_IP", codes)
            self.assertIn("DUPLICATE_MAC", codes)
            self.assertIn("DUPLICATE_SERIAL_NUMBER", codes)
            self.assertIn("MULTIPLE_PDU_IN_ROOM", codes)
            self.assertIn("MULTIPLE_VIDEO_CODEC_IN_ROOM", codes)
            self.assertIn("CONTROLLER_REFERENCE_CONFLICT", codes)
            self.assertIn("CONTROLLER_REFERENCE_MISSING_TARGET", codes)
            self.assertNotIn("controller_record_id", json.dumps(json.loads(output.read_text(encoding="utf-8")), ensure_ascii=False))

    def test_pdu_diagnostic_models_with_other_kind_do_not_emit_false_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            write_xlsx(
                source,
                [
                    source_row(
                        "RID-ATEN-OTHER",
                        source_type="Other",
                        manufacturer="Aten",
                        model="PE8208AV",
                        ip="192.0.2.50",
                    ),
                    source_row(
                        "RID-PCS-OTHER",
                        source_type="Other",
                        manufacturer="Extron",
                        model="IPL-T-PCS-4i",
                        ip="192.0.2.51",
                    ),
                    source_row(
                        "RID-ATEN-CONFLICT",
                        source_type="БРП",
                        manufacturer="Aten",
                        model="PE8208AV",
                        ip="192.0.2.52",
                    ),
                ],
            )
            result = import_equipment_inventory(source, output_path=output)
            self.assertTrue(result.published)
            inventory = load_equipment_inventory(output)
            by_id = {item.record_id: item for item in inventory.records}
            self.assertEqual("other", by_id["RID-ATEN-OTHER"].device_kind)
            self.assertEqual("Aten PE8208AV", by_id["RID-ATEN-OTHER"].diagnostic_model)
            self.assertEqual("other", by_id["RID-PCS-OTHER"].device_kind)
            self.assertEqual("Extron IPL T PCS4i", by_id["RID-PCS-OTHER"].diagnostic_model)
            codes_by_record = issue_codes_by_record(result.issues)
            self.assertNotIn(
                "KNOWN_MODEL_TYPE_MISMATCH",
                codes_by_record.get("RID-ATEN-OTHER", set()),
            )
            self.assertNotIn(
                "KNOWN_MODEL_TYPE_MISMATCH",
                codes_by_record.get("RID-PCS-OTHER", set()),
            )
            self.assertIn(
                "KNOWN_MODEL_TYPE_MISMATCH",
                codes_by_record.get("RID-ATEN-CONFLICT", set()),
            )

    def test_diagnostic_model_reconciles_model_and_name_evidence_by_distinct_union(self):
        cases = [
            {
                "record_id": "RID-NAME-ONLY",
                "model": None,
                "source_model": " ATEN Aten PE8208AV ",
                "expected_model": "Aten PE8208AV",
                "expected_issue": None,
                "expected_source_model": "ATEN Aten PE8208AV",
            },
            {
                "record_id": "RID-MODEL-ONLY",
                "model": "TE40",
                "source_model": None,
                "expected_model": "Huawei TE40",
                "expected_issue": None,
                "source_type": "Video Conference",
            },
            {
                "record_id": "RID-MODEL-UNMAPPED-NAME",
                "model": "TE40",
                "source_model": "Synthetic terminal",
                "expected_model": "Huawei TE40",
                "expected_issue": None,
                "source_type": "Video Conference",
            },
            {
                "record_id": "RID-AGREE",
                "model": "PE8208AV",
                "source_model": "ATEN Aten PE8208AV",
                "expected_model": "Aten PE8208AV",
                "expected_issue": None,
                "source_type": "Other",
                "manufacturer": "Aten",
            },
            {
                "record_id": "RID-DISAGREE",
                "model": "IPL-T-PCS-4i",
                "source_model": "ATEN Aten PE8208AV",
                "expected_model": None,
                "expected_issue": "AMBIGUOUS_DIAGNOSTIC_MODEL",
                "source_type": "Other",
                "manufacturer": None,
            },
            {
                "record_id": "RID-MODEL-AMB-NAME-AGREES",
                "model": "TE20 / TE40",
                "source_model": "Huawei TE20",
                "expected_model": None,
                "expected_issue": "AMBIGUOUS_DIAGNOSTIC_MODEL",
                "source_type": "Video Conference",
                "manufacturer": None,
            },
            {
                "record_id": "RID-NAME-AMB-MODEL-AGREES",
                "model": "TE20",
                "source_model": "Huawei TE20 / Huawei TE40",
                "expected_model": None,
                "expected_issue": "AMBIGUOUS_DIAGNOSTIC_MODEL",
                "source_type": "Video Conference",
                "manufacturer": None,
            },
            {
                "record_id": "RID-AMB-UNMAPPED",
                "model": "TE20 / TE40",
                "source_model": "Synthetic terminal",
                "expected_model": None,
                "expected_issue": "AMBIGUOUS_DIAGNOSTIC_MODEL",
                "source_type": "Video Conference",
                "manufacturer": None,
            },
            {
                "record_id": "RID-BOTH-UNMAPPED",
                "model": "CloudLink Box 610",
                "source_model": "Huawei CloudLink Box 610",
                "expected_model": None,
                "expected_issue": "UNMAPPED_DIAGNOSTIC_MODEL",
                "source_type": "Video Conference",
                "manufacturer": None,
            },
        ]
        model_issue_codes = {"UNMAPPED_DIAGNOSTIC_MODEL", "AMBIGUOUS_DIAGNOSTIC_MODEL"}

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            rows = []
            for index, case in enumerate(cases, start=1):
                rows.append(
                    source_row(
                        case["record_id"],
                        room_id=f"ROOM-REC-{index}",
                        room_name=f"Reconciliation Room {index}",
                        source_model=case["source_model"],
                        source_type=case.get("source_type", "Other"),
                        manufacturer=case.get("manufacturer", "Huawei"),
                        model=case["model"],
                        ip=f"192.0.2.{30 + index}",
                        mac=f"00:11:22:33:77:{index:02x}",
                        serial=f"REC-{index}",
                        controller=None,
                    )
                )
            write_xlsx(source, rows)
            result = import_equipment_inventory(source, output_path=output)
            inventory = load_equipment_inventory(output)

        self.assertTrue(result.published, [issue.to_dict() for issue in result.issues])
        by_id = {record.record_id: record for record in inventory.records}
        codes_by_record = issue_codes_by_record(result.issues)
        for case in cases:
            with self.subTest(record_id=case["record_id"]):
                item = by_id[case["record_id"]]
                self.assertEqual(case["expected_model"], item.diagnostic_model)
                self.assertEqual(case.get("expected_source_model", case["source_model"]), item.source_model)
                model_issues = codes_by_record.get(case["record_id"], set()) & model_issue_codes
                if case["expected_issue"] is None:
                    self.assertEqual(set(), model_issues)
                else:
                    self.assertEqual({case["expected_issue"]}, model_issues)

    def test_cloudlink_box_310_recognition_preserves_field_boundaries_and_bar_distinction(self):
        cases = (
            ("BOX-MODEL-HUAWEI", "Huawei CloudLink Box 310", "Synthetic", "CloudLink Box 310", None),
            ("BOX-MODEL-SEPARATORS", "CloudLink-Box-310", "Synthetic", "CloudLink Box 310", None),
            ("BOX-NAME-COMPACT", None, "cloudlink_box310", "CloudLink Box 310", None),
            ("BOX-NAME-CASE", None, "CLOUDLINK BOX 310", "CloudLink Box 310", None),
            ("BOX-MISSING-CLOUDLINK", "Box 310", "Synthetic", None, "UNMAPPED_DIAGNOSTIC_MODEL"),
            ("BOX-MISSING-BOX", "CloudLink 310", "Synthetic", None, "UNMAPPED_DIAGNOSTIC_MODEL"),
            ("BOX-MISSING-310", "CloudLink Box", "Synthetic", None, "UNMAPPED_DIAGNOSTIC_MODEL"),
            ("BOX-WRONG-VERSION", "CloudLink Box 610", "Synthetic", None, "UNMAPPED_DIAGNOSTIC_MODEL"),
            ("BAR-EXACT", "CloudLink Bar 310", "Synthetic", "CloudLink Bar 310", None),
            ("BOX-EXACT", "CloudLink Box 310", "Synthetic", "CloudLink Box 310", None),
            ("BAR-BOX-CONFLICT", "CloudLink Bar 310", "CloudLink Box 310", None, "AMBIGUOUS_DIAGNOSTIC_MODEL"),
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            write_xlsx(
                source,
                [
                    source_row(
                        record_id,
                        room_id=f"ROOM-{index}",
                        room_name=f"Room {index}",
                        model=model,
                        source_model=source_model,
                        source_type="Video Conference",
                        ip=f"192.0.2.{150 + index}",
                        mac=f"00:11:22:33:88:{index:02x}",
                        serial=f"BOX-{index}",
                        controller=None,
                    )
                    for index, (record_id, model, source_model, _expected, _issue) in enumerate(cases, start=1)
                ],
            )
            result = import_equipment_inventory(source, output_path=output)
            imported = load_equipment_inventory(output)

        by_id = {item.record_id: item for item in imported.records}
        codes_by_record = issue_codes_by_record(result.issues)
        for record_id, _model, _source_model, expected, issue in cases:
            with self.subTest(record_id=record_id):
                self.assertEqual(expected, by_id[record_id].diagnostic_model)
                model_issues = codes_by_record.get(record_id, set()) & {
                    "UNMAPPED_DIAGNOSTIC_MODEL", "AMBIGUOUS_DIAGNOSTIC_MODEL"
                }
                self.assertEqual(set() if issue is None else {issue}, model_issues)

    def test_name_evidence_recognizes_every_closed_registry_model(self):
        cases = [
            ("RID-NAME-01", "Huawei TE20", "Huawei TE20", "Video Conference"),
            ("RID-NAME-02", "Huawei TE40", "Huawei_TE.40", "Video Conference"),
            ("RID-NAME-03", "CloudLink Bar 310", "cloudlink/bar-310", "Video Conference"),
            ("RID-NAME-03B", "CloudLink Box 310", "cloudlink_box310", "Video Conference"),
            ("RID-NAME-04", "Polycom RPG 310", "polycom_rpg_310", "Video Conference"),
            ("RID-NAME-05", "Polycom RPG 310", "RealPresence Group 310", "Video Conference"),
            ("RID-NAME-06", "Extron IN1804", "in1804", "Other"),
            ("RID-NAME-07", "Aten PE8208AV", "pe8208", "Other"),
            ("RID-NAME-08", "Extron IPL T PCS4i", "IPL-T-PCS-4i", "Other"),
            ("RID-NAME-09", "Biamp Tesira Forte CI", "tesira forte", "Other"),
            ("RID-NAME-10", "Biamp Tesira Forte CI", "TESIRA FORTÉ CI", "Other"),
            ("RID-NAME-11", "Extron DMP 64 Plus", "DMP64", "Other"),
            ("RID-NAME-12", "Extron DMP 64 Plus", "DMP 64 Plus", "Other"),
        ]

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            rows = []
            for index, (record_id, _expected_model, source_model, source_type) in enumerate(cases, start=1):
                rows.append(
                    source_row(
                        record_id,
                        room_id=f"ROOM-NAME-{index}",
                        room_name=f"Name Evidence Room {index}",
                        source_model=source_model,
                        source_type=source_type,
                        manufacturer=None,
                        model=None,
                        ip=f"192.0.2.{50 + index}",
                        mac=f"00:11:22:33:88:{index:02x}",
                        serial=f"NAME-{index}",
                        controller=None,
                    )
                )
            write_xlsx(source, rows)
            result = import_equipment_inventory(source, output_path=output)
            inventory = load_equipment_inventory(output)

        self.assertTrue(result.published, [issue.to_dict() for issue in result.issues])
        codes_by_record = issue_codes_by_record(result.issues)
        by_id = {record.record_id: record for record in inventory.records}
        self.assertEqual({case[1] for case in cases}, {record.diagnostic_model for record in inventory.records})
        for record_id, expected_model, source_model, source_type in cases:
            with self.subTest(record_id=record_id):
                self.assertEqual(expected_model, by_id[record_id].diagnostic_model)
                self.assertEqual(source_model, by_id[record_id].source_model)
                self.assertEqual("video_codec" if source_type == "Video Conference" else "other", by_id[record_id].device_kind)
                self.assertNotIn("UNMAPPED_DIAGNOSTIC_MODEL", codes_by_record.get(record_id, set()))
                self.assertNotIn("AMBIGUOUS_DIAGNOSTIC_MODEL", codes_by_record.get(record_id, set()))

    def test_name_evidence_preserves_boundaries_and_kind_diagnostics(self):
        boundary_values = ("LTE 40", "TE200", "TE401", "IN18040", "PE82080", "DMP640")
        model_issue_codes = {"UNMAPPED_DIAGNOSTIC_MODEL", "AMBIGUOUS_DIAGNOSTIC_MODEL"}

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            rows = [
                source_row(
                    "RID-KIND-MISMATCH",
                    source_model="ATEN Aten PE8208AV",
                    source_type="БРП",
                    manufacturer=None,
                    model=None,
                    ip="192.0.2.70",
                    mac="00:11:22:33:99:01",
                    serial="KIND-1",
                    controller=None,
                )
            ]
            for index, value in enumerate(boundary_values, start=1):
                rows.append(
                    source_row(
                        f"RID-BOUNDARY-{index}",
                        room_id=f"ROOM-BOUNDARY-{index}",
                        room_name=f"Boundary Name Room {index}",
                        source_model=value,
                        source_type="Video Conference",
                        manufacturer=None,
                        model=value,
                        ip=f"192.0.2.{70 + index}",
                        mac=f"00:11:22:33:99:{index + 1:02x}",
                        serial=f"BOUNDARY-NAME-{index}",
                        controller=None,
                    )
                )
            write_xlsx(source, rows)
            result = import_equipment_inventory(source, output_path=output)
            inventory = load_equipment_inventory(output)

        self.assertTrue(result.published, [issue.to_dict() for issue in result.issues])
        by_id = {record.record_id: record for record in inventory.records}
        codes_by_record = issue_codes_by_record(result.issues)
        kind_record = by_id["RID-KIND-MISMATCH"]
        self.assertEqual("Aten PE8208AV", kind_record.diagnostic_model)
        self.assertEqual("pdu", kind_record.device_kind)
        self.assertIn("KNOWN_MODEL_TYPE_MISMATCH", codes_by_record.get("RID-KIND-MISMATCH", set()))
        for index, value in enumerate(boundary_values, start=1):
            record_id = f"RID-BOUNDARY-{index}"
            with self.subTest(value=value):
                self.assertIsNone(by_id[record_id].diagnostic_model)
                self.assertEqual(value, by_id[record_id].source_model)
                self.assertEqual({"UNMAPPED_DIAGNOSTIC_MODEL"}, codes_by_record.get(record_id, set()) & model_issue_codes)

    def test_importer_recognizes_closed_diagnostic_model_registry_components(self):
        cases = [
            ("RID-01", "Huawei TE20", "TE20", None, "Video Conference"),
            ("RID-02", "Huawei TE40", "Huawei_TE.40", "Conflicting Maker", "Video Conference"),
            ("RID-03", "CloudLink Bar 310", "cloudlink/bar-310", "Huawei", "Video Conference"),
            ("RID-03B", "CloudLink Box 310", "CloudLink-Box-310", "Huawei", "Video Conference"),
            ("RID-04", "Polycom RPG 310", "polycom_rpg_310", "Polycom", "Video Conference"),
            ("RID-05", "Polycom RPG 310", "RealPresence Group 310", "Polycom", "Video Conference"),
            ("RID-06", "Extron IN1804", "in1804", "Extron", "Other"),
            ("RID-07", "Aten PE8208AV", "pe8208", None, "БРП"),
            ("RID-08", "Aten PE8208AV", "PE8208AV", "Other Maker", "БРП"),
            ("RID-09", "Extron IPL T PCS4i", "IPL-T-PCS-4i", "Extron", "Other"),
            ("RID-10", "Biamp Tesira Forte CI", "tesira forte", "Biamp", "Other"),
            ("RID-11", "Biamp Tesira Forte CI", "TESIRA FORTÉ CI", "Biamp", "Other"),
            ("RID-12", "Extron DMP 64 Plus", "DMP64", "Extron", "Other"),
            ("RID-13", "Extron DMP 64 Plus", "DMP 64 Plus", "Extron", "Other"),
        ]
        expected_kind = {
            "Video Conference": "video_codec",
            "БРП": "pdu",
            "Other": "other",
        }

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            rows = []
            for index, (record_id, expected_model, model, manufacturer, source_type) in enumerate(cases, start=1):
                rows.append(
                    source_row(
                        record_id,
                        room_id=f"ROOM-{index:02d}",
                        room_name=f"Synthetic Room {index:02d}",
                        source_model=f"Authority Source {record_id}",
                        source_type=source_type,
                        manufacturer=manufacturer,
                        model=model,
                        ip=f"192.0.2.{index}",
                        mac=f"00:11:22:33:44:{index:02x}",
                        serial=f"SER-{index:02d}",
                        controller=None,
                    )
                )
            write_xlsx(source, rows)
            result = import_equipment_inventory(source, output_path=output, generated_at="2026-07-30T00:00:00Z")
            self.assertTrue(result.published, [issue.to_dict() for issue in result.issues])
            inventory = load_equipment_inventory(output)

        codes_by_record = issue_codes_by_record(result.issues)
        by_id = {record.record_id: record for record in inventory.records}
        self.assertEqual({case[1] for case in cases}, {record.diagnostic_model for record in inventory.records})
        for record_id, expected_model, _model, _manufacturer, source_type in cases:
            with self.subTest(record_id=record_id):
                self.assertEqual(expected_model, by_id[record_id].diagnostic_model)
                self.assertEqual(f"Authority Source {record_id}", by_id[record_id].source_model)
                self.assertEqual(expected_kind[source_type], by_id[record_id].device_kind)
                self.assertNotIn("UNMAPPED_DIAGNOSTIC_MODEL", codes_by_record.get(record_id, set()))
                self.assertNotIn("AMBIGUOUS_DIAGNOSTIC_MODEL", codes_by_record.get(record_id, set()))

    def test_importer_preserves_mixed_component_separator_boundaries(self):
        positive_cases = [
            ("RID-MIX-P1", "IPL_PCS_4i"),
            ("RID-MIX-P2", "IPL-PCS-4i"),
            ("RID-MIX-P3", "IPL PCS PCS4i"),
        ]
        negative_cases = [
            ("RID-MIX-N1", "IPL_PCS_4_i"),
            ("RID-MIX-N2", "IPL-PCS-4-i"),
            ("RID-MIX-N3", "IPL PCS 4 i"),
            ("RID-MIX-N4", "IPL.PCS.4.i"),
            ("RID-MIX-N5", "IPL/PCS/4/i"),
        ]
        model_issue_codes = {"UNMAPPED_DIAGNOSTIC_MODEL", "AMBIGUOUS_DIAGNOSTIC_MODEL"}

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            rows = []
            for index, (record_id, model) in enumerate(positive_cases + negative_cases, start=1):
                rows.append(
                    source_row(
                        record_id,
                        room_id=f"ROOM-MIX-{index}",
                        room_name=f"Mixed Component Room {index}",
                        source_model=f"Source Authority {record_id}",
                        source_type="Other",
                        manufacturer="Extron",
                        model=model,
                        ip=f"192.0.2.{120 + index}",
                        mac=f"00:11:22:33:66:{index:02x}",
                        serial=f"MIXED-{index}",
                        controller=None,
                    )
                )
            write_xlsx(source, rows)
            result = import_equipment_inventory(source, output_path=output)
            self.assertTrue(result.published, [issue.to_dict() for issue in result.issues])
            inventory = load_equipment_inventory(output)

        by_id = {record.record_id: record for record in inventory.records}
        codes_by_record = issue_codes_by_record(result.issues)
        for record_id, _model in positive_cases:
            with self.subTest(record_id=record_id):
                self.assertEqual("Extron IPL T PCS4i", by_id[record_id].diagnostic_model)
                self.assertEqual(set(), codes_by_record.get(record_id, set()) & model_issue_codes)
        for record_id, _model in negative_cases:
            with self.subTest(record_id=record_id):
                self.assertIsNone(by_id[record_id].diagnostic_model)
                self.assertEqual({"UNMAPPED_DIAGNOSTIC_MODEL"}, codes_by_record.get(record_id, set()) & model_issue_codes)

    def test_importer_classifies_unmapped_and_ambiguous_model_evidence(self):
        cases = [
            ("RID-BLANK", None, "UNMAPPED_DIAGNOSTIC_MODEL"),
            ("RID-LTE", "LTE 40", "UNMAPPED_DIAGNOSTIC_MODEL"),
            ("RID-TE200", "TE200", "UNMAPPED_DIAGNOSTIC_MODEL"),
            ("RID-TE401", "TE401", "UNMAPPED_DIAGNOSTIC_MODEL"),
            ("RID-IN18040", "IN18040", "UNMAPPED_DIAGNOSTIC_MODEL"),
            ("RID-PE82080", "PE82080", "UNMAPPED_DIAGNOSTIC_MODEL"),
            ("RID-DMP640", "DMP640", "UNMAPPED_DIAGNOSTIC_MODEL"),
            ("RID-AMB", "TE20 / TE40", "AMBIGUOUS_DIAGNOSTIC_MODEL"),
        ]
        model_issue_codes = {"UNMAPPED_DIAGNOSTIC_MODEL", "AMBIGUOUS_DIAGNOSTIC_MODEL"}

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            rows = []
            for index, (record_id, model, _expected_issue) in enumerate(cases, start=1):
                rows.append(
                    source_row(
                        record_id,
                        room_id=f"ROOM-X{index}",
                        room_name=f"Boundary Room {index}",
                        source_model=f"Preserved Source {record_id}",
                        source_type="Video Conference",
                        manufacturer="Huawei",
                        model=model,
                        ip=f"192.0.2.{100 + index}",
                        mac=f"00:11:22:33:55:{index:02x}",
                        serial=f"BOUNDARY-{index}",
                        controller=None,
                    )
                )
            write_xlsx(source, rows)
            result = import_equipment_inventory(source, output_path=output)
            self.assertTrue(result.published, [issue.to_dict() for issue in result.issues])
            inventory = load_equipment_inventory(output)

        by_id = {record.record_id: record for record in inventory.records}
        codes_by_record = issue_codes_by_record(result.issues)
        for record_id, _model, expected_issue in cases:
            with self.subTest(record_id=record_id):
                self.assertIsNone(by_id[record_id].diagnostic_model)
                self.assertEqual(f"Preserved Source {record_id}", by_id[record_id].source_model)
                self.assertEqual("video_codec", by_id[record_id].device_kind)
                record_model_issues = codes_by_record.get(record_id, set()) & model_issue_codes
                self.assertEqual({expected_issue}, record_model_issues)
        self.assertNotIn("Huawei TE20", {record.diagnostic_model for record in inventory.records})
        self.assertNotIn("Huawei TE40", {record.diagnostic_model for record in inventory.records})

    def test_snapshot_identity_is_deterministic_and_metadata_independent(self):
        with tempfile.TemporaryDirectory() as directory:
            source_a = Path(directory) / "a.xlsx"
            source_b = Path(directory) / "b.xlsx"
            output_a = Path(directory) / "a.json"
            output_b = Path(directory) / "b.json"
            rows = [
                source_row("RID-2", ip="192.0.2.12", mac="00:11:22:33:44:56", serial="SER-2"),
                source_row("RID-1", ip="192.0.2.11", mac="00:11:22:33:44:55", serial="SER-1"),
            ]
            write_xlsx(source_a, rows)
            write_xlsx(source_b, list(reversed(rows)))
            result_a = import_equipment_inventory(source_a, output_path=output_a, generated_at="2026-07-23T00:00:00Z")
            result_b = import_equipment_inventory(source_b, output_path=output_b, generated_at="2026-07-24T00:00:00Z")
            changed = copy.deepcopy(json.loads(output_a.read_text(encoding="utf-8")))
            changed["generated_at"] = "2026-07-25T00:00:00Z"
            changed["source_row_count"] = 999
            changed_mac = copy.deepcopy(changed)
            changed_mac["records"][0]["mac_address"] = "00:11:22:33:44:57"
            changed_serial = copy.deepcopy(changed)
            changed_serial["records"][0]["serial_number"] = "SER-CHANGED"
        self.assertEqual(result_a.snapshot_id, result_b.snapshot_id)
        self.assertEqual(changed["snapshot_id"], compute_snapshot_id(changed["records"]))
        self.assertNotEqual(changed["snapshot_id"], compute_snapshot_id(changed_mac["records"]))
        self.assertNotEqual(changed["snapshot_id"], compute_snapshot_id(changed_serial["records"]))

    def test_missing_required_source_structure_is_fatal(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            headers = [header for header in HEADERS if header != SOURCE_COLUMNS["record_id"]]
            write_xlsx(source, [source_row("RID-1")], headers=headers)
            result = import_equipment_inventory(source, output_path=output)
        self.assertFalse(result.published)
        self.assertFalse(output.exists())
        self.assertEqual(("SOURCE_STRUCTURE_MISSING",), tuple(issue.code for issue in result.fatal_issues))

    def test_sparse_worksheet_header_row_uses_excel_row_numbers_not_list_indexes(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            write_xlsx_sheets(
                source,
                [("SparseRows", [source_row("RID-1"), source_row("RID-2", ip="192.0.2.11")], HEADERS, 5)],
            )
            result = import_equipment_inventory(source, output_path=output)
            inventory = load_equipment_inventory(output)
        self.assertTrue(result.published)
        self.assertEqual("SparseRows", result.worksheet)
        self.assertEqual(5, result.header_row)
        self.assertEqual(2, result.source_row_count)
        self.assertEqual(("RID-1", "RID-2"), tuple(record.record_id for record in inventory.records))

    def test_multiple_matching_worksheets_are_ambiguous_even_when_one_is_active(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            write_xlsx_sheets(
                source,
                [
                    ("First", [source_row("RID-1")], HEADERS),
                    ("Second", [source_row("RID-2")], HEADERS),
                ],
                active_index=1,
            )
            result = import_equipment_inventory(source, output_path=output)
        self.assertFalse(result.published)
        self.assertFalse(output.exists())
        self.assertEqual(("SOURCE_STRUCTURE_AMBIGUOUS",), tuple(issue.code for issue in result.fatal_issues))


class EquipmentInventoryConverterOperationTests(unittest.TestCase):
    def _write_primary_and_network(self, directory):
        source = Path(directory) / "inventory.xlsx"
        network = Path(directory) / "network.xlsx"
        write_xlsx(
            source,
            [
                source_row(
                    "RID-1",
                    source_model="Huawei TE20",
                    ip="192.0.2.10",
                    mac="00:11:22:33:44:01",
                    serial="SER-1",
                    manufacturer="Huawei",
                    model="TE20",
                    controller=None,
                )
            ],
        )
        write_network_xlsx(network, [network_row("00-11-22-33-44-01")])
        return source, network

    def assertClosedReportShape(self, report):
        self.assertTrue(
            {
                "operation",
                "status",
                "stage_reached",
                "schema_version",
                "source_files",
                "output_path",
                "published",
                "data_quality_issue_count",
                "consistency_issue_count",
                "worksheet",
                "header_row",
                "source_row_count",
                "record_count",
                "snapshot_id",
                "fatal_issue_count",
                "non_fatal_issue_count",
                "issues",
            }.issubset(report)
        )
        self.assertEqual({"primary", "network"}, set(report["source_files"]))
        for issue in report["issues"]:
            self.assertEqual(
                {
                    "class",
                    "code",
                    "sheet",
                    "row",
                    "record_id",
                    "description",
                    "stage",
                    "source_file_role",
                    "source_column",
                    "related_row",
                    "details",
                },
                set(issue),
            )
            self.assertIsInstance(issue["details"], dict)

    def test_preflight_operations_use_closed_report_shape_and_do_not_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            source, network = self._write_primary_and_network(directory)
            output = Path(directory) / "snapshot.json"
            output.write_text("previous-output", encoding="utf-8")

            primary = preflight_primary_source(source)
            network_result = preflight_network_source(network)
            combined = preflight_combined_sources(source, network)
            preserved_output = output.read_text(encoding="utf-8")

        self.assertEqual("previous-output", preserved_output)
        self.assertEqual(ConverterOperation.PRIMARY_SOURCE_PREFLIGHT.value, primary.operation)
        self.assertEqual(ConverterOperation.NETWORK_SOURCE_PREFLIGHT.value, network_result.operation)
        self.assertEqual(ConverterOperation.COMBINED_PREFLIGHT.value, combined.operation)
        self.assertFalse(primary.published)
        self.assertFalse(network_result.published)
        self.assertFalse(combined.published)
        self.assertIsNone(primary.output_path)
        self.assertIsNone(network_result.output_path)
        self.assertIsNone(combined.output_path)
        self.assertEqual(SCHEMA_VERSION_V4, combined.schema_version)
        self.assertIsNotNone(combined.snapshot_id)
        self.assertEqual(1, combined.record_count)
        self.assertNotIn("NETWORK_MAC_NOT_IN_INVENTORY", {issue.code for issue in network_result.issues})
        for result in (primary, network_result, combined):
            self.assertEqual(ConverterStage.COMPLETE.value, result.stage_reached)
            self.assertClosedReportShape(result.to_report())

    def test_conversion_rereads_current_source_after_successful_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            source, network = self._write_primary_and_network(directory)
            output = Path(directory) / "snapshot.json"
            preflight = preflight_combined_sources(source, network)
            self.assertEqual("SUCCEEDED", preflight.status)

            write_xlsx(source, [source_row(None, mac="00:11:22:33:44:01")])
            result = import_equipment_inventory(source, network_source_path=network, output_path=output)

        self.assertFalse(result.published)
        self.assertFalse(output.exists())
        self.assertEqual(("MISSING_RECORD_ID",), tuple(issue.code for issue in result.fatal_issues))

    def test_guarded_publication_allows_absent_and_unchanged_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source, network = self._write_primary_and_network(directory)
            absent_output = Path(directory) / "absent.json"
            absent_precondition = capture_output_precondition(absent_output)
            absent = import_equipment_inventory(
                source,
                network_source_path=network,
                output_path=absent_output,
                publication_precondition=absent_precondition,
            )

            existing_output = Path(directory) / "existing.json"
            existing_output.write_text("previous-output", encoding="utf-8")
            existing_precondition = capture_output_precondition(existing_output)
            existing = import_equipment_inventory(
                source,
                network_source_path=network,
                output_path=existing_output,
                publication_precondition=existing_precondition,
            )
            absent_schema = json.loads(absent_output.read_text(encoding="utf-8"))["schema_version"]
            existing_schema = json.loads(existing_output.read_text(encoding="utf-8"))["schema_version"]

        self.assertTrue(absent.published)
        self.assertTrue(existing.published)
        self.assertEqual(SCHEMA_VERSION_V4, absent_schema)
        self.assertEqual(SCHEMA_VERSION_V4, existing_schema)

    def test_guarded_publication_rejects_output_state_changes_and_preserves_bytes(self):
        cases = ("appeared", "modified", "deleted", "path_mismatch")
        for case in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as directory:
                    source, network = self._write_primary_and_network(directory)
                    output = Path(directory) / "snapshot.json"
                    call_output = output
                    if case == "appeared":
                        precondition = capture_output_precondition(output)
                        output.write_text("new-current-output", encoding="utf-8")
                        expected = "new-current-output"
                    elif case == "modified":
                        output.write_text("previous-output", encoding="utf-8")
                        precondition = capture_output_precondition(output)
                        output.write_text("changed-output", encoding="utf-8")
                        expected = "changed-output"
                    elif case == "deleted":
                        output.write_text("previous-output", encoding="utf-8")
                        precondition = capture_output_precondition(output)
                        output.unlink()
                        expected = None
                    else:
                        output.write_text("previous-output", encoding="utf-8")
                        precondition = capture_output_precondition(output)
                        call_output = Path(directory) / "other.json"
                        expected = "previous-output"

                    result = import_equipment_inventory(
                        source,
                        network_source_path=network,
                        output_path=call_output,
                        publication_precondition=precondition,
                    )

                    self.assertFalse(result.published)
                    self.assertEqual(("OUTPUT_CHANGED_SINCE_CONFIRMATION",), tuple(issue.code for issue in result.fatal_issues))
                    self.assertEqual(SourceFileRole.OUTPUT.value, result.fatal_issues[0].source_file_role)
                    if expected is None:
                        self.assertFalse(output.exists())
                    else:
                        self.assertEqual(expected, output.read_text(encoding="utf-8"))
                    if call_output != output:
                        self.assertFalse(call_output.exists())


class EquipmentInventoryGitignoreTests(unittest.TestCase):
    def test_production_snapshot_name_is_ignored(self):
        gitignore = (application_root() / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("equipment_inventory.local.json", gitignore)


class EquipmentInventorySchemaV4Tests(unittest.TestCase):
    def test_room_address_mapping_normalizes_blank_and_participates_in_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            output = Path(directory) / "snapshot.json"
            write_xlsx(
                source,
                [
                    source_row("RID-1", room_address="  Cafe\u0301  "),
                    source_row("RID-2", room_address="   ", ip="192.0.2.11", mac="00:11:22:33:44:56", serial="SER-2"),
                ],
            )
            result = import_equipment_inventory(source, output_path=output)
            document = json.loads(output.read_text(encoding="utf-8"))
            changed = copy.deepcopy(document)
            changed["records"][0]["room_address"] = "Different address"

        self.assertTrue(result.published)
        self.assertEqual(SCHEMA_VERSION_V4, document["schema_version"])
        self.assertEqual("Café", document["records"][0]["room_address"])
        self.assertIsNone(document["records"][1]["room_address"])
        self.assertTrue(all(record["switch_ip_address"] is None and record["switch_port"] is None for record in document["records"]))
        self.assertNotEqual(document["snapshot_id"], compute_snapshot_id(changed["records"], schema_version=SCHEMA_VERSION_V4))

    def test_missing_or_ambiguous_room_address_header_is_fatal_and_preserves_output(self):
        for headers in (
            [header for header in HEADERS if header != SOURCE_COLUMNS["room_address"]],
            HEADERS + [SOURCE_COLUMNS["room_address"]],
        ):
            with self.subTest(headers=headers):
                with tempfile.TemporaryDirectory() as directory:
                    source = Path(directory) / "inventory.xlsx"
                    output = Path(directory) / "snapshot.json"
                    write_snapshot(output, [record("PREVIOUS")])
                    previous = output.read_text(encoding="utf-8")
                    write_xlsx(source, [source_row("RID-1")], headers=headers)
                    result = import_equipment_inventory(source, output_path=output)
                    preserved = output.read_text(encoding="utf-8")

                self.assertFalse(result.published)
                self.assertEqual(previous, preserved)
                self.assertTrue(result.fatal_issues)

    def test_schema_v4_is_strict_and_preserves_per_record_room_display_metadata(self):
        document = snapshot_document(
            [
                record("RID-1", room_id="ROOM-1", room_name="One", room_address="Address One", room_vip=True),
                record("RID-2", room_id="ROOM-1", room_name="Two", room_address="Address Two", room_vip=False),
            ],
            schema_version=SCHEMA_VERSION_V4,
        )
        inventory = inventory_from_document(document)
        missing = copy.deepcopy(document)
        del missing["records"][0]["room_address"]
        extra = copy.deepcopy(document)
        extra["records"][0]["extra"] = None

        self.assertEqual(("One", "Two"), tuple(record.room_name for record in inventory.records))
        self.assertEqual(("Address One", "Address Two"), tuple(record.room_address for record in inventory.records))
        for malformed in (missing, extra):
            with self.assertRaises(EquipmentInventoryLoadError) as error:
                inventory_from_document(malformed)
            self.assertEqual(InventoryLoadFailure.INVALID_SNAPSHOT, error.exception.category)


if __name__ == "__main__":
    unittest.main()
