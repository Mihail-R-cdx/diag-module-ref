"""Exact-row room Call Log lifecycle, independent from reusable codec screens."""

from __future__ import annotations

from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from typing import Any, Mapping

from PyQt5.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal

from core.interactive_session import (
    InteractiveOperation,
    InteractiveSessionController,
    OperationSemantic,
)
from core.room_interaction import RoomInteractionContext


_CODEC_MODELS = frozenset(
    {
        "Huawei TE20",
        "Huawei TE40",
        "CloudLink Bar 310",
        "CloudLink Box 310",
        "Polycom RPG 310",
    }
)
_CONNECTION_FAILURES = frozenset({"authentication", "session_invalid", "transport"})


@dataclass
class _CallLogRun:
    controller: InteractiveSessionController
    terminal: tuple[bool, Any, bool, str | None] | None = None
    cancelled: bool = False
    cleanup_started: bool = False


class _CleanupWorker(QRunnable):
    def __init__(self, owner: "RoomCodecCallLogController", context: RoomInteractionContext, call_log_run: _CallLogRun):
        super().__init__()
        self.owner = owner
        self.context = context
        self.call_log_run = call_log_run

    def run(self) -> None:
        timed_out = False
        try:
            self.call_log_run.controller.wait_until_idle(timeout=self.owner.cleanup_timeout_seconds)
            self.call_log_run.controller.shutdown(wait=True)
        except FutureTimeout:
            timed_out = True
            self.call_log_run.controller.shutdown(wait=False)
        except Exception:
            timed_out = True
            try:
                self.call_log_run.controller.shutdown(wait=False)
            except Exception:
                pass
        self.owner.cleanupCompleted.emit(self.context, self.call_log_run, timed_out)


class RoomCodecCallLogController(QObject):
    """One isolated, cancellable Call Log acquisition per exact room row."""

    operationFinished = pyqtSignal(object, bool, object, bool, object)
    cleanupFinished = pyqtSignal(object, bool)
    cleanupCompleted = pyqtSignal(object, object, bool)

    def __init__(self, *, parent=None, thread_pool=None, cleanup_timeout_seconds: float = 5.0):
        super().__init__(parent)
        self.cleanup_timeout_seconds = cleanup_timeout_seconds
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._runs: dict[RoomInteractionContext, _CallLogRun] = {}
        self.cleanupCompleted.connect(self._accept_cleanup)

    def start(
        self,
        context: RoomInteractionContext,
        candidates: tuple[Mapping[str, Any], ...],
        start_index: int,
        saved_profile: Mapping[str, Any] | None = None,
    ) -> None:
        if context.diagnostic_model not in _CODEC_MODELS:
            self.operationFinished.emit(
                context, False, None, False, "Журнал звонков для этой модели недоступен"
            )
            return
        if not candidates:
            self.operationFinished.emit(context, False, None, False, "Credentials не настроены")
            return
        controller = InteractiveSessionController(self)
        run = _CallLogRun(controller)
        self._runs[context] = run
        controller.signals.result.connect(
            lambda payload, current=context: self._accept_result(current, payload)
        )
        controller.signals.error.connect(
            lambda payload, current=context: self._accept_error(current, payload)
        )
        try:
            generation = controller.activate_context(
                context.diagnostic_model,
                context.ip_address,
                candidates,
                start_index,
                saved_profile,
            )
            operation_id = controller.submit(
                InteractiveOperation(
                    kind="room_call_log",
                    method="get_call_history_snapshot",
                    semantic=OperationSemantic.READ_ONLY,
                    quiet=True,
                ),
                generation=generation,
            )
        except Exception:
            operation_id = None
        if operation_id is None:
            self._finish(context, False, None, False, "Не удалось запустить журнал звонков")

    def cancel(self, context: RoomInteractionContext) -> None:
        run = self._runs.get(context)
        if run is None:
            return
        run.cancelled = True
        self._begin_cleanup(context, run)

    def _accept_result(self, context: RoomInteractionContext, payload: dict) -> None:
        if context not in self._runs:
            return
        self._finish(context, True, payload.get("value"), False, None)

    def _accept_error(self, context: RoomInteractionContext, payload: dict) -> None:
        if context not in self._runs:
            return
        category = str(payload.get("category") or "")
        self._finish(
            context,
            False,
            None,
            category in _CONNECTION_FAILURES,
            "Не удалось загрузить журнал звонков",
        )

    def _finish(self, context: RoomInteractionContext, success: bool, data: Any, connection_lost: bool, warning: str | None) -> None:
        run = self._runs.get(context)
        if run is None or run.cancelled or run.terminal is not None:
            return
        run.terminal = (success, data, connection_lost, warning)
        self._begin_cleanup(context, run)

    def _begin_cleanup(self, context: RoomInteractionContext, run: _CallLogRun) -> None:
        if run.cleanup_started:
            return
        run.cleanup_started = True
        run.controller.invalidate_context()
        self._thread_pool.start(_CleanupWorker(self, context, run))

    def _accept_cleanup(self, context: RoomInteractionContext, run: _CallLogRun, timed_out: bool) -> None:
        if self._runs.get(context) is not run:
            return
        self._runs.pop(context, None)
        if run.cancelled:
            self.cleanupFinished.emit(context, timed_out)
            return
        success, data, connection_lost, warning = run.terminal or (
            False,
            None,
            True,
            "Не удалось завершить журнал звонков",
        )
        if timed_out:
            success = False
            connection_lost = True
            warning = "Не удалось завершить соединение"
        self.operationFinished.emit(context, success, data, connection_lost, warning)
