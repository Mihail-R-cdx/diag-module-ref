import paramiko
import time
import re
from typing import Dict, Any, Optional, List
from core.exceptions import AuthenticationError, ConnectionError, CommandError


class PolycomRPG310Handler:
    """
    Обработчик для Polycom RealPresence Group 310
    Использует SSH подключение с интерактивной сессией
    """
    def __init__(self, ip_address: str, port: int = 22,
                 username: str = 'admin', password: str = '',
                 timeout: int = 10):
        """
        Инициализация обработчика
        
        Args:
            ip_address: IP адрес устройства
            port: Порт SSH (по умолчанию 22)
            username: Имя пользователя
            password: Пароль
            timeout: Таймаут подключения
        """
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        
        # SSH клиент
        self.client: Optional[paramiko.SSHClient] = None
        self.channel: Optional[paramiko.Channel] = None
        
        # Состояние аутентификации
        self.authenticated = False
        
        # Буфер для чтения данных
        self.buffer_size = 65535
        
        # Регулярные выражения для парсинга
        self.regex_patterns = {
            'firmware': re.compile(r'Software Version:\s+([\d.]+)'),
            'ip_address': re.compile(r'ipaddress\s+([\d\.]+)'),
            'volume': re.compile(r'volume\s+(\d+)'),
            'mic_mute': re.compile(r'mute near\s+(on|off)'),
            'camera_mute': re.compile(r'videomute near\s+(on|off)'),
            'selfview': re.compile(r'systemsetting selfview\s+(on|off|auto)'),
            'auto_answer': re.compile(r'autoanswer\s+(yes|no|donotdisturb)'),
            'call_state': re.compile(r'(callstate registered|active: call|ended: call|incoming: call)'),
            'lan_settings': re.compile(r'lanport\s+(\S+)'),
            'dual_monitor': re.compile(r'dualmonitor\s+(yes|no)'),
            'multipoint_mode': re.compile(r'mpmode\s+(\S+)'),
            'sleep_time': re.compile(r'sleeptime\s+(\d+)'),
            'transmit_level': re.compile(r'audiotransmitlevel\s+(-?\d+)'),
            'camera_source': re.compile(r'camera near source\s+(-?\d)'),
            'camera_tracking': re.compile(r'camera near tracking\s+(on|off|Voice|GroupFrame|FrameGroup)'),
            'uptime': re.compile(r'(\d+)\s+Days?,?\s*(\d+)\s+Hours?'),
        }

    def _log_command(self, message: str) -> None:
        logger = getattr(self, 'command_logger', None)
        if callable(logger):
            logger(message)
        
    def connect(self) -> bool:
        """
        Установка SSH соединения с устройством
        
        Returns:
            bool: True если подключение успешно
        
        Raises:
            ConnectionError: При ошибке подключения
            AuthenticationError: При ошибке аутентификации
        """
        try:
            print(f"PolycomRPG310Handler: Подключение к {self.ip_address}:{self.port}")
            self._log_command(f"[connect] ssh://{self.ip_address}:{self.port}")
            
            # Создаем SSH клиент
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Подключаемся
            self.client.connect(
                hostname=self.ip_address,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False
            )
            
            # Получаем интерактивную сессию
            self.channel = self.client.invoke_shell()
            time.sleep(2)  # Ждем приглашение
            
            # Очищаем буфер от приветствия
            self._clear_buffer()
            
            # Проверяем успешность подключения
            output = self._read_channel()
            if 'password failed' in output.lower():
                self.disconnect()
                raise AuthenticationError(f"Ошибка аутентификации для {self.username}")
            
            # Отправляем начальную команду для активации
            self.send_command('whoami')
            
            self.authenticated = True
            print("PolycomRPG310Handler: Подключение успешно")
            return True
            
        except paramiko.AuthenticationException as e:
            raise AuthenticationError(f"Ошибка аутентификации: {str(e)}")
        except paramiko.SSHException as e:
            raise ConnectionError(f"SSH ошибка: {str(e)}")
        except Exception as e:
            raise ConnectionError(f"Ошибка подключения: {str(e)}")
    
    def disconnect(self):
        """Закрытие соединения"""
        try:
            if self.channel:
                self.channel.close()
            if self.client:
                self.client.close()
            self.authenticated = False
            print("PolycomRPG310Handler: Соединение закрыто")
        except Exception as e:
            print(f"PolycomRPG310Handler: Ошибка при закрытии соединения: {e}")
    
    def is_connected(self) -> bool:
        """Проверка состояния соединения"""
        if self.client and self.channel:
            return not self.channel.closed
        return False
    
    def send_command(self, command: str, wait_time: float = 2.0) -> str:
        """
        Отправка команды и получение ответа
        
        Args:
            command: Команда для отправки
            wait_time: Время ожидания ответа в секундах
            
        Returns:
            str: Ответ устройства
            
        Raises:
            CommandError: При ошибке выполнения команды
        """
        if not self.is_connected():
            raise CommandError("Нет активного соединения")
        
        try:
            # Очищаем буфер перед отправкой
            self._clear_buffer()
            
            # Отправляем команду
            print(f"PolycomRPG310Handler: Отправка команды: {command.strip()}")
            self._log_command(f"[request] SSH {command.strip()}")
            self.channel.send(command + '\r')
            time.sleep(wait_time)
            
            # Читаем ответ
            output = self._read_channel()
            
            # Удаляем эхо команды из ответа
            lines = output.split('\n')
            if lines and command.strip() in lines[0]:
                output = '\n'.join(lines[1:])
            self._log_command(f"[response] {output.strip()}")
            
            return output.strip()
            
        except Exception as e:
            self._log_command(f"[error] {type(e).__name__} {command}: {str(e)}")
            raise CommandError(f"Ошибка выполнения команды '{command}': {str(e)}")
    
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение полного статуса устройства в формате, совместимом с GUI
        
        Returns:
            Dict: Статус устройства с ключами для парсера
        """
        status = {
            'model': 'Polycom RealPresence Group 310',
            'ip_address': self.ip_address
        }
        
        try:
            # Проверяем соединение
            if not self.is_connected():
                self.connect()
            
            # Получаем версию прошивки и серийный номер
            response = self.send_command('whoami', wait_time=3.0)
            print(f"WHOAMI response: {response}")  # Для отладки
            
            # Парсим версию
            version_match = self.regex_patterns['firmware'].search(response)
            if version_match:
                status['version'] = version_match.group(1)
            
            # Парсим серийный номер из whoami
            serial_match = re.search(r'Serial Number:\s*(\S+)', response, re.IGNORECASE)
            if not serial_match:
                serial_match = re.search(r'SN:\s*(\S+)', response, re.IGNORECASE)
            if not serial_match:
                serial_match = re.search(r'serial\s+(\S+)', response, re.IGNORECASE)
            
            if serial_match:
                status['serial_number'] = serial_match.group(1)
                print(f"Найден серийный номер: {status['serial_number']}")
            
            # Получаем статус звонка
            response = self.send_command('callstate get', wait_time=2.0)
            status['call_status'] = self._parse_call_status(response)
            
            # Получаем громкость
            response = self.send_command('volume get', wait_time=2.0)
            volume_match = self.regex_patterns['volume'].search(response)
            if volume_match:
                status['speaker_volume'] = int(volume_match.group(1))
                print(f"Громкость: {status['speaker_volume']}")
            
            # Получаем статус микрофона
            response = self.send_command('mute near get', wait_time=2.0)
            mic_match = self.regex_patterns['mic_mute'].search(response)
            if mic_match:
                status['mic_mute'] = mic_match.group(1)
            
            # Получаем время работы
            try:
                response = self.send_command('uptime get', wait_time=2.0)
                uptime = response.strip()
                if uptime and not uptime.startswith('Invalid') and not 'error' in uptime.lower():
                    status['uptime'] = uptime
                    print(f"Время работы: {status['uptime']}")
                else:
                    status['uptime'] = 'N/A'
            except Exception as e:
                print(f"Ошибка получения uptime: {e}")
                status['uptime'] = 'N/A'
            
            # Получаем статус SIP регистрации из команды status
            try:
                response = self.send_command('status', wait_time=3.0)
                print(f"STATUS response: {response}")  # Для отладки
                
                # Ищем строку с sipserver
                for line in response.split('\n'):
                    if 'sipserver' in line.lower():
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            sip_status = parts[1].lower()
                            status['sip_status'] = 'online' if sip_status == 'online' else 'offline'
                            print(f"Статус SIP: {status['sip_status']}")
                            break
            except Exception as e:
                print(f"Ошибка получения статуса SIP: {e}")
                status['sip_status'] = 'N/A'

            try:
                sip_server = self.verify_sip_server()
                if sip_server:
                    status['sip_server'] = sip_server
                    print(f"SIP сервер: {sip_server}")
            except Exception as e:
                print(f"Ошибка получения адреса SIP сервера: {e}")
            
            # Получаем информацию о вызове (опционально)
            try:
                response = self.send_command('callinfo all', wait_time=3.0)
                status['call_info'] = response
            except:
                pass
            
            print(f"PolycomRPG310Handler: Получен статус: {status}")
            
        except Exception as e:
            print(f"PolycomRPG310Handler: Ошибка получения статуса: {e}")
            status['error'] = str(e)
        
        return status  


    def get_device_info(self) -> Dict[str, Any]:
        """
        Получение базовой информации об устройстве
        
        Returns:
            Dict: Информация об устройстве
        """
        info = {
            'model': 'Polycom RealPresence Group 310',
            'ip_address': self.ip_address,
        }
        
        try:
            if not self.is_connected():
                self.connect()
            
            response = self.send_command('whoami', wait_time=3.0)
            version_match = self.regex_patterns['firmware'].search(response)
            if version_match:
                info['version'] = version_match.group(1)
                
        except Exception as e:
            print(f"PolycomRPG310Handler: Ошибка получения информации: {e}")
        
        return info
    
    def _clear_buffer(self):
        """Очистка буфера канала"""
        if self.channel and self.channel.recv_ready():
            self.channel.recv(self.buffer_size)
    
    def _read_channel(self) -> str:
        """Чтение данных из канала"""
        output = ""
        if self.channel and self.channel.recv_ready():
            try:
                data = self.channel.recv(self.buffer_size)
                output = data.decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"PolycomRPG310Handler: Ошибка чтения канала: {e}")
        return output
    
    def _parse_call_status(self, response: str) -> str:
        """Парсинг статуса звонка"""
        response_lower = response.lower()
        if 'active: call' in response_lower:
            return 'Active'
        elif 'incoming: call' in response_lower:
            return 'Incoming'
        elif 'callstate registered' in response_lower:
            return 'Registered'
        elif 'ended: call' in response_lower:
            return 'Ended'
        else:
            return 'No Call'
    
    def _get_uptime(self) -> str:
        """Получение времени работы (приблизительно)"""
        # У Polycom нет прямой команды uptime, используем приблизительные данные
        return "N/A"

    def get_volume_range(self):
        return 0, 50

    def set_presentation(self, value: str) -> bool:
        command_map = {
            'Start': 'vcbutton play 2',
            'Stop': 'vcbutton stop',
        }
        command = command_map.get(value)
        if not command:
            raise ValueError("Presentation value must be 'Start' or 'Stop'")

        if not self.is_connected():
            self.connect()

        response = self.send_command(command, wait_time=2.0)
        response_lower = response.lower()
        if 'invalid' in response_lower or 'error' in response_lower:
            return False
        return True

    def set_speaker_volume(self, value: int) -> bool:
        min_value, max_value = self.get_volume_range()
        if not min_value <= value <= max_value:
            raise ValueError(f"Speaker volume must be in range {min_value}..{max_value}")

        if not self.is_connected():
            self.connect()

        response = self.send_command(f'volume set {int(value)}', wait_time=2.0)
        response_lower = response.lower()
        if 'invalid' in response_lower or 'error' in response_lower:
            return False
        return True

    def get_speaker_volume(self) -> Optional[int]:
        if not self.is_connected():
            self.connect()

        response = self.send_command('volume get', wait_time=2.0)
        volume_match = self.regex_patterns['volume'].search(response)
        if not volume_match:
            return None
        return int(volume_match.group(1))

    def verify_sip_server(self) -> Optional[str]:
        """Получить адрес SIP registrar server."""
        if not self.is_connected():
            self.connect()

        response = self.send_command('systemsetting get sipregistrarserver', wait_time=2.0)
        match = re.search(r'systemsetting\s+sipregistrarserver\s+(.+)', response, re.IGNORECASE)
        if not match:
            return None

        value = match.group(1).strip()
        if not value or value.lower() in {'get', 'off', 'none'}:
            return None
        return value

    def set_sip_server(self, sip_address: str = "vcs-core-a.sber.ru") -> bool:
        """Установить адрес SIP registrar server."""
        if not self.is_connected():
            self.connect()

        response = self.send_command(f'systemsetting sipregistrarserver {sip_address}', wait_time=2.0)
        response_lower = response.lower()
        if 'invalid' in response_lower or 'error' in response_lower:
            return False

        time.sleep(0.5)
        return self.verify_sip_server() == sip_address


# Алиас для обратной совместимости
PolycomRPG310Handler = PolycomRPG310Handler
