"""Local credential profile resolution at the application/core boundary.

Only the bootstrap layer should instantiate a provider.  Workers and handlers
receive the returned ``Credential`` explicitly and never read the JSON file.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from core.exceptions import (
    CredentialConfigurationError,
    CredentialFieldMissingError,
    CredentialFileMissingError,
    CredentialJsonError,
    CredentialProfileNotFoundError,
    CredentialSchemaError,
)


AUTH_USERNAME_PASSWORD = "username_password"
AUTH_PASSWORD = "password"
AUTH_NONE = "unauthenticated"
AUTH_MODES = {AUTH_USERNAME_PASSWORD, AUTH_PASSWORD, AUTH_NONE}


@dataclass(frozen=True)
class Credential:
    """Resolved device authentication contract; it is never a model registry."""

    auth_mode: str
    username: Optional[str] = None
    password: Optional[str] = None

    def __repr__(self) -> str:
        """Keep debugger, assertion, and log output free of credentials."""
        return f"Credential(auth_mode={self.auth_mode!r}, username=<redacted>, password=<redacted>)"

    def as_handler_kwargs(self) -> dict[str, str]:
        """Return only values that the selected authentication contract uses."""
        result: dict[str, str] = {}
        if self.auth_mode == AUTH_USERNAME_PASSWORD:
            result["username"] = self.username or ""
            result["password"] = self.password or ""
        elif self.auth_mode == AUTH_PASSWORD:
            result["password"] = self.password or ""
        return result


class CredentialProvider(ABC):
    """Replaceable source of resolved request-scoped credentials."""

    @abstractmethod
    def resolve(
        self,
        *,
        device_model: Optional[str] = None,
        profile_name: Optional[str] = None,
    ) -> Credential:
        """Resolve an explicitly requested or device-mapped profile."""

    def resolve_candidates(
        self,
        *,
        device_model: Optional[str] = None,
        profile_name: Optional[str] = None,
    ) -> Sequence[Credential]:
        """Resolve ordered candidates while keeping single-provider compatibility."""
        return (self.resolve(device_model=device_model, profile_name=profile_name),)


def application_root() -> Path:
    """Resolve the project root from this stable module path, never ``cwd``."""
    return Path(__file__).resolve().parent.parent


def default_credentials_path() -> Path:
    return application_root() / "credentials.local.json"


def normalize_credential(value: Credential | Mapping[str, Any]) -> Credential:
    """Validate direct caller/test injection with the same profile rules."""
    if isinstance(value, Credential):
        return _validated_credential(value.auth_mode, value.username, value.password)
    if not isinstance(value, Mapping):
        raise CredentialSchemaError("Credential configuration has an invalid direct credential object.")
    mode = value.get("auth_mode", AUTH_USERNAME_PASSWORD)
    return _validated_credential(mode, value.get("username"), value.get("password"))


def resolve_request_credentials(
    provider: CredentialProvider,
    *,
    device_model: Optional[str] = None,
    profile_name: Optional[str] = None,
    explicit_credentials: Credential | Mapping[str, Any] | None = None,
) -> Credential:
    """Apply source priority: direct input, explicit profile, model mapping."""
    return resolve_request_credential_candidates(
        provider,
        device_model=device_model,
        profile_name=profile_name,
        explicit_credentials=explicit_credentials,
    )[0]


def resolve_request_credential_candidates(
    provider: CredentialProvider,
    *,
    device_model: Optional[str] = None,
    profile_name: Optional[str] = None,
    explicit_credentials: Credential | Mapping[str, Any] | None = None,
) -> Sequence[Credential]:
    """Apply source priority and return all request-scoped candidates."""
    if explicit_credentials is not None:
        return (normalize_credential(explicit_credentials),)
    resolve_candidates = getattr(provider, "resolve_candidates", None)
    if callable(resolve_candidates):
        return resolve_candidates(device_model=device_model, profile_name=profile_name)
    return (provider.resolve(device_model=device_model, profile_name=profile_name),)


class JsonCredentialProvider(CredentialProvider):
    """Version-one plain-text JSON provider using only the standard ``json`` module."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else default_credentials_path()

    def resolve(
        self,
        *,
        device_model: Optional[str] = None,
        profile_name: Optional[str] = None,
    ) -> Credential:
        return self.resolve_candidates(
            device_model=device_model,
            profile_name=profile_name,
        )[0]

    def resolve_candidates(
        self,
        *,
        device_model: Optional[str] = None,
        profile_name: Optional[str] = None,
    ) -> Sequence[Credential]:
        document = self._load_document()
        profiles = document["profiles"]
        if profile_name is not None:
            profile_names = self._validate_profile_names((profile_name,))
        else:
            if not device_model:
                raise CredentialProfileNotFoundError(
                    "Credential configuration needs an explicit profile or a mapped device model."
                )
            mapping = document["device_profiles"].get(device_model)
            if mapping is None:
                raise CredentialProfileNotFoundError(
                    "Credential configuration has no profile mapped for the selected device."
                )
            profile_names = self._mapping_profile_names(mapping)

        resolved: list[Credential] = []
        for name in profile_names:
            profile = profiles.get(name)
            if not isinstance(profile, dict):
                raise CredentialProfileNotFoundError("Credential configuration profile was not found.")
            resolved.append(self._parse_profile(profile))
        return tuple(resolved)

    def _load_document(self) -> dict[str, Any]:
        try:
            with self.path.open("r", encoding="utf-8") as source:
                document = json.load(source)
        except FileNotFoundError as error:
            raise CredentialFileMissingError(
                "Local credential configuration is missing; create credentials.local.json from credentials.example.json."
            ) from error
        except json.JSONDecodeError as error:
            raise CredentialJsonError("Local credential configuration contains invalid JSON.") from error
        except OSError as error:
            raise CredentialConfigurationError("Local credential configuration could not be read.") from error

        if not isinstance(document, dict):
            raise CredentialSchemaError("Credential configuration root must be an object.")
        if document.get("version") != 1:
            raise CredentialSchemaError("Credential configuration has an unsupported version.")
        profiles = document.get("profiles")
        mappings = document.get("device_profiles", {})
        if not isinstance(profiles, dict) or not profiles:
            raise CredentialSchemaError("Credential configuration requires a profiles object.")
        if not isinstance(mappings, dict):
            raise CredentialSchemaError("Credential configuration device_profiles must be an object.")
        for model, mapping in mappings.items():
            if not isinstance(model, str) or not model.strip():
                raise CredentialSchemaError("Credential configuration has an invalid device profile mapping.")
            self._mapping_profile_names(mapping)
        return {"profiles": profiles, "device_profiles": mappings}

    @classmethod
    def _mapping_profile_names(cls, mapping: Any) -> tuple[str, ...]:
        if isinstance(mapping, str):
            return cls._validate_profile_names((mapping,))
        if isinstance(mapping, list):
            return cls._validate_profile_names(mapping)
        raise CredentialSchemaError("Credential configuration has an invalid device profile mapping.")

    @staticmethod
    def _validate_profile_names(names: Sequence[Any]) -> tuple[str, ...]:
        if not names:
            raise CredentialSchemaError("Credential configuration has an invalid device profile mapping.")
        if any(not isinstance(name, str) or not name.strip() for name in names):
            raise CredentialSchemaError("Credential configuration has an invalid device profile mapping.")
        return tuple(names)

    @staticmethod
    def _parse_profile(profile: Mapping[str, Any]) -> Credential:
        mode = profile.get("auth_mode")
        if mode not in AUTH_MODES:
            raise CredentialSchemaError("Credential configuration has an unsupported authentication mode.")
        return _validated_credential(mode, profile.get("username"), profile.get("password"))


def _validated_credential(mode: Any, username: Any, password: Any) -> Credential:
    if mode not in AUTH_MODES:
        raise CredentialSchemaError("Credential configuration has an unsupported authentication mode.")
    if mode == AUTH_USERNAME_PASSWORD:
        if not isinstance(username, str) or not username:
            raise CredentialFieldMissingError("Credential configuration is missing a required username field.")
        if not isinstance(password, str) or not password:
            raise CredentialFieldMissingError("Credential configuration is missing a required password field.")
        return Credential(auth_mode=mode, username=username, password=password)
    if mode == AUTH_PASSWORD:
        if not isinstance(password, str) or not password:
            raise CredentialFieldMissingError("Credential configuration is missing a required password field.")
        return Credential(auth_mode=mode, password=password)
    return Credential(auth_mode=mode)
