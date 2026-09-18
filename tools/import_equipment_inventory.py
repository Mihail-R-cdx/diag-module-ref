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
from enum import Enum
from pathlib import Path
from typing import Any, Mapping
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


class WorkbookReadError(Exception):
    """Raised when an XLSX package cannot be read as importer workbook input."""


class ConverterOperation(str, Enum):
    PRIMARY_SOURCE_PREFLIGHT = "PRIMARY_SOURCE_PREFLIGHT"
    NETWORK_SOURCE_PREFLIGHT = "NETWORK_SOURCE_PREFLIGHT"
    COMBINED_PREFLIGHT = "COMBINED_PREFLIGHT"
    CONVERSION = "CONVERSION"


class ConverterStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    SUCCEEDED_WITH_WARNINGS = "SUCCEEDED_WITH_WARNINGS"
    FAILED = "FAILED"


class ConverterStage(str, Enum):
    CONFIGURATION = "CONFIGURATION"
    SOURCE_PREFLIGHT = "SOURCE_PREFLIGHT"
    WORKBOOK_READ = "WORKBOOK_READ"
    LAYOUT_DISCOVERY = "LAYOUT_DISCOVERY"
    ROW_MAPPING = "ROW_MAPPING"
    SOURCE_VALIDATION = "SOURCE_VALIDATION"
    CROSS_SOURCE_RECONCILIATION = "CROSS_SOURCE_RECONCILIATION"
    CANDIDATE_VALIDATION = "CANDIDATE_VALIDATION"
    PUBLICATION = "PUBLICATION"
    COMPLETE = "COMPLETE"
    INTERNAL = "INTERNAL"


class SourceFileRole(str, Enum):
    PRIMARY = "PRIMARY"
    NETWORK = "NETWORK"
    OUTPUT = "OUTPUT"

