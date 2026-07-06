# handlers/aten/pdu.py

import requests
import xml.etree.ElementTree as ET
import warnings
import time
from typing import Optional, List, Dict, Any
from core.base_handler import ProtocolHandler
from core.exceptions import AuthenticationError, ConnectionError

warnings.filterwarnings('ignore')


class AtenPDUHandler(ProtocolHandler):
    """Обработчик для PDU Aten (серия PE)"""
    
    def __init__(self, ip_address: str, port: int = 443, username: str = 'admin', 
                 password: str = 'admin', use_ssl: bool = True, verify_ssl: bool = False):
        super().__init__(ip_address, port)
        
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.verify_ssl = verify_ssl
        self.base_url = f"https://{ip_address}" if use_ssl else f"http://{ip_address}"
        self.session = requests.Session()
        self.connected = False
        self._outlet_names_loaded = False
        
        # Стандартные имена розеток (можно загружать из конфига)
        self.outlet_names = [
            "Контроллер", "Сенс. панель", "Кодек ВКС", "ТВ панели",
            "Видеоматрица", "Настольные устройства", "Аудиоматрица", "<пусто>"
        ]

    @staticmethod
    def _timestamp_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def _xml_text(response_text: str, tag: str) -> str:
        root = ET.fromstring(response_text)
        node = root.find(tag)
        return "" if node is None or node.text is None else node.text

    def _fetch_outlet_names_https(self, expected_count: int = 0) -> List[str]:
        """Read outlet names through the ATEN web HTTPS XML endpoints."""
        sid = ""
        headers = {
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.base_url}/mainpage.html?time={self._timestamp_ms()}",
        }
        names_session = requests.Session()

        try:
            login = names_session.post(
                f"{self.base_url}/xml/login_result.xml",
                params={"timeStamp": self._timestamp_ms()},
                data={"username": self.username, "password": self.password},
                headers=headers,
                verify=self.verify_ssl,
                timeout=10,
            )
            login.raise_for_status()

            login_validate = self._xml_text(login.text, "LoginValidate")
            sid = self._xml_text(login.text, "SID")
            outlet_auth = self._xml_text(login.text, "OutletAuth")
            if login_validate != "0" or not sid:
                raise AuthenticationError(
                    f"ATEN HTTPS login failed: LoginValidate={login_validate!r}, SID={sid!r}"
                )

            outlet_count = expected_count or len([item for item in outlet_auth.split(";") if item != ""])
            outlets = names_session.get(
                f"{self.base_url}/xml/protected/connections_dynamic_outlet_name.xml",
                params={"Name": self.username, "timeStamp": self._timestamp_ms()},
                headers={
                    **headers,
                    "Authorization": sid,
                    "Accept": "application/xml, text/xml, */*; q=0.01",
                },
                verify=self.verify_ssl,
                timeout=10,
            )
            outlets.raise_for_status()

            outlet_name_text = self._xml_text(outlets.text, "outletname")
            names = outlet_name_text.split(";") if outlet_name_text else []
            if outlet_count:
                names = (names + [""] * outlet_count)[:outlet_count]
            return names
        finally:
            if sid:
                try:
                    names_session.get(
                        f"{self.base_url}/cgi/protected/logout.cgi",
                        params={"Name": self.username, "timeStamp": self._timestamp_ms()},
                        headers={"Authorization": sid},
                        verify=self.verify_ssl,
                        timeout=10,
                    )
                except requests.exceptions.RequestException:
                    pass
            names_session.close()

    def _refresh_outlet_names_https(self, expected_count: int = 0) -> None:
        if self._outlet_names_loaded:
            return

        try:
            names = self._fetch_outlet_names_https(expected_count)
        except Exception as e:
            print(f"DEBUG: Failed to load outlet names over HTTPS: {e}")
            return

        if not names:
            return

        for idx, name in enumerate(names):
            display_name = name.strip() if name else "<без названия>"
            if idx >= len(self.outlet_names):
                self.outlet_names.append(display_name)
            else:
                self.outlet_names[idx] = display_name
        self._outlet_names_loaded = True
    
    def connect(self) -> bool:
        """Подключение к PDU (проверка доступности)"""
        try:
            # Пробуем получить статус устройства для проверки подключения
            resp = self._api_request("GET", "/api/device/relay")
            
            if resp is None:
                self.connected = False
                return False

            if resp.status_code in (401, 403):
                raise AuthenticationError("Авторизация неуспешна")

            response_text = resp.text.lower() if resp.text else ""
            is_login_page = any(
                marker in response_text
                for marker in ("login", "authentication", "session expired")
            )

            if resp.status_code == 200 and not is_login_page:
                self.connected = True
                return True
            if resp.status_code == 200 and is_login_page:
                raise AuthenticationError("Авторизация неуспешна")
            else:
                self.connected = False
                return False
                
        except AuthenticationError:
            self.connected = False
            raise
        except Exception as e:
            self.connected = False
            raise ConnectionError(f"Ошибка подключения к PDU: {str(e)}")
    
    def disconnect(self):
        """Отключение от PDU"""
        self.session.close()
        self.connected = False
    

    def _api_request(self, method: str, endpoint: str, 
                     params: Optional[Dict] = None, 
                     data: Optional[Dict] = None) -> Optional[requests.Response]:
        """Универсальная функция для запросов к API Aten PDU"""
        
        url = f"{self.base_url}{endpoint}"
        print(f"DEBUG: Request URL: {url}")  # Отладка
        
        # Параметры авторизации
        auth_params = {"usr": self.username, "pwd": self.password}
        
        if params:
            auth_params.update(params)
        
        print(f"DEBUG: Auth params: usr={self.username}, pwd={'*' * len(self.password)}")  # Отладка
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/xml, text/xml, */*",
        }
        
        try:
            if method.upper() == "GET":
                print(f"DEBUG: Making GET request with params: {auth_params}")  # Отладка
                resp = self.session.get(url, params=auth_params, headers=headers, 
                                        verify=self.verify_ssl, timeout=10)
            else:
                post_data = auth_params if data is None else {**auth_params, **data}
                print(f"DEBUG: Making POST request with data: {post_data}")  # Отладка
                resp = self.session.post(url, data=post_data, headers=headers, 
                                         verify=self.verify_ssl, timeout=10)
            
            print(f"DEBUG: Response status: {resp.status_code}")  # Отладка
            return resp
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: Request exception: {e}")  # Отладка
            return None    

    def authenticate(self, passwords_list: List[str]) -> bool:
        """Попытка аутентификации с перебором паролей"""
        
        for pwd in passwords_list:
            self.password = pwd
            resp = self._api_request("GET", "/api/device/relay")
            
            if resp and resp.status_code == 200 and resp.text.strip():
                # Проверяем, что это не страница логина
                is_login_page = any(marker in resp.text.lower() for marker in 
                                   ['login', 'authentication', 'session expired'])
                
                if not is_login_page:
                    self.connected = True
                    return True
        
        self.connected = False
        return False
    
    def get_device_info(self) -> Dict[str, Any]:
        """Получение информации об устройстве"""
        if not self.connected:
            raise ConnectionError("Нет подключения к PDU")
        
        info = {
            'model': 'PE8208AV',
            'manufacturer': 'Aten',
            'ip_address': self.ip_address
        }
        
        # Пробуем получить дополнительную информацию
        resp = self._api_request("GET", "/api/device/info")
        if resp and resp.status_code == 200:
            # Парсим информацию, если API предоставляет
            pass
        
        return info
    

    
    def get_outlets_status(self) -> List[Dict[str, Any]]:
        """Получение статуса всех розеток"""
        if not self.connected:
            raise ConnectionError("Нет подключения к PDU")
        
        print(f"DEBUG: Getting outlets status...")
        resp = self._api_request("GET", "/api/device/relay")
        
        if resp and resp.status_code == 200:
            print(f"DEBUG: Response received, length: {len(resp.text)}")
            print(f"DEBUG: First 200 chars: {resp.text[:200]}")
            
            # Парсим XML ответ
            outlets = self._parse_relay_xml(resp.text)
            print(f"DEBUG: Parsed {len(outlets)} outlets")

            self._refresh_outlet_names_https(len(outlets))
            
            # Добавляем имена розеток
            for i, outlet in enumerate(outlets):
                idx = outlet['number'] - 1
                if 0 <= idx < len(self.outlet_names):
                    outlet['name'] = self.outlet_names[idx]
                print(f"DEBUG: Outlet {outlet['number']}: {outlet['status']} - {outlet['name']}")
            
            return outlets
        else:
            print(f"DEBUG: Request failed. Status: {resp.status_code if resp else 'No response'}")
            return []  # Возвращаем пустой список вместо исключения

        
    def _parse_relay_xml(self, xml_text: str) -> List[Dict[str, Any]]:
        """Парсинг XML с состоянием реле (специальный формат Aten)"""
        outlets = []
        try:
            import re
            print(f"DEBUG: Parsing XML: {xml_text}")  # Отладка
            
            # Используем регулярное выражение для поиска всех тегов с числами
            # Ищем паттерн <число>значение<число>
            pattern = r'<(\d+)>(.*?)<\1>'
            matches = re.findall(pattern, xml_text, re.DOTALL)
            
            print(f"DEBUG: Regex matches: {matches}")  # Отладка
            
            for match in matches:
                outlet_num = int(match[0])
                status = match[1].strip().lower()
                print(f"DEBUG: Found outlet {outlet_num}: {status}")  # Отладка
                
                outlets.append({
                    'number': outlet_num,
                    'status': status,
                    'name': f"Розетка {outlet_num}"
                })
            
            # Если не нашли через regex, пробуем другой подход
            if not outlets:
                print("DEBUG: Trying alternative parsing...")
                # Разбиваем на строки и ищем вручную
                lines = xml_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and line[0] == '<' and line[-1] == '>' and line[1] != '/':
                        # Ищем закрывающий тег с тем же номером
                        for i in range(1, 9):  # для розеток 1-8
                            tag = f"<{i:02d}>"
                            if line.startswith(tag):
                                value = line[len(tag):-len(tag)]
                                outlets.append({
                                    'number': i,
                                    'status': value.lower(),
                                    'name': f"Розетка {i}"
                                })
                                break
            
        except Exception as e:
            print(f"DEBUG: Error in parsing: {e}")
        
        # Сортируем по номеру
        outlets.sort(key=lambda x: x['number'])
        print(f"DEBUG: Final outlets: {outlets}")  # Отладка
        return outlets

    def set_outlet_state(self, outlet_number: int, command: str) -> bool:
        """
        Управление розеткой
        
        Args:
            outlet_number: номер розетки (1-8)
            command: 'on', 'off', 'reboot'
        
        Returns:
            bool: успех операции
        """
        if not self.connected:
            raise ConnectionError("Нет подключения к PDU")
        
        # Проверяем допустимость команды
        valid_commands = ['on', 'off', 'reboot', 'on_immediate', 'off_immediate']
        if command not in valid_commands:
            raise ValueError(f"Недопустимая команда. Используйте: {valid_commands}")
        
        data = {"index": outlet_number, "method": command}
        resp = self._api_request("POST", "/api/outlet/relay", data=data)
        
        return resp is not None and resp.status_code == 200
    
    def turn_on(self, outlet_number: int) -> bool:
        """Включить розетку"""
        return self.set_outlet_state(outlet_number, "on")
    
    def turn_off(self, outlet_number: int) -> bool:
        """Выключить розетку"""
        return self.set_outlet_state(outlet_number, "off")
    
    def reboot(self, outlet_number: int) -> bool:
        """Перезагрузить розетку"""
        return self.set_outlet_state(outlet_number, "reboot")
    
    def get_status(self) -> Dict[str, Any]:
        """Получение полного статуса (для совместимости с базовым классом)"""
        outlets = self.get_outlets_status()
        device_info = self.get_device_info()
        
        return {
            'device_info': device_info,
            'outlets': outlets,
            'connected': self.connected
        }
    
    def send_command(self, command: str, params: Optional[Dict] = None) -> Any:
        """Отправка произвольной команды"""
        if command == "get_outlets":
            return self.get_outlets_status()
        elif command == "set_outlet":
            if params and 'outlet' in params and 'action' in params:
                return self.set_outlet_state(params['outlet'], params['action'])
        elif command == "turn_on":
            if params and 'outlet' in params:
                return self.turn_on(params['outlet'])
        elif command == "turn_off":
            if params and 'outlet' in params:
                return self.turn_off(params['outlet'])
        elif command == "reboot":
            if params and 'outlet' in params:
                return self.reboot(params['outlet'])
        
        raise NotImplementedError(f"Команда {command} не поддерживается")
