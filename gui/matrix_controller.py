"""Matrix-specific application lifecycle controller."""

from __future__ import annotations

from dataclasses import dataclass
import itertools
import threading
from typing import Callable, Iterable, Optional

from PyQt5.QtCore import QObject, QRunnable, QThreadPool, QTimer, pyqtSignal, pyqtSlot

from core.exceptions import classify_matrix_failure
from core.parser import ExtronIN1804DataParser
from core.redaction import redact_data, redacted_callback
from core.workers.common import _safe_error
from handlers.extron.in1804 import ExtronIN1804Handler


MATRIX_DEVICE_NAME = "Extron IN1804"


@dataclass(frozen=True)
class MatrixOperationContext:
    model: str
    ip_address: str
    operation_kind: str
    generation: int
    operation_id: int
    expected_operation_id: int
    credential_context_revision: int
    candidate_index: Optional[int] = None
    output_num: Optional[int] = None
    input_num: Optional[int] = None
    state_changing: bool = False


@dataclass(frozen=True)
class MatrixSessionIdentity:
    model: str
    ip_address: str
    protocol: str
    port: int
    credential_context_revision: int
    candidate_index: int


class MatrixOperationHandle:
    """Public, secret-free object used by existing MainWindow callbacks."""

    def __init__(self, context: MatrixOperationContext):
        self.device_name = context.model
        self.ip_address = context.ip_address
        self.current_idx = context.candidate_index or 0
        self.matrix_context = context
        self.matrix_operation_id = context.operation_id
        self.creds_list = ()


class MatrixOperationSignals(QObject):
    result = pyqtSignal(object, dict)
    error = pyqtSignal(object, tuple)
    progress = pyqtSignal(object, int)
    status = pyqtSignal(object, str)
    terminal_log = pyqtSignal(object, str)
    finished = pyqtSignal(object)


class MatrixBackgroundOperation(QRunnable):
    def __init__(self, controller: "MatrixController", context: MatrixOperationContext):
        super().__init__()
        self.controller = controller
        self.context = context

    @pyqtSlot()
    def run(self):
        self.controller._run_background_operation(self.context)


