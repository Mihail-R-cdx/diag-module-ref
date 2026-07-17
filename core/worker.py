from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, QRunnable
from typing import Dict, Optional
import traceback
from core.parser import HuaweiTE40DataParser
from core.parser import HuaweiBar310DataParser
from core.parser import ExtronIN1804DataParser
from core.parser import BiampTesiraForteCIDataParser
from handlers.huawei.te40 import HuaweiTE40Handler
from handlers.huawei.bar310 import CloudLinkBar310Handler
from core.te20_worker import HuaweiTE20Worker
from handlers.extron.in1804 import ExtronIN1804Handler
from core.codec_connection_profiles import order_codec_profiles
from .exceptions import (
    AuthenticationError,
    CommandError,
    CommandOutcomeUnknownError,
    ConnectionError,
    CredentialRequired,
    classify_codec_failure,
)
from core.pdu import (
    REFRESH,
    PDUOperationDescriptor,
    execute_pdu_command,
    execute_pdu_refresh,
    normalize_pdu_credentials,
)
import traceback
import builtins
from core.redaction import redact_data, redact_diagnostic, redact_exception, redacted_callback


def _worker_secrets(worker):
    values = [getattr(worker, "username", None), getattr(worker, "password", None)]
    for credential in getattr(worker, "creds_list", ()):
        if isinstance(credential, dict):
            values.extend(credential.values())
    return tuple(values)


def _safe_error(error, secrets):
    return (
        redact_exception(error, secrets),
        redact_exception(traceback.format_exc(), secrets),
    )


def _emit_error(worker, category, error, trace=True):
    if category is None:
        category = classify_codec_failure(error).value
    message, details = _safe_error(error, _worker_secrets(worker))
    worker.signals.error.emit((category, message, details if trace else ""))


class WorkerSignals(QObject):
    """Сигналы для общения между потоками"""
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(dict)
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    terminal_log = pyqtSignal(str)
    connected = pyqtSignal()
    disconnected = pyqtSignal()


class PolycomCallLogWorker(QRunnable):
    """Load Polycom call records without blocking the Qt event loop."""

    def __init__(self, handler_class, handler_kwargs):
        super().__init__()
        self.handler_class = handler_class
        self.handler_kwargs = dict(handler_kwargs)
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        handler = None
        try:
            handler = self.handler_class(**self.handler_kwargs)
            handler.connect()
            records = handler.get_call_records()
            self.signals.result.emit({"records": list(records or [])})
        except Exception as error:
            secrets = (
                self.handler_kwargs.get("username"),
                self.handler_kwargs.get("password"),
            )
            message = "Polycom call log request failed: {}".format(
                redact_exception(error, secrets)
            )
            self.signals.error.emit(
                (
                    "PolycomCallLogError",
                    message,
                    "",
                )
            )
        finally:
            if handler is not None:
                try:
                    handler.disconnect()
                except Exception:
                    pass
            self.signals.finished.emit()


class HuaweiTE40Worker(QRunnable):
    """Специализированный Worker для Huawei TE40"""
    
    def __init__(self, ip_address: str, port: int = 443,
                 username: str = None, password: str = None,
                 preferred_profile: dict = None):
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.signals = WorkerSignals()
        self.creds_list = []
        self.current_idx = 0
        self.device_name = "Huawei TE40"
        self.preferred_profile = dict(preferred_profile) if preferred_profile else None

    @pyqtSlot()
    def run(self):
        handler = None
        succeeded = False
        try:
            if not self.username or not self.password:
                raise AuthenticationError("Credentials are required for Huawei TE40 before connecting.")
            self.signals.status.emit("Начинаю подключение...")
            self.signals.progress.emit(10)
            
            print(f"=== HuaweiTE40Worker.run() для {self.ip_address} ===")
            print("[WORKER] 🔐 Credentials загружены (значения скрыты)")
            print(f"[WORKER] --- Начало попытки аутентификации ---")
            
            self.signals.status.emit("Подключаюсь к устройству...")
            self.signals.progress.emit(30)
            profiles = order_codec_profiles(
                "Huawei TE40", self.preferred_profile
            )
            last_error = None
            for ordinal, profile in enumerate(profiles, start=1):
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
            raw_data = redact_data(handler.get_status(), _worker_secrets(self))
            print(f"get_status() вернул: {raw_data}")
            
            self.signals.status.emit("Обрабатываю данные...")
            self.signals.progress.emit(70)
            
            print("Парсинг данных...")
            parsed_data = HuaweiTE40DataParser.parse_raw_data(raw_data)
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


