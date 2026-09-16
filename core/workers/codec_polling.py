"""Polling workers for codec status diagnostics."""

import builtins
import traceback
from collections.abc import Mapping

from PyQt5.QtCore import QRunnable, pyqtSlot

from core.codec_connection_profiles import order_codec_profiles
from core.cloudlink_310 import cloudlink_310_display_identity
from core.exceptions import AuthenticationError, ConnectionError, ParseError, ProtocolError
from core.parser import HuaweiBar310DataParser, HuaweiTE40DataParser
from core.redaction import (
    redact_data,
    redact_diagnostic,
    redact_exception,
    redacted_callback,
)
from core.workers.common import WorkerSignals, _emit_error, _worker_secrets
from handlers.huawei.bar310 import CloudLinkBar310Handler
from handlers.huawei.te40 import HuaweiTE40Handler


class HuaweiTE40Worker(QRunnable):
    """Специализированный Worker для Huawei TE40"""

    def __init__(self, ip_address: str, port: int = 443,
                 username: str = None, password: str = None,
                 preferred_profile: dict = None, *, assigned_model: str = "Huawei TE40", is_current=None):
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.signals = WorkerSignals()
        self.creds_list = []
        self.current_idx = 0
        if assigned_model not in {"Huawei TE40", "Huawei TE50"}:
            raise ValueError(f"Unsupported Huawei TE40-backed model: {assigned_model}")
        self.device_name = assigned_model
        self.preferred_profile = dict(preferred_profile) if preferred_profile else None
        self.is_current = is_current or (lambda: True)

    @pyqtSlot()
    def run(self):
        handler = None
        succeeded = False
        try:
            if not self.is_current():
                return
            if not self.username or not self.password:
                raise AuthenticationError(f"Credentials are required for {self.device_name} before connecting.")
            self.signals.status.emit("Начинаю подключение...")
            self.signals.progress.emit(10)

            print(f"=== HuaweiTE40Worker.run() для {self.ip_address} ===")
            print("[WORKER] 🔐 Credentials загружены (значения скрыты)")
            print(f"[WORKER] --- Начало попытки аутентификации ---")

            self.signals.status.emit("Подключаюсь к устройству...")
            self.signals.progress.emit(30)
            profiles = order_codec_profiles(self.device_name, self.preferred_profile)
            last_error = None
            for ordinal, profile in enumerate(profiles, start=1):
                if not self.is_current():
                    return
                handler = HuaweiTE40Handler(
                    ip_address=self.ip_address,
                    port=profile["port"],
                    username=self.username,
                    password=self.password,
                    use_ssl=profile["use_ssl"],
                )
                handler.command_logger = redacted_callback(
                    self.signals.terminal_log.emit, _worker_secrets(self)
                )
                self.signals.terminal_log.emit(
                    f"[connect] attempt {ordinal}/{len(profiles)} via {profile['label']}"
                )
                try:
                    if not self.is_current():
                        return
                    if handler.connect():
                        self.signals.terminal_log.emit(
                            f"[connect] success via {profile['label']}"
                        )
                        break
                    raise ConnectionError(
                        f"{profile['label']} did not return a valid TE40 session"
                    )
                except AuthenticationError:
                    try:
                        handler.disconnect()
                    except Exception:
                        pass
                    handler = None
                    raise
                except Exception as error:
                    last_error = error
                    try:
                        handler.disconnect()
                    except Exception:
                        pass
                    handler = None
                    self.signals.terminal_log.emit(
                        redact_exception(
                            f"[connect] {profile['label']} failed: "
                            f"{type(error).__name__}: {error}",
                            _worker_secrets(self),
                        )
                    )
            if handler is None:
                raise ConnectionError(str(last_error or "TE40 connection failed"))

            self.signals.connected.emit()
            self.signals.status.emit("Получаю данные...")
            self.signals.progress.emit(50)

            print("Вызываю handler.get_status()...")
            if not self.is_current():
                return
            raw_data = redact_data(handler.get_status(), _worker_secrets(self))
            print(f"get_status() вернул: {raw_data}")

            self.signals.status.emit("Обрабатываю данные...")
            self.signals.progress.emit(70)

            print("Парсинг данных...")
            parsed_data = HuaweiTE40DataParser.parse_raw_data(raw_data)
            parsed_data['Модель'] = self.device_name
            print(f"Парсинг завершен: {parsed_data}")

            parsed_data['ip_address'] = self.ip_address
            parsed_data['connection_profile'] = {
                'port': handler.port,
                'use_ssl': bool(getattr(handler, 'use_ssl', True)),
                'label': f"{'HTTPS' if getattr(handler, 'use_ssl', True) else 'HTTP'}:{handler.port}",
            }

            self.signals.progress.emit(90)
            print("Отправка результата...")
            self.signals.result.emit(redact_data(parsed_data, _worker_secrets(self)))
            succeeded = True

        except AuthenticationError as e:
            print(f"!!! Ошибка аутентификации в HuaweiTE40Worker: {redact_exception(e, _worker_secrets(self))}")
            # Пробрасываем как ошибку с ключевым словом authentication
            _emit_error(self, None, e)
        except Exception as e:
            print(f"!!! Ошибка в HuaweiTE40Worker: {type(e).__name__}: {redact_exception(e, _worker_secrets(self))}")
            print(redact_exception(traceback.format_exc(), _worker_secrets(self)))
            _emit_error(self, None, e)
        finally:
            if handler is not None:
                try:
                    print("Отключение...")
                    handler.disconnect()
                except Exception:
                    pass
            if succeeded:
                self.signals.disconnected.emit()
            self.signals.finished.emit()


    def set_sip_server(self, sip_address="link.ru"):
        """
        Установка SIP сервера в отдельном потоке
        """
        print(f"\n=== HuaweiTE40Worker.set_sip_server called ===")
        print(f"IP: {self.ip_address}")
        print(f"Port: {self.port}")
        print("Credentials: <redacted>")
        print(f"SIP Address: {sip_address}")

        try:
            self.signals.status.emit(f"Установка SIP сервера: {sip_address}...")

            handler = HuaweiTE40Handler(
                ip_address=self.ip_address,
                port=self.port,
                username=self.username,
                password=self.password
            )

            print("Handler created, connecting...")
            # connect() already raises AuthenticationError on failure
            handler.connect()

            print("Connected successfully")
            print("Session ID: <redacted>")
            print("CSRF Token: <redacted>")

            print("Calling set_sip_server...")
            success = handler.set_sip_server(sip_address)
            print(f"set_sip_server returned: {success}")

            if success:
                print("Verifying SIP server...")
                current_sip = handler.verify_sip_server()
                print(f"Current SIP server: {current_sip}")
                handler.disconnect()

                if current_sip == sip_address:
                    print("Verification passed")
                    self.signals.result.emit({
                        'action': 'set_sip_server',
                        'success': True,
                        'message': f'SIP сервер успешно установлен: {sip_address}'
                    })
                else:
                    print(f"Verification failed: expected {sip_address}, got {current_sip}")
                    self.signals.result.emit({
                        'action': 'set_sip_server',
                        'success': False,
                        'message': f'Ошибка: SIP сервер не изменился (текущий: {current_sip})'
                    })
            else:
                print("set_sip_server returned False")
                handler.disconnect()
                self.signals.result.emit({
                    'action': 'set_sip_server',
                    'success': False,
                    'message': 'Ошибка установки SIP сервера'
                })

        except Exception as e:
            print(f"Exception in set_sip_server: {redact_exception(e, _worker_secrets(self))}")
            print(redact_exception(traceback.format_exc(), _worker_secrets(self)))
            _emit_error(self, 'set_sip_server_error', e)



