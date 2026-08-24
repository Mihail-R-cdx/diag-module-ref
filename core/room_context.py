"""Pure equipment-to-room resolution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.equipment_inventory import EquipmentInventory, EquipmentRecord


class RoomResolutionStatus(str, Enum):
    INVENTORY_UNAVAILABLE = "INVENTORY_UNAVAILABLE"
    PDU_NOT_FOUND = "PDU_NOT_FOUND"
    AMBIGUOUS_PDU_IP = "AMBIGUOUS_PDU_IP"
    PDU_MODEL_UNSUPPORTED = "PDU_MODEL_UNSUPPORTED"
    PDU_MODEL_MISMATCH = "PDU_MODEL_MISMATCH"
    ROOM_UNRESOLVED = "ROOM_UNRESOLVED"
    CODEC_NOT_FOUND = "CODEC_NOT_FOUND"
    AMBIGUOUS_CODEC = "AMBIGUOUS_CODEC"
    CODEC_IP_MISSING = "CODEC_IP_MISSING"
    CODEC_UNSUPPORTED = "CODEC_UNSUPPORTED"
    RESOLVED = "RESOLVED"


ROOM_NAME_CONFLICT = "ROOM_NAME_CONFLICT"
ROOM_VIP_CONFLICT = "ROOM_VIP_CONFLICT"
class RoomVipStatus(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    NO_DATA = "NO_DATA"
    VIP_TRUE = "VIP_TRUE"
    VIP_FALSE = "VIP_FALSE"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class EquipmentRoomContext:
    snapshot_id: str
    equipment_record_id: str
    equipment_model: str | None
    equipment_ip_address: str
    room_id: str
    room_name: str | None
    room_vip_status: RoomVipStatus


@dataclass(frozen=True)
class EquipmentRoomResolutionResult:
    status: RoomResolutionStatus
    context: EquipmentRoomContext | None = None
    warnings: tuple[str, ...] = ()
    safe_message: str | None = None
    room_id: str | None = None
    room_name: str | None = None
    room_vip_status: RoomVipStatus | None = None

    @property
    def resolved(self) -> bool:
        return self.status is RoomResolutionStatus.RESOLVED and self.context is not None


class RoomContextResolver:
    """Resolve exact equipment room context without side effects."""

    def resolve_equipment_room_context(
        self,
        inventory: EquipmentInventory | None,
        equipment_ip_address: str,
    ) -> EquipmentRoomResolutionResult:
        if inventory is None:
            return EquipmentRoomResolutionResult(
                RoomResolutionStatus.INVENTORY_UNAVAILABLE,
                safe_message="Equipment inventory is unavailable.",
                room_vip_status=RoomVipStatus.UNRESOLVED,
            )

        resolution = _resolve_record_by_ip(
            inventory,
            equipment_ip_address,
            not_found_status=RoomResolutionStatus.PDU_NOT_FOUND,
            ambiguous_status=RoomResolutionStatus.AMBIGUOUS_PDU_IP,
        )
        if isinstance(resolution, EquipmentRoomResolutionResult):
            return resolution

        return _resolve_room_context_for_record(
            inventory,
            resolution,
            equipment_ip_address,
        )

def aggregate_room_vip(records: tuple[EquipmentRecord, ...]) -> RoomVipStatus:
    if not records:
        return RoomVipStatus.UNRESOLVED
    has_true = any(record.room_vip is True for record in records)
    has_false = any(record.room_vip is False for record in records)
    if has_true and has_false:
        return RoomVipStatus.CONFLICT
    if has_true:
        return RoomVipStatus.VIP_TRUE
    if has_false:
        return RoomVipStatus.VIP_FALSE
    return RoomVipStatus.NO_DATA


def room_vip_label(status: RoomVipStatus | str | None) -> str | None:
    status_value = getattr(status, "value", status)
    return {
        RoomVipStatus.VIP_TRUE.value: "ДА",
        RoomVipStatus.VIP_FALSE.value: "НЕТ",
        RoomVipStatus.NO_DATA.value: "НЕТ ДАННЫХ",
        RoomVipStatus.CONFLICT.value: "КОНФЛИКТ ДАННЫХ",
        RoomVipStatus.UNRESOLVED.value: None,
    }.get(status_value)


def _resolve_record_by_ip(
    inventory: EquipmentInventory,
    equipment_ip_address: str,
    *,
    not_found_status: RoomResolutionStatus,
    ambiguous_status: RoomResolutionStatus,
) -> EquipmentRecord | EquipmentRoomResolutionResult:
    records = tuple(inventory.find_by_ip(equipment_ip_address))
    if not records:
        return EquipmentRoomResolutionResult(not_found_status, room_vip_status=RoomVipStatus.UNRESOLVED)
    if len(records) > 1:
        return EquipmentRoomResolutionResult(ambiguous_status, room_vip_status=RoomVipStatus.UNRESOLVED)
    return records[0]


def _resolve_room_context_for_record(
    inventory: EquipmentInventory,
    record: EquipmentRecord,
    equipment_ip_address: str,
) -> EquipmentRoomResolutionResult:
    if not record.room_id:
        return EquipmentRoomResolutionResult(
            RoomResolutionStatus.ROOM_UNRESOLVED,
            room_name=record.room_name,
            room_vip_status=RoomVipStatus.UNRESOLVED,
        )

    room_records = tuple(inventory.find_room_equipment(record.room_id))
    if not room_records:
        return EquipmentRoomResolutionResult(
            RoomResolutionStatus.ROOM_UNRESOLVED,
            room_id=record.room_id,
            room_name=record.room_name,
            room_vip_status=RoomVipStatus.UNRESOLVED,
        )

    room_name, warnings = _room_name_evidence(room_records)
    room_vip_status = aggregate_room_vip(room_records)
    if room_vip_status is RoomVipStatus.CONFLICT:
        warnings = (*warnings, ROOM_VIP_CONFLICT)
    context = EquipmentRoomContext(
        snapshot_id=inventory.metadata.snapshot_id,
        equipment_record_id=record.record_id,
        equipment_model=record.diagnostic_model,
        equipment_ip_address=record.ip_address or equipment_ip_address,
        room_id=record.room_id,
        room_name=room_name,
        room_vip_status=room_vip_status,
    )
    return EquipmentRoomResolutionResult(
        RoomResolutionStatus.RESOLVED,
        context=context,
        warnings=warnings,
        room_id=context.room_id,
        room_name=context.room_name,
        room_vip_status=context.room_vip_status,
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
