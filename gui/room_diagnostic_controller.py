"""Background owner for one automatic room diagnostic generation."""

from __future__ import annotations

from PyQt5.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal

from core.room_diagnostic_tree import RoomDiagnosticOrchestrator, RoomDiagnosticSession

from .room_one_shot_adapters import build_room_one_shot_adapters


class _RoomCycleSignals(QObject):
    updated = pyqtSignal(object)
    finished = pyqtSignal(object)


class _RoomCycleWorker(QRunnable):
    def __init__(self, controller: "RoomDiagnosticController", session: RoomDiagnosticSession):
        super().__init__()
        self.controller = controller
        self.session = session

    def run(self):
        self.controller._run_session(self.session)


class RoomDiagnosticController(QObject):
    """Runs one queue on a background lane and suppresses stale completions."""

    sessionFinished = pyqtSignal(object)
    sessionUpdated = pyqtSignal(object)

    def __init__(self, *, candidate_provider, ping, persist_success, starting_index, parent=None, thread_pool=None):
        super().__init__(parent)
        self._candidate_provider = candidate_provider
        self._ping = ping
        self._persist_success = persist_success
        self._starting_index = starting_index
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._active_session: RoomDiagnosticSession | None = None
        self._signals = _RoomCycleSignals()
        self._signals.updated.connect(self._accept_update)
        self._signals.finished.connect(self._accept_finished)

    def start(self, session: RoomDiagnosticSession) -> None:
        self.supersede()
        self._active_session = session
        self._thread_pool.start(_RoomCycleWorker(self, session))

    def supersede(self) -> None:
        if self._active_session is not None:
            self._active_session.invalidate()
        self._active_session = None

    def _run_session(self, session: RoomDiagnosticSession) -> None:
        orchestrator = RoomDiagnosticOrchestrator(
            adapters=build_room_one_shot_adapters(),
            credential_candidates=self._candidate_provider,
            ping=self._ping,
            persist_success=self._persist_success,
            starting_index=self._starting_index,
            on_update=self._signals.updated.emit,
        )
        self._signals.finished.emit(orchestrator.run(session))

    def _accept_finished(self, session: RoomDiagnosticSession) -> None:
        if session is not self._active_session or session.invalidated:
            return
        self._active_session = None
        self.sessionFinished.emit(session)

    def _accept_update(self, session: RoomDiagnosticSession) -> None:
        if session is self._active_session and not session.invalidated:
            self.sessionUpdated.emit(session)
