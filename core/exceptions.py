"""
Исключения для модуля диагностики оборудования ВКС
"""


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
