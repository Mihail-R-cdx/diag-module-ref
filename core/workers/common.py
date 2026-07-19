"""Shared infrastructure for background worker modules."""

import traceback

from PyQt5.QtCore import QObject, pyqtSignal

from core.exceptions import classify_codec_failure
from core.redaction import redact_exception


def _worker_secrets(worker):
    values = [getattr(worker, "username", None), getattr(worker, "password", None)]
    for credential in getattr(worker, "creds_list", ()):
        if isinstance(credential, dict):
            values.extend(credential.values())
    return tuple(values)


def _safe_error(error, secrets):
    return (
        redact_exception(error, secrets),
        redact_exception(traceback.format_exc(), secrets),
    )


def _emit_error(worker, category, error, trace=True):
    if category is None:
        category = classify_codec_failure(error).value
    message, details = _safe_error(error, _worker_secrets(worker))
    worker.signals.error.emit((category, message, details if trace else ""))


class WorkerSignals(QObject):
    """Сигналы для общения между потоками"""
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(dict)
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    terminal_log = pyqtSignal(str)
    connected = pyqtSignal()
    disconnected = pyqtSignal()
