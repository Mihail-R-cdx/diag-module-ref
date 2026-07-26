"""PDU-specific application lifecycle controller."""

from __future__ import annotations

from dataclasses import dataclass
import itertools
from typing import Callable, Optional

from PyQt5.QtCore import QThreadPool
from PyQt5.QtWidgets import QMessageBox

from core.exceptions import CodecFailureCategory
from core.exceptions import CredentialConfigurationError
from core.pdu import (
    BULK_COMMAND_OFF,
    BULK_COMMAND_ON,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_REBOOT,
    REFRESH,
    PDUOperationDescriptor,
    build_pdu_bulk_outlet_sequence,
    ensure_pdu_operation_supported,
    normalize_pdu_credential_candidates,
)
from core.worker import PDUOperationWorker
from .pdu_room_codec_enrichment import PDUAcceptedRefreshContext, PDUContextSuperseded
from .ui_states import UIState


PDU_DEVICE_NAMES = {"Aten PE8208AV", "Extron IPL T PCS4i"}


@dataclass(frozen=True)
class PDUCommonContext:
    generation: int
    model: str
    ip_address: str
    credential_context_revision: int


@dataclass(frozen=True)
class PDUAttemptState:
    candidates: tuple
    current_index: int
    lane: str


@dataclass(frozen=True)
class PDURefreshLane:
    operation_id: int
    expected_worker_id: int
    context: PDUCommonContext
    state_epoch: int
    originating_mutation_operation_id: Optional[int] = None


@dataclass(frozen=True)
class PDUMutationLane:
    operation_id: int
    expected_worker_id: int
    mutation_kind: str
    context: PDUCommonContext