class MatrixController(QObject):
    """Owns Matrix refresh, route, persistent session, and stale suppression."""

    resultAccepted = pyqtSignal(dict, object)
    errorAccepted = pyqtSignal(tuple, object)
    progressAccepted = pyqtSignal(int, object)
    statusAccepted = pyqtSignal(str, object)
    terminalAccepted = pyqtSignal(str, object)
    finishedAccepted = pyqtSignal(object)
    routeAccepted = pyqtSignal(int)
    routeError = pyqtSignal(str)

    def __init__(
        self,
        *,
        context_provider: Callable[[], tuple[str, str]],
        credential_candidates_provider: Callable[[str, str], Iterable[dict]],
        credential_index_provider: Callable[[str, str, Iterable[dict]], int],
        credential_advance_provider: Callable[
            [str, str, Iterable[dict], int, int], Optional[int]
        ],
        credential_revision_provider: Callable[[], int],
        thread_pool: Optional[QThreadPool] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._context_provider = context_provider
        self._credential_candidates_provider = credential_candidates_provider
        self._credential_index_provider = credential_index_provider
        self._credential_advance_provider = credential_advance_provider
        self._credential_revision_provider = credential_revision_provider
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._operation_serial = itertools.count(1)
        self._generation = 0
        self._active_context: Optional[MatrixOperationContext] = None
        self._last_model = MATRIX_DEVICE_NAME
        self._last_ip = ""
        self._last_credential_revision = self._credential_revision()
        self._session_lock = threading.RLock()
        self._session_identity: Optional[MatrixSessionIdentity] = None
        self._session_handler = None
        self._signals = MatrixOperationSignals()
        self._signals.result.connect(self._on_result)
        self._signals.error.connect(self._on_error)
        self._signals.progress.connect(self._on_progress)
        self._signals.status.connect(self._on_status)
        self._signals.terminal_log.connect(self._on_terminal)
        self._signals.finished.connect(self._on_finished)

        self._keepalive_timer = QTimer(self)
        self._keepalive_timer.setInterval(15000)
        self._keepalive_timer.timeout.connect(self.request_keepalive)

    def invalidate_context(self):
        self._generation += 1
        self._active_context = None
        self._stop_keepalive()
        self._release_session_background()

    def shutdown(self):
        self.invalidate_context()

    def request_full_refresh(self, ip_address: str, candidates, candidate_index: int):
        self._last_model = MATRIX_DEVICE_NAME
        self._last_ip = ip_address
        context = self._make_context(
            operation_kind="full_refresh",
            ip_address=ip_address,
            candidate_index=candidate_index,
            state_changing=False,
        )
        self._submit(context)

    def request_route(self, output_num: int, input_num: int):
        model, ip_address = self._context_provider()
        candidates = tuple(self._credential_candidates_provider(model, ip_address) or ())
        if not candidates:
            self.routeError.emit("Нет credentials для Extron IN1804")
            return
        candidate_index = self._credential_index_provider(model, ip_address, candidates)
        if candidate_index < 0 or candidate_index >= len(candidates):
            candidate_index = 0
        context = self._make_context(
            operation_kind="route",
            ip_address=ip_address,
            candidate_index=candidate_index,
            output_num=output_num,
            input_num=input_num,
            state_changing=True,
        )
        self._submit(context)

    def request_status_refresh(self):
        model, ip_address = self._context_provider()
        candidates = tuple(self._credential_candidates_provider(model, ip_address) or ())
        if not candidates:
            return
        candidate_index = self._credential_index_provider(model, ip_address, candidates)
        if candidate_index < 0 or candidate_index >= len(candidates):
            candidate_index = 0
        context = self._make_context(
            operation_kind="quick_refresh",
            ip_address=ip_address,
            candidate_index=candidate_index,
            state_changing=False,
        )
        self._submit(context)

    @pyqtSlot()
    def request_keepalive(self):
        if self._active_context is not None:
            return
        with self._session_lock:
            identity = self._session_identity
            handler = self._session_handler
        if identity is None or handler is None:
            self._stop_keepalive()
            return
        context = self._make_context(
            operation_kind="keepalive",
            ip_address=identity.ip_address,
            candidate_index=identity.candidate_index,
            state_changing=False,
            reuse_generation=self._generation,
        )
        self._submit(context)

    def _credential_revision(self) -> int:
        revision = self._credential_revision_provider()
        return int(revision or 0)

    def _make_context(
        self,
        *,
        operation_kind: str,
        ip_address: str,
        candidate_index: Optional[int],
        output_num: Optional[int] = None,
        input_num: Optional[int] = None,
        state_changing: bool,
        reuse_generation: Optional[int] = None,
    ) -> MatrixOperationContext:
        model = MATRIX_DEVICE_NAME
        revision = self._credential_revision()
        if reuse_generation is None:
            self._generation += 1
            generation = self._generation
        else:
            generation = reuse_generation
        operation_id = next(self._operation_serial)
        context = MatrixOperationContext(
            model=model,
            ip_address=ip_address,
            operation_kind=operation_kind,
            generation=generation,
            operation_id=operation_id,
            expected_operation_id=operation_id,
            credential_context_revision=revision,
            candidate_index=candidate_index,
            output_num=output_num,
            input_num=input_num,
            state_changing=state_changing,
        )
        if (
            self._last_ip
            and (
                self._last_ip != ip_address
                or self._last_credential_revision != revision
            )
        ):
            self._release_session_background()
        self._last_ip = ip_address
        self._last_credential_revision = revision
        self._active_context = context
        return context

    def _submit(self, context: MatrixOperationContext):
        self._thread_pool.start(MatrixBackgroundOperation(self, context))

    def _run_background_operation(self, context: MatrixOperationContext):
        secrets = self._candidate_secrets(context)
        route_command_invoked = False
        try:
            if context.operation_kind == "full_refresh":
                self._signals.status.emit(context, "Подключение к матрице Extron IN1804...")
                self._signals.progress.emit(context, 10)
                handler = self._acquire_session(context, secrets)
                self._signals.status.emit(context, "Получение информации об устройстве...")
                self._signals.progress.emit(context, 30)
                status = handler.get_full_status()
                parser = ExtronIN1804DataParser()
                data = parser.parse(status)
                data["ip_address"] = context.ip_address
                data["_matrix_credential_success_candidate"] = context.candidate_index
                self._signals.progress.emit(context, 100)
                self._signals.status.emit(context, "Готово!")
                self._signals.result.emit(context, redact_data(data, secrets))
            elif context.operation_kind == "route":
                handler = self._acquire_session(context, secrets)
                route_command_invoked = True
                handler.set_connection(context.output_num, context.input_num)
                self._signals.result.emit(context, {"route_input": context.input_num})
            elif context.operation_kind == "quick_refresh":
                handler = self._acquire_session(context, secrets)
                connections = handler.get_connections()
                current = connections[0] if connections else None
                self._signals.result.emit(context, {"current_connection": current})
            elif context.operation_kind == "keepalive":
                with self._session_lock:
                    handler = self._session_handler
                if handler is None or not handler.is_connected():
                    raise RuntimeError("keepalive failed")
                original_log_callback = handler.log_callback
                try:
                    handler.log_callback = None
                    result = handler.send_command("w20STAT")
                    if not result or not result.get("success"):
                        raise RuntimeError("keepalive failed")
                finally:
                    handler.log_callback = original_log_callback
                self._signals.result.emit(context, {"keepalive": True})
        except Exception as error:
            message, details = _safe_error(error, secrets)
            category = classify_matrix_failure(error).value
            if (
                context.operation_kind == "route"
                and route_command_invoked
                and category == "authentication_error"
            ):
                category = "unknown_command_outcome"
            self._signals.error.emit(context, (category, message, details))
        finally:
            self._signals.finished.emit(context)

    def _candidate_secrets(self, context: MatrixOperationContext):
        candidate = self._candidate_for_context(context)
        if not isinstance(candidate, dict):
            return ()
        return tuple(value for value in candidate.values() if value)

    def _candidate_for_context(self, context: MatrixOperationContext):
        if context.candidate_index is None:
            return None
        candidates = tuple(
            self._credential_candidates_provider(context.model, context.ip_address)
            or ()
        )
        if context.candidate_index < 0 or context.candidate_index >= len(candidates):
            return None
        return candidates[context.candidate_index]

    def _acquire_session(self, context: MatrixOperationContext, secrets):
        candidate = self._candidate_for_context(context)
        if not isinstance(candidate, dict):
            raise RuntimeError("Нет credentials для Extron IN1804")
        identity = MatrixSessionIdentity(
            model=context.model,
            ip_address=context.ip_address,
            protocol="auto",
            port=22023,
            credential_context_revision=context.credential_context_revision,
            candidate_index=context.candidate_index,
        )
        with self._session_lock:
            if (
                self._session_identity == identity
                and self._session_handler is not None
                and self._session_handler.is_connected()
            ):
                return self._session_handler

            self._disconnect_locked()
            handler = ExtronIN1804Handler(
                ip_address=context.ip_address,
                port=22023,
                username=candidate.get("username", ""),
                password=candidate.get("password", ""),
            )
            handler.log_callback = redacted_callback(
                lambda message: self._signals.terminal_log.emit(context, message),
                secrets,
            )
            handler.connect()
            self._session_identity = identity
            self._session_handler = handler
            self._keepalive_timer.start()
            return handler

    def _release_session_background(self):
        with self._session_lock:
            handler = self._session_handler
            self._session_handler = None
            self._session_identity = None
        if handler is not None:
            context = self._make_cleanup_context()
            self._thread_pool.start(_MatrixCleanupOperation(self, context, handler))

    def _make_cleanup_context(self):
        operation_id = next(self._operation_serial)
        return MatrixOperationContext(
            model=MATRIX_DEVICE_NAME,
            ip_address=self._last_ip,
            operation_kind="cleanup",
            generation=self._generation,
            operation_id=operation_id,
            expected_operation_id=operation_id,
            credential_context_revision=self._last_credential_revision,
        )

    def _disconnect_locked(self):
        if self._session_handler is not None:
            try:
                self._session_handler.disconnect()
            except Exception:
                pass
        self._session_handler = None
        self._session_identity = None
        self._stop_keepalive()

    def _stop_keepalive(self):
        if self._keepalive_timer.isActive():
            self._keepalive_timer.stop()

    def _is_current(self, context: MatrixOperationContext) -> bool:
        current = self._active_context
        if current is None and context.operation_kind in {"keepalive", "cleanup"}:
            return context.generation == self._generation
        return (
            current is not None
            and current.generation == context.generation
            and current.expected_operation_id == context.expected_operation_id
            and current.model == context.model
            and current.ip_address == context.ip_address
            and current.credential_context_revision
            == context.credential_context_revision
            and current.candidate_index == context.candidate_index
        )

    def _handle(self, context: MatrixOperationContext) -> MatrixOperationHandle:
        return MatrixOperationHandle(context)

    def _on_result(self, context: MatrixOperationContext, data: dict):
        if not self._is_current(context):
            return
        if context.operation_kind == "route":
            self.routeAccepted.emit(context.input_num or 1)
            follow_up = self._make_context(
                operation_kind="quick_refresh",
                ip_address=context.ip_address,
                candidate_index=context.candidate_index,
                state_changing=False,
                reuse_generation=context.generation,
            )
            self._submit(follow_up)
            return
        if context.operation_kind == "quick_refresh":
            current = data.get("current_connection")
            if current is not None:
                self.routeAccepted.emit(current)
            return
        if context.operation_kind == "keepalive":
            self._active_context = None
            return
        self.resultAccepted.emit(data, self._handle(context))

    def _on_error(self, context: MatrixOperationContext, error: tuple):
        if not self._is_current(context):
            return
        if context.operation_kind == "route" and error[0] == "authentication_error":
            candidates = tuple(
                self._credential_candidates_provider(
                    context.model,
                    context.ip_address,
                )
                or ()
            )
            next_index = self._credential_advance_provider(
                context.model,
                context.ip_address,
                candidates,
                context.candidate_index or 0,
                context.generation,
            )
            if next_index is not None:
                retry = self._make_context(
                    operation_kind="route",
                    ip_address=context.ip_address,
                    candidate_index=next_index,
                    output_num=context.output_num,
                    input_num=context.input_num,
                    state_changing=True,
                    reuse_generation=context.generation,
                )
                self._submit(retry)
                return
        if context.operation_kind in {"route", "quick_refresh", "keepalive"}:
            if context.operation_kind == "keepalive":
                self._release_session_background()
            else:
                self.routeError.emit(error[1])
            return
        self.errorAccepted.emit(error, self._handle(context))

    def _on_progress(self, context: MatrixOperationContext, progress: int):
        if self._is_current(context):
            self.progressAccepted.emit(progress, self._handle(context))

    def _on_status(self, context: MatrixOperationContext, status: str):
        if self._is_current(context):
            self.statusAccepted.emit(status, self._handle(context))

    def _on_terminal(self, context: MatrixOperationContext, message: str):
        if self._is_current(context):
            self.terminalAccepted.emit(message, self._handle(context))

    def _on_finished(self, context: MatrixOperationContext):
        if not self._is_current(context):
            return
        if context.operation_kind in {"route", "quick_refresh", "keepalive", "cleanup"}:
            if self._active_context == context:
                self._active_context = None
            return
        handle = self._handle(context)
        self._active_context = None
        self.finishedAccepted.emit(handle)


class _MatrixCleanupOperation(QRunnable):
    def __init__(self, controller: MatrixController, context, handler):
        super().__init__()
        self.controller = controller
        self.context = context
        self.handler = handler

    @pyqtSlot()
    def run(self):
        try:
            self.handler.disconnect()
        finally:
            self.controller._signals.finished.emit(self.context)