class CodecSipFixWorker(QRunnable):
    """Фоновый worker для установки SIP-сервера на поддерживаемых кодеках."""

    def __init__(self, device_name: str, ip_address: str, port: int,
                 username: str, password: str, sip_server: str):
        super().__init__()
        self.device_name = device_name
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.sip_server = sip_server
        self.signals = WorkerSignals()

    def _create_handler(self):
        if self.device_name == "Huawei TE40":
            return HuaweiTE40Handler(
                ip_address=self.ip_address,
                port=self.port,
                username=self.username,
                password=self.password,
            )
        if self.device_name == "CloudLink Bar 310":
            return CloudLinkBar310Handler(
                ip_address=self.ip_address,
                port=self.port,
                username=self.username,
                password=self.password,
            )
        if self.device_name == "Polycom RPG 310":
            from handlers.polycom.rpg310 import PolycomRPG310Handler
            return PolycomRPG310Handler(
                ip_address=self.ip_address,
                port=self.port,
                username=self.username,
                password=self.password,
            )
        raise ValueError(f"Устройство не поддерживает SIP fix: {self.device_name}")

    @pyqtSlot()
    def run(self):
        handler = None
        try:
            if not self.username or not self.password:
                raise AuthenticationError("Credentials are required before setting a SIP server.")
            self.signals.status.emit(
                f"Подключение к {self.device_name} для установки SIP сервера..."
            )
            self.signals.progress.emit(10)

            handler = self._create_handler()
            handler.command_logger = redacted_callback(self.signals.terminal_log.emit, _worker_secrets(self))
            handler.connect()

            self.signals.status.emit(f"Устанавливаю SIP сервер: {self.sip_server}...")
            self.signals.progress.emit(60)
            success = handler.set_sip_server(self.sip_server)
            current_sip = handler.verify_sip_server() if hasattr(handler, 'verify_sip_server') else None

            if success and current_sip == self.sip_server:
                self.signals.result.emit({
                    'action': 'set_sip_server',
                    'success': True,
                    'message': f'SIP сервер успешно установлен: {self.sip_server}',
                    'device_name': self.device_name,
                    'ip_address': self.ip_address,
                })
            elif success:
                self.signals.result.emit({
                    'action': 'set_sip_server',
                    'success': False,
                    'message': (
                        'Команда отправлена, но проверка не подтвердила новое значение '
                        f'(текущий SIP: {current_sip})'
                    ),
                    'device_name': self.device_name,
                    'ip_address': self.ip_address,
                })
            else:
                self.signals.result.emit({
                    'action': 'set_sip_server',
                    'success': False,
                    'message': 'Не удалось установить SIP сервер',
                    'device_name': self.device_name,
                    'ip_address': self.ip_address,
                })

            self.signals.progress.emit(100)
        except AuthenticationError as e:
            _emit_error(self, None, e)
        except Exception as e:
            _emit_error(self, 'set_sip_server_error', e)
        finally:
            if handler:
                try:
                    handler.disconnect()
                except Exception:
                    pass
            self.signals.finished.emit()


class HuaweiBar310Worker(QRunnable):
    """Worker for one CloudLink Bar 310 credential attempt."""
    
    def __init__(self, ip_address: str, port: int = 443,
                 username: str = None, password: str = None,
                 creds_list: list = None):
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.signals = WorkerSignals()
        
        self.handler = None
        self.creds_list = creds_list if creds_list is not None else []
        self.current_idx = 0
        self.device_name = "Huawei CloudLink Bar 310"
    
    @pyqtSlot()
    def run(self):
        def print(*args, **kwargs):
            secrets = _worker_secrets(self)
            return builtins.print(*(redact_diagnostic(value, secrets) for value in args), **kwargs)

        handler = None
        try:
            if not self.username or not self.password:
                raise AuthenticationError(
                    'Credentials are required for CloudLink Bar 310 before connecting.'
                )

            print(f"=== HuaweiBar310Worker.run() для {self.ip_address} ===")
            self.signals.status.emit("Подключение к устройству...")
            self.signals.progress.emit(10)

            handler = CloudLinkBar310Handler(
                ip_address=self.ip_address,
                port=self.port,
                username=self.username,
                password=self.password
            )
            self.handler = handler
            handler.command_logger = redacted_callback(
                self.signals.terminal_log.emit, _worker_secrets(self)
            )

            self.signals.progress.emit(30)
            handler.connect()

            self.signals.connected.emit()
            self.signals.status.emit("Получаю данные...")
            self.signals.progress.emit(50)

            print("Вызываю handler.get_status()...")
            raw_data = handler.get_status()
            print(f"get_status() вернул: {raw_data}")

            self.signals.status.emit("Обрабатываю данные...")
            self.signals.progress.emit(70)

            print("Парсинг данных...")
            parsed_data = HuaweiBar310DataParser.parse_raw_data(raw_data)
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

            print("Отключение...")
            try:
                handler.disconnect()
            except Exception:
                pass
            handler = None
            self.handler = None
            self.signals.disconnected.emit()

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
            self.handler = None
            self.signals.finished.emit()


