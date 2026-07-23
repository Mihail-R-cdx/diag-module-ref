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
    SCHEMA_VERSION,
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
    EVIDENCE_COLUMNS,
    SOURCE_COLUMNS,
    import_equipment_inventory,
)


HEADERS = [
    SOURCE_COLUMNS["room_id"],
    SOURCE_COLUMNS["room_name"],
    SOURCE_COLUMNS["record_id"],
    SOURCE_COLUMNS["device_kind"],
    SOURCE_COLUMNS["source_model"],
    EVIDENCE_COLUMNS["controller_record_id"],
    EVIDENCE_COLUMNS["model"],
    EVIDENCE_COLUMNS["manufacturer"],
    SOURCE_COLUMNS["ip_address"],
    SOURCE_COLUMNS["mac_address"],
    SOURCE_COLUMNS["serial_number"],
]


def record(record_id, *, ip_address=None, mac_address=None, serial_number=None, room_id=None, room_name=None, device_kind="other", source_model=None, diagnostic_model=None):
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
    )


def snapshot_document(records, **metadata):
    ordered = tuple(sorted(records, key=lambda item: item.record_id))
    document = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": compute_snapshot_id(ordered),
        "records": [record_to_dict(item) for item in ordered],
    }
    document.update(metadata)
    return document


def write_snapshot(path, records, **metadata):
    document = snapshot_document(records, **metadata)
    Path(path).write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return document


def source_row(record_id, *, room_id="ROOM-1", room_name="Room One", source_model="Huawei TE20", source_type="Video Conference", ip="192.0.2.10", mac="00-11-22-33-44-55", serial="SER-1", manufacturer="Huawei", model="TE20", controller="CTRL-1"):
    return {
        SOURCE_COLUMNS["room_id"]: room_id,
        SOURCE_COLUMNS["room_name"]: room_name,
        SOURCE_COLUMNS["record_id"]: record_id,
        SOURCE_COLUMNS["device_kind"]: source_type,
        SOURCE_COLUMNS["source_model"]: source_model,
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


def _sheet_xml(rows, headers=HEADERS):
    def cell(reference, value):
        if value is None:
            return f'<c r="{reference}"/>'
        text = str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f'<c r="{reference}" t="inlineStr"><is><t>{text}</t></is></c>'

    sheet_rows = []
    all_rows = [dict(zip(headers, headers))]
    all_rows.extend(rows)
    for row_index, row in enumerate(all_rows, start=1):
        cells = [cell(f"{_column_name(col_index)}{row_index}", row.get(header)) for col_index, header in enumerate(headers, start=1)]
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<dimension ref="A1:K{len(all_rows)}"/>
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
        f'<sheet name="{name}" sheetId="{index}" r:id="rId{index}"/>'
        for index, (name, _rows, _headers) in enumerate(sheets, start=1)
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
        for index, (_name, sheet_rows, sheet_headers) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _sheet_xml(sheet_rows, sheet_headers))


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
        ):
            invalid = copy.deepcopy(valid)
            mutation(invalid)
            invalid["snapshot_id"] = compute_snapshot_id(invalid["records"])
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
            unsupported.write_text(json.dumps({"schema_version": 2, "snapshot_id": "sha256:" + "0" * 64, "records": []}), encoding="utf-8")
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
