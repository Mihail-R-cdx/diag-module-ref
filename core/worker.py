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
from .exceptions import AuthenticationError, ConnectionError
import traceback


def _mask_secret_text(text: str, secret_values=()):
    masked = str(text)
    for secret in secret_values:
        if secret:
            masked = masked.replace(str(secret), "***")
    return masked


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


class HuaweiTE40Worker(QRunnable):
    """Специализированный Worker для Huawei TE-40"""
    
    def __init__(self, ip_address: str, port: int = 443,
                 username: str = 'api', password: str = ''):
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        handler = None
        try:
            if not self.username or not self.password:
                raise AuthenticationError("Credentials are required for Huawei TE40 before connecting.")
            self.signals.status.emit("Начинаю подключение...")
            self.signals.progress.emit(10)
            
            print(f"=== HuaweiTE40Worker.run() для {self.ip_address} ===")
            print("[WORKER] 🔐 Credentials загружены (значения скрыты)")
            print(f"[WORKER] --- Начало попытки аутентификации ---")
            
            handler = HuaweiTE40Handler(
                ip_address=self.ip_address,
                port=self.port,
                username=self.username,
                password=self.password,
                use_ssl=True
            )
            handler.command_logger = self.signals.terminal_log.emit
            
            self.signals.status.emit("Подключаюсь к устройству...")
            self.signals.progress.emit(30)
            
            # Try TE40 over HTTPS first, then fall back to HTTP.
            self.signals.terminal_log.emit(f"[connect] attempt 1/2 via HTTPS:{self.port}")
            try:
                if not handler.connect():
                    raise ConnectionError(f"HTTPS:{self.port} did not return a valid TE40 session")
                self.signals.terminal_log.emit(f"[connect] success via HTTPS:{self.port}")
            except Exception as first_error:
                first_auth_error = first_error if isinstance(first_error, AuthenticationError) else None
                handler.disconnect()
                self.signals.terminal_log.emit(f"[connect] HTTPS:{self.port} failed: {type(first_error).__name__}: {first_error}")

                handler = HuaweiTE40Handler(
                    ip_address=self.ip_address,
                    port=80,
                    username=self.username,
                    password=self.password,
                    use_ssl=False
                )
                handler.command_logger = self.signals.terminal_log.emit
                self.signals.terminal_log.emit("[connect] attempt 2/2 via HTTP:80")
                try:
                    if not handler.connect():
                        raise ConnectionError("HTTP:80 did not return a valid TE40 session")
                    self.signals.terminal_log.emit("[connect] success via HTTP:80")
                except Exception:
                    if first_auth_error is not None:
                        raise first_auth_error
                    raise
            
            self.signals.connected.emit()
            self.signals.status.emit("Получаю данные...")
            self.signals.progress.emit(50)
            
            print("Вызываю handler.get_status()...")
            raw_data = handler.get_status()
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
            self.signals.result.emit(parsed_data)
            
            print("Отключение...")
            handler.disconnect()
            self.signals.disconnected.emit()
            
        except AuthenticationError as e:
            print(f"!!! Ошибка аутентификации в HuaweiTE40Worker: {str(e)}")
            # Пробрасываем как ошибку с ключевым словом authentication
            self.signals.error.emit(('authentication_error', str(e), traceback.format_exc()))
        except Exception as e:
            print(f"!!! Ошибка в HuaweiTE40Worker: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            error_data = {
                'ip_address': self.ip_address,
                'Модель': 'Huawei TE40',
                'Версия ПО': 'Ошибка подключения',
                'Сообщение': f'Ошибка: {str(e)}'
            }
            self.signals.result.emit(error_data)
        finally:
            self.signals.finished.emit()
        

    def set_sip_server(self, sip_address="vcs-core-a.sber.ru"):
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
            print(f"Exception in set_sip_server: {e}")
            import traceback
            traceback.print_exc()
            self.signals.error.emit(('set_sip_server_error', str(e), traceback.format_exc()))


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
            self.signals.status.emit(
                f"Подключение к {self.device_name} для установки SIP сервера..."
            )
            self.signals.progress.emit(10)

            handler = self._create_handler()
            handler.command_logger = self.signals.terminal_log.emit
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
            self.signals.error.emit(('authentication_error', str(e), traceback.format_exc()))
        except Exception as e:
            self.signals.error.emit(('set_sip_server_error', str(e), traceback.format_exc()))
        finally:
            if handler:
                try:
                    handler.disconnect()
                except Exception:
                    pass
            self.signals.finished.emit()


