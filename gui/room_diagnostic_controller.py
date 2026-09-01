"""Background owner for one automatic room diagnostic generation."""

from __future__ import annotations

import threading

from PyQt5.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal

from core.exceptions import AuthenticationError
from core.pdu import PDUOperationDescriptor, execute_pdu_command
from handlers.extron.in1804 import ExtronIN1804Handler
from core.room_interaction import RoomInteractionContext
from core.room_diagnostic_tree import (
    OneShotAttemptContext,
    OneShotEventKind,
    RoomCleanupPolicy,
    RoomDiagnosticOrchestrator,
    RoomDiagnosticSession,
    RoomDiagnosticSessionIdentity,
)
from gui.diagnostic_dispatch import dispatch_entry_for_model

from .room_one_shot_adapters import build_room_one_shot_adapters


class _RoomCycleSignals(QObject):
    updated = pyqtSignal(object)
    finished = pyqtSignal(object)


class _RoomCycleWorker(QRunnable):
    def __init__(self, controller: "RoomDiagnosticController", session: RoomDiagnosticSession):
        super().__init__()
        self.controller = controller
        self.session = session

    def run(self):
        self.controller._run_session(self.session)


class _RoomLocalRefreshWorker(QRunnable):
    def __init__(
        self,
        controller: "RoomDiagnosticController",
        context: RoomInteractionContext,
        cancelled: threading.Event,
        credential,
        candidate_index: int | None,
    ):
        super().__init__()
        self.controller = controller
        self.context = context
        self.cancelled = cancelled
        self.credential = credential
        self.candidate_index = candidate_index

    def run(self):
        self.controller._run_local_refresh(self.context, self.cancelled, self.credential, self.candidate_index)


class _RoomPDUMutationWorker(QRunnable):
    def __init__(self, controller, context, command, cancelled, credential, candidate_index):
        super().__init__()
        self.controller = controller
        self.context = context
        self.command = command
        self.cancelled = cancelled
        self.credential = credential
        self.candidate_index = candidate_index

    def run(self):
        self.controller._run_pdu_mutation(self.context, self.command, self.cancelled, self.credential, self.candidate_index)


class _RoomMatrixMutationWorker(QRunnable):
    def __init__(self, controller, context, command, cancelled, credential, candidate_index):
        super().__init__()
        self.controller, self.context, self.command = controller, context, command
        self.cancelled, self.credential, self.candidate_index = cancelled, credential, candidate_index

    def run(self):
        self.controller._run_matrix_mutation(self.context, self.command, self.cancelled, self.credential, self.candidate_index)


class RoomAuthenticationRejected:
    """Typed pre-delivery authentication result; never derived from text."""

    def __init__(self, candidate_index: int | None):
        self.candidate_index = candidate_index


