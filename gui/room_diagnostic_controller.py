"""Background owner for one automatic room diagnostic generation."""

from __future__ import annotations

import threading

from PyQt5.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal

from core.exceptions import AuthenticationError
from core.pdu import PDUOperationDescriptor, execute_pdu_command
from core.room_interaction import RoomInteractionContext
from core.room_diagnostic_tree import (
    OneShotAttemptContext,
    OneShotEventKind,
    RoomCleanupPolicy,
    RoomDiagnosticOrchestrator,
    RoomDiagnosticSession,
    RoomDiagnosticSessionIdentity,
)

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
    ):
        super().__init__()
        self.controller = controller
        self.context = context
        self.cancelled = cancelled

    def run(self):
        self.controller._run_local_refresh(self.context, self.cancelled)


class _RoomPDUMutationWorker(QRunnable):
    def __init__(self, controller, context, command, cancelled):
        super().__init__()
        self.controller = controller
        self.context = context
        self.command = command
        self.cancelled = cancelled

    def run(self):
        self.controller._run_pdu_mutation(self.context, self.command, self.cancelled)


class RoomDiagnosticController(QObject):
    """Runs one queue on a background lane and suppresses stale completions."""

    sessionFinished = pyqtSignal(object)
    sessionUpdated = pyqtSignal(object)
    localRefreshFinished = pyqtSignal(object, bool, object, bool, object)
    localRefreshCleanupFinished = pyqtSignal(object, bool)
    pduMutationFinished = pyqtSignal(object, bool, object, bool, object)

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

    def start_local_refresh(self, context: RoomInteractionContext) -> None:
        """Run one exact-row read-only refresh outside the automatic queue.

        The immutable interaction context is the sole target authority.  The
        worker receives neither a screen nor the global IP input.
        """
        cancelled = threading.Event()
        self._local_refresh_cancellations[context] = cancelled
        self._thread_pool.start(_RoomLocalRefreshWorker(self, context, cancelled))

    def cancel_local_refresh(self, context: RoomInteractionContext) -> None:
        cancelled = self._local_refresh_cancellations.get(context)
        if cancelled is not None:
            cancelled.set()

    def start_pdu_mutation(self, context: RoomInteractionContext, command) -> None:
        cancelled = threading.Event()
        self._pdu_mutation_cancellations[context] = cancelled
        self._thread_pool.start(_RoomPDUMutationWorker(self, context, command, cancelled))

    def cancel_pdu_mutation(self, context: RoomInteractionContext) -> None:
        cancelled = self._pdu_mutation_cancellations.get(context)
        if cancelled is not None:
            cancelled.set()

    def _run_pdu_mutation(self, context: RoomInteractionContext, command, cancelled: threading.Event) -> None:
        if not isinstance(command, dict):
            self.pduMutationFinished.emit(context, False, None, True, "Некорректная команда PDU")
            return
        try:
            outlet_number = int(command["outlet_number"])
            operation = str(command["operation"])
            candidates = tuple(self._candidate_provider(context.diagnostic_model, context.ip_address) or ())
            if not candidates and context.diagnostic_model in _CREDENTIALLESS_ROOM_MODELS:
                candidates = ({},)
            if not candidates:
                raise ValueError("Credentials не настроены")
            index = max(0, min(
                self._starting_index(context.diagnostic_model, context.ip_address, candidates),
                len(candidates) - 1,
            ))
            result = None
            for candidate_index in range(index, len(candidates)):
                descriptor = PDUOperationDescriptor(
                    context.row_operation_token,
                    context.room_generation,
                    context.diagnostic_model,
                    context.ip_address,
                    operation,
                    outlet_number=outlet_number,
                    credential_index=(
                        None if not candidates[candidate_index] else candidate_index
                    ),
                )
                try:
                    result = execute_pdu_command(
                        descriptor=descriptor,
                        credentials=candidates[candidate_index],
                        is_current=lambda _descriptor: not cancelled.is_set(),
                    )
                    break
                except AuthenticationError:
                    # ``execute_pdu_command`` re-raises AuthenticationError
                    # only before its tracked state-changing send.  Any auth
                    # error after send is converted to an indeterminate
                    # outcome there and deliberately reaches the outer
                    # failure path instead of authorizing a retry.
                    if candidate_index + 1 >= len(candidates):
                        raise
            if result is None:
                raise AuthenticationError("PDU credentials rejected before command")
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

    def _run_local_refresh(
        self,
        context: RoomInteractionContext,
        cancelled: threading.Event,
    ) -> None:
        try:
            candidates = tuple(
                self._candidate_provider(context.diagnostic_model, context.ip_address) or ()
            )
        except Exception:
            candidates = ()
        if not candidates:
            # Credentialless models are represented by an explicit empty map;
            # credential-required models fail safely without worker acquisition.
            if context.diagnostic_model not in _CREDENTIALLESS_ROOM_MODELS:
                self.localRefreshFinished.emit(
                    context, False, None, False, "Credentials не настроены"
                )
                return
            candidates = ({},)
        try:
            reachable = bool(self._ping(context.ip_address))
        except Exception:
            reachable = False
        if not reachable:
            self.localRefreshFinished.emit(
                context, False, None, True, "Устройство недоступно"
            )
            return
        adapter_key = _ROOM_ADAPTER_KEY_BY_MODEL.get(context.diagnostic_model)
        adapter = build_room_one_shot_adapters(self._cleanup_policy).get(adapter_key)
        if adapter is None:
            self.localRefreshFinished.emit(
                context, False, None, False, "Диагностический адаптер недоступен"
            )
            return
        start = max(0, min(
            self._starting_index(context.diagnostic_model, context.ip_address, candidates),
            len(candidates) - 1,
        ))
        for candidate_index in range(start, len(candidates)):
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
                credential=candidates[candidate_index],
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
                            self.localRefreshFinished.emit(
                                context, False, None, True, event.failure_reason
                            )
                            return
                    elif event.kind is OneShotEventKind.CLEANUP_COMPLETE:
                        cleanup_complete = True
                    elif event.kind is OneShotEventKind.CLEANUP_TIMEOUT:
                        self.localRefreshFinished.emit(
                            context, False, None, True, "Не удалось завершить соединение"
                        )
                        return
            except Exception:
                self.localRefreshFinished.emit(
                    context, False, None, True, "Не удалось выполнить локальный опрос"
                )
                return
            if cancelled.is_set():
                self.localRefreshCleanupFinished.emit(context, False)
                return
            if success_data is not None and cleanup_complete:
                self.localRefreshFinished.emit(
                    context, True, success_data, False, success_warning
                )
                return
            if authentication_failure and cleanup_complete and candidate_index + 1 < len(candidates):
                continue
            self.localRefreshFinished.emit(
                context, False, None, True, "Не удалось выполнить локальный опрос"
            )
            return

    def forget_local_refresh(self, context: RoomInteractionContext) -> None:
        self._local_refresh_cancellations.pop(context, None)
        self._pdu_mutation_cancellations.pop(context, None)

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


_ROOM_ADAPTER_KEY_BY_MODEL = {
    "Huawei TE20": "codec_one_shot",
    "Huawei TE40": "codec_one_shot",
    "CloudLink Bar 310": "codec_one_shot",
    "CloudLink Box 310": "codec_one_shot",
    "Polycom RPG 310": "polycom_one_shot",
    "Extron IN1804": "matrix_one_shot",
    "Aten PE8208AV": "pdu_one_shot",
    "Extron IPL T PCS4i": "pdu_one_shot",
    "Biamp Tesira Forte CI": "biamp_one_shot",
    "Extron DMP 64 Plus": "dmp_one_shot",
}
_CREDENTIALLESS_ROOM_MODELS = frozenset({"Extron IPL T PCS4i"})
