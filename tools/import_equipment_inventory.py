"""Offline importer for canonical equipment inventory snapshots."""

from __future__ import annotations

import argparse
import json
import os
import posixpath
import sys
import tempfile
import unicodedata
import zipfile
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping
import xml.etree.ElementTree as ET


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from core.equipment_inventory import (  # noqa: E402
    RECORD_FIELDS,
    SCHEMA_VERSION_V3,
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
    "room_vip": "VIP оборудование",
}
EVIDENCE_COLUMNS = {
    "manufacturer": "Производитель",
    "model": "Модель",
    "controller_record_id": "SmartRoomID контроллера",
}
REQUIRED_SOURCE_COLUMNS = tuple(SOURCE_COLUMNS.values())
OPTIONAL_EVIDENCE_COLUMNS = tuple(EVIDENCE_COLUMNS.values())
SOURCE_XLSX_ENV = "DIAG_INVENTORY_XLSX"
OUTPUT_JSON_ENV = "DIAG_INVENTORY_JSON"
NETWORK_XLSX_ENV = "DIAG_INVENTORY_NETWORK_XLSX"
SOURCE_XLSX_PATH: Path | None = None
OUTPUT_JSON_PATH: Path | None = None
NETWORK_XLSX_PATH: Path | None = None
NETWORK_WORKSHEET = "Устройства"
NETWORK_COLUMNS = {
    "mac_address": "MAC-адрес",
    "switch_ip_address": "IP коммутатора",
    "switch_port": "Порт",
}
REQUIRED_NETWORK_COLUMNS = tuple(NETWORK_COLUMNS.values())

DIAGNOSTIC_MODEL_RULES = (
    ("Huawei TE20", (frozenset({"te", "20"}),)),
    ("Huawei TE40", (frozenset({"te", "40"}),)),
    ("CloudLink Bar 310", (frozenset({"cloudlink", "bar", "310"}),)),
    (
        "Polycom RPG 310",
        (
            frozenset({"rpg", "310"}),
            frozenset({"realpresence", "group", "310"}),
        ),
    ),
    ("Extron IN1804", (frozenset({"in", "1804"}),)),
    ("Aten PE8208AV", (frozenset({"pe", "8208"}),)),
    ("Extron IPL T PCS4i", (frozenset({"ipl", "pcs", "4i"}),)),
    (
        "Biamp Tesira Forte CI",
        (
            frozenset({"tesira", "forte"}),
            frozenset({"tesira", "forté"}),
        ),
    ),
    ("Extron DMP 64 Plus", (frozenset({"dmp", "64"}),)),
)
EXPECTED_KIND_BY_DIAGNOSTIC_MODEL = {
    "Huawei TE20": "video_codec",
    "Huawei TE40": "video_codec",
    "CloudLink Bar 310": "video_codec",
    "Polycom RPG 310": "video_codec",
    "Extron IN1804": "other",
    "Extron IPL T PCS4i": "other",
    "Extron DMP 64 Plus": "other",
    "Biamp Tesira Forte CI": "other",
    "Aten PE8208AV": "other",
}


@dataclass(frozen=True)
class ImportIssue:
    issue_class: str
    code: str
    sheet: str | None = None
    row: int | None = None
    record_id: str | None = None
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "class": self.issue_class,
            "code": self.code,
            "sheet": self.sheet,
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
    network_worksheet: str | None = None
    network_header_row: int | None = None
    network_source_row_count: int | None = None
    distinct_network_mac_count: int | None = None
    enriched_record_count: int | None = None
    empty_connection_row_count: int | None = None
    duplicate_connection_count: int | None = None
    ambiguity_count: int | None = None
    unmatched_network_mac_count: int | None = None

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
            "network_worksheet": self.network_worksheet,
            "network_header_row": self.network_header_row,
            "network_source_row_count": self.network_source_row_count,
            "distinct_network_mac_count": self.distinct_network_mac_count,
            "enriched_record_count": self.enriched_record_count,
            "empty_connection_row_count": self.empty_connection_row_count,
            "duplicate_connection_count": self.duplicate_connection_count,
            "ambiguity_count": self.ambiguity_count,
            "unmatched_network_mac_count": self.unmatched_network_mac_count,
            "fatal_issue_count": len(self.fatal_issues),
            "non_fatal_issue_count": len(self.non_fatal_issues),
            "issues": [issue.to_dict() for issue in self.issues],
        }


