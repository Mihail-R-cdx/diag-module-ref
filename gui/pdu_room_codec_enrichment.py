"""Application controller for PDU room codec enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import itertools
from typing import Any, Callable, Mapping, Sequence

from PyQt5.QtCore import QObject, pyqtSignal

from core.equipment_inventory import EquipmentInventory, EquipmentInventoryLoadError
from core.exceptions import CodecFailureCategory
from core.interactive_session import (
    InteractiveOperation,
    InteractiveSessionController,
    OperationSemantic,
)
from core.related_codec_status import RelatedCodecStatusAdapter
from core.cloudlink_microphone_meter import CloudLinkMicrophoneMeter, SUPPORTED_CLOUDLINK_METER_MODELS
from core.room_context import (
    RoomContext,
    RoomContextResolver,
    RoomResolutionResult,
    RoomResolutionStatus,
    room_vip_label,
)


class CodecDiagnosticStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    TRANSPORT_FAILED = "TRANSPORT_FAILED"
    PROTOCOL_FAILED = "PROTOCOL_FAILED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class PDUAcceptedRefreshContext:
    pdu_generation: int
    refresh_operation_id: int
    model: str
    ip_address: str
    credential_context_revision: int


@dataclass(frozen=True)
class PDUContextSuperseded:
    pdu_generation_or_revision: int
    reason: str


@dataclass(frozen=True)
class EnrichmentPresentation:
    generation: int
    operation_id: int
    pdu_generation: int | None
    pdu_refresh_operation_id: int | None
    resolution_status: str
    codec_diagnostic_status: str
    pdu_credential_context_revision: int | None = None
    codec_credential_context_revision: int | None = None
    room_id: str | None = None
    room_name: str | None = None
    room_vip_status: str | None = None
    room_vip_label: str | None = None
    codec_source_model: str | None = None
    codec_diagnostic_model: str | None = None
    codec_ip_address: str | None = None
    call_status: str | None = None
    presentation_status: str | None = None
    microphone_available: bool = False
    microphone_raw_level: float | int | None = None
    microphone_fraction: float | None = None
    warnings: tuple[str, ...] = ()
    safe_message: str | None = None
    pending: bool = False
    reset: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "operation_id": self.operation_id,
            "pdu_generation": self.pdu_generation,
            "pdu_refresh_operation_id": self.pdu_refresh_operation_id,
            "pdu_credential_context_revision": self.pdu_credential_context_revision,
            "codec_credential_context_revision": self.codec_credential_context_revision,
            "resolution_status": self.resolution_status,
            "codec_diagnostic_status": self.codec_diagnostic_status,
            "room_id": self.room_id,
            "room_name": self.room_name,
            "room_vip_status": self.room_vip_status,
            "room_vip_label": self.room_vip_label,
            "codec_source_model": self.codec_source_model,
            "codec_diagnostic_model": self.codec_diagnostic_model,
            "codec_ip_address": self.codec_ip_address,
            "call_status": self.call_status,
            "presentation_status": self.presentation_status,
            "microphone_available": self.microphone_available,
            "microphone_raw_level": self.microphone_raw_level,
            "microphone_fraction": self.microphone_fraction,
            "warnings": self.warnings,
            "safe_message": self.safe_message,
            "pending": self.pending,
            "reset": self.reset,
        }


class PDURoomCodecEnrichmentSignals(QObject):
    presentationAccepted = pyqtSignal(dict)


class PDURoomCodecEnrichmentController(QObject):
    """Own focused related-codec enrichment and stale acceptance."""

    def __init__(
        self,
        *,
        inventory_provider: Callable[[], EquipmentInventory | None],
        inventory_failure_provider: Callable[[], EquipmentInventoryLoadError | None] | None = None,
        credential_candidates_provider: Callable[[str, str], Sequence[Mapping[str, Any]]],
        credential_index_provider: Callable[[str, str, Sequence[Mapping[str, Any]]], int],
        credential_revision_provider: Callable[[], int],
        connection_profile_provider: Callable[[str, str], Mapping[str, Any] | None],
        success_persistence: Callable[[str, str, int, Mapping[str, Any] | None], None],
        presentation_callback: Callable[[dict[str, Any]], None] | None = None,
        resolver: RoomContextResolver | None = None,
        status_adapter: RelatedCodecStatusAdapter | None = None,
        session_controller: InteractiveSessionController | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.signals = PDURoomCodecEnrichmentSignals(self)
        self._inventory_provider = inventory_provider
        self._inventory_failure_provider = inventory_failure_provider
        self._credential_candidates_provider = credential_candidates_provider
        self._credential_index_provider = credential_index_provider
        self._credential_revision_provider = credential_revision_provider
        self._connection_profile_provider = connection_profile_provider
        self._success_persistence = success_persistence
        self._resolver = resolver or RoomContextResolver()
        self._status_adapter = status_adapter or RelatedCodecStatusAdapter()
        self._session = session_controller or InteractiveSessionController(
            parent=self,
            handler_factory=self._handler_factory,
        )
        self._generation = 0
        self._operation_serial = itertools.count(1)
        self._current_operation_id: int | None = None
        self._current_session_generation: int | None = None
        self._shutdown = False
        self._meter = CloudLinkMicrophoneMeter(self, session=self._session)
        self._meter.sample.connect(self._on_meter_sample)
        self._meter.terminal.connect(self._on_meter_terminal)
        self._session.signals.result.connect(self._on_session_result)
        self._session.signals.error.connect(self._on_session_error)
        self._session.signals.dropped.connect(self._on_session_dropped)
        if presentation_callback is not None:
            self.signals.presentationAccepted.connect(presentation_callback)

    @property
    def generation(self) -> int:
        return self._generation

    def accept_pdu_refresh(self, context: PDUAcceptedRefreshContext) -> None:
        if self._shutdown:
            return
        self._generation += 1
        generation = self._generation
        operation_id = next(self._operation_serial)
        self._current_operation_id = operation_id
        self._current_session_generation = None
        self._session.invalidate_context()
        self._meter.stop()
        self._publish(
            EnrichmentPresentation(
                generation=generation,
                operation_id=operation_id,
                pdu_generation=context.pdu_generation,
                pdu_refresh_operation_id=context.refresh_operation_id,
                pdu_credential_context_revision=context.credential_context_revision,
                resolution_status="PENDING",
                codec_diagnostic_status=CodecDiagnosticStatus.PENDING.value,
                pending=True,
            )
        )

        inventory = self._inventory_provider()
        resolution = self._resolver.resolve_related_codec(
            inventory,
            context.ip_address,
            context.model,
        )
        if inventory is None:
            failure = self._inventory_failure_provider() if self._inventory_failure_provider else None
            resolution = RoomResolutionResult(
                RoomResolutionStatus.INVENTORY_UNAVAILABLE,
                safe_message=_safe_inventory_message(failure),
            )
        if not self._is_current(generation, operation_id):
            return
        if not resolution.resolved:
            self._publish_resolution_terminal(generation, operation_id, context, resolution)
            return
        room_context = resolution.context
        assert room_context is not None
        try:
            codec_credential_revision = self._credential_revision_provider()
            candidates = tuple(
                dict(candidate)
                for candidate in self._credential_candidates_provider(
                    room_context.codec_diagnostic_model,
                    room_context.codec_ip_address,
                )
            )
            if not candidates:
                self._publish_resolution_terminal(
                    generation,
                    operation_id,
                    context,
                    resolution,
                    codec_status=CodecDiagnosticStatus.UNAVAILABLE,
                    safe_message="Related codec credentials are unavailable.",
                    codec_credential_revision=codec_credential_revision,
                )
                return
            start_index = self._credential_index_provider(
                room_context.codec_diagnostic_model,
                room_context.codec_ip_address,
                candidates,
            )
            saved_profile = self._connection_profile_provider(
                room_context.codec_diagnostic_model,
                room_context.codec_ip_address,
            )
            session_generation = self._session.activate_context(
                room_context.codec_diagnostic_model,
                room_context.codec_ip_address,
                candidates,
                start_index=start_index,
                saved_profile=saved_profile,
            )
            self._current_session_generation = session_generation
            self._publish_resolved_pending(
                generation,
                operation_id,
                context,
                room_context,
                resolution.warnings,
                codec_credential_revision,
            )
            self._session.submit(
                InteractiveOperation(
                    kind="pdu_room_codec_status",
                    method="read_status",
                    args=(room_context.codec_diagnostic_model,),
                    semantic=OperationSemantic.READ_ONLY,
                    quiet=True,
                    client_token=operation_id,
                ),
                generation=session_generation,
            )
        except Exception:
            if self._is_current(generation, operation_id):
                self._publish_resolution_terminal(
                    generation,
                    operation_id,
                    context,
                    resolution,
                    codec_status=CodecDiagnosticStatus.UNAVAILABLE,
                    safe_message="Related codec status is unavailable.",
                )
                self._terminate_session_context()

    def supersede_pdu_context(self, event: PDUContextSuperseded) -> None:
        if self._shutdown:
            return
        self._generation += 1
        generation = self._generation
        operation_id = next(self._operation_serial)
        self._current_operation_id = operation_id
        self._current_session_generation = None
        self._session.invalidate_context()
        self._meter.stop()
        self._publish(
            EnrichmentPresentation(
                generation=generation,
                operation_id=operation_id,
                pdu_generation=event.pdu_generation_or_revision,
                pdu_refresh_operation_id=None,
                resolution_status="NOT_STARTED",
                codec_diagnostic_status=CodecDiagnosticStatus.NOT_STARTED.value,
                reset=True,
            )
        )

    def invalidate_context(self, reason: str = "superseded") -> None:
        self.supersede_pdu_context(PDUContextSuperseded(self._generation + 1, reason))

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        self._generation += 1
        self._current_operation_id = None
        self._current_session_generation = None
        self._session.invalidate_context()
        self._meter.stop()
        self._session.shutdown(wait=False)

    def _handler_factory(self, model: str, kwargs: Mapping[str, Any]) -> Any:
        from core.interactive_session import _default_handler_factory

        handler = _default_handler_factory(model, kwargs)

        def read_status(expected_model=model, related_handler=handler):
            return self._status_adapter.read_status(related_handler, expected_model)

        setattr(handler, "read_status", read_status)
        return handler

    def _on_session_result(self, payload: dict[str, Any]) -> None:
        if payload.get("kind") == "cloudlink_microphone_meter":
            return
        operation_id = payload.get("client_token")
        generation = self._generation
        if not self._is_current(generation, operation_id):
            return
        value = payload.get("value")
        if not hasattr(value, "as_dict"):
            self._publish_current_failure(generation, operation_id, CodecDiagnosticStatus.PROTOCOL_FAILED)
            self._terminate_session_context()
            return
        if not bool(getattr(value, "has_authoritative_status", True)):
            self._publish_current_failure(generation, operation_id, CodecDiagnosticStatus.PROTOCOL_FAILED)
            self._terminate_session_context()
            return
        presentation = self._last_presentation_with_status(
            generation,
            operation_id,
            CodecDiagnosticStatus.SUCCESS,
            value.as_dict(),
        )
        if presentation is None:
            return
        profile = payload.get("connection_profile")
        credential_index = payload.get("credential_index")
        if bool(getattr(value, "complete", False)) and isinstance(credential_index, int):
            self._success_persistence(
                presentation.codec_diagnostic_model or payload.get("model"),
                presentation.codec_ip_address or payload.get("ip_address"),
                credential_index,
                profile if isinstance(profile, Mapping) else None,
            )
        self._publish(presentation)
        if presentation.codec_diagnostic_model in SUPPORTED_CLOUDLINK_METER_MODELS:
            self._meter.start(
                presentation.codec_diagnostic_model,
                presentation.codec_ip_address or payload.get("ip_address"),
                (), generation=self._current_session_generation, token=operation_id,
            )
        else:
            self._terminate_session_context()

    def _on_session_error(self, payload: dict[str, Any]) -> None:
        if payload.get("kind") == "cloudlink_microphone_meter":
            return
        operation_id = payload.get("client_token")
        generation = self._generation
        if not self._is_current(generation, operation_id):
            return
        category = payload.get("category")
        status = {
            CodecFailureCategory.AUTHENTICATION.value: CodecDiagnosticStatus.AUTHENTICATION_FAILED,
            CodecFailureCategory.TRANSPORT.value: CodecDiagnosticStatus.TRANSPORT_FAILED,
            CodecFailureCategory.SESSION_INVALID.value: CodecDiagnosticStatus.TRANSPORT_FAILED,
            CodecFailureCategory.PROTOCOL.value: CodecDiagnosticStatus.PROTOCOL_FAILED,
        }.get(category, CodecDiagnosticStatus.UNAVAILABLE)
        self._publish_current_failure(generation, operation_id, status)
        self._terminate_session_context()

    def _on_session_dropped(self, _payload: dict[str, Any]) -> None:
        return

    def _publish_resolution_terminal(
        self,
        generation: int,
        operation_id: int,
        pdu_context: PDUAcceptedRefreshContext,
        resolution: RoomResolutionResult,
        *,
        codec_status: CodecDiagnosticStatus = CodecDiagnosticStatus.NOT_STARTED,
        safe_message: str | None = None,
        codec_credential_revision: int | None = None,
    ) -> None:
        self._publish(
            EnrichmentPresentation(
                generation=generation,
                operation_id=operation_id,
                pdu_generation=pdu_context.pdu_generation,
                pdu_refresh_operation_id=pdu_context.refresh_operation_id,
                pdu_credential_context_revision=pdu_context.credential_context_revision,
                codec_credential_context_revision=codec_credential_revision,
                resolution_status=resolution.status.value,
                codec_diagnostic_status=codec_status.value,
                room_id=resolution.room_id,
                room_name=resolution.room_name,
                room_vip_status=getattr(resolution.room_vip_status, "value", resolution.room_vip_status),
                room_vip_label=room_vip_label(resolution.room_vip_status),
                codec_source_model=resolution.codec_source_model,
                codec_diagnostic_model=resolution.codec_diagnostic_model,
                codec_ip_address=resolution.codec_ip_address,
                warnings=resolution.warnings,
                safe_message=safe_message or resolution.safe_message,
            )
        )

    def _publish_resolved_pending(
        self,
        generation: int,
        operation_id: int,
        pdu_context: PDUAcceptedRefreshContext,
        room_context: RoomContext,
        warnings: tuple[str, ...],
        codec_credential_revision: int,
    ) -> None:
        self._publish(
            EnrichmentPresentation(
                generation=generation,
                operation_id=operation_id,
                pdu_generation=pdu_context.pdu_generation,
                pdu_refresh_operation_id=pdu_context.refresh_operation_id,
                pdu_credential_context_revision=pdu_context.credential_context_revision,
                codec_credential_context_revision=codec_credential_revision,
                resolution_status=RoomResolutionStatus.RESOLVED.value,
                codec_diagnostic_status=CodecDiagnosticStatus.PENDING.value,
                room_id=room_context.room_id,
                room_name=room_context.room_name,
                room_vip_status=room_context.room_vip_status.value,
                room_vip_label=room_vip_label(room_context.room_vip_status),
                codec_source_model=room_context.codec_source_model,
                codec_diagnostic_model=room_context.codec_diagnostic_model,
                codec_ip_address=room_context.codec_ip_address,
                warnings=warnings,
                pending=True,
            )
        )

    def _publish_current_failure(
        self,
        generation: int,
        operation_id: int,
        status: CodecDiagnosticStatus,
    ) -> None:
        presentation = self._last_presentation_with_status(generation, operation_id, status, {})
        if presentation is not None:
            self._publish(presentation)

    def _last_presentation_with_status(
        self,
        generation: int,
        operation_id: int,
        status: CodecDiagnosticStatus,
        fields: Mapping[str, Any],
    ) -> EnrichmentPresentation | None:
        current = getattr(self, "_last_presentation", None)
        if current is None or current.generation != generation or current.operation_id != operation_id:
            return None
        return EnrichmentPresentation(
            generation=current.generation,
            operation_id=current.operation_id,
            pdu_generation=current.pdu_generation,
            pdu_refresh_operation_id=current.pdu_refresh_operation_id,
            pdu_credential_context_revision=current.pdu_credential_context_revision,
            codec_credential_context_revision=current.codec_credential_context_revision,
            resolution_status=current.resolution_status,
            codec_diagnostic_status=status.value,
            room_id=current.room_id,
            room_name=current.room_name,
            room_vip_status=current.room_vip_status,
            room_vip_label=current.room_vip_label,
            codec_source_model=current.codec_source_model,
            codec_diagnostic_model=current.codec_diagnostic_model,
            codec_ip_address=current.codec_ip_address,
            call_status=fields.get("call_status"),
            presentation_status=fields.get("presentation_status"),
            microphone_available=current.microphone_available,
            microphone_raw_level=current.microphone_raw_level,
            microphone_fraction=current.microphone_fraction,
            warnings=current.warnings,
            safe_message=current.safe_message,
        )

    def _publish(self, presentation: EnrichmentPresentation) -> None:
        if self._is_current(presentation.generation, presentation.operation_id):
            self._last_presentation = presentation
            self.signals.presentationAccepted.emit(presentation.as_dict())

    def _is_current(self, generation: int, operation_id: int | None) -> bool:
        return (
            not self._shutdown
            and operation_id is not None
            and self._generation == generation
            and self._current_operation_id == operation_id
        )

    def _terminate_session_context(self) -> None:
        self._meter.stop()
        if self._current_session_generation is None:
            return
        self._current_session_generation = None
        self._session.invalidate_context()

    def _on_meter_sample(self, sample: dict[str, Any]) -> None:
        current = getattr(self, "_last_presentation", None)
        if current is None or not self._is_current(current.generation, current.operation_id):
            return
        if (
            sample.get("_meter_generation") != self._current_session_generation
            or sample.get("_meter_token") != current.operation_id
        ):
            return
        available = bool(sample.get("available"))
        self._publish(EnrichmentPresentation(
            **{**current.__dict__, "microphone_available": available,
               "microphone_raw_level": sample.get("raw_level") if available else None,
               "microphone_fraction": sample.get("fraction") if available else None}
        ))

    def _on_meter_terminal(self, outcome: dict[str, Any]) -> None:
        """Close the retained dedicated lane after typed meter recovery fails."""
        current = getattr(self, "_last_presentation", None)
        if current is None or not self._is_current(current.generation, current.operation_id):
            return
        if (
            outcome.get("_meter_generation") != self._current_session_generation
            or outcome.get("_meter_token") != current.operation_id
        ):
            return
        # Keep the accepted related-codec status and PDU result intact; only
        # optional telemetry is unavailable.  _terminate_session_context()
        # schedules handler cleanup on the dedicated session lane.
        self._publish(EnrichmentPresentation(
            **{**current.__dict__, "microphone_available": False,
               "microphone_raw_level": None, "microphone_fraction": None}
        ))
        self._terminate_session_context()


def _safe_inventory_message(error: EquipmentInventoryLoadError | None) -> str:
    if error is None:
        return "Equipment inventory is unavailable."
    category = getattr(error, "category", None)
    if category is not None:
        return f"Equipment inventory unavailable: {category.value}."
    return "Equipment inventory is unavailable."