class RoomDiagnosticController(QObject):
    """Runs one queue on a background lane and suppresses stale completions."""

    sessionFinished = pyqtSignal(object)
    sessionUpdated = pyqtSignal(object)
    localRefreshFinished = pyqtSignal(object, bool, object, bool, object)
    localRefreshCleanupFinished = pyqtSignal(object, bool)
    pduMutationFinished = pyqtSignal(object, bool, object, bool, object)
    matrixMutationFinished = pyqtSignal(object, bool, object, bool, object)

    def __init__(
        self,
        *,
        candidate_provider,
        ping,
        persist_success,
        starting_index,
        cleanup_policy: RoomCleanupPolicy | None = None,
        parent=None,
        thread_pool=None,
    ):
        super().__init__(parent)
        self._candidate_provider = candidate_provider
        self._ping = ping
        self._persist_success = persist_success
        self._starting_index = starting_index
        self._cleanup_policy = cleanup_policy or RoomCleanupPolicy()
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._active_session: RoomDiagnosticSession | None = None
        self._local_refresh_cancellations: dict[RoomInteractionContext, threading.Event] = {}
        self._pdu_mutation_cancellations: dict[RoomInteractionContext, threading.Event] = {}
        self._matrix_mutation_cancellations: dict[RoomInteractionContext, threading.Event] = {}
        self._signals = _RoomCycleSignals()
        self._signals.updated.connect(self._accept_update)
        self._signals.finished.connect(self._accept_finished)

    def start(self, session: RoomDiagnosticSession) -> None:
        self.supersede()
        self._active_session = session
        self._thread_pool.start(_RoomCycleWorker(self, session))

    def supersede(self) -> None:
        if self._active_session is not None:
            self._active_session.invalidate()
        self._active_session = None

    def start_local_refresh(self, context: RoomInteractionContext, *, credential=None, candidate_index: int | None = None) -> None:
        """Run one exact-row read-only refresh outside the automatic queue.

        The immutable interaction context is the sole target authority.  The
        worker receives neither a screen nor the global IP input.
        """
        cancelled = threading.Event()
        self._local_refresh_cancellations[context] = cancelled
        self._thread_pool.start(_RoomLocalRefreshWorker(self, context, cancelled, credential, candidate_index))

    def cancel_local_refresh(self, context: RoomInteractionContext) -> None:
        cancelled = self._local_refresh_cancellations.get(context)
        if cancelled is not None:
            cancelled.set()

    def start_pdu_mutation(self, context: RoomInteractionContext, command, *, credential=None, candidate_index: int | None = None) -> None:
        cancelled = threading.Event()
        self._pdu_mutation_cancellations[context] = cancelled
        self._thread_pool.start(_RoomPDUMutationWorker(self, context, command, cancelled, credential, candidate_index))

    def cancel_pdu_mutation(self, context: RoomInteractionContext) -> None:
        cancelled = self._pdu_mutation_cancellations.get(context)
        if cancelled is not None:
            cancelled.set()

    def start_matrix_mutation(self, context: RoomInteractionContext, command, *, credential=None, candidate_index: int | None = None) -> None:
        cancelled = threading.Event()
        self._matrix_mutation_cancellations[context] = cancelled
        self._thread_pool.start(_RoomMatrixMutationWorker(self, context, command, cancelled, credential, candidate_index))

    def cancel_matrix_mutation(self, context: RoomInteractionContext) -> None:
        cancelled = self._matrix_mutation_cancellations.get(context)
        if cancelled is not None:
            cancelled.set()

    def _run_matrix_mutation(self, context, command, cancelled, credential=None, candidate_index=None):
        """Perform exactly one room-bound Matrix route send off the GUI thread."""
        handler = None
        command_invoked = False
        try:
            entry = dispatch_entry_for_model(context.diagnostic_model)
            if entry is None or entry.mutation_binding_key != "matrix_room_route":
                raise ValueError("Matrix routing is unavailable")
            if not isinstance(command, dict) or command.get("output_num") != 1:
                raise ValueError("Некорректная команда Matrix")
            input_num = command.get("input_num")
            if not isinstance(input_num, int) or input_num < 1 or credential is None or cancelled.is_set():
                raise ValueError("Matrix route is not actionable")
            # The currentness gate precedes both handler acquisition and send.
            handler = ExtronIN1804Handler(context.ip_address, username=credential.get("username"), password=credential.get("password"))
            if cancelled.is_set():
                return
            try:
                handler.connect()
            except AuthenticationError:
                # A typed pre-send rejection may advance credentials only
                # after the old handler has crossed its real release boundary.
                handler.disconnect()
                handler = None
                if not cancelled.is_set():
                    self.matrixMutationFinished.emit(
                        context, False, RoomAuthenticationRejected(candidate_index), False, None
                    )
                return
            if cancelled.is_set():
                return
            # From this point a transport failure can follow delivery; never
            # treat it as a pre-delivery authentication retry opportunity.
            command_invoked = True
            handler.set_connection(1, input_num)
            if cancelled.is_set():
                return
            # The mutation owner must release the transport before its ACK can
            # advance the coordinator into read-only reconciliation.
            handler.disconnect()
            handler = None
            # ACK is deliberately not cache evidence; coordinator reconciles.
            self.matrixMutationFinished.emit(context, True, {"input_num": input_num}, False, None)
        except Exception:
            # Any error after an attempted send is ambiguous and cannot retry.
            message = "Состояние Matrix после команды не подтверждено" if command_invoked else "Не удалось выполнить коммутацию Matrix"
            self.matrixMutationFinished.emit(context, False, None, True, message)
        finally:
            if handler is not None:
                try:
                    handler.disconnect()
                except Exception:
                    pass

    def _run_pdu_mutation(self, context: RoomInteractionContext, command, cancelled: threading.Event, credential=None, candidate_index: int | None = None) -> None:
        if not isinstance(command, dict):
            self.pduMutationFinished.emit(context, False, None, True, "Некорректная команда PDU")
            return
        try:
            outlet_number = int(command["outlet_number"])
            operation = str(command["operation"])
            entry = dispatch_entry_for_model(context.diagnostic_model)
            if entry is None or entry.mutation_binding_key != "room_pdu_mutation":
                raise ValueError("PDU mutation is unavailable")
            if credential is None:
                raise ValueError("Credentials не настроены")
            descriptor = PDUOperationDescriptor(context.row_operation_token, context.room_generation, context.diagnostic_model, context.ip_address, operation, outlet_number=outlet_number, credential_index=(None if not credential else candidate_index))
            try:
                result = execute_pdu_command(descriptor=descriptor, credentials=credential, is_current=lambda _descriptor: not cancelled.is_set())
            except AuthenticationError:
                self.pduMutationFinished.emit(context, False, RoomAuthenticationRejected(candidate_index), False, None)
                return
            if cancelled.is_set() or result.get("_outcome") == "stale":
                self.localRefreshCleanupFinished.emit(context, False)
                return
            self.pduMutationFinished.emit(context, bool(result.get("success")), result, False, None)
        except Exception:
            # Any failure after a potential send is unconfirmed; the
            # coordinator blocks this exact row until a full room refresh.
            self.pduMutationFinished.emit(
                context, False, None, True, "Состояние PDU после команды не подтверждено"
            )

    def _run_local_refresh(self, context: RoomInteractionContext, cancelled: threading.Event, credential=None, candidate_index: int | None = None) -> None:
        entry = dispatch_entry_for_model(context.diagnostic_model)
        if entry is None or entry.local_refresh_binding_key != "room_one_shot_refresh":
            self.localRefreshFinished.emit(context, False, None, False, "Локальное обновление недоступно")
            return
        if credential is None:
            self.localRefreshFinished.emit(context, False, None, False, "Credentials не настроены")
            return
        try:
            reachable = bool(self._ping(context.ip_address))
        except Exception:
            reachable = False
        if not reachable:
            self.localRefreshFinished.emit(
                context, False, None, True, "Устройство недоступно"
            )
            return
        adapter = build_room_one_shot_adapters(self._cleanup_policy).get(entry.room_adapter_key)
        if adapter is None:
            self.localRefreshFinished.emit(
                context, False, None, False, "Диагностический адаптер недоступен"
            )
            return
        if cancelled.is_set():
            self.localRefreshCleanupFinished.emit(context, False)
            return
        attempt = OneShotAttemptContext(
                session_identity=RoomDiagnosticSessionIdentity(
                    context.inventory_snapshot_id,
                    context.room_generation,
                    context.ip_address,
                    context.record_id,
                    "",
                ),
                record_id=context.record_id,
                diagnostic_model=context.diagnostic_model,
                ip_address=context.ip_address,
                operation_token=context.row_operation_token,
                credential=credential,
                is_current=lambda: not cancelled.is_set(),
        )
        success_data = None
        success_warning = None
        authentication_failure = False
        cleanup_complete = False
        try:
            for event in adapter.run(attempt):
                if cancelled.is_set():
                    self.localRefreshCleanupFinished.emit(context, False)
                    return
                if event.kind in {
                        OneShotEventKind.USABLE_SUCCESS,
                        OneShotEventKind.USABLE_SUCCESS_WITH_WARNING,
                    }:
                        success_data = event.data
                        success_warning = event.warning
                elif event.kind is OneShotEventKind.TERMINAL_FAILURE:
                    authentication_failure = isinstance(event.data, AuthenticationError)
                    if not authentication_failure:
                        self.localRefreshFinished.emit(context, False, None, True, event.failure_reason)
                        return
                elif event.kind is OneShotEventKind.CLEANUP_COMPLETE:
                    cleanup_complete = True
                elif event.kind is OneShotEventKind.CLEANUP_TIMEOUT:
                    self.localRefreshFinished.emit(context, False, None, True, "Не удалось завершить соединение")
                    return
        except Exception:
            self.localRefreshFinished.emit(context, False, None, True, "Не удалось выполнить локальный опрос")
            return
        if cancelled.is_set():
            self.localRefreshCleanupFinished.emit(context, False)
            return
        if success_data is not None and cleanup_complete:
            self.localRefreshFinished.emit(context, True, success_data, False, success_warning)
            return
        if authentication_failure and cleanup_complete:
            self.localRefreshFinished.emit(context, False, RoomAuthenticationRejected(candidate_index), False, None)
            return
        self.localRefreshFinished.emit(context, False, None, True, "Не удалось выполнить локальный опрос")

    def forget_local_refresh(self, context: RoomInteractionContext) -> None:
        self._local_refresh_cancellations.pop(context, None)
        self._pdu_mutation_cancellations.pop(context, None)
        self._matrix_mutation_cancellations.pop(context, None)

    def _run_session(self, session: RoomDiagnosticSession) -> None:
        orchestrator = RoomDiagnosticOrchestrator(
            adapters=build_room_one_shot_adapters(self._cleanup_policy),
            credential_candidates=self._candidate_provider,
            ping=self._ping,
            persist_success=self._persist_success,
            starting_index=self._starting_index,
            on_update=self._signals.updated.emit,
        )
        self._signals.finished.emit(orchestrator.run(session))

    def _accept_finished(self, session: RoomDiagnosticSession) -> None:
        if session is not self._active_session or session.invalidated:
            return
        self._active_session = None
        self.sessionFinished.emit(session)

    def _accept_update(self, session: RoomDiagnosticSession) -> None:
        if session is self._active_session and not session.invalidated:
            self.sessionUpdated.emit(session)
