from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import datetime
import socket
import time
import paramiko

from core.exceptions import AuthenticationError, ConnectionError


class ProtocolHandler(ABC):
    """Абстрактный базовый класс для всех обработчиков протоколов"""

    def __init__(self, ip_address: str, credentials: Optional[Dict] = None):
        self.ip_address = ip_address
        self.credentials = credentials or {}
        self._connected = False
        self._connection_time = None
        self._last_error = None

    # --- АБСТРАКТНЫЕ МЕТОДЫ ---
    @abstractmethod
    def connect(self) -> bool:
        """Установить соединение с устройством"""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Разорвать соединение"""
        pass

    @abstractmethod
    def send_command(self, command: str, data: Optional[Dict] = None) -> Dict:
        """Отправить команду устройству"""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Получить полный статус устройства"""
        pass

    @abstractmethod
    def get_device_info(self) -> Dict[str, str]:
        """Получить базовую информацию об устройстве"""
        pass

    # --- РЕАЛИЗОВАННЫЕ МЕТОДЫ ---
    def is_connected(self) -> bool:
        """Проверить, установлено ли соединение"""
        return self._connected

    def get_connection_time(self) -> Optional[datetime.datetime]:
        """Получить время установки соединения"""
        return self._connection_time

    def get_last_error(self) -> Optional[str]:
        """Получить последнюю ошибку"""
        return self._last_error


class BaseHuaweiCodecHandler(ProtocolHandler):
    """Базовый класс для всех кодеков Huawei"""

    def __init__(self, ip_address: str, port: int = 443,
                 username: str = 'admin', password: str = 'admin',
                 use_ssl: bool = True, verify_ssl: bool = False):
        super().__init__(ip_address, {'username': username, 'password': password})
        self.port = port
        self.use_ssl = use_ssl
        self.verify_ssl = verify_ssl
        self.session = None
        self.base_url = None
        self.device_model = None

    def _setup_session(self):
        """Настройка HTTP сессии"""
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.session = requests.Session()
        if not self.verify_ssl:
            self.session.verify = False

    @abstractmethod
    def get_system_info(self) -> Dict[str, str]:
        """Получить системную информацию"""
        pass

    @abstractmethod
    def get_call_status(self) -> Dict[str, Any]:
        """Получить статус вызова"""
        pass

    @abstractmethod
    def get_audio_status(self) -> Dict[str, Any]:
        """Получить статус аудио"""
        pass

    @abstractmethod
    def get_video_status(self) -> Dict[str, Any]:
        """Получить статус видео"""
        pass

    @abstractmethod
    def get_network_status(self) -> Dict[str, Any]:
        """Получить статус сети"""
        pass


