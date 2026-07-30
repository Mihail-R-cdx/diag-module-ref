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
    SCHEMA_VERSION,
    SCHEMA_VERSION_V1,
    SCHEMA_VERSION_V2,
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
    EVIDENCE_COLUMNS,
    OUTPUT_JSON_ENV,
    SOURCE_COLUMNS,
    SOURCE_XLSX_ENV,
    import_equipment_inventory,
    resolve_converter_paths,
)


HEADERS = [
    SOURCE_COLUMNS["room_id"],
    SOURCE_COLUMNS["room_name"],
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


def record(record_id, *, ip_address=None, mac_address=None, serial_number=None, room_id=None, room_name=None, device_kind="other", source_model=None, diagnostic_model=None, room_vip=None):
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
    )


def snapshot_document(records, *, schema_version=SCHEMA_VERSION, **metadata):
    ordered = tuple(sorted(records, key=lambda item: item.record_id))
    fields = RECORD_FIELDS_V1 if schema_version == SCHEMA_VERSION_V1 else RECORD_FIELDS
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


def source_row(record_id, *, room_id="ROOM-1", room_name="Room One", source_model="Huawei TE20", source_type="Video Conference", room_vip=None, ip="192.0.2.10", mac="00-11-22-33-44-55", serial="SER-1", manufacturer="Huawei", model="TE20", controller="CTRL-1"):
    return {
        SOURCE_COLUMNS["room_id"]: room_id,
        SOURCE_COLUMNS["room_name"]: room_name,
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
            unsupported.write_text(json.dumps({"schema_version": 3, "snapshot_id": "sha256:" + "0" * 64, "records": []}), encoding="utf-8")
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
            self.assertEqual(set(RECORD_FIELDS), set(json.loads(output.read_text(encoding="utf-8"))["records"][0]))

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
                self.assertEqual(expects_conflict, "ROOM_VIP_CONFLICT" in codes)

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
                source_row("RID-1", room_id="ROOM-1", room_name="Room Alpha", source_model="Source Name", source_type="Unexpected", manufacturer="Huawei", model="TE20", ip="192.0.2.9"),
                source_row("RID-2", room_id="ROOM-1", room_name="Room Beta", source_type="БРП", manufacturer="Aten", model="PE8208AV", ip="192.0.2.10", mac="00:11:22:33:44:55", serial="SER-DUP"),
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
            self.assertIn("ROOM_ID_NAME_CONFLICT", codes)
            self.assertIn("ROOM_NAME_REUSED", codes)
            self.assertIn("DUPLICATE_IP", codes)
            self.assertIn("DUPLICATE_MAC", codes)
            self.assertIn("DUPLICATE_SERIAL_NUMBER", codes)
            self.assertIn("MULTIPLE_PDU_IN_ROOM", codes)
            self.assertIn("MULTIPLE_VIDEO_CODEC_IN_ROOM", codes)
            self.assertIn("CONTROLLER_REFERENCE_CONFLICT", codes)
            self.assertIn("CONTROLLER_REFERENCE_MISSING_TARGET", codes)
            self.assertNotIn("controller_record_id", json.dumps(json.loads(output.read_text(encoding="utf-8")), ensure_ascii=False))

    def test_importer_recognizes_closed_diagnostic_model_registry_components(self):
        cases = [
            ("RID-01", "Huawei TE20", "TE20", None, "Video Conference"),
            ("RID-02", "Huawei TE40", "Huawei_TE.40", "Conflicting Maker", "Video Conference"),
            ("RID-03", "CloudLink Bar 310", "cloudlink/bar-310", "Huawei", "Video Conference"),
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


class EquipmentInventoryGitignoreTests(unittest.TestCase):
    def test_production_snapshot_name_is_ignored(self):
        gitignore = (application_root() / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("equipment_inventory.local.json", gitignore)


if __name__ == "__main__":
    unittest.main()
