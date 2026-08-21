"""Application-owned room diagnostic session, row state, and one-shot queue.

This module deliberately contains no Qt objects or transport knowledge.  The GUI and
model lifecycle owners project/execute these immutable contexts; inventory remains the
only source of room membership and identity.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from core.equipment_inventory import EquipmentInventory, EquipmentRecord, normalize_ip_address
from core.exceptions import AuthenticationError


class RoomSourceStatus(str, Enum):
    INVENTORY_UNAVAILABLE = "INVENTORY_UNAVAILABLE"
    IP_NOT_FOUND = "IP_NOT_FOUND"
    AMBIGUOUS_SOURCE_IP = "AMBIGUOUS_SOURCE_IP"
    ROOM = "ROOM"
    LEGACY_SINGLE_DEVICE = "LEGACY_SINGLE_DEVICE"
    MODEL_UNMAPPED = "MODEL_UNMAPPED"
    MODEL_UNSUPPORTED = "MODEL_UNSUPPORTED"


class DeviceRowStatus(str, Enum):
    UNSUPPORTED = "не поддерживается"
    MISSING_IP = "IP не указан"
    AMBIGUOUS_IP = "неоднозначный IP"
    WAITING = "ожидание опроса"
    CONNECTING = "подключение..."
    CONNECTED = "подключено"
    FAILED = "не удалось подключиться"
    DEGRADED = "соединение потеряно"


class RoomCycleStatus(str, Enum):
    ACTIVE = "Опрос оборудования помещения..."
    COMPLETE = "Опрос завершён"
    COMPLETE_WITH_PROBLEMS = "Опрос завершён с проблемами"


class OneShotEventKind(str, Enum):
    PARTIAL = "PARTIAL"
    USABLE_SUCCESS = "USABLE_SUCCESS"
    USABLE_SUCCESS_WITH_WARNING = "USABLE_SUCCESS_WITH_WARNING"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"
    CLEANUP_COMPLETE = "CLEANUP_COMPLETE"
    CLEANUP_TIMEOUT = "CLEANUP_TIMEOUT"


@dataclass(frozen=True)
class RoomCleanupPolicy:
    """Non-UI, testable limit for logical room-row retirement."""

    timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("Room cleanup timeout must be positive.")


@dataclass(frozen=True)
class RoomModelCapability:
    """Exact registry data consumed by room mode without model inference."""

    diagnostic_model: str
    screen_key: str
    lifecycle_route: str
    room_adapter_key: str
    presentation_capability: str = "presentation_only"
    requires_credentials: bool = True
    credentialless_allowed: bool = False


@dataclass(frozen=True)
class RoomDiagnosticSessionIdentity:
    inventory_snapshot_id: str
    room_generation: int
    normalized_source_ip: str
    source_record_id: str
    room_id: str


@dataclass
class DeviceRowState:
    record_id: str
    diagnostic_model: str | None
    ip_address: str | None
    source_model: str | None
    status: DeviceRowStatus
    capability: RoomModelCapability | None = None
    accepted_snapshot: Any | None = None
    partial_data: Any | None = None
    warnings: list[str] = field(default_factory=list)
    failure_reason: str | None = None
    operation_token: int = 0
    cleanup_complete: bool = False
    stale: bool = False

    @property
    def eligible(self) -> bool:
        return self.status is DeviceRowStatus.WAITING

    @property
    def model_label(self) -> str:
        return self.diagnostic_model or self.source_model or "Модель не определена"


@dataclass
class RoomDiagnosticSession:
    identity: RoomDiagnosticSessionIdentity
    room_name: str | None
    room_address: str | None
    room_vip: bool | None
    rows: list[DeviceRowState]
    status: RoomCycleStatus = RoomCycleStatus.ACTIVE
    completion_timestamp: Any | None = None
    active_record_id: str | None = None
    invalidated: bool = False
    expanded_record_id: str | None = None

    def row_for(self, record_id: str) -> DeviceRowState:
        for row in self.rows:
            if row.record_id == record_id:
                return row
        raise KeyError(record_id)

    def is_current(self, identity: RoomDiagnosticSessionIdentity, row: DeviceRowState, token: int) -> bool:
        return not self.invalidated and self.identity == identity and row.operation_token == token

    def invalidate(self) -> None:
        self.invalidated = True
        self.active_record_id = None
        for row in self.rows:
            row.operation_token += 1


@dataclass(frozen=True)
class RoomSourceResolution:
    status: RoomSourceStatus
    normalized_source_ip: str
    record: EquipmentRecord | None = None
    capability: RoomModelCapability | None = None
    safe_reason: str | None = None


@dataclass(frozen=True)
class OneShotAttemptContext:
    session_identity: RoomDiagnosticSessionIdentity
    record_id: str
    diagnostic_model: str
    ip_address: str
    operation_token: int
    credential: Mapping[str, Any] | None
    is_current: Callable[[], bool] | None = None


@dataclass(frozen=True)
class OneShotEvent:
    kind: OneShotEventKind
    data: Any | None = None
    warning: str | None = None
    failure_reason: str | None = None
    credential_success: bool = False


class RoomOneShotAdapter(Protocol):
    def run(self, context: OneShotAttemptContext) -> Iterable[OneShotEvent]: ...

    def cleanup(self, context: OneShotAttemptContext) -> bool: ...


def resolve_room_source(
    inventory: EquipmentInventory | None,
    source_ip: str,
    capabilities: Mapping[str, RoomModelCapability],
) -> RoomSourceResolution:
    """Resolve a source before any manual-model or device lifecycle decision."""
    normalized = normalize_ip_address(source_ip) or ""
    if inventory is None:
        return RoomSourceResolution(RoomSourceStatus.INVENTORY_UNAVAILABLE, normalized)
    records = inventory.find_by_ip(normalized)
    if not records:
        return RoomSourceResolution(RoomSourceStatus.IP_NOT_FOUND, normalized, safe_reason="IP-адрес не найден в базе оборудования.")
    if len(records) != 1:
        return RoomSourceResolution(RoomSourceStatus.AMBIGUOUS_SOURCE_IP, normalized, safe_reason="В базе найдено несколько устройств с этим IP-адресом.")
    record = records[0]
    capability = capabilities.get(record.diagnostic_model or "")
    if record.room_id is not None:
        return RoomSourceResolution(RoomSourceStatus.ROOM, normalized, record, capability)
    if record.diagnostic_model is None:
        return RoomSourceResolution(RoomSourceStatus.MODEL_UNMAPPED, normalized, record)
    if capability is None:
        return RoomSourceResolution(RoomSourceStatus.MODEL_UNSUPPORTED, normalized, record)
    return RoomSourceResolution(RoomSourceStatus.LEGACY_SINGLE_DEVICE, normalized, record, capability)


def build_room_session(
    *,
    inventory: EquipmentInventory,
    source: RoomSourceResolution,
    generation: int,
    capabilities: Mapping[str, RoomModelCapability],
) -> RoomDiagnosticSession:
    if source.status is not RoomSourceStatus.ROOM or source.record is None or source.record.room_id is None:
        raise ValueError("A resolved room source is required.")
    source_record = source.record
    canonical_records = tuple(sorted(inventory.find_room_equipment(source_record.room_id), key=lambda record: record.record_id))
    ordered = (source_record,) + tuple(record for record in canonical_records if record.record_id != source_record.record_id)
    duplicate_ips = {record.ip_address for record in ordered if record.ip_address and sum(other.ip_address == record.ip_address for other in ordered) > 1}
    rows = [_row_state(record, capabilities.get(record.diagnostic_model or ""), duplicate_ips) for record in ordered]
    identity = RoomDiagnosticSessionIdentity(
        inventory.metadata.snapshot_id, generation, source.normalized_source_ip, source_record.record_id, source_record.room_id
    )
    return RoomDiagnosticSession(
        identity=identity,
        room_name=_display_value(source_record, canonical_records, "room_name"),
        room_address=_display_value(source_record, canonical_records, "room_address"),
        room_vip=_display_value(source_record, canonical_records, "room_vip"),
        rows=rows,
        expanded_record_id=source_record.record_id if rows and rows[0].eligible else None,
    )


def _display_value(source: EquipmentRecord, records: tuple[EquipmentRecord, ...], name: str) -> Any | None:
    value = getattr(source, name)
    if value is not None and (not isinstance(value, str) or value.strip()):
        return value
    for record in records:
        value = getattr(record, name)
        if value is not None and (not isinstance(value, str) or value.strip()):
            return value
    return None


def _row_state(record: EquipmentRecord, capability: RoomModelCapability | None, duplicate_ips: set[str]) -> DeviceRowState:
    if capability is None:
        status = DeviceRowStatus.UNSUPPORTED
    elif record.ip_address is None:
        status = DeviceRowStatus.MISSING_IP
    elif record.ip_address in duplicate_ips:
        status = DeviceRowStatus.AMBIGUOUS_IP
    else:
        status = DeviceRowStatus.WAITING
    return DeviceRowState(record.record_id, record.diagnostic_model, record.ip_address, record.source_model, status, capability)


class RoomDiagnosticOrchestrator:
    """Serialized application queue; adapters never select credentials themselves."""

    def __init__(
        self,
        *,
        adapters: Mapping[str, RoomOneShotAdapter],
        credential_candidates: Callable[[str, str], tuple[Mapping[str, Any], ...]],
        ping: Callable[[str], bool],
        persist_success: Callable[[str, str, int], None] | None = None,
        starting_index: Callable[[str, str, tuple[Mapping[str, Any], ...]], int] | None = None,
        clock: Callable[[], Any] | None = None,
        on_update: Callable[[RoomDiagnosticSession], None] | None = None,
    ) -> None:
        self._adapters = adapters
        self._credential_candidates = credential_candidates
        self._ping = ping
        self._persist_success = persist_success
        self._starting_index = starting_index or (lambda _model, _ip, _candidates: 0)
        self._clock = clock
        self._on_update = on_update

    def run(self, session: RoomDiagnosticSession) -> RoomDiagnosticSession:
        for row in session.rows:
            if session.invalidated:
                return session
            if not row.eligible:
                continue
            self._run_row(session, row)
            self._notify(session)
        if not session.invalidated:
            session.active_record_id = None
            session.status = RoomCycleStatus.COMPLETE if not self._has_problem(session) else RoomCycleStatus.COMPLETE_WITH_PROBLEMS
            if self._clock is not None:
                session.completion_timestamp = self._clock()
            self._notify(session)
        return session

    def _run_row(self, session: RoomDiagnosticSession, row: DeviceRowState) -> None:
        capability = row.capability
        assert capability is not None and row.diagnostic_model is not None and row.ip_address is not None
        try:
            candidates = tuple(self._credential_candidates(row.diagnostic_model, row.ip_address) or ())
        except Exception:
            # Credential-provider details are never diagnostic presentation.
            candidates = ()
        if not candidates and capability.requires_credentials and not capability.credentialless_allowed:
            row.status = DeviceRowStatus.FAILED
            row.failure_reason = "Credentials не настроены"
            self._notify(session)
            return
        if not candidates:
            candidates = (None,)
        index = max(0, min(self._starting_index(row.diagnostic_model, row.ip_address, candidates), len(candidates) - 1))
        if not self._is_current(session, row):
            return
        # The plan is validated before ping; no adapter/handler is acquired before this point.
        if not self._ping(row.ip_address):
            row.status = DeviceRowStatus.FAILED
            row.failure_reason = "Устройство недоступно"
            self._notify(session)
            return
        row.status = DeviceRowStatus.CONNECTING
        session.active_record_id = row.record_id
        self._notify(session)
        while index < len(candidates) and self._is_current(session, row):
            row.operation_token += 1
            token = row.operation_token
            context = OneShotAttemptContext(
                session.identity,
                row.record_id,
                row.diagnostic_model,
                row.ip_address,
                token,
                candidates[index],
                is_current=lambda: self._is_current(session, row, token),
            )
            adapter = self._adapters.get(capability.room_adapter_key)
            if adapter is None:
                row.status = DeviceRowStatus.FAILED
                row.failure_reason = "Диагностический адаптер недоступен"
                return
            retry = False
            pending_success_index: int | None = None
            try:
                for event in adapter.run(context):
                    if not self._is_current(session, row, token):
                        return
                    if event.kind is OneShotEventKind.PARTIAL:
                        row.partial_data = event.data
                    elif event.kind in {OneShotEventKind.USABLE_SUCCESS, OneShotEventKind.USABLE_SUCCESS_WITH_WARNING}:
                        row.accepted_snapshot = event.data
                        row.status = DeviceRowStatus.CONNECTED
                        if event.warning:
                            row.warnings.append(event.warning)
                        if event.credential_success and event.kind is OneShotEventKind.USABLE_SUCCESS:
                            # A diagnostic result is not yet a completed attempt:
                            # retain only non-secret evidence until retirement ends.
                            pending_success_index = index
                    elif event.kind is OneShotEventKind.TERMINAL_FAILURE:
                        pending_success_index = None
                        if isinstance(event.data, AuthenticationError) and index + 1 < len(candidates):
                            retry = True
                        else:
                            row.status = DeviceRowStatus.FAILED
                            row.failure_reason = event.failure_reason or "Не удалось выполнить диагностику"
                    elif event.kind is OneShotEventKind.CLEANUP_COMPLETE:
                        row.cleanup_complete = True
                        if pending_success_index is not None and self._persist_success:
                            self._persist_success(row.diagnostic_model, row.ip_address, pending_success_index)
                            pending_success_index = None
                    elif event.kind is OneShotEventKind.CLEANUP_TIMEOUT:
                        # The worker may finish physically later, but its token loses
                        # authority now and the serial queue can make progress.
                        row.cleanup_complete = True
                        row.operation_token += 1
                        pending_success_index = None
                        if row.accepted_snapshot is not None:
                            row.status = DeviceRowStatus.DEGRADED
                            row.stale = True
                            row.warnings.append("Соединение завершено по таймауту")
                        else:
                            row.status = DeviceRowStatus.FAILED
                            row.failure_reason = "Не удалось завершить соединение"
                    self._notify(session)
                if not row.cleanup_complete:
                    row.cleanup_complete = bool(adapter.cleanup(context))
                    if row.cleanup_complete and pending_success_index is not None and self._persist_success:
                        self._persist_success(row.diagnostic_model, row.ip_address, pending_success_index)
                        pending_success_index = None
            except AuthenticationError:
                retry = index + 1 < len(candidates)
            except Exception:
                row.status = DeviceRowStatus.FAILED
                row.failure_reason = "Не удалось выполнить диагностику"
            if retry:
                row.cleanup_complete = False
                index += 1
                continue
            if row.status is DeviceRowStatus.CONNECTING:
                row.status = DeviceRowStatus.FAILED
                row.failure_reason = "Не удалось выполнить диагностику"
            return

    def _notify(self, session: RoomDiagnosticSession) -> None:
        if self._on_update is not None and not session.invalidated:
            self._on_update(session)

    @staticmethod
    def _is_current(session: RoomDiagnosticSession, row: DeviceRowState, token: int | None = None) -> bool:
        return session.is_current(session.identity, row, row.operation_token if token is None else token)

    @staticmethod
    def _has_problem(session: RoomDiagnosticSession) -> bool:
        return any(row.status is not DeviceRowStatus.CONNECTED or row.warnings for row in session.rows)
