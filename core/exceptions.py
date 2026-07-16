"""
Исключения для модуля диагностики оборудования ВКС
"""

from __future__ import annotations

from enum import Enum


class DeviceError(Exception):
    """Базовое исключение для ошибок устройств"""
    pass


class ConnectionError(DeviceError):
    """Ошибка подключения к устройству"""
    pass


class AuthenticationError(DeviceError):
    """Ошибка аутентификации"""
    pass


class CommandError(DeviceError):
    """Ошибка выполнения команды на устройстве"""
    pass


class TimeoutError(DeviceError):
    """Ошибка таймаута"""
    pass


class ParseError(DeviceError):
    """Ошибка парсинга данных"""
    pass


class DeviceNotFoundError(DeviceError):
    """Устройство не найдено"""
    pass


class ProtocolError(DeviceError):
    """Ошибка протокола"""
    pass


class SessionInvalidError(DeviceError):
    """An established codec session is no longer accepted by the device."""


class CommandOutcomeUnknownError(DeviceError):
    """A state-changing command may have reached the device without a reply."""


class CodecFailureCategory(str, Enum):
    """Stable retry/recovery authority for codec refresh and interactive paths."""

    AUTHENTICATION = "authentication_error"
    SESSION_INVALID = "session_invalid"
    TRANSPORT = "connection_error"
    PROTOCOL = "protocol_error"
    COMMAND = "command_error"
    UNKNOWN_COMMAND_OUTCOME = "unknown_command_outcome"


def classify_codec_failure(error: BaseException) -> CodecFailureCategory:
    """Classify a caught typed failure without inspecting human-readable text."""

    if isinstance(error, AuthenticationError):
        return CodecFailureCategory.AUTHENTICATION
    if isinstance(error, SessionInvalidError):
        return CodecFailureCategory.SESSION_INVALID
    if isinstance(error, CommandOutcomeUnknownError):
        return CodecFailureCategory.UNKNOWN_COMMAND_OUTCOME
    if isinstance(error, CommandError):
        return CodecFailureCategory.COMMAND
    if isinstance(error, (ProtocolError, ParseError)):
        return CodecFailureCategory.PROTOCOL
    return CodecFailureCategory.TRANSPORT


class CredentialConfigurationError(DeviceError):
    """Safe error raised before network I/O when local credentials are invalid."""
    pass


class CredentialFileMissingError(CredentialConfigurationError):
    """The ignored local credential file has not been created."""
    pass


class CredentialJsonError(CredentialConfigurationError):
    """The local credential file is not valid JSON."""
    pass


class CredentialSchemaError(CredentialConfigurationError):
    """The local credential file does not match the supported schema."""
    pass


class CredentialProfileNotFoundError(CredentialConfigurationError):
    """The requested or mapped credential profile is unavailable."""
    pass


class CredentialFieldMissingError(CredentialConfigurationError):
    """A selected authentication mode is missing a required field."""
    pass
