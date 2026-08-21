"""Bounded read-only adapters used exclusively by automatic room polling.

The existing workers retain protocol/parser ownership.  This bridge provides the
model-neutral room contract and deliberately does not use MainWindow callbacks,
so automatic PDU refreshes cannot publish the legacy user-refresh enrichment
trigger and no reused device screen becomes lifecycle authority.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from queue import Empty, Queue
import threading
import time
from typing import Any

from PyQt5.QtCore import Qt

from core.exceptions import AuthenticationError
from core.pdu import PDUOperationDescriptor, REFRESH
from core.room_diagnostic_tree import (
    OneShotAttemptContext,
    OneShotEvent,
    OneShotEventKind,
    RoomCleanupPolicy,
)
from core.worker import (
    BiampTesiraForteCIWorker,
    ExtronDMP64PlusMeterWorker,
    ExtronIN1804Worker,
    HuaweiBar310Worker,
    HuaweiTE20Worker,
    HuaweiTE40Worker,
    PDUOperationWorker,
    PolycomRPG310Worker,
)


@dataclass(frozen=True)
class WorkerAdapterBinding:
    key: str
    factory: Callable[[OneShotAttemptContext], Any]
    polycom: bool = False


class WorkerOneShotAdapter:
    """Run one existing worker once and normalize only its safe public signals."""

    def __init__(
        self,
        factory: Callable[[OneShotAttemptContext], Any],
        *,
        polycom: bool = False,
        cleanup_policy: RoomCleanupPolicy | None = None,
    ):
        self._factory = factory
        self._polycom = polycom
        self._cleanup_policy = cleanup_policy or RoomCleanupPolicy()

    def run(self, context: OneShotAttemptContext) -> Iterable[OneShotEvent]:
        if context.is_current is not None and not context.is_current():
            return
        worker = self._factory(context)
        events: Queue[tuple[str, Any]] = Queue()
        worker.signals.result.connect(
            lambda value: _queue_if_current(events, "result", value, context),
            Qt.DirectConnection,
        )
        worker.signals.error.connect(
            lambda value: _queue_if_current(events, "error", value, context),
            Qt.DirectConnection,
        )

        # The worker owns physical disconnect in its finally path.  We never kill
        # this thread: after the deadline the core revokes logical authority and
        # ignores late signals while advancing the room queue.
        # A factory can only allocate protocol objects; it must not establish
        # device I/O. Recheck before handing execution to the worker so an
        # invalidated queued row never starts its first operation.
        if context.is_current is not None and not context.is_current():
            return
        finished = threading.Event()

        def execute() -> None:
            try:
                worker.run()
            finally:
                finished.set()

        execution = threading.Thread(target=execute, daemon=True)
        execution.start()
        terminal = False
        last_partial: dict | None = None
        while not terminal:
            try:
                kind, value = events.get(timeout=0.02)
            except Empty:
                if finished.is_set():
                    if context.is_current is not None and not context.is_current():
                        return
                    yield OneShotEvent(
                        OneShotEventKind.TERMINAL_FAILURE,
                        failure_reason="Не удалось выполнить диагностику",
                    )
                    terminal = True
                continue
            if kind == "result":
                if value.get("_partial_update") is True:
                    last_partial = value
                    yield OneShotEvent(OneShotEventKind.PARTIAL, value)
                    continue
                yield OneShotEvent(
                    OneShotEventKind.USABLE_SUCCESS,
                    value,
                    credential_success=bool(value.get("_credential_used", True)),
                )
                terminal = True
                continue
            category = str(value[0]) if value else ""
            message = str(value[1]) if len(value) > 1 else "Не удалось выполнить диагностику"
            if self._polycom and last_partial is not None:
                # HTTPS status is authoritative; SSH enrichment is optional.
                yield OneShotEvent(
                    OneShotEventKind.USABLE_SUCCESS_WITH_WARNING,
                    last_partial,
                    warning="Дополнительные параметры SSH недоступны",
                    credential_success=False,
                )
            else:
                error: Exception | None = AuthenticationError(message) if category == "authentication_error" else None
                yield OneShotEvent(OneShotEventKind.TERMINAL_FAILURE, error, failure_reason=_safe_failure(category))
            terminal = True

        # Only terminal diagnostic state starts the bounded retirement window.
        deadline = time.monotonic() + self._cleanup_policy.timeout_seconds
        while not finished.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                yield OneShotEvent(OneShotEventKind.CLEANUP_TIMEOUT)
                return
            finished.wait(min(remaining, 0.02))
        yield OneShotEvent(OneShotEventKind.CLEANUP_COMPLETE)

    def cleanup(self, _context: OneShotAttemptContext) -> bool:
        # Completion is emitted by `run`; an unfinished physical lifecycle is
        # represented by CLEANUP_TIMEOUT, never by a fabricated True result.
        return False


def _credentials(context: OneShotAttemptContext) -> Mapping[str, Any]:
    return context.credential if isinstance(context.credential, Mapping) else {}


def _codec_worker(context: OneShotAttemptContext):
    credentials = _credentials(context)
    if context.diagnostic_model == "Huawei TE20":
        return HuaweiTE20Worker(context.ip_address, username=credentials.get("username"), password=credentials.get("password"), is_current=context.is_current)
    if context.diagnostic_model in {"CloudLink Bar 310", "CloudLink Box 310"}:
        return HuaweiBar310Worker(context.ip_address, username=credentials.get("username"), password=credentials.get("password"), assigned_model=context.diagnostic_model, is_current=context.is_current)
    return HuaweiTE40Worker(context.ip_address, username=credentials.get("username"), password=credentials.get("password"), is_current=context.is_current)


def _polycom_worker(context: OneShotAttemptContext):
    credentials = _credentials(context)
    return PolycomRPG310Worker(context.ip_address, username=credentials.get("username"), password=credentials.get("password"), is_current=context.is_current)


def _matrix_worker(context: OneShotAttemptContext):
    credentials = _credentials(context)
    return ExtronIN1804Worker(context.ip_address, username=credentials.get("username"), password=credentials.get("password"), is_current=context.is_current)


def _pdu_worker(context: OneShotAttemptContext):
    descriptor = PDUOperationDescriptor(
        operation_id=context.operation_token,
        generation=context.session_identity.room_generation,
        model=context.diagnostic_model,
        ip_address=context.ip_address,
        operation=REFRESH,
        credential_index=0 if context.credential else None,
    )
    current = context.is_current or (lambda: False)
    return PDUOperationWorker(
        descriptor,
        credentials=dict(_credentials(context)),
        is_current=lambda _descriptor: current(),
    )


def _biamp_worker(context: OneShotAttemptContext):
    credentials = _credentials(context)
    return BiampTesiraForteCIWorker(context.ip_address, username=credentials.get("username"), password=credentials.get("password"), is_current=context.is_current)


def _dmp_worker(context: OneShotAttemptContext):
    credentials = _credentials(context)
    return ExtronDMP64PlusMeterWorker(context.ip_address, username=credentials.get("username"), password=credentials.get("password"), max_cycles=1, is_current=context.is_current)


def _safe_failure(category: str) -> str:
    return {
        "authentication_error": "Ошибка аутентификации",
        "credential_required": "Credentials не настроены",
        "connection_error": "Не удалось подключиться",
        "protocol_error": "Ошибка протокола устройства",
    }.get(category, "Не удалось выполнить диагностику")


def _queue_if_current(events: Queue[tuple[str, Any]], kind: str, value: Any, context: OneShotAttemptContext) -> None:
    if context.is_current is not None and not context.is_current():
        return
    if context.is_current is None or context.is_current():
        events.put((kind, value))


ROOM_ADAPTER_BINDINGS: tuple[WorkerAdapterBinding, ...] = (
    WorkerAdapterBinding("codec_one_shot", _codec_worker),
    WorkerAdapterBinding("polycom_one_shot", _polycom_worker, polycom=True),
    WorkerAdapterBinding("matrix_one_shot", _matrix_worker),
    WorkerAdapterBinding("pdu_one_shot", _pdu_worker),
    WorkerAdapterBinding("biamp_one_shot", _biamp_worker),
    WorkerAdapterBinding("dmp_one_shot", _dmp_worker),
)


def room_adapter_keys() -> frozenset[str]:
    return frozenset(binding.key for binding in ROOM_ADAPTER_BINDINGS)


def build_room_one_shot_adapters(
    cleanup_policy: RoomCleanupPolicy | None = None,
) -> dict[str, WorkerOneShotAdapter]:
    return {
        binding.key: WorkerOneShotAdapter(
            binding.factory,
            polycom=binding.polycom,
            cleanup_policy=cleanup_policy,
        )
        for binding in ROOM_ADAPTER_BINDINGS
    }
