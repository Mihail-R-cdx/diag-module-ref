"""Application-owned exact diagnostic model dispatch registry and resolver."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.equipment_inventory import EquipmentInventory, EquipmentRecord
from core.room_diagnostic_tree import RoomModelCapability


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
    room_adapter_key: str | None = None
    presentation_capability: str = "presentation_only"
    requires_credentials: bool = True
    credentialless_allowed: bool = False
    # These optional keys name composition bindings.  Keeping them on the
    # exact model entry prevents room mode from growing parallel model lists.
    live_binding_key: str | None = None
    local_refresh_binding_key: str | None = None
    auxiliary_binding_key: str | None = None
    mutation_binding_key: str | None = None
    reconciliation_binding_key: str | None = None
    cleanup_binding_key: str | None = None
    call_activity_capability: bool = False
    call_activity_binding_key: str | None = None
    # This independent marker states that the exact registry entry is required
    # to participate in call-activity projection.  It deliberately does not
    # derive from the binding key: validation must fail closed if a required
    # binding is accidentally removed rather than silently dropping the model.
    call_activity_required: bool = False

    def room_capability(self) -> RoomModelCapability:
        return RoomModelCapability(
            diagnostic_model=self.diagnostic_model,
            screen_key=self.screen_key,
            lifecycle_route=self.lifecycle_route,
            room_adapter_key=self.room_adapter_key or self.lifecycle_route,
            presentation_capability=self.presentation_capability,
            requires_credentials=self.requires_credentials,
            credentialless_allowed=self.credentialless_allowed,
            call_activity_binding_key=self.call_activity_binding_key,
        )


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


def _room_entry(
    diagnostic_model: str,
    screen_key: str,
    lifecycle_route: str,
    room_adapter_key: str,
    *,
    credentialless_allowed: bool = False,
    call_log: bool = False,
    pdu_mutation: bool = False,
    matrix_mutation: bool = False,
    live_binding_key: str | None = None,
    call_activity_binding_key: str | None = None,
    call_activity_required: bool = False,
) -> DiagnosticDispatchEntry:
    """Build the one registry entry used by both room phases.

    Every currently supported row offers only the safe read-only local
    refresh.  Live polling, auxiliary reads and mutation remain undeclared
    until model-specific adapters with their own cleanup contracts exist.
    """
    return DiagnosticDispatchEntry(
        diagnostic_model,
        screen_key,
        lifecycle_route,
        room_adapter_key,
        credentialless_allowed=credentialless_allowed,
        local_refresh_binding_key="room_one_shot_refresh",
        live_binding_key=live_binding_key,
        auxiliary_binding_key="room_codec_call_log" if call_log else None,
        mutation_binding_key=("room_pdu_mutation" if pdu_mutation else "matrix_room_route" if matrix_mutation else None),
        reconciliation_binding_key=("room_one_shot_refresh" if pdu_mutation else "matrix_room_route_reconcile" if matrix_mutation else None),
        cleanup_binding_key="room_one_shot_cleanup",
        call_activity_capability=call_activity_binding_key is not None,
        call_activity_binding_key=call_activity_binding_key,
        call_activity_required=call_activity_required,
    )


DISPATCH_REGISTRY: tuple[DiagnosticDispatchEntry, ...] = (
    _room_entry("Huawei TE20", "codec", "huawei_te20", "codec_one_shot", call_log=True, call_activity_binding_key="huawei_call_activity", call_activity_required=True),
    _room_entry("Huawei TE40", "codec", "huawei_te40", "codec_one_shot", call_log=True, call_activity_binding_key="huawei_call_activity", call_activity_required=True),
    _room_entry("CloudLink Bar 310", "codec", "cloudlink_bar_310", "codec_one_shot", call_log=True, live_binding_key="cloudlink_room_live", call_activity_binding_key="cloudlink_call_activity", call_activity_required=True),
    _room_entry("CloudLink Box 310", "codec", "cloudlink_bar_310", "codec_one_shot", call_log=True, live_binding_key="cloudlink_room_live", call_activity_binding_key="cloudlink_call_activity", call_activity_required=True),
    _room_entry("Polycom RPG 310", "codec", "polycom_rpg_310", "polycom_one_shot", call_log=True, call_activity_binding_key="polycom_call_activity", call_activity_required=True),
    _room_entry("Extron IN1804", "matrix", "matrix_controller", "matrix_one_shot", live_binding_key="matrix_room_live", matrix_mutation=True),
    _room_entry("Aten PE8208AV", "pdu", "pdu_aten_pe8208av", "pdu_one_shot", pdu_mutation=True),
    _room_entry("Extron IPL T PCS4i", "pdu", "pdu_pcs4i", "pdu_one_shot", credentialless_allowed=True, pdu_mutation=True),
    _room_entry("Biamp Tesira Forte CI", "audio_dsp", "biamp_tesira_forte_ci", "biamp_one_shot"),
    _room_entry("Extron DMP 64 Plus", "audio_dsp", "dmp_polling_controller", "dmp_one_shot", live_binding_key="dmp_room_live"),
)


def dispatch_entries() -> tuple[DiagnosticDispatchEntry, ...]:
    return DISPATCH_REGISTRY


def dispatch_model_names() -> tuple[str, ...]:
    return tuple(entry.diagnostic_model for entry in DISPATCH_REGISTRY)


def room_model_capabilities() -> dict[str, RoomModelCapability]:
    """Return the room view/adapter bindings from the sole exact registry."""
    return {entry.diagnostic_model: entry.room_capability() for entry in DISPATCH_REGISTRY}


def dispatch_entry_for_model(model: str | None) -> DiagnosticDispatchEntry | None:
    if model is None:
        return None
    return _DISPATCH_BY_MODEL.get(model)


def validate_dispatch_registry(
    *,
    registered_screens: set[str] | frozenset[str],
    page_models_by_screen: dict[str, tuple[str, ...]],
    available_room_adapter_keys: set[str] | frozenset[str] | None = None,
    available_room_interaction_binding_keys: set[str] | frozenset[str] | None = None,
    available_call_activity_binding_keys: set[str] | frozenset[str] | None = None,
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
        if not entry.room_adapter_key:
            raise ValueError(f"Dispatch model has no room adapter: {entry.diagnostic_model}")
        if (
            available_room_adapter_keys is not None
            and entry.room_adapter_key not in available_room_adapter_keys
        ):
            raise ValueError(
                f"Dispatch room adapter is not bound: {entry.diagnostic_model}"
            )
        if not entry.presentation_capability:
            raise ValueError(f"Dispatch model has no presentation capability: {entry.diagnostic_model}")
        if entry.screen_key not in registered_screens:
            raise ValueError(f"Dispatch screen is not registered: {entry.screen_key}")
        if entry.diagnostic_model not in page_models_by_screen.get(entry.screen_key, ()):
            raise ValueError(
                f"Dispatch model {entry.diagnostic_model} is not registered on {entry.screen_key}"
            )
        interaction_keys = (
            entry.live_binding_key,
            entry.local_refresh_binding_key,
            entry.auxiliary_binding_key,
            entry.mutation_binding_key,
            entry.reconciliation_binding_key,
        )
        declared_interaction = tuple(key for key in interaction_keys if key)
        if declared_interaction and not entry.cleanup_binding_key:
            raise ValueError(
                f"Dispatch interaction capability has no cleanup binding: {entry.diagnostic_model}"
            )
        if available_room_interaction_binding_keys is not None:
            for key in (*declared_interaction, entry.cleanup_binding_key):
                if key and key not in available_room_interaction_binding_keys:
                    raise ValueError(
                        f"Dispatch interaction binding is not bound: {entry.diagnostic_model}"
                    )
        if entry.call_activity_required and not entry.call_activity_binding_key:
            raise ValueError(
                f"Dispatch required call-activity binding is missing: {entry.diagnostic_model}"
            )
        if entry.call_activity_required and not entry.call_activity_capability:
            raise ValueError(
                f"Dispatch required call-activity capability is missing: {entry.diagnostic_model}"
            )
        if entry.call_activity_capability and not entry.call_activity_binding_key:
            raise ValueError(f"Dispatch call-activity binding is missing: {entry.diagnostic_model}")
        if entry.call_activity_binding_key and not entry.call_activity_capability:
            raise ValueError(f"Dispatch call-activity capability is missing: {entry.diagnostic_model}")
        if (
            available_call_activity_binding_keys is not None
            and entry.call_activity_capability
            and entry.call_activity_binding_key not in available_call_activity_binding_keys
        ):
            raise ValueError(f"Dispatch call-activity binding is not bound: {entry.diagnostic_model}")


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