SOURCE_COLUMNS = {
    "record_id": "SmartRoomID",
    "room_id": "ID комнаты",
    "room_name": "Название комнаты",
    "room_address": "Адрес комнаты",
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


def _diagnostic_model_rule(
    required_components: set[str], *, forbidden_components: set[str] | None = None
) -> tuple[frozenset[str], frozenset[str]]:
    """Build a complete component rule without introducing match priority."""

    return frozenset(required_components), frozenset(forbidden_components or ())


DIAGNOSTIC_MODEL_RULES = (
    ("Huawei TE20", (_diagnostic_model_rule({"te", "20"}),)),
    ("Huawei TE40", (_diagnostic_model_rule({"te", "40"}),)),
    ("Huawei TE50", (_diagnostic_model_rule({"te", "50"}),)),
    ("CloudLink Bar 310", (_diagnostic_model_rule({"cloudlink", "bar", "310"}),)),
    ("CloudLink Box 310", (_diagnostic_model_rule({"cloudlink", "box", "310"}),)),
    (
        "Polycom RPG 310",
        (
            _diagnostic_model_rule({"rpg", "310"}),
            _diagnostic_model_rule({"realpresence", "group", "310"}),
        ),
    ),
    ("Extron IN1804", (_diagnostic_model_rule({"in", "1804"}),)),
    ("Extron IN1808", (_diagnostic_model_rule({"in", "1808"}),)),
    ("Extron IN1608 xi", (_diagnostic_model_rule({"in", "1608", "xi"}),)),
    (
        "Extron DTP CrossPoint 84",
        (_diagnostic_model_rule({"dtp", "crosspoint", "84"}, forbidden_components={"4k"}),),
    ),
    ("Extron DTP CrossPoint 82 4K", (_diagnostic_model_rule({"dtp", "crosspoint", "82", "4k"}),)),
    ("Extron DTP CrossPoint 84 4K", (_diagnostic_model_rule({"dtp", "crosspoint", "84", "4k"}),)),
    ("Extron DTP CrossPoint 86 4K", (_diagnostic_model_rule({"dtp", "crosspoint", "86", "4k"}),)),
    ("Extron DTP CrossPoint 108 4K", (_diagnostic_model_rule({"dtp", "crosspoint", "108", "4k"}),)),
    (
        "Extron XTP CrossPoint 1600",
        (_diagnostic_model_rule({"xtp", "crosspoint", "1600"}, forbidden_components={"ii"}),),
    ),
    (
        "Extron XTP CrossPoint 3200",
        (_diagnostic_model_rule({"xtp", "crosspoint", "3200"}, forbidden_components={"ii"}),),
    ),
    ("Extron XTP II CrossPoint 1600", (_diagnostic_model_rule({"xtp", "ii", "crosspoint", "1600"}),)),
    ("Extron XTP II CrossPoint 3200", (_diagnostic_model_rule({"xtp", "ii", "crosspoint", "3200"}),)),
    ("Extron XTP II CrossPoint 6400", (_diagnostic_model_rule({"xtp", "ii", "crosspoint", "6400"}),)),
    ("Aten PE8208AV", (_diagnostic_model_rule({"pe", "8208"}),)),
    ("Extron IPL T PCS4i", (_diagnostic_model_rule({"ipl", "pcs", "4i"}),)),
    (
        "Biamp Tesira Forte CI",
        (
            _diagnostic_model_rule({"tesira", "forte"}),
            _diagnostic_model_rule({"tesira", "forté"}),
        ),
    ),
    ("Extron DMP 64 Plus", (_diagnostic_model_rule({"dmp", "64"}),)),
)
EXPECTED_KIND_BY_DIAGNOSTIC_MODEL = {
    "Huawei TE20": "video_codec",
    "Huawei TE40": "video_codec",
    "Huawei TE50": "video_codec",
    "CloudLink Bar 310": "video_codec",
    "CloudLink Box 310": "video_codec",
    "Polycom RPG 310": "video_codec",
    "Extron IN1804": "other",
    "Extron IN1808": "other",
    "Extron IN1608 xi": "other",
    "Extron DTP CrossPoint 84": "other",
    "Extron DTP CrossPoint 82 4K": "other",
    "Extron DTP CrossPoint 84 4K": "other",
    "Extron DTP CrossPoint 86 4K": "other",
    "Extron DTP CrossPoint 108 4K": "other",
    "Extron XTP CrossPoint 1600": "other",
    "Extron XTP CrossPoint 3200": "other",
    "Extron XTP II CrossPoint 1600": "other",
    "Extron XTP II CrossPoint 3200": "other",
    "Extron XTP II CrossPoint 6400": "other",
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
    stage: str | None = None
    source_file_role: str | None = None
    source_column: str | None = None
    related_row: int | None = None
    details: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "class": self.issue_class,
            "code": self.code,
            "sheet": self.sheet,
            "row": self.row,
            "record_id": self.record_id,
            "description": self.description,
            "stage": self.stage or ConverterStage.SOURCE_VALIDATION.value,
            "source_file_role": self.source_file_role,
            "source_column": self.source_column,
            "related_row": self.related_row,
            "details": _flat_json_details(self.details),
        }


@dataclass(frozen=True)
class WorksheetLayout:
    worksheet: str
    header_row: int
    headers: tuple[str, ...]


@dataclass(frozen=True)
class ImportResult:
    published: bool
    output_path: Path | None
    worksheet: str | None
    header_row: int | None
    source_row_count: int
    record_count: int
    snapshot_id: str | None
    issues: tuple[ImportIssue, ...]
    operation: str = ConverterOperation.CONVERSION.value
    stage_reached: str = ConverterStage.COMPLETE.value
    schema_version: int | None = None
    primary_source_path: Path | None = None
    network_source_path: Path | None = None
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

    @property
    def data_quality_issues(self) -> tuple[ImportIssue, ...]:
        return tuple(issue for issue in self.issues if issue.issue_class == "data_quality")

    @property
    def consistency_issues(self) -> tuple[ImportIssue, ...]:
        return tuple(issue for issue in self.issues if issue.issue_class == "consistency")

    @property
    def status(self) -> str:
        if self.fatal_issues:
            return ConverterStatus.FAILED.value
        if self.non_fatal_issues:
            return ConverterStatus.SUCCEEDED_WITH_WARNINGS.value
        return ConverterStatus.SUCCEEDED.value

    def to_report(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "status": self.status,
            "stage_reached": self.stage_reached,
            "schema_version": self.schema_version,
            "source_files": {
                "primary": str(self.primary_source_path) if self.primary_source_path is not None else None,
                "network": str(self.network_source_path) if self.network_source_path is not None else None,
            },
            "published": self.published,
            "output_path": str(self.output_path) if self.output_path is not None else None,
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
            "data_quality_issue_count": len(self.data_quality_issues),
            "consistency_issue_count": len(self.consistency_issues),
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
class OutputFileState:
    path: Path
    exists: bool
    size: int | None = None
    mtime_ns: int | None = None
    file_identity: tuple[int, int] | None = None


@dataclass(frozen=True)
class PublicationPrecondition:
    output_path: Path
    confirmed_state: OutputFileState


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


def capture_output_precondition(output_path: str | Path) -> PublicationPrecondition:
    resolved = _resolve_path(output_path)
    return PublicationPrecondition(output_path=resolved, confirmed_state=_capture_output_state(resolved))


def import_equipment_inventory(
    source_path: str | Path,
    *,
    network_source_path: str | Path | None = None,
    output_path: str | Path | None = None,
    generated_at: str | None = None,
    publication_precondition: PublicationPrecondition | None = None,
) -> ImportResult:
    network_source = _configured_network_source(network_source_path)
    output = _resolve_path(output_path) if output_path is not None else _resolve_path(default_snapshot_path())
    generated = generated_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return _run_inventory_operation(
        operation=ConverterOperation.CONVERSION.value,
        source=_resolve_path(source_path),
        network_source=network_source,
        output=output,
        generated_at=generated,
        publish=True,
        publication_precondition=publication_precondition,
    )


def preflight_primary_source(source_path: str | Path) -> ImportResult:
    return _run_inventory_operation(
        operation=ConverterOperation.PRIMARY_SOURCE_PREFLIGHT.value,
        source=_resolve_path(source_path),
        network_source=None,
        output=None,
        generated_at=None,
        publish=False,
        publication_precondition=None,
        validate_candidate=False,
    )


def preflight_network_source(network_source_path: str | Path) -> ImportResult:
    network_source = _resolve_path(network_source_path)
    issues: list[ImportIssue] = []
    try:
        workbook = _read_workbook(network_source)
    except WorkbookReadError as exc:
        return _make_result(
            operation=ConverterOperation.NETWORK_SOURCE_PREFLIGHT.value,
            stage_reached=ConverterStage.WORKBOOK_READ.value,
            published=False,
            output_path=None,
            primary_source_path=None,
            network_source_path=network_source,
            worksheet=None,
            header_row=None,
            source_row_count=0,
            record_count=0,
            snapshot_id=None,
            issues=(
                ImportIssue(
                    "fatal",
                    "NETWORK_WORKBOOK_UNREADABLE",
                    description=f"Network workbook could not be read: {type(exc).__name__}",
                    stage=ConverterStage.WORKBOOK_READ.value,
                    source_file_role=SourceFileRole.NETWORK.value,
                ),
            ),
        )

    network_layout = _select_network_layout(workbook, issues)
    issues = list(_with_issue_defaults(issues, ConverterStage.LAYOUT_DISCOVERY.value, SourceFileRole.NETWORK.value))
    if network_layout is None:
        return _make_result(
            operation=ConverterOperation.NETWORK_SOURCE_PREFLIGHT.value,
            stage_reached=ConverterStage.LAYOUT_DISCOVERY.value,
            published=False,
            output_path=None,
            primary_source_path=None,
            network_source_path=network_source,
            worksheet=None,
            header_row=None,
            source_row_count=0,
            record_count=0,
            snapshot_id=None,
            issues=tuple(issues),
        )

    network_rows = workbook["rows_by_sheet"][network_layout.worksheet]
    network_source_rows = [row for row in network_rows if row[0] > network_layout.header_row]
    enrichment = _apply_network_enrichment((), network_layout, network_source_rows)
    network_issues = tuple(issue for issue in enrichment.issues if issue.code != "NETWORK_MAC_NOT_IN_INVENTORY")
    issues.extend(_with_issue_defaults(network_issues, ConverterStage.SOURCE_VALIDATION.value, SourceFileRole.NETWORK.value))
    return _make_result(
        operation=ConverterOperation.NETWORK_SOURCE_PREFLIGHT.value,
        stage_reached=ConverterStage.COMPLETE.value,
        published=False,
        output_path=None,
        primary_source_path=None,
        network_source_path=network_source,
        worksheet=None,
        header_row=None,
        source_row_count=0,
        record_count=0,
        snapshot_id=None,
        issues=tuple(issues),
        network_worksheet=network_layout.worksheet,
        network_header_row=network_layout.header_row,
        network_source_row_count=len(network_source_rows),
        distinct_network_mac_count=enrichment.distinct_network_mac_count,
        enriched_record_count=0,
        empty_connection_row_count=enrichment.empty_connection_row_count,
        duplicate_connection_count=enrichment.duplicate_connection_count,
        ambiguity_count=enrichment.ambiguity_count,
        unmatched_network_mac_count=0,
    )


def preflight_combined_sources(
    source_path: str | Path,
    network_source_path: str | Path,
) -> ImportResult:
    return _run_inventory_operation(
        operation=ConverterOperation.COMBINED_PREFLIGHT.value,
        source=_resolve_path(source_path),
        network_source=_resolve_path(network_source_path),
        output=None,
        generated_at=None,
        publish=False,
        publication_precondition=None,
        validate_candidate=True,
    )


def _run_inventory_operation(
    *,
    operation: str,
    source: Path,
    network_source: Path | None,
    output: Path | None,
    generated_at: str | None,
    publish: bool,
    publication_precondition: PublicationPrecondition | None,
    validate_candidate: bool = True,
) -> ImportResult:
    issues: list[ImportIssue] = []
    if publish and output is not None and (output == source or output == network_source):
        return _make_result(
            operation=operation,
            stage_reached=ConverterStage.CONFIGURATION.value,
            published=False,
            output_path=output,
            primary_source_path=source,
            network_source_path=network_source,
            worksheet=None,
            header_row=None,
            source_row_count=0,
            record_count=0,
            snapshot_id=None,
            issues=(
                ImportIssue(
                    "fatal",
                    "OUTPUT_PATH_CONFLICTS_WITH_SOURCE",
                    description="Output path must not match either source workbook path.",
                    stage=ConverterStage.CONFIGURATION.value,
                    source_file_role=SourceFileRole.OUTPUT.value,
                ),
            ),
        )
    try:
        workbook = _read_workbook(source)
    except WorkbookReadError as exc:
        return _make_result(
            operation=operation,
            stage_reached=ConverterStage.WORKBOOK_READ.value,
            published=False,
            output_path=output,
            primary_source_path=source,
            network_source_path=network_source,
            worksheet=None,
            header_row=None,
            source_row_count=0,
            record_count=0,
            snapshot_id=None,
            issues=(
                ImportIssue(
                    "fatal",
                    "WORKBOOK_UNREADABLE",
                    description=f"Workbook could not be read: {type(exc).__name__}",
                    stage=ConverterStage.WORKBOOK_READ.value,
                    source_file_role=SourceFileRole.PRIMARY.value,
                ),
            ),
        )

    layout = _select_layout(workbook, issues)
    issues = list(_with_issue_defaults(issues, ConverterStage.LAYOUT_DISCOVERY.value, SourceFileRole.PRIMARY.value))
    if layout is None:
        return _make_result(
            operation=operation,
            stage_reached=ConverterStage.LAYOUT_DISCOVERY.value,
            published=False,
            output_path=output,
            primary_source_path=source,
            network_source_path=network_source,
            worksheet=None,
            header_row=None,
            source_row_count=0,
            record_count=0,
            snapshot_id=None,
            issues=tuple(issues),
        )

    rows = workbook["rows_by_sheet"][layout.worksheet]
    source_rows = [row for row in rows if row[0] > layout.header_row]
    records, row_issues = _build_records(layout, source_rows)
    issues.extend(_with_issue_defaults(row_issues, ConverterStage.ROW_MAPPING.value, SourceFileRole.PRIMARY.value))
    issues.extend(_with_issue_defaults(_detect_cross_row_issues(records, source_rows, layout), ConverterStage.SOURCE_VALIDATION.value, SourceFileRole.PRIMARY.value))

    if any(issue.issue_class == "fatal" for issue in issues):
        return _make_result(
            operation=operation,
            stage_reached=ConverterStage.SOURCE_VALIDATION.value,
            published=False,
            output_path=output,
            primary_source_path=source,
            network_source_path=network_source,
            worksheet=layout.worksheet,
            header_row=layout.header_row,
            source_row_count=len(source_rows),
            record_count=0,
            snapshot_id=None,
            issues=tuple(issues),
        )

    if operation == ConverterOperation.PRIMARY_SOURCE_PREFLIGHT.value and network_source is None:
        return _make_result(
            operation=operation,
            stage_reached=ConverterStage.COMPLETE.value,
            published=False,
            output_path=None,
            primary_source_path=source,
            network_source_path=None,
            worksheet=layout.worksheet,
            header_row=layout.header_row,
            source_row_count=len(source_rows),
            record_count=len(records),
            snapshot_id=None,
            issues=tuple(issues),
        )

    network_layout: WorksheetLayout | None = None
    network_source_rows: list[tuple[int, tuple[Any, ...]]] = []
    enrichment: NetworkEnrichment | None = None
    schema_version = SCHEMA_VERSION
    final_records: tuple[EquipmentRecord, ...] = tuple(records)
    if network_source is not None:
        try:
            network_workbook = _read_workbook(network_source)
        except WorkbookReadError as exc:
            issues.append(
                ImportIssue(
                    "fatal",
                    "NETWORK_WORKBOOK_UNREADABLE",
                    description=f"Network workbook could not be read: {type(exc).__name__}",
                    stage=ConverterStage.WORKBOOK_READ.value,
                    source_file_role=SourceFileRole.NETWORK.value,
                )
            )
            return _make_result(
                operation=operation,
                stage_reached=ConverterStage.WORKBOOK_READ.value,
                published=False,
                output_path=output,
                primary_source_path=source,
                network_source_path=network_source,
                worksheet=layout.worksheet,
                header_row=layout.header_row,
                source_row_count=len(source_rows),
                record_count=0,
                snapshot_id=None,
                issues=tuple(issues),
            )
        network_layout = _select_network_layout(network_workbook, issues)
        issues = list(_with_issue_defaults(issues, ConverterStage.LAYOUT_DISCOVERY.value, SourceFileRole.NETWORK.value))
        if network_layout is None:
            return _make_result(
                operation=operation,
                stage_reached=ConverterStage.LAYOUT_DISCOVERY.value,
                published=False,
                output_path=output,
                primary_source_path=source,
                network_source_path=network_source,
                worksheet=layout.worksheet,
                header_row=layout.header_row,
                source_row_count=len(source_rows),
                record_count=0,
                snapshot_id=None,
                issues=tuple(issues),
            )
        network_rows = network_workbook["rows_by_sheet"][network_layout.worksheet]
        network_source_rows = [row for row in network_rows if row[0] > network_layout.header_row]
        enrichment = _apply_network_enrichment(final_records, network_layout, network_source_rows)
        issues.extend(_with_issue_defaults(enrichment.issues, ConverterStage.CROSS_SOURCE_RECONCILIATION.value, SourceFileRole.NETWORK.value))
        final_records = enrichment.records

    ordered_records = tuple(sorted(final_records, key=lambda record: record.record_id))
    snapshot_id = compute_snapshot_id(ordered_records, schema_version=schema_version)
    document = {
        "schema_version": schema_version,
        "snapshot_id": snapshot_id,
        "generated_at": generated_at,
        "source_row_count": len(source_rows),
        "records": [record_to_dict(record, schema_version=schema_version) for record in ordered_records],
    }
    if generated_at is None:
        document.pop("generated_at")
    if validate_candidate:
        try:
            inventory_from_document(document)
        except Exception as exc:
            issues.append(
                ImportIssue(
                    "fatal",
                    "CANDIDATE_SNAPSHOT_INVALID",
                    description=f"Candidate canonical snapshot failed validation: {type(exc).__name__}",
                    stage=ConverterStage.CANDIDATE_VALIDATION.value,
                )
            )
            return _candidate_result(
                operation=operation,
                stage_reached=ConverterStage.CANDIDATE_VALIDATION.value,
                published=False,
                output_path=output,
                primary_source_path=source,
                network_source_path=network_source,
                layout=layout,
                source_row_count=len(source_rows),
                ordered_records=ordered_records,
                snapshot_id=snapshot_id,
                issues=tuple(issues),
                schema_version=schema_version,
                network_layout=network_layout,
                network_source_rows=network_source_rows,
                enrichment=enrichment,
            )

    if not publish:
        return _candidate_result(
            operation=operation,
            stage_reached=ConverterStage.COMPLETE.value,
            published=False,
            output_path=None,
            primary_source_path=source,
            network_source_path=network_source,
            layout=layout,
            source_row_count=len(source_rows),
            ordered_records=ordered_records,
            snapshot_id=snapshot_id if validate_candidate else None,
            issues=tuple(issues),
            schema_version=schema_version if validate_candidate else None,
            network_layout=network_layout,
            network_source_rows=network_source_rows,
            enrichment=enrichment,
        )

    assert output is not None
    try:
        _atomic_write_json(output, document, publication_precondition=publication_precondition)
    except PublicationPreconditionError as exc:
        issues.append(exc.issue)
        return _candidate_result(
            operation=operation,
            stage_reached=ConverterStage.PUBLICATION.value,
            published=False,
            output_path=output,
            primary_source_path=source,
            network_source_path=network_source,
            layout=layout,
            source_row_count=len(source_rows),
            ordered_records=ordered_records,
            snapshot_id=snapshot_id,
            issues=tuple(issues),
            schema_version=schema_version,
            network_layout=network_layout,
            network_source_rows=network_source_rows,
            enrichment=enrichment,
        )
    except OSError as exc:
        issues.append(
            ImportIssue(
                "fatal",
                "OUTPUT_PUBLICATION_FAILED",
                description=f"Snapshot output could not be published: {type(exc).__name__}",
                stage=ConverterStage.PUBLICATION.value,
                source_file_role=SourceFileRole.OUTPUT.value,
            )
        )
        return _candidate_result(
            operation=operation,
            stage_reached=ConverterStage.PUBLICATION.value,
            published=False,
            output_path=output,
            primary_source_path=source,
            network_source_path=network_source,
            layout=layout,
            source_row_count=len(source_rows),
            ordered_records=ordered_records,
            snapshot_id=snapshot_id,
            issues=tuple(issues),
            schema_version=schema_version,
            network_layout=network_layout,
            network_source_rows=network_source_rows,
            enrichment=enrichment,
        )
    return _candidate_result(
        operation=operation,
        stage_reached=ConverterStage.COMPLETE.value,
        published=True,
        output_path=output,
        primary_source_path=source,
        network_source_path=network_source,
        layout=layout,
        source_row_count=len(source_rows),
        ordered_records=ordered_records,
        snapshot_id=snapshot_id,
        issues=tuple(issues),
        schema_version=schema_version,
        network_layout=network_layout,
        network_source_rows=network_source_rows,
        enrichment=enrichment,
    )


def _make_result(
    *,
    operation: str,
    stage_reached: str,
    published: bool,
    output_path: Path | None,
    primary_source_path: Path | None,
    network_source_path: Path | None,
    worksheet: str | None,
    header_row: int | None,
    source_row_count: int,
    record_count: int,
    snapshot_id: str | None,
    issues: tuple[ImportIssue, ...],
    schema_version: int | None = None,
    network_worksheet: str | None = None,
    network_header_row: int | None = None,
    network_source_row_count: int | None = None,
    distinct_network_mac_count: int | None = None,
    enriched_record_count: int | None = None,
    empty_connection_row_count: int | None = None,
    duplicate_connection_count: int | None = None,
    ambiguity_count: int | None = None,
    unmatched_network_mac_count: int | None = None,
) -> ImportResult:
    if any(issue.issue_class == "fatal" for issue in issues) and stage_reached == ConverterStage.COMPLETE.value:
        stage_reached = ConverterStage.INTERNAL.value
    return ImportResult(
        published,
        output_path,
        worksheet,
        header_row,
        source_row_count,
        record_count,
        snapshot_id,
        issues,
        operation=operation,
        stage_reached=stage_reached,
        schema_version=schema_version,
        primary_source_path=primary_source_path,
        network_source_path=network_source_path,
        network_worksheet=network_worksheet,
        network_header_row=network_header_row,
        network_source_row_count=network_source_row_count,
        distinct_network_mac_count=distinct_network_mac_count,
        enriched_record_count=enriched_record_count,
        empty_connection_row_count=empty_connection_row_count,
        duplicate_connection_count=duplicate_connection_count,
        ambiguity_count=ambiguity_count,
        unmatched_network_mac_count=unmatched_network_mac_count,
    )


def _candidate_result(
    *,
    operation: str,
    stage_reached: str,
    published: bool,
    output_path: Path | None,
    primary_source_path: Path,
    network_source_path: Path | None,
    layout: WorksheetLayout,
    source_row_count: int,
    ordered_records: tuple[EquipmentRecord, ...],
    snapshot_id: str | None,
    issues: tuple[ImportIssue, ...],
    schema_version: int | None,
    network_layout: WorksheetLayout | None,
    network_source_rows: list[tuple[int, tuple[Any, ...]]],
    enrichment: NetworkEnrichment | None,
) -> ImportResult:
    return _make_result(
        operation=operation,
        stage_reached=stage_reached,
        published=published,
        output_path=output_path,
        primary_source_path=primary_source_path,
        network_source_path=network_source_path,
        worksheet=layout.worksheet,
        header_row=layout.header_row,
        source_row_count=source_row_count,
        record_count=len(ordered_records),
        snapshot_id=snapshot_id,
        issues=issues,
        schema_version=schema_version,
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


def _with_issue_defaults(
    issues: tuple[ImportIssue, ...] | list[ImportIssue],
    stage: str,
    role: str | None,
) -> tuple[ImportIssue, ...]:
    return tuple(
        replace(
            issue,
            stage=issue.stage or stage,
            source_file_role=issue.source_file_role or role,
        )
        for issue in issues
    )


def _flat_json_details(details: Mapping[str, Any] | None) -> dict[str, Any]:
    if not details:
        return {}
    flattened: dict[str, Any] = {}
    for key, value in details.items():
        text_key = str(key)
        if isinstance(value, (str, int, float, bool)) or value is None:
            flattened[text_key] = value
        elif isinstance(value, (list, tuple)):
            flattened[text_key] = [
                item for item in value
                if isinstance(item, (str, int, float, bool)) or item is None
            ]
        else:
            flattened[text_key] = str(value)
    return flattened


class PublicationPreconditionError(Exception):
    def __init__(self, issue: ImportIssue):
        super().__init__(issue.code)
        self.issue = issue


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
        room_address = normalize_text(_value(row, header_index, SOURCE_COLUMNS["room_address"]))
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
                room_address=room_address,
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
                room_ids_by_name.setdefault(record.room_name, set()).add(record.room_id)
            records_by_room_kind.setdefault((record.room_id, record.device_kind), []).append(record)
        for field in values_by_field:
            value = getattr(record, field)
            if value is not None:
                values_by_field[field].setdefault(value, []).append(record)

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
            if not all(column in headers for column in REQUIRED_SOURCE_COLUMNS):
                continue
            if any(headers.count(column) > 1 for column in REQUIRED_SOURCE_COLUMNS):
                issues.append(
                    ImportIssue(
                        "fatal",
                        "SOURCE_STRUCTURE_AMBIGUOUS",
                        sheet=sheet_name,
                        row=row_number,
                        description="Primary worksheet has an ambiguous required header.",
                    )
                )
                return None
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
        candidate_rows = candidates_by_mac.get(mac_address, {})
        primary_records = primary_by_mac.get(mac_address, [])
        issue_record_id = primary_records[0].record_id if len(primary_records) == 1 else None
        candidate_issue_row = min(
            (row_number for rows in candidate_rows.values() for row_number in rows),
            default=rows_by_network_mac[mac_address][0],
        )

        for candidate, rows in sorted(candidate_rows.items(), key=lambda item: (item[0][0] or "", item[0][1] or "")):
            if len(rows) > 1:
                duplicate_connection_count += 1
                issues.append(
                    ImportIssue(
                        "consistency",
                        "DUPLICATE_SWITCH_CONNECTION_SOURCE",
                        sheet=layout.worksheet,
                        row=rows[0],
                        record_id=issue_record_id,
                        description="Repeated network rows normalize to one switch connection.",
                    )
                )

        has_source_ambiguity = len(candidate_rows) > 1
        if has_source_ambiguity:
            ambiguity_count += 1
            issues.append(
                ImportIssue(
                    "consistency",
                    "AMBIGUOUS_SWITCH_CONNECTION",
                    sheet=layout.worksheet,
                    row=candidate_issue_row,
                    record_id=issue_record_id,
                    description="Multiple distinct switch connections exist for one inventory MAC.",
                )
            )

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
        if len(primary_records) > 1:
            ambiguity_count += 1
            issues.append(
                ImportIssue(
                    "consistency",
                    "AMBIGUOUS_INVENTORY_MAC_FOR_SWITCH",
                    sheet=layout.worksheet,
                    row=candidate_issue_row,
                    record_id=primary_records[0].record_id,
                    description="Multiple primary records share the network MAC.",
                )
            )
            continue

        if len(candidate_rows) == 1 and not has_source_ambiguity:
            candidate = next(iter(candidate_rows))
            enrichment_by_record_id[primary_records[0].record_id] = candidate

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
    try:
        return _read_workbook_package(path)
    except (OSError, zipfile.BadZipFile, ET.ParseError, KeyError, IndexError, ValueError) as exc:
        raise WorkbookReadError(type(exc).__name__) from exc


def _read_workbook_package(path: Path) -> dict[str, Any]:
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
        if any(_diagnostic_model_rule_matches(rule, components) for rule in alternatives):
            matches.append(diagnostic_model)
    return tuple(matches)


def _diagnostic_model_rule_matches(
    rule: tuple[frozenset[str], frozenset[str]], components: frozenset[str]
) -> bool:
    required, forbidden = rule
    return required.issubset(components) and not forbidden.intersection(components)


def _atomic_write_json(
    output: Path,
    document: dict[str, Any],
    *,
    publication_precondition: PublicationPrecondition | None = None,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(document, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
        if publication_precondition is not None:
            _verify_publication_precondition(output, publication_precondition)
        os.replace(temp_path, output)
    except Exception:
        try:
            temp_path.unlink()
        except OSError:
            pass
        raise


def _capture_output_state(output: Path) -> OutputFileState:
    resolved = _resolve_path(output)
    try:
        stat = resolved.stat()
    except FileNotFoundError:
        return OutputFileState(path=resolved, exists=False)
    identity = _file_identity(stat)
    return OutputFileState(
        path=resolved,
        exists=True,
        size=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
        file_identity=identity,
    )


def _file_identity(stat: os.stat_result) -> tuple[int, int] | None:
    device = getattr(stat, "st_dev", None)
    inode = getattr(stat, "st_ino", None)
    if device is None or inode in (None, 0):
        return None
    return (int(device), int(inode))


def _verify_publication_precondition(output: Path, precondition: PublicationPrecondition) -> None:
    resolved_output = _resolve_path(output)
    confirmed_path = _resolve_path(precondition.output_path)
    confirmed_state = precondition.confirmed_state
    if resolved_output != confirmed_path or resolved_output != _resolve_path(confirmed_state.path):
        raise PublicationPreconditionError(_publication_precondition_issue("Output path no longer matches the confirmed path."))

    current = _capture_output_state(resolved_output)
    if not confirmed_state.exists:
        if current.exists:
            raise PublicationPreconditionError(_publication_precondition_issue("Confirmed absent output appeared before publication."))
        return

    if not current.exists:
        raise PublicationPreconditionError(_publication_precondition_issue("Confirmed existing output disappeared before publication."))
    if current.size != confirmed_state.size or current.mtime_ns != confirmed_state.mtime_ns:
        raise PublicationPreconditionError(_publication_precondition_issue("Confirmed output size or modification time changed before publication."))
    if confirmed_state.file_identity is not None and current.file_identity != confirmed_state.file_identity:
        raise PublicationPreconditionError(_publication_precondition_issue("Confirmed output file identity changed before publication."))


def _publication_precondition_issue(description: str) -> ImportIssue:
    return ImportIssue(
        "fatal",
        "OUTPUT_CHANGED_SINCE_CONFIRMATION",
        description=description,
        stage=ConverterStage.PUBLICATION.value,
        source_file_role=SourceFileRole.OUTPUT.value,
    )


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
        result = ImportResult(
            published=False,
            output_path=None,
            worksheet=None,
            header_row=None,
            source_row_count=0,
            record_count=0,
            snapshot_id=None,
            issues=(
                ImportIssue(
                    "fatal",
                    "CONVERTER_CONFIGURATION_ERROR",
                    description=str(exc),
                    stage=ConverterStage.CONFIGURATION.value,
                ),
            ),
            operation=ConverterOperation.CONVERSION.value,
            stage_reached=ConverterStage.CONFIGURATION.value,
        )
        print(json.dumps(result.to_report(), ensure_ascii=False, indent=2, sort_keys=True))
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