class ConverterConfigurationError(ValueError):
    """Safe converter path configuration failure."""


@dataclass(frozen=True)
class ConverterPaths:
    source_xlsx_path: Path
    output_json_path: Path
    network_xlsx_path: Path | None = None


@dataclass(frozen=True)
class NetworkEnrichment:
    records: tuple[EquipmentRecord, ...]
    issues: tuple[ImportIssue, ...]
    distinct_network_mac_count: int
    enriched_record_count: int
    empty_connection_row_count: int
    duplicate_connection_count: int
    ambiguity_count: int
    unmatched_network_mac_count: int


def import_equipment_inventory(
    source_path: str | Path,
    *,
    network_source_path: str | Path | None = None,
    output_path: str | Path | None = None,
    generated_at: str | None = None,
) -> ImportResult:
    source = _resolve_path(source_path)
    network_source = _configured_network_source(network_source_path)
    output = _resolve_path(output_path) if output_path is not None else _resolve_path(default_snapshot_path())
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

    network_layout: WorksheetLayout | None = None
    network_source_rows: list[tuple[int, tuple[Any, ...]]] = []
    enrichment: NetworkEnrichment | None = None
    schema_version = SCHEMA_VERSION
    final_records: tuple[EquipmentRecord, ...] = tuple(records)
    if network_source is not None:
        schema_version = SCHEMA_VERSION_V3
        try:
            network_workbook = _read_workbook(network_source)
        except (OSError, zipfile.BadZipFile, ET.ParseError) as exc:
            issues.append(
                ImportIssue(
                    "fatal",
                    "NETWORK_WORKBOOK_UNREADABLE",
                    description=f"Network workbook could not be read: {type(exc).__name__}",
                )
            )
            return ImportResult(False, output, layout.worksheet, layout.header_row, len(source_rows), 0, None, tuple(issues))
        network_layout = _select_network_layout(network_workbook, issues)
        if network_layout is None:
            return ImportResult(False, output, layout.worksheet, layout.header_row, len(source_rows), 0, None, tuple(issues))
        network_rows = network_workbook["rows_by_sheet"][network_layout.worksheet]
        network_source_rows = [row for row in network_rows if row[0] > network_layout.header_row]
        enrichment = _apply_network_enrichment(final_records, network_layout, network_source_rows)
        issues.extend(enrichment.issues)
        final_records = enrichment.records

    ordered_records = tuple(sorted(final_records, key=lambda record: record.record_id))
    snapshot_id = compute_snapshot_id(ordered_records, schema_version=schema_version)
    document = {
        "schema_version": schema_version,
        "snapshot_id": snapshot_id,
        "generated_at": generated,
        "source_row_count": len(source_rows),
        "records": [record_to_dict(record, schema_version=schema_version) for record in ordered_records],
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

    try:
        _atomic_write_json(output, document)
    except OSError as exc:
        issues.append(
            ImportIssue(
                "fatal",
                "OUTPUT_PUBLICATION_FAILED",
                description=f"Snapshot output could not be published: {type(exc).__name__}",
            )
        )
        return ImportResult(False, output, layout.worksheet, layout.header_row, len(source_rows), 0, None, tuple(issues))
    return ImportResult(
        True,
        output,
        layout.worksheet,
        layout.header_row,
        len(source_rows),
        len(ordered_records),
        snapshot_id,
        tuple(issues),
        network_worksheet=network_layout.worksheet if network_layout is not None else None,
        network_header_row=network_layout.header_row if network_layout is not None else None,
        network_source_row_count=len(network_source_rows) if network_layout is not None else None,
        distinct_network_mac_count=enrichment.distinct_network_mac_count if enrichment is not None else None,
        enriched_record_count=enrichment.enriched_record_count if enrichment is not None else None,
        empty_connection_row_count=enrichment.empty_connection_row_count if enrichment is not None else None,
        duplicate_connection_count=enrichment.duplicate_connection_count if enrichment is not None else None,
        ambiguity_count=enrichment.ambiguity_count if enrichment is not None else None,
        unmatched_network_mac_count=enrichment.unmatched_network_mac_count if enrichment is not None else None,
    )


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
        room_vip, room_vip_issue = _map_room_vip(
            _value(row, header_index, SOURCE_COLUMNS["room_vip"])
        )
        if room_vip_issue is not None:
            issues.append(
                ImportIssue(
                    "data_quality",
                    room_vip_issue,
                    row=row_number,
                    record_id=record_id,
                    description="Room VIP value is unsupported and was represented as null.",
                )
            )

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
        diagnostic_model, diagnostic_issue = _reconcile_diagnostic_model_evidence(
            model,
            source_model,
        )
        if diagnostic_issue is not None:
            issues.append(ImportIssue("data_quality", diagnostic_issue, row=row_number, record_id=record_id, description="Diagnostic model is not mapped by reviewed model evidence."))
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
                room_vip=room_vip,
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
    room_vip_values_by_id: dict[str, list[bool | None]] = {}
    values_by_field: dict[str, dict[str, list[EquipmentRecord]]] = {
        "ip_address": {},
        "mac_address": {},
        "serial_number": {},
    }
    for record in records:
        if record.room_id is not None:
            room_vip_values_by_id.setdefault(record.room_id, []).append(record.room_vip)
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
    for room_id, values in room_vip_values_by_id.items():
        if _aggregate_room_vip_values(values) == "CONFLICT":
            issues.append(
                ImportIssue(
                    "consistency",
                    "ROOM_VIP_CONFLICT",
                    record_id=room_id,
                    description="One room ID has conflicting VIP evidence.",
                )
            )

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


def _select_network_layout(workbook: dict[str, Any], issues: list[ImportIssue]) -> WorksheetLayout | None:
    matching_sheet_count = sum(1 for sheet_name in workbook["sheet_names"] if sheet_name == NETWORK_WORKSHEET)
    if matching_sheet_count == 0:
        issues.append(
            ImportIssue(
                "fatal",
                "NETWORK_WORKSHEET_MISSING",
                sheet=NETWORK_WORKSHEET,
                description="Network workbook does not contain the required worksheet.",
            )
        )
        return None
    if matching_sheet_count > 1:
        issues.append(
            ImportIssue(
                "fatal",
                "NETWORK_WORKSHEET_AMBIGUOUS",
                sheet=NETWORK_WORKSHEET,
                description="Network workbook contains multiple required worksheets.",
            )
        )
        return None

    candidates: list[WorksheetLayout] = []
    for row_number, row in workbook["rows_by_sheet"][NETWORK_WORKSHEET][:50]:
        headers = tuple(normalize_text(value) or "" for value in row)
        if not all(column in headers for column in REQUIRED_NETWORK_COLUMNS):
            continue
        ambiguous_headers = [column for column in REQUIRED_NETWORK_COLUMNS if headers.count(column) > 1]
        if ambiguous_headers:
            issues.append(
                ImportIssue(
                    "fatal",
                    "NETWORK_HEADER_AMBIGUOUS",
                    sheet=NETWORK_WORKSHEET,
                    row=row_number,
                    description="Network worksheet has an ambiguous required header.",
                )
            )
            return None
        candidates.append(WorksheetLayout(NETWORK_WORKSHEET, row_number, headers))

    if not candidates:
        issues.append(
            ImportIssue(
                "fatal",
                "NETWORK_HEADER_MISSING",
                sheet=NETWORK_WORKSHEET,
                description="Network worksheet does not contain all required headers.",
            )
        )
        return None
    if len(candidates) > 1:
        issues.append(
            ImportIssue(
                "fatal",
                "NETWORK_HEADER_ROW_AMBIGUOUS",
                sheet=NETWORK_WORKSHEET,
                description="Network worksheet contains multiple candidate header rows.",
            )
        )
        return None
    return candidates[0]


def _apply_network_enrichment(
    records: tuple[EquipmentRecord, ...],
    layout: WorksheetLayout,
    source_rows: list[tuple[int, tuple[Any, ...]]],
) -> NetworkEnrichment:
    header_index = {header: index for index, header in enumerate(layout.headers)}
    issues: list[ImportIssue] = []
    primary_by_mac: dict[str, list[EquipmentRecord]] = {}
    for record in records:
        if record.mac_address is not None:
            primary_by_mac.setdefault(record.mac_address, []).append(record)

    rows_by_network_mac: dict[str, list[int]] = {}
    candidates_by_mac: dict[str, dict[tuple[str | None, str | None], list[int]]] = {}
    empty_connection_row_count = 0

    for row_number, row in source_rows:
        if _is_empty_row(row):
            continue
        mac_source = _value(row, header_index, NETWORK_COLUMNS["mac_address"])
        mac_address = normalize_mac_address(mac_source)
        if normalize_text(mac_source) is None or mac_address is None:
            issues.append(
                ImportIssue(
                    "data_quality",
                    "INVALID_NETWORK_MAC",
                    sheet=layout.worksheet,
                    row=row_number,
                    description="Network MAC is missing or invalid and cannot participate in reconciliation.",
                )
            )
            continue
        rows_by_network_mac.setdefault(mac_address, []).append(row_number)

        switch_ip_source = _value(row, header_index, NETWORK_COLUMNS["switch_ip_address"])
        switch_ip_text = normalize_text(switch_ip_source)
        switch_ip_address = normalize_ip_address(switch_ip_source)
        invalid_switch_ip = switch_ip_text is not None and switch_ip_address is None
        if invalid_switch_ip:
            issues.append(
                ImportIssue(
                    "data_quality",
                    "INVALID_SWITCH_IP",
                    sheet=layout.worksheet,
                    row=row_number,
                    description="Switch IP is invalid and was represented as null.",
                )
            )

        switch_port = normalize_text(_value(row, header_index, NETWORK_COLUMNS["switch_port"]))
        if switch_ip_address is None and switch_port is None:
            if not invalid_switch_ip:
                empty_connection_row_count += 1
                issues.append(
                    ImportIssue(
                        "data_quality",
                        "EMPTY_SWITCH_CONNECTION",
                        sheet=layout.worksheet,
                        row=row_number,
                        description="Network row has no usable switch IP or port.",
                    )
                )
            continue
        if switch_ip_address is not None and switch_port is None:
            issues.append(
                ImportIssue(
                    "data_quality",
                    "MISSING_SWITCH_PORT",
                    sheet=layout.worksheet,
                    row=row_number,
                    description="Switch port is missing while switch IP is present.",
                )
            )
        if switch_ip_address is None and switch_port is not None and not invalid_switch_ip:
            issues.append(
                ImportIssue(
                    "data_quality",
                    "MISSING_SWITCH_IP",
                    sheet=layout.worksheet,
                    row=row_number,
                    description="Switch IP is missing while switch port is present.",
                )
            )
        candidates_by_mac.setdefault(mac_address, {}).setdefault((switch_ip_address, switch_port), []).append(row_number)

    enrichment_by_record_id: dict[str, tuple[str | None, str | None]] = {}
    duplicate_connection_count = 0
    ambiguity_count = 0
    unmatched_network_mac_count = 0
    all_network_macs = set(rows_by_network_mac)
    for mac_address in sorted(all_network_macs):
        primary_records = primary_by_mac.get(mac_address, [])
        if not primary_records:
            unmatched_network_mac_count += 1
            issues.append(
                ImportIssue(
                    "consistency",
                    "NETWORK_MAC_NOT_IN_INVENTORY",
                    sheet=layout.worksheet,
                    row=rows_by_network_mac[mac_address][0],
                    description="Network MAC is absent from the primary inventory.",
                )
            )
            continue
        candidate_rows = candidates_by_mac.get(mac_address, {})
        if not candidate_rows:
            continue
        if len(primary_records) > 1:
            ambiguity_count += 1
            issues.append(
                ImportIssue(
                    "consistency",
                    "AMBIGUOUS_INVENTORY_MAC_FOR_SWITCH",
                    sheet=layout.worksheet,
                    row=min(row_number for rows in candidate_rows.values() for row_number in rows),
                    record_id=primary_records[0].record_id,
                    description="Multiple primary records share the network MAC.",
                )
            )
            continue
        if len(candidate_rows) == 1:
            (candidate, rows), = candidate_rows.items()
            if len(rows) > 1:
                duplicate_connection_count += 1
                issues.append(
                    ImportIssue(
                        "consistency",
                        "DUPLICATE_SWITCH_CONNECTION_SOURCE",
                        sheet=layout.worksheet,
                        row=rows[0],
                        record_id=primary_records[0].record_id,
                        description="Repeated network rows normalize to one switch connection.",
                    )
                )
            enrichment_by_record_id[primary_records[0].record_id] = candidate
            continue
        ambiguity_count += 1
        issues.append(
            ImportIssue(
                "consistency",
                "AMBIGUOUS_SWITCH_CONNECTION",
                sheet=layout.worksheet,
                row=min(row_number for rows in candidate_rows.values() for row_number in rows),
                record_id=primary_records[0].record_id,
                description="Multiple distinct switch connections exist for one inventory MAC.",
            )
        )

    enriched_records = tuple(
        replace(
            record,
            switch_ip_address=enrichment_by_record_id.get(record.record_id, (None, None))[0],
            switch_port=enrichment_by_record_id.get(record.record_id, (None, None))[1],
        )
        for record in records
    )
    return NetworkEnrichment(
        records=enriched_records,
        issues=tuple(issues),
        distinct_network_mac_count=len(rows_by_network_mac),
        enriched_record_count=len(enrichment_by_record_id),
        empty_connection_row_count=empty_connection_row_count,
        duplicate_connection_count=duplicate_connection_count,
        ambiguity_count=ambiguity_count,
        unmatched_network_mac_count=unmatched_network_mac_count,
    )


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
            if target.startswith("/"):
                target = target.lstrip("/")
            elif not target.startswith("xl/"):
                target = posixpath.normpath(posixpath.join("xl", target))
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


def _map_room_vip(value: Any) -> tuple[bool | None, str | None]:
    if value is None:
        return None, None
    if isinstance(value, bool):
        return value, None
    text = normalize_text(value)
    if text is None:
        return None, None
    folded = text.casefold()
    if folded == "истина":
        return True, None
    if folded == "ложь":
        return False, None
    return None, "INVALID_ROOM_VIP"


def _aggregate_room_vip_values(values: list[bool | None] | tuple[bool | None, ...]) -> str:
    if not values:
        return "UNRESOLVED"
    has_true = any(value is True for value in values)
    has_false = any(value is False for value in values)
    if has_true and has_false:
        return "CONFLICT"
    if has_true:
        return "VIP_TRUE"
    if has_false:
        return "VIP_FALSE"
    return "NO_DATA"


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


def _evaluate_diagnostic_model_evidence(value: Any) -> frozenset[str]:
    components = _extract_model_components(_normalize_model_evidence(value))
    return frozenset(_evaluate_diagnostic_model_rules(components))


def _reconcile_diagnostic_model_evidence(
    model_value: Any,
    name_value: Any,
) -> tuple[str | None, str | None]:
    matches = (
        _evaluate_diagnostic_model_evidence(model_value)
        | _evaluate_diagnostic_model_evidence(name_value)
    )
    if not matches:
        return None, "UNMAPPED_DIAGNOSTIC_MODEL"
    if len(matches) > 1:
        return None, "AMBIGUOUS_DIAGNOSTIC_MODEL"
    return next(iter(matches)), None


def _normalize_model_evidence(value: Any) -> str | None:
    text = normalize_text(value)
    if text is None:
        return None
    folded = unicodedata.normalize("NFC", text).strip().casefold()
    return folded or None


def _extract_model_components(value: str | None) -> frozenset[str]:
    if value is None:
        return frozenset()

    components: set[str] = set()
    for chunk in _alphanumeric_chunks(value):
        runs = _split_alphanumeric_runs(chunk)
        components.update(run for _kind, run in runs)
        for first, second in zip(runs, runs[1:]):
            if first[0] == "decimal" and second[0] == "alpha":
                components.add(first[1] + second[1])
    return frozenset(components)


def _alphanumeric_chunks(value: str) -> tuple[str, ...]:
    chunks: list[str] = []
    current: list[str] = []
    for character in value:
        if character.isalnum():
            current.append(character)
            continue
        if current:
            chunks.append("".join(current))
            current = []
    if current:
        chunks.append("".join(current))
    return tuple(chunks)


def _split_alphanumeric_runs(chunk: str) -> tuple[tuple[str, str], ...]:
    runs: list[tuple[str, str]] = []
    current_kind: str | None = None
    current: list[str] = []
    for character in chunk:
        if character.isalpha():
            kind = "alpha"
        elif character.isdecimal():
            kind = "decimal"
        else:
            kind = "separator"

        if kind == "separator":
            if current_kind is not None:
                runs.append((current_kind, "".join(current)))
                current_kind = None
                current = []
            continue
        if current_kind is None or current_kind == kind:
            current.append(character)
            current_kind = kind
            continue
        runs.append((current_kind, "".join(current)))
        current = [character]
        current_kind = kind
    if current_kind is not None:
        runs.append((current_kind, "".join(current)))
    return tuple(runs)


def _evaluate_diagnostic_model_rules(components: frozenset[str]) -> tuple[str, ...]:
    matches: list[str] = []
    for diagnostic_model, alternatives in DIAGNOSTIC_MODEL_RULES:
        if any(alternative.issubset(components) for alternative in alternatives):
            matches.append(diagnostic_model)
    return tuple(matches)


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


def _resolve_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve(strict=False)


def _configured_network_source(value: str | Path | None) -> Path | None:
    if value not in (None, ""):
        return _resolve_path(value)
    env_value = os.environ.get(NETWORK_XLSX_ENV)
    if env_value not in (None, ""):
        return _resolve_path(env_value)
    if NETWORK_XLSX_PATH is not None:
        return _resolve_path(NETWORK_XLSX_PATH)
    return None


def resolve_converter_paths(
    *,
    source_override: str | Path | None = None,
    output_override: str | Path | None = None,
    network_override: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> ConverterPaths:
    values = os.environ if env is None else env
    source_value = source_override or values.get(SOURCE_XLSX_ENV)
    if source_value in (None, ""):
        raise ConverterConfigurationError(
            "Source workbook path is not configured. Use --source or DIAG_INVENTORY_XLSX."
        )
    output_value = output_override or values.get(OUTPUT_JSON_ENV) or default_snapshot_path()
    network_value = network_override or values.get(NETWORK_XLSX_ENV)
    network_path = _resolve_path(network_value) if network_value not in (None, "") else NETWORK_XLSX_PATH
    return ConverterPaths(
        source_xlsx_path=_resolve_path(source_value),
        output_json_path=_resolve_path(output_value),
        network_xlsx_path=_resolve_path(network_path) if network_path is not None else None,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import an equipment inventory workbook into a canonical JSON snapshot.")
    parser.add_argument("source", nargs="?", help="Path to the source .xlsx workbook.")
    parser.add_argument("--output", default=None, help="Snapshot output path. Defaults to equipment_inventory.local.json at the repository root.")
    parser.add_argument("--network-source", default=None, help="Optional network connection .xlsx workbook for schema-v3 enrichment.")
    args = parser.parse_args(argv)

    global SOURCE_XLSX_PATH, OUTPUT_JSON_PATH, NETWORK_XLSX_PATH
    try:
        paths = resolve_converter_paths(
            source_override=args.source,
            output_override=args.output,
            network_override=args.network_source,
        )
    except ConverterConfigurationError as exc:
        print(json.dumps({"published": False, "error": str(exc)}, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    SOURCE_XLSX_PATH = paths.source_xlsx_path
    OUTPUT_JSON_PATH = paths.output_json_path
    NETWORK_XLSX_PATH = paths.network_xlsx_path
    result = import_equipment_inventory(
        SOURCE_XLSX_PATH,
        network_source_path=NETWORK_XLSX_PATH,
        output_path=OUTPUT_JSON_PATH,
    )
    print(json.dumps(result.to_report(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.published else 1


if __name__ == "__main__":
    raise SystemExit(main())
