"""Central equipment-page registry and shared room presentation widgets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from PyQt5.QtWidgets import QVBoxLayout, QWidget

from core.room_context import RoomVipStatus, room_vip_label

from .components import ParameterRow, SectionCard


PDU_DEVICE_NAMES = frozenset({"Aten PE8208AV", "Extron IPL T PCS4i"})

# Stable labels used on every registered equipment page. The network-connection
# workbook uses the same "IP коммутатора" / "Порт" wording; these are the
# display-only canonical labels for the existing device-information cards.
SWITCH_IP_LABEL = "IP коммутатора"
SWITCH_PORT_LABEL = "Порт коммутатора"


def apply_switch_connection_row_values(
    ip_row: ParameterRow,
    port_row: ParameterRow,
    *,
    switch_ip_address: str | None,
    switch_port: str | None,
) -> None:
    """Render safe scalar switch presentation into the two switch rows.

    Each field is independent: a non-null canonical field is shown exactly
    while a null/absent field renders as an unavailable "—".
    """
    ip_value = str(switch_ip_address) if switch_ip_address is not None else "—"
    port_value = str(switch_port) if switch_port is not None else "—"
    ip_row.set_value(ip_value)
    port_row.set_value(port_value)
    ip_row.set_state("normal" if switch_ip_address is not None else "inactive")
    port_row.set_state("normal" if switch_port is not None else "inactive")


def attach_switch_connection_rows(
    card,
    parent,
):
    """Attach the two switch-presentation rows to the information card.

    The rows are inventory-context presentation, not device-observed status,
    so they carry an explicit ownership marker and are excluded from generic
    device-data clearing. The screen renders only safe scalar values; it never
    queries the inventory or decides lookup multiplicity.
    """
    ip_row = ParameterRow(SWITCH_IP_LABEL, "—", parent)
    port_row = ParameterRow(SWITCH_PORT_LABEL, "—", parent)
    for row in (ip_row, port_row):
        row.setProperty("inventoryContextBoundary", True)
        row.value_display.setProperty("inventoryContextBoundary", True)
        row.value_display.setProperty("data_field", False)
        row.set_value("—")
        row.set_state("inactive")
        card.add_widget(row)
    return (ip_row, port_row)


@dataclass(frozen=True)
class EquipmentPageRegistration:
    screen_key: str
    page_kind: str
    device_models: tuple[str, ...]
    shared_room_block: bool
    dedicated_pdu_room_placement: bool


EQUIPMENT_PAGE_REGISTRY = (
    EquipmentPageRegistration(
        screen_key="codec",
        page_kind="non_pdu",
        device_models=(
            "Huawei TE20",
            "Huawei TE40",
            "Huawei TE50",
            "CloudLink Bar 310",
            "CloudLink Box 310",
            "Polycom RPG 310",
        ),
        shared_room_block=True,
        dedicated_pdu_room_placement=False,
    ),
    EquipmentPageRegistration(
        screen_key="matrix",
        page_kind="non_pdu",
        device_models=(
            "Extron IN1804", "Extron IN1806", "Extron IN1808", "Extron IN1608 xi",
            "Extron DTP CrossPoint 84", "Extron DTP CrossPoint 82 4K",
            "Extron DTP CrossPoint 84 4K", "Extron DTP CrossPoint 86 4K",
            "Extron DTP CrossPoint 108 4K",
        ),
        shared_room_block=True,
        dedicated_pdu_room_placement=False,
    ),
    EquipmentPageRegistration(
        screen_key="audio_dsp",
        page_kind="non_pdu",
        device_models=("Biamp Tesira Forte CI", "Extron DMP 64 Plus"),
        shared_room_block=True,
        dedicated_pdu_room_placement=False,
    ),
    EquipmentPageRegistration(
        screen_key="pdu",
        page_kind="pdu",
        device_models=tuple(sorted(PDU_DEVICE_NAMES)),
        shared_room_block=False,
        dedicated_pdu_room_placement=True,
    ),
)


def registrations_by_screen() -> dict[str, EquipmentPageRegistration]:
    return {registration.screen_key: registration for registration in EQUIPMENT_PAGE_REGISTRY}


def screen_key_for_model(device_model: str) -> str | None:
    for registration in EQUIPMENT_PAGE_REGISTRY:
        if device_model in registration.device_models:
            return registration.screen_key
    return None


def non_pdu_registrations() -> tuple[EquipmentPageRegistration, ...]:
    return tuple(
        registration
        for registration in EQUIPMENT_PAGE_REGISTRY
        if registration.page_kind != "pdu"
    )


class RoomInformationBlock(SectionCard):
    """Reusable room information block kept outside device request state."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Комната", "◇", parent)
        self.setObjectName("sharedRoomInformationBlock")
        self.setProperty("roomContextBoundary", True)
        self.room_vip_row = ParameterRow("VIP", "—", self, compact=True)
        self.room_name_row = ParameterRow("Адрес", "—", self, compact=True)
        self.message_row = ParameterRow("Статус", "—", self, compact=True)
        self.room_vip_value = self.room_vip_row.value_display
        self.room_name_value = self.room_name_row.value_display
        self.message_value = self.message_row.value_display
        for row in (self.room_vip_row, self.room_name_row, self.message_row):
            row.value_display.setProperty("data_field", False)
            self.add_widget(row)
        self.reset_room_presentation()

    def reset_room_presentation(self) -> None:
        self.set_room_presentation(
            room_name=None,
            room_vip_status=RoomVipStatus.UNRESOLVED,
            safe_message=None,
        )

    def set_room_presentation(
        self,
        *,
        room_name: str | None,
        room_vip_status: RoomVipStatus | str | None,
        safe_message: str | None = None,
    ) -> None:
        vip_status_value = getattr(room_vip_status, "value", room_vip_status)
        vip_label = room_vip_label(room_vip_status) or "—"
        self.room_vip_row.set_value(vip_label)
        if vip_status_value == RoomVipStatus.VIP_TRUE.value:
            self.room_vip_row.set_state("success")
        elif vip_status_value == RoomVipStatus.CONFLICT.value:
            self.room_vip_row.set_state("warning")
        elif vip_label == "—":
            self.room_vip_row.set_state("inactive")
        else:
            self.room_vip_row.set_state("normal")

        self.room_name_row.set_value(room_name or "—")
        self.room_name_row.set_state("normal" if room_name else "inactive")

        message = str(safe_message or "").strip()
        self.message_row.setVisible(bool(message))
        self.message_row.set_value(message or "—")
        self.message_row.set_state("warning" if message else "inactive")


