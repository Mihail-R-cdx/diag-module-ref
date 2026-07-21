"""Long-lived Extron DMP meter polling workers."""

import time

from PyQt5.QtCore import QRunnable, pyqtSlot

from core.dmp64_plus import (
    DMPCancelled,
    DMPCancellationToken,
    DMPTransactionTimeout,
    DMPUnsupportedModel,
    SELECTOR_MODEL as DMP64_PLUS_MODEL,
    SIS_PORT as DMP64_PLUS_PORT,
    wait_cancelable,
)
from core.exceptions import AuthenticationError, ConnectionError
from core.redaction import redact_data
from core.workers.common import WorkerSignals, _emit_error, _worker_secrets


class ExtronDMP64PlusMeterWorker(QRunnable):
    """Long-lived DMP 64 Plus physical meter polling worker."""

    def __init__(
        self,
        ip_address: str,
        username: str = None,
        password: str = None,
        *,
        cancellation: DMPCancellationToken | None = None,
        handler_factory=None,
        poll_interval: float = 1.0,
        max_cycles: int | None = None,
    ):
        super().__init__()
        self.ip_address = ip_address
        self.username = username
        self.password = password
        self.cancellation = cancellation or DMPCancellationToken()
        self.handler_factory = handler_factory
        self.poll_interval = poll_interval
        self.max_cycles = max_cycles
        self.signals = WorkerSignals()
        self.current_idx = 0
        self.device_name = DMP64_PLUS_MODEL
        self._credential_success_emitted = False

    @pyqtSlot()
    def run(self):
        handler = None
        try:
            if self.cancellation.is_cancelled():
                return
            if not self.username or not self.password:
                raise AuthenticationError(
                    "Credentials are required for Extron DMP 64 Plus before connecting."
                )

            from handlers.extron.dmp64_plus import ExtronDMP64PlusHandler

            handler_class = self.handler_factory or ExtronDMP64PlusHandler
            self.signals.status.emit("Подключение к Extron DMP 64 Plus...")
            self.signals.progress.emit(10)
            handler = handler_class(
                ip_address=self.ip_address,
                port=DMP64_PLUS_PORT,
                username=self.username,
                password=self.password,
            )
            self.cancellation.raise_if_cancelled()
            handler.connect(self.cancellation)
            self.signals.connected.emit()

            cycles = 0
            while not self.cancellation.is_cancelled():
                cycle_started = time.monotonic()
                self.cancellation.raise_if_cancelled()
                self.signals.status.emit("Чтение meter snapshot DMP...")
                self.signals.progress.emit(40)
                snapshot = handler.get_meter_snapshot(self.cancellation)
                self.cancellation.raise_if_cancelled()
                cycles += 1
                snapshot["_continuous_update"] = True
                snapshot["_credential_used"] = (
                    not self._credential_success_emitted
                    and bool(self.username or self.password)
                )
                self._credential_success_emitted = True
                self.signals.progress.emit(100)
                safe_snapshot = redact_data(snapshot, _worker_secrets(self))
                safe_snapshot["_continuous_update"] = snapshot["_continuous_update"]
                safe_snapshot["_credential_used"] = snapshot["_credential_used"]
                self.signals.result.emit(safe_snapshot)

                if self.max_cycles is not None and cycles >= self.max_cycles:
                    break
                remaining_wait = max(0.0, self.poll_interval - (time.monotonic() - cycle_started))
                wait_cancelable(self.cancellation, remaining_wait)
        except DMPCancelled:
            pass
        except AuthenticationError as exc:
            _emit_error(self, "authentication_error", exc, trace=False)
        except DMPUnsupportedModel as exc:
            _emit_error(self, "unsupported_device", exc, trace=False)
        except DMPTransactionTimeout as exc:
            _emit_error(self, "transport_session_failure", exc, trace=False)
        except ConnectionError as exc:
            _emit_error(self, "transport_session_failure", exc, trace=False)
        except Exception as exc:
            _emit_error(self, "transport_session_failure", exc)
        finally:
            if handler is not None:
                try:
                    handler.disconnect()
                except Exception:
                    pass
            self.signals.finished.emit()