class HuaweiBar310Worker(QRunnable):
    """Специализированный Worker для Huawei CloudLink Bar 310 с перебором credentials"""
    
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
        """Основной метод работы с циклом перебора credentials"""
        creds_to_try = self.creds_list or [
            {'username': self.username, 'password': self.password}
        ]
        if not all(creds.get('username') and creds.get('password') for creds in creds_to_try):
            self.signals.error.emit(('authentication_error', 'Credentials are required for CloudLink Bar 310 before connecting.', ''))
            self.signals.finished.emit()
            return
        
        total_creds = len(creds_to_try)
        start_idx = self.current_idx if 0 <= self.current_idx < total_creds else 0
        ordered_indices = list(range(start_idx, total_creds)) + list(range(0, start_idx))
        
        print(f"=== HuaweiBar310Worker.run() для {self.ip_address} ===")
        print(f"[WORKER] Всего credentials для проверки: {total_creds}")
        print(f"[WORKER] Старт с credentials #{start_idx + 1}")
        
        for attempt_no, actual_idx in enumerate(ordered_indices, start=1):
            self.current_idx = actual_idx
            creds = creds_to_try[actual_idx]
            print(f"[WORKER] Попытка #{attempt_no}/{total_creds} (credentials #{actual_idx + 1}): {creds['username']}:{'*' * len(creds['password'])}")
            
            handler = None
            try:
                self.signals.status.emit(f"Подключение (попытка {attempt_no}/{total_creds})...")
                self.signals.progress.emit(10)
                
                handler = CloudLinkBar310Handler(
                    ip_address=self.ip_address,
                    port=self.port,
                    username=creds['username'],
                    password=creds['password']
                )
                handler.command_logger = self.signals.terminal_log.emit
                
                self.signals.status.emit("Подключаюсь к устройству...")
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
                self.signals.result.emit(parsed_data)
                
                print("Отключение...")
                handler.disconnect()
                self.signals.disconnected.emit()
                
                if hasattr(self, 'device_name') and self.device_name:
                    if not hasattr(self, 'current_credential_index'):
                        self.current_credential_index = {}
                    self.current_credential_index[self.device_name] = actual_idx
                    print(f"[BAR310] Сохранен успешный credentials #{actual_idx + 1} для {self.device_name}")
                
                self.signals.finished.emit()
                return
                
            except AuthenticationError as e:
                print(f"[BAR310] Ошибка аутентификации на попытке #{attempt_no}: {str(e)}")
                if attempt_no < total_creds:
                    print("[BAR310] Пробуем следующие credentials...")
                    continue
                print("[BAR310] Все credentials исчерпаны, пробрасываем ошибку")
                self.signals.error.emit(('authentication_error', str(e), traceback.format_exc()))
                self.signals.finished.emit()
                return
                    
            except Exception as e:
                print(f"[BAR310] Ошибка подключения на попытке #{attempt_no}: {type(e).__name__}: {str(e)}")
                if attempt_no < total_creds:
                    print("[BAR310] Пробуем следующие credentials...")
                    continue
                print("[BAR310] Все credentials исчерпаны, пробрасываем ошибку")
                self.signals.error.emit(('connection_error', str(e), traceback.format_exc()))
                self.signals.finished.emit()
                return
                    
            finally:
                if handler:
                    try:
                        handler.disconnect()
                    except:
                        pass
        
        print("[BAR310] Все попытки подключения неудачны")
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
            handler.command_logger = self.signals.terminal_log.emit
            
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
            self.signals.result.emit(parsed_data)

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
            self.signals.result.emit(parsed_data)
            
        except AuthenticationError as e:
            print(f"!!! Ошибка аутентификации в PolycomRPG310Worker: {str(e)}")
            self.signals.error.emit(('authentication_error', str(e), traceback.format_exc()))
        except Exception as e:
            print(f"!!! Ошибка в PolycomRPG310Worker: {type(e).__name__}: {str(e)}")
            traceback.print_exc()
            
            error_data = {
                'ip_address': self.ip_address,
                'Модель': 'Polycom RealPresence Group 310',
                'Версия ПО': 'Ошибка подключения',
                'Сообщение': f'Ошибка: {str(e)}'
            }
            self.signals.result.emit(error_data)
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
        creds_to_try = self.creds_list if self.creds_list else [
            {"username": self.username, "password": self.password}
        ]
        total_creds = len(creds_to_try)
        start_idx = self.current_idx if 0 <= self.current_idx < total_creds else 0
        ordered_indices = list(range(start_idx, total_creds)) + list(range(0, start_idx))

        from handlers.biamp.tesira_forte_ci import BiampTesiraForteCIHandler

        try:
            for attempt_no, actual_idx in enumerate(ordered_indices, start=1):
                creds = creds_to_try[actual_idx]
                self.current_idx = actual_idx
                handler = None
                try:
                    self.signals.status.emit(
                        f"Подключение к Biamp Tesira Forte CI (попытка {attempt_no}/{total_creds})..."
                    )
                    self.signals.progress.emit(15)
                    self.signals.terminal_log.emit(
                        f"[connect] Biamp Tesira Forte CI {self.ip_address} attempt {attempt_no}/{total_creds}"
                    )

                    handler = BiampTesiraForteCIHandler(
                        ip_address=self.ip_address,
                        username=creds.get("username", ""),
                        password=creds.get("password", ""),
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
                    self.signals.result.emit(parsed_data)
                    self.signals.disconnected.emit()
                    return
                except AuthenticationError:
                    if attempt_no < total_creds:
                        continue
                    raise
                except Exception as exc:
                    safe_error = _mask_secret_text(str(exc), (creds.get("password", ""),))
                    if attempt_no < total_creds and "auth" in safe_error.lower():
                        continue
                    raise RuntimeError(safe_error) from None
                finally:
                    if handler:
                        try:
                            handler.disconnect()
                        except Exception:
                            pass
        except AuthenticationError as exc:
            self.signals.error.emit(("authentication_error", _mask_secret_text(str(exc), [self.password]), ""))
        except Exception as exc:
            self.signals.error.emit(("connection_error", _mask_secret_text(str(exc), [self.password]), traceback.format_exc()))
        finally:
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
            self.handler.log_callback = self.signals.terminal_log.emit
            
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
            self.signals.result.emit(parsed_data)
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            error_message = str(e)
            if "authentication" in error_message.lower():
                self.signals.error.emit(("authentication_error", error_message, error_traceback))
            else:
                self.signals.error.emit(("ExtronIN1804Error", error_message, error_traceback))
        
        finally:
            if self.handler:
                self.handler.disconnect()
            self.signals.finished.emit()
            


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
        creds_to_try = self.creds_list or [{'username': self.username, 'password': self.password}]
        if not all(creds.get('username') and creds.get('password') for creds in creds_to_try):
            self.signals.error.emit(('authentication_error', 'Credentials are required for Aten PDU before connecting.', ''))
            self.signals.finished.emit()
            return

        total_creds = len(creds_to_try)
        start_idx = self.current_idx if 0 <= self.current_idx < total_creds else 0
        ordered_indices = list(range(start_idx, total_creds)) + list(range(0, start_idx))

        from handlers.aten.pdu import AtenPDUHandler

        try:
            for attempt_no, actual_idx in enumerate(ordered_indices, start=1):
                creds = creds_to_try[actual_idx]
                self.current_idx = actual_idx
                self.handler = AtenPDUHandler(
                    ip_address=self.ip_address,
                    port=self.port,
                    username=creds['username'],
                    password=creds['password']
                )

                try:
                    self.signals.progress.emit(10)
                    self.signals.status.emit(f"Подключение к PDU (попытка {attempt_no}/{total_creds})...")

                    if not self.handler.connect():
                        raise AuthenticationError("Не удалось аутентифицироваться с указанными credentials")

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
                    self.signals.result.emit(result)
                    return

                except AuthenticationError:
                    if self.handler:
                        self.handler.disconnect()
                        self.handler = None
                    if attempt_no < total_creds:
                        continue
                    raise
                except Exception:
                    if self.handler:
                        self.handler.disconnect()
                        self.handler = None
                    raise

        except AuthenticationError as e:
            self.signals.error.emit(('authentication_error', str(e), ''))
        except ConnectionError as e:
            self.signals.error.emit(('connection', str(e), ''))
        except Exception as e:
            self.signals.error.emit(('unknown', str(e), traceback.format_exc()))
        finally:
            if self.handler:
                self.handler.disconnect()
            self.signals.finished.emit()


