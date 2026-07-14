# core/workers/te20_worker.py
from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot
import traceback

from core.exceptions import AuthenticationError, ConnectionError
from core.parser import HuaweiTE20DataParser
from handlers.huawei.te20 import HuaweiTE20Handler
from utils.te20_stack import inspect_te20_https_stack
from core.redaction import redact_data, redact_exception, redact_text, redacted_callback


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

    def __init__(self, ip_address: str, port: int = 80, username: str = None, password: str = None):
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
        self._emit(
            self.signals.terminal_log,
            redact_text(message, self._secrets()),
        )

    def _secrets(self) -> tuple:
        values = [self.username, self.password]
        for credential in self.creds_list:
            if isinstance(credential, dict):
                values.extend(credential.values())
        return tuple(values)

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

    @pyqtSlot()
    def run(self):
        handler = None

        try:
            if not self.username or not self.password:
                raise AuthenticationError("Credentials are required for Huawei TE20 before connecting.")
            self._log(f"[session] start {self.ip_address}")
            self._emit(self.signals.status, "Начинаю подключение к TE-20...")
            self._emit(self.signals.progress, 10)

            print(f"=== HuaweiTE20Worker.run() для {self.ip_address} ===")

            unique_profiles = self._build_unique_profiles()
            last_connection_error = None
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
                current_handler.command_logger = redacted_callback(
                    self._log, self._secrets()
                )

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
                    try:
                        current_handler.disconnect()
                    except Exception:
                        pass
                    safe_error = redact_exception(e, self._secrets())
                    print(f"[TE20] Ошибка аутентификации через {profile['label']}: {safe_error}")
                    self._log(f"[auth] {profile['label']}: {safe_error}")
                    raise
                except Exception as e:
                    safe_error = redact_exception(e, self._secrets())
                    last_connection_error = f"{profile['label']}: {safe_error}"
                    try:
                        current_handler.disconnect()
                    except Exception:
                        pass
                    print(f"[TE20] Ошибка подключения через {profile['label']}: {safe_error}")
                    self._log(f"[error] {profile['label']}: {type(e).__name__}: {safe_error}")

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
            print(f"get_status() вернул: {redact_data(raw_data, self._secrets())}")
            self._log(f"[status] raw keys: {', '.join(sorted(raw_data.keys())) if raw_data else 'none'}")

            self._emit(self.signals.status, "Обрабатываю данные...")
            self._emit(self.signals.progress, 70)

            print("Парсинг данных...")
            parsed_data = HuaweiTE20DataParser.parse_raw_data(raw_data)
            print(f"Парсинг завершен: {redact_data(parsed_data, self._secrets())}")
            self._log(f"[status] parsed keys: {', '.join(sorted(parsed_data.keys())) if parsed_data else 'none'}")

            parsed_data["ip_address"] = self.ip_address
            parsed_data["connection_profile"] = {
                "port": handler.port,
                "use_ssl": bool(handler.use_ssl),
                "label": f"{'HTTPS' if handler.use_ssl else 'HTTP'}:{handler.port}",
            }

            self._emit(self.signals.progress, 90)
            print("Отправка результата...")
            self._emit(self.signals.result, redact_data(parsed_data, self._secrets()))
            self._log("[session] completed successfully")

            print("Отключение...")
            try:
                handler.disconnect()
            except Exception:
                pass
            handler = None
            self._emit(self.signals.disconnected)

        except AuthenticationError as e:
            safe_error = redact_exception(e, self._secrets())
            print(f"!!! Ошибка аутентификации в HuaweiTE20Worker: {safe_error}")
            self._log(f"[session] failed authentication: {safe_error}")
            self._emit(self.signals.error, ("authentication_error", safe_error, redact_text(traceback.format_exc(), self._secrets())))
        except Exception as e:
            safe_error = redact_exception(e, self._secrets())
            print(f"!!! Ошибка в HuaweiTE20Worker: {type(e).__name__}: {safe_error}")
            try:
                print(redact_text(traceback.format_exc(), self._secrets()))
            except OSError:
                pass
            self._log(f"[session] failed: {type(e).__name__}: {safe_error}")
            self._emit(self.signals.error, ("connection_error", safe_error, redact_text(traceback.format_exc(), self._secrets())))
        finally:
            if handler is not None:
                try:
                    handler.disconnect()
                except Exception:
                    pass
            self._emit(self.signals.finished)

    def stop(self):
        self.is_running = False
