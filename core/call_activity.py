"""Exact-model call evidence normalization used by room presentation only."""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping


class CallActivity(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    UNKNOWN = "UNKNOWN"


_CALL_ACTIVITY_BY_BINDING = {
    "huawei_call_activity": {
        "calling": CallActivity.ACTIVE,
        "connected": CallActivity.ACTIVE,
        "no call": CallActivity.INACTIVE,
        "disconnected": CallActivity.INACTIVE,
        "нет звонка": CallActivity.INACTIVE,
        "вызов": CallActivity.ACTIVE,
        "отключен": CallActivity.INACTIVE,
    },
    "cloudlink_call_activity": {
        "calling": CallActivity.ACTIVE,
        "connected": CallActivity.ACTIVE,
        "no call": CallActivity.INACTIVE,
        "disconnected": CallActivity.INACTIVE,
    },
    "polycom_call_activity": {
        "active": CallActivity.ACTIVE,
        "no call": CallActivity.INACTIVE,
        "inactive": CallActivity.INACTIVE,
    },
}


def normalize_call_activity(binding_key: str | None, snapshot: Any) -> CallActivity:
    """Normalize already accepted exact-model evidence; unknown is deliberately safe."""
    if not isinstance(snapshot, Mapping):
        return CallActivity.UNKNOWN
    value = snapshot.get("call_status")
    if not isinstance(value, str):
        return CallActivity.UNKNOWN
    normalized = value.strip().casefold()
    return _CALL_ACTIVITY_BY_BINDING.get(binding_key, {}).get(normalized, CallActivity.UNKNOWN)