class PDUController:
    """Owns PDU refresh, mutation, stale acceptance, and reconciliation."""

    def __init__(
        self,
        *,
        shell,
        screen_provider: Callable[[], object],
        thread_pool: Optional[QThreadPool] = None,
        accepted_refresh_callback: Optional[Callable[[PDUAcceptedRefreshContext], None]] = None,
        superseded_callback: Optional[Callable[[PDUContextSuperseded], None]] = None,
    ):
        self.shell = shell
        self._screen_provider = screen_provider
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._accepted_refresh_callback = accepted_refresh_callback
        self._superseded_callback = superseded_callback
        self._context_revision = 0
        self._operation_serial = itertools.count(1)
        self._refresh_lane: Optional[PDURefreshLane] = None
        self._mutation_lane: Optional[PDUMutationLane] = None
        self._current_outlet_context = None
        self._state_epoch = 0
        self._attempt_states = {}

    @property
    def context_revision(self) -> int:
        return self._context_revision

    def invalidate_context(self) -> None:
        self._context_revision += 1
        self._state_epoch += 1
        self._publish_superseded("context_invalidated")
        self._refresh_lane = None
        self._mutation_lane = None
        self._current_outlet_context = None
        self._attempt_states.clear()
        self.shell.__dict__.pop("_active_request_credentials", None)
        request = self.shell.__dict__.get("_active_request")
        if request is not None:
            request["credential_context"] = self._context_revision
        screen = self._screen()
        if screen is not None:
            if hasattr(screen, "clear_pdu_mutation_state"):
                screen.clear_pdu_mutation_state()
            if hasattr(screen, "set_bulk_records_current"):
                screen.set_bulk_records_current(False)

    def shutdown(self) -> None:
        self.invalidate_context()

    def context_token(self) -> int:
        return self._context_revision

    def next_operation_id(self) -> int:
        return next(self._operation_serial)

    def request_refresh(self) -> bool:
        device_name, ip_address = self._selected_context()
        if device_name not in PDU_DEVICE_NAMES:
            return False
        return self.refresh_pdu(ip_address, device_name)

    def refresh_pdu(self, ip_address: str, device_name: Optional[str] = None) -> bool:
        device_name = device_name or self.shell.device_combo.currentText()
        print(f"=== Начинаю обновление {device_name} для {ip_address} ===")

        if not self.shell.validate_ip_address(ip_address):
            QMessageBox.warning(
                self.shell,
                "Неверный IP адрес",
                "Введите корректный IP адрес.",
            )
            return False

        try:
            self._publish_superseded("user_refresh_started")
            if not self._ensure_common_request(device_name, ip_address):
                return False
            creds_list = self._credential_candidates(device_name, ip_address)
            operation_id = self.next_operation_id()
            current_idx = self._refresh_credential_index(
                device_name,
                ip_address,
                creds_list,
            )
            worker = self._build_refresh_worker(
                device_name=device_name,
                ip_address=ip_address,
                creds_list=creds_list,
                current_idx=current_idx,
                operation_id=operation_id,
                generation=self.shell._active_request["id"],
                state_epoch=self._state_epoch,
                originating_mutation_operation_id=None,
            )
            if hasattr(self.shell, "refresh_btn"):
                self.shell.refresh_btn.setEnabled(False)
                self.shell.refresh_btn.setText("Подключение...")
            self.shell.show_progress_dialog(
                f"Подключение к {device_name} "
                f"(попытка {current_idx + 1}/{len(creds_list)})..."
            )
            self.shell.current_worker = worker
            self._thread_pool.start(worker)
            print(f"Worker для {device_name} запущен")
            return True
        except CredentialConfigurationError as error:
            message = str(error)
            self.shell.set_ui_state(UIState.REQUEST_ERROR, message)
            QMessageBox.warning(self.shell, "Настройка credentials", message)
            if hasattr(self.shell, "refresh_btn"):
                self.shell.refresh_btn.setEnabled(True)
                self.shell.refresh_btn.setText("Обновить данные")
            return False
        except Exception as error:
            print(f"Ошибка создания Worker: {error}")
            self.shell._fail_request_start(error)
            QMessageBox.critical(
                self.shell,
                "Ошибка",
                f"Не удалось создать Worker: {str(error)}",
            )
            if hasattr(self.shell, "refresh_btn"):
                self.shell.refresh_btn.setEnabled(True)
                self.shell.refresh_btn.setText("Обновить данные")
            return False

    def request_individual_mutation(self, outlet_num: int, command: str) -> bool:
        device_name, ip_address = self._selected_context()
        if device_name not in PDU_DEVICE_NAMES:
            return False
        if self.is_mutation_active():
            self._warn_busy()
            return False

        operation = {
            "on": COMMAND_ON,
            "off": COMMAND_OFF,
            "reboot": COMMAND_REBOOT,
        }.get(command)
        try:
            ensure_pdu_operation_supported(device_name, operation)
        except Exception as error:
            self.shell.set_ui_state(UIState.REQUEST_ERROR, str(error))
            QMessageBox.warning(self.shell, "Команда не поддерживается", str(error))
            return False

        self.shell.set_ui_state(
            UIState.COMMAND,
            f"Выполнение команды для розетки {outlet_num}…",
        )
        print(f"Управление PDU: розетка {outlet_num}, команда {command}")

        descriptor = None
        try:
            creds_list = self._credential_candidates(device_name, ip_address)
            operation_id = self.next_operation_id()
            current_idx = self._mutation_credential_index(
                device_name,
                ip_address,
                creds_list,
                operation_id,
                individual=True,
            )
            if current_idx >= len(creds_list):
                self.shell.set_ui_state(UIState.REQUEST_ERROR, "Нет credentials для PDU")
                return False
            creds = creds_list[current_idx]
            credential_index = None if not creds else current_idx
            self._set_active_credential_context(
                device_name,
                ip_address,
                credential_index,
            )
            descriptor = PDUOperationDescriptor(
                operation_id=operation_id,
                generation=(self.shell._active_request or {}).get(
                    "id",
                    self.shell._request_serial,
                ),
                model=device_name,
                ip_address=ip_address,
                operation=operation,
                outlet_number=outlet_num,
                credential_index=credential_index,
                credential_context=self.context_token(),
            )
            worker = self._build_mutation_worker(
                descriptor=descriptor,
                creds=creds,
                creds_list=creds_list,
                current_idx=current_idx,
                kind="individual",
            )
            self.shell.current_worker = worker
            self.shell.show_progress_dialog(f"Выполнение команды {command}...")
            self.set_command_busy(descriptor, True)
            self.set_mutation_busy(descriptor, "individual", True, worker)
            self._thread_pool.start(worker)
            return True
        except Exception as error:
            if descriptor is not None:
                self.set_command_busy(descriptor, False)
                self.set_mutation_busy(descriptor, "individual", False)
            self.shell._fail_request_start(error)
            QMessageBox.critical(
                self.shell,
                "Ошибка",
                f"Ошибка при управлении PDU: {str(error)}",
            )
            return False

    def request_bulk_mutation(self, command: str) -> bool:
        device_name, ip_address = self._selected_context()
        if device_name not in PDU_DEVICE_NAMES:
            return False
        if self.is_mutation_active():
            self._warn_busy()
            return False

        operation = {"on": BULK_COMMAND_ON, "off": BULK_COMMAND_OFF}.get(command)
        if operation is None:
            return False
        try:
            ensure_pdu_operation_supported(device_name, operation)
            outlet_records = self.current_outlet_records(device_name, ip_address)
            if outlet_records is None:
                raise ValueError("Список розеток PDU устарел. Обновите статус устройства.")
            outlet_sequence = build_pdu_bulk_outlet_sequence(
                device_name,
                outlet_records,
            )
        except Exception as error:
            self.shell.set_ui_state(UIState.REQUEST_ERROR, str(error))
            QMessageBox.warning(self.shell, "Групповая команда недоступна", str(error))
            return False

        descriptor = None
        try:
            creds_list = self._credential_candidates(device_name, ip_address)
            operation_id = self.next_operation_id()
            current_idx = self._mutation_credential_index(
                device_name,
                ip_address,
                creds_list,
                operation_id,
                individual=False,
            )
            if current_idx >= len(creds_list):
                self.shell.set_ui_state(UIState.REQUEST_ERROR, "Нет credentials для PDU")
                return False

            creds = creds_list[current_idx]
            credential_index = None if not creds else current_idx
            self._set_active_credential_context(
                device_name,
                ip_address,
                credential_index,
            )
            descriptor = PDUOperationDescriptor(
                operation_id=operation_id,
                generation=(self.shell._active_request or {}).get(
                    "id",
                    self.shell._request_serial,
                ),
                model=device_name,
                ip_address=ip_address,
                operation=operation,
                credential_index=credential_index,
                credential_context=self.context_token(),
                outlet_sequence=outlet_sequence,
            )
            worker = self._build_mutation_worker(
                descriptor=descriptor,
                creds=creds,
                creds_list=creds_list,
                current_idx=current_idx,
                kind="bulk",
            )
            self.shell.current_worker = worker
            self.set_mutation_busy(descriptor, "bulk", True, worker)
            self.shell.set_ui_state(
                UIState.COMMAND,
                "Выполнение групповой команды PDU…",
            )
            self.shell.show_progress_dialog("Выполнение групповой команды PDU...")
            self._thread_pool.start(worker)
            return True
        except Exception as error:
            if descriptor is not None:
                self.set_mutation_busy(descriptor, "bulk", False)
            self.shell._fail_request_start(error)
            QMessageBox.critical(
                self.shell,
                "Ошибка",
                f"Ошибка при групповой команде PDU: {str(error)}",
            )
            return False

    def start_reconciliation(self, origin_descriptor: PDUOperationDescriptor) -> bool:
        if self._last_accepted_mutation_id() != origin_descriptor.operation_id:
            return False
        try:
            creds_list = normalize_pdu_credential_candidates(
                origin_descriptor.model,
                getattr(self.shell, "_active_request_credentials", None)
                or self.shell._resolve_pdu_attempt_credentials(
                    origin_descriptor.model,
                    origin_descriptor.ip_address,
                ),
            )
        except Exception:
            return False
        current_idx = (
            0
            if origin_descriptor.credential_index is None
            else origin_descriptor.credential_index
        )
        if current_idx >= len(creds_list):
            return False
        worker = self._build_refresh_worker(
            device_name=origin_descriptor.model,
            ip_address=origin_descriptor.ip_address,
            creds_list=creds_list,
            current_idx=current_idx,
            operation_id=self.next_operation_id(),
            generation=origin_descriptor.generation,
            state_epoch=self._state_epoch,
            originating_mutation_operation_id=origin_descriptor.operation_id,
        )
        self.shell.current_worker = worker
        self._thread_pool.start(worker)
        return True

    def _build_refresh_worker(
        self,
        *,
        device_name: str,
        ip_address: str,
        creds_list,
        current_idx: int,
        operation_id: int,
        generation: int,
        state_epoch: int,
        originating_mutation_operation_id: Optional[int],
    ):
        creds = creds_list[current_idx]
        credential_index = None if not creds else current_idx
        self._set_active_credential_context(device_name, ip_address, credential_index)
        descriptor = PDUOperationDescriptor(
            operation_id=operation_id,
            generation=generation,
            model=device_name,
            ip_address=ip_address,
            operation=REFRESH,
            credential_index=credential_index,
            credential_context=self.context_token(),
        )
        worker = PDUOperationWorker(descriptor, credentials=creds)
        worker.is_current = lambda d: self.is_refresh_descriptor_current(d, worker)
        worker.device_name = device_name
        self._record_attempt_state(descriptor, creds_list, current_idx, "refresh")
        self._refresh_lane = PDURefreshLane(
            operation_id=descriptor.operation_id,
            expected_worker_id=id(worker),
            context=self._context_from_descriptor(descriptor),
            state_epoch=state_epoch,
            originating_mutation_operation_id=originating_mutation_operation_id,
        )
        self._bind_refresh_worker(worker, descriptor)
        return worker

    def _build_mutation_worker(
        self,
        *,
        descriptor: PDUOperationDescriptor,
        creds,
        creds_list,
        current_idx: int,
        kind: str,
    ):
        worker = PDUOperationWorker(descriptor, credentials=creds)
        worker.is_current = lambda d: self.is_mutation_descriptor_current(d, kind, worker)
        worker.device_name = descriptor.model
        self._record_attempt_state(descriptor, creds_list, current_idx, kind)
        if kind == "bulk":
            worker.signals.result.connect(
                lambda data, w=worker, d=descriptor: self.on_bulk_result(data, w, d)
            )
            worker.signals.error.connect(
                lambda error, w=worker, d=descriptor: self.on_bulk_error(error, w, d)
            )
            worker.signals.finished.connect(
                lambda w=worker, d=descriptor: self.on_bulk_finished(w, d)
            )
        else:
            worker.signals.result.connect(
                lambda data, w=worker, d=descriptor: self.on_command_result(data, w, d)
            )
            worker.signals.error.connect(
                lambda error, w=worker, d=descriptor: self.on_command_error(error, w, d)
            )
            worker.signals.finished.connect(
                lambda w=worker, d=descriptor: self.on_command_finished(w, d)
            )
        return worker

    def _bind_refresh_worker(self, worker, descriptor):
        worker.signals.result.connect(
            lambda data, w=worker, d=descriptor: self.on_refresh_result(data, w, d)
        )
        worker.signals.error.connect(
            lambda error, w=worker, d=descriptor: self.on_refresh_error(error, w, d)
        )
        worker.signals.progress.connect(
            lambda progress, w=worker, d=descriptor: self.on_refresh_progress(progress, w, d)
        )
        worker.signals.status.connect(
            lambda status, w=worker, d=descriptor: self.on_refresh_status(status, w, d)
        )
        worker.signals.finished.connect(
            lambda w=worker, d=descriptor: self.on_refresh_finished(w, d)
        )

    def start_refresh_retry_worker(self, *, descriptor, current_idx):
        attempt = self._attempt_state(descriptor)
        if attempt is None:
            return
        creds_list = attempt.candidates
        creds = creds_list[current_idx]
        credential_index = None if not creds else current_idx
        self._set_active_credential_context(
            descriptor.model,
            descriptor.ip_address,
            credential_index,
        )
        worker = self._build_refresh_worker(
            device_name=descriptor.model,
            ip_address=descriptor.ip_address,
            creds_list=creds_list,
            current_idx=current_idx,
            operation_id=descriptor.operation_id,
            generation=descriptor.generation,
            state_epoch=self._state_epoch,
            originating_mutation_operation_id=(
                self._refresh_lane.originating_mutation_operation_id
                if self._refresh_lane is not None
                else None
            ),
        )
        self.shell.current_worker = worker
        self.shell.show_progress_dialog(
            f"Подключение к {descriptor.model} "
            f"(попытка {current_idx + 1}/{len(creds_list)})..."
        )
        self._thread_pool.start(worker)

    def start_command_retry_worker(self, *, descriptor, creds_list, current_idx):
        creds = creds_list[current_idx]
        credential_index = None if not creds else current_idx
        self._set_active_credential_context(
            descriptor.model,
            descriptor.ip_address,
            credential_index,
        )
        retry_descriptor = PDUOperationDescriptor(
            operation_id=descriptor.operation_id,
            generation=descriptor.generation,
            model=descriptor.model,
            ip_address=descriptor.ip_address,
            operation=descriptor.operation,
            outlet_number=descriptor.outlet_number,
            credential_index=credential_index,
            credential_context=self.context_token(),
        )
        worker = self._build_mutation_worker(
            descriptor=retry_descriptor,
            creds=creds,
            creds_list=creds_list,
            current_idx=current_idx,
            kind="individual",
        )
        self.shell.current_worker = worker
        self.shell.show_progress_dialog(
            f"Выполнение команды {descriptor.operation}..."
        )
        self.set_command_busy(retry_descriptor, True)
        self.set_mutation_busy(retry_descriptor, "individual", True, worker)
        self._thread_pool.start(worker)

    def start_bulk_retry_worker(self, *, descriptor, creds_list, current_idx):
        creds = creds_list[current_idx]
        credential_index = None if not creds else current_idx
        self._set_active_credential_context(
            descriptor.model,
            descriptor.ip_address,
            credential_index,
        )
        retry_descriptor = PDUOperationDescriptor(
            operation_id=descriptor.operation_id,
            generation=descriptor.generation,
            model=descriptor.model,
            ip_address=descriptor.ip_address,
            operation=descriptor.operation,
            credential_index=credential_index,
            credential_context=self.context_token(),
            outlet_sequence=descriptor.outlet_sequence,
        )
        worker = self._build_mutation_worker(
            descriptor=retry_descriptor,
            creds=creds,
            creds_list=creds_list,
            current_idx=current_idx,
            kind="bulk",
        )
        self.shell.current_worker = worker
        self.set_mutation_busy(retry_descriptor, "bulk", True, worker)
        self.shell.show_progress_dialog("Выполнение групповой команды PDU...")
        self._thread_pool.start(worker)

    def is_common_context_current(self, context: PDUCommonContext) -> bool:
        request = self.shell.__dict__.get("_active_request")
        return bool(
            request
            and request.get("id") == context.generation
            and request.get("device") == context.model
            and request.get("ip") == context.ip_address
            and request.get("credential_context")
            == context.credential_context_revision
        )

    def is_descriptor_common_current(self, descriptor: PDUOperationDescriptor) -> bool:
        return self.is_common_context_current(self._context_from_descriptor(descriptor))

    def is_refresh_descriptor_current(self, descriptor, worker=None) -> bool:
        lane = self._refresh_lane
        if lane is None:
            return self.is_descriptor_common_current(descriptor)
        if worker is not None and lane.expected_worker_id != id(worker):
            return False
        return (
            lane.operation_id == descriptor.operation_id
            and lane.context == self._context_from_descriptor(descriptor)
            and self.is_common_context_current(lane.context)
            and lane.state_epoch >= self._state_epoch_at_last_mutation()
        )

    def is_mutation_descriptor_current(self, descriptor, kind=None, worker=None) -> bool:
        lane = self._mutation_lane
        if lane is None:
            return self.is_descriptor_common_current(descriptor)
        if kind is not None and lane.mutation_kind != kind:
            return False
        if worker is not None and lane.expected_worker_id != id(worker):
            return False
        return (
            lane.operation_id == descriptor.operation_id
            and lane.context == self._context_from_descriptor(descriptor)
            and self.is_common_context_current(lane.context)
        )

    def remember_outlet_context(self, data, descriptor: PDUOperationDescriptor) -> None:
        if "outlets" not in (data or {}):
            return
        self._current_outlet_context = {
            "descriptor": descriptor,
            "outlets": tuple(dict(outlet) for outlet in (data.get("outlets") or ())),
        }
        screen = self._screen()
        if screen is not None and hasattr(screen, "set_bulk_records_current"):
            screen.set_bulk_records_current(True)

    def current_outlet_records(self, device_name: str, ip_address: str):
        context = self._current_outlet_context
        if not context:
            return None
        descriptor = context.get("descriptor")
        if not isinstance(descriptor, PDUOperationDescriptor):
            return None
        if descriptor.model != device_name or descriptor.ip_address != ip_address:
            return None
        if not self.is_descriptor_common_current(descriptor):
            return None
        return context.get("outlets")

    def is_mutation_active(self) -> bool:
        lane = self._mutation_lane
        return bool(lane and self.is_common_context_current(lane.context))

    def set_mutation_busy(
        self,
        descriptor: PDUOperationDescriptor,
        kind: str,
        busy: bool,
        worker=None,
    ) -> None:
        screen = self._screen()
        if busy:
            self._state_epoch += 1
            self._last_mutation_epoch = self._state_epoch
            self._mutation_lane = PDUMutationLane(
                operation_id=descriptor.operation_id,
                expected_worker_id=id(worker) if worker is not None else 0,
                mutation_kind=kind,
                context=self._context_from_descriptor(descriptor),
            )
            if screen is not None and hasattr(screen, "set_pdu_mutation_state"):
                screen.set_pdu_mutation_state(descriptor.operation_id, kind, True)
            return

        if self.is_mutation_descriptor_current(descriptor, kind, worker):
            self._mutation_lane = None
            self._last_accepted_mutation_operation_id = descriptor.operation_id
            if screen is not None and hasattr(screen, "set_pdu_mutation_state"):
                screen.set_pdu_mutation_state(descriptor.operation_id, kind, False)

    def set_command_busy(self, descriptor: PDUOperationDescriptor, busy: bool) -> None:
        screen = self._screen()
        if screen is None or descriptor.outlet_number is None:
            return
        setter = getattr(screen, "set_outlet_command_state", None)
        if setter is None:
            return
        setter(descriptor.outlet_number, descriptor.operation, busy)

    def on_refresh_result(self, data, worker, descriptor):
        if not self.is_refresh_descriptor_current(descriptor, worker):
            self._clear_attempt_state(descriptor)
            return
        self._commit_refresh_success_if_allowed(data, descriptor)
        self.shell._discard_credential_attempt_plan(
            descriptor.model,
            descriptor.ip_address,
            descriptor.operation_id,
        )
        self._clear_attempt_state(descriptor)
        self.remember_outlet_context(data, descriptor)
        rendered = dict(data or {})
        rendered["_credential_policy_handled"] = True
        self.shell.on_device_data_received(rendered, worker, descriptor.generation)
        lane = self._refresh_lane
        if lane is not None and lane.originating_mutation_operation_id is None:
            self._publish_accepted_refresh(descriptor)

    def on_refresh_error(self, error_info, worker, descriptor):
        if not self.is_refresh_descriptor_current(descriptor, worker):
            self._clear_attempt_state(descriptor)
            return
        error_type = error_info[0]
        error = error_info[1]
        if error_type == CodecFailureCategory.AUTHENTICATION.value:
            next_idx = self._advance_attempt_state(descriptor)
            if next_idx is not None:
                attempt = self._attempt_state(descriptor)
                self.shell.set_ui_state(
                    UIState.LOADING,
                    f"Ошибка авторизации; попытка {next_idx + 1} из {len(attempt.candidates)}...",
                )
                self.start_refresh_retry_worker(descriptor=descriptor, current_idx=next_idx)
                return
        self.shell._discard_credential_attempt_plan(
            descriptor.model,
            descriptor.ip_address,
            descriptor.operation_id,
        )
        self._clear_attempt_state(descriptor)
        self.shell.hide_progress_dialog()
        self.shell.set_ui_state(UIState.REQUEST_ERROR, f"Ошибка PDU: {error}")
        QMessageBox.critical(self.shell, "Ошибка", f"Ошибка PDU: {error}")

    def on_refresh_progress(self, progress, worker, descriptor):
        if self.is_refresh_descriptor_current(descriptor, worker):
            self.shell.on_progress_update(progress, worker, descriptor.generation)

    def on_refresh_status(self, status, worker, descriptor):
        if self.is_refresh_descriptor_current(descriptor, worker):
            self.shell.on_status_update(status, worker, descriptor.generation)

    def on_refresh_finished(self, worker, descriptor):
        if not self.is_refresh_descriptor_current(descriptor, worker):
            return
        self.shell.on_worker_finished(worker, descriptor.generation)

    def on_bulk_result(self, data, worker, descriptor):
        from_lane = self._mutation_lane is not None
        if not self.is_mutation_descriptor_current(descriptor, "bulk", worker):
            self._clear_attempt_state(descriptor)
            return
        self.shell.hide_progress_dialog()
        self.set_mutation_busy(descriptor, "bulk", False, worker)
        self.shell._discard_credential_attempt_plan(
            descriptor.model,
            descriptor.ip_address,
            descriptor.operation_id,
        )
        self._clear_attempt_state(descriptor)
        if data.get("success"):
            if (
                (
                    descriptor.model == "Aten PE8208AV"
                    or (
                        descriptor.model == "Extron IPL T PCS4i"
                        and data.get("_credential_used") is True
                    )
                )
                and descriptor.credential_index is not None
            ):
                self.shell.set_current_credential_index(
                    descriptor.model,
                    descriptor.credential_index,
                    descriptor.ip_address,
                )
            completed = len(data.get("successful_outlets") or ())
            self.shell.set_ui_state(
                UIState.CONNECTED,
                f"Групповая команда PDU выполнена: {completed}",
            )
            QMessageBox.information(
                self.shell,
                "Успех",
                f"Групповая команда выполнена для {completed} розеток.",
            )
            if from_lane:
                self.start_reconciliation(descriptor)
            return

        terminal_state = data.get("terminal_state")
        completed = len(data.get("successful_outlets") or ())
        stopping_outlet = data.get("stopping_outlet")
        if terminal_state in {"partial_failure", "failure_before_completion"}:
            message = (
                f"Групповая команда остановлена на розетке {stopping_outlet}. "
                f"Успешно обработано: {completed}."
            )
            self.shell.set_ui_state(UIState.REQUEST_ERROR, message)
            QMessageBox.warning(self.shell, "Групповая команда остановлена", message)
            if completed or data.get("state_changing_send_attempted"):
                if from_lane:
                    self.start_reconciliation(descriptor)
            return

        message = "Групповая команда PDU не была завершена."
        self.shell.set_ui_state(UIState.REQUEST_ERROR, message)
        QMessageBox.warning(self.shell, "Групповая команда PDU", message)
        if data.get("state_changing_send_attempted"):
            if from_lane:
                self.start_reconciliation(descriptor)

    def on_bulk_error(self, error_info, worker, descriptor):
        from_lane = self._mutation_lane is not None
        if not self.is_mutation_descriptor_current(descriptor, "bulk", worker):
            self._clear_attempt_state(descriptor)
            return
        self.shell.hide_progress_dialog()
        error_type = error_info[0]
        error = error_info[1]
        metadata = error_info[3] if len(error_info) > 3 and isinstance(error_info[3], dict) else {}
        if (
            error_type == CodecFailureCategory.AUTHENTICATION.value
            and metadata.get("state_changing_send_attempted") is False
        ):
            attempt = self._attempt_state(descriptor)
            next_idx = self._advance_attempt_state(descriptor)
            if next_idx is not None:
                attempt = self._attempt_state(descriptor)
                creds_list = attempt.candidates
                self.shell.set_ui_state(
                    UIState.LOADING,
                    f"Ошибка авторизации; попытка {next_idx + 1} из {len(creds_list)}...",
                )
                self.set_mutation_busy(descriptor, "bulk", False, worker)
                self.start_bulk_retry_worker(
                    descriptor=descriptor,
                    creds_list=creds_list,
                    current_idx=next_idx,
                )
                return
        self.shell._discard_credential_attempt_plan(
            descriptor.model,
            descriptor.ip_address,
            descriptor.operation_id,
        )
        self._clear_attempt_state(descriptor)
        self.set_mutation_busy(descriptor, "bulk", False, worker)
        self.shell.set_ui_state(UIState.REQUEST_ERROR, f"Ошибка групповой команды PDU: {error}")
        QMessageBox.critical(self.shell, "Ошибка", f"Ошибка групповой команды PDU: {error}")
        if metadata.get("state_changing_send_attempted"):
            if from_lane:
                self.start_reconciliation(descriptor)

    def on_bulk_finished(self, worker, descriptor):
        if not self.is_mutation_descriptor_current(descriptor, "bulk", worker):
            return
        self.shell.hide_progress_dialog()
        self.set_mutation_busy(descriptor, "bulk", False, worker)

    def on_command_result(self, data, worker, descriptor):
        from_lane = self._mutation_lane is not None
        if not self.is_mutation_descriptor_current(descriptor, "individual", worker):
            self._clear_attempt_state(descriptor)
            return
        self.shell.hide_progress_dialog()
        self.set_command_busy(descriptor, False)
        self.set_mutation_busy(descriptor, "individual", False, worker)
        self._clear_attempt_state(descriptor)
        if data.get("success"):
            if (
                descriptor.model == "Extron IPL T PCS4i"
                and data.get("_credential_used") is True
                and descriptor.credential_index is not None
            ):
                self.shell.set_current_credential_index(
                    descriptor.model,
                    descriptor.credential_index,
                    descriptor.ip_address,
                )
                self.shell._discard_credential_attempt_plan(
                    descriptor.model,
                    descriptor.ip_address,
                    descriptor.operation_id,
                )
            elif descriptor.model == "Extron IPL T PCS4i":
                self.shell._discard_credential_attempt_plan(
                    descriptor.model,
                    descriptor.ip_address,
                    descriptor.operation_id,
                )
            self.shell.set_ui_state(
                UIState.CONNECTED,
                f"Команда для розетки {data.get('outlet_number')} выполнена",
            )
            QMessageBox.information(
                self.shell,
                "Успех",
                f"Команда '{data.get('operation')}' для розетки {data.get('outlet_number')} выполнена",
            )
            if from_lane:
                self.start_reconciliation(descriptor)
        else:
            if descriptor.model == "Extron IPL T PCS4i":
                self.shell._discard_credential_attempt_plan(
                    descriptor.model,
                    descriptor.ip_address,
                    descriptor.operation_id,
                )
            self.shell.set_ui_state(UIState.REQUEST_ERROR, "Команда PDU не выполнена")
            QMessageBox.warning(self.shell, "Ошибка", "Не удалось выполнить команду PDU")
            if data.get("state_changing_send_attempted"):
                if from_lane:
                    self.start_reconciliation(descriptor)

    def on_command_error(self, error_info, worker, descriptor):
        from_lane = self._mutation_lane is not None
        if not self.is_mutation_descriptor_current(descriptor, "individual", worker):
            self._clear_attempt_state(descriptor)
            return
        self.shell.hide_progress_dialog()
        error_type = error_info[0]
        error = error_info[1]
        metadata = error_info[3] if len(error_info) > 3 and isinstance(error_info[3], dict) else {}
        if (
            descriptor.model == "Extron IPL T PCS4i"
            and error_type == CodecFailureCategory.AUTHENTICATION.value
            and metadata.get("state_changing_send_attempted") is False
        ):
            attempt = self._attempt_state(descriptor)
            next_idx = self._advance_attempt_state(descriptor)
            if next_idx is not None:
                attempt = self._attempt_state(descriptor)
                creds_list = attempt.candidates
                self.shell.set_ui_state(
                    UIState.LOADING,
                    f"Ошибка авторизации; попытка {next_idx + 1} из {len(creds_list)}...",
                )
                self.set_command_busy(descriptor, False)
                self.set_mutation_busy(descriptor, "individual", False, worker)
                self.start_command_retry_worker(
                    descriptor=descriptor,
                    creds_list=creds_list,
                    current_idx=next_idx,
                )
                return
            self.shell._discard_credential_attempt_plan(
                descriptor.model,
                descriptor.ip_address,
                descriptor.operation_id,
            )
            self._clear_attempt_state(descriptor)
        if error_type == "indeterminate_outcome":
            if descriptor.model == "Extron IPL T PCS4i":
                self.shell._discard_credential_attempt_plan(
                    descriptor.model,
                    descriptor.ip_address,
                    descriptor.operation_id,
                )
            self._clear_attempt_state(descriptor)
            message = (
                "Не удалось достоверно определить итог команды. "
                "Проверьте состояние устройства перед повторной операцией."
            )
            self.shell.set_ui_state(UIState.REQUEST_ERROR, message)
            QMessageBox.warning(self.shell, "Итог команды неизвестен", message)
            self.set_command_busy(descriptor, False)
            self.set_mutation_busy(descriptor, "individual", False, worker)
            if from_lane:
                self.start_reconciliation(descriptor)
            return
        if error_type == "command_failed":
            if descriptor.model == "Extron IPL T PCS4i":
                self.shell._discard_credential_attempt_plan(
                    descriptor.model,
                    descriptor.ip_address,
                    descriptor.operation_id,
                )
            self._clear_attempt_state(descriptor)
            message = "Команда PDU была отклонена устройством или не достигла запрошенного состояния."
            self.shell.set_ui_state(UIState.REQUEST_ERROR, message)
            QMessageBox.warning(self.shell, "Команда PDU не выполнена", message)
            self.set_command_busy(descriptor, False)
            self.set_mutation_busy(descriptor, "individual", False, worker)
            if from_lane:
                self.start_reconciliation(descriptor)
            return
        if descriptor.model == "Extron IPL T PCS4i":
            self.shell._discard_credential_attempt_plan(
                descriptor.model,
                descriptor.ip_address,
                descriptor.operation_id,
            )
        self._clear_attempt_state(descriptor)
        self.shell.set_ui_state(UIState.REQUEST_ERROR, f"Ошибка команды PDU: {error}")
        QMessageBox.critical(self.shell, "Ошибка", f"Ошибка при управлении PDU: {error}")
        self.set_command_busy(descriptor, False)
        self.set_mutation_busy(descriptor, "individual", False, worker)
        if metadata.get("state_changing_send_attempted"):
            if from_lane:
                self.start_reconciliation(descriptor)

    def on_command_finished(self, worker, descriptor):
        if not self.is_mutation_descriptor_current(descriptor, "individual", worker):
            return
        self.shell.hide_progress_dialog()
        self.set_command_busy(descriptor, False)
        self.set_mutation_busy(descriptor, "individual", False, worker)

    def _credential_candidates(self, device_name, ip_address):
        creds_list = getattr(self.shell, "_active_request_credentials", None)
        if creds_list is None:
            creds_list = self.shell._resolve_pdu_attempt_credentials(
                device_name,
                ip_address,
            )
        else:
            creds_list = normalize_pdu_credential_candidates(device_name, creds_list)
        self.shell._active_request_credentials = creds_list
        return creds_list

    def _refresh_credential_index(self, device_name, ip_address, creds_list):
        return self.shell.get_valid_current_credential_index(
            device_name,
            creds_list,
            ip_address,
        )

    def _mutation_credential_index(
        self,
        device_name,
        ip_address,
        creds_list,
        operation_id,
        *,
        individual: bool,
    ) -> int:
        if individual and not self.shell._is_pcs4i_device(device_name):
            return self.shell.get_valid_current_credential_index(
                device_name,
                creds_list,
                ip_address,
            )
        return self.shell._credential_attempt_index(
            device_name,
            creds_list,
            ip_address,
            operation_id,
        )

    def _set_active_credential_context(self, device_name, ip_address, credential_index):
        request = self.shell.__dict__.get("_active_request")
        if not request:
            return
        if request.get("device") != device_name or request.get("ip") != ip_address:
            return
        request["credential_index"] = credential_index

    def _ensure_common_request(self, device_name, ip_address) -> bool:
        request = self.shell.__dict__.get("_active_request")
        screen = self._screen()
        same_context = bool(
            request
            and request.get("device") == device_name
            and request.get("ip") == ip_address
            and request.get("credential_context") == self.context_token()
        )
        if not same_context:
            self.shell._begin_request(device_name, ip_address, screen)
            if screen is not None and hasattr(screen, "clear_data"):
                screen.clear_data()
        else:
            self.shell.set_ui_state(
                UIState.LOADING,
                f"Подключение к {device_name} ({ip_address})…",
                screen,
            )
        if (
            screen is not None
            and hasattr(self.shell, "screen_container")
            and self.shell.screen_container.currentWidget() is not screen
        ):
            self.shell.screen_container.setCurrentWidget(screen)
        if screen is not None and hasattr(screen, "set_ui_state"):
            screen.set_ui_state(UIState.LOADING, "Загрузка данных…")
        return True

    def _context_from_descriptor(self, descriptor: PDUOperationDescriptor) -> PDUCommonContext:
        return PDUCommonContext(
            generation=descriptor.generation,
            model=descriptor.model,
            ip_address=descriptor.ip_address,
            credential_context_revision=descriptor.credential_context or 0,
        )

    def _publish_accepted_refresh(self, descriptor: PDUOperationDescriptor) -> None:
        callback = self._accepted_refresh_callback
        if callback is None:
            return
        callback(
            PDUAcceptedRefreshContext(
                pdu_generation=descriptor.generation,
                refresh_operation_id=descriptor.operation_id,
                model=descriptor.model,
                ip_address=descriptor.ip_address,
                credential_context_revision=descriptor.credential_context or 0,
            )
        )

    def _publish_superseded(self, reason: str) -> None:
        callback = self._superseded_callback
        if callback is None:
            return
        callback(
            PDUContextSuperseded(
                pdu_generation_or_revision=self._context_revision,
                reason=reason,
            )
        )

    def _screen(self):
        return self._screen_provider()

    def _selected_context(self) -> tuple[str, str]:
        return (
            self.shell.device_combo.currentText(),
            self.shell.ip_entry.text().strip(),
        )

    def _warn_busy(self):
        QMessageBox.warning(
            self.shell,
            "Команда PDU занята",
            "Дождитесь завершения текущей операции PDU.",
        )

    def _state_epoch_at_last_mutation(self) -> int:
        return getattr(self, "_last_mutation_epoch", 0)

    def _last_accepted_mutation_id(self):
        return getattr(self, "_last_accepted_mutation_operation_id", None)

    def _attempt_key(self, descriptor: PDUOperationDescriptor):
        return descriptor.operation_id

    def _record_attempt_state(self, descriptor, creds_list, current_idx, lane) -> None:
        self._attempt_states[self._attempt_key(descriptor)] = PDUAttemptState(
            candidates=tuple(creds_list or ()),
            current_index=current_idx,
            lane=lane,
        )

    def _attempt_state(self, descriptor):
        return self._attempt_states.get(self._attempt_key(descriptor))

    def _clear_attempt_state(self, descriptor) -> None:
        self._attempt_states.pop(self._attempt_key(descriptor), None)

    def _advance_attempt_state(self, descriptor):
        attempt = self._attempt_state(descriptor)
        if attempt is None:
            return None
        next_idx = self.shell._advance_request_credential_attempt(
            descriptor.model,
            attempt.candidates,
            descriptor.ip_address,
            attempt.current_index,
            descriptor.operation_id,
        )
        if next_idx is None:
            self._clear_attempt_state(descriptor)
            return None
        self._attempt_states[self._attempt_key(descriptor)] = PDUAttemptState(
            candidates=attempt.candidates,
            current_index=next_idx,
            lane=attempt.lane,
        )
        return next_idx

    def _commit_refresh_success_if_allowed(self, data, descriptor) -> None:
        if descriptor.credential_index is None:
            return
        if descriptor.model == "Aten PE8208AV":
            self.shell.set_current_credential_index(
                descriptor.model,
                descriptor.credential_index,
                descriptor.ip_address,
            )
            return
        if (
            descriptor.model == "Extron IPL T PCS4i"
            and (data or {}).get("_credential_used") is True
        ):
            self.shell.set_current_credential_index(
                descriptor.model,
                descriptor.credential_index,
                descriptor.ip_address,
            )
