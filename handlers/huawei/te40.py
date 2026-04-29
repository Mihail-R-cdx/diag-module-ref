import requests
import json
import ssl
import urllib.request
import urllib.error
import urllib.parse
import re
import random
import time
from typing import Dict, Any, Optional
from core.base_handler import BaseHuaweiCodecHandler
from core.exceptions import AuthenticationError, ConnectionError

class HuaweiTE40Handler(BaseHuaweiCodecHandler):
    """Обработчик для Huawei TE-40 с рабочей реализацией подключения"""
    
    def __init__(self, ip_address: str, port: int = 443,
                 username: str = 'api', password: str = '',
                 use_ssl: bool = True, verify_ssl: bool = False):
        super().__init__(ip_address, port, username, password, use_ssl, verify_ssl)
        self.device_model = 'Huawei TE-40'
        self.session_id = None
        self.csrf_token = None
        self.opener = None
        self._connected = False
        
        # Настройка SSL контекста
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        self.context.check_hostname = False
        self.context.verify_mode = ssl.CERT_NONE
        self.context.set_ciphers('DEFAULT@SECLEVEL=1')
        
        # Настройка HTTP Basic аутентификации
        protocol = 'https' if use_ssl else 'http'
        self.base_url = f"{protocol}://{ip_address}:{port}"
        
        password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(
            None,
            f"{self.base_url}/",
            username,
            password
        )
        
        # Создаем opener с аутентификацией
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPBasicAuthHandler(password_mgr),
            urllib.request.HTTPSHandler(context=self.context),
            urllib.request.HTTPCookieProcessor()
        )

    def _log_command(self, message: str) -> None:
        logger = getattr(self, 'command_logger', None)
        if callable(logger):
            logger(message)

    def _is_authentication_response(self, result: Dict[str, Any]) -> bool:
        if not isinstance(result, dict):
            return False

        auth_codes = {401, 403, 100666780, 16781315}
        auth_code_strings = {str(code) for code in auth_codes}
        values = [result.get('error'), result.get('code'), result.get('id')]

        for key in ('error', 'exception'):
            details = result.get(key)
            if isinstance(details, dict):
                values.extend([details.get('id'), details.get('code')])

        if any(value in auth_codes or str(value) in auth_code_strings for value in values):
            return True

        result_text = str(result).lower()
        return "authentication" in result_text or "auth" in result_text
    
    def connect(self) -> bool:
        """Установка соединения с кодеком Huawei TE-40"""
        try:
            print(f"Подключаюсь к {self.base_url}/")
            
            # 1. Получаем Session ID
            session_url = f"{self.base_url}/action.cgi?ActionID=WEB_RequestSessionIDAPI"
            session_request = urllib.request.Request(session_url, method='POST')
            self._log_command(f"[request] POST {session_url}")
            
            try:
                session_response = self.opener.open(session_request, timeout=10)
                session_response_text = session_response.read().decode('utf-8')
                self._log_command(f"[response] 200 {session_response_text}")
                print(f"Ответ Session ID: {session_response_text}")
                
                result = json.loads(session_response_text)
                
                if result.get('success') == 1:
                    data = result.get('data', '{}')
                    if isinstance(data, str):
                        try:
                            data_json = json.loads(data)
                            self.session_id = data_json.get('acSessionId')
                        except json.JSONDecodeError:
                            self.session_id = result.get('data', {}).get('acSessionId')
                    elif isinstance(data, dict):
                        self.session_id = data.get('acSessionId')
                    
                    print(f"✓ Session ID получен: {self.session_id}")
                else:
                    print(f"✗ Session ID не получен: {result}")
                    # Проверяем, не ошибка ли это аутентификации
                    if self._is_authentication_response(result):
                        raise AuthenticationError(f"Ошибка аутентификации: {result.get('message', 'Неверные учетные данные')}")
                    return False
                    
            except urllib.error.HTTPError as e:
                if e.code == 401 or e.code == 403:
                    raise AuthenticationError(f"HTTP {e.code}: Ошибка аутентификации")
                raise ConnectionError(f"HTTP ошибка: {e.code}")
            except Exception as e:
                if "authentication" in str(e).lower() or "401" in str(e):
                    raise AuthenticationError(f"Ошибка аутентификации: {str(e)}")
                raise ConnectionError(f"Ошибка подключения: {str(e)}")
            
            # 2. Получаем CSRF Token
            print("Получаю CSRF Token...")
            token_url = f"{self.base_url}/action.cgi?ActionID=WEB_RequestCertificateAPI"
            
            data = json.dumps({
                "user": self.credentials.get('username', 'api'),
                "password": self.credentials.get('password', '')
            }).encode('utf-8')
            self._log_command(f"[request] POST {token_url}")
            self._log_command(f"[payload] {data.decode('utf-8', errors='ignore')}")
            
            token_request = urllib.request.Request(
                token_url,
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Sessionid': self.session_id
                },
                method='POST'
            )
            
            try:
                token_response = self.opener.open(token_request, timeout=10)
                token_response_text = token_response.read().decode('utf-8')
                self._log_command(f"[response] 200 {token_response_text}")
                print(f"Ответ CSRF Token: {token_response_text}")
                
                token_result = json.loads(token_response_text)
                
                if token_result.get('success') == 1:
                    token_data = token_result.get('data', '')
                    
                    if isinstance(token_data, str):
                        if token_data:
                            try:
                                data_json = json.loads(token_data)
                                self.csrf_token = data_json.get('acCSRFToken')
                            except json.JSONDecodeError:
                                match = re.search(r'acCSRFToken["\']?:\s*["\']?([^"\']+)["\']?', token_data)
                                if match:
                                    self.csrf_token = match.group(1)
                                else:
                                    self.csrf_token = token_data
                    elif isinstance(token_data, dict):
                        self.csrf_token = token_data.get('acCSRFToken')
                    
                    if self.csrf_token:
                        print(f"✓ CSRF Token получен: {self.csrf_token}")
                    else:
                        print("⚠ CSRF Token не получен (пустой ответ)")
                else:
                    print(f"✗ CSRF Token запрос неуспешен: {token_result}")
                    # Проверяем, не ошибка ли это аутентификации
                    if self._is_authentication_response(token_result):
                        raise AuthenticationError(f"Ошибка аутентификации при получении CSRF токена")
                    self.csrf_token = None
                    
            except urllib.error.HTTPError as e:
                if e.code == 401 or e.code == 403:
                    raise AuthenticationError(f"HTTP {e.code}: Ошибка аутентификации при получении CSRF токена")
                raise ConnectionError(f"HTTP ошибка при получении CSRF токена: {e.code}")
            except Exception as e:
                if "authentication" in str(e).lower() or "401" in str(e):
                    raise AuthenticationError(f"Ошибка аутентификации при получении CSRF токена: {str(e)}")
                print(f"Ошибка получения CSRF Token: {type(e).__name__}: {str(e)}")
                self.csrf_token = None
            
            # 3. Проверяем подключение
            if self.session_id:
                self._connected = True
                print("✓ Подключение установлено")
                return True
            else:
                print("✗ Не удалось установить подключение")
                return False
                
        except AuthenticationError:
            # Пробрасываем AuthenticationError дальше
            raise
        except Exception as e:
            print(f"Ошибка подключения: {type(e).__name__}: {str(e)}")
            raise ConnectionError(f"Ошибка подключения: {str(e)}")


    
    def disconnect(self) -> None:
        """Разорвать соединение"""
        self._connected = False
        self.session_id = None
        self.csrf_token = None
    
    def send_command(self, command: str, data: Optional[Dict] = None) -> Dict:
        """Отправить команду устройству"""
        if not self.is_connected() or not self.session_id:
            if not self.connect():
                return {'success': False, 'error': 'Not connected'}
        
        try:
            # Маппинг команд на ActionID
            command_map = {
                'get_version': 'WEB_GetVersionInfoAPI',
                'get_call_status': 'WEB_GetMailboxDataAPI',
                'get_sip_status': 'WEB_GetLineStateInfoAPI',
                'get_audio_status': 'WEB_InitAudioCtrlParamsAPI',
                'get_presentation': 'WEB_IsSendAuxStreamAPI',
                'get_system_sleep': 'WEB_IsSystemSleepAPI',
                'get_camera_status': 'WEB_GetLocalCameraList',
                'get_mac': 'WEB_GetSystemMacAddrAPI',
                'get_system_info': 'WEB_GetSystemInfoAPI',
                'get_network': 'WEB_GetNetworkInfoAPI',
                'get_video': 'WEB_GetVideoInfoAPI',
            }
            
            action = command_map.get(command, command)
            
            # ИСПРАВЛЕНО: правильный формат URL - без ? перед rmd
            import random
            rmd = random.random()
            url = f"{self.base_url}/action.cgi?ActionID={action}&rmd={rmd}"
            
            print(f"Отправка команды {command} на {url}")
            
            # Подготавливаем заголовки
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Sessionid': self.session_id
            }
            
            # Подготавливаем данные
            request_data = data or {}
            if self.csrf_token and 'acCSRFToken' not in request_data:
                request_data['acCSRFToken'] = self.csrf_token
            self._log_command(f"[request] {'POST' if request_data else 'GET'} {url}")
            if request_data:
                self._log_command(f"[payload] {json.dumps(request_data, ensure_ascii=False)}")
            
            # Отправляем запрос
            if request_data:
                data_bytes = json.dumps(request_data).encode('utf-8')
                request = urllib.request.Request(
                    url,
                    data=data_bytes,
                    headers=headers,
                    method='POST'
                )
            else:
                request = urllib.request.Request(
                    url,
                    headers=headers,
                    method='GET'
                )
            
            response = self.opener.open(request, timeout=10)
            response_text = response.read().decode('utf-8')
            self._log_command(f"[response] 200 {response_text}")
            print(f"Ответ {command}: {response_text[:200]}...")
            
            try:
                result = json.loads(response_text)
                return result
            except json.JSONDecodeError:
                print(f"Не JSON ответ: {response_text}")
                return {}
            
        except Exception as e:
            self._log_command(f"[error] {type(e).__name__} {command}: {str(e)}")
            print(f"Ошибка выполнения команды {command}: {e}")
            return {}

    def get_status(self) -> Dict[str, Any]:
        """Получение полного статуса устройства"""
        status = {}
        
        try:
            print("Начинаю сбор статуса...")
            
            # 1. Получаем информацию о версии
            print("Запрос версии...")
            result = self.send_command('get_version')
            if result and result.get('success') == 1:
                data = result.get('data', '{}')
                processed_data = self._parse_json_data(data)
                if processed_data:
                    soft_version = processed_data.get('softVersion', 'Unknown')
                    soft_version = soft_version.replace('TEX0 ', '').strip()
                    status['version'] = soft_version
                    status['model'] = processed_data.get('model', 'Huawei TE-40')
                    status['serial_number'] = processed_data.get('lisence', 'Unknown')
                    mic_version = processed_data.get('micVersion')
                    status['mic_version'] = mic_version
                    status['mic_connection_status'] = (
                        'Микрофон не подключён'
                        if mic_version in (None, [], '', 'N/A')
                        else 'Подключён'
                    )
                    if status['mic_connection_status'] == 'Микрофон не подключён':
                        status['mic_volume'] = 'Микрофон не подключён'
                    print(f"Версия: {soft_version}")
            
            # 2. Получаем MAC адрес
            print("Запрос MAC...")
            mac_result = self.send_command('get_mac')
            if mac_result and mac_result.get('success') == 1:
                mac_data = self._parse_json_data(mac_result.get('data', '{}'))
                if mac_data:
                    mac_address = mac_data.get('system_wanMAC_addr') or mac_data.get('system_lanMAC_addr')
                    if mac_address:
                        status['mac_address'] = mac_address
                        print(f"MAC: {mac_address}")
            
            # 3. Получаем SIP информацию
            print("Запрос SIP...")
            sip_result = self.send_command('get_sip_status')
            if sip_result and sip_result.get('success') == 1:
                sip_data = self._parse_json_data(sip_result.get('data', '{}'))
                if sip_data:
                    sip_status = sip_data.get('sipStatusTxStr', 'EMPTY')
                    status['sip_status'] = 'On' if sip_status == 'SIP_STATE_OK' else 'Off'
                    status['sip_server'] = sip_data.get('sipAddr', 'Unknown')
                    sip_number = sip_data.get('sipNumber', '')
                    if sip_number:
                        status['sip_number'] = sip_number
                    
                    run_day = int(sip_data.get('runDay', 0))
                    run_hour = int(sip_data.get('runHour', 0))
                    run_min = int(sip_data.get('runMin', 0))
                    
                    uptime_parts = []
                    if run_day > 0:
                        uptime_parts.append(f"{run_day} дней")
                    if run_hour > 0:
                        uptime_parts.append(f"{run_hour} часов")
                    if run_min > 0:
                        uptime_parts.append(f"{run_min} минут")
                    
                    status['uptime'] = ' '.join(uptime_parts) if uptime_parts else '0 минут'
                    print(f"SIP статус: {status.get('sip_status')}")
            
            # 4. Получаем статус звонка (с таймаутом)
            print("Запрос статуса звонка...")
            try:
                call_result = self.send_command('get_call_status')
                if call_result and call_result.get('success') == 1:
                    call_data = self._parse_json_data(call_result.get('data', '{}'))
                    if call_data:
                        state = call_data.get('state', {})
                        if isinstance(state, dict):
                            call_state = state.get('callstate', 0)
                            call_status_map = {0: 'No Call', 1: 'Disconnected', 2: 'Calling'}
                            status['call_status'] = call_status_map.get(call_state, 'Unknown')
                            print(f"Статус звонка: {status.get('call_status')}")
            except Exception as e:
                print(f"Ошибка получения статуса звонка: {e}")
            
            # 5. Получаем аудио статус
            print("Запрос аудио статуса...")
            try:
                audio_result = self.send_command('get_audio_status')
                if audio_result and audio_result.get('success') == 1:
                    audio_data = self._parse_json_data(audio_result.get('data', '{}'))
                    if audio_data:
                        status['mic_mute'] = 'On' if audio_data.get('MicSwitch', 0) == 0 else 'Off'
                        status['speaker_mute'] = 'On' if audio_data.get('SpeakerSwitch', 0) == 1 else 'Off'
                        status['speaker_volume'] = audio_data.get('speakerValue', 0)
                        if (
                            status.get('mic_connection_status') != 'Микрофон не подключён'
                            and 'micValue' in audio_data
                        ):
                            status['mic_volume'] = audio_data.get('micValue')
                        print(f"Аудио статус получен")
            except Exception as e:
                print(f"Ошибка получения аудио статуса: {e}")
            
            # 6. Получаем статус презентации
            print("Запрос статуса презентации...")
            try:
                pres_result = self.send_command('get_presentation')
                if pres_result and pres_result.get('success') == 1:
                    pres_data = self._parse_json_data(pres_result.get('data', '{}'))
                    if pres_data:
                        presentation = pres_data.get('isSendAux', 'auxClose')
                        status['presentation'] = 'Start' if presentation == 'auxOpen' else 'Stop'
                        print(f"Презентация: {status.get('presentation')}")
            except Exception as e:
                print(f"Ошибка получения статуса презентации: {e}")
            
            # 7. Получаем статус камеры
            print("Запрос статуса камеры...")
            try:
                camera_result = self.send_command('get_camera_status')
                if camera_result and camera_result.get('success') == 1:
                    camera_data = self._parse_json_data(camera_result.get('data', '{}'))
                    if camera_data:
                        item_list = camera_data.get('itemList', [])
                        if isinstance(item_list, list) and len(item_list) >= 2:
                            cam1_status = 'On' if item_list[0].get('itemState', 0) == 1 else 'Off'
                            cam2_status = 'On' if item_list[1].get('itemState', 0) == 1 else 'Off'
                            status['camera_status'] = f"{cam1_status}{cam2_status}"
                            print(f"Статус камеры: {status.get('camera_status')}")
            except Exception as e:
                print(f"Ошибка получения статуса камеры: {e}")
            
            print(f"Сбор статуса завершен. Получено полей: {len(status)}")
            
        except Exception as e:
            print(f"Ошибка получения статуса: {e}")
            import traceback
            traceback.print_exc()
        
        return status    


    def _parse_json_data(self, data):
        """Помощник для парсинга JSON данных"""
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return {}
        elif isinstance(data, dict):
            return data
        else:
            return {}
    
    # Реализация абстрактных методов
    def get_device_info(self) -> Dict[str, str]:
        """Получить информацию об устройстве"""
        status = self.get_status()
        return {
            'model': status.get('model', 'Huawei TE-40'),
            'serial': status.get('serial_number', 'N/A'),
            'version': status.get('version', 'N/A'),
            'mac': status.get('mac_address', 'N/A'),
            'ip': self.ip_address
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Получить системную информацию"""
        status = self.get_status()
        return {
            'uptime': status.get('uptime', 'N/A'),
            'temperature': 'N/A'  # TE-40 не предоставляет температуру
        }
    
    def get_call_status(self) -> Dict[str, Any]:
        """Получить статус вызова"""
        status = self.get_status()
        return {
            'status': status.get('call_status', 'idle'),
            'type': 'none',
            'remote_number': '',
            'remote_name': '',
            'duration': 0,
            'protocol': '',
            'bandwidth': 0
        }
    
    def get_network_status(self) -> Dict[str, Any]:
        """Получить статус сети"""
        status = self.get_status()
        return {
            'ip': self.ip_address,
            'gateway': 'N/A',
            'dns': 'N/A',
            'bandwidth': 'N/A'
        }
    
    def get_audio_status(self) -> Dict[str, Any]:
        """Получить статус аудио"""
        status = self.get_status()
        return {
            'volume': 0,
            'mute': status.get('mic_mute', 'Off'),
            'speaker_volume': status.get('speaker_volume', 0),
            'speaker_mute': status.get('speaker_mute', 'Off'),
            'microphone_volume': status.get('mic_volume')
        }
    
    def get_video_status(self) -> Dict[str, Any]:
        """Получить статус видео"""
        status = self.get_status()
        return {
            'presentation': status.get('presentation', 'off'),
            'camera': status.get('camera_status', 'OffOff'),
            'format': '',
            'resolution': ''
        }
    
    def get_mac_address(self) -> str:
        """Получение MAC адреса"""
        device_info = self.get_device_info()
        return device_info.get('mac', 'N/A')
    
    
    def set_sip_server(self, sip_address="vcs-core-a.sber.ru") -> bool:
        """
        Установка адреса SIP сервера на кодеке Huawei TE-40
        """
        print(f"\n=== set_sip_server called ===")
        print(f"IP: {self.ip_address}")
        print(f"Session ID: {self.session_id}")
        print(f"CSRF Token: {self.csrf_token}")
        print(f"SIP Address: {sip_address}")
        
        if not self.is_connected():
            print("Not connected, trying to connect...")
            if not self.connect():
                print("Failed to connect")
                return False
        
        try:
            # Формируем данные для установки SIP сервера
            data = {
                "CfgItemInt": [],
                "CfgItemString": [
                    {
                        "CfgItemID": "sipserv_addr",
                        "CfgItemInfo": sip_address
                    }
                ]
            }
            
            # Добавляем CSRF токен, если есть
            if self.csrf_token:
                data["acCSRFToken"] = self.csrf_token
                print(f"CSRF Token added to data: {self.csrf_token}")
            else:
                print("No CSRF token available")
            
            print(f"Request data: {json.dumps(data, indent=2)}")
            
            # Отправляем команду сохранения конфигурации
            url = f"{self.base_url}/action.cgi?ActionID=WEB_SaveCfgParamAPI&rmd={random.random()}"
            print(f"Request URL: {url}")
            
            headers = {
                'Content-Type': 'application/json',
                'Sessionid': self.session_id
            }
            print(f"Headers: {headers}")
            
            data_bytes = json.dumps(data).encode('utf-8')
            print(f"Data bytes length: {len(data_bytes)}")
            
            request = urllib.request.Request(
                url,
                data=data_bytes,
                headers=headers,
                method='POST'
            )
            
            print("Sending request...")
            response = self.opener.open(request, timeout=10)
            response_text = response.read().decode('utf-8')
            print(f"Response: {response_text}")
            
            result = json.loads(response_text)
            print(f"Parsed result: {result}")
            
            if result and result.get('success') == 1:
                print(f"✓ SIP server set successfully: {sip_address}")
                return True
            else:
                print(f"✗ Failed to set SIP server: {result}")
                return False
                
        except Exception as e:
            print(f"Error setting SIP server: {e}")
            import traceback
            traceback.print_exc()
            return False  
    
    
    
    def verify_sip_server(self) -> str:
        """
        Проверка текущего адреса SIP сервера
        
        Returns:
            str: Текущий адрес SIP сервера или None в случае ошибки
        """
        if not self.is_connected():
            if not self.connect():
                return None
        
        try:
            url = f"{self.base_url}/action.cgi?ActionID=WEB_GetCfgParamAPI&rmd={random.random()}"
            data = {
                "CfgIDString": ["sipserv_addr"]
            }
            if self.csrf_token:
                data["acCSRFToken"] = self.csrf_token
            
            headers = {
                'Content-Type': 'application/json',
                'Sessionid': self.session_id
            }
            
            request = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            response = self.opener.open(request, timeout=10)
            response_text = response.read().decode('utf-8')
            result = json.loads(response_text)
            
            if result.get('success') == 1:
                data_field = result.get('data')
                
                # data может быть строкой или словарем
                if isinstance(data_field, str):
                    try:
                        data_field = json.loads(data_field)
                    except:
                        return data_field
                
                if isinstance(data_field, dict):
                    return data_field.get('sipserv_addr', 'Не найден')
                else:
                    return str(data_field)
            else:
                return None
                
        except Exception as e:
            print(f"Ошибка проверки SIP сервера: {e}")
            return None

    def get_volume_range(self):
        return 0, 21

    def get_sleep_mode(self) -> str:
        """Получить режим сна."""
        result = self.send_command('get_system_sleep')
        if not result or result.get('success') != 1:
            return 'Off'

        data = result.get('data', {})
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return 'Off'

        if not isinstance(data, dict):
            return 'Off'

        return 'On' if data.get('isSystemSleep') == 'sleep' else 'Off'

    def wake_up(self) -> bool:
        """Разбудить устройство из режима сна."""
        payload = {
            "acCSRFToken": self.csrf_token or "",
        }
        result = self.send_command('WEB_SystemWakeUpAPI', payload)
        return bool(result and result.get('success') == 1)

    def get_presentation_status(self) -> str:
        """Получить текущий статус презентации."""
        result = self.send_command('get_presentation')
        if not result or result.get('success') != 1:
            return 'Stop'

        data = result.get('data', {})
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return 'Stop'

        if not isinstance(data, dict):
            return 'Stop'

        return 'Start' if data.get('isSendAux') == 'auxOpen' else 'Stop'

    def set_presentation(self, value: str) -> bool:
        command_map = {
            'Start': 'WEB_StartSendAuxStreamAPI',
            'Stop': 'WEB_StopSendAuxStreamAPI',
        }
        command = command_map.get(value)
        if not command:
            raise ValueError("Presentation value must be 'Start' or 'Stop'")

        payload = {
            "acCSRFToken": self.csrf_token or "",
        }
        result = self.send_command(command, payload)
        if result and result.get('success') == 1:
            return True

        # Некоторые TE40 меняют статус, но не возвращают success=1 на set-команду.
        time.sleep(0.5)
        return self.get_presentation_status() == value

    def set_speaker_volume(self, value: int) -> bool:
        min_value, max_value = self.get_volume_range()
        if not min_value <= value <= max_value:
            raise ValueError(f"Speaker volume must be in range {min_value}..{max_value}")

        payload = {
            "speaker": 1,
            "speakerValue": int(value),
            "acCSRFToken": self.csrf_token or "",
        }
        result = self.send_command('WEB_SetSpeakVolumeAPI', payload)
        if result and result.get('success') == 1:
            return True

        time.sleep(0.5)
        return self.get_speaker_volume() == int(value)

    def get_speaker_volume(self) -> Optional[int]:
        result = self.send_command('get_audio_status')
        if not result or result.get('success') != 1:
            return None

        data = self._parse_json_data(result.get('data', {}))
        volume = data.get('speakerValue')
        try:
            return int(volume)
        except (TypeError, ValueError):
            return None

    def set_microphone_mute(self, muted: bool) -> bool:
        action = 'WEB_CloseMicAPI' if muted else 'WEB_OpenMicAPI'
        payload = {
            "acCSRFToken": self.csrf_token or "",
        }
        result = self.send_command(action, payload)
        if result and result.get('success') == 1:
            return True

        time.sleep(0.5)
        audio_status = self.get_audio_status()
        mic_mute = str(audio_status.get('mute', '')).lower()
        if muted:
            return mic_mute.startswith('on') or 'выключ' in mic_mute or 'muted' in mic_mute
        return mic_mute.startswith('off') or 'включ' in mic_mute or 'unmuted' in mic_mute

    def set_microphone_volume(self, value: int) -> bool:
        # TE40 web API exposes microphone mute, not a separate microphone gain command.
        # The UI uses value 0 as muted and any positive value as unmuted.
        return self.set_microphone_mute(int(value) <= 0)

    def get_microphone_volume(self) -> Optional[int]:
        audio_status = self.get_audio_status()
        volume = audio_status.get('microphone_volume')
        try:
            return int(volume)
        except (TypeError, ValueError):
            return None
