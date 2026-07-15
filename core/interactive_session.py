"""Serialized application-owned codec interactive session lifecycle."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
import threading
from typing import Any, Callable, Mapping, Optional, Sequence

from PyQt5.QtCore import QObject, pyqtSignal

from core.codec_connection_profiles import order_codec_profiles
from core.credentials import CredentialAttemptPlan
from core.exceptions import (
    AuthenticationError,
    CodecFailureCategory,
    CommandError,
    CommandOutcomeUnknownError,
    ConnectionError,
    SessionInvalidError,
    TimeoutError as DeviceTimeoutError,
    classify_codec_failure,
)


class OperationSemantic(str, Enum):
    READ_ONLY = "read_only"
    ABSOLUTE = "absolute"
    DESIRED_STATE = "desired_state"
    RELATIVE_AS_ABSOLUTE = "relative_as_absolute"


@dataclass(frozen=True)
class InteractiveOperation:
    kind: str
    method: str
    args: tuple[Any, ...] = ()
    kwargs: Mapping[str, Any] = field(default_factory=dict)
    semantic: OperationSemantic = OperationSemantic.READ_ONLY
    readback_method: Optional[str] = None
    readback_args: tuple[Any, ...] = ()
    readback_kwargs: Mapping[str, Any] = field(default_factory=dict)
    target: Any = None
    original: Any = None
    allow_set_from_any_authoritative: bool = False
    duplicate_key: Optional[str] = None
    quiet: bool = False
    client_token: Optional[int] = None


@dataclass(frozen=True)
class _Context:
    generation: int
    model: str
    ip_address: str
    candidates: tuple[dict[str, Any], ...]
    candidate_identities: tuple[tuple[tuple[str, Any], ...], ...]
    start_index: int
    saved_profile: Optional[dict[str, Any]]

    @property
    def identity(self) -> tuple[Any, ...]:
        return (
            self.model,
            self.ip_address,
            self.candidate_identities,
            self.start_index,
            _profile_key(self.saved_profile),
        )


@dataclass
class _HandlerRecord:
    handler: Any
    model: str
    ip_address: str
    credential_index: int
    credential_identity: tuple[tuple[str, Any], ...]
    profile: dict[str, Any]
    context_identity: tuple[Any, ...]


class InteractiveSessionSignals(QObject):
    result = pyqtSignal(dict)
    error = pyqtSignal(dict)
    finished = pyqtSignal(dict)
    dropped = pyqtSignal(dict)


class InteractiveSessionController(QObject):
    """Own one cached handler and execute all of its work on one lane."""

    def __init__(
        self,
        parent: Optional[QObject] = None,
        *,
        handler_factory: Optional[Callable[[str, Mapping[str, Any]], Any]] = None,
        profile_orderer: Callable[..., Sequence[Mapping[str, Any]]] = order_codec_profiles,
    ):
        super().__init__(parent)
        self.signals = InteractiveSessionSignals(self)
        self._handler_factory = handler_factory or _default_handler_factory
        self._profile_orderer = profile_orderer
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="codec-interactive"
        )
        self._lock = threading.RLock()
        self._generation = 0
        self._context: Optional[_Context] = None
        self._handler_record: Optional[_HandlerRecord] = None
        self._operation_serial = 0
        self._pending_duplicates: set[str] = set()
        self._accepting = True

    @property
    def generation(self) -> int:
        with self._lock:
            return self._generation

    def activate_context(
        self,
        model: str,
        ip_address: str,
        candidates: Sequence[Mapping[str, Any]],
        start_index: int = 0,
        saved_profile: Optional[Mapping[str, Any]] = None,
    ) -> int:
        """Publish a new context before old queued work can execute."""

        resolved = tuple(dict(candidate) for candidate in candidates)
        if not resolved:
            raise ValueError("Interactive codec context requires credentials.")
        identities = tuple(_credential_identity(candidate) for candidate in resolved)
        if start_index < 0 or start_index >= len(resolved):
            start_index = 0
        saved = dict(saved_profile) if isinstance(saved_profile, Mapping) else None
        prospective_identity = (
            model,
            ip_address,
            identities,
            start_index,
            _profile_key(saved),
        )
        with self._lock:
            if not self._accepting:
                raise RuntimeError("Interactive session controller is shutting down.")
            if self._context is not None and self._context.identity == prospective_identity:
                return self._generation
            self._generation += 1
            self._context = _Context(
                generation=self._generation,
                model=str(model),
                ip_address=str(ip_address),
                candidates=resolved,
                candidate_identities=identities,
                start_index=start_index,
                saved_profile=saved,
            )
            generation = self._generation
            self._pending_duplicates.clear()
        self._executor.submit(self._invalidate_superseded_handler, generation)
        return generation

    def invalidate_context(self) -> int:
        """Supersede all queued operations and close the cached handler on its lane."""

        with self._lock:
            self._generation += 1
            self._context = None
            self._pending_duplicates.clear()
            generation = self._generation
        self._executor.submit(self._invalidate_superseded_handler, generation)
        return generation

    def submit(
        self,
        operation: InteractiveOperation,
        *,
        generation: Optional[int] = None,
    ) -> Optional[int]:
        with self._lock:
            if not self._accepting or self._context is None:
                return None
            context = self._context
            captured_generation = context.generation if generation is None else generation
            duplicate_key = operation.duplicate_key
            if duplicate_key and duplicate_key in self._pending_duplicates:
                return None
            if duplicate_key:
                self._pending_duplicates.add(duplicate_key)
            self._operation_serial += 1
            operation_id = self._operation_serial
        self._executor.submit(
            self._run_operation,
            operation_id,
            captured_generation,
            context,
            operation,
        )
        return operation_id

    def wait_until_idle(self, timeout: Optional[float] = None) -> None:
        self._executor.submit(lambda: None).result(timeout=timeout)

    def shutdown(self, *, wait: bool = True) -> None:
        with self._lock:
            if not self._accepting:
                return
            self._accepting = False
            self._generation += 1
            self._context = None
            self._pending_duplicates.clear()
        future = self._executor.submit(self._close_handler)
        if wait:
            future.result()
        self._executor.shutdown(wait=wait, cancel_futures=False)

    def _run_operation(
        self,
        operation_id: int,
        generation: int,
        context: _Context,
        operation: InteractiveOperation,
    ) -> None:
        terminal = self._public_context(operation_id, generation, context, operation)
        try:
            if not self._context_is_current(generation, context):
                _emit_signal(self.signals.dropped, terminal)
                return
            record = self._acquire_handler(context)
            if not self._context_is_current(generation, context):
                _emit_signal(self.signals.dropped, terminal)
                return
            try:
                value = self._invoke(record.handler, operation)
                if operation.semantic != OperationSemantic.READ_ONLY and value is False:
                    raise CommandError("Device rejected the requested codec command.")
                reconciled = False
            except (
                SessionInvalidError,
                AuthenticationError,
                ConnectionError,
                DeviceTimeoutError,
                OSError,
                CommandOutcomeUnknownError,
            ) as error:
                record = self._recover_once(context, record, error)
                if operation.semantic == OperationSemantic.READ_ONLY:
                    value = self._invoke(record.handler, operation)
                    reconciled = False
                else:
                    value = self._reconcile(record.handler, operation)
                    reconciled = True

            if not self._context_is_current(generation, context):
                _emit_signal(self.signals.dropped, terminal)
                return
            payload = dict(terminal)
            payload.update(
                {
                    "value": value,
                    "credential_index": record.credential_index,
                    "connection_profile": dict(record.profile),
                    "reconciled": reconciled,
                }
            )
            _emit_signal(self.signals.result, payload)
        except Exception as error:
            if self._context_is_current(generation, context):
                payload = dict(terminal)
                payload.update(
                    {
                        "category": classify_codec_failure(error).value,
                        "message": _public_error_message(error),
                    }
                )
                _emit_signal(self.signals.error, payload)
            else:
                _emit_signal(self.signals.dropped, terminal)
        finally:
            with self._lock:
                if operation.duplicate_key:
                    self._pending_duplicates.discard(operation.duplicate_key)
            _emit_signal(self.signals.finished, terminal)

    def _recover_once(
        self, context: _Context, record: _HandlerRecord, error: BaseException
    ) -> _HandlerRecord:
        del error
        preferred_index = record.credential_index
        self._close_handler()
        return self._acquire_handler(context, preferred_index=preferred_index)

    def _reconcile(self, handler: Any, operation: InteractiveOperation) -> Any:
        if not operation.readback_method:
            raise CommandOutcomeUnknownError(
                "Codec state cannot be reconciled after session recovery."
            )
        readback = getattr(handler, operation.readback_method, None)
        if not callable(readback):
            raise CommandOutcomeUnknownError(
                "Codec does not expose authoritative state readback."
            )
        observed = readback(*operation.readback_args, **dict(operation.readback_kwargs))
        if observed is None:
            raise CommandOutcomeUnknownError(
                "Codec state is unavailable after session recovery."
            )
        if _state_matches(observed, operation.target):
            return observed
        can_set = operation.allow_set_from_any_authoritative or (
            operation.original is not None
            and _state_matches(observed, operation.original)
        )
        if not can_set:
            raise CommandOutcomeUnknownError(
                "Codec state changed concurrently; command was not replayed."
            )
        result = self._invoke(handler, operation)
        if result is False:
            raise CommandError("Device rejected the reconciled codec command.")
        return result

    @staticmethod
    def _invoke(handler: Any, operation: InteractiveOperation) -> Any:
        method = getattr(handler, operation.method, None)
        if not callable(method):
            raise CommandError("Selected codec does not support this operation.")
        return method(*operation.args, **dict(operation.kwargs))

    def _acquire_handler(
        self, context: _Context, preferred_index: Optional[int] = None
    ) -> _HandlerRecord:
        if not self._context_is_current(context.generation, context):
            raise ConnectionError("Interactive codec context was superseded.")
        current = self._handler_record
        if current is not None and self._record_matches_context(current, context):
            if _handler_is_connected(current.handler):
                return current
            self._close_handler()

        start_index = context.start_index if preferred_index is None else preferred_index
        plan = CredentialAttemptPlan(context.candidates, start_index)
        last_error: Optional[BaseException] = None
        while True:
            index = plan.current_index
            candidate = plan.current_candidate
            profiles = tuple(
                dict(profile)
                for profile in self._profile_orderer(
                    context.model, context.saved_profile
                )
            )
            if not profiles:
                raise ConnectionError("Selected codec has no supported interactive transport.")
            authentication_failed = False
            for profile in profiles:
                if not self._context_is_current(context.generation, context):
                    raise ConnectionError("Interactive codec context was superseded.")
                kwargs = {
                    "ip_address": context.ip_address,
                    **candidate,
                    "port": profile["port"],
                }
                if context.model != "Polycom RPG 310":
                    kwargs["use_ssl"] = bool(profile.get("use_ssl"))
                handler = self._handler_factory(context.model, kwargs)
                try:
                    if not handler.connect():
                        raise ConnectionError(
                            f"{profile.get('label', 'codec transport')} did not connect"
                        )
                    record = _HandlerRecord(
                        handler=handler,
                        model=context.model,
                        ip_address=context.ip_address,
                        credential_index=index,
                        credential_identity=context.candidate_identities[index],
                        profile=dict(profile),
                        context_identity=context.identity,
                    )
                    self._handler_record = record
                    return record
                except AuthenticationError as error:
                    last_error = error
                    authentication_failed = True
                    _disconnect(handler)
                    break
                except Exception as error:
                    last_error = error
                    _disconnect(handler)
            if authentication_failed and plan.advance_after_authentication_failure():
                continue
            if authentication_failed:
                raise last_error or AuthenticationError("Codec login was rejected.")
            raise ConnectionError("All supported codec transports failed.") from last_error

    def _record_matches_context(self, record: _HandlerRecord, context: _Context) -> bool:
        if record.context_identity != context.identity:
            return False
        if record.model != context.model or record.ip_address != context.ip_address:
            return False
        if record.credential_index >= len(context.candidate_identities):
            return False
        if record.credential_identity != context.candidate_identities[record.credential_index]:
            return False
        supported = self._profile_orderer(context.model, context.saved_profile)
        return _profile_key(record.profile) in {_profile_key(profile) for profile in supported}

    def _context_is_current(self, generation: int, context: _Context) -> bool:
        with self._lock:
            return (
                self._accepting
                and self._context is not None
                and self._generation == generation
                and self._context.identity == context.identity
            )

    def _invalidate_superseded_handler(self, generation: int) -> None:
        with self._lock:
            active = self._context
            current_generation = self._generation
        record = self._handler_record
        if record is None:
            return
        if active is None or current_generation != generation or not self._record_matches_context(record, active):
            self._close_handler()

    def _close_handler(self) -> None:
        record = self._handler_record
        self._handler_record = None
        if record is not None:
            _disconnect(record.handler)

    @staticmethod
    def _public_context(
        operation_id: int,
        generation: int,
        context: _Context,
        operation: InteractiveOperation,
    ) -> dict[str, Any]:
        return {
            "operation_id": operation_id,
            "generation": generation,
            "model": context.model,
            "ip_address": context.ip_address,
            "kind": operation.kind,
            "quiet": operation.quiet,
            "client_token": operation.client_token,
        }


def _default_handler_factory(model: str, kwargs: Mapping[str, Any]) -> Any:
    if model == "Huawei TE20":
        from handlers.huawei.te20 import HuaweiTE20Handler

        return HuaweiTE20Handler(**dict(kwargs))
    if model == "Huawei TE40":
        from handlers.huawei.te40 import HuaweiTE40Handler

        return HuaweiTE40Handler(**dict(kwargs))
    if model == "CloudLink Bar 310":
        from handlers.huawei.bar310 import CloudLinkBar310Handler

        return CloudLinkBar310Handler(**dict(kwargs))
    if model == "Polycom RPG 310":
        from handlers.polycom.rpg310 import PolycomRPG310Handler

        clean_kwargs = dict(kwargs)
        clean_kwargs.pop("use_ssl", None)
        return PolycomRPG310Handler(**clean_kwargs)
    raise ConnectionError("Selected codec has no interactive handler.")


def _credential_identity(candidate: Mapping[str, Any]) -> tuple[tuple[str, Any], ...]:
    """Private in-process equality key; never render or persist this value."""

    return tuple(sorted(candidate.items(), key=lambda item: item[0]))


def _profile_key(profile: Optional[Mapping[str, Any]]) -> Optional[tuple[Any, bool]]:
    if not isinstance(profile, Mapping):
        return None
    return profile.get("port"), bool(profile.get("use_ssl"))


def _handler_is_connected(handler: Any) -> bool:
    predicate = getattr(handler, "is_connected", None)
    if callable(predicate):
        try:
            return bool(predicate())
        except Exception:
            return False
    return bool(getattr(handler, "_connected", False))


def _disconnect(handler: Any) -> None:
    disconnect = getattr(handler, "disconnect", None)
    if callable(disconnect):
        try:
            disconnect()
        except Exception:
            pass


def _state_matches(observed: Any, target: Any) -> bool:
    if observed == target:
        return True
    if isinstance(observed, str) and isinstance(target, str):
        return observed.strip().casefold() == target.strip().casefold()
    return False


def _emit_signal(signal: Any, payload: dict[str, Any]) -> None:
    """Ignore late worker emissions after Qt has destroyed the owner."""

    try:
        signal.emit(payload)
    except RuntimeError:
        pass


def _public_error_message(error: BaseException) -> str:
    category = classify_codec_failure(error)
    messages = {
        CodecFailureCategory.AUTHENTICATION: "Codec authentication failed.",
        CodecFailureCategory.SESSION_INVALID: "Codec session recovery failed.",
        CodecFailureCategory.TRANSPORT: "Codec connection failed.",
        CodecFailureCategory.PROTOCOL: "Codec returned an invalid response.",
        CodecFailureCategory.COMMAND: "Codec rejected the command.",
        CodecFailureCategory.UNKNOWN_COMMAND_OUTCOME: "Codec command outcome is indeterminate.",
    }
    return messages[category]
