"""DMP-specific application polling lifecycle controller."""

from __future__ import annotations

from dataclasses import dataclass
import itertools
from typing import Callable, Optional

from PyQt5.QtCore import QThreadPool
from PyQt5.QtWidgets import QMessageBox

from core.dmp64_plus import DMPCancellationToken
from core.exceptions import CodecFailureCategory, CredentialConfigurationError
from core.worker import ExtronDMP64PlusMeterWorker
from .ui_states import UIState


DMP_DEVICE_NAME = "Extron DMP 64 Plus"


@dataclass(frozen=True)
class DMPPollingContext:
    generation: int
    model: str
    ip_address: str
    request_id: int
    candidate_index: int
    credential_context_revision: int
    attempt_id: int


@dataclass(frozen=True)
class PendingDMPRetry:
    failed_context: DMPPollingContext
    expected_worker_id: int
    next_candidate_index: int


class DMPPollingController:
    """Owns DMP polling context, callback authority, and credential handoff."""

    def __init__(
        self,
        *,
        shell,
        screen_provider: Callable[[], object],
        thread_pool: Optional[QThreadPool] = None,
    ):
        self.shell = shell
        self._screen_provider = screen_provider
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._generation = 0
        self._credential_context_revision = 0
        self._attempt_serial = itertools.count(1)
        self._active_context: Optional[DMPPollingContext] = None
        self._active_cancellation: Optional[DMPCancellationToken] = None
        self._expected_worker_id: Optional[int] = None
        self._pending_retry: Optional[PendingDMPRetry] = None
        self._retiring_context: Optional[DMPPollingContext] = None
        self._retiring_worker_id: Optional[int] = None
        self._success_committed_context: Optional[DMPPollingContext] = None

    @property
    def credential_context_revision(self) -> int:
        return self._credential_context_revision

    @property
    def active_context(self) -> Optional[DMPPollingContext]:
        return self._active_context

    @property
    def pending_retry(self) -> Optional[PendingDMPRetry]:
        return self._pending_retry

    def invalidate_credential_context(self) -> None:
        self._credential_context_revision += 1
        self.invalidate_context()

    def invalidate_context(self) -> None:
        token = self._active_cancellation
        if token is not None:
            token.cancel()
        self._generation += 1
        self._active_context = None
        self._active_cancellation = None
        self._expected_worker_id = None
        self._pending_retry = None
        self._retiring_context = None
        self._retiring_worker_id = None
        self._success_committed_context = None

    def shutdown(self) -> None:
        self.invalidate_context()

    def refresh(self, ip_address: str) -> bool:
        if not self.shell.validate_ip_address(ip_address):
            QMessageBox.warning(self.shell, "Invalid IP", "Enter a valid IP address.")
            return False

        self.invalidate_context()
        try:
            request = self._ensure_request(ip_address)
            creds_list = tuple(self.shell.device_credentials.get(DMP_DEVICE_NAME) or ())
            if not creds_list:
                raise CredentialConfigurationError(
                    "Credentials are required for Extron DMP 64 Plus."
                )
            current_idx = self.shell._credential_attempt_index(
                DMP_DEVICE_NAME,
                creds_list,
                ip_address,
                request["id"],
            )
            self._start_attempt(
                ip_address=ip_address,
                request_id=request["id"],
                creds_list=creds_list,
                current_idx=current_idx,
                reset_terminal=(current_idx == 0),
            )
            return True
        except CredentialConfigurationError as error:
            self._handle_start_failure(error, warning=True)
            return False
        except Exception as error:
            self._handle_start_failure(error, warning=False)
            return False

    def _ensure_request(self, ip_address: str):
        request = self.shell.__dict__.get("_active_request")
        if (
            request is not None
            and request.get("device") == DMP_DEVICE_NAME
            and request.get("ip") == ip_address
        ):
            return request
        return self.shell._begin_request(
            DMP_DEVICE_NAME,
            ip_address,
            self._screen(),
        )

    def _start_attempt(
        self,
        *,
        ip_address: str,
        request_id: int,
        creds_list: tuple,
        current_idx: int,
        reset_terminal: bool,
    ) -> None:
        creds = creds_list[current_idx]
        cancellation = DMPCancellationToken()
        context = DMPPollingContext(
            generation=self._generation,
            model=DMP_DEVICE_NAME,
            ip_address=ip_address,
            request_id=request_id,
            candidate_index=current_idx,
            credential_context_revision=self._credential_context_revision,
            attempt_id=next(self._attempt_serial),
        )
        worker = ExtronDMP64PlusMeterWorker(
            ip_address=ip_address,
            cancellation=cancellation,
            **creds,
        )
        worker.creds_list = list(creds_list)
        worker.current_idx = current_idx
        worker.device_name = DMP_DEVICE_NAME
        worker.dmp_context = context

        self._active_context = context
        self._active_cancellation = cancellation
        self._expected_worker_id = id(worker)
        self._success_committed_context = None
        self.shell.current_worker = worker

        if hasattr(self.shell, "refresh_btn"):
            self.shell.refresh_btn.setEnabled(False)
            self.shell.refresh_btn.setText("Подключение...")
        self.shell.show_progress_dialog(
            f"Подключение к {DMP_DEVICE_NAME} "
            f"(попытка {current_idx + 1}/{len(creds_list)})..."
        )
        self.shell.show_codec_poll_terminal(
            DMP_DEVICE_NAME,
            ip_address,
            current_idx + 1,
            len(creds_list),
            reset=reset_terminal,
        )

        self._bind_worker(worker, context)
        self._thread_pool.start(worker)

    def _bind_worker(self, worker, context: DMPPollingContext) -> None:
        worker.signals.result.connect(
            lambda data, w=worker, c=context: self.on_result(data, w, c)
        )
        worker.signals.error.connect(
            lambda error, w=worker, c=context: self.on_error(error, w, c)
        )
        worker.signals.progress.connect(
            lambda progress, w=worker, c=context: self.on_progress(progress, w, c)
        )
        worker.signals.status.connect(
            lambda status, w=worker, c=context: self.on_status(status, w, c)
        )
        worker.signals.terminal_log.connect(
            lambda message, w=worker, c=context: self.on_terminal_log(message, w, c)
        )
        worker.signals.finished.connect(
            lambda w=worker, c=context: self.on_finished(w, c)
        )

    def on_result(self, data, worker, context: DMPPollingContext) -> None:
        if not self._is_current(context, worker):
            return
        rendered = dict(data or {})
        self._commit_success_if_allowed(rendered, context)
        rendered["_credential_policy_handled"] = True
        self.shell.on_device_data_received(rendered, worker, context.request_id)

    def on_error(self, error_info, worker, context: DMPPollingContext) -> None:
        if not self._is_current(context, worker):
            return
        error_type = error_info[0]
        if error_type == CodecFailureCategory.AUTHENTICATION.value:
            next_idx = self._advance_after_authentication_failure(context, worker)
            if next_idx is not None:
                self._pending_retry = PendingDMPRetry(
                    failed_context=context,
                    expected_worker_id=id(worker),
                    next_candidate_index=next_idx,
                )
                self._retiring_context = context
                self._retiring_worker_id = id(worker)
                self._active_context = None
                self._active_cancellation = None
                self._expected_worker_id = None
                self.shell.set_ui_state(
                    UIState.LOADING,
                    f"Ошибка авторизации; ожидание cleanup перед попыткой {next_idx + 1}...",
                )
                return

        self._discard_attempt_plan(context)
        self.shell.on_device_error(error_info, worker, context.request_id)

    def on_progress(self, progress, worker, context: DMPPollingContext) -> None:
        if self._is_current(context, worker):
            self.shell.on_progress_update(progress, worker, context.request_id)

    def on_status(self, status, worker, context: DMPPollingContext) -> None:
        if self._is_current(context, worker):
            self.shell.on_status_update(status, worker, context.request_id)

    def on_terminal_log(self, message, worker, context: DMPPollingContext) -> None:
        if self._is_current(context, worker):
            self.shell.on_codec_poll_terminal_log(message)

    def on_finished(self, worker, context: DMPPollingContext) -> None:
        if self._release_pending_retry(worker, context):
            return
        if self._is_current(context, worker):
            self._active_context = None
            self._active_cancellation = None
            self._expected_worker_id = None
            self.shell.on_worker_finished(worker, context.request_id)

    def _release_pending_retry(self, worker, context: DMPPollingContext) -> bool:
        pending = self._pending_retry
        if pending is None:
            return False
        if (
            pending.failed_context != context
            or pending.expected_worker_id != id(worker)
            or self._retiring_context != context
            or self._retiring_worker_id != id(worker)
        ):
            return False
        if not self._context_authority_still_valid(context):
            self._pending_retry = None
            self._retiring_context = None
            self._retiring_worker_id = None
            return True

        next_idx = pending.next_candidate_index
        self._pending_retry = None
        self._retiring_context = None
        self._retiring_worker_id = None
        creds_list = tuple(getattr(worker, "creds_list", ()) or ())
        self._start_attempt(
            ip_address=context.ip_address,
            request_id=context.request_id,
            creds_list=creds_list,
            current_idx=next_idx,
            reset_terminal=False,
        )
        return True

    def _is_current(self, context: DMPPollingContext, worker) -> bool:
        return (
            self._active_context == context
            and self._expected_worker_id == id(worker)
            and self._context_authority_still_valid(context)
        )

    def _context_authority_still_valid(self, context: DMPPollingContext) -> bool:
        request = self.shell.__dict__.get("_active_request") or {}
        return (
            context.generation == self._generation
            and context.credential_context_revision == self._credential_context_revision
            and request.get("id") == context.request_id
            and request.get("device") == context.model
            and request.get("ip") == context.ip_address
        )

    def _advance_after_authentication_failure(self, context, worker):
        creds_list = tuple(getattr(worker, "creds_list", ()) or ())
        return self.shell._advance_request_credential_attempt(
            context.model,
            creds_list,
            context.ip_address,
            context.candidate_index,
            context.request_id,
        )

    def _commit_success_if_allowed(self, data, context: DMPPollingContext) -> None:
        if self._success_committed_context == context:
            return
        if not data.get("complete"):
            return
        if data.get("_credential_used") is not True:
            return
        self.shell.set_current_credential_index(
            context.model,
            context.candidate_index,
            context.ip_address,
        )
        connection_profile = data.get("connection_profile")
        if isinstance(connection_profile, dict) and connection_profile:
            self.shell.set_device_connection_profile(
                context.model,
                connection_profile,
                context.ip_address,
            )
        self._discard_attempt_plan(context)
        self._success_committed_context = context

    def _discard_attempt_plan(self, context: DMPPollingContext) -> None:
        self.shell._discard_credential_attempt_plan(
            context.model,
            context.ip_address,
            context.request_id,
        )

    def _handle_start_failure(self, error, *, warning: bool) -> None:
        self.invalidate_context()
        message = str(error)
        self.shell._fail_request_start(error)
        if warning:
            QMessageBox.warning(self.shell, "Настройка credentials", message)
        else:
            QMessageBox.critical(
                self.shell,
                "Error",
                f"Could not create worker: {message}",
            )
        if hasattr(self.shell, "refresh_btn"):
            self.shell.refresh_btn.setEnabled(True)
            self.shell.refresh_btn.setText("Обновить данные")

    def _screen(self):
        return self._screen_provider()
