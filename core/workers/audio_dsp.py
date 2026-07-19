"""Polling workers for audio DSP diagnostics."""

from PyQt5.QtCore import QRunnable, pyqtSlot

from core.exceptions import AuthenticationError
from core.parser import BiampTesiraForteCIDataParser
from core.redaction import redact_data
from core.workers.common import WorkerSignals, _emit_error, _worker_secrets


class BiampTesiraForteCIWorker(QRunnable):
    """Read-only worker for Biamp Tesira Forte CI audio-DSP signal status."""

    def __init__(self, ip_address: str, username: str = None, password: str = None):
        super().__init__()
        self.ip_address = ip_address
        self.username = username
        self.password = password
        self.signals = WorkerSignals()
        self.creds_list = []
        self.current_idx = 0
        self.device_name = "Biamp Tesira Forte CI"

    @pyqtSlot()
    def run(self):
        from handlers.biamp.tesira_forte_ci import BiampTesiraForteCIHandler

        handler = None
        try:
            if not self.username or not self.password:
                raise AuthenticationError(
                    "Credentials are required for Biamp Tesira Forte CI before connecting."
                )
            self.signals.status.emit("Подключение к Biamp Tesira Forte CI...")
            self.signals.progress.emit(15)
            self.signals.terminal_log.emit(
                f"[connect] Biamp Tesira Forte CI {self.ip_address}"
            )

            handler = BiampTesiraForteCIHandler(
                ip_address=self.ip_address,
                username=self.username,
                password=self.password,
            )
            handler.connect()
            self.signals.connected.emit()

            self.signals.status.emit("Получение источников сигнала...")
            self.signals.progress.emit(55)
            raw_data = handler.get_status()

            self.signals.status.emit("Обработка данных Biamp...")
            self.signals.progress.emit(80)
            parsed_data = BiampTesiraForteCIDataParser.parse_raw_data(raw_data)
            parsed_data["ip_address"] = self.ip_address

            self.signals.progress.emit(100)
            self.signals.result.emit(redact_data(parsed_data, _worker_secrets(self)))
            self.signals.disconnected.emit()
        except AuthenticationError as exc:
            _emit_error(self, "authentication_error", exc, trace=False)
        except Exception as exc:
            _emit_error(self, "connection_error", exc)
        finally:
            if handler:
                try:
                    handler.disconnect()
                except Exception:
                    pass
            self.signals.finished.emit()
