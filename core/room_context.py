"""Pure PDU room and related codec resolution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.equipment_inventory import EquipmentInventory, EquipmentRecord


SUPPORTED_RELATED_CODEC_MODELS = frozenset(
    {
        "Huawei TE20",
        "Huawei TE40",
        "CloudLink Bar 310",
        "Polycom RPG 310",
    }
)


class RoomResolutionStatus(str, Enum):
    INVENTORY_UNAVAILABLE = "INVENTORY_UNAVAILABLE"
    PDU_NOT_FOUND = "PDU_NOT_FOUND"
    AMBIGUOUS_PDU_IP = "AMBIGUOUS_PDU_IP"
    PDU_KIND_MISMATCH = "PDU_KIND_MISMATCH"
    ROOM_UNRESOLVED = "ROOM_UNRESOLVED"
    CODEC_NOT_FOUND = "CODEC_NOT_FOUND"
    AMBIGUOUS_CODEC = "AMBIGUOUS_CODEC"
    CODEC_IP_MISSING = "CODEC_IP_MISSING"
    CODEC_UNSUPPORTED = "CODEC_UNSUPPORTED"
    RESOLVED = "RESOLVED"


ROOM_NAME_CONFLICT = "ROOM_NAME_CONFLICT"


@dataclass(frozen=True)
class RoomContext:
    snapshot_id: str
    pdu_record_id: str
    pdu_model: str | None
    pdu_ip_address: str
    room_id: str
    room_name: str | None
    codec_record_id: str
    codec_source_model: str | None
    codec_diagnostic_model: str
    codec_ip_address: str


@dataclass(frozen=True)
class RoomResolutionResult:
    status: RoomResolutionStatus
    context: RoomContext | None = None
    warnings: tuple[str, ...] = ()
    safe_message: str | None = None
    room_id: str | None = None
    room_name: str | None = None
    codec_source_model: str | None = None
    codec_diagnostic_model: str | None = None
    codec_ip_address: str | None = None

    @property
    def resolved(self) -> bool:
        return self.status is RoomResolutionStatus.RESOLVED and self.context is not None


class RoomContextResolver:
    """Resolve exact PDU-room-codec context without side effects."""

    def resolve_related_codec(
        self,
        inventory: EquipmentInventory | None,
        pdu_ip_address: str,
    ) -> RoomResolutionResult:
        if inventory is None:
            return RoomResolutionResult(
                RoomResolutionStatus.INVENTORY_UNAVAILABLE,
                safe_message="Equipment inventory is unavailable.",
            )

        pdu_records = tuple(inventory.find_by_ip(pdu_ip_address))
        if not pdu_records:
            return RoomResolutionResult(RoomResolutionStatus.PDU_NOT_FOUND)
        if len(pdu_records) > 1:
            return RoomResolutionResult(RoomResolutionStatus.AMBIGUOUS_PDU_IP)

        pdu_record = pdu_records[0]
        if pdu_record.device_kind != "pdu":
            return RoomResolutionResult(RoomResolutionStatus.PDU_KIND_MISMATCH)
        if not pdu_record.room_id:
            return RoomResolutionResult(
                RoomResolutionStatus.ROOM_UNRESOLVED,
                room_name=pdu_record.room_name,
            )

        room_records = tuple(inventory.find_room_equipment(pdu_record.room_id))
        room_name, warnings = _room_name_evidence(room_records)
        codec_records = tuple(
            inventory.find_by_room_and_kind(pdu_record.room_id, "video_codec")
        )
        if not codec_records:
            return RoomResolutionResult(
                RoomResolutionStatus.CODEC_NOT_FOUND,
                warnings=warnings,
                room_id=pdu_record.room_id,
                room_name=room_name,
            )
        if len(codec_records) > 1:
            return RoomResolutionResult(
                RoomResolutionStatus.AMBIGUOUS_CODEC,
                warnings=warnings,
                room_id=pdu_record.room_id,
                room_name=room_name,
            )

        codec_record = codec_records[0]
        if not codec_record.ip_address:
            return RoomResolutionResult(
                RoomResolutionStatus.CODEC_IP_MISSING,
                warnings=warnings,
                room_id=pdu_record.room_id,
                room_name=room_name,
                codec_source_model=codec_record.source_model,
                codec_diagnostic_model=codec_record.diagnostic_model,
            )
        if codec_record.diagnostic_model not in SUPPORTED_RELATED_CODEC_MODELS:
            return RoomResolutionResult(
                RoomResolutionStatus.CODEC_UNSUPPORTED,
                warnings=warnings,
                room_id=pdu_record.room_id,
                room_name=room_name,
                codec_source_model=codec_record.source_model,
                codec_diagnostic_model=codec_record.diagnostic_model,
                codec_ip_address=codec_record.ip_address,
            )

        context = RoomContext(
            snapshot_id=inventory.metadata.snapshot_id,
            pdu_record_id=pdu_record.record_id,
            pdu_model=pdu_record.diagnostic_model,
            pdu_ip_address=pdu_record.ip_address or pdu_ip_address,
            room_id=pdu_record.room_id,
            room_name=room_name,
            codec_record_id=codec_record.record_id,
            codec_source_model=codec_record.source_model,
            codec_diagnostic_model=codec_record.diagnostic_model,
            codec_ip_address=codec_record.ip_address,
        )
        return RoomResolutionResult(
            RoomResolutionStatus.RESOLVED,
            context=context,
            warnings=warnings,
            room_id=context.room_id,
            room_name=context.room_name,
            codec_source_model=context.codec_source_model,
            codec_diagnostic_model=context.codec_diagnostic_model,
            codec_ip_address=context.codec_ip_address,
        )


def _room_name_evidence(records: tuple[EquipmentRecord, ...]) -> tuple[str | None, tuple[str, ...]]:
    names = {
        record.room_name
        for record in records
        if isinstance(record.room_name, str) and record.room_name.strip()
    }
    if len(names) == 1:
        return next(iter(names)), ()
    if len(names) > 1:
        return None, (ROOM_NAME_CONFLICT,)
    return None, ()