class HuaweiBar310Worker(QRunnable):
    """Worker for one CloudLink Bar 310 credential attempt."""

    def __init__(self, ip_address: str, port: int = 443,
                 username: str = None, password: str = None,
                 creds_list: list = None, assigned_model: str = "CloudLink Bar 310", *, is_current=None):
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.signals = WorkerSignals()

        self.handler = None
        self.creds_list = creds_list if creds_list is not None else []
        self.current_idx = 0
        self.assigned_model = assigned_model
        self.device_name = assigned_model
        self.expected_identity = cloudlink_310_display_identity(assigned_model)
        self.is_current = is_current or (lambda: True)

    @staticmethod
    def _validate_raw_status(raw_data, expected_identity="Huawei CloudLink Bar 310"):
        if not isinstance(raw_data, Mapping):
            raise ProtocolError("Bar 310 status payload is not an object")
        if raw_data.get("model") != expected_identity:
            raise ProtocolError("Bar 310 status payload has no valid model")
        version = raw_data.get("version")
        if (
            not isinstance(version, str)
            or not version.strip()
            or version.casefold() == "unknown"
        ):
            raise ProtocolError("Bar 310 status payload has no usable version")

    @pyqtSlot()
    def run(self):
        def print(*args, **kwargs):
            secrets = _worker_secrets(self)
            return builtins.print(*(redact_diagnostic(value, secrets) for value in args), **kwargs)

        handler = None
        try:
            if not self.is_current():
                return
            if not self.username or not self.password:
                raise AuthenticationError(
                    'Credentials are required for CloudLink Bar 310 before connecting.'
                )

            print(f"=== HuaweiBar310Worker.run() для {self.ip_address} ===")
            self.signals.status.emit("Подключение к устройству...")
            self.signals.progress.emit(10)

            if not self.is_current():
                return
            handler = CloudLinkBar310Handler(
                ip_address=self.ip_address,
                port=self.port,
                username=self.username,
                password=self.password,
                expected_identity=self.expected_identity,
            )
            self.handler = handler
            handler.command_logger = redacted_callback(
                self.signals.terminal_log.emit, _worker_secrets(self)
            )

            self.signals.progress.emit(30)
            if not self.is_current():
                return
            handler.connect()

            self.signals.connected.emit()
            self.signals.status.emit("Получаю данные...")
            self.signals.progress.emit(50)

            if not self.is_current():
                return
            raw_data = handler.get_status()
            self._validate_raw_status(raw_data, self.expected_identity)

            self.signals.status.emit("Обрабатываю данные...")
            self.signals.progress.emit(70)

            parsed_data = HuaweiBar310DataParser.parse_raw_data(
                raw_data, self.expected_identity
            )
            if (
                not isinstance(parsed_data, Mapping)
                or parsed_data.get("Модель") != self.expected_identity
                or not isinstance(parsed_data.get("Версия ПО"), str)
                or not parsed_data["Версия ПО"].strip()
                or parsed_data["Версия ПО"].casefold() == "unknown"
            ):
                raise ParseError("Bar 310 parser returned unusable status")

            parsed_data['ip_address'] = self.ip_address
            parsed_data['connection_profile'] = {
                'port': handler.port,
                'use_ssl': bool(getattr(handler, 'use_ssl', True)),
                'label': f"{'HTTPS' if getattr(handler, 'use_ssl', True) else 'HTTP'}:{handler.port}",
            }

            self.signals.progress.emit(90)
            self.signals.result.emit(redact_data(parsed_data, _worker_secrets(self)))

        except AuthenticationError as e:
            print(f"[BAR310] Ошибка аутентификации: {redact_exception(e, _worker_secrets(self))}")
            _emit_error(self, 'authentication_error', e)
        except Exception as e:
            print(f"[BAR310] Ошибка подключения: {type(e).__name__}: {redact_exception(e, _worker_secrets(self))}")
            _emit_error(self, None, e)
        finally:
            if handler:
                try:
                    handler.disconnect()
                except Exception:
                    pass
                self.signals.disconnected.emit()
            self.handler = None
            self.signals.finished.emit()



