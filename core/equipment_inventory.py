"""Canonical equipment inventory snapshot loading and indexed lookup."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


SCHEMA_VERSION = 1
SNAPSHOT_FILENAME = "equipment_inventory.local.json"
DEVICE_KINDS = frozenset({"pdu", "video_codec", "other"})
SUPPORTED_DIAGNOSTIC_MODELS = frozenset(
    {
        "Huawei TE20",
        "Huawei TE40",
        "CloudLink Bar 310",
        "Polycom RPG 310",
        "Extron IN1804",
        "Aten PE8208AV",
        "Extron IPL T PCS4i",
        "Biamp Tesira Forte CI",
        "Extron DMP 64 Plus",
    }
)
RECORD_FIELDS = (
    "record_id",
    "source_model",
    "diagnostic_model",
    "ip_address",
    "mac_address",
    "serial_number",
    "room_id",
    "room_name",
    "device_kind",
)
ROOT_FIELDS = frozenset({"schema_version", "snapshot_id", "records", "generated_at", "source_row_count"})
REQUIRED_ROOT_FIELDS = frozenset({"schema_version", "snapshot_id", "records"})
SNAPSHOT_ID_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
RFC3339_UTC_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


class InventoryLoadFailure(str, Enum):
    NOT_FOUND = "NOT_FOUND"
    UNREADABLE = "UNREADABLE"
    INVALID_FORMAT = "INVALID_FORMAT"
    UNSUPPORTED_SCHEMA = "UNSUPPORTED_SCHEMA"
    INVALID_SNAPSHOT = "INVALID_SNAPSHOT"


class EquipmentInventoryLoadError(Exception):
    """Structured inventory load failure safe for application consumers."""

    def __init__(self, category: InventoryLoadFailure, message: str):
        super().__init__(message)
        self.category = category
        self.message = message


@dataclass(frozen=True)
class EquipmentRecord:
    record_id: str
    source_model: str | None
    diagnostic_model: str | None
    ip_address: str | None
    mac_address: str | None
    serial_number: str | None
    room_id: str | None
    room_name: str | None
    device_kind: str


@dataclass(frozen=True)
class EquipmentInventoryMetadata:
    schema_version: int
    snapshot_id: str
    generated_at: str | None = None
    source_row_count: int | None = None


@dataclass(frozen=True)
class EquipmentInventory:
    metadata: EquipmentInventoryMetadata
    records: tuple[EquipmentRecord, ...]
    _by_ip: Mapping[str, tuple[EquipmentRecord, ...]]
    _by_room: Mapping[str, tuple[EquipmentRecord, ...]]
    _by_room_and_kind: Mapping[tuple[str, str], tuple[EquipmentRecord, ...]]

    @classmethod
    def from_records(
        cls,
        records: tuple[EquipmentRecord, ...],
        metadata: EquipmentInventoryMetadata,
    ) -> "EquipmentInventory":
        ordered_records = tuple(sorted(records, key=lambda record: record.record_id))
        by_ip: dict[str, list[EquipmentRecord]] = {}
        by_room: dict[str, list[EquipmentRecord]] = {}
        by_room_kind: dict[tuple[str, str], list[EquipmentRecord]] = {}

        for record in ordered_records:
            if record.ip_address is not None:
                by_ip.setdefault(record.ip_address, []).append(record)
            if record.room_id is not None:
                by_room.setdefault(record.room_id, []).append(record)
                by_room_kind.setdefault((record.room_id, record.device_kind), []).append(record)

        return cls(
            metadata=metadata,
            records=ordered_records,
            _by_ip=_freeze_index(by_ip),
            _by_room=_freeze_index(by_room),
            _by_room_and_kind=_freeze_index(by_room_kind),
        )

    def find_by_ip(self, ip_address: str) -> tuple[EquipmentRecord, ...]:
        normalized = normalize_ip_address(ip_address)
        if normalized is None:
            return ()
        return self._by_ip.get(normalized, ())

    def find_room_equipment(self, room_id: str) -> tuple[EquipmentRecord, ...]:
        normalized = normalize_required_text(room_id)
        if normalized is None:
            return ()
        return self._by_room.get(normalized, ())

    def find_by_room_and_kind(self, room_id: str, device_kind: str) -> tuple[EquipmentRecord, ...]:
        normalized_room_id = normalize_required_text(room_id)
        if normalized_room_id is None or device_kind not in DEVICE_KINDS:
            return ()
        return self._by_room_and_kind.get((normalized_room_id, device_kind), ())


def application_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_snapshot_path() -> Path:
    return application_root() / SNAPSHOT_FILENAME


def load_equipment_inventory(path: str | Path | None = None) -> EquipmentInventory:
    snapshot_path = Path(path) if path is not None else default_snapshot_path()
    try:
        raw_bytes = snapshot_path.read_bytes()
    except FileNotFoundError as exc:
        raise EquipmentInventoryLoadError(
            InventoryLoadFailure.NOT_FOUND,
            "Equipment inventory snapshot was not found.",
        ) from exc
    except OSError as exc:
        raise EquipmentInventoryLoadError(
            InventoryLoadFailure.UNREADABLE,
            "Equipment inventory snapshot could not be read.",
        ) from exc

    try:
        raw = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EquipmentInventoryLoadError(
            InventoryLoadFailure.INVALID_FORMAT,
            "Equipment inventory snapshot is not valid UTF-8 JSON.",
        ) from exc

    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EquipmentInventoryLoadError(
            InventoryLoadFailure.INVALID_FORMAT,
            "Equipment inventory snapshot is not valid UTF-8 JSON.",
        ) from exc

    return inventory_from_document(document)


def inventory_from_document(document: Any) -> EquipmentInventory:
    if not isinstance(document, dict):
        _invalid_snapshot("Snapshot root must be a JSON object.")
    root_keys = set(document)
    if not REQUIRED_ROOT_FIELDS.issubset(root_keys) or not root_keys.issubset(ROOT_FIELDS):
        _invalid_snapshot("Snapshot root fields do not match schema v1.")
    if (
        not isinstance(document["schema_version"], int)
        or isinstance(document["schema_version"], bool)
        or document["schema_version"] != SCHEMA_VERSION
    ):
        raise EquipmentInventoryLoadError(
            InventoryLoadFailure.UNSUPPORTED_SCHEMA,
            "Equipment inventory snapshot schema is not supported.",
        )
    if not isinstance(document["snapshot_id"], str) or not SNAPSHOT_ID_PATTERN.fullmatch(document["snapshot_id"]):
        _invalid_snapshot("Snapshot identity is malformed.")
    if not isinstance(document["records"], list):
        _invalid_snapshot("Snapshot records must be an array.")
    generated_at = document.get("generated_at")
    if generated_at is not None and not _is_rfc3339_utc(generated_at):
        _invalid_snapshot("Snapshot generated_at metadata is invalid.")
    source_row_count = document.get("source_row_count")
    if source_row_count is not None:
        if not isinstance(source_row_count, int) or isinstance(source_row_count, bool) or source_row_count < 0:
            _invalid_snapshot("Snapshot source_row_count metadata is invalid.")

    records = tuple(_parse_record(record) for record in document["records"])
    normalized_ids: set[str] = set()
    for record in records:
        if record.record_id in normalized_ids:
            _invalid_snapshot("Snapshot contains duplicate record_id values.")
        normalized_ids.add(record.record_id)

    expected_snapshot_id = compute_snapshot_id(records, schema_version=SCHEMA_VERSION)
    if document["snapshot_id"] != expected_snapshot_id:
        raise EquipmentInventoryLoadError(
            InventoryLoadFailure.INVALID_SNAPSHOT,
            "Equipment inventory snapshot identity does not match its canonical content.",
        )

    metadata = EquipmentInventoryMetadata(
        schema_version=SCHEMA_VERSION,
        snapshot_id=document["snapshot_id"],
        generated_at=generated_at,
        source_row_count=source_row_count,
    )
    return EquipmentInventory.from_records(records, metadata)


def compute_snapshot_id(records: tuple[EquipmentRecord, ...] | list[EquipmentRecord | Mapping[str, Any]], *, schema_version: int = SCHEMA_VERSION) -> str:
    payload = {
        "schema_version": schema_version,
        "records": [
            _record_identity_dict(record)
            for record in sorted(records, key=lambda item: _record_id_for_sort(item))
        ],
    }
    encoded = json.dumps(
        _normalize_json_text(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def record_to_dict(record: EquipmentRecord) -> dict[str, Any]:
    return {field: getattr(record, field) for field in RECORD_FIELDS}


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    normalized = unicodedata.normalize("NFC", value).strip()
    return normalized or None


def normalize_required_text(value: Any) -> str | None:
    return normalize_text(value)


def normalize_ip_address(value: Any) -> str | None:
    text = normalize_text(value)
    if text is None:
        return None
    try:
        return str(ipaddress.IPv4Address(text))
    except ipaddress.AddressValueError:
        return None


def normalize_mac_address(value: Any) -> str | None:
    text = normalize_text(value)
    if text is None:
        return None
    if re.fullmatch(r"[0-9A-Fa-f]{12}", text):
        compact = text.lower()
    elif re.fullmatch(r"[0-9A-Fa-f]{2}([-:])[0-9A-Fa-f]{2}(\1[0-9A-Fa-f]{2}){4}", text):
        compact = re.sub(r"[-:]", "", text).lower()
    elif re.fullmatch(r"[0-9A-Fa-f]{4}(\.[0-9A-Fa-f]{4}){2}", text):
        compact = text.replace(".", "").lower()
    else:
        return None
    return ":".join(compact[index : index + 2] for index in range(0, 12, 2))


def _parse_record(document: Any) -> EquipmentRecord:
    if not isinstance(document, dict) or set(document) != set(RECORD_FIELDS):
        _invalid_snapshot("Canonical record fields do not match schema v1.")

    record_id = _canonical_required_string(document["record_id"], "record_id")
    device_kind = document["device_kind"]
    if not isinstance(device_kind, str) or device_kind not in DEVICE_KINDS:
        _invalid_snapshot("Canonical record has invalid device_kind.")

    source_model = _canonical_nullable_string(document["source_model"], "source_model")
    diagnostic_model = _canonical_nullable_string(document["diagnostic_model"], "diagnostic_model")
    if diagnostic_model is not None and diagnostic_model not in SUPPORTED_DIAGNOSTIC_MODELS:
        _invalid_snapshot("Canonical record has unsupported diagnostic_model.")
    ip_address = document["ip_address"]
    if ip_address is not None:
        if not isinstance(ip_address, str) or normalize_ip_address(ip_address) != ip_address:
            _invalid_snapshot("Canonical record has invalid ip_address.")
    mac_address = document["mac_address"]
    if mac_address is not None:
        if not isinstance(mac_address, str) or normalize_mac_address(mac_address) != mac_address:
            _invalid_snapshot("Canonical record has invalid mac_address.")

    return EquipmentRecord(
        record_id=record_id,
        source_model=source_model,
        diagnostic_model=diagnostic_model,
        ip_address=ip_address,
        mac_address=mac_address,
        serial_number=_canonical_nullable_string(document["serial_number"], "serial_number"),
        room_id=_canonical_nullable_string(document["room_id"], "room_id"),
        room_name=_canonical_nullable_string(document["room_name"], "room_name"),
        device_kind=device_kind,
    )


def _canonical_required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or normalize_text(value) != value:
        _invalid_snapshot(f"Canonical record has invalid {field}.")
    return value


def _canonical_nullable_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or normalize_text(value) != value:
        _invalid_snapshot(f"Canonical record has invalid {field}.")
    return value


def _record_identity_dict(record: EquipmentRecord | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(record, EquipmentRecord):
        return record_to_dict(record)
    return {field: record[field] for field in RECORD_FIELDS}


def _record_id_for_sort(record: EquipmentRecord | Mapping[str, Any]) -> str:
    if isinstance(record, EquipmentRecord):
        return record.record_id
    return str(record["record_id"])


def _normalize_json_text(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize_json_text(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_json_text(item) for key, item in value.items()}
    return value


def _freeze_index(index: dict[Any, list[EquipmentRecord]]) -> Mapping[Any, tuple[EquipmentRecord, ...]]:
    return MappingProxyType({key: tuple(value) for key, value in index.items()})


def _is_rfc3339_utc(value: Any) -> bool:
    if not isinstance(value, str) or not RFC3339_UTC_PATTERN.fullmatch(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == UTC.utcoffset(None)


def _invalid_snapshot(message: str) -> None:
    raise EquipmentInventoryLoadError(InventoryLoadFailure.INVALID_SNAPSHOT, message)
