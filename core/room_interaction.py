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
from core.call_activity import normalize_call_activity


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


@dataclass(frozen=True)
class _PendingCodecPreview:
    """Automatic preview admission bound to one immutable expansion identity."""

    session_identity: Any
    record_id: str
    expansion_epoch: int


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
        self._pending_codec_preview: _PendingCodecPreview | None = None
        self._pending_global_refresh: Callable[[], None] | None = None
        self._expanded_record_id: str | None = None
        self._codec_preview_epochs: dict[str, int] = {}
        self._codec_preview_attempts: set[tuple[Any, str, int]] = set()

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
        pending_kind = self._pending_operation[0] if self._pending_operation else None
        return pending_kind in {
            RoomInteractionKind.LOCAL_REFRESH,
            RoomInteractionKind.AUXILIARY_READ,
            RoomInteractionKind.MUTATION,
            RoomInteractionKind.RECONCILIATION,
        } or (self._active is not None and self._active.kind in {
            RoomInteractionKind.LOCAL_REFRESH,
            RoomInteractionKind.AUXILIARY_READ,
            RoomInteractionKind.MUTATION,
            RoomInteractionKind.RECONCILIATION,
        })

    @property
    def ui_lock_kind(self) -> RoomInteractionKind:
        """Accepted intent is UI authority even while old LIVE is retiring."""
        if self._pending_operation is not None:
            return self._pending_operation[0]
        return self._active.kind if self._active is not None else RoomInteractionKind.IDLE

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

    def accepts_context(self, context: RoomInteractionContext) -> bool:
        """Public currentness boundary for composition-owned success evidence."""
        return self._is_current(context)

    def block_ambiguous_mutation(self, context: RoomInteractionContext, reason: str) -> bool:
        """Fail closed for a retiring mutation whose submitted command is ambiguous."""
        if self._active != context or self._session is None:
            return False
        try:
            row = self._session.row_for(context.record_id)
        except KeyError:
            return False
        self._block_unconfirmed(row, reason)
        self._notify()
        return True

    def is_bound_session(self, session: RoomDiagnosticSession) -> bool:
        """Whether composition still owns this exact, current room session."""
        return self._session is session and not session.invalidated

    def bind_session(self, session: RoomDiagnosticSession | None) -> None:
        self.invalidate("room_session_changed")
        self._session = session
        self._expanded_record_id = None
        self._codec_preview_epochs.clear()
        self._codec_preview_attempts.clear()
        self._pending_codec_preview = None

    def cycle_finished(self, session: RoomDiagnosticSession) -> None:
        if session is not self._session or session.invalidated:
            return
        self._start_eligible_live()
        self._maybe_start_codec_preview()

    def expand(self, record_id: str) -> None:
        session = self._require_session()
        if session is None:
            return
        session.expanded_record_id = record_id
        if self._expanded_record_id != record_id:
            self._expanded_record_id = record_id
            self._codec_preview_epochs[record_id] = self._codec_preview_epochs.get(record_id, 0) + 1
        self._discard_stale_pending_codec_preview()
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
        self._expanded_record_id = None
        self._pending_live_record_id = None
        self._pending_operation = None
        self._pending_codec_preview = None
        if self._active is not None and self._active.record_id == record_id:
            self._retire_active()
        self._notify()

    def request_local_refresh(self) -> RoomInteractionContext | None:
        return self._start_user_operation(RoomInteractionKind.LOCAL_REFRESH)

    def request_auxiliary(self, action: str) -> RoomInteractionContext | None:
        return self._start_user_operation(RoomInteractionKind.AUXILIARY_READ, action=action)

    def confirm_mutation(
        self,
        command: Any,
        *,
        expected_session_identity: RoomDiagnosticSessionIdentity | None = None,
        expected_record_id: str | None = None,
        expected_row_token: int | None = None,
    ) -> RoomInteractionContext | None:
        """Admit a confirmed mutation only while optional exact-row proof holds."""
        if any(value is not None for value in (expected_session_identity, expected_record_id, expected_row_token)):
            session = self._require_session()
            if session is None or session.identity != expected_session_identity:
                return None
            if session.expanded_record_id != expected_record_id:
                return None
            try:
                row = session.row_for(expected_record_id)
            except KeyError:
                return None
            if expected_row_token is None or not session.is_current(session.identity, row, expected_row_token):
                return None
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
            row.call_activity = normalize_call_activity(row.capability.call_activity_binding_key if row.capability else None, data)
            row.partial_data = None
            row.stale = False
            row.network_actions_enabled = True
            row.status = DeviceRowStatus.CONNECTED
            if warning:
                row.warnings.append(warning)
            self._notify()
            return
        if (
            context.kind is RoomInteractionKind.MUTATION
            and success
            and isinstance(data, dict)
            and isinstance(data.get("_room_codec_confirmed"), dict)
        ):
            # Codec mutations publish only their targeted authoritative
            # getter result. Do not replace unrelated accepted diagnostics.
            snapshot = dict(row.accepted_snapshot or {})
            snapshot.update(data["_room_codec_confirmed"])
            row.accepted_snapshot = snapshot
            row.partial_data = None
            row.stale = False
            row.unconfirmed_after_command = False
            row.interaction_blocked = False
            row.network_actions_enabled = True
            row.status = DeviceRowStatus.CONNECTED
        elif context.kind is RoomInteractionKind.MUTATION and success:
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
            row.call_activity = normalize_call_activity(row.capability.call_activity_binding_key if row.capability else None, data)
            row.partial_data = None
            row.stale = False
            row.unconfirmed_after_command = False
            row.interaction_blocked = False
            row.network_actions_enabled = True
            row.status = DeviceRowStatus.CONNECTED
        elif context.kind is RoomInteractionKind.LOCAL_REFRESH and success:
            row.accepted_snapshot = data
            row.call_activity = normalize_call_activity(row.capability.call_activity_binding_key if row.capability else None, data)
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
        if context.kind is RoomInteractionKind.LIVE and not success:
            # A terminal live outcome still owns model resources.  Keep the
            # serialized lane retiring until composition reports their real
            # release or bounded abandonment.
            self._retire_active()
            return
        if warning and success:
            row.warnings.append(warning)
        self._finish_active(context)

    def child_window_closed(self, context: RoomInteractionContext) -> None:
        if context.kind is RoomInteractionKind.AUXILIARY_READ and self._is_current(context):
            self._retire_active()

    def cleanup_finished(self, context: RoomInteractionContext, *, timed_out: bool = False) -> None:
        if self._active != context:
            return
        row = None
        session = self._session
        if session is not None:
            row = session.row_for(context.record_id)
        if timed_out:
            if row is not None:
                self._degrade(row, "Не удалось завершить соединение")
        if row is not None:
            row.live_state = RoomLiveState.INACTIVE
            if row.interaction_blocked:
                row.interaction_state = RoomInteractionState.BLOCKED
                row.network_actions_enabled = False
            else:
                row.interaction_state = RoomInteractionState.IDLE
                row.network_actions_enabled = self._usable(row)
        self._active = None
        global_refresh = self._pending_global_refresh
        self._pending_global_refresh = None
        if global_refresh is not None:
            self._pending_operation = None
            self._pending_live_record_id = None
            self._notify()
            global_refresh()
            return
        pending = self._pending_operation
        self._pending_operation = None
        if pending is not None:
            kind, action, command = pending
            if kind is RoomInteractionKind.AUXILIARY_READ and action == "call_log_preview":
                self._start_pending_codec_preview()
            else:
                self._start_user_operation(kind, action=action, command=command)
        elif self._pending_codec_preview is not None:
            self._start_pending_codec_preview()
        else:
            self._start_eligible_live()
        self._notify()

    def defer_global_refresh(self, callback: Callable[[], None]) -> bool:
        """Retire read-only authority before beginning a new room cycle.

        The callback is deliberately invoked only from ``cleanup_finished``.
        This makes top Refresh a non-blocking supersession boundary rather than
        permitting a new room worker to overlap a still-closing child session.
        """
        if self._active is None or self._active.kind not in {
            RoomInteractionKind.AUXILIARY_READ,
            RoomInteractionKind.LIVE,
        }:
            return False
        self._pending_global_refresh = callback
        self._pending_operation = None
        self._pending_live_record_id = None
        self._retire_active()
        return True

    def invalidate(self, _reason: str = "superseded") -> None:
        self._generation += 1
        active = self._active
        self._active = None
        self._pending_live_record_id = None
        self._pending_operation = None
        self._pending_codec_preview = None
        self._pending_global_refresh = None
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
                # Automatic preview work has its own immutable pending
                # authority.  Mirroring it into the generic user-operation
                # slot would let a stale marker consume cleanup handoff after
                # its row/epoch identity has been discarded.
                if not (
                    kind is RoomInteractionKind.AUXILIARY_READ
                    and action == "call_log_preview"
                ):
                    self._pending_operation = (kind, action, command)
                self._retire_active()
                # No user operation may acquire resources before cleanup.
            elif kind is RoomInteractionKind.AUXILIARY_READ and action == "call_log_preview":
                # A mandatory automatic preview remains application-owned
                # pending work while another serialized operation owns the lane.
                # The immutable admission identity was established before this
                # generic operation entry point.  Do not rebind it to the
                # currently expanded row while the lane is retiring.
                pass
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
        if kind is RoomInteractionKind.AUXILIARY_READ and action == "call_log_preview":
            self._pending_codec_preview = None
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

    def _maybe_start_codec_preview(self) -> None:
        """Admit exactly one automatic preview for a real expansion epoch."""
        session = self._require_session()
        record_id = self._expanded_record_id
        if (
            session is None
            or record_id is None
            or session.status not in {RoomCycleStatus.COMPLETE, RoomCycleStatus.COMPLETE_WITH_PROBLEMS}
        ):
            return
        row = session.row_for(record_id)
        binding = self._binding_for(row)
        if (
            not self._usable(row)
            or row.capability is None
            or row.capability.screen_key != "codec"
            or binding is None
            or binding.auxiliary is None
        ):
            return
        epoch = self._codec_preview_epochs.get(record_id)
        if epoch is None:
            return
        key = (session.identity, record_id, epoch)
        if key in self._codec_preview_attempts:
            return
        # Claim before publication. Render/theme/resize cannot create a
        # second attempt even if it ends with a local unavailable outcome.
        self._codec_preview_attempts.add(key)
        # Preview evidence is presentation-local, but only an accepted
        # same-row snapshot may complete this epoch without a lane owner.
        if getattr(row, "call_log_preview_snapshot", None) is not None:
            self._notify()
            return
        # LIVE owns priority over automatic enrichment.  It is deliberately
        # not retired or queued behind: this completes the epoch locally.
        if self._active is not None and self._active.kind is RoomInteractionKind.LIVE:
            self._notify()
            return
        # A live-capable expanded row is eligible ahead of preview even if a
        # caller reaches this bridge before the live start callback.
        if binding.live is not None:
            self._start_eligible_live()
            if self._active is not None and self._active.kind is RoomInteractionKind.LIVE:
                self._notify()
                return
        self._pending_codec_preview = _PendingCodecPreview(
            session.identity, record_id, epoch
        )
        self._start_pending_codec_preview()

    def request_codec_preview(self) -> None:
        """Presentation event bridge; no renderer may call this implicitly."""
        self._maybe_start_codec_preview()

    def _pending_codec_preview_is_current(self, pending: _PendingCodecPreview) -> bool:
        """Verify delayed automatic work against the original expansion."""
        session = self._require_session()
        if (
            session is None
            or session.identity != pending.session_identity
            or session.expanded_record_id != pending.record_id
            or self._expanded_record_id != pending.record_id
            or self._codec_preview_epochs.get(pending.record_id) != pending.expansion_epoch
        ):
            return False
        try:
            row = session.row_for(pending.record_id)
        except KeyError:
            return False
        binding = self._binding_for(row)
        return bool(
            self._usable(row)
            and row.capability is not None
            and row.capability.screen_key == "codec"
            and binding is not None
            and binding.auxiliary is not None
        )

    def _discard_stale_pending_codec_preview(self) -> None:
        pending = self._pending_codec_preview
        if pending is not None and not self._pending_codec_preview_is_current(pending):
            self._pending_codec_preview = None

    def _start_pending_codec_preview(self) -> None:
        pending = self._pending_codec_preview
        if pending is None:
            return
        if not self._pending_codec_preview_is_current(pending):
            self._pending_codec_preview = None
            self._start_eligible_live()
            return
        # A preview deferred behind another serialized owner must check LIVE
        # again after cleanup: it can become eligible only at this boundary.
        session = self._require_session()
        assert session is not None
        row = session.row_for(pending.record_id)
        binding = self._binding_for(row)
        if binding is not None and binding.live is not None:
            self._start_eligible_live()
            if self._active is not None and self._active.kind is RoomInteractionKind.LIVE:
                # This epoch is terminal locally and owns no preview I/O.
                self._pending_codec_preview = None
                self._notify()
                return
        self._start_user_operation(RoomInteractionKind.AUXILIARY_READ, action="call_log_preview")

    def _retire_active(self) -> None:
        context = self._active
        if context is None:
            return
        session = self._session
        if session is not None:
            row = session.row_for(context.record_id)
            if row.interaction_state is RoomInteractionState.RETIRING:
                self._notify()
                return
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
        pending = self._pending_operation
        self._pending_operation = None
        if pending is not None:
            kind, action, command = pending
            if kind is RoomInteractionKind.AUXILIARY_READ and action == "call_log_preview":
                self._start_pending_codec_preview()
            else:
                self._start_user_operation(kind, action=action, command=command)
        elif self._pending_codec_preview is not None:
            self._start_pending_codec_preview()
        else:
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
