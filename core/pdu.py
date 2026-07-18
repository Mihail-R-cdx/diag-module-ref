"""Shared PDU operation contracts for GUI dispatch and offline tests."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional

from core.exceptions import (
    AuthenticationError,
    CommandError,
    CommandOutcomeUnknownError,
    CommandRejectedError,
    UnsupportedOperationError,
)


COMMAND_ON = "on"
COMMAND_OFF = "off"
COMMAND_REBOOT = "reboot"
BULK_COMMAND_ON = "bulk_on"
BULK_COMMAND_OFF = "bulk_off"
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
    outlet_sequence: tuple[int, ...] = field(default_factory=tuple)


def pdu_capabilities(model: str) -> frozenset[str]:
    return PDU_CAPABILITIES.get(model, frozenset())


def pdu_result_capabilities(model: str) -> dict[str, bool]:
    capabilities = pdu_capabilities(model)
    return {
        REFRESH: REFRESH in capabilities,
        COMMAND_ON: COMMAND_ON in capabilities,
        COMMAND_OFF: COMMAND_OFF in capabilities,
        COMMAND_REBOOT: COMMAND_REBOOT in capabilities,
        BULK_COMMAND_ON: COMMAND_ON in capabilities,
        BULK_COMMAND_OFF: COMMAND_OFF in capabilities,
    }


def ensure_pdu_operation_supported(model: str, operation: str) -> None:
    if operation == BULK_COMMAND_ON:
        operation = COMMAND_ON
    elif operation == BULK_COMMAND_OFF:
        operation = COMMAND_OFF
    if operation not in pdu_capabilities(model):
        raise UnsupportedOperationError(f"{model} does not support PDU operation {operation!r}.")


def validate_pdu_outlet(model: str, outlet_number: int) -> None:
    if not isinstance(outlet_number, int) or isinstance(outlet_number, bool) or outlet_number < 1:
        raise UnsupportedOperationError("PDU outlet number must be a positive integer.")
    if model == "Extron IPL T PCS4i" and outlet_number not in range(1, 5):
        raise UnsupportedOperationError("PCS4i outlet number must be in range 1..4.")


def validate_pdu_bulk_outlet_sequence(model: str, outlet_sequence: tuple[int, ...]) -> tuple[int, ...]:
    if not outlet_sequence:
        raise CommandError("PDU bulk operation requires at least one outlet.")
    seen: set[int] = set()
    for outlet_number in outlet_sequence:
        validate_pdu_outlet(model, outlet_number)
        if outlet_number in seen:
            raise CommandError(f"Duplicate PDU outlet number in bulk sequence: {outlet_number}.")
        seen.add(outlet_number)
    return tuple(sorted(outlet_sequence))


def build_pdu_bulk_outlet_sequence(model: str, outlet_records: Any) -> tuple[int, ...]:
    sequence: list[int] = []
    for record in outlet_records or ():
        if not isinstance(record, Mapping):
            raise CommandError("PDU outlet record is malformed.")
        outlet_number = record.get("number")
        if not isinstance(outlet_number, int) or isinstance(outlet_number, bool):
            raise CommandError("PDU outlet record has missing or malformed number.")
        sequence.append(outlet_number)
    return validate_pdu_bulk_outlet_sequence(model, tuple(sequence))


def is_pdu_bulk_operation(operation: str) -> bool:
    return operation in {BULK_COMMAND_ON, BULK_COMMAND_OFF}


def bulk_target_operation(operation: str) -> str:
    if operation == BULK_COMMAND_ON:
        return COMMAND_ON
    if operation == BULK_COMMAND_OFF:
        return COMMAND_OFF
    raise UnsupportedOperationError(f"Unsupported PDU bulk operation: {operation}")


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


class _MutationTrackingHandler:
    def __init__(self, handler: Any):
        self._handler = handler
        self.state_changing_send_attempted = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._handler, name)

    def send_outlet_command_once(self, outlet_number: int, operation: str) -> None:
        self.state_changing_send_attempted = True
        send = getattr(self._handler, "send_outlet_command_once", None)
        if callable(send):
            send(outlet_number, operation)
            return
        if operation == COMMAND_ON:
            self._handler.turn_on(outlet_number)
        elif operation == COMMAND_OFF:
            self._handler.turn_off(outlet_number)
        elif operation == COMMAND_REBOOT:
            self._handler.reboot(outlet_number)
        else:
            raise UnsupportedOperationError(f"Unsupported PDU operation: {operation}")


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
    except AuthenticationError:
        raise
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
    tracker = _MutationTrackingHandler(handler)
    try:
        if not is_current(descriptor):
            return {"_outcome": "stale", "operation": descriptor.operation}
        handler.connect()
        if descriptor.operation in (COMMAND_ON, COMMAND_OFF):
            try:
                success = _execute_absolute_outlet_policy(
                    tracker,
                    descriptor.outlet_number,
                    descriptor.operation,
                )
            except AuthenticationError as error:
                if tracker.state_changing_send_attempted:
                    raise CommandOutcomeUnknownError(
                        "PDU authentication failed after a state-changing command; "
                        "outcome is indeterminate."
                    ) from error
                raise
        elif descriptor.operation == COMMAND_REBOOT:
            try:
                success = _execute_reboot_policy(tracker, descriptor.outlet_number)
            except AuthenticationError as error:
                if tracker.state_changing_send_attempted:
                    raise CommandOutcomeUnknownError(
                        "PDU authentication failed after a state-changing command; "
                        "outcome is indeterminate."
                    ) from error
                raise
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
            "state_changing_send_attempted": tracker.state_changing_send_attempted,
        }
    finally:
        disconnect_quietly(handler)


def execute_pdu_bulk(
    *,
    descriptor: PDUOperationDescriptor,
    credentials: Mapping[str, Any],
    is_current: Callable[[PDUOperationDescriptor], bool],
    handler_factory: Callable[[str, str, Mapping[str, Any]], Any] = build_pdu_handler,
    delay: Callable[[float], None] = time.sleep,
    interval_seconds: float = 1.0,
) -> dict[str, Any]:
    target_operation = bulk_target_operation(descriptor.operation)
    ensure_pdu_operation_supported(descriptor.model, descriptor.operation)
    outlet_sequence = validate_pdu_bulk_outlet_sequence(
        descriptor.model,
        tuple(descriptor.outlet_sequence),
    )
    if not is_current(descriptor):
        return {
            "action": "pdu_bulk",
            "success": False,
            "operation": descriptor.operation,
            "target_operation": target_operation,
            "outlet_sequence": outlet_sequence,
            "successful_outlets": (),
            "stopping_outlet": outlet_sequence[0],
            "terminal_state": "stale_before_mutation",
            "state_changing_send_attempted": False,
            "_outcome": "stale",
        }

    handler = handler_factory(
        descriptor.model,
        descriptor.ip_address,
        normalize_pdu_credentials(descriptor.model, credentials),
    )
    tracker = _MutationTrackingHandler(handler)
    successful_outlets: list[int] = []
    try:
        if not is_current(descriptor):
            return {
                "action": "pdu_bulk",
                "success": False,
                "operation": descriptor.operation,
                "target_operation": target_operation,
                "outlet_sequence": outlet_sequence,
                "successful_outlets": tuple(successful_outlets),
                "stopping_outlet": outlet_sequence[0],
                "terminal_state": "stale_before_mutation",
                "state_changing_send_attempted": False,
                "_outcome": "stale",
            }
        handler.connect()

        for index, outlet_number in enumerate(outlet_sequence):
            if index > 0:
                if not is_current(descriptor):
                    return {
                        "action": "pdu_bulk",
                        "success": False,
                        "operation": descriptor.operation,
                        "target_operation": target_operation,
                        "outlet_sequence": outlet_sequence,
                        "successful_outlets": tuple(successful_outlets),
                        "stopping_outlet": outlet_number,
                        "terminal_state": "stale_after_partial_completion",
                        "state_changing_send_attempted": tracker.state_changing_send_attempted,
                        "_outcome": "stale",
                    }
                delay(interval_seconds)
                if not is_current(descriptor):
                    return {
                        "action": "pdu_bulk",
                        "success": False,
                        "operation": descriptor.operation,
                        "target_operation": target_operation,
                        "outlet_sequence": outlet_sequence,
                        "successful_outlets": tuple(successful_outlets),
                        "stopping_outlet": outlet_number,
                        "terminal_state": "stale_after_partial_completion",
                        "state_changing_send_attempted": tracker.state_changing_send_attempted,
                        "_outcome": "stale",
                    }

            try:
                _execute_absolute_outlet_policy(
                    tracker,
                    outlet_number,
                    target_operation,
                )
            except Exception as error:
                if isinstance(error, AuthenticationError) and not tracker.state_changing_send_attempted:
                    raise
                return {
                    "action": "pdu_bulk",
                    "success": False,
                    "operation": descriptor.operation,
                    "target_operation": target_operation,
                    "outlet_sequence": outlet_sequence,
                    "successful_outlets": tuple(successful_outlets),
                    "stopping_outlet": outlet_number,
                    "terminal_state": "partial_failure"
                    if successful_outlets
                    else "failure_before_completion",
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "state_changing_send_attempted": tracker.state_changing_send_attempted,
                    "_credential_used": bool(getattr(handler, "credential_used", False)),
                }

            successful_outlets.append(outlet_number)

        return {
            "action": "pdu_bulk",
            "success": True,
            "operation": descriptor.operation,
            "target_operation": target_operation,
            "outlet_sequence": outlet_sequence,
            "successful_outlets": tuple(successful_outlets),
            "stopping_outlet": None,
            "terminal_state": "full_success",
            "state_changing_send_attempted": tracker.state_changing_send_attempted,
            "_credential_used": bool(getattr(handler, "credential_used", False)),
        }
    finally:
        disconnect_quietly(handler)
