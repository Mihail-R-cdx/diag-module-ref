"""Background workers for codec state-changing actions."""

from PyQt5.QtCore import QRunnable, pyqtSlot

from core.exceptions import AuthenticationError
from core.redaction import redacted_callback
from core.workers.common import WorkerSignals, _emit_error, _worker_secrets
from handlers.huawei.bar310 import CloudLinkBar310Handler
from handlers.huawei.te40 import HuaweiTE40Handler


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
        if self.device_name in {"CloudLink Bar 310", "CloudLink Box 310"}:
            return CloudLinkBar310Handler(
                ip_address=self.ip_address,
                port=self.port,
                username=self.username,
                password=self.password,
                expected_identity=(
                    "Huawei CloudLink Box 310"
                    if self.device_name == "CloudLink Box 310"
                    else "Huawei CloudLink Bar 310"
                ),
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
