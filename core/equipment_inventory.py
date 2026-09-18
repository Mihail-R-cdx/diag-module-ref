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


SCHEMA_VERSION_V1 = 1
SCHEMA_VERSION_V2 = 2
SCHEMA_VERSION_V3 = 3
SCHEMA_VERSION_V4 = 4
SCHEMA_VERSION = SCHEMA_VERSION_V4
SNAPSHOT_FILENAME = "equipment_inventory.local.json"
DEVICE_KINDS = frozenset({"pdu", "video_codec", "other"})
SUPPORTED_DIAGNOSTIC_MODELS = frozenset(
    {
        "Huawei TE20",
        "Huawei TE40",
        "Huawei TE50",
        "CloudLink Bar 310",
        "CloudLink Box 310",
        "Polycom RPG 310",
        "Extron IN1804",
        "Extron IN1808",
        "Extron IN1608 xi",
        "Extron DTP CrossPoint 84",
        "Extron DTP CrossPoint 82 4K",
        "Extron DTP CrossPoint 84 4K",
        "Extron DTP CrossPoint 86 4K",
        "Extron DTP CrossPoint 108 4K",
        "Extron XTP CrossPoint 1600",
        "Extron XTP CrossPoint 3200",
        "Extron XTP II CrossPoint 1600",
        "Extron XTP II CrossPoint 3200",
        "Extron XTP II CrossPoint 6400",
        "Aten PE8208AV",
        "Extron IPL T PCS4i",
        "Biamp Tesira Forte CI",
        "Extron DMP 64 Plus",
    }
)
RECORD_FIELDS_V1 = (
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
RECORD_FIELDS = RECORD_FIELDS_V1 + ("room_vip",)
RECORD_FIELDS_V3 = RECORD_FIELDS + ("switch_ip_address", "switch_port")
RECORD_FIELDS_V4 = (
    "record_id",
    "source_model",
    "diagnostic_model",
    "ip_address",
    "mac_address",
    "serial_number",
    "room_id",
    "room_name",
    "room_address",
    "device_kind",
    "room_vip",
    "switch_ip_address",
    "switch_port",
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
    room_vip: bool | None = None
    room_address: str | None = None
    switch_ip_address: str | None = None
    switch_port: str | None = None


@dataclass(frozen=True)
class EquipmentInventoryMetadata:
    schema_version: int
    snapshot_id: str
    generated_at: str | None = None
    source_row_count: int | None = None


@dataclass(frozen=True)
class RoomSearchResult:
    """A display projection whose identity remains the canonical room id."""

    room_id: str
    display_name: str
    display_address: str | None
    selection_label: str


@dataclass(frozen=True)
class EquipmentInventory:
    metadata: EquipmentInventoryMetadata
    records: tuple[EquipmentRecord, ...]
    _by_ip: Mapping[str, tuple[EquipmentRecord, ...]]
    _by_room: Mapping[str, tuple[EquipmentRecord, ...]]
    _by_room_and_kind: Mapping[tuple[str, str], tuple[EquipmentRecord, ...]]
    _room_search: tuple[tuple[str, tuple[str, ...], str, str | None], ...]

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

        room_search: list[tuple[str, tuple[str, ...], str, str | None]] = []
        for room_id, room_records in by_room.items():
            names = tuple(
                name for name in (normalize_required_text(record.room_name) for record in room_records)
                if name is not None
            )
            if not names:
                continue
            address = next(
                (value for value in (normalize_required_text(record.room_address) for record in room_records) if value is not None),
                None,
            )
            room_search.append((room_id, names, names[0], address))
        room_search.sort(key=lambda item: (item[2].casefold(), (item[3] or "").casefold(), item[0]))

        return cls(
            metadata=metadata,
            records=ordered_records,
            _by_ip=_freeze_index(by_ip),
            _by_room=_freeze_index(by_room),
            _by_room_and_kind=_freeze_index(by_room_kind),
            _room_search=tuple(room_search),
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

    def find_rooms_by_name(self, query: str) -> tuple[RoomSearchResult, ...]:
        """Return immutable deterministic room results without device/network I/O."""
        normalized = normalize_required_text(query)
        if normalized is None:
            return ()
        needle = normalized.casefold()
        matches = [item for item in self._room_search if any(needle in name.casefold() for name in item[1])]
        counts: dict[str, int] = {}
        bases = [f"{name} — {address}" if address else name for _room, _names, name, address in matches]
        for base in bases:
            counts[base.casefold()] = counts.get(base.casefold(), 0) + 1
        variants: dict[str, int] = {}
        results: list[RoomSearchResult] = []
        for item, base in zip(matches, bases):
            key = base.casefold()
            if counts[key] > 1:
                variants[key] = variants.get(key, 0) + 1
                label = f"{base} (Вариант {variants[key]})"
            else:
                label = base
            results.append(RoomSearchResult(item[0], item[2], item[3], label))
        return tuple(results)


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
    schema_version = document["schema_version"]
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version not in {SCHEMA_VERSION_V1, SCHEMA_VERSION_V2, SCHEMA_VERSION_V3, SCHEMA_VERSION_V4}
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

    records = tuple(_parse_record(record, schema_version=schema_version) for record in document["records"])
    normalized_ids: set[str] = set()
    for record in records:
        if record.record_id in normalized_ids:
            _invalid_snapshot("Snapshot contains duplicate record_id values.")
        normalized_ids.add(record.record_id)

    expected_snapshot_id = compute_snapshot_id(
        document["records"],
        schema_version=schema_version,
    )
    if document["snapshot_id"] != expected_snapshot_id:
        raise EquipmentInventoryLoadError(
            InventoryLoadFailure.INVALID_SNAPSHOT,
            "Equipment inventory snapshot identity does not match its canonical content.",
        )

    metadata = EquipmentInventoryMetadata(
        schema_version=schema_version,
        snapshot_id=document["snapshot_id"],
        generated_at=generated_at,
        source_row_count=source_row_count,
    )
    return EquipmentInventory.from_records(records, metadata)


def compute_snapshot_id(records: tuple[EquipmentRecord, ...] | list[EquipmentRecord | Mapping[str, Any]], *, schema_version: int = SCHEMA_VERSION) -> str:
    if schema_version not in {SCHEMA_VERSION_V1, SCHEMA_VERSION_V2, SCHEMA_VERSION_V3, SCHEMA_VERSION_V4}:
        raise ValueError(f"Unsupported inventory schema version: {schema_version}")
    fields = _record_fields_for_schema(schema_version)
    payload = {
        "schema_version": schema_version,
        "records": [
            _record_identity_dict(record, fields)
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


def record_to_dict(record: EquipmentRecord, *, schema_version: int = SCHEMA_VERSION) -> dict[str, Any]:
    return {field: getattr(record, field) for field in _record_fields_for_schema(schema_version)}


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


def _parse_record(document: Any, *, schema_version: int) -> EquipmentRecord:
    fields = _record_fields_for_schema(schema_version)
    if not isinstance(document, dict) or set(document) != set(fields):
        _invalid_snapshot(f"Canonical record fields do not match schema v{schema_version}.")

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

    room_vip = None
    if schema_version in {SCHEMA_VERSION_V2, SCHEMA_VERSION_V3, SCHEMA_VERSION_V4}:
        room_vip = document["room_vip"]
        if room_vip is not None and not isinstance(room_vip, bool):
            _invalid_snapshot("Canonical record has invalid room_vip.")
    switch_ip_address = None
    switch_port = None
    if schema_version in {SCHEMA_VERSION_V3, SCHEMA_VERSION_V4}:
        switch_ip_address = document["switch_ip_address"]
        if switch_ip_address is not None:
            if not isinstance(switch_ip_address, str) or normalize_ip_address(switch_ip_address) != switch_ip_address:
                _invalid_snapshot("Canonical record has invalid switch_ip_address.")
        switch_port = _canonical_nullable_string(document["switch_port"], "switch_port")

    room_address = None
    if schema_version == SCHEMA_VERSION_V4:
        room_address = _canonical_nullable_string(document["room_address"], "room_address")

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
        room_vip=room_vip,
        room_address=room_address,
        switch_ip_address=switch_ip_address,
        switch_port=switch_port,
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


def _record_identity_dict(record: EquipmentRecord | Mapping[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    if isinstance(record, EquipmentRecord):
        return {field: getattr(record, field) for field in fields}
    return {field: record[field] for field in fields}


def _record_id_for_sort(record: EquipmentRecord | Mapping[str, Any]) -> str:
    if isinstance(record, EquipmentRecord):
        return record.record_id
    return str(record["record_id"])


def _record_fields_for_schema(schema_version: int) -> tuple[str, ...]:
    if schema_version == SCHEMA_VERSION_V1:
        return RECORD_FIELDS_V1
    if schema_version == SCHEMA_VERSION_V2:
        return RECORD_FIELDS
    if schema_version == SCHEMA_VERSION_V3:
        return RECORD_FIELDS_V3
    if schema_version == SCHEMA_VERSION_V4:
        return RECORD_FIELDS_V4
    raise ValueError(f"Unsupported inventory schema version: {schema_version}")


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
