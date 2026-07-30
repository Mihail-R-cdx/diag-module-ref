"""Application-owned exact diagnostic model dispatch registry and resolver."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.equipment_inventory import EquipmentInventory, EquipmentRecord


class DiagnosticActionPurpose(str, Enum):
    DIAGNOSTIC_START = "DIAGNOSTIC_START"
    CREDENTIAL_CONFIGURATION = "CREDENTIAL_CONFIGURATION"


class ModelResolutionStatus(str, Enum):
    INVENTORY_UNAVAILABLE = "INVENTORY_UNAVAILABLE"
    IP_NOT_FOUND = "IP_NOT_FOUND"
    AMBIGUOUS_IP = "AMBIGUOUS_IP"
    MODEL_UNMAPPED = "MODEL_UNMAPPED"
    MODEL_UNSUPPORTED = "MODEL_UNSUPPORTED"
    RESOLVED = "RESOLVED"


@dataclass(frozen=True)
class DiagnosticDispatchEntry:
    diagnostic_model: str
    screen_key: str
    lifecycle_route: str


@dataclass(frozen=True)
class ActionBinding:
    purpose: DiagnosticActionPurpose
    generation: int
    normalized_ip: str
    inventory_context_identity: str
    resolution_status: str | None
    selection_source: str | None
    accepted_model: str | None
    screen_key: str | None
    lifecycle_route: str | None
    fallback_dialog_id: int | None = None
    credential_dialog_id: int | None = None


@dataclass(frozen=True)
class ModelResolutionResult:
    purpose: DiagnosticActionPurpose
    status: ModelResolutionStatus
    normalized_ip: str
    snapshot_id: str | None
    record_count: int | None = None
    record: EquipmentRecord | None = None
    entry: DiagnosticDispatchEntry | None = None
    safe_reason: str | None = None

    @property
    def resolved(self) -> bool:
        return self.status is ModelResolutionStatus.RESOLVED and self.entry is not None


DISPATCH_REGISTRY: tuple[DiagnosticDispatchEntry, ...] = (
    DiagnosticDispatchEntry("Huawei TE20", "codec", "huawei_te20"),
    DiagnosticDispatchEntry("Huawei TE40", "codec", "huawei_te40"),
    DiagnosticDispatchEntry("CloudLink Bar 310", "codec", "cloudlink_bar_310"),
    DiagnosticDispatchEntry("Polycom RPG 310", "codec", "polycom_rpg_310"),
    DiagnosticDispatchEntry("Extron IN1804", "matrix", "matrix_controller"),
    DiagnosticDispatchEntry("Aten PE8208AV", "pdu", "pdu_aten_pe8208av"),
    DiagnosticDispatchEntry("Extron IPL T PCS4i", "pdu", "pdu_pcs4i"),
    DiagnosticDispatchEntry("Biamp Tesira Forte CI", "audio_dsp", "biamp_tesira_forte_ci"),
    DiagnosticDispatchEntry("Extron DMP 64 Plus", "audio_dsp", "dmp_polling_controller"),
)


def dispatch_entries() -> tuple[DiagnosticDispatchEntry, ...]:
    return DISPATCH_REGISTRY


def dispatch_model_names() -> tuple[str, ...]:
    return tuple(entry.diagnostic_model for entry in DISPATCH_REGISTRY)


def dispatch_entry_for_model(model: str | None) -> DiagnosticDispatchEntry | None:
    if model is None:
        return None
    return _DISPATCH_BY_MODEL.get(model)


def validate_dispatch_registry(
    *,
    registered_screens: set[str] | frozenset[str],
    page_models_by_screen: dict[str, tuple[str, ...]],
) -> None:
    seen: set[str] = set()
    for entry in DISPATCH_REGISTRY:
        if entry.diagnostic_model in seen:
            raise ValueError(f"Duplicate diagnostic model: {entry.diagnostic_model}")
        seen.add(entry.diagnostic_model)
        if not entry.screen_key:
            raise ValueError(f"Dispatch model has no screen: {entry.diagnostic_model}")
        if not entry.lifecycle_route:
            raise ValueError(f"Dispatch model has no lifecycle: {entry.diagnostic_model}")
        if entry.screen_key not in registered_screens:
            raise ValueError(f"Dispatch screen is not registered: {entry.screen_key}")
        if entry.diagnostic_model not in page_models_by_screen.get(entry.screen_key, ()):
            raise ValueError(
                f"Dispatch model {entry.diagnostic_model} is not registered on {entry.screen_key}"
            )


def resolve_exact_model_for_ip(
    *,
    purpose: DiagnosticActionPurpose,
    normalized_ip: str,
    inventory: EquipmentInventory | None,
) -> ModelResolutionResult:
    snapshot_id = inventory.metadata.snapshot_id if inventory is not None else None
    if inventory is None:
        return ModelResolutionResult(
            purpose=purpose,
            status=ModelResolutionStatus.INVENTORY_UNAVAILABLE,
            normalized_ip=normalized_ip,
            snapshot_id=snapshot_id,
            record_count=None,
            safe_reason="База оборудования недоступна.",
        )

    records = tuple(inventory.find_by_ip(normalized_ip))
    if not records:
        return ModelResolutionResult(
            purpose=purpose,
            status=ModelResolutionStatus.IP_NOT_FOUND,
            normalized_ip=normalized_ip,
            snapshot_id=snapshot_id,
            record_count=0,
            safe_reason="IP-адрес не найден в базе оборудования.",
        )
    if len(records) > 1:
        return ModelResolutionResult(
            purpose=purpose,
            status=ModelResolutionStatus.AMBIGUOUS_IP,
            normalized_ip=normalized_ip,
            snapshot_id=snapshot_id,
            record_count=len(records),
            safe_reason="В базе найдено несколько устройств с этим IP-адресом.",
        )

    record = records[0]
    if record.diagnostic_model is None:
        return ModelResolutionResult(
            purpose=purpose,
            status=ModelResolutionStatus.MODEL_UNMAPPED,
            normalized_ip=normalized_ip,
            snapshot_id=snapshot_id,
            record_count=1,
            record=record,
            safe_reason="Для устройства не назначена поддерживаемая диагностическая модель.",
        )
    entry = dispatch_entry_for_model(record.diagnostic_model)
    if entry is None:
        return ModelResolutionResult(
            purpose=purpose,
            status=ModelResolutionStatus.MODEL_UNSUPPORTED,
            normalized_ip=normalized_ip,
            snapshot_id=snapshot_id,
            record_count=1,
            record=record,
            safe_reason="Диагностическая модель устройства не поддерживается приложением.",
        )
    return ModelResolutionResult(
        purpose=purpose,
        status=ModelResolutionStatus.RESOLVED,
        normalized_ip=normalized_ip,
        snapshot_id=snapshot_id,
        record_count=1,
        record=record,
        entry=entry,
    )


_DISPATCH_BY_MODEL = {entry.diagnostic_model: entry for entry in DISPATCH_REGISTRY}
