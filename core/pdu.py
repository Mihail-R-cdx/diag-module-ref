"""Shared PDU operation contracts for GUI dispatch and offline tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

from core.exceptions import CommandError


COMMAND_ON = "on"
COMMAND_OFF = "off"
COMMAND_REBOOT = "reboot"
REFRESH = "refresh"


PDU_CAPABILITIES: dict[str, frozenset[str]] = {
    "Aten PE8208AV": frozenset({REFRESH, COMMAND_ON, COMMAND_OFF, COMMAND_REBOOT}),
    "Extron IPL T PCS4i": frozenset({REFRESH, COMMAND_ON, COMMAND_OFF}),
}


@dataclass(frozen=True)
class PDUOperationDescriptor:
    operation_id: int
    generation: int
    model: str
    ip_address: str
    operation: str
    outlet_number: Optional[int] = None
    credential_index: Optional[int] = None
    credential_context: Optional[int] = None


def pdu_capabilities(model: str) -> frozenset[str]:
    return PDU_CAPABILITIES.get(model, frozenset())


def pdu_result_capabilities(model: str) -> dict[str, bool]:
    capabilities = pdu_capabilities(model)
    return {
        REFRESH: REFRESH in capabilities,
        COMMAND_ON: COMMAND_ON in capabilities,
        COMMAND_OFF: COMMAND_OFF in capabilities,
        COMMAND_REBOOT: COMMAND_REBOOT in capabilities,
    }


def ensure_pdu_operation_supported(model: str, operation: str) -> None:
    if operation not in pdu_capabilities(model):
        raise CommandError(f"{model} does not support PDU operation {operation!r}.")


def validate_pdu_outlet(model: str, outlet_number: int) -> None:
    if model == "Extron IPL T PCS4i" and outlet_number not in range(1, 5):
        raise CommandError("PCS4i outlet number must be in range 1..4.")


def normalize_pdu_credentials(model: str, credentials: Mapping[str, Any]) -> dict[str, Any]:
    raw = dict(credentials or {})
    if model == "Extron IPL T PCS4i":
        return {"password": raw["password"]} if raw.get("password") else {}
    return raw


def build_pdu_handler(model: str, ip_address: str, credentials: Mapping[str, Any]):
    credentials = normalize_pdu_credentials(model, credentials)
    if model == "Aten PE8208AV":
        from handlers.aten.pdu import AtenPDUHandler

        return AtenPDUHandler(ip_address=ip_address, port=443, **credentials)
    if model == "Extron IPL T PCS4i":
        from handlers.extron.pcs4i import ExtronIPLTPCS4iHandler

        return ExtronIPLTPCS4iHandler(ip_address=ip_address, **credentials)
    raise CommandError(f"Unsupported PDU model: {model}")


def disconnect_quietly(handler: Any) -> None:
    disconnect = getattr(handler, "disconnect", None)
    if callable(disconnect):
        try:
            disconnect()
        except Exception:
            pass


def execute_pdu_refresh(
    *,
    descriptor: PDUOperationDescriptor,
    credentials: Mapping[str, Any],
    is_current: Callable[[PDUOperationDescriptor], bool],
    handler_factory: Callable[[str, str, Mapping[str, Any]], Any] = build_pdu_handler,
) -> dict[str, Any]:
    ensure_pdu_operation_supported(descriptor.model, REFRESH)
    if not is_current(descriptor):
        return {"_outcome": "stale", "operation": REFRESH}

    handler = handler_factory(
        descriptor.model,
        descriptor.ip_address,
        normalize_pdu_credentials(descriptor.model, credentials),
    )
    try:
        if not is_current(descriptor):
            return {"_outcome": "stale", "operation": REFRESH}
        handler.connect()
        outlets = handler.get_outlets_status()
        device_info = handler.get_device_info()
        result = {
            "device_info": device_info,
            "outlets": outlets,
            "ip_address": descriptor.ip_address,
            "model": device_info.get("model", descriptor.model),
            "manufacturer": device_info.get("manufacturer"),
            "type": "pdu",
            "capabilities": pdu_result_capabilities(descriptor.model),
        }
        if hasattr(handler, "credential_used"):
            result["_credential_used"] = bool(getattr(handler, "credential_used"))
        return result
    finally:
        disconnect_quietly(handler)


def execute_pdu_command(
    *,
    descriptor: PDUOperationDescriptor,
    credentials: Mapping[str, Any],
    is_current: Callable[[PDUOperationDescriptor], bool],
    handler_factory: Callable[[str, str, Mapping[str, Any]], Any] = build_pdu_handler,
) -> dict[str, Any]:
    ensure_pdu_operation_supported(descriptor.model, descriptor.operation)
    if descriptor.outlet_number is None:
        raise CommandError("PDU outlet command requires an outlet number.")
    validate_pdu_outlet(descriptor.model, descriptor.outlet_number)
    if not is_current(descriptor):
        return {"_outcome": "stale", "operation": descriptor.operation}

    handler = handler_factory(
        descriptor.model,
        descriptor.ip_address,
        normalize_pdu_credentials(descriptor.model, credentials),
    )
    try:
        if not is_current(descriptor):
            return {"_outcome": "stale", "operation": descriptor.operation}
        handler.connect()
        if descriptor.operation == COMMAND_ON:
            success = handler.turn_on(descriptor.outlet_number)
        elif descriptor.operation == COMMAND_OFF:
            success = handler.turn_off(descriptor.outlet_number)
        elif descriptor.operation == COMMAND_REBOOT:
            success = handler.reboot(descriptor.outlet_number)
        else:
            raise CommandError(f"Unsupported PDU operation: {descriptor.operation}")
        return {
            "action": "pdu_command",
            "success": bool(success),
            "operation": descriptor.operation,
            "outlet_number": descriptor.outlet_number,
            "ip_address": descriptor.ip_address,
            "device_name": descriptor.model,
        }
    finally:
        disconnect_quietly(handler)
