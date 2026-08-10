"""Closed application-to-protocol identity mapping for CloudLink 310 devices."""
from __future__ import annotations

CLOUDLINK_BAR_310 = "CloudLink Bar 310"
CLOUDLINK_BOX_310 = "CloudLink Box 310"
CLOUDLINK_310_MODELS = frozenset({CLOUDLINK_BAR_310, CLOUDLINK_BOX_310})
_DISPLAY_IDENTITIES = {CLOUDLINK_BAR_310: "Huawei CloudLink Bar 310", CLOUDLINK_BOX_310: "Huawei CloudLink Box 310"}

def cloudlink_310_display_identity(model: str) -> str:
    try:
        return _DISPLAY_IDENTITIES[model]
    except KeyError as error:
        raise ValueError(f"Unsupported CloudLink 310 model: {model}") from error
