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