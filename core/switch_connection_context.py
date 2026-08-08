"""Pure equipment switch-connection presentation resolution.

This module converts the one unambiguous canonical record for a normalized
device IP into safe scalar display values for the switch connection rows.
It is a pure, UI-independent resolver: it never talks to a switch, never
queries by switch IP/port, and never becomes a device-diagnostic authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.equipment_inventory import EquipmentInventory, normalize_ip_address


class SwitchConnectionStatus(str, Enum):
    INVENTORY_UNAVAILABLE = "INVENTORY_UNAVAILABLE"
    INVALID_IP = "INVALID_IP"
    IP_NOT_FOUND = "IP_NOT_FOUND"
    AMBIGUOUS_IP = "AMBIGUOUS_IP"
    RESOLVED = "RESOLVED"


@dataclass(frozen=True)
class SwitchConnectionPresentation:
    """Safe scalar equipment-page switch presentation values.

    The status is a safe internal resolution/status marker for tests and
    lifecycle diagnostics. It never exposes workbook rows, source evidence,
    or mutable canonical state, and it is not a device failure category.
    """

    status: SwitchConnectionStatus
    switch_ip_address: str | None = None
    switch_port: str | None = None

    @property
    def resolved(self) -> bool:
        return self.status is SwitchConnectionStatus.RESOLVED


class SwitchConnectionResolver:
    """Resolve equipment-page switch presentation without side effects."""

    def resolve_switch_connection(
        self,
        inventory: EquipmentInventory | None,
        equipment_ip_address: str | None,
    ) -> SwitchConnectionPresentation:
        if inventory is None:
            return SwitchConnectionPresentation(
                SwitchConnectionStatus.INVENTORY_UNAVAILABLE
            )
        normalized_ip = normalize_ip_address(equipment_ip_address)
        if normalized_ip is None:
            return SwitchConnectionPresentation(SwitchConnectionStatus.INVALID_IP)
        records = tuple(inventory.find_by_ip(normalized_ip))
        if not records:
            return SwitchConnectionPresentation(SwitchConnectionStatus.IP_NOT_FOUND)
        if len(records) > 1:
            return SwitchConnectionPresentation(SwitchConnectionStatus.AMBIGUOUS_IP)
        record = records[0]
        return SwitchConnectionPresentation(
            SwitchConnectionStatus.RESOLVED,
            switch_ip_address=record.switch_ip_address,
            switch_port=record.switch_port,
        )
