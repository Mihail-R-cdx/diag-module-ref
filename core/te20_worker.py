# core/workers/te20_worker.py
from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot
import traceback

from core.exceptions import AuthenticationError, ConnectionError
from core.parser import HuaweiTE20DataParser
from handlers.huawei.te20 import HuaweiTE20Handler
from utils.te20_stack import inspect_te20_https_stack


class WorkerSignals(QObject):
    """Сигналы для общения между потоками."""

    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(dict)
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    terminal_log = pyqtSignal(str)
    connected = pyqtSignal()
    disconnected = pyqtSignal()


class HuaweiTE20Worker(QRunnable):
    """Специализированный worker для Huawei TE20."""

    def __init__(self, ip_address: str, port: int = 80, username: str = "admin", password: str = "admin"):
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.signals = WorkerSignals()
        self.is_running = True
        self.creds_list = []
        self.current_idx = 0

    def _emit(self, signal, *args) -> bool:
        try:
            signal.emit(*args)
            return True
        except RuntimeError:
            return False

    def _log(self, message: str) -> None:
        self._emit(self.signals.terminal_log, message)

    def _build_unique_profiles(self) -> list[dict]:
        connection_profiles = [
            {"port": self.port, "use_ssl": False, "label": "HTTP:80"},
        ]
        https_stack_info = inspect_te20_https_stack()
        if https_stack_info["ready"]:
            connection_profiles.append({"port": 443, "use_ssl": True, "label": "HTTPS:443"})
        else:
            self._log(
                "[connect] HTTPS:443 fallback skipped: "
                f"{https_stack_info['transport']} is not ready. {https_stack_info['warning']}"
            )

        seen_profiles = set()
        unique_profiles = []
        for profile in connection_profiles:
            key = (profile["port"], profile["use_ssl"])
            if key not in seen_profiles:
                seen_profiles.add(key)
                unique_profiles.append(profile)
        return unique_profiles

    def _ordered_credentials(self) -> list[tuple[int, dict]]:
        creds_to_try = self.creds_list or [{"username": self.username, "password": self.password}]
        total_creds = len(creds_to_try)
        start_idx = self.current_idx if 0 <= self.current_idx < total_creds else 0
        ordered_indices = list(range(start_idx, total_creds)) + list(range(0, start_idx))
        return [(index, creds_to_try[index]) for index in ordered_indices]

    @pyqtSlot()
    def run(self):
        handler = None

        try:
            self._log(f"[session] start {self.ip_address}")
            self._emit(self.signals.status, "Начинаю подключение к TE-20...")
            self._emit(self.signals.progress, 10)

            print(f"=== HuaweiTE20Worker.run() для {self.ip_address} ===")

            unique_profiles = self._build_unique_profiles()
            ordered_creds = self._ordered_credentials()
            total_creds = len(ordered_creds)
            print(f"[TE20] Credentials to try: {total_creds}")

            last_connection_error = None
            auth_error = None

            for attempt_no, (actual_idx, creds) in enumerate(ordered_creds, start=1):
                self.current_idx = actual_idx
                self.username = creds.get("username", self.username)
                self.password = creds.get("password", self.password)

                self._log(f"[session] attempt {attempt_no}/{total_creds}")
                print(
                    f"[TE20] Credential attempt #{attempt_no}/{total_creds} "
                    f"(#{actual_idx + 1}); values redacted"
                )

                credential_auth_error = None

                for index, profile in enumerate(unique_profiles, start=1):
                    self._emit(
                        self.signals.status,
                        f"Подключаюсь к устройству ({profile['label']}, {index}/{len(unique_profiles)})..."
                    )
                    self._emit(self.signals.progress, 20 + index * 10)
                    self._log(f"[connect] attempt {index}/{len(unique_profiles)} via {profile['label']}")

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
                    current_handler.command_logger = self._log

                    try:
                        if current_handler.connect():
                            handler = current_handler
                            print(f"[TE20] Подключение успешно через {profile['label']}")
                            self._log(f"[connect] success via {profile['label']}")
                            break

                        last_connection_error = (
                            f"Устройство не приняло подключение через {profile['label']}"
                        )
                        self._log(f"[connect] rejected via {profile['label']}")
                        current_handler.disconnect()
                    except AuthenticationError as e:
                        current_handler.disconnect()
                        print(f"[TE20] Ошибка аутентификации через {profile['label']}: {e}")
                        self._log(f"[auth] {profile['label']}: {e}")
                        credential_auth_error = e
                        last_connection_error = str(e)
                        break
                    except Exception as e:
                        last_connection_error = f"{profile['label']}: {e}"
                        current_handler.disconnect()
                        print(f"[TE20] Ошибка подключения через {profile['label']}: {e}")
                        self._log(f"[error] {profile['label']}: {type(e).__name__}: {e}")

                if handler is not None:
                    break
                if credential_auth_error is not None:
                    auth_error = credential_auth_error
                    continue

            if handler is None and auth_error is not None:
                raise auth_error
            if handler is None:
                raise ConnectionError(
                    last_connection_error
                    or "Не удалось подключиться к TE-20 ни по HTTP:80, ни по HTTPS:443"
                )

            self._emit(self.signals.connected)
            self._emit(self.signals.status, "Получаю данные...")
            self._emit(self.signals.progress, 50)
            self._log("[status] collecting device status")

            print("Вызываю handler.get_status()...")
            raw_data = handler.get_status()
            print(f"get_status() вернул: {raw_data}")
            self._log(f"[status] raw keys: {', '.join(sorted(raw_data.keys())) if raw_data else 'none'}")

            self._emit(self.signals.status, "Обрабатываю данные...")
            self._emit(self.signals.progress, 70)

            print("Парсинг данных...")
            parsed_data = HuaweiTE20DataParser.parse_raw_data(raw_data)
            print(f"Парсинг завершен: {parsed_data}")
            self._log(f"[status] parsed keys: {', '.join(sorted(parsed_data.keys())) if parsed_data else 'none'}")

            parsed_data["ip_address"] = self.ip_address
            parsed_data["connection_profile"] = {
                "port": handler.port,
                "use_ssl": bool(handler.use_ssl),
                "label": f"{'HTTPS' if handler.use_ssl else 'HTTP'}:{handler.port}",
            }

            self._emit(self.signals.progress, 90)
            print("Отправка результата...")
            self._emit(self.signals.result, parsed_data)
            self._log("[session] completed successfully")

            print("Отключение...")
            handler.disconnect()
            handler = None
            self._emit(self.signals.disconnected)

        except AuthenticationError as e:
            print(f"!!! Ошибка аутентификации в HuaweiTE20Worker: {str(e)}")
            self._log(f"[session] failed authentication: {e}")
            self._emit(self.signals.error, ("authentication_error", str(e), traceback.format_exc()))
        except Exception as e:
            print(f"!!! Ошибка в HuaweiTE20Worker: {type(e).__name__}: {str(e)}")
            try:
                print(traceback.format_exc())
            except OSError:
                pass
            self._log(f"[session] failed: {type(e).__name__}: {e}")
            self._emit(self.signals.error, ("connection_error", str(e), traceback.format_exc()))
        finally:
            if handler is not None:
                try:
                    handler.disconnect()
                except Exception:
                    pass
            self._emit(self.signals.finished)

    def stop(self):
        self.is_running = False