class PolycomRPG310Worker(QRunnable):
    """Специализированный Worker для Polycom RealPresence Group 310"""
    
    def __init__(self, ip_address: str, port: int = 443,
                 username: str = None, password: str = None):
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.signals = WorkerSignals()
        self.creds_list = []
        self.current_idx = 0
        self.device_name = "Polycom RPG 310"
    
    @pyqtSlot()
    def run(self):
        handler = None
        try:
            if not self.username or not self.password:
                raise AuthenticationError("Credentials are required for Polycom RPG 310 before connecting.")
            self.signals.status.emit("Начинаю подключение к Polycom RPG 310...")
            self.signals.progress.emit(10)
            
            print(f"=== PolycomRPG310Worker.run() для {self.ip_address} ===")
            print("[WORKER] 🔐 Credentials загружены (значения скрыты)")
            print(f"[WORKER] --- Начало попытки аутентификации ---")
            
            # Импортируем обработчик
            from handlers.polycom.rpg310 import PolycomRPG310Handler
            
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
            handler.connect()
            
            self.signals.connected.emit()
            from core.parser import PolycomDataParser

            self.signals.status.emit("Получаю данные по HTTPS...")
            self.signals.progress.emit(45)

            print("Вызываю handler.get_https_status()...")
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
            

class BiampTesiraForteCIWorker(QRunnable):
    """Read-only worker for Biamp Tesira Forte CI audio-DSP signal status."""

    def __init__(self, ip_address: str, username: str = None, password: str = None):
        super().__init__()
        self.ip_address = ip_address
        self.username = username
        self.password = password
        self.signals = WorkerSignals()
        self.creds_list = []
        self.current_idx = 0
        self.device_name = "Biamp Tesira Forte CI"

    @pyqtSlot()
    def run(self):
        from handlers.biamp.tesira_forte_ci import BiampTesiraForteCIHandler

        handler = None
        try:
            if not self.username or not self.password:
                raise AuthenticationError(
                    "Credentials are required for Biamp Tesira Forte CI before connecting."
                )
            self.signals.status.emit("Подключение к Biamp Tesira Forte CI...")
            self.signals.progress.emit(15)
            self.signals.terminal_log.emit(
                f"[connect] Biamp Tesira Forte CI {self.ip_address}"
            )

            handler = BiampTesiraForteCIHandler(
                ip_address=self.ip_address,
                username=self.username,
                password=self.password,
            )
            handler.connect()
            self.signals.connected.emit()

            self.signals.status.emit("Получение источников сигнала...")
            self.signals.progress.emit(55)
            raw_data = handler.get_status()

            self.signals.status.emit("Обработка данных Biamp...")
            self.signals.progress.emit(80)
            parsed_data = BiampTesiraForteCIDataParser.parse_raw_data(raw_data)
            parsed_data["ip_address"] = self.ip_address

            self.signals.progress.emit(100)
            self.signals.result.emit(redact_data(parsed_data, _worker_secrets(self)))
            self.signals.disconnected.emit()
        except AuthenticationError as exc:
            _emit_error(self, "authentication_error", exc, trace=False)
        except Exception as exc:
            _emit_error(self, "connection_error", exc)
        finally:
            if handler:
                try:
                    handler.disconnect()
                except Exception:
                    pass
            self.signals.finished.emit()


class ExtronIN1804Worker(QRunnable):
    """Worker для опроса матрицы Extron IN1804"""
    
    def __init__(self, ip_address, port=22023, username=None, password=None):
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.signals = WorkerSignals()
        self.handler = None
    
    @pyqtSlot()
    def run(self):
        """Запуск процесса опроса"""
        try:
            self.signals.status.emit("Подключение к матрице Extron IN1804...")
            self.signals.progress.emit(10)
            
            # Создаем и подключаем обработчик
            self.handler = ExtronIN1804Handler(
                ip_address=self.ip_address,
                port=self.port,
                username=self.username,
                password=self.password
            )
            self.handler.log_callback = redacted_callback(self.signals.terminal_log.emit, _worker_secrets(self))
            
            self.signals.status.emit("Установка соединения...")
            self.signals.progress.emit(20)
            self.handler.connect()
            
            self.signals.status.emit("Получение информации об устройстве...")
            self.signals.progress.emit(30)
            status = self.handler.get_full_status()
            
            self.signals.status.emit("Парсинг данных...")
            self.signals.progress.emit(80)
            
            # Парсим данные
            parser = ExtronIN1804DataParser()
            parsed_data = parser.parse(status)
            
            # Добавляем IP адрес
            parsed_data['ip_address'] = self.ip_address
            
            self.signals.progress.emit(100)
            self.signals.status.emit("Готово!")
            self.signals.result.emit(redact_data(parsed_data, _worker_secrets(self)))
            
        except Exception as e:
            import traceback
            error_message, error_traceback = _safe_error(e, _worker_secrets(self))
            if "authentication" in error_message.lower():
                self.signals.error.emit(("authentication_error", error_message, error_traceback))
            else:
                self.signals.error.emit(("ExtronIN1804Error", error_message, error_traceback))
        
        finally:
            if self.handler:
                self.handler.disconnect()
            self.signals.finished.emit()
            


