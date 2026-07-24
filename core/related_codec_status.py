"""Narrow related-codec status adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.exceptions import ProtocolError


UNKNOWN_STATUS = "unknown"


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
        get_status = getattr(handler, "get_status", None)
        if not callable(get_status):
            raise ProtocolError("Related codec handler does not expose status.")
        raw_status = get_status()
        if not isinstance(raw_status, Mapping):
            raise ProtocolError("Related codec status response is invalid.")
        return self.normalize(model, raw_status)

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
