"""Reusable redaction helpers for public diagnostic boundaries."""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Iterable

SENSITIVE_FIELD_MARKERS = (
    "password", "credential", "token", "session", "authorization",
    "auth_header", "secret", "username", "usr", "pwd", "cookie",
    "csrf", "access_key", "api_key",
)
REDACTION_MARKER = "<redacted>"
_SENSITIVE_TEXT_VALUE = re.compile(
    r"""(?ix)
    (?P<label>\b(?:authorization|proxy-authorization|cookie|set-cookie|x-csrf-token|
    csrf(?:token)?|session(?:id)?|token|access[_-]?key|api[_-]?key|username|password|passwd|pwd)\b\s*[:=]\s*)
    (?P<value>\"[^\"]*\"|'[^']*'|[^\s,;\}\]]+)
    """
)
_AUTHORIZATION_SCHEME_VALUE = re.compile(r"(?i)\b(?:bearer|basic)\s+[^\s,;\}\]]+")


def redact_text(value: Any, secrets: Iterable[Any] = ()) -> str:
    text = str(value)
    for secret in secrets:
        if secret is not None and str(secret):
            text = text.replace(str(secret), REDACTION_MARKER)
    text = _SENSITIVE_TEXT_VALUE.sub(
        lambda match: f"{match.group('label')}{REDACTION_MARKER}", text
    )
    return _AUTHORIZATION_SCHEME_VALUE.sub(REDACTION_MARKER, text)


def redact_exception(value: BaseException | str, secrets: Iterable[Any] = ()) -> str:
    """Prepare exception text and tracebacks for public error boundaries."""
    return redact_text(value, secrets)


def redact_diagnostic(value: Any, secrets: Iterable[Any] = ()) -> Any:
    """Redact structured diagnostic text as well as Python containers."""
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return redact_text(value, secrets)
        return json.dumps(redact_data(parsed, secrets), ensure_ascii=False)
    return redact_data(value, secrets)


def redacted_callback(callback: Callable[[str], Any], secrets: Iterable[Any] = ()) -> Callable[[Any], Any]:
    """Wrap a public logging/debug callback without retaining a raw secret."""
    values = tuple(secrets)

    def emit(value: Any) -> Any:
        return callback(redact_text(value, values))

    return emit


def redact_data(value: Any, secrets: Iterable[Any] = ()) -> Any:
    """Remove sensitive fields recursively without mutating application data."""
    if isinstance(value, dict):
        return {
            key: REDACTION_MARKER if _is_sensitive_key(key) else redact_data(item, secrets)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_data(item, secrets) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_data(item, secrets) for item in value)
    if isinstance(value, str):
        # Responses and exception details are often serialized JSON embedded
        # inside a larger diagnostic structure.  Redact their keys as data,
        # not merely their currently-known values.
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return redact_text(value, secrets)
        if isinstance(parsed, (dict, list, tuple)):
            return json.dumps(redact_data(parsed, secrets), ensure_ascii=False)
        return redact_text(value, secrets)
    return value


def _is_sensitive_key(key: Any) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return any(marker in normalized for marker in SENSITIVE_FIELD_MARKERS)
