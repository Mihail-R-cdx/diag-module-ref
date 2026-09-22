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


_SESSION_INVALIDATING_CATEGORIES = {
    "authentication_error",
    "connection_error",
    "protocol_error",
    "unknown_command_outcome",
}
DEFAULT_RETIREMENT_TIMEOUT_SECONDS = 5.0


class MatrixRetirementBoundaryError(RuntimeError):
    """A prior Matrix transport did not release its conflicting owner slot."""


class MatrixOperationSuperseded(RuntimeError):
    """An operation lost current authority while waiting for retirement."""


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


@dataclass(frozen=True)
class MatrixRetirement:
    """A detached handler and its already-published exclusive owner boundary."""

    context: MatrixOperationContext
    handler: object
    key: tuple[str, int]
    event: threading.Event


@dataclass(frozen=True)
class MatrixRetirementRequest:
    """A GUI-published request for background session retirement."""

    context: MatrixOperationContext
    key: tuple[str, int]
    event: threading.Event


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
    def __init__(self, category: str, message: str, details: str, retirement=None):
        super().__init__(message)
        self.category = category
        self.message = message
        self.details = details
        self.retirement = retirement


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

    _startKeepaliveRequested = pyqtSignal(object)
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
        self._last_model: Optional[str] = None
        self._last_ip = ""
        self._last_credential_revision = self._credential_revision()
        # Metadata authority is deliberately distinct from transport locks.
        # GUI paths take only this lock briefly.  Background ownership paths
        # acquire it only while already holding ``_session_lock`` (and, where
        # applicable, ``_operation_lock``); it never encloses I/O, disconnect,
        # or a retirement wait.  This yields the one-way order
        # operation -> session -> authority, while GUI code never takes the
        # operation or session locks.  Retirement-event metadata has its own
        # lock and is never acquired while authority is held; owner paths may
        # release retirement metadata before taking authority, never inversely.
        self._authority_lock = threading.RLock()
        self._session_lock = threading.RLock()
        self._operation_lock = threading.RLock()
        self._retirement_lock = threading.RLock()
        self._retirement_events: dict[tuple[str, int], threading.Event] = {}
        self._retirement_cleanup_events: set[tuple[tuple[str, int], threading.Event]] = set()
        self._published_session_ip: Optional[str] = None
        self._published_session_model: Optional[str] = None
        self._session_identity: Optional[MatrixSessionIdentity] = None
        self._session_handler = None
        self._keepalive_authority: Optional[MatrixOperationContext] = None
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
        retiring_ip = self._invalidate_authority()
        self._request_keepalive_stop()
        self._release_session_background(retiring_ip=retiring_ip)

    def shutdown(self):
        """Retire active work/session asynchronously on the Matrix owner lane."""
        retiring_ip = self._invalidate_authority()
        self._request_keepalive_stop()
        self._release_session_background(retiring_ip=retiring_ip)

    def request_full_refresh(self, ip_address: str, candidates, candidate_index: int):
        try:
            context = self._make_context(
                operation_kind="full_refresh",
                ip_address=ip_address,
                candidate_index=candidate_index,
                state_changing=False,
            )
        except ValueError:
            return False
        self._submit(context, candidates)
        return True

    def request_route(self, output_num: int, input_num: int):
        if self._authoritative_input_ids and input_num not in self._authoritative_input_ids:
            self.routeError.emit("Input is unavailable on the current Matrix topology")
            return
        if self._authoritative_output_ids and output_num not in self._authoritative_output_ids:
            self.routeError.emit("Output is unavailable on the current Matrix topology")
            return
        provided = self._provided_context()
        if provided is None:
            self.routeError.emit("No current Matrix diagnostic context")
            return
        model, ip_address = provided
        candidates = tuple(self._credential_candidates_provider(model, ip_address) or ())
        if not candidates:
            self.routeError.emit("No credentials for current Matrix context")
            return
        candidate_index = self._credential_index_provider(model, ip_address, candidates)
        if candidate_index < 0 or candidate_index >= len(candidates):
            candidate_index = 0
        try:
            context = self._make_context(
                operation_kind="route",
                ip_address=ip_address,
                candidate_index=candidate_index,
                output_num=output_num,
                input_num=input_num,
                state_changing=True,
            )
        except ValueError:
            self.routeError.emit("No current Matrix diagnostic context")
            return
        self._submit(context, candidates)

    def request_status_refresh(self):
        provided = self._provided_context()
        if provided is None:
            return
        model, ip_address = provided
        candidates = tuple(self._credential_candidates_provider(model, ip_address) or ())
        if not candidates:
            return
        candidate_index = self._credential_index_provider(model, ip_address, candidates)
        if candidate_index < 0 or candidate_index >= len(candidates):
            candidate_index = 0
        try:
            context = self._make_context(
                operation_kind="quick_refresh",
                ip_address=ip_address,
                candidate_index=candidate_index,
                state_changing=False,
            )
        except ValueError:
            return
        self._submit(context, candidates)

    @pyqtSlot()
    def request_keepalive(self):
        with self._authority_lock:
            if self._active_context is not None:
                return
            generation = self._generation
            keepalive_authority = self._keepalive_authority
        if keepalive_authority is None:
            return
        with self._session_lock:
            identity = self._session_identity
            handler = self._session_handler
        if identity is None or handler is None:
            self._request_keepalive_stop()
            return
        try:
            context = self._make_context(
                operation_kind="keepalive",
                ip_address=identity.ip_address,
                candidate_index=identity.candidate_index,
                state_changing=False,
                reuse_generation=generation,
            )
        except ValueError:
            self._request_keepalive_stop()
            return
        self._submit(context)

    def _credential_revision(self) -> int:
        revision = self._credential_revision_provider()
        return int(revision or 0)

    def _provided_context(self):
        """Read application-owned authority without inventing a Matrix target."""
        try:
            model, ip_address = self._context_provider()
        except (TypeError, ValueError):
            return None
        if not isinstance(model, str) or not model.strip():
            return None
        if not isinstance(ip_address, str) or not ip_address.strip():
            return None
        return (model, ip_address)

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
        provided = self._provided_context()
        if provided is None:
            raise ValueError("No current Matrix diagnostic context")
        model, accepted_ip = provided
        if ip_address != accepted_ip:
            raise ValueError("Matrix operation IP does not match current diagnostic context")
        revision = self._credential_revision()
        with self._authority_lock:
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
            replacement = (
                self._last_ip
                and (
                    self._last_ip != ip_address
                    or self._last_model != model
                    or self._last_credential_revision != revision
                )
            )
            # A queued start may only use the exact context which committed
            # the persistent session.  A new interactive request revokes that
            # token before the worker can later reuse or replace the session.
            if operation_kind != "keepalive":
                self._keepalive_authority = None
            retiring_ip = self._published_session_ip if replacement else None
            self._last_model = model
            self._last_ip = ip_address
            self._last_credential_revision = revision
            self._active_context = context
        if replacement:
            # Do not take session/operation locks on the GUI path.  The exact
            # persistent owner was snapshotted while metadata authority held.
            self._request_keepalive_stop()
            self._release_session_background(retiring_ip=retiring_ip)
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
            self._schedule_retirement(failure.retirement)
            self._signals.error.emit(
                context,
                (failure.category, failure.message, failure.details),
            )
        finally:
            self._signals.finished.emit(context)

    def _execute_serialized(self, context: MatrixOperationContext, secrets):
        while True:
            # Retirement completion can need the serialized transport owner
            # lane.  Never wait for it while holding that lane's lock.
            try:
                self._await_retirement_boundary(context)
            except Exception as error:
                message, details = _safe_error(error, secrets)
                raise MatrixOperationFailure(
                    classify_matrix_failure(error).value,
                    message,
                    details,
                ) from error
            if not self._is_current(context):
                return
            retry_after_retirement = False
            with self._operation_lock:
                if not self._is_current(context):
                    return
                # A GUI invalidation can publish a boundary between the wait
                # above and acquisition of this lock.  Release the owner lane
                # before waiting again so retirement can make progress.
                if self._has_pending_retirement():
                    retry_after_retirement = True
                else:
                    try:
                        self._execute_operation_body(context, secrets)
                    except MatrixOperationSuperseded:
                        # Supersession is a normal silent terminal outcome. In
                        # particular, a waiter which became stale while a
                        # previous transport retired must not construct or use
                        # a new handler.
                        return
                    except Exception as error:
                        message, details = _safe_error(error, secrets)
                        category = classify_matrix_failure(error).value
                        if (
                            context.operation_kind == "route"
                            and getattr(error, "_matrix_route_command_invoked", False)
                            and category == "authentication_error"
                        ):
                            category = "unknown_command_outcome"
                        retirement = getattr(error, "_matrix_retirement", None)
                        if category in _SESSION_INVALIDATING_CATEGORIES:
                            detached_handler = self._detach_failed_session_locked(context)
                            if retirement is None:
                                retirement = self._reserve_retirement_locked(
                                    context, detached_handler
                                )
                        raise MatrixOperationFailure(
                            category,
                            message,
                            details,
                            retirement=retirement,
                        ) from error
            if not retry_after_retirement:
                return

    def _execute_operation_body(self, context: MatrixOperationContext, secrets):
        if context.operation_kind == "full_refresh":
            self._signals.status.emit(context, "Connecting to Matrix device...")
            self._signals.progress.emit(context, 10)
            handler = self._acquire_session(context, secrets, retirement_checked=True)
            if not self._is_current(context):
                return
            self._signals.status.emit(context, "Reading Matrix device status...")
            self._signals.progress.emit(context, 30)
            if not self._is_current(context):
                return
            status = handler.get_full_status()
            parser = ExtronIN1804DataParser()
            data = parser.parse(status)
            data["ip_address"] = context.ip_address
            data["_matrix_credential_success_candidate"] = context.candidate_index
            self._signals.progress.emit(context, 100)
            self._signals.status.emit(context, "Ready")
            self._signals.result.emit(context, redact_data(data, secrets))
        elif context.operation_kind == "route":
            handler = self._acquire_session(context, secrets, retirement_checked=True)
            if not self._is_current(context):
                return
            try:
                if not self._is_current(context):
                    return
                handler.set_connection(context.output_num, context.input_num)
            except Exception as error:
                setattr(error, "_matrix_route_command_invoked", True)
                raise
            # Command ACK is deliberately not route authority.  Reconciliation
            # below reads the exact target output before acceptance.
            self._signals.result.emit(context, {"route_input": context.input_num, "route_output": context.output_num})
        elif context.operation_kind == "quick_refresh":
            handler = self._acquire_session(context, secrets, retirement_checked=True)
            if not self._is_current(context):
                return
            if hasattr(handler, "get_routes"):
                if not self._is_current(context):
                    return
                routes = handler.get_routes((context.output_num,)) if context.output_num else handler.get_routes()
                self._signals.result.emit(context, {"routes": routes})
            else:
                connections = handler.get_connections()
                self._signals.result.emit(context, {"routes": {1: connections[0] if connections else None}})
        elif context.operation_kind == "keepalive":
            with self._session_lock:
                handler = self._session_handler
                with self._authority_lock:
                    if not self._is_current_locked(context):
                        raise MatrixOperationSuperseded()
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

    def _acquire_session(self, context: MatrixOperationContext, secrets, *, retirement_checked=False):
        if not retirement_checked:
            self._await_retirement_boundary(context)
        # Waiting does not retain current authority.  A replacement context
        # may have been admitted on the GUI thread while this worker waited.
        # Reject it before credentials, handler allocation, or any Matrix I/O.
        if not self._is_current(context):
            raise MatrixOperationSuperseded()
        candidate = self._candidate_for_context(context)
        if not self._is_credential_mapping(candidate):
            raise RuntimeError("No credentials for current Matrix context")
        identity = self._session_identity_for_context(context)
        with self._session_lock:
            if not self._is_current(context):
                raise MatrixOperationSuperseded()
            if (
                self._session_identity == identity
                and self._session_handler is not None
                and self._session_handler.is_connected()
            ):
                if not self._commit_session_authority_locked(
                    context, identity, self._session_handler
                ):
                    raise MatrixOperationSuperseded()
                self._request_keepalive_start()
                return self._session_handler

            self._disconnect_locked()
            if not self._is_current(context):
                raise MatrixOperationSuperseded()
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
                if not self._is_current(context):
                    raise MatrixOperationSuperseded()
                handler.connect()
            except MatrixOperationSuperseded:
                raise
            except Exception as error:
                # A connect/authentication failure can still leave a transport
                # allocated.  It never becomes reusable session authority, but
                # its physical retirement must gate a conflicting candidate.
                setattr(
                    error,
                    "_matrix_retirement",
                    self._reserve_retirement_locked(context, handler),
                )
                raise
            if not self._commit_session_authority_locked(context, identity, handler):
                # ``connect`` can return after GUI invalidation.  Currentness
                # and publication are one authority-locked transaction, so a
                # stale handler can never become reusable persistent authority
                # or enqueue a valid keepalive start.
                retirement = self._reserve_retirement_locked(context, handler)
                self._schedule_retirement(retirement)
                raise MatrixOperationSuperseded()
            self._request_keepalive_start()
            return handler

    def _commit_session_authority_locked(
        self,
        context: MatrixOperationContext,
        identity: MatrixSessionIdentity,
        handler,
    ) -> bool:
        """Atomically verify currentness and publish persistent ownership.

        Callers hold ``_session_lock``.  The metadata lock is intentionally
        held only for the test-and-publish transaction, never for transport
        I/O or retirement waiting.
        """
        with self._authority_lock:
            if not self._is_current_locked(context):
                return False
            self._session_identity = identity
            self._session_handler = handler
            self._published_session_ip = identity.ip_address
            self._published_session_model = identity.model
            self._keepalive_authority = context
            return True

    def _invalidate_authority(self):
        """Revoke GUI-visible authority and snapshot its persistent owner."""
        with self._authority_lock:
            retiring_ip = self._published_session_ip
            self._generation += 1
            self._active_context = None
            self._keepalive_authority = None
            return retiring_ip

    def _release_session_background(self, *, retiring_ip=None):
        """Publish a non-blocking retirement request and enqueue its owner work.

        This method is called by GUI-facing invalidation paths.  It touches
        only retirement metadata; session detach and physical disconnect are
        performed later by ``_MatrixRetirementOperation``.
        """
        if retiring_ip is None:
            with self._authority_lock:
                retiring_ip = self._published_session_ip
        if not retiring_ip:
            return
        context = self._make_retirement_context(retiring_ip)
        key = self._retirement_key(context)
        with self._retirement_lock:
            event = self._retirement_events.get(key)
            if event is not None and not event.is_set():
                return
            event = threading.Event()
            self._retirement_events[key] = event
        self._thread_pool.start(
            _MatrixRetirementOperation(self, MatrixRetirementRequest(context, key, event))
        )

    def _retirement_owner_ip(self, fallback_ip):
        """Return actual persistent transport ownership, not mutable UI state."""
        with self._authority_lock:
            return self._published_session_ip or fallback_ip

    def _make_cleanup_context(self, *, model=None, ip_address=None, credential_revision=None):
        with self._authority_lock:
            operation_id = next(self._operation_serial)
            return MatrixOperationContext(
                model=model or self._last_model or "",
                ip_address=ip_address if ip_address is not None else self._last_ip,
                operation_kind="cleanup",
                generation=self._generation,
                operation_id=operation_id,
                expected_operation_id=operation_id,
                credential_context_revision=(
                    self._last_credential_revision
                    if credential_revision is None
                    else credential_revision
                ),
            )

    def _make_retirement_context(self, ip_address):
        with self._authority_lock:
            operation_id = next(self._operation_serial)
            return MatrixOperationContext(
                model=self._published_session_model or self._last_model or "",
                ip_address=ip_address,
                operation_kind="retirement",
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
        with self._authority_lock:
            self._published_session_ip = None
            self._published_session_model = None
            self._keepalive_authority = None
        self._request_keepalive_stop()

    def _request_keepalive_start(self):
        with self._authority_lock:
            context = self._keepalive_authority
        if context is None:
            return
        if QThread.currentThread() == self.thread():
            self._start_keepalive_timer(context)
        else:
            self._startKeepaliveRequested.emit(context)

    def _request_keepalive_stop(self):
        if QThread.currentThread() == self.thread():
            self._stop_keepalive_timer()
        else:
            self._stopKeepaliveRequested.emit()

    @pyqtSlot(object)
    def _start_keepalive_timer(self, context=None):
        with self._authority_lock:
            if (
                context is None
                or context != self._keepalive_authority
                or not self._is_current_locked(context)
            ):
                return
        if not self._keepalive_timer.isActive():
            self._keepalive_timer.start()

    @pyqtSlot()
    def _stop_keepalive_timer(self):
        if self._keepalive_timer.isActive():
            self._keepalive_timer.stop()

    def _invalidate_failed_session(self, context: MatrixOperationContext):
        with self._operation_lock:
            handler = self._detach_failed_session_locked(context)
            retirement = self._reserve_retirement_locked(context, handler)
        self._schedule_retirement(retirement)

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
            with self._authority_lock:
                self._published_session_ip = None
                self._published_session_model = None
                self._keepalive_authority = None
        self._request_keepalive_stop()
        return handler

    @staticmethod
    def _retirement_key(context: MatrixOperationContext) -> tuple[str, int]:
        return (context.ip_address, 22023)

    def _await_retirement_boundary(self, context: MatrixOperationContext):
        # A controller owns one persistent Matrix session.  Await every
        # pending boundary before replacing that session so a different target
        # cannot inherit or disconnect an old target's authority.
        with self._retirement_lock:
            events = tuple(
                event for event in self._retirement_events.values() if not event.is_set()
            )
        for event in events:
            if not event.wait(self._retirement_timeout_seconds):
                # The operation lane is background-owned, but a timeout never
                # authorizes a second conflicting Matrix transport owner.
                raise MatrixRetirementBoundaryError(
                    "Previous Matrix session did not reach its retirement boundary"
                )

    def _has_pending_retirement(self):
        with self._retirement_lock:
            return any(not event.is_set() for event in self._retirement_events.values())

    def _reserve_retirement_locked(self, context: MatrixOperationContext, handler):
        """Detach authority and publish its conflict boundary under owner serialization."""
        if handler is None:
            return None
        key = self._retirement_key(context)
        with self._retirement_lock:
            event = self._retirement_events.get(key)
            if event is None or event.is_set():
                event = threading.Event()
                self._retirement_events[key] = event
            self._retirement_cleanup_events.add((key, event))
        cleanup_context = (
            context
            if context.operation_kind == "cleanup"
            else self._make_cleanup_context(
                model=context.model,
                ip_address=context.ip_address,
                credential_revision=context.credential_context_revision,
            )
        )
        return MatrixRetirement(cleanup_context, handler, key, event)

    def _schedule_retirement(self, retirement):
        if retirement is not None:
            self._thread_pool.start(_MatrixCleanupOperation(self, retirement))

    def _complete_retirement(self, key, event):
        with self._retirement_lock:
            self._retirement_cleanup_events.discard((key, event))
            if self._retirement_events.get(key) is event:
                self._retirement_events.pop(key, None)
            event.set()

    def _is_current(self, context: MatrixOperationContext) -> bool:
        with self._authority_lock:
            return self._is_current_locked(context)

    def _is_current_locked(self, context: MatrixOperationContext) -> bool:
        """Check context freshness while ``_authority_lock`` is held."""
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
            with self._authority_lock:
                if self._is_current_locked(context) and self._active_context == context:
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
        with self._authority_lock:
            if not self._is_current_locked(context):
                return
            if context.operation_kind in {"route", "quick_refresh", "keepalive", "cleanup"}:
                if self._active_context == context:
                    self._active_context = None
                return
            handle = self._handle(context)
            self._active_context = None
        self.finishedAccepted.emit(handle)


class _MatrixCleanupOperation(QRunnable):
    def __init__(self, controller: MatrixController, retirement: MatrixRetirement):
        super().__init__()
        self.controller = controller
        self.context = retirement.context
        self.handler = retirement.handler
        self.retirement_key = retirement.key
        self.retirement_event = retirement.event

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
    """Detach on the owner lane, then close transport without its locks."""

    def __init__(self, controller: MatrixController, request: MatrixRetirementRequest):
        super().__init__()
        self.controller = controller
        self.context = request.context
        self.retirement_key = request.key
        self.retirement_event = request.event

    @pyqtSlot()
    def run(self):
        handler = None
        with self.controller._operation_lock:
            with self.controller._session_lock:
                identity = self.controller._session_identity
                if identity is not None and identity.ip_address == self.context.ip_address:
                    handler = self.controller._session_handler
                    self.controller._session_handler = None
                    self.controller._session_identity = None
                    with self.controller._authority_lock:
                        self.controller._published_session_ip = None
                        self.controller._published_session_model = None
                        self.controller._keepalive_authority = None
            if handler is not None:
                self.controller._request_keepalive_stop()

        # No waiter holds _operation_lock here: physical transport cleanup may
        # block, but it cannot stall GUI invalidation or owner-lane progress.
        if handler is not None:
            try:
                handler.disconnect()
            except Exception:
                pass

        with self.controller._retirement_lock:
            cleanup_owns_boundary = (
                (self.retirement_key, self.retirement_event)
                in self.controller._retirement_cleanup_events
            )
        if not cleanup_owns_boundary:
            self.controller._complete_retirement(
                self.retirement_key, self.retirement_event
            )
        self.controller._signals.finished.emit(self.context)
