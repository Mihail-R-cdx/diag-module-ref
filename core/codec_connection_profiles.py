"""Pure model/runtime codec transport ordering shared by all codec paths."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from utils.te20_stack import inspect_te20_https_stack


TE20 = "Huawei TE20"
TE40 = "Huawei TE40"
BAR310 = "CloudLink Bar 310"
POLYCOM = "Polycom RPG 310"


def supported_codec_profiles(
    model: str,
    *,
    te20_https_ready: bool | None = None,
) -> tuple[dict[str, Any], ...]:
    """Return the currently supported default profiles for one codec model."""

    if model == TE20:
        if te20_https_ready is None:
            te20_https_ready = bool(inspect_te20_https_stack().get("ready"))
        profiles = [{"port": 80, "use_ssl": False, "label": "HTTP:80"}]
        if te20_https_ready:
            profiles.append({"port": 443, "use_ssl": True, "label": "HTTPS:443"})
        return tuple(profiles)
    if model == TE40:
        return (
            {"port": 443, "use_ssl": True, "label": "HTTPS:443"},
            {"port": 80, "use_ssl": False, "label": "HTTP:80"},
        )
    if model == BAR310:
        return ({"port": 443, "use_ssl": True, "label": "HTTPS:443"},)
    if model == POLYCOM:
        return ({"port": 443, "use_ssl": True, "label": "HTTPS:443"},)
    return ()


def order_codec_profiles(
    model: str,
    saved_profile: Mapping[str, Any] | None = None,
    *,
    supported_profiles: Sequence[Mapping[str, Any]] | None = None,
    te20_https_ready: bool | None = None,
) -> tuple[dict[str, Any], ...]:
    """Put a supported saved profile first and deduplicate by port/SSL mode."""

    defaults = tuple(
        dict(profile)
        for profile in (
            supported_profiles
            if supported_profiles is not None
            else supported_codec_profiles(model, te20_https_ready=te20_https_ready)
        )
    )
    supported_keys = {_profile_key(profile) for profile in defaults}
    ordered: list[dict[str, Any]] = []
    if isinstance(saved_profile, Mapping) and _profile_key(saved_profile) in supported_keys:
        saved_key = _profile_key(saved_profile)
        canonical = next(profile for profile in defaults if _profile_key(profile) == saved_key)
        preferred = dict(canonical)
        if saved_profile.get("label"):
            preferred["label"] = str(saved_profile["label"])
        ordered.append(preferred)
    ordered.extend(defaults)

    result: list[dict[str, Any]] = []
    seen: set[tuple[Any, bool]] = set()
    for profile in ordered:
        key = _profile_key(profile)
        if key in seen:
            continue
        seen.add(key)
        result.append(profile)
    return tuple(result)


def _profile_key(profile: Mapping[str, Any]) -> tuple[Any, bool]:
    return profile.get("port"), bool(profile.get("use_ssl"))