class PolycomRPG310Worker(QRunnable):
    """Специализированный Worker для Polycom RealPresence Group 310"""

    def __init__(self, ip_address: str, port: int = 443,
                 username: str = None, password: str = None, *, is_current=None):
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.signals = WorkerSignals()
        self.creds_list = []
        self.current_idx = 0
        self.device_name = "Polycom RPG 310"
        self.is_current = is_current or (lambda: True)

    @pyqtSlot()
    def run(self):
        handler = None
        try:
            if not self.is_current():
                return
            if not self.username or not self.password:
                raise AuthenticationError("Credentials are required for Polycom RPG 310 before connecting.")
            self.signals.status.emit("Начинаю подключение к Polycom RPG 310...")
            self.signals.progress.emit(10)

            print(f"=== PolycomRPG310Worker.run() для {self.ip_address} ===")
            print("[WORKER] 🔐 Credentials загружены (значения скрыты)")
            print(f"[WORKER] --- Начало попытки аутентификации ---")

            # Импортируем обработчик
            from handlers.polycom.rpg310 import PolycomRPG310Handler

            if not self.is_current():
                return
            handler = PolycomRPG310Handler(
                ip_address=self.ip_address,
                port=self.port,
                username=self.username,
                password=self.password
            )
            handler.command_logger = redacted_callback(self.signals.terminal_log.emit, _worker_secrets(self))

            self.signals.status.emit("Подключаюсь к устройству...")
            self.signals.progress.emit(30)

            # connect() already raises AuthenticationError on failure
            if not self.is_current():
                return
            handler.connect()

            self.signals.connected.emit()
            from core.parser import PolycomDataParser

            self.signals.status.emit("Получаю данные по HTTPS...")
            self.signals.progress.emit(45)

            print("Вызываю handler.get_https_status()...")
            if not self.is_current():
                return
            raw_data = handler.get_https_status()
            print(
                "get_https_status() вернул поля:",
                sorted(str(key) for key in raw_data),
            )

            self.signals.status.emit("Отображаю данные HTTPS...")
            self.signals.progress.emit(60)

            parsed_data = PolycomDataParser.parse_raw_data(raw_data)
            if 'Модель' not in parsed_data:
                parsed_data['Модель'] = 'Polycom RealPresence Group 310'
            parsed_data['ip_address'] = self.ip_address
            parsed_data['connection_profile'] = {
                'port': handler.port,
                'use_ssl': True,
                'label': f"HTTPS:{handler.port}",
            }
            parsed_data['_partial_update'] = True
            self.signals.result.emit(redact_data(parsed_data, _worker_secrets(self)))

            self.signals.status.emit("Подключение по SSH для дополнительных параметров...")
            self.signals.progress.emit(68)
            if not self.is_current():
                return
            handler._populate_cli_status(
                raw_data,
                progress_callback=self.signals.progress.emit,
                status_callback=self.signals.status.emit,
            )

            self.signals.status.emit("Обрабатываю данные SSH...")
            self.signals.progress.emit(94)

            print("Парсинг данных...")
            parsed_data = PolycomDataParser.parse_raw_data(raw_data)
            print(
                "Парсинг завершен. Поля GUI:",
                sorted(str(key) for key in parsed_data),
            )

            # Проверяем, есть ли громкость в parsed_data
            if 'Громкость' in parsed_data:
                print("Громкость присутствует в parsed_data")
            else:
                print("ВНИМАНИЕ: Громкость отсутствует в parsed_data!")

            # Добавляем модель, если её нет
            if 'Модель' not in parsed_data:
                parsed_data['Модель'] = 'Polycom RealPresence Group 310'

            parsed_data['ip_address'] = self.ip_address
            parsed_data['connection_profile'] = {
                'port': handler.port,
                'use_ssl': True,
                'label': f"HTTPS:{handler.port}",
            }

            self.signals.progress.emit(100)
            print("Отправка результата в GUI...")
            self.signals.result.emit(redact_data(parsed_data, _worker_secrets(self)))

        except AuthenticationError as e:
            print(f"!!! Ошибка аутентификации в PolycomRPG310Worker: {redact_exception(e, _worker_secrets(self))}")
            _emit_error(self, None, e)
        except Exception as e:
            print(f"!!! Ошибка в PolycomRPG310Worker: {type(e).__name__}: {redact_exception(e, _worker_secrets(self))}")
            print(redact_exception(traceback.format_exc(), _worker_secrets(self)))
            _emit_error(self, None, e)
        finally:
            if handler is not None:
                try:
                    print("Отключение...")
                    handler.disconnect()
                    self.signals.disconnected.emit()
                except Exception as error:
                    print(
                        "Ошибка cleanup Polycom worker: "
                        f"{type(error).__name__}"
                    )
            self.signals.finished.emit()
