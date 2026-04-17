# core/workers/te20_worker.py
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, QRunnable
import traceback

from core.exceptions import AuthenticationError, ConnectionError
from core.parser import HuaweiTE20DataParser
from handlers.huawei.te20 import HuaweiTE20Handler


class WorkerSignals(QObject):
    """Сигналы для общения между потоками."""

    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(dict)
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    connected = pyqtSignal()
    disconnected = pyqtSignal()


class HuaweiTE20Worker(QRunnable):
    """Специализированный Worker для Huawei TE-20."""

    def __init__(self, ip_address: str, port: int = 80, username: str = "api", password: str = ""):
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.signals = WorkerSignals()
        self.is_running = True

    @pyqtSlot()
    def run(self):
        handler = None

        try:
            self.signals.status.emit("Начинаю подключение к TE-20...")
            self.signals.progress.emit(10)

            print(f"=== HuaweiTE20Worker.run() для {self.ip_address} ===")
            print(f"Username: '{self.username}', Password: '{self.password}'")

            connection_profiles = [
                {"port": self.port, "use_ssl": False, "label": "HTTP:80"},
                {"port": 443, "use_ssl": True, "label": "HTTPS:443"},
            ]

            seen_profiles = set()
            unique_profiles = []
            for profile in connection_profiles:
                key = (profile["port"], profile["use_ssl"])
                if key not in seen_profiles:
                    seen_profiles.add(key)
                    unique_profiles.append(profile)

            last_connection_error = None
            auth_error = None

            for index, profile in enumerate(unique_profiles, start=1):
                self.signals.status.emit(
                    f"Подключаюсь к устройству ({profile['label']}, {index}/{len(unique_profiles)})..."
                )
                self.signals.progress.emit(20 + index * 10)

                print(
                    f"[TE20] Пробую подключение через {profile['label']} "
                    f"(use_ssl={profile['use_ssl']}, port={profile['port']})"
                )

                current_handler = HuaweiTE20Handler(
                    ip_address=self.ip_address,
                    port=profile["port"],
                    username=self.username,
                    password=self.password,
                    use_ssl=profile["use_ssl"],
                )

                try:
                    if current_handler.connect():
                        handler = current_handler
                        print(f"[TE20] Подключение успешно через {profile['label']}")
                        break

                    last_connection_error = (
                        f"Устройство не приняло подключение через {profile['label']}"
                    )
                    current_handler.disconnect()
                except AuthenticationError as e:
                    auth_error = e
                    current_handler.disconnect()
                    print(f"[TE20] Ошибка аутентификации через {profile['label']}: {e}")
                    break
                except Exception as e:
                    last_connection_error = f"{profile['label']}: {e}"
                    current_handler.disconnect()
                    print(f"[TE20] Ошибка подключения через {profile['label']}: {e}")

            if auth_error is not None:
                raise auth_error
            if handler is None:
                raise ConnectionError(
                    last_connection_error
                    or "Не удалось подключиться к TE-20 ни по HTTP:80, ни по HTTPS:443"
                )

            self.signals.connected.emit()
            self.signals.status.emit("Получаю данные...")
            self.signals.progress.emit(50)

            print("Вызываю handler.get_status()...")
            raw_data = handler.get_status()
            print(f"get_status() вернул: {raw_data}")

            self.signals.status.emit("Обрабатываю данные...")
            self.signals.progress.emit(70)

            print("Парсинг данных...")
            parsed_data = HuaweiTE20DataParser.parse_raw_data(raw_data)
            print(f"Парсинг завершен: {parsed_data}")

            parsed_data["ip_address"] = self.ip_address

            self.signals.progress.emit(90)
            print("Отправка результата...")
            self.signals.result.emit(parsed_data)

            print("Отключение...")
            handler.disconnect()
            handler = None
            self.signals.disconnected.emit()

        except AuthenticationError as e:
            print(f"!!! Ошибка аутентификации в HuaweiTE20Worker: {str(e)}")
            self.signals.error.emit(("authentication_error", str(e), traceback.format_exc()))
        except Exception as e:
            print(f"!!! Ошибка в HuaweiTE20Worker: {type(e).__name__}: {str(e)}")
            traceback.print_exc()
            self.signals.error.emit(("connection_error", str(e), traceback.format_exc()))
        finally:
            if handler is not None:
                try:
                    handler.disconnect()
                except Exception:
                    pass
            self.signals.finished.emit()

    def stop(self):
        self.is_running = False
