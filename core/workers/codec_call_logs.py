"""Background workers for codec call-log operations."""

from PyQt5.QtCore import QRunnable, pyqtSlot

from core.redaction import redact_exception
from core.workers.common import WorkerSignals


class PolycomCallLogWorker(QRunnable):
    """Load Polycom call records without blocking the Qt event loop."""

    def __init__(self, handler_class, handler_kwargs):
        super().__init__()
        self.handler_class = handler_class
        self.handler_kwargs = dict(handler_kwargs)
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        handler = None
        try:
            handler = self.handler_class(**self.handler_kwargs)
            handler.connect()
            records = handler.get_call_records()
            self.signals.result.emit({"records": list(records or [])})
        except Exception as error:
            secrets = (
                self.handler_kwargs.get("username"),
                self.handler_kwargs.get("password"),
            )
            message = "Polycom call log request failed: {}".format(
                redact_exception(error, secrets)
            )
            self.signals.error.emit(
                (
                    "PolycomCallLogError",
                    message,
                    "",
                )
            )
        finally:
            if handler is not None:
                try:
                    handler.disconnect()
                except Exception:
                    pass
            self.signals.finished.emit()
