"""Narrow related-codec status adapter."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

from core.exceptions import ProtocolError


UNKNOWN_STATUS = "unknown"

_HUAWEI_CALL_COMMANDS = {
    "Huawei TE20": "get_call_status",
    "Huawei TE40": "get_call_status",
    "CloudLink Bar 310": "get_call_status",
}

_HUAWEI_PRESENTATION_COMMANDS = {
    "Huawei TE20": "get_presentation_local",
    "Huawei TE40": "get_presentation",
    "CloudLink Bar 310": "get_presentation",
}

_CALL_STATUS_MAPS = {
    "Huawei TE20": {
        0: "No Call",
        1: "Calling",
        2: "Disconnected",
    },
    "Huawei TE40": {
        0: "No Call",
        1: "Disconnected",
        2: "Calling",
    },
    "CloudLink Bar 310": {
        0: "No Call",
        1: "Calling",
        2: "Disconnected",
        3: "Connected",
    },
}


@dataclass(frozen=True)
class RelatedCodecStatus:
    call_status: str
    presentation_status: str

    def as_dict(self) -> dict[str, str]:
        return {
            "call_status": self.call_status,
            "presentation_status": self.presentation_status,
        }


class RelatedCodecStatusAdapter:
    """Normalize the small status surface needed by PDUScreen."""

    supported_models = frozenset(
        {
            "Huawei TE20",
            "Huawei TE40",
            "CloudLink Bar 310",
            "Polycom RPG 310",
        }
    )

    def read_status(self, handler: Any, model: str) -> RelatedCodecStatus:
        if model not in self.supported_models:
            raise ProtocolError("Related codec status model is unsupported.")
        if model in _HUAWEI_CALL_COMMANDS:
            return self._read_huawei_status(handler, model)
        if model == "Polycom RPG 310":
            return self._read_polycom_status(handler)
        raise ProtocolError("Related codec status model is unsupported.")

    def normalize(self, model: str, raw_status: Mapping[str, Any]) -> RelatedCodecStatus:
        if model not in self.supported_models:
            raise ProtocolError("Related codec status model is unsupported.")
        call_status = _string_value(
            raw_status.get("call_status")
            or raw_status.get("Статус звонка")
            or _nested(raw_status, "call", "status")
        )
        presentation_status = _string_value(
            raw_status.get("presentation_status")
            or raw_status.get("presentation")
            or raw_status.get("presentation_local")
            or raw_status.get("Режим презентации")
        )
        if call_status is None and presentation_status is None:
            raise ProtocolError("Related codec status fields are unavailable.")
        return RelatedCodecStatus(
            call_status=call_status or UNKNOWN_STATUS,
            presentation_status=presentation_status or UNKNOWN_STATUS,
        )

    def _read_huawei_status(self, handler: Any, model: str) -> RelatedCodecStatus:
        send_command = getattr(handler, "send_command", None)
        if not callable(send_command):
            raise ProtocolError("Related codec handler does not expose commands.")
        call_status = _read_huawei_call_status(send_command, model)
        presentation_status = _read_huawei_presentation_status(send_command, model)
        if call_status is None and presentation_status is None:
            raise ProtocolError("Related codec status fields are unavailable.")
        return RelatedCodecStatus(
            call_status=call_status or UNKNOWN_STATUS,
            presentation_status=presentation_status or UNKNOWN_STATUS,
        )

    def _read_polycom_status(self, handler: Any) -> RelatedCodecStatus:
        call_status = None
        presentation_status = None
        get_call_status = getattr(handler, "_get_call_status", None)
        if callable(get_call_status):
            try:
                call_status = _string_value(get_call_status())
            except Exception:
                call_status = None
        get_presentation_status = getattr(handler, "get_presentation_status", None)
        if callable(get_presentation_status):
            try:
                presentation_status = _string_value(get_presentation_status())
            except Exception:
                presentation_status = None
        if call_status is None and presentation_status is None:
            raise ProtocolError("Related codec status fields are unavailable.")
        return RelatedCodecStatus(
            call_status=call_status or UNKNOWN_STATUS,
            presentation_status=presentation_status or UNKNOWN_STATUS,
        )


def _read_huawei_call_status(send_command: Any, model: str) -> str | None:
    result = _successful_result(send_command(_HUAWEI_CALL_COMMANDS[model]))
    if result is None:
        return None
    data = _object_data(result.get("data"))
    state = data.get("state")
    if not isinstance(state, Mapping) or "callstate" not in state:
        return None
    try:
        call_state = int(state["callstate"])
    except (TypeError, ValueError):
        return None
    return _CALL_STATUS_MAPS[model].get(call_state, "Unknown")


def _read_huawei_presentation_status(send_command: Any, model: str) -> str | None:
    result = _successful_result(send_command(_HUAWEI_PRESENTATION_COMMANDS[model]))
    if result is None:
        return None
    data = _object_data(result.get("data"))
    if "isSendAux" not in data:
        return None
    return "Start" if data.get("isSendAux") == "auxOpen" else "Stop"


def _successful_result(result: Any) -> Mapping[str, Any] | None:
    if not isinstance(result, Mapping) or result.get("success") != 1:
        return None
    return result


def _object_data(data: Any) -> Mapping[str, Any]:
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return {}
    if isinstance(data, Mapping):
        return data
    return {}


def _nested(mapping: Mapping[str, Any], key: str, child: str) -> Any:
    value = mapping.get(key)
    if isinstance(value, Mapping):
        return value.get(child)
    return None


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() == "N/A":
        return None
    return text
