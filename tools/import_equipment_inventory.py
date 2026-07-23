"""Offline importer for canonical equipment inventory snapshots."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from core.equipment_inventory import (  # noqa: E402
    RECORD_FIELDS,
    SCHEMA_VERSION,
    EquipmentRecord,
    compute_snapshot_id,
    default_snapshot_path,
    inventory_from_document,
    normalize_ip_address,
    normalize_mac_address,
    normalize_text,
    record_to_dict,
)


NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

SOURCE_COLUMNS = {
    "record_id": "SmartRoomID",
    "room_id": "ID комнаты",
    "room_name": "Название комнаты",
    "source_model": "Наименование",
    "ip_address": "IP",
    "mac_address": "MAC",
    "serial_number": "Серийный номер",
    "device_kind": "Тип модели",
}
EVIDENCE_COLUMNS = {
    "manufacturer": "Производитель",
    "model": "Модель",
    "controller_record_id": "SmartRoomID контроллера",
}
REQUIRED_SOURCE_COLUMNS = tuple(SOURCE_COLUMNS.values())
OPTIONAL_EVIDENCE_COLUMNS = tuple(EVIDENCE_COLUMNS.values())

DIAGNOSTIC_MODEL_BY_EVIDENCE = {
    ("huawei", "te20"): "Huawei TE20",
    ("huawei", "te40"): "Huawei TE40",
    ("huawei", "bar 310"): "CloudLink Bar 310",
    ("cloudlink", "bar 310"): "CloudLink Bar 310",
    ("polycom", "rpg 310"): "Polycom RPG 310",
    ("polycom", "realpresence group 310"): "Polycom RPG 310",
    ("extron", "in1804"): "Extron IN1804",
    ("biamp", "tesira forte ci"): "Biamp Tesira Forte CI",
    ("aten", "pe8208av"): "Aten PE8208AV",
}
EXPECTED_KIND_BY_DIAGNOSTIC_MODEL = {
    "Huawei TE20": "video_codec",
    "Huawei TE40": "video_codec",
    "CloudLink Bar 310": "video_codec",
    "Polycom RPG 310": "video_codec",
    "Extron IN1804": "other",
    "Biamp Tesira Forte CI": "other",
    "Aten PE8208AV": "pdu",
}


@dataclass(frozen=True)
class ImportIssue:
    issue_class: str
    code: str
    row: int | None = None
    record_id: str | None = None
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "class": self.issue_class,
            "code": self.code,
            "row": self.row,
            "record_id": self.record_id,
            "description": self.description,
        }


@dataclass(frozen=True)
class WorksheetLayout:
    worksheet: str
    header_row: int
    headers: tuple[str, ...]


@dataclass(frozen=True)
class ImportResult:
    published: bool
    output_path: Path
    worksheet: str | None
    header_row: int | None
    source_row_count: int
    record_count: int
    snapshot_id: str | None
    issues: tuple[ImportIssue, ...]

    @property
    def fatal_issues(self) -> tuple[ImportIssue, ...]:
        return tuple(issue for issue in self.issues if issue.issue_class == "fatal")

    @property
    def non_fatal_issues(self) -> tuple[ImportIssue, ...]:
        return tuple(issue for issue in self.issues if issue.issue_class != "fatal")

    def to_report(self) -> dict[str, Any]:
        return {
            "published": self.published,
            "output_path": str(self.output_path),
            "worksheet": self.worksheet,
            "header_row": self.header_row,
            "source_row_count": self.source_row_count,
            "record_count": self.record_count,
            "snapshot_id": self.snapshot_id,
            "fatal_issue_count": len(self.fatal_issues),
            "non_fatal_issue_count": len(self.non_fatal_issues),
            "issues": [issue.to_dict() for issue in self.issues],
        }


def import_equipment_inventory(
    source_path: str | Path,
    *,
    output_path: str | Path | None = None,
    generated_at: str | None = None,
) -> ImportResult:
    source = Path(source_path)
    output = Path(output_path) if output_path is not None else default_snapshot_path()
    generated = generated_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    issues: list[ImportIssue] = []
    try:
        workbook = _read_workbook(source)
    except (OSError, zipfile.BadZipFile, ET.ParseError) as exc:
        return ImportResult(
            published=False,
            output_path=output,
            worksheet=None,
            header_row=None,
            source_row_count=0,
            record_count=0,
            snapshot_id=None,
            issues=(ImportIssue("fatal", "WORKBOOK_UNREADABLE", description=f"Workbook could not be read: {type(exc).__name__}"),),
        )

    layout = _select_layout(workbook, issues)
    if layout is None:
        return ImportResult(False, output, None, None, 0, 0, None, tuple(issues))

    rows = workbook["rows_by_sheet"][layout.worksheet]
    source_rows = [row for row in rows if row[0] > layout.header_row]
    records, row_issues = _build_records(layout, source_rows)
    issues.extend(row_issues)
    issues.extend(_detect_cross_row_issues(records, source_rows, layout))

    if any(issue.issue_class == "fatal" for issue in issues):
        return ImportResult(False, output, layout.worksheet, layout.header_row, len(source_rows), 0, None, tuple(issues))

    ordered_records = tuple(sorted(records, key=lambda record: record.record_id))
    snapshot_id = compute_snapshot_id(ordered_records, schema_version=SCHEMA_VERSION)
    document = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "generated_at": generated,
        "source_row_count": len(source_rows),
        "records": [record_to_dict(record) for record in ordered_records],
    }
    try:
        inventory_from_document(document)
    except Exception as exc:
        issues.append(
            ImportIssue(
                "fatal",
                "CANDIDATE_SNAPSHOT_INVALID",
                description=f"Candidate canonical snapshot failed validation: {type(exc).__name__}",
            )
        )
        return ImportResult(False, output, layout.worksheet, layout.header_row, len(source_rows), 0, None, tuple(issues))

    _atomic_write_json(output, document)
    return ImportResult(True, output, layout.worksheet, layout.header_row, len(source_rows), len(ordered_records), snapshot_id, tuple(issues))


def _build_records(
    layout: WorksheetLayout,
    source_rows: list[tuple[int, tuple[Any, ...]]],
) -> tuple[list[EquipmentRecord], list[ImportIssue]]:
    header_index = {header: index for index, header in enumerate(layout.headers)}
    issues: list[ImportIssue] = []
    records: list[EquipmentRecord] = []
    seen_ids: dict[str, int] = {}

    for row_number, row in source_rows:
        if _is_empty_row(row):
            continue
        record_id = normalize_text(_value(row, header_index, SOURCE_COLUMNS["record_id"]))
        if record_id is None:
            issues.append(ImportIssue("fatal", "MISSING_RECORD_ID", row=row_number, description="SmartRoomID is missing or blank."))
            continue
        if record_id in seen_ids:
            issues.append(ImportIssue("fatal", "DUPLICATE_RECORD_ID", row=row_number, record_id=record_id, description="SmartRoomID duplicates another source row."))
            continue
        seen_ids[record_id] = row_number

        source_type = normalize_text(_value(row, header_index, SOURCE_COLUMNS["device_kind"]))
        device_kind = _map_device_kind(source_type)
        source_model = normalize_text(_value(row, header_index, SOURCE_COLUMNS["source_model"]))
        room_id = normalize_text(_value(row, header_index, SOURCE_COLUMNS["room_id"]))
        room_name = normalize_text(_value(row, header_index, SOURCE_COLUMNS["room_name"]))
        serial_number = normalize_text(_value(row, header_index, SOURCE_COLUMNS["serial_number"]))

        ip_source = _value(row, header_index, SOURCE_COLUMNS["ip_address"])
        ip_address = normalize_ip_address(ip_source)
        if normalize_text(ip_source) is not None and ip_address is None:
            issues.append(ImportIssue("data_quality", "INVALID_IP", row=row_number, record_id=record_id, description="IP is invalid and was represented as null."))

        mac_source = _value(row, header_index, SOURCE_COLUMNS["mac_address"])
        mac_address = normalize_mac_address(mac_source)
        if normalize_text(mac_source) is not None and mac_address is None:
            issues.append(ImportIssue("data_quality", "INVALID_MAC", row=row_number, record_id=record_id, description="MAC is invalid and was represented as null."))

        if room_id is None and room_name is not None:
            issues.append(ImportIssue("consistency", "ROOM_NAME_WITHOUT_ROOM_ID", row=row_number, record_id=record_id, description="Room name is present while room ID is missing."))
        if serial_number is None:
            issues.append(ImportIssue("data_quality", "MISSING_SERIAL_NUMBER", row=row_number, record_id=record_id, description="Serial number is missing."))

        manufacturer = normalize_text(_value(row, header_index, EVIDENCE_COLUMNS["manufacturer"]))
        model = normalize_text(_value(row, header_index, EVIDENCE_COLUMNS["model"]))
        diagnostic_model = _map_diagnostic_model(manufacturer, model)
        if diagnostic_model is None:
            issues.append(ImportIssue("data_quality", "UNMAPPED_DIAGNOSTIC_MODEL", row=row_number, record_id=record_id, description="Diagnostic model is not mapped by reviewed evidence."))
        expected_kind = EXPECTED_KIND_BY_DIAGNOSTIC_MODEL.get(diagnostic_model)
        if expected_kind is not None and expected_kind != device_kind:
            issues.append(ImportIssue("consistency", "KNOWN_MODEL_TYPE_MISMATCH", row=row_number, record_id=record_id, description="Known diagnostic model evidence conflicts with authoritative source type."))
        if source_model is not None and manufacturer is not None and model is not None:
            expected_source_model = normalize_text(f"{manufacturer} {model}")
            if expected_source_model is not None and expected_source_model.casefold() != source_model.casefold():
                issues.append(ImportIssue("consistency", "SOURCE_MODEL_EVIDENCE_MISMATCH", row=row_number, record_id=record_id, description="Source model differs from manufacturer/model evidence."))

        records.append(
            EquipmentRecord(
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
        )

    return records, issues


def _detect_cross_row_issues(
    records: list[EquipmentRecord],
    source_rows: list[tuple[int, tuple[Any, ...]]],
    layout: WorksheetLayout,
) -> tuple[ImportIssue, ...]:
    issues: list[ImportIssue] = []
    header_index = {header: index for index, header in enumerate(layout.headers)}
    row_by_record_id = {record.record_id: row_number for record, (row_number, _) in zip(records, source_rows)}

    room_names_by_id: dict[str, set[str]] = {}
    room_ids_by_name: dict[str, set[str]] = {}
    records_by_room_kind: dict[tuple[str, str], list[EquipmentRecord]] = {}
    values_by_field: dict[str, dict[str, list[EquipmentRecord]]] = {
        "ip_address": {},
        "mac_address": {},
        "serial_number": {},
    }
    for record in records:
        if record.room_id is not None:
            if record.room_name is not None:
                room_names_by_id.setdefault(record.room_id, set()).add(record.room_name)
                room_ids_by_name.setdefault(record.room_name, set()).add(record.room_id)
            records_by_room_kind.setdefault((record.room_id, record.device_kind), []).append(record)
        for field in values_by_field:
            value = getattr(record, field)
            if value is not None:
                values_by_field[field].setdefault(value, []).append(record)

    for room_id, names in room_names_by_id.items():
        if len(names) > 1:
            issues.append(ImportIssue("consistency", "ROOM_ID_NAME_CONFLICT", record_id=room_id, description="One room ID has conflicting room names."))
    for room_name, room_ids in room_ids_by_name.items():
        if len(room_ids) > 1:
            issues.append(ImportIssue("consistency", "ROOM_NAME_REUSED", description="One room name is reused by different room IDs."))
    for (room_id, device_kind), matching in records_by_room_kind.items():
        if device_kind in {"pdu", "video_codec"} and len(matching) > 1:
            issues.append(ImportIssue("consistency", f"MULTIPLE_{device_kind.upper()}_IN_ROOM", record_id=room_id, description="Multiple records of this device kind exist in one room."))
    duplicate_codes = {
        "ip_address": "DUPLICATE_IP",
        "mac_address": "DUPLICATE_MAC",
        "serial_number": "DUPLICATE_SERIAL_NUMBER",
    }
    for field, values in values_by_field.items():
        for matching in values.values():
            if len(matching) > 1:
                issues.append(ImportIssue("data_quality", duplicate_codes[field], record_id=matching[0].record_id, description="A physical identifier is shared by multiple records."))

    if EVIDENCE_COLUMNS["controller_record_id"] in header_index:
        controller_refs_by_room: dict[str, set[str]] = {}
        rooms_with_missing_refs: set[str] = set()
        record_ids = {record.record_id for record in records}
        record_by_id = {record.record_id: record for record in records}
        for row_number, row in source_rows:
            record_id = normalize_text(_value(row, header_index, SOURCE_COLUMNS["record_id"]))
            if record_id is None or record_id not in record_by_id:
                continue
            record = record_by_id[record_id]
            if record.room_id is None:
                continue
            controller_ref = normalize_text(_value(row, header_index, EVIDENCE_COLUMNS["controller_record_id"]))
            if controller_ref is None:
                rooms_with_missing_refs.add(record.room_id)
                continue
            controller_refs_by_room.setdefault(record.room_id, set()).add(controller_ref)
            if controller_ref not in record_ids:
                issues.append(ImportIssue("consistency", "CONTROLLER_REFERENCE_MISSING_TARGET", row=row_number, record_id=record_id, description="Controller reference does not match a source SmartRoomID."))
        for room_id, refs in controller_refs_by_room.items():
            if len(refs) > 1:
                issues.append(ImportIssue("consistency", "CONTROLLER_REFERENCE_CONFLICT", record_id=room_id, description="One room has multiple controller references."))
            if room_id in rooms_with_missing_refs:
                issues.append(ImportIssue("consistency", "CONTROLLER_REFERENCE_PARTIAL", record_id=room_id, description="Controller reference is missing from part of a room."))

    return tuple(issues)


def _select_layout(workbook: dict[str, Any], issues: list[ImportIssue]) -> WorksheetLayout | None:
    candidates: list[WorksheetLayout] = []
    for sheet_name, rows in workbook["rows_by_sheet"].items():
        for row_number, row in rows[:50]:
            headers = tuple(normalize_text(value) or "" for value in row)
            if all(column in headers for column in REQUIRED_SOURCE_COLUMNS):
                candidates.append(WorksheetLayout(sheet_name, row_number, headers))
                break
    if not candidates:
        issues.append(ImportIssue("fatal", "SOURCE_STRUCTURE_MISSING", description="No worksheet contains the confirmed required source columns."))
        return None
    if len(candidates) == 1:
        return candidates[0]
    issues.append(ImportIssue("fatal", "SOURCE_STRUCTURE_AMBIGUOUS", description="Multiple worksheets contain the confirmed source columns."))
    return None


def _read_workbook(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        shared_strings = _read_shared_strings(archive)
        workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
        rels_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_targets = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels_root.findall("rel:Relationship", NS)}

        workbook_view = workbook_root.find("main:bookViews/main:workbookView", NS)
        active_index = int(workbook_view.attrib.get("activeTab", "0")) if workbook_view is not None else 0
        sheets: list[tuple[str, str]] = []
        for sheet in workbook_root.findall("main:sheets/main:sheet", NS):
            sheet_name = sheet.attrib["name"]
            relationship_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = rel_targets[relationship_id]
            if not target.startswith("xl/"):
                target = "xl/" + target.lstrip("/")
            sheets.append((sheet_name, target))

        rows_by_sheet = {
            sheet_name: _read_sheet_rows(archive, target, shared_strings)
            for sheet_name, target in sheets
        }
        return {
            "sheet_names": tuple(sheet_name for sheet_name, _ in sheets),
            "active_sheet": sheets[active_index][0] if sheets else None,
            "rows_by_sheet": rows_by_sheet,
        }


def _read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(text.text or "" for text in item.findall(".//main:t", NS))
        for item in root.findall("main:si", NS)
    ]


def _read_sheet_rows(
    archive: zipfile.ZipFile,
    target: str,
    shared_strings: list[str],
) -> list[tuple[int, tuple[Any, ...]]]:
    root = ET.fromstring(archive.read(target))
    rows: list[tuple[int, tuple[Any, ...]]] = []
    for row in root.findall("main:sheetData/main:row", NS):
        row_number = int(row.attrib.get("r", "0"))
        values: list[Any] = []
        for cell in row.findall("main:c", NS):
            index = _column_index(cell.attrib.get("r", "A1"))
            while len(values) <= index:
                values.append(None)
            values[index] = _cell_value(cell, shared_strings)
        rows.append((row_number, tuple(values)))
    return rows


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> Any:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//main:t", NS))
    value = cell.find("main:v", NS)
    if value is None:
        return None
    raw = value.text or ""
    if cell_type == "s":
        return shared_strings[int(raw)]
    if cell_type == "b":
        return raw == "1"
    return raw


def _column_index(cell_reference: str) -> int:
    letters = "".join(character for character in cell_reference if character.isalpha())
    index = 0
    for character in letters:
        index = index * 26 + ord(character.upper()) - 64
    return index - 1


def _value(row: tuple[Any, ...], header_index: dict[str, int], header: str) -> Any:
    index = header_index.get(header)
    if index is None or index >= len(row):
        return None
    return row[index]


def _is_empty_row(row: tuple[Any, ...]) -> bool:
    return all(normalize_text(value) is None for value in row)


def _map_device_kind(source_type: str | None) -> str:
    if source_type == "Video Conference":
        return "video_codec"
    if source_type == "БРП":
        return "pdu"
    return "other"


def _map_diagnostic_model(manufacturer: str | None, model: str | None) -> str | None:
    if manufacturer is None or model is None:
        return None
    return DIAGNOSTIC_MODEL_BY_EVIDENCE.get((manufacturer.casefold(), model.casefold()))


def _atomic_write_json(output: Path, document: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(document, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
        os.replace(temp_path, output)
    except Exception:
        try:
            temp_path.unlink()
        except OSError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import an equipment inventory workbook into a canonical JSON snapshot.")
    parser.add_argument("source", help="Path to the source .xlsx workbook.")
    parser.add_argument("--output", default=None, help="Snapshot output path. Defaults to equipment_inventory.local.json at the repository root.")
    args = parser.parse_args(argv)

    result = import_equipment_inventory(args.source, output_path=args.output)
    print(json.dumps(result.to_report(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.published else 1


if __name__ == "__main__":
    raise SystemExit(main())
