"""Shared PDU operation contracts for GUI dispatch and offline tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

from core.exceptions import (
    CommandError,
    CommandOutcomeUnknownError,
    CommandRejectedError,
    UnsupportedOperationError,
)


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
        raise UnsupportedOperationError(f"{model} does not support PDU operation {operation!r}.")


def validate_pdu_outlet(model: str, outlet_number: int) -> None:
    if model == "Extron IPL T PCS4i" and outlet_number not in range(1, 5):
        raise UnsupportedOperationError("PCS4i outlet number must be in range 1..4.")


def normalize_pdu_credentials(model: str, credentials: Mapping[str, Any]) -> dict[str, Any]:
    raw = dict(credentials or {})
    if model == "Extron IPL T PCS4i":
        return {"password": raw["password"]} if raw.get("password") else {}
    return raw


def normalize_pdu_credential_candidates(model: str, credentials: Any) -> list[dict[str, Any]]:
    return [normalize_pdu_credentials(model, credential) for credential in (credentials or ())]


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


def _read_outlet_power_state(handler: Any, outlet_number: int) -> bool:
    read = getattr(handler, "read_outlet_power_state", None)
    if callable(read):
        return bool(read(outlet_number))

    for outlet in handler.get_outlets_status():
        if outlet.get("number") == outlet_number:
            status = str(outlet.get("status")).strip().lower()
            if status in {"on", "1", "true"}:
                return True
            if status in {"off", "0", "false"}:
                return False
            break
    raise CommandOutcomeUnknownError("PDU outlet state is unavailable.")


def _try_read_outlet_power_state(handler: Any, outlet_number: int) -> Optional[bool]:
    try:
        return _read_outlet_power_state(handler, outlet_number)
    except Exception:
        return None


def _send_outlet_command_once(handler: Any, outlet_number: int, operation: str) -> None:
    send = getattr(handler, "send_outlet_command_once", None)
    if callable(send):
        send(outlet_number, operation)
        return

    if operation == COMMAND_ON:
        handler.turn_on(outlet_number)
    elif operation == COMMAND_OFF:
        handler.turn_off(outlet_number)
    elif operation == COMMAND_REBOOT:
        handler.reboot(outlet_number)
    else:
        raise UnsupportedOperationError(f"Unsupported PDU operation: {operation}")


def _execute_absolute_outlet_policy(handler: Any, outlet_number: int, operation: str) -> bool:
    target_on = operation == COMMAND_ON
    pre_state = _try_read_outlet_power_state(handler, outlet_number)

    try:
        _send_outlet_command_once(handler, outlet_number, operation)
    except CommandOutcomeUnknownError:
        pass

    post_state = _try_read_outlet_power_state(handler, outlet_number)
    if post_state is target_on:
        return True
    if post_state is None:
        raise CommandOutcomeUnknownError("PDU command outcome is indeterminate.")
    if pre_state is None:
        raise CommandOutcomeUnknownError("PDU command outcome is indeterminate.")
    if post_state is pre_state:
        try:
            _send_outlet_command_once(handler, outlet_number, operation)
        except CommandOutcomeUnknownError:
            pass

        terminal_state = _try_read_outlet_power_state(handler, outlet_number)
        if terminal_state is target_on:
            return True
        if terminal_state is pre_state:
            raise CommandRejectedError("PDU command did not reach the requested state.")
        raise CommandOutcomeUnknownError("PDU terminal confirmation is indeterminate.")

    raise CommandOutcomeUnknownError("PDU command outcome is indeterminate.")


def _execute_reboot_policy(handler: Any, outlet_number: int) -> bool:
    _send_outlet_command_once(handler, outlet_number, COMMAND_REBOOT)
    return True


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
        if descriptor.operation in (COMMAND_ON, COMMAND_OFF):
            success = _execute_absolute_outlet_policy(
                handler,
                descriptor.outlet_number,
                descriptor.operation,
            )
        elif descriptor.operation == COMMAND_REBOOT:
            success = _execute_reboot_policy(handler, descriptor.outlet_number)
        else:
            raise UnsupportedOperationError(f"Unsupported PDU operation: {descriptor.operation}")
        return {
            "action": "pdu_command",
            "success": bool(success),
            "operation": descriptor.operation,
            "outlet_number": descriptor.outlet_number,
            "ip_address": descriptor.ip_address,
            "device_name": descriptor.model,
            "_credential_used": bool(getattr(handler, "credential_used", False)),
        }
    finally:
        disconnect_quietly(handler)
