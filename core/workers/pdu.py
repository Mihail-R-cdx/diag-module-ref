"""Background workers for PDU refresh and control operations."""

from typing import Dict, Optional

from PyQt5.QtCore import QRunnable, pyqtSlot

from core.exceptions import (
    AuthenticationError,
    CommandError,
    CommandOutcomeUnknownError,
    CommandRejectedError,
    ConnectionError,
    CredentialRequired,
    UnsupportedOperationError,
)
from core.pdu import (
    REFRESH,
    PDUOperationDescriptor,
    execute_pdu_bulk,
    execute_pdu_command,
    execute_pdu_refresh,
    is_pdu_bulk_operation,
    normalize_pdu_credentials,
)
from core.redaction import redact_data
from core.workers.common import WorkerSignals, _emit_error, _safe_error, _worker_secrets


class PDUOperationWorker(QRunnable):
    """Background refresh/control worker for model-aware PDU operations."""

    def __init__(
        self,
        descriptor: PDUOperationDescriptor,
        credentials: Optional[Dict] = None,
        is_current=None,
        handler_factory=None,
    ):
        super().__init__()
        self.descriptor = descriptor
        self.ip_address = descriptor.ip_address
        self.device_name = descriptor.model
        self.operation = descriptor.operation
        self.outlet_number = descriptor.outlet_number
        self.credentials = normalize_pdu_credentials(descriptor.model, credentials or {})
        self.username = self.credentials.get("username")
        self.password = self.credentials.get("password")
        self.current_idx = descriptor.credential_index or 0
        self.creds_list = []
        self.is_current = is_current or (lambda _descriptor: True)
        self.handler_factory = handler_factory
        self.bulk_delay = None
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            self.signals.progress.emit(10)
            if self.operation == REFRESH:
                self.signals.status.emit("Получение статуса PDU...")
                result = execute_pdu_refresh(
                    descriptor=self.descriptor,
                    credentials=self.credentials,
                    is_current=self.is_current,
                    **self._factory_kwargs(),
                )
            elif is_pdu_bulk_operation(self.operation):
                self.signals.status.emit("Выполнение групповой команды PDU...")
                kwargs = self._factory_kwargs()
                if self.bulk_delay is not None:
                    kwargs["delay"] = self.bulk_delay
                result = execute_pdu_bulk(
                    descriptor=self.descriptor,
                    credentials=self.credentials,
                    is_current=self.is_current,
                    **kwargs,
                )
            else:
                self.signals.status.emit("Выполнение команды PDU...")
                result = execute_pdu_command(
                    descriptor=self.descriptor,
                    credentials=self.credentials,
                    is_current=self.is_current,
                    **self._factory_kwargs(),
                )
            self.signals.progress.emit(100)
            if result.get("_outcome") == "stale":
                return
            self.signals.result.emit(redact_data(result, _worker_secrets(self)))
        except CredentialRequired as error:
            _emit_error(self, "credential_required", error, trace=False)
        except AuthenticationError as error:
            message, _details = _safe_error(error, _worker_secrets(self))
            self.signals.error.emit(
                (
                    "authentication_error",
                    message,
                    "",
                    {"state_changing_send_attempted": False},
                )
            )
        except UnsupportedOperationError as error:
            _emit_error(self, "unsupported_operation", error, trace=False)
        except CommandRejectedError as error:
            _emit_error(self, "command_failed", error, trace=False)
        except CommandOutcomeUnknownError as error:
            _emit_error(self, "indeterminate_outcome", error, trace=False)
        except CommandError as error:
            _emit_error(self, "command_failed", error, trace=False)
        except ConnectionError as error:
            _emit_error(self, "connection_error", error, trace=False)
        except Exception as error:
            _emit_error(self, "connection_error", error)
        finally:
            self.signals.finished.emit()

    def _factory_kwargs(self):
        if self.handler_factory is None:
            return {}
        return {"handler_factory": self.handler_factory}



class AtenPDUWorker(QRunnable):
    """Worker для асинхронной работы с PDU Aten"""

    def __init__(self, ip_address: str, port: int = 443,
                 username: str = None, password: str = None):
        super().__init__()

        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.signals = WorkerSignals()

        self.handler = None
        self.creds_list = []  # Будет заполнено в refresh_data
        self.current_idx = 0
        self.device_name = "Aten PE8208AV"

    @pyqtSlot()
    def run(self):
        """Основной метод работы в потоке"""
        from handlers.aten.pdu import AtenPDUHandler

        try:
            if not self.username or not self.password:
                raise AuthenticationError(
                    'Credentials are required for Aten PDU before connecting.'
                )
            self.handler = AtenPDUHandler(
                ip_address=self.ip_address,
                port=self.port,
                username=self.username,
                password=self.password
            )

            self.signals.progress.emit(10)
            self.signals.status.emit("Подключение к PDU...")

            if not self.handler.connect():
                raise AuthenticationError(
                    "Не удалось аутентифицироваться с указанными credentials"
                )

            self.signals.progress.emit(60)
            self.signals.status.emit("Получение статуса розеток...")
            outlets = self.handler.get_outlets_status()

            self.signals.progress.emit(80)
            self.signals.status.emit("Получение информации об устройстве...")
            device_info = self.handler.get_device_info()

            result = {
                'device_info': device_info,
                'outlets': outlets,
                'ip_address': self.ip_address,
                'model': 'PE8208AV',
                'manufacturer': 'Aten',
                'type': 'pdu'
            }

            self.signals.progress.emit(100)
            self.signals.result.emit(redact_data(result, _worker_secrets(self)))

        except AuthenticationError as e:
            _emit_error(self, 'authentication_error', e, trace=False)
        except ConnectionError as e:
            _emit_error(self, 'connection_error', e, trace=False)
        except Exception as e:
            _emit_error(self, 'connection_error', e)
        finally:
            if self.handler:
                try:
                    self.handler.disconnect()
                except Exception:
                    pass
                self.handler = None
            self.signals.finished.emit()
