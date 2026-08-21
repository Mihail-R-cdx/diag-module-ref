"""Bounded read-only adapters used exclusively by automatic room polling.

The existing workers retain protocol/parser ownership.  This bridge provides the
model-neutral room contract and deliberately does not use MainWindow callbacks,
so automatic PDU refreshes cannot publish the legacy user-refresh enrichment
trigger and no reused device screen becomes lifecycle authority.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from PyQt5.QtCore import Qt

from core.exceptions import AuthenticationError
from core.pdu import PDUOperationDescriptor, REFRESH
from core.room_diagnostic_tree import OneShotAttemptContext, OneShotEvent, OneShotEventKind
from core.worker import (
    AtenPDUWorker,
    BiampTesiraForteCIWorker,
    ExtronDMP64PlusMeterWorker,
    ExtronIN1804Worker,
    HuaweiBar310Worker,
    HuaweiTE20Worker,
    HuaweiTE40Worker,
    PDUOperationWorker,
    PolycomRPG310Worker,
)


class WorkerOneShotAdapter:
    """Run one existing worker once and normalize only its safe public signals."""

    def __init__(self, factory: Callable[[OneShotAttemptContext], Any], *, polycom: bool = False):
        self._factory = factory
        self._polycom = polycom

    def run(self, context: OneShotAttemptContext) -> Iterable[OneShotEvent]:
        worker = self._factory(context)
        results: list[dict] = []
        errors: list[tuple] = []
        worker.signals.result.connect(results.append, Qt.DirectConnection)
        worker.signals.error.connect(errors.append, Qt.DirectConnection)
        worker.run()

        partial = [item for item in results if item.get("_partial_update") is True]
        final = [item for item in results if item.get("_partial_update") is not True]
        for item in partial:
            yield OneShotEvent(OneShotEventKind.PARTIAL, item)
        if final:
            # Existing workers already retire their owned handler/session in finally.
            yield OneShotEvent(
                OneShotEventKind.USABLE_SUCCESS,
                final[-1],
                credential_success=bool(final[-1].get("_credential_used", True)),
            )
            yield OneShotEvent(OneShotEventKind.CLEANUP_COMPLETE)
            return
        if partial and self._polycom and errors:
            # HTTPS status is authoritative; SSH enrichment is explicitly optional.
            yield OneShotEvent(
                OneShotEventKind.USABLE_SUCCESS_WITH_WARNING,
                partial[-1],
                warning="Дополнительные параметры SSH недоступны",
                credential_success=False,
            )
            yield OneShotEvent(OneShotEventKind.CLEANUP_COMPLETE)
            return
        if errors:
            category = str(errors[-1][0]) if errors[-1] else ""
            message = str(errors[-1][1]) if len(errors[-1]) > 1 else "Не удалось выполнить диагностику"
            error: Exception | None = AuthenticationError(message) if category == "authentication_error" else None
            yield OneShotEvent(OneShotEventKind.TERMINAL_FAILURE, error, failure_reason=_safe_failure(category))
        else:
            yield OneShotEvent(OneShotEventKind.TERMINAL_FAILURE, failure_reason="Не удалось выполнить диагностику")
        yield OneShotEvent(OneShotEventKind.CLEANUP_COMPLETE)

    def cleanup(self, _context: OneShotAttemptContext) -> bool:
        # Every wrapped worker closes its handler/channel in its `finally` path.
        return True


def build_room_one_shot_adapters() -> dict[str, WorkerOneShotAdapter]:
    return {
        "codec_one_shot": WorkerOneShotAdapter(_codec_worker),
        "polycom_one_shot": WorkerOneShotAdapter(_polycom_worker, polycom=True),
        "matrix_one_shot": WorkerOneShotAdapter(_matrix_worker),
        "pdu_one_shot": WorkerOneShotAdapter(_pdu_worker),
        "biamp_one_shot": WorkerOneShotAdapter(_biamp_worker),
        "dmp_one_shot": WorkerOneShotAdapter(_dmp_worker),
    }


def _credentials(context: OneShotAttemptContext) -> Mapping[str, Any]:
    return context.credential if isinstance(context.credential, Mapping) else {}


def _codec_worker(context: OneShotAttemptContext):
    credentials = _credentials(context)
    if context.diagnostic_model == "Huawei TE20":
        return HuaweiTE20Worker(context.ip_address, username=credentials.get("username"), password=credentials.get("password"))
    if context.diagnostic_model in {"CloudLink Bar 310", "CloudLink Box 310"}:
        return HuaweiBar310Worker(context.ip_address, username=credentials.get("username"), password=credentials.get("password"), assigned_model=context.diagnostic_model)
    return HuaweiTE40Worker(context.ip_address, username=credentials.get("username"), password=credentials.get("password"))


def _polycom_worker(context: OneShotAttemptContext):
    credentials = _credentials(context)
    return PolycomRPG310Worker(context.ip_address, username=credentials.get("username"), password=credentials.get("password"))


def _matrix_worker(context: OneShotAttemptContext):
    credentials = _credentials(context)
    return ExtronIN1804Worker(context.ip_address, username=credentials.get("username"), password=credentials.get("password"))


def _pdu_worker(context: OneShotAttemptContext):
    descriptor = PDUOperationDescriptor(
        operation_id=context.operation_token,
        generation=context.session_identity.room_generation,
        model=context.diagnostic_model,
        ip_address=context.ip_address,
        operation=REFRESH,
        credential_index=0 if context.credential else None,
    )
    return PDUOperationWorker(descriptor, credentials=dict(_credentials(context)))


def _biamp_worker(context: OneShotAttemptContext):
    credentials = _credentials(context)
    return BiampTesiraForteCIWorker(context.ip_address, username=credentials.get("username"), password=credentials.get("password"))


def _dmp_worker(context: OneShotAttemptContext):
    credentials = _credentials(context)
    return ExtronDMP64PlusMeterWorker(context.ip_address, username=credentials.get("username"), password=credentials.get("password"), max_cycles=1)


def _safe_failure(category: str) -> str:
    return {
        "authentication_error": "Ошибка аутентификации",
        "credential_required": "Credentials не настроены",
        "connection_error": "Не удалось подключиться",
        "protocol_error": "Ошибка протокола устройства",
    }.get(category, "Не удалось выполнить диагностику")
