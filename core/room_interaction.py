"""Exact-row post-cycle room interaction authority.

The automatic room queue deliberately ends with a presentation-only session.
This module owns the distinct post-cycle lifecycle.  It contains no Qt or
transport code: composition supplies non-secret operation/cleanup bindings and
all callbacks are accepted only through immutable row contexts.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from core.room_diagnostic_tree import (
    DeviceRowState,
    DeviceRowStatus,
    RoomCycleStatus,
    RoomDiagnosticSession,
)


class RoomInteractionKind(str, Enum):
    IDLE = "IDLE"
    LIVE = "LIVE"
    LOCAL_REFRESH = "LOCAL_REFRESH"
    AUXILIARY_READ = "AUXILIARY_READ"
    MUTATION = "MUTATION"
    RECONCILIATION = "RECONCILIATION"


class RoomInteractionState(str, Enum):
    IDLE = "IDLE"
    ACTIVE = "ACTIVE"
    RETIRING = "RETIRING"
    BLOCKED = "BLOCKED"


class RoomLiveState(str, Enum):
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"


@dataclass(frozen=True)
class RoomInteractionContext:
    """Immutable network target; widget state is intentionally absent."""

    inventory_snapshot_id: str
    room_generation: int
    record_id: str
    diagnostic_model: str
    ip_address: str
    row_operation_token: int
    interaction_generation: int
    credential_context_revision: int
    kind: RoomInteractionKind


@dataclass(frozen=True)
class RoomInteractionBindings:
    """Model bindings supplied by composition from the sole dispatch registry."""

    live: Callable[[RoomInteractionContext], None] | None = None
    local_refresh: Callable[[RoomInteractionContext], None] | None = None
    auxiliary: Callable[[RoomInteractionContext, str], None] | None = None
    mutation: Callable[[RoomInteractionContext, Any], None] | None = None
    reconciliation: Callable[[RoomInteractionContext, Any], None] | None = None
    cancel: Callable[[RoomInteractionContext], None] | None = None
    cleanup: Callable[[RoomInteractionContext], bool] | None = None

    def validate(self) -> None:
        declared = any((self.live, self.local_refresh, self.auxiliary, self.mutation, self.reconciliation))
        if declared and (self.cancel is None or self.cleanup is None):
            raise ValueError("Declared room interaction capability requires cancel and cleanup bindings.")


class RoomInteractionCoordinator:
    """One serialized, latest-wins interaction lane for a room session.

    Composition calls ``complete`` from its background operation callbacks.
    The coordinator is intentionally small and synchronous: it establishes
    authority before handing work to a background adapter, never performs I/O.
    """

    def __init__(
        self,
        *,
        bindings_for_model: Callable[[str], RoomInteractionBindings | None],
        credential_context_revision: Callable[[], int] | None = None,
        changed: Callable[[RoomDiagnosticSession], None] | None = None,
    ) -> None:
        self._bindings_for_model = bindings_for_model
        self._credential_context_revision = credential_context_revision or (lambda: 0)
        self._changed = changed
        self._session: RoomDiagnosticSession | None = None
        self._generation = 0
        self._active: RoomInteractionContext | None = None
        self._pending_live_record_id: str | None = None
        self._pending_operation: tuple[RoomInteractionKind, str | None, Any] | None = None

    @property
    def active_context(self) -> RoomInteractionContext | None:
        return self._active

    @property
    def has_exclusive_operation(self) -> bool:
        """Whether a post-cycle operation owns the room interaction lane.

        Live is intentionally not a UI-wide lock: it can be retired by a
        Local Refresh.  Every user-started network operation remains exclusive
        until its terminal callback or retirement cleanup boundary.
        """
        return self._active is not None and self._active.kind in {
            RoomInteractionKind.LOCAL_REFRESH,
            RoomInteractionKind.AUXILIARY_READ,
            RoomInteractionKind.MUTATION,
            RoomInteractionKind.RECONCILIATION,
        }

    def is_retiring(self, context: RoomInteractionContext) -> bool:
        """Whether ``context`` is awaiting its terminal cleanup boundary.

        A periodic live sample uses the same one-shot worker cleanup as Local
        Refresh. Its per-sample release is not retirement of the live
        lifecycle; callers use this predicate to distinguish it from a
        cancel/supersede cleanup that is allowed to free the lane.
        """
        if self._active != context or self._session is None:
            return False
        try:
            return (
                self._session.row_for(context.record_id).interaction_state
                is RoomInteractionState.RETIRING
            )
        except KeyError:
            return False

    def bind_session(self, session: RoomDiagnosticSession | None) -> None:
        self.invalidate("room_session_changed")
        self._session = session

    def cycle_finished(self, session: RoomDiagnosticSession) -> None:
        if session is not self._session or session.invalidated:
            return
        self._start_eligible_live()

    def expand(self, record_id: str) -> None:
        session = self._require_session()
        if session is None:
            return
        session.expanded_record_id = record_id
        if self._active is not None and self._active.record_id != record_id:
            self._pending_live_record_id = record_id
            self._retire_active()
            return
        self._start_eligible_live()

    def collapse(self, record_id: str) -> None:
        session = self._require_session()
        if session is None or session.expanded_record_id != record_id:
            return
        session.expanded_record_id = None
        self._pending_live_record_id = None
        self._pending_operation = None
        if self._active is not None and self._active.record_id == record_id:
            self._retire_active()
        self._notify()

    def request_local_refresh(self) -> RoomInteractionContext | None:
        return self._start_user_operation(RoomInteractionKind.LOCAL_REFRESH)

    def request_auxiliary(self, action: str) -> RoomInteractionContext | None:
        return self._start_user_operation(RoomInteractionKind.AUXILIARY_READ, action=action)

    def confirm_mutation(self, command: Any) -> RoomInteractionContext | None:
        # A confirmation dialog calls this only after explicit acceptance.
        return self._start_user_operation(RoomInteractionKind.MUTATION, command=command)

    def complete(
        self,
        context: RoomInteractionContext,
        *,
        success: bool,
        data: Any = None,
        connection_lost: bool = False,
        unconfirmed: bool = False,
        warning: str | None = None,
    ) -> None:
        """Accept an operation terminal callback only while its context is current."""
        if not self._is_current(context):
            return
        session = self._session
        assert session is not None
        row = session.row_for(context.record_id)
        if context.kind is RoomInteractionKind.LIVE and success:
            row.accepted_snapshot = data
            row.partial_data = None
            row.stale = False
            row.network_actions_enabled = True
            row.status = DeviceRowStatus.CONNECTED
            if warning:
                row.warnings.append(warning)
            self._notify()
            return
        if context.kind is RoomInteractionKind.MUTATION and success:
            # ACK is deliberately non-authoritative; reconciliation owns cache.
            reconciliation = self._replace_kind(context, RoomInteractionKind.RECONCILIATION)
            binding = self._binding_for(row)
            if binding is None or binding.reconciliation is None:
                self._block_unconfirmed(row, "Не удалось подтвердить состояние после команды")
                self._active = None
                self._notify()
                return
            binding.reconciliation(reconciliation, data)
            return
        if context.kind is RoomInteractionKind.RECONCILIATION and success:
            row.accepted_snapshot = data
            row.partial_data = None
            row.stale = False
            row.unconfirmed_after_command = False
            row.interaction_blocked = False
            row.network_actions_enabled = True
            row.status = DeviceRowStatus.CONNECTED
        elif context.kind is RoomInteractionKind.LOCAL_REFRESH and success:
            row.accepted_snapshot = data
            row.partial_data = None
            row.stale = False
            row.network_actions_enabled = True
            row.status = DeviceRowStatus.CONNECTED
        elif not success:
            if context.kind in {RoomInteractionKind.MUTATION, RoomInteractionKind.RECONCILIATION} or unconfirmed:
                self._block_unconfirmed(row, warning or "Состояние устройства не подтверждено")
            elif connection_lost or context.kind in {RoomInteractionKind.LOCAL_REFRESH, RoomInteractionKind.LIVE}:
                self._degrade(row, warning or "Соединение потеряно", failed=context.kind is RoomInteractionKind.LOCAL_REFRESH)
            elif warning:
                row.last_safe_operation_error = warning
        if warning and success:
            row.warnings.append(warning)
        self._finish_active(context)

    def child_window_closed(self, context: RoomInteractionContext) -> None:
        if context.kind is RoomInteractionKind.AUXILIARY_READ and self._is_current(context):
            self._retire_active()

    def cleanup_finished(self, context: RoomInteractionContext, *, timed_out: bool = False) -> None:
        if self._active != context:
            return
        if timed_out:
            session = self._session
            if session is not None:
                self._degrade(session.row_for(context.record_id), "Не удалось завершить соединение")
        self._active = None
        pending = self._pending_operation
        self._pending_operation = None
        if pending is not None:
            kind, action, command = pending
            self._start_user_operation(kind, action=action, command=command)
        else:
            self._start_eligible_live()
        self._notify()

    def invalidate(self, _reason: str = "superseded") -> None:
        self._generation += 1
        active = self._active
        self._active = None
        self._pending_live_record_id = None
        self._pending_operation = None
        if active is not None:
            binding = self._binding_for_context(active)
            if binding is not None and binding.cancel is not None:
                binding.cancel(active)

    def _start_user_operation(self, kind: RoomInteractionKind, *, action: str | None = None, command: Any = None) -> RoomInteractionContext | None:
        session = self._require_session()
        if (
            session is None
            or session.status not in {RoomCycleStatus.COMPLETE, RoomCycleStatus.COMPLETE_WITH_PROBLEMS}
            or session.expanded_record_id is None
        ):
            return None
        row = session.row_for(session.expanded_record_id)
        if not self._usable(row):
            return None
        if self._active is not None:
            if self._active.kind is RoomInteractionKind.LIVE:
                self._pending_live_record_id = None
                self._pending_operation = (kind, action, command)
                self._retire_active()
                # No user operation may acquire resources before cleanup.
            return None
        context = self._new_context(row, kind)
        binding = self._binding_for(row)
        callback = {
            RoomInteractionKind.LOCAL_REFRESH: None if binding is None else binding.local_refresh,
            RoomInteractionKind.AUXILIARY_READ: None if binding is None else binding.auxiliary,
            RoomInteractionKind.MUTATION: None if binding is None else binding.mutation,
        }[kind]
        if callback is None:
            return None
        self._active = context
        row.interaction_state = RoomInteractionState.ACTIVE
        row.network_actions_enabled = False
        self._notify()
        if kind is RoomInteractionKind.AUXILIARY_READ:
            callback(context, action or "")
        elif kind is RoomInteractionKind.MUTATION:
            callback(context, command)
        else:
            callback(context)
        return context

    def _start_eligible_live(self) -> None:
        session = self._require_session()
        if session is None or self._active is not None or session.expanded_record_id is None:
            return
        row = session.row_for(session.expanded_record_id)
        binding = self._binding_for(row)
        if not self._usable(row) or binding is None or binding.live is None:
            return
        context = self._new_context(row, RoomInteractionKind.LIVE)
        self._active = context
        row.interaction_state = RoomInteractionState.ACTIVE
        row.live_state = RoomLiveState.ACTIVE
        row.network_actions_enabled = False
        self._notify()
        binding.live(context)

    def _retire_active(self) -> None:
        context = self._active
        if context is None:
            return
        session = self._session
        if session is not None:
            row = session.row_for(context.record_id)
            row.operation_token += 1
            row.interaction_state = RoomInteractionState.RETIRING
            row.live_state = RoomLiveState.INACTIVE
        binding = self._binding_for_context(context)
        if binding is not None and binding.cancel is not None:
            binding.cancel(context)
        # Cleanup is asynchronous in production. A synchronous cleanup hook
        # remains useful for deterministic adapters and tests.
        if binding is not None and binding.cleanup is not None and binding.cleanup(context):
            self.cleanup_finished(context)
        self._notify()

    def _finish_active(self, context: RoomInteractionContext) -> None:
        if not self._is_current(context):
            return
        self._active = None
        session = self._session
        if session is not None:
            row = session.row_for(context.record_id)
            row.interaction_state = RoomInteractionState.IDLE
            row.live_state = RoomLiveState.INACTIVE
            if not row.interaction_blocked:
                row.network_actions_enabled = True
        self._start_eligible_live()
        self._notify()

    def _replace_kind(self, context: RoomInteractionContext, kind: RoomInteractionKind) -> RoomInteractionContext:
        replacement = RoomInteractionContext(
            context.inventory_snapshot_id, context.room_generation, context.record_id,
            context.diagnostic_model, context.ip_address, context.row_operation_token,
            context.interaction_generation, context.credential_context_revision, kind,
        )
        self._active = replacement
        return replacement

    def _new_context(self, row: DeviceRowState, kind: RoomInteractionKind) -> RoomInteractionContext:
        session = self._session
        assert session is not None and row.diagnostic_model is not None and row.ip_address is not None
        self._generation += 1
        row.operation_token += 1
        return RoomInteractionContext(
            session.identity.inventory_snapshot_id, session.identity.room_generation, row.record_id,
            row.diagnostic_model, row.ip_address, row.operation_token, self._generation,
            self._credential_context_revision(), kind,
        )

    def _is_current(self, context: RoomInteractionContext) -> bool:
        session = self._session
        if session is None or self._active != context or session.invalidated:
            return False
        try:
            row = session.row_for(context.record_id)
        except KeyError:
            return False
        return session.is_current(session.identity, row, context.row_operation_token)

    def _binding_for(self, row: DeviceRowState) -> RoomInteractionBindings | None:
        return self._bindings_for_model(row.diagnostic_model or "")

    def _binding_for_context(self, context: RoomInteractionContext) -> RoomInteractionBindings | None:
        return self._bindings_for_model(context.diagnostic_model)

    def _require_session(self) -> RoomDiagnosticSession | None:
        session = self._session
        if session is None or session.invalidated:
            return None
        return session

    @staticmethod
    def _usable(row: DeviceRowState) -> bool:
        return row.status is DeviceRowStatus.CONNECTED and not row.interaction_blocked and not row.stale

    def _degrade(self, row: DeviceRowState, reason: str, *, failed: bool = False) -> None:
        row.status = DeviceRowStatus.FAILED if failed else DeviceRowStatus.DEGRADED
        row.stale = row.accepted_snapshot is not None
        row.network_actions_enabled = False
        row.interaction_blocked = True
        row.last_safe_operation_error = reason
        session = self._session
        if session is not None:
            session.post_cycle_problem = True

    def _block_unconfirmed(self, row: DeviceRowState, reason: str) -> None:
        row.interaction_blocked = True
        row.unconfirmed_after_command = True
        row.stale = row.accepted_snapshot is not None
        row.network_actions_enabled = False
        row.interaction_state = RoomInteractionState.BLOCKED
        row.last_safe_operation_error = reason
        session = self._session
        if session is not None:
            session.post_cycle_problem = True

    def _notify(self) -> None:
        if self._changed is not None and self._session is not None and not self._session.invalidated:
            self._changed(self._session)
