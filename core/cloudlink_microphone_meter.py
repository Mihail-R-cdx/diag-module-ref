"""Focused, serialized live microphone polling for CloudLink 310 codecs."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from core.interactive_session import InteractiveOperation, InteractiveSessionController, OperationSemantic


SUPPORTED_CLOUDLINK_METER_MODELS = {"CloudLink Bar 310", "CloudLink Box 310"}


class CloudLinkMicrophoneMeter(QObject):
    """Owns one optional one-second polling lifecycle and never persists login state."""

    sample = pyqtSignal(dict)

    def __init__(self, parent: QObject | None = None, *, session: InteractiveSessionController | None = None):
        super().__init__(parent)
        self._session = session or InteractiveSessionController(parent=self)
        self._owns_session = session is None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._submit_next)
        self._generation: int | None = None
        self._token: int | None = None
        self._model: str | None = None
        self._active = False
        self._in_flight = False
        self._session.signals.result.connect(self._on_result)
        self._session.signals.error.connect(self._on_error)
        self._session.signals.dropped.connect(self._on_dropped)

    def start(self, model: str, ip_address: str, candidates: Sequence[Mapping[str, Any]], start_index: int = 0,
              saved_profile: Mapping[str, Any] | None = None, *, generation: int | None = None, token: int | None = None) -> bool:
        self.stop()
        if model not in SUPPORTED_CLOUDLINK_METER_MODELS:
            return False
        if self._owns_session:
            generation = self._session.activate_context(model, ip_address, candidates, start_index, saved_profile)
        if generation is None:
            return False
        self._generation, self._token, self._model = generation, token, model
        self._active = True
        self._submit_next()
        return True

    def stop(self) -> None:
        self._active = False
        self._in_flight = False
        self._timer.stop()
        if self._owns_session:
            self._session.invalidate_context()
        self._generation = self._token = self._model = None

    def shutdown(self) -> None:
        self.stop()
        if self._owns_session:
            self._session.shutdown(wait=False)

    def _submit_next(self) -> None:
        if not self._active or self._in_flight or self._generation is None:
            return
        self._in_flight = True
        operation = InteractiveOperation(kind="cloudlink_microphone_meter", method="get_live_microphone_sample",
                                         semantic=OperationSemantic.READ_ONLY, quiet=True, client_token=self._token)
        if self._session.submit(operation, generation=self._generation) is None:
            self._finish_cycle({"available": False, "raw_level": None, "fraction": None})

    def _matches(self, payload: dict) -> bool:
        return self._active and payload.get("kind") == "cloudlink_microphone_meter" and payload.get("generation") == self._generation and payload.get("client_token") == self._token

    def _on_result(self, payload: dict) -> None:
        if self._matches(payload):
            value = payload.get("value")
            self._finish_cycle(value if isinstance(value, dict) else {"available": False, "raw_level": None, "fraction": None})

    def _on_error(self, payload: dict) -> None:
        if self._matches(payload):
            # A typed terminal failure stops this context; a new diagnostic context may restart it.
            self._finish_cycle({"available": False, "raw_level": None, "fraction": None}, terminal=True)

    def _on_dropped(self, payload: dict) -> None:
        if self._matches(payload):
            self._in_flight = False

    def _finish_cycle(self, value: dict, terminal: bool = False) -> None:
        self._in_flight = False
        if not self._active:
            return
        self.sample.emit(dict(value))
        if terminal:
            self._active = False
            return
        self._timer.start(1000)
