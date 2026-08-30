"""Typed call evidence shared by exact-model parsers and room presentation."""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping


class CallActivity(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    UNKNOWN = "UNKNOWN"


CALL_ACTIVITY_EVIDENCE_KEY = "_room_call_activity"


_CALL_ACTIVITY_BY_BINDING: dict[str, dict[str, CallActivity]] = {
    "huawei_call_activity": {
        "Calling": CallActivity.ACTIVE,
        "Connected": CallActivity.ACTIVE,
        "No Call": CallActivity.INACTIVE,
        "Disconnected": CallActivity.INACTIVE,
    },
    "cloudlink_call_activity": {
        "Calling": CallActivity.ACTIVE,
        "Connected": CallActivity.ACTIVE,
        "No Call": CallActivity.INACTIVE,
        "Disconnected": CallActivity.INACTIVE,
    },
    "polycom_call_activity": {
        "Active": CallActivity.ACTIVE,
        "Incoming": CallActivity.ACTIVE,
        "No Call": CallActivity.INACTIVE,
        "Ended": CallActivity.INACTIVE,
    },
}

_CALL_ACTIVITY_BY_TOKEN: dict[str, CallActivity] = {
    activity.value: activity for activity in CallActivity
}


def call_activity_binding_keys() -> frozenset[str]:
    """Return the composition-visible normalizer bindings from one registry."""
    return frozenset(_CALL_ACTIVITY_BY_BINDING)


def call_activity_from_model_evidence(binding_key: str | None, evidence: Any) -> CallActivity:
    """Classify machine-readable evidence in the exact model parser/adapter."""
    if not isinstance(evidence, str):
        return CallActivity.UNKNOWN
    return _CALL_ACTIVITY_BY_BINDING.get(binding_key or "", {}).get(
        evidence, CallActivity.UNKNOWN
    )


def publish_call_activity_evidence(
    snapshot: dict[str, Any], *, binding_key: str, evidence: Any
) -> None:
    """Attach a transport-safe, non-display evidence token to a snapshot."""
    snapshot[CALL_ACTIVITY_EVIDENCE_KEY] = call_activity_from_model_evidence(
        binding_key, evidence
    ).value


def normalize_call_activity(binding_key: str | None, snapshot: Any) -> CallActivity:
    """Read exact transport evidence only; unknown-by-default at the UI boundary."""
    if binding_key not in _CALL_ACTIVITY_BY_BINDING or not isinstance(snapshot, Mapping):
        return CallActivity.UNKNOWN
    evidence = snapshot.get(CALL_ACTIVITY_EVIDENCE_KEY)
    if not isinstance(evidence, str):
        return CallActivity.UNKNOWN
    return _CALL_ACTIVITY_BY_TOKEN.get(evidence, CallActivity.UNKNOWN)