def attach_shared_room_block(
    screen: QWidget,
    registration: EquipmentPageRegistration,
) -> RoomInformationBlock | None:
    if not registration.shared_room_block:
        return None

    block = RoomInformationBlock(screen)
    block.setProperty("equipmentPage", registration.screen_key)
    _room_block_layout(screen).insertWidget(_room_block_insert_index(screen), block)
    setattr(screen, "shared_room_information_block", block)
    return block


def _room_block_layout(screen: QWidget) -> QVBoxLayout:
    for attribute in ("param_layout", "content_layout"):
        layout = getattr(screen, attribute, None)
        if isinstance(layout, QVBoxLayout):
            return layout
    content = getattr(screen, "content", None)
    if content is not None and isinstance(content.layout(), QVBoxLayout):
        return content.layout()
    layout = screen.layout()
    if isinstance(layout, QVBoxLayout):
        return layout
    raise RuntimeError(f"Screen {screen!r} does not expose a room-block layout.")


def _room_block_insert_index(screen: QWidget) -> int:
    layout = _room_block_layout(screen)
    if layout.count() > 0 and layout.itemAt(layout.count() - 1).spacerItem() is not None:
        return layout.count() - 1
    return layout.count()


def registered_models() -> tuple[str, ...]:
    return tuple(
        model
        for registration in EQUIPMENT_PAGE_REGISTRY
        for model in registration.device_models
    )
