"""Polling workers for matrix switch diagnostics."""

from PyQt5.QtCore import QRunnable, pyqtSlot

from core.parser import ExtronIN1804DataParser
from core.redaction import redact_data
from core.workers.common import WorkerSignals, _emit_error, _worker_secrets
from handlers.extron.in1804 import ExtronIN1804Handler


class ExtronIN1804Worker(QRunnable):
    """Worker для опроса матрицы Extron IN1804"""

    def __init__(self, ip_address, port=22023, username=None, password=None):
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.signals = WorkerSignals()
        self.handler = None

    @pyqtSlot()
    def run(self):
        """Запуск процесса опроса"""
        try:
            self.signals.status.emit("Подключение к матрице Extron IN1804...")
            self.signals.progress.emit(10)

            # Создаем и подключаем обработчик
            self.handler = ExtronIN1804Handler(
                ip_address=self.ip_address,
                port=self.port,
                username=self.username,
                password=self.password
            )
            self.handler.log_callback = redacted_callback(self.signals.terminal_log.emit, _worker_secrets(self))

            self.signals.status.emit("Установка соединения...")
            self.signals.progress.emit(20)
            self.handler.connect()

            self.signals.status.emit("Получение информации об устройстве...")
            self.signals.progress.emit(30)
            status = self.handler.get_full_status()

            self.signals.status.emit("Парсинг данных...")
            self.signals.progress.emit(80)

            # Парсим данные
            parser = ExtronIN1804DataParser()
            parsed_data = parser.parse(status)

            # Добавляем IP адрес
            parsed_data['ip_address'] = self.ip_address

            self.signals.progress.emit(100)
            self.signals.status.emit("Готово!")
            self.signals.result.emit(redact_data(parsed_data, _worker_secrets(self)))

        except Exception as e:
            import traceback
            error_message, error_traceback = _safe_error(e, _worker_secrets(self))
            if "authentication" in error_message.lower():
                self.signals.error.emit(("authentication_error", error_message, error_traceback))
            else:
                self.signals.error.emit(("ExtronIN1804Error", error_message, error_traceback))

        finally:
            if self.handler:
                self.handler.disconnect()
            self.signals.finished.emit()