class PDUOperationWorker(QRunnable):
    """Background refresh/control worker for model-aware PDU operations."""

    def __init__(
        self,
        descriptor: PDUOperationDescriptor,
        credentials: Optional[Dict] = None,
        is_current=None,
        handler_factory=None,
    ):
        super().__init__()
        self.descriptor = descriptor
        self.ip_address = descriptor.ip_address
        self.device_name = descriptor.model
        self.operation = descriptor.operation
        self.outlet_number = descriptor.outlet_number
        self.credentials = normalize_pdu_credentials(descriptor.model, credentials or {})
        self.username = self.credentials.get("username")
        self.password = self.credentials.get("password")
        self.current_idx = descriptor.credential_index or 0
        self.creds_list = []
        self.is_current = is_current or (lambda _descriptor: True)
        self.handler_factory = handler_factory
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            self.signals.progress.emit(10)
            if self.operation == REFRESH:
                self.signals.status.emit("Получение статуса PDU...")
                result = execute_pdu_refresh(
                    descriptor=self.descriptor,
                    credentials=self.credentials,
                    is_current=self.is_current,
                    **self._factory_kwargs(),
                )
            else:
                self.signals.status.emit("Выполнение команды PDU...")
                result = execute_pdu_command(
                    descriptor=self.descriptor,
                    credentials=self.credentials,
                    is_current=self.is_current,
                    **self._factory_kwargs(),
                )
            self.signals.progress.emit(100)
            if result.get("_outcome") == "stale":
                return
            self.signals.result.emit(redact_data(result, _worker_secrets(self)))
        except CredentialRequired as error:
            _emit_error(self, "credential_required", error, trace=False)
        except AuthenticationError as error:
            _emit_error(self, "authentication_error", error, trace=False)
        except CommandOutcomeUnknownError as error:
            _emit_error(self, "indeterminate_outcome", error, trace=False)
        except CommandError as error:
            _emit_error(self, "unsupported_operation", error, trace=False)
        except ConnectionError as error:
            _emit_error(self, "connection_error", error, trace=False)
        except Exception as error:
            _emit_error(self, "connection_error", error)
        finally:
            self.signals.finished.emit()

    def _factory_kwargs(self):
        if self.handler_factory is None:
            return {}
        return {"handler_factory": self.handler_factory}


class AtenPDUWorker(QRunnable):
    """Worker для асинхронной работы с PDU Aten"""
    
    def __init__(self, ip_address: str, port: int = 443, 
                 username: str = None, password: str = None):
        super().__init__()
        
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.signals = WorkerSignals()
        
        self.handler = None
        self.creds_list = []  # Будет заполнено в refresh_data
        self.current_idx = 0
        self.device_name = "Aten PE8208AV"
    
    @pyqtSlot()
    def run(self):
        """Основной метод работы в потоке"""
        from handlers.aten.pdu import AtenPDUHandler

        try:
            if not self.username or not self.password:
                raise AuthenticationError(
                    'Credentials are required for Aten PDU before connecting.'
                )
            self.handler = AtenPDUHandler(
                ip_address=self.ip_address,
                port=self.port,
                username=self.username,
                password=self.password
            )

            self.signals.progress.emit(10)
            self.signals.status.emit("Подключение к PDU...")

            if not self.handler.connect():
                raise AuthenticationError(
                    "Не удалось аутентифицироваться с указанными credentials"
                )

            self.signals.progress.emit(60)
            self.signals.status.emit("Получение статуса розеток...")
            outlets = self.handler.get_outlets_status()

            self.signals.progress.emit(80)
            self.signals.status.emit("Получение информации об устройстве...")
            device_info = self.handler.get_device_info()

            result = {
                'device_info': device_info,
                'outlets': outlets,
                'ip_address': self.ip_address,
                'model': 'PE8208AV',
                'manufacturer': 'Aten',
                'type': 'pdu'
            }

            self.signals.progress.emit(100)
            self.signals.result.emit(redact_data(result, _worker_secrets(self)))

        except AuthenticationError as e:
            _emit_error(self, 'authentication_error', e, trace=False)
        except ConnectionError as e:
            _emit_error(self, 'connection_error', e, trace=False)
        except Exception as e:
            _emit_error(self, 'connection_error', e)
        finally:
            if self.handler:
                try:
                    self.handler.disconnect()
                except Exception:
                    pass
                self.handler = None
            self.signals.finished.emit()


