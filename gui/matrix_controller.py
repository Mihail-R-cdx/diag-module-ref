"""Matrix-specific application lifecycle controller."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import itertools
import threading
from typing import Callable, Iterable, Optional

from PyQt5.QtCore import QObject, QRunnable, QThread, QThreadPool, QTimer, pyqtSignal, pyqtSlot

from core.exceptions import classify_matrix_failure
from core.parser import ExtronIN1804DataParser
from core.redaction import redact_data, redacted_callback
from core.workers.common import _safe_error
from handlers.extron.in1804 import ExtronIN1804Handler


MATRIX_DEVICE_NAME = "Extron IN1804"
_SESSION_INVALIDATING_CATEGORIES = {
    "authentication_error",
    "connection_error",
    "protocol_error",
    "unknown_command_outcome",
}
DEFAULT_RETIREMENT_TIMEOUT_SECONDS = 5.0


class MatrixRetirementBoundaryError(RuntimeError):
    """A prior Matrix transport did not release its conflicting owner slot."""


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


class MatrixOperationFailure(Exception):
    def __init__(self, category: str, message: str, details: str, detached_handler=None):
        super().__init__(message)
        self.category = category
        self.message = message
        self.details = details
        self.detached_handler = detached_handler


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

    _startKeepaliveRequested = pyqtSignal()
    _stopKeepaliveRequested = pyqtSignal()

    resultAccepted = pyqtSignal(dict, object)
    errorAccepted = pyqtSignal(tuple, object)
    progressAccepted = pyqtSignal(int, object)
    statusAccepted = pyqtSignal(str, object)
    terminalAccepted = pyqtSignal(str, object)
    finishedAccepted = pyqtSignal(object)
    cleanupFinished = pyqtSignal(object)
    routeAccepted = pyqtSignal(int)
    routeAcceptedForOutput = pyqtSignal(int, int)
    routeError = pyqtSignal(str)

    def __init__(
        self,
        *,
        context_provider: Callable[[], tuple[str, str]],
        credential_candidates_provider: Callable[
            [str, str], Iterable[Mapping[str, object]]
        ],
        credential_index_provider: Callable[
            [str, str, Iterable[Mapping[str, object]]], int
        ],
        credential_advance_provider: Callable[
            [str, str, Iterable[Mapping[str, object]], int, int], Optional[int]
        ],
        credential_revision_provider: Callable[[], int],
        thread_pool: Optional[QThreadPool] = None,
        retirement_timeout_seconds: float = DEFAULT_RETIREMENT_TIMEOUT_SECONDS,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._context_provider = context_provider
        self._credential_candidates_provider = credential_candidates_provider
        self._credential_index_provider = credential_index_provider
        self._credential_advance_provider = credential_advance_provider
        self._credential_revision_provider = credential_revision_provider
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        if retirement_timeout_seconds <= 0:
            raise ValueError("Matrix retirement timeout must be positive.")
        self._retirement_timeout_seconds = retirement_timeout_seconds
        self._operation_serial = itertools.count(1)
        self._generation = 0
        self._active_context: Optional[MatrixOperationContext] = None
        self._last_model = MATRIX_DEVICE_NAME
        self._last_ip = ""
        self._last_credential_revision = self._credential_revision()
        self._session_lock = threading.RLock()
        self._operation_lock = threading.RLock()
        self._retirement_lock = threading.RLock()
        self._retirement_events: dict[tuple[str, int], threading.Event] = {}
        self._session_identity: Optional[MatrixSessionIdentity] = None
        self._session_handler = None
        self._candidate_snapshots = {}
        self._authoritative_input_ids = ()
        self._authoritative_output_ids = ()
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
        self._startKeepaliveRequested.connect(self._start_keepalive_timer)
        self._stopKeepaliveRequested.connect(self._stop_keepalive_timer)

    def invalidate_context(self):
        self._generation += 1
        self._active_context = None
        self._request_keepalive_stop()
        self._release_session_background()

    def shutdown(self):
        """Retire active work/session asynchronously on the Matrix owner lane."""
        self._generation += 1
        self._active_context = None
        self._request_keepalive_stop()
        context = self._make_cleanup_context()
        self._thread_pool.start(_MatrixRetirementOperation(self, context))

    def request_full_refresh(self, ip_address: str, candidates, candidate_index: int):
        self._last_model = MATRIX_DEVICE_NAME
        self._last_ip = ip_address
        context = self._make_context(
            operation_kind="full_refresh",
            ip_address=ip_address,
            candidate_index=candidate_index,
            state_changing=False,
        )
        self._submit(context, candidates)

    def request_route(self, output_num: int, input_num: int):
        if self._authoritative_input_ids and input_num not in self._authoritative_input_ids:
            self.routeError.emit("Input is unavailable on the current Matrix topology")
            return
        if self._authoritative_output_ids and output_num not in self._authoritative_output_ids:
            self.routeError.emit("Output is unavailable on the current Matrix topology")
            return
        model, ip_address = self._context_provider()
        candidates = tuple(self._credential_candidates_provider(model, ip_address) or ())
        if not candidates:
            self.routeError.emit("No credentials for Extron IN1804")
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
        self._submit(context, candidates)

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
        self._submit(context, candidates)

    @pyqtSlot()
    def request_keepalive(self):
        if self._active_context is not None:
            return
        with self._session_lock:
            identity = self._session_identity
            handler = self._session_handler
        if identity is None or handler is None:
            self._request_keepalive_stop()
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
        model, _ignored_ip = self._context_provider()
        model = model or MATRIX_DEVICE_NAME
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

    def _submit(self, context: MatrixOperationContext, candidates=None):
        if candidates is not None and context.candidate_index is not None:
            self._candidate_snapshots[context.operation_id] = tuple(candidates or ())
        self._thread_pool.start(MatrixBackgroundOperation(self, context))

    def _run_background_operation(self, context: MatrixOperationContext):
        if not self._is_current(context):
            self._candidate_snapshots.pop(context.operation_id, None)
            return
        secrets = self._candidate_secrets(context)
        try:
            self._execute_serialized(context, secrets)
        except MatrixOperationFailure as failure:
            # Logical retirement already happened under the operation/session
            # locks.  Physical close may block indefinitely in a transport, so
            # it must never delay the terminal result or make the failed
            # handler reusable by a later operation.
            self._schedule_detached_cleanup(context, failure.detached_handler)
            self._signals.error.emit(
                context,
                (failure.category, failure.message, failure.details),
            )
        finally:
            self._signals.finished.emit(context)

    def _execute_serialized(self, context: MatrixOperationContext, secrets):
        with self._operation_lock:
            if not self._is_current(context):
                return
            try:
                self._execute_operation_body(context, secrets)
            except Exception as error:
                message, details = _safe_error(error, secrets)
                category = classify_matrix_failure(error).value
                if (
                    context.operation_kind == "route"
                    and getattr(error, "_matrix_route_command_invoked", False)
                    and category == "authentication_error"
                ):
                    category = "unknown_command_outcome"
                detached_handler = None
                if category in _SESSION_INVALIDATING_CATEGORIES:
                    detached_handler = self._detach_failed_session_locked(context)
                raise MatrixOperationFailure(
                    category,
                    message,
                    details,
                    detached_handler=detached_handler,
                ) from error

    def _execute_operation_body(self, context: MatrixOperationContext, secrets):
        if context.operation_kind == "full_refresh":
            self._signals.status.emit(context, "Connecting to Extron IN1804 matrix...")
            self._signals.progress.emit(context, 10)
            handler = self._acquire_session(context, secrets)
            if not self._is_current(context):
                return
            self._signals.status.emit(context, "Reading Matrix device status...")
            self._signals.progress.emit(context, 30)
            status = handler.get_full_status()
            parser = ExtronIN1804DataParser()
            data = parser.parse(status)
            data["ip_address"] = context.ip_address
            data["_matrix_credential_success_candidate"] = context.candidate_index
            self._signals.progress.emit(context, 100)
            self._signals.status.emit(context, "Ready")
            self._signals.result.emit(context, redact_data(data, secrets))
        elif context.operation_kind == "route":
            handler = self._acquire_session(context, secrets)
            if not self._is_current(context):
                return
            try:
                handler.set_connection(context.output_num, context.input_num)
            except Exception as error:
                setattr(error, "_matrix_route_command_invoked", True)
                raise
            # Command ACK is deliberately not route authority.  Reconciliation
            # below reads the exact target output before acceptance.
            self._signals.result.emit(context, {"route_input": context.input_num, "route_output": context.output_num})
        elif context.operation_kind == "quick_refresh":
            handler = self._acquire_session(context, secrets)
            if not self._is_current(context):
                return
            if hasattr(handler, "get_routes"):
                routes = handler.get_routes((context.output_num,)) if context.output_num else handler.get_routes()
                self._signals.result.emit(context, {"routes": routes})
            else:
                connections = handler.get_connections()
                self._signals.result.emit(context, {"routes": {1: connections[0] if connections else None}})
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

    def _is_credential_mapping(self, candidate) -> bool:
        return isinstance(candidate, Mapping)

    def _candidate_secrets(self, context: MatrixOperationContext):
        candidate = self._candidate_for_context(context)
        if not self._is_credential_mapping(candidate):
            return ()
        return tuple(value for value in candidate.values() if value)

    def _candidate_for_context(self, context: MatrixOperationContext):
        if context.candidate_index is None:
            return None
        candidates = self._candidate_snapshots.get(context.operation_id)
        if candidates is None:
            candidates = tuple(
                self._credential_candidates_provider(context.model, context.ip_address)
                or ()
            )
        if context.candidate_index < 0 or context.candidate_index >= len(candidates):
            return None
        return candidates[context.candidate_index]

    def _session_identity_for_context(self, context: MatrixOperationContext):
        if context.candidate_index is None:
            return None
        return MatrixSessionIdentity(
            model=context.model,
            ip_address=context.ip_address,
            protocol="auto",
            port=22023,
            credential_context_revision=context.credential_context_revision,
            candidate_index=context.candidate_index,
        )

    def _acquire_session(self, context: MatrixOperationContext, secrets):
        self._await_retirement_boundary(context)
        candidate = self._candidate_for_context(context)
        if not self._is_credential_mapping(candidate):
            raise RuntimeError("No credentials for Extron IN1804")
        identity = self._session_identity_for_context(context)
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
                expected_model=context.model,
            )
            handler.log_callback = redacted_callback(
                lambda message: self._signals.terminal_log.emit(context, message),
                secrets,
            )
            try:
                handler.connect()
            except Exception:
                # A connect/authentication failure can still leave a transport
                # allocated.  It never becomes reusable session authority, but
                # its physical retirement must gate a conflicting candidate.
                self._schedule_detached_cleanup(context, handler)
                raise
            self._session_identity = identity
            self._session_handler = handler
            self._request_keepalive_start()
            return handler

    def _release_session_background(self):
        with self._session_lock:
            handler = self._session_handler
            self._session_handler = None
            self._session_identity = None
        if handler is not None:
            context = self._make_cleanup_context()
            self._schedule_detached_cleanup(context, handler)

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
        self._request_keepalive_stop()

    def _request_keepalive_start(self):
        if QThread.currentThread() == self.thread():
            self._start_keepalive_timer()
        else:
            self._startKeepaliveRequested.emit()

    def _request_keepalive_stop(self):
        if QThread.currentThread() == self.thread():
            self._stop_keepalive_timer()
        else:
            self._stopKeepaliveRequested.emit()

    @pyqtSlot()
    def _start_keepalive_timer(self):
        if not self._keepalive_timer.isActive():
            self._keepalive_timer.start()

    @pyqtSlot()
    def _stop_keepalive_timer(self):
        if self._keepalive_timer.isActive():
            self._keepalive_timer.stop()

    def _invalidate_failed_session(self, context: MatrixOperationContext):
        with self._operation_lock:
            handler = self._detach_failed_session_locked(context)
        self._schedule_detached_cleanup(context, handler)

    def _detach_failed_session_locked(self, context: MatrixOperationContext):
        identity = self._session_identity_for_context(context)
        if identity is None:
            return None
        with self._session_lock:
            if self._session_identity != identity:
                return None
            handler = self._session_handler
            self._session_handler = None
            self._session_identity = None
        self._request_keepalive_stop()
        return handler

    @staticmethod
    def _retirement_key(context: MatrixOperationContext) -> tuple[str, int]:
        return (context.ip_address, 22023)

    def _await_retirement_boundary(self, context: MatrixOperationContext):
        key = self._retirement_key(context)
        with self._retirement_lock:
            event = self._retirement_events.get(key)
        if event is not None and not event.wait(self._retirement_timeout_seconds):
            # The operation lane is background-owned, but a timeout never
            # authorizes a second conflicting Matrix transport owner.  This is
            # especially important for a route whose prior delivery may be
            # ambiguous.
            raise MatrixRetirementBoundaryError(
                "Previous Matrix session did not reach its retirement boundary"
            )

    def _schedule_detached_cleanup(self, context: MatrixOperationContext, handler):
        if handler is not None:
            key = self._retirement_key(context)
            with self._retirement_lock:
                event = self._retirement_events.get(key)
                if event is None or event.is_set():
                    event = threading.Event()
                    self._retirement_events[key] = event
            cleanup_context = (
                context if context.operation_kind == "cleanup" else self._make_cleanup_context()
            )
            self._thread_pool.start(
                _MatrixCleanupOperation(self, cleanup_context, handler, key, event)
            )

    def _complete_retirement(self, key, event):
        with self._retirement_lock:
            if self._retirement_events.get(key) is event:
                self._retirement_events.pop(key, None)
            event.set()

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
            follow_up = self._make_context(
                operation_kind="quick_refresh",
                ip_address=context.ip_address,
                candidate_index=context.candidate_index,
                output_num=context.output_num,
                input_num=context.input_num,
                state_changing=False,
                reuse_generation=context.generation,
            )
            self._submit(follow_up, self._candidate_snapshots.get(context.operation_id))
            return
        if context.operation_kind == "quick_refresh":
            routes = data.get("routes") if isinstance(data.get("routes"), Mapping) else {}
            output_num = context.output_num or 1
            current = routes.get(output_num)
            if current is not None and (context.input_num is None or current == context.input_num):
                self.routeAccepted.emit(current)
                self.routeAcceptedForOutput.emit(output_num, current)
            return
        if context.operation_kind == "keepalive":
            self._active_context = None
            return
        self._authoritative_input_ids = tuple(data.get("available_input_ids", ()) or ())
        self._authoritative_output_ids = tuple(data.get("available_output_ids", ()) or ())
        self.resultAccepted.emit(data, self._handle(context))

    def _on_error(self, context: MatrixOperationContext, error: tuple):
        if not self._is_current(context):
            return
        if context.operation_kind == "route" and error[0] == "authentication_error":
            candidates = self._candidate_snapshots.get(context.operation_id)
            if candidates is None:
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
                self._submit(retry, candidates)
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
        self._candidate_snapshots.pop(context.operation_id, None)
        if context.operation_kind == "retirement":
            self.cleanupFinished.emit(context)
            return
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
    def __init__(self, controller: MatrixController, context, handler, retirement_key, retirement_event):
        super().__init__()
        self.controller = controller
        self.context = context
        self.handler = handler
        self.retirement_key = retirement_key
        self.retirement_event = retirement_event

    @pyqtSlot()
    def run(self):
        # The handler has been detached before this runnable is scheduled.
        # Do not serialize a potentially blocked transport close with a new
        # logical operation: it owns no session authority any longer.
        try:
            self.handler.disconnect()
        finally:
            self.controller._complete_retirement(
                self.retirement_key, self.retirement_event
            )
            self.controller._signals.finished.emit(self.context)


class _MatrixRetirementOperation(QRunnable):
    """Wait behind active Matrix work, then release its session physically."""

    def __init__(self, controller: MatrixController, context):
        super().__init__()
        self.controller = controller
        self.context = MatrixOperationContext(
            model=context.model,
            ip_address=context.ip_address,
            operation_kind="retirement",
            generation=context.generation,
            operation_id=context.operation_id,
            expected_operation_id=context.expected_operation_id,
            credential_context_revision=context.credential_context_revision,
        )

    @pyqtSlot()
    def run(self):
        handler = None
        with self.controller._operation_lock:
            with self.controller._session_lock:
                handler = self.controller._session_handler
                self.controller._session_handler = None
                self.controller._session_identity = None
            if handler is not None:
                try:
                    handler.disconnect()
                except Exception:
                    pass
        self.controller._signals.finished.emit(self.context)
