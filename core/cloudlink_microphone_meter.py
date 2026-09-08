"""Focused, serialized live microphone polling for CloudLink 310 codecs."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from core.interactive_session import InteractiveOperation, InteractiveSessionController, OperationSemantic


# Box LIVE is intentionally deferred.  Keeping the exact supported set here
# makes legacy codec-page composition fail closed as well as room composition.
SUPPORTED_CLOUDLINK_METER_MODELS = {"CloudLink Bar 310"}


class CloudLinkMicrophoneMeter(QObject):
    """Owns one optional one-second polling lifecycle and never persists login state."""

    sample = pyqtSignal(dict)
    accepted = pyqtSignal(dict, dict)
    terminal = pyqtSignal(dict)

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
            evidence = {
                "credential_index": payload.get("credential_index"),
                "connection_profile": dict(payload.get("connection_profile") or {}),
            }
            self._finish_cycle(
                value if isinstance(value, dict) else {"available": False, "raw_level": None, "fraction": None},
                success_evidence=evidence,
            )

    def _on_error(self, payload: dict) -> None:
        if self._matches(payload):
            # Protocol/command failures are sample-local: the established
            # session remains usable and the next cadence may sample again.
            # Only typed session/auth/transport exhaustion is terminal.
            terminal = payload.get("category") in {
                "authentication_error", "session_invalid", "connection_error",
            }
            self._finish_cycle(
                {"available": False, "raw_level": None, "fraction": None},
                terminal=terminal,
                terminal_category=payload.get("category"),
            )

    def _on_dropped(self, payload: dict) -> None:
        if self._matches(payload):
            self._in_flight = False

    def _finish_cycle(
        self,
        value: dict,
        terminal: bool = False,
        terminal_category: str | None = None,
        success_evidence: dict | None = None,
    ) -> None:
        self._in_flight = False
        if not self._active:
            return
        presentation = dict(value)
        # Consumers use this opaque lifecycle identity to reject a queued
        # callback after their authoritative context has been replaced.
        presentation["_meter_generation"] = self._generation
        presentation["_meter_token"] = self._token
        if success_evidence is not None:
            # This focused signal carries only non-secret accepted connection
            # evidence from the session owner.  The presentation sample stays
            # unchanged for existing consumers.
            self.accepted.emit(presentation, dict(success_evidence))
        self.sample.emit(presentation)
        if terminal:
            self._active = False
            # The meter does not own shared PDU or codec-page sessions.  Its
            # composition owner must therefore receive the typed exhausted
            # outcome and schedule cleanup on the session-owning lane.
            terminal_outcome = dict(presentation)
            terminal_outcome["category"] = terminal_category
            self.terminal.emit(terminal_outcome)
            return
        self._timer.start(1000)