class BaseExtronMatrixHandler(ProtocolHandler):
    """Базовый класс для обработчиков матриц Extron"""

    def __init__(self, ip_address: str, port: int = 22023, username: str = None, password: str = None):
        credentials = {
            'port': port,
            'username': username,
            'password': password
        }
        super().__init__(ip_address, credentials)
        self.port = port
        self.username = username
        self.password = password
        self.socket = None
        self.ssh_client = None
        self.ssh_channel = None
        self.timeout = 5
        self.authenticated = False
        self.connection_protocol = 'Unknown'
        self._last_prompt = b''
        self.log_callback = None

    def connect(self) -> bool:
        """Установка TCP соединения с матрицей и аутентификация"""
        errors = []

        for attempt in self._build_connection_attempts():
            self.disconnect()
            attempt_name = attempt['name']
            attempt_port = attempt['port']
            print(f"Connecting to {self.ip_address}:{attempt_port} via {attempt_name}")
            self._emit_log(f"[connect] {self.ip_address}:{attempt_port} via {attempt_name}")

            try:
                if attempt['type'] == 'ssh':
                    self._connect_via_ssh(
                        port=attempt_port,
                        protocol_label=attempt['protocol_label']
                    )
                else:
                    initial_response = self._connect_plain_socket(
                        port=attempt_port,
                        protocol_label=attempt['protocol_label']
                    )
                    if self._is_ssh_banner(initial_response):
                        print(f"SSH banner detected on plain TCP port {attempt_port}, switching to SSH")
                        self._emit_log(f"[connect] SSH banner detected on {attempt_port}, switching to SSH")
                        self._close_socket()
                        self._connect_via_ssh(
                            port=attempt_port,
                            protocol_label=f"SSH ({attempt_port})"
                        )
                    else:
                        if not self._authenticate(initial_response):
                            raise AuthenticationError("Authentication failed")

                self._connected = True
                self.authenticated = True
                print(f"Successfully connected and authenticated to Extron matrix via {self.connection_protocol}")
                self._emit_log(f"[connect] connected via {self.connection_protocol}")
                return True
            except Exception as e:
                errors.append(f"{attempt_name}: {e}")
                print(f"Connection attempt failed ({attempt_name}): {e}")
                self._emit_log(f"[error] {attempt_name}: {e}")

        self.disconnect()

        auth_errors = [message for message in errors if 'auth' in message.lower() or 'login' in message.lower() or 'password' in message.lower()]
        if auth_errors:
            raise AuthenticationError("; ".join(auth_errors))
        raise ConnectionError(f"Failed to connect to Extron matrix: {'; '.join(errors)}")

    def _build_connection_attempts(self):
        attempts = [
            {
                'type': 'ssh',
                'port': 22022,
                'name': 'SSH first priority',
                'protocol_label': 'SSH (22022)'
            }
        ]

        if self.port != 22022:
            attempts.append({
                'type': 'plain',
                'port': self.port,
                'name': f'plain TCP on {self.port}',
                'protocol_label': f'Telnet ({self.port})'
            })

        if self.port != 22023:
            attempts.append({
                'type': 'plain',
                'port': 22023,
                'name': 'plain TCP fallback on 22023',
                'protocol_label': 'Telnet (22023)'
            })

        return attempts

    def _connect_plain_socket(self, port: int, protocol_label: str) -> bytes:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)
        self.socket.connect((self.ip_address, port))
        self.connection_protocol = protocol_label

        initial_response = self._read_until_patterns(
            [b'login as:', b'password:', b'ssh-'],
            timeout=1.5
        )
        if not initial_response:
            try:
                self.socket.sendall(b'\r\n')
            except Exception:
                pass
            wake_response = self._read_until_patterns(
                [b'login as:', b'password:', b'ssh-'],
                timeout=1.5
            )
            initial_response += wake_response

        self._last_prompt = initial_response
        print(f"Initial plain response: {initial_response[:200]}...")
        if initial_response:
            self._emit_log(f"[recv] {self._format_bytes(initial_response)}")
        return initial_response

    def _connect_via_ssh(self, port: int, protocol_label: str) -> None:
        if not self.username:
            raise AuthenticationError("Username required for Extron authentication")
        if self.password is None:
            raise AuthenticationError("Password required for Extron authentication")

        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(
                hostname=self.ip_address,
                port=port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False
            )
            self.ssh_channel = self.ssh_client.invoke_shell()
            self.ssh_channel.settimeout(self.timeout)
            self.connection_protocol = protocol_label
            time.sleep(1.0)
            self._last_prompt = self._read_until_patterns([b'>', b']', b'#'], timeout=1.5)
            self._emit_log(f"[connect] SSH session established on port {port}")
            if self._last_prompt:
                self._emit_log(f"[recv] {self._format_bytes(self._last_prompt)}")
            lowered_prompt = self._last_prompt.lower()
            if b'this service allows sftp connections only' in lowered_prompt:
                raise ConnectionError("SSH service is SFTP-only and does not provide CLI access")
        except paramiko.AuthenticationException as e:
            raise AuthenticationError(f"SSH authentication failed: {e}")
        except paramiko.SSHException as e:
            raise ConnectionError(f"SSH connection failed: {e}")

    def _authenticate(self, initial_response: bytes = b'') -> bool:
        """Вход в Extron: ждем `login as:`, отправляем логин, ждем `Password:`, отправляем пароль."""
        if self.connection_protocol == 'SSH':
            return True

        if not self.username:
            raise AuthenticationError("Username required for Extron authentication")
        if self.password is None:
            raise AuthenticationError("Password required for Extron authentication")

        login_prompt = initial_response or self._read_until_patterns(
            [b'login as:', b'password:', b'>', b']'],
            timeout=self.timeout
        )
        print(f"Login prompt received: {login_prompt[:200]}...")
        if login_prompt:
            self._emit_log(f"[recv] {self._format_bytes(login_prompt)}")
        lowered_login_prompt = login_prompt.lower()

        if self._is_ssh_banner(login_prompt):
            raise ConnectionError("SSH banner detected during telnet authentication")

        if b'password:' in lowered_login_prompt and b'login as:' not in lowered_login_prompt:
            print("Password prompt arrived before login prompt, sending username first")
            self._emit_log(f"[send] {self.username}")
            self._send_bytes((self.username + '\r\n').encode())
            password_prompt = self._read_until_patterns(
                [b'password:', b'login incorrect', b'login as:', b'>', b']'],
                timeout=self.timeout
            )
        else:
            if b'login as:' not in lowered_login_prompt and b'>' not in lowered_login_prompt and b']' not in lowered_login_prompt:
                self._send_bytes(b'\r\n')
                extra_prompt = self._read_until_patterns(
                    [b'login as:', b'password:', b'>', b']'],
                    timeout=self.timeout
                )
                login_prompt += extra_prompt
                lowered_login_prompt = login_prompt.lower()
                if extra_prompt:
                    self._emit_log(f"[recv] {self._format_bytes(extra_prompt)}")

            print(f"Sending username: {self.username}")
            self._emit_log(f"[send] {self.username}")
            self._send_bytes((self.username + '\r\n').encode())
            password_prompt = self._read_until_patterns(
                [b'Password:', b'Login incorrect', b'login as:', b'>', b']'],
                timeout=self.timeout
            )

        print(f"Response after username: {password_prompt[:200]}...")
        if password_prompt:
            self._emit_log(f"[recv] {self._format_bytes(password_prompt)}")
        lowered_password_prompt = password_prompt.lower()
        if b'login incorrect' in lowered_password_prompt:
            raise AuthenticationError("Invalid username")
        if b'password:' not in lowered_password_prompt and b'>' not in lowered_password_prompt and b']' not in lowered_password_prompt:
            raise AuthenticationError("Device did not request password")

        print("Sending password...")
        self._emit_log("[send] <password>")
        self._send_bytes((self.password + '\r\n').encode())

        final_response = self._read_until_patterns(
            [b'Password:', b'Login incorrect', b'login as:', b'>', b']'],
            timeout=self.timeout
        )
        print(f"Response after password: {final_response[:200]}...")
        if final_response:
            self._emit_log(f"[recv] {self._format_bytes(final_response)}")
        lowered_final_response = final_response.lower()

        if b'login incorrect' in lowered_final_response:
            raise AuthenticationError("Invalid password")
        if b'password:' in lowered_final_response or b'login as:' in lowered_final_response:
            raise AuthenticationError("Authentication prompts repeated after password")

        print("Authentication successful")
        return True

    def disconnect(self) -> None:
        """Закрытие соединения"""
        self._close_socket()
        self._close_ssh()
        self._connected = False
        self.authenticated = False
        self.connection_protocol = 'Unknown'
        self._last_prompt = b''

    def send_command(self, command: str, data: dict = None) -> dict:
        """Отправка команды и получение ответа"""
        if not self.socket and not self.ssh_channel:
            return {'success': False, 'error': 'Not connected to device', 'response': ''}

        try:
            if not self.authenticated:
                if not self._authenticate():
                    return {'success': False, 'error': 'Not authenticated', 'response': ''}

            if not command.endswith('\r'):
                command += '\r'

            print(f"Sending command: {command.strip()}")
            self._emit_log(f"[send] {command.strip()}")
            self._send_bytes(command.encode())
            time.sleep(0.5)

            response_bytes = self._read_response()
            print(f"Received response bytes: {response_bytes[:100]}...")
            if response_bytes:
                self._emit_log(f"[recv] {self._format_bytes(response_bytes)}")

            lowered_response = response_bytes.lower()
            if b'password:' in lowered_response or b'login as:' in lowered_response:
                print("Authentication requested again, re-authenticating...")
                self.authenticated = False
                if self._authenticate():
                    return self.send_command(command, data)
                return {'success': False, 'error': 'Re-authentication failed', 'response': ''}

            try:
                response_text = response_bytes.decode('utf-8', errors='ignore').strip()
            except:
                response_text = str(response_bytes)

            response_text = self._strip_command_echo(command, response_text)

            return {
                'success': True,
                'response': response_text,
                'raw_response': response_bytes
            }

        except Exception as e:
            print(f"Error in send_command: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': ''
            }

    def _read_response(self):
        """Чтение ответа от сокета"""
        response = b''
        start_time = time.time()
        last_chunk_time = None
        idle_after_data = 0.35
        poll_timeout = 0.1
        previous_timeout = self._set_transport_timeout(poll_timeout)

        try:
            while True:
                try:
                    if time.time() - start_time > self.timeout:
                        break

                    if response and last_chunk_time and (time.time() - last_chunk_time) > idle_after_data:
                        break

                    chunk = self._recv_bytes(1024)
                    if not chunk:
                        break
                    response += chunk
                    last_chunk_time = time.time()

                except socket.timeout:
                    if response and last_chunk_time and (time.time() - last_chunk_time) > idle_after_data:
                        break
                    continue
        finally:
            self._set_transport_timeout(previous_timeout)

        return response

    def _read_until_patterns(self, patterns, timeout=None):
        """Читаем ответ, пока не появится одно из ожидаемых подстрок."""
        if timeout is None:
            timeout = self.timeout

        response = b''
        start_time = time.time()
        normalized_patterns = [pattern.lower() for pattern in patterns]
        poll_timeout = 0.1
        previous_timeout = self._set_transport_timeout(poll_timeout)

        try:
            while time.time() - start_time <= timeout:
                try:
                    chunk = self._recv_bytes(1024)
                    if not chunk:
                        break

                    response += chunk
                    lowered_response = response.lower()
                    if any(pattern in lowered_response for pattern in normalized_patterns):
                        break
                except socket.timeout:
                    continue
        finally:
            self._set_transport_timeout(previous_timeout)

        return response

    def _send_bytes(self, payload: bytes) -> None:
        if self.ssh_channel:
            self.ssh_channel.send(payload.decode('utf-8', errors='ignore'))
        elif self.socket:
            self.socket.sendall(payload)
        else:
            raise ConnectionError("No active Extron transport")

    def _recv_bytes(self, size: int) -> bytes:
        if self.ssh_channel:
            if not self.ssh_channel.recv_ready():
                time.sleep(0.1)
            return self.ssh_channel.recv(size)
        if self.socket:
            return self.socket.recv(size)
        raise ConnectionError("No active Extron transport")

    def _close_socket(self) -> None:
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None

    def _close_ssh(self) -> None:
        if self.ssh_channel:
            try:
                self.ssh_channel.close()
            except Exception:
                pass
            self.ssh_channel = None
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except Exception:
                pass
            self.ssh_client = None

    @staticmethod
    def _is_ssh_banner(response: bytes) -> bool:
        return b'ssh-' in response.lower()

    def _emit_log(self, message: str) -> None:
        if self.log_callback:
            try:
                self.log_callback(message)
            except Exception:
                pass

    def _set_transport_timeout(self, timeout_value: float):
        previous_timeout = None
        try:
            if self.ssh_channel:
                previous_timeout = self.ssh_channel.gettimeout()
                self.ssh_channel.settimeout(timeout_value)
            elif self.socket:
                previous_timeout = self.socket.gettimeout()
                self.socket.settimeout(timeout_value)
        except Exception:
            previous_timeout = None
        return previous_timeout

    @staticmethod
    def _format_bytes(payload: bytes) -> str:
        return payload.decode('utf-8', errors='ignore').replace('\r', '\\r').replace('\n', '\\n')

    @staticmethod
    def _strip_command_echo(command: str, response_text: str) -> str:
        if not response_text:
            return response_text

        normalized_command = command.strip()
        if not normalized_command:
            return response_text.strip()

        lines = [line.strip() for line in response_text.splitlines()]
        while lines and not lines[0]:
            lines.pop(0)

        if lines and lines[0] == normalized_command:
            lines.pop(0)
            while lines and not lines[0]:
                lines.pop(0)

        return '\n'.join(lines).strip()
