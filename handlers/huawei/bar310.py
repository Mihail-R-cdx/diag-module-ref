"""
Обработчик для Huawei CloudLink Bar 310.
Реализует протокол взаимодействия с устройством через HTTPS API.
"""

import requests
import json
import time
import urllib3
from datetime import datetime
from typing import Dict, Any, Optional
from requests.auth import HTTPBasicAuth
from core.base_handler import BaseHuaweiCodecHandler
from core.exceptions import AuthenticationError, ConnectionError
from utils.ssl_adapter import SSLAdapter, create_legacy_ssl_context

# Отключаем предупреждения о самоподписанных сертификатах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CloudLinkBar310Handler(BaseHuaweiCodecHandler):
    """Обработчик для Huawei CloudLink Bar 310"""
    
    def __init__(self, ip_address: str, port: int = 443,
                 username: str = 'api', password: str = '',
                 use_ssl: bool = True, verify_ssl: bool = False):
        print(f"=== CloudLinkBar310Handler.__init__ для {ip_address} ===")
        print(f"[INIT] Инициализация handler с логином: '{username}', паролем: '{password}'")
        super().__init__(ip_address, port, username, password, use_ssl, verify_ssl)
        self.device_model = 'Huawei CloudLink Bar 310'
        self.base_url = f"https://{ip_address}:{port}"
        self.username = username
        self.password = password
        self.session = None
        self.acCSRFToken = None
        self.session_cookie = None
        self._connected = False
        self.last_presentation_error_message = None
        
        # Маппинг команд на ActionID для Bar 310
        self.command_map = {
            # Информация об устройстве
            'get_version': 'action.cgi?ActionID=WEB_GetVersionInfoAPI',
            'get_mac': 'action.cgi?ActionID=WEB_GetSystemMacAddrAPI',
            'get_line_state': 'action.cgi?ActionID=WEB_GetLineStateInfoAPI',
            
            # Статусы
            'get_call_status': 'action.cgi?ActionID=WEB_GetMailboxDataAPI',
            'get_audio_status': 'action.cgi?ActionID=WEB_InitAudioCtrlParamsAPI',
            'get_presentation': 'action.cgi?ActionID=WEB_IsSendAuxStreamAPI',
            'get_sleep_mode': 'action.cgi?ActionID=WEB_IsSystemSleepAPI',
            'get_camera_status': 'action.cgi?ActionID=WEB_GetCurCtrlCamSrcAPI',
            
            # Конфигурация
            'get_config_default': 'action.cgi?ActionID=WEB_GetTermSpecsInfoAPI',
            'get_config': 'action.cgi?ActionID=WEB_GetCfgParamAPI',

        }
        
        # Создаем сессию с HTTP Basic аутентификацией
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, password)
        self.session.verify = self.verify_ssl
        if self.use_ssl:
            legacy_context = create_legacy_ssl_context(verify_ssl=self.verify_ssl)
            self.session.mount("https://", SSLAdapter(ssl_context=legacy_context))

    def _log_command(self, message: str) -> None:
        logger = getattr(self, 'command_logger', None)
        if callable(logger):
            logger(message)
        
    def connect(self) -> bool:
        """Установка соединения с кодеком Huawei CloudLink Bar 310"""
        try:
            print(f"Подключаюсь к {self.base_url}/")
            
            # 1. Получаем Session ID
            endpoint = "action.cgi?ActionID=WEB_RequestSessionIDAPI"
            self._log_command(f"[request] POST {self.base_url}/{endpoint}")
            result = self._make_request(endpoint)
            
            if result and result.get('success') == 1:
                print("✓ Сессия успешно получена")
                self.session_cookie = True
            else:
                print("✗ Не удалось получить сессию")
                # Проверяем, не ошибка ли это аутентификации
                if result and result.get('error'):
                    error_msg = result.get('message', '')
                    if "authentication" in error_msg.lower() or result.get('error') == 401:
                        raise AuthenticationError(f"Ошибка аутентификации: {error_msg}")
                # Если не удалось получить сессию без явной ошибки аутентификации - тоже считаем ошибкой
                raise AuthenticationError("Ошибка аутентификации при получении сессии")
            
            # 2. Получаем CSRF Token
            endpoint = "action.cgi?ActionID=WEB_RequestCertificateAPI"
            data = {
                "user": self.username,
                "password": self.password
            }
            self._log_command(f"[request] POST {self.base_url}/{endpoint}")
            self._log_command(f"[payload] {json.dumps(data, ensure_ascii=False)}")
            
            print(f"🔐 Попытка аутентификации с логином: {self.username}")
            result = self._make_request(endpoint, data=data)
            
            if result and result.get('success') == 1:
                data_field = result.get('data', {})
                
                if isinstance(data_field, dict):
                    self.acCSRFToken = data_field.get('acCSRFToken')
                elif isinstance(data_field, str):
                    try:
                        inner_data = json.loads(data_field)
                        self.acCSRFToken = inner_data.get('acCSRFToken')
                    except:
                        pass
                
                if self.acCSRFToken:
                    print(f"✓ CSRF токен получен: {self.acCSRFToken[:20]}...")
                    self._connected = True
                    return True
                else:
                    print("✗ Не удалось извлечь CSRF токен")
                    raise AuthenticationError("Не удалось извлечь CSRF токен")
            else:
                error_msg = result.get('message', 'Неизвестная ошибка') if result else 'Нет ответа'
                print(f"✗ Ошибка аутентификации: {error_msg}")
                # Проверяем, не ошибка ли это аутентификации
                if result and (result.get('error') == 401 or "authentication" in error_msg.lower()):
                    raise AuthenticationError(f"Ошибка аутентификации: {error_msg}")
                # Если ошибка не 401, но и не успешная аутентификация - тоже считаем ошибкой аутентификации
                raise AuthenticationError(f"Ошибка аутентификации: {error_msg}")
                
        except AuthenticationError:
            # Пробрасываем AuthenticationError дальше
            raise
        except Exception as e:
            print(f"✗ Ошибка подключения: {type(e).__name__}: {str(e)}")
            raise ConnectionError(f"Ошибка подключения: {str(e)}")
    
    def disconnect(self) -> None:
        """Разорвать соединение"""
        if self._connected and self.acCSRFToken:
            try:
                endpoint = "action.cgi?ActionID=WEB_LogoutAPI"
                data = {"acCSRFToken": self.acCSRFToken}
                self._make_request(endpoint, data=data)
            except:
                pass
        
        if self.session:
            self.session.close()
        
        self._connected = False
        self.acCSRFToken = None
        self.session_cookie = None
    
    def _parse_response(self, response_text: str) -> Optional[Dict]:
        """
        Парсинг ответа от сервера с обработкой двойной сериализации
        """
        try:
            # Сначала парсим внешний JSON
            outer_data = json.loads(response_text)
            
            # Проверяем, есть ли поле data и является ли оно строкой
            if isinstance(outer_data, dict) and 'data' in outer_data:
                data_field = outer_data['data']
                
                # Если data - это строка, которая содержит JSON, парсим её
                if isinstance(data_field, str):
                    try:
                        inner_data = json.loads(data_field)
                        outer_data['data'] = inner_data
                    except json.JSONDecodeError:
                        # Если не получается распарсить, оставляем как есть
                        pass
            
            return outer_data
            
        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON: {e}")
            return None
    
    def _get_error_text(self, error_data) -> str:
        """Получить текст ошибки"""
        if not error_data:
            return "Неизвестная ошибка"
        
        # Если error_data - строка, возвращаем её
        if isinstance(error_data, str):
            return error_data
        
        # Если error_data - словарь, возвращаем его представление
        if isinstance(error_data, dict):
            return json.dumps(error_data, ensure_ascii=False)
        
        # Если не нашли, возвращаем как есть
        return str(error_data)


    def _make_request(self, endpoint: str, method: str = 'POST', data: Optional[Dict] = None) -> Optional[Dict]:
        """
        Универсальный метод для выполнения запросов к API
        """
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if data:
            request_data = json.dumps(data)
        else:
            request_data = None
        
        try:
            print(f"  -> Запрос: {method} {url}")
            self._log_command(f"[request] {method} {url}")
            
            # ВЫВОД ССЫЛКИ ДЛЯ БРАУЗЕРА (только для GET запросов)
            if method == 'GET':
                print(f"  🔗 Ссылка для браузера: {url}")
            
            if request_data:
                print(f"  -> Данные: {request_data}")
                self._log_command(f"[payload] {request_data}")
            
            response = self.session.request(
                method=method,
                url=url,
                data=request_data,
                headers=headers,
                timeout=5
            )
            self._log_command(f"[response] {response.status_code} {response.text}")
            
            # ВЫВОД СЫРОГО ОТВЕТА
            print(f"  ! Сырой ответ (статус {response.status_code}):")
            if response.text:
                # Пытаемся распарсить и вывести красиво
                try:
                    parsed = json.loads(response.text)
                    # Если есть поле data с строкой JSON, распарсим и его
                    if isinstance(parsed, dict) and 'data' in parsed and isinstance(parsed['data'], str):
                        try:
                            inner_data = json.loads(parsed['data'])
                            parsed['data'] = inner_data
                        except:
                            pass
                    # Выводим полный отформатированный JSON
                    print(json.dumps(parsed, indent=2, ensure_ascii=False))
                except:
                    # Если не получается распарсить, выводим как есть, но полностью
                    print(response.text)
            else:
                print(f"  <пустой ответ>")
            
            if response.status_code == 200:
                # Парсим ответ
                parsed_response = self._parse_response(response.text)
                return parsed_response
            else:
                print(f"  ! HTTP ошибка {response.status_code}")
                error_message = response.text.strip() if response.text else f"HTTP {response.status_code}"
                return {
                    'success': 0,
                    'error': response.status_code,
                    'message': error_message,
                }
                
        except requests.exceptions.RequestException as e:
            self._log_command(f"[error] RequestException: {str(e)}")
            print(f"  ! Ошибка запроса: {e}")
            return {
                'success': 0,
                'error': 'request_exception',
                'message': str(e),
            }
    

    def send_command(self, command: str, data: Optional[Dict] = None) -> Dict:
        """Отправить команду устройству"""
        if not self.is_connected() or not self.acCSRFToken:
            if not self.connect():
                return {'success': False, 'error': 'Not connected'}
        
        endpoint = self.command_map.get(command, command)
        
        # Подготавливаем данные
        request_data = data or {}
        
        # Добавляем CSRF токен для всех action.cgi запросов
        if self.acCSRFToken and 'acCSRFToken' not in request_data:
            request_data['acCSRFToken'] = self.acCSRFToken
        
        result = self._make_request(endpoint, data=request_data if request_data else None)
        
        if result:
            return result
        else:
            return {'success': False, 'error': 'No response'}

    def _get_mic_devices_data(self) -> Dict[str, Any]:
        result = self._make_request('v1/mediacontrol/mic/devices', method='GET')
        if not result or result.get('success') != 1:
            return {}

        data = result.get('data', {})
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return {}

        return data if isinstance(data, dict) else {}

    def _get_hd_ai_microphones(self) -> list:
        data = self._get_mic_devices_data()
        device_list = data.get('deviceList', [])
        if not isinstance(device_list, list):
            return []

        return [
            device for device in device_list
            if isinstance(device, dict) and device.get('groupName') == 'HD-AI'
        ]

    def _get_controllable_hd_ai_microphones(self) -> list:
        hd_ai_mics = self._get_hd_ai_microphones()
        controllable = [mic for mic in hd_ai_mics if str(mic.get('enablePlug')) == '1']
        selected = controllable or hd_ai_mics
        return sorted(selected, key=lambda mic: mic.get('deviceId', 0))[:3]

    @staticmethod
    def _format_call_start_time(raw_value: str) -> str:
        if not raw_value:
            return ""
        try:
            parsed = datetime.strptime(str(raw_value), "%d/%m/%Y %H:%M:%S")
            return parsed.strftime("%d.%m.%Y %H:%M:%S")
        except ValueError:
            return str(raw_value)

    @staticmethod
    def _format_call_duration(start_value: str, end_value: str) -> str:
        if not start_value or not end_value:
            return ""
        try:
            started_at = datetime.strptime(str(start_value), "%d/%m/%Y %H:%M:%S")
            ended_at = datetime.strptime(str(end_value), "%d/%m/%Y %H:%M:%S")
        except ValueError:
            return ""

        total_seconds = max(0, int((ended_at - started_at).total_seconds()))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @staticmethod
    def _format_call_rate(rate_value) -> str:
        try:
            rate_key = int(rate_value)
        except (TypeError, ValueError):
            return str(rate_value or "")
        return f"{rate_key} kbps"

    def _parse_call_records(self, data) -> list[Dict[str, str]]:
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return []
        if not isinstance(data, dict):
            return []

        records = []
        for item in data.get("callRecordList", [])[:10]:
            if not isinstance(item, dict):
                continue
            start_time = item.get("startTime", "")
            end_time = item.get("endTime", "")
            records.append({
                "room_number": item.get("callNumber") or item.get("callName") or "",
                "start_time": self._format_call_start_time(start_time),
                "duration": self._format_call_duration(start_time, end_time),
                "speed": self._format_call_rate(item.get("rate")),
            })
        return records

    def get_call_records(self) -> list[Dict[str, str]]:
        """Download and parse the latest CloudLink Bar 310 call records."""
        if not self.is_connected() or not self.acCSRFToken:
            if not self.connect():
                raise ConnectionError("Не удалось подключиться к CloudLink Bar 310 для получения журнала звонков")

        url = f"{self.base_url}/v1/meeting/calls/history"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Cache-Control": "no-cache",
            "ClientType": "browser",
            "Content-Type": "application/json",
            "Pragma": "no-cache",
            "Referer": f"{self.base_url}/",
            "X-Access-Token": self.acCSRFToken or "",
            "X-Requested-With": "XMLHttpRequest",
            "userType": "web",
        }
        self._log_command(f"[request] GET {url}")

        try:
            response = self.session.get(url, headers=headers, timeout=10)
            self._log_command(f"[response] {response.status_code} {response.text[:500]}")
        except requests.exceptions.RequestException as e:
            self._log_command(f"[error] RequestException: {str(e)}")
            raise ConnectionError(f"Ошибка запроса журнала звонков Bar 310: {str(e)}") from e

        if response.status_code in (401, 403):
            raise AuthenticationError(
                f"HTTP {response.status_code}: ошибка аутентификации при получении журнала звонков Bar 310"
            )
        if response.status_code >= 400:
            raise ConnectionError(
                f"HTTP {response.status_code}: ошибка получения журнала звонков Bar 310"
            )

        result = self._parse_response(response.text)
        if not result or result.get("success") != 1:
            raise ConnectionError(
                f"Кодек не вернул журнал звонков: {result.get('message', result) if isinstance(result, dict) else result}"
            )

        return self._parse_call_records(result.get("data", {}))


    def get_status(self) -> Dict[str, Any]:
        """Получение полного статуса устройства"""
        status = {}
        
        try:
            print("📊 Начинаю сбор статуса для Huawei CloudLink Bar 310...")
            
            # Список базовых команд, которые точно работают
            base_commands = ['get_version', 'get_mac', 'get_audio_status', 'get_line_state', 'get_camera_status']
            
            # Сначала выполняем базовые команды
            for cmd in base_commands:
                if cmd in self.command_map:
                    print(f"\n  Запрос {cmd} ({self.command_map[cmd]})...")
                    result = self.send_command(cmd)
                    
                    if result:
                        if result.get('success') == 1:
                            data = result.get('data', {})
                            if isinstance(data, dict):
                                # Сохраняем все полученные данные в status
                                for key, value in data.items():
                                    status[f"{cmd}_{key}"] = value
                                print(f"  вњ… {cmd} выполнен успешно")
                                
                                # Для get_version сразу извлекаем основные поля
                                if cmd == 'get_version':
                                    status['model'] = data.get('model', 'Huawei CloudLink Bar 310')
                                    status['version'] = data.get('softVersion', 'Unknown')
                                    status['serial_number'] = data.get('lisence', 'N/A')
                                    status['mic_version'] = data.get('micVersion', 'N/A')
                                    print(f"    Модель: {status['model']}")
                                    print(f"    Серийный номер: {status['serial_number']}")
                                    print(f"    Версия: {status['version']}")
                                
                                # Для get_mac извлекаем MAC адрес
                                elif cmd == 'get_mac':
                                    status['mac_address'] = (data.get('system_wanMAC_addr') or 
                                                            data.get('system_lanMAC_addr') or 'N/A')
                                    print(f"    MAC адрес: {status['mac_address']}")
                                
                                # Для get_audio_status извлекаем аудио параметры
                                elif cmd == 'get_audio_status':
                                    status['mic_mute'] = 'On' if data.get('MicSwitch', 0) == 0 else 'Off'
                                    status['speaker_mute'] = 'On' if data.get('SpeakerSwitch', 0) == 1 else 'Off'
                                    status['speaker_volume'] = data.get('speakerValue', 0)
                                    print(f"    Микрофон: {status['mic_mute']}, Динамик: {status['speaker_mute']}, Громкость: {status['speaker_volume']}")
                                
                                # Для get_line_state извлекаем время работы и SIP информацию
                                elif cmd == 'get_line_state':
                                    # Время работы
                                    run_day = int(data.get('runDay', 0))
                                    run_hour = int(data.get('runHour', 0))
                                    run_min = int(data.get('runMin', 0))
                                    
                                    uptime_parts = []
                                    if run_day > 0:
                                        uptime_parts.append(f"{run_day} д")
                                    if run_hour > 0:
                                        uptime_parts.append(f"{run_hour} ч")
                                    if run_min > 0:
                                        uptime_parts.append(f"{run_min} мин")
                                    
                                    status['uptime'] = ' '.join(uptime_parts) if uptime_parts else '0 мин'
                                    
                                    # SIP информация
                                    status['sip_server'] = data.get('sipAddr', 'N/A')
                                    status['sip_number'] = data.get('sipNumber', '')
                                    
                                    # SIP статус из sipStatusTxStr
                                    sip_status_str = data.get('sipStatusTxStr', '')
                                    status['sip_status'] = 'On' if sip_status_str == 'SIP_STATE_OK' else 'Off'
                                    
                                    print(f"    Время работы: {status['uptime']}")
                                    print(f"    SIP статус: {status['sip_status']}")
                                    print(f"    SIP сервер: {status['sip_server']}")
                                    print(f"    SIP номер: {status['sip_number']}")
                                    
                                elif cmd == 'get_call_status':
                                    state = data.get('state', {})
                                    if isinstance(state, dict):
                                        # Статус звонка
                                        call_state = state.get('callstate', 0)
                                        call_status_map = {
                                            0: 'No Call',
                                            1: 'Calling',
                                            2: 'Disconnected',
                                            3: 'Connected'
                                        }
                                        status['call_status'] = call_status_map.get(call_state, 'Unknown')
                                        
                                        # SIP статус из поля sip
                                        sip_value = state.get('sip', 0)
                                        if 'sip_status' not in status:
                                            status['sip_status'] = 'On' if sip_value == 1 else 'Off'
                                        
                                        print(f"      micValue из статуса звонка: {state.get('micValue', 0)}")
                                        
                                        print(f"      Статус звонка: {status['call_status']}")    
                                elif cmd == 'get_camera_status':
                                    local_source = data.get('localInMainSource', 0)
                                    # 255 - подключена, 0 - не подключена
                                    status['camera_status'] = 'On' if local_source == 255 else 'Off'
                                    print(f"    Статус камеры: {'Подключена' if local_source == 255 else 'Не подключена'} (localInMainSource={local_source})")
                        else:
                            error_data = result.get('error', {})
                            if isinstance(error_data, dict):
                                error_text = self._get_error_text(error_data)
                            else:
                                error_text = str(error_data)
                            print(f"  ! {cmd} вернул ошибку: {error_text}")
                    else:
                        print(f"  ✗ {cmd} - нет ответа")
            
            # Затем тестируем ВСЕ остальные команды из command_map
            print("\n📋 Тестирование всех доступных команд:")
            for cmd_name, cmd_endpoint in self.command_map.items():
                # Пропускаем уже выполненные базовые команды
                if cmd_name in base_commands:
                    continue
                    
                print(f"\n  Тест: {cmd_name} -> {cmd_endpoint}")
                result = self.send_command(cmd_name)
                
                if result:
                    if result.get('success') == 1:
                        print(f"    вњ… Успешно (success=1)")
                        # Сохраняем данные из успешных ответов
                        data = result.get('data', {})
                        if isinstance(data, dict):
                            for key, value in data.items():
                                status[f"{cmd_name}_{key}"] = value
                            
                            # СПЕЦИАЛЬНАЯ ОБРАБОТКА ДЛЯ get_call_status
                            if cmd_name == 'get_call_status':
                                state = data.get('state', {})
                                if isinstance(state, dict):
                                    # Статус звонка
                                    call_state = state.get('callstate', 0)
                                    call_status_map = {
                                        0: 'No Call',
                                        1: 'Calling',
                                        2: 'Disconnected',
                                        3: 'Connected'
                                    }
                                    status['call_status'] = call_status_map.get(call_state, 'Unknown')
                                    
                                    # SIP статус из поля sip
                                    sip_value = state.get('sip', 0)
                                    # Не перезаписываем sip_status, если он уже есть из get_line_state
                                    if 'sip_status' not in status:
                                        status['sip_status'] = 'On' if sip_value == 1 else 'Off'
                                    print(f"      Статус звонка: {status['call_status']}")
                    else:
                        error_data = result.get('error', {})
                        if isinstance(error_data, dict):
                            error_text = self._get_error_text(error_data)
                        else:
                            error_text = str(error_data)
                        print(f"    ! Ошибка: {error_text}")
                else:
                    print(f"    ✗ Нет ответа")

            print("\n  Запрос статуса микрофонов HD-AI...")
            status['mic_volume'] = 'Микрофон не подключён'
            status['mic_connection_status'] = 'Микрофон не подключён'
            hd_ai_mics = self._get_hd_ai_microphones()
            if hd_ai_mics:
                first_hd_ai_mic = hd_ai_mics[0]
                plug_status = first_hd_ai_mic.get('plugStatus')
                if str(plug_status) == '0':
                    status['mic_volume'] = 'Микрофон не подключён'
                    status['mic_connection_status'] = 'Микрофон не подключён'
                else:
                    status['mic_volume'] = first_hd_ai_mic.get('gainVolume', 0)
                    status['mic_connection_status'] = 'Подключён'
                print(
                    f"    HD-AI микрофон: plugStatus={plug_status}, "
                    f"gainVolume={first_hd_ai_mic.get('gainVolume')}, "
                    f"GUI value={status['mic_volume']}, "
                    f"GUI status={status['mic_connection_status']}"
                )
            
            # Формируем итоговый статус
            final_status = {
                'model': status.get('model', 'Huawei CloudLink Bar 310'),
                'version': status.get('version', 'Unknown'),
                'serial_number': status.get('serial_number', 'N/A'),
                'mac_address': status.get('mac_address', 'N/A'),
                'mic_version': status.get('mic_version', 'N/A'),
                'mic_mute': status.get('mic_mute', 'Off'),
                'mic_connection_status': status.get('mic_connection_status'),
                'mic_volume': status.get('mic_volume', 0),
                'speaker_mute': status.get('speaker_mute', 'Off'),
                'speaker_volume': status.get('speaker_volume', 0),
                'call_status': status.get('call_status', 'No Call'),
                'sip_status': status.get('sip_status', 'Off'),
                'sip_server': status.get('sip_server', 'N/A'),
                'sip_number': status.get('sip_number', ''),
                'presentation': status.get('presentation', 'Stop'),
                'sleep_mode': status.get('sleep_mode', 'Off'),
                'uptime': status.get('uptime', 'N/A'),
                'camera_status': status.get('camera_status', 'Off'),
            }
            
            print(f"\n📊 Сбор статуса завершен. Протестировано команд: {len(self.command_map)}")
            print(f"📊 Получено полей в статусе: {len(final_status)}")
            print(f"📊 Время работы: {final_status['uptime']}")
            
            return final_status
            
        except Exception as e:
            print(f"✗ Ошибка получения статуса: {e}")
            import traceback
            traceback.print_exc()
            return {}
  
    # Реализация абстрактных методов
    def get_device_info(self) -> Dict[str, str]:
        """Получить информацию об устройстве"""
        status = self.get_status()
        return {
            'model': status.get('model', 'Huawei CloudLink Bar 310'),
            'serial': status.get('serial_number', 'N/A'),
            'version': status.get('version', 'N/A'),
            'mac': status.get('mac_address', 'N/A'),
            'ip': self.ip_address,
            'mic_version': status.get('mic_version', 'N/A')
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Получить системную информацию"""
        status = self.get_status()
        return {
            'uptime': status.get('uptime', 'N/A'),
            'sleep_mode': status.get('sleep_mode', 'Off'),
            'temperature': 'N/A'
        }
    
    def get_call_status(self) -> Dict[str, Any]:
        """Получить статус вызова"""
        status = self.get_status()
        return {
            'status': status.get('call_status', 'Idle'),
            'type': status.get('call_type', 'Unknown'),
            'remote_number': '',
            'remote_name': '',
            'duration': 0,
            'protocol': status.get('call_type', ''),
            'bandwidth': 0
        }
    
    def get_network_status(self) -> Dict[str, Any]:
        """Получить статус сети"""
        status = self.get_status()
        return {
            'ip': self.ip_address,
            'gateway': 'N/A',
            'dns': 'N/A',
            'bandwidth': 'N/A',
            'sip_server': status.get('sip_server', 'N/A'),
            'sip_number': status.get('sip_number', 'N/A')
        }
    
    def get_audio_status(self) -> Dict[str, Any]:
        """Получить статус аудио"""
        status = self.get_status()
        return {
            'volume': status.get('speaker_volume', 0),
            'mute': status.get('mic_mute', 'Off'),
            'speaker_volume': status.get('speaker_volume', 0),
            'speaker_mute': status.get('speaker_mute', 'Off'),
            'microphone_volume': status.get('mic_volume')
        }
    
    def get_video_status(self) -> Dict[str, Any]:
        """Получить статус видео"""
        status = self.get_status()
        return {
            'presentation': status.get('presentation', 'Stop'),
            'camera': 'N/A',
            'format': '',
            'resolution': ''
        }
    
    def get_mac_address(self) -> str:
        """Получение MAC адреса"""
        result = self.send_command('get_mac')
        if result and result.get('success') == 1:
            data = result.get('data', {})
            if isinstance(data, dict):
                return (data.get('system_wanMAC_addr') or 
                       data.get('system_lanMAC_addr') or 
                       data.get('mac_addr') or 'N/A')
        return 'N/A'
    
    def get_presentation_status(self) -> str:
        """Получить статус презентации"""
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
    
    def get_sleep_mode(self) -> str:
        """Получить режим сна"""
        result = self.send_command('get_sleep_mode')
        if result and result.get('success') == 1:
            data = result.get('data', {})
            if isinstance(data, dict):
                is_sleep = data.get('isSystemSleep', 'unsleep')
                return 'On' if is_sleep == 'sleep' else 'Off'
        return 'Off'

    def wake_up(self) -> bool:
        """Разбудить устройство из режима сна."""
        payload = {
            "acCSRFToken": self.acCSRFToken or "",
        }
        result = self.send_command('action.cgi?ActionID=WEB_SystemWakeUpAPI', payload)
        return bool(result and result.get('success') == 1)

    def get_volume_range(self):
        return 0, 15

    def set_presentation(self, value: str) -> bool:
        self.last_presentation_error_message = None
        command_map = {
            'Start': 'action.cgi?ActionID=WEB_StartSendAuxStreamAPI',
            'Stop': 'action.cgi?ActionID=WEB_StopSendAuxStreamAPI',
        }
        command = command_map.get(value)
        if not command:
            raise ValueError("Presentation value must be 'Start' or 'Stop'")

        payload = {
            "acCSRFToken": self.acCSRFToken or "",
        }
        result = self.send_command(command, payload)
        if result and result.get('success') == 1:
            return True

        error_info = result.get('error') if isinstance(result, dict) else None
        if value == 'Start' and isinstance(error_info, dict):
            if error_info.get('id') == 100666941 and error_info.get('code') == 100687877:
                self.last_presentation_error_message = (
                    "К видеовходу не подключён источник. Старт презентации невозможен"
                )

        # У Bar310 ответ set-команды бывает без явного success, поэтому сверяем статус.
        retries = 2 if value == 'Start' else 0
        for _ in range(retries):
            time.sleep(1.5)
            result = self.send_command(command, payload)
            if result and result.get('success') == 1:
                return True

            if self.get_presentation_status() == value:
                return True

        time.sleep(0.5)
        return self.get_presentation_status() == value

    def set_speaker_volume(self, value: int) -> bool:
        min_value, max_value = self.get_volume_range()
        if not min_value <= value <= max_value:
            raise ValueError(f"Speaker volume must be in range {min_value}..{max_value}")

        payload = {
            "speaker": 1,
            "speakerValue": int(value),
            "acCSRFToken": self.acCSRFToken or "",
        }
        # Для set-команды нужен полный action.cgi endpoint, иначе запрос уходит
        # на несуществующий URL вида /WEB_SetSpeakVolumeAPI.
        result = self.send_command('action.cgi?ActionID=WEB_SetSpeakVolumeAPI', payload)
        if result and result.get('success') == 1:
            return True

        time.sleep(0.5)
        return self.get_speaker_volume() == int(value)

    def get_speaker_volume(self) -> Optional[int]:
        result = self.send_command('get_audio_status')
        if not result or result.get('success') != 1:
            return None

        data = result.get('data', {})
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return None

        if not isinstance(data, dict):
            return None

        volume = data.get('speakerValue')
        try:
            return int(volume)
        except (TypeError, ValueError):
            return None

    def set_microphone_volume(self, value: int) -> bool:
        min_value, max_value = self.get_volume_range()
        if not min_value <= int(value) <= max_value:
            raise ValueError(f"Microphone volume must be in range {min_value}..{max_value}")

        if not self.is_connected() or not self.acCSRFToken:
            if not self.connect():
                return False

        microphones = self._get_controllable_hd_ai_microphones()
        if not microphones:
            microphones = [{"deviceId": device_id, "ctrlStatus": 1} for device_id in (4, 5, 6)]

        payload = {
            "setMicInfoList": [
                {
                    "deviceId": mic.get("deviceId"),
                    "ctrlStatus": mic.get("ctrlStatus", 1),
                    "gainVolume": int(value),
                }
                for mic in microphones
                if mic.get("deviceId") is not None
            ]
        }
        if not payload["setMicInfoList"]:
            return False

        result = self._make_request('v1/mediacontrol/mic/devices', method='PUT', data=payload)
        if result and result.get('success') == 1:
            return True

        result = self._make_request('v1/mediacontrol/mic/devices', method='POST', data=payload)
        return bool(result and result.get('success') == 1)

    def get_microphone_volume(self) -> Optional[int]:
        hd_ai_mics = self._get_hd_ai_microphones()
        if not hd_ai_mics:
            return None

        first_hd_ai_mic = hd_ai_mics[0]
        if str(first_hd_ai_mic.get('plugStatus')) == '0':
            return None

        volume = first_hd_ai_mic.get('gainVolume')
        try:
            return int(volume)
        except (TypeError, ValueError):
            return None

    def set_sip_server(self, sip_address: str = "vcs-core-a.sber.ru") -> bool:
        """Установить SIP-сервер через тот же API, что и в референсном драйвере."""
        payload = {
            "CfgItemInt": [],
            "CfgItemString": [
                {
                    "CfgItemID": "sipserv_addr",
                    "CfgItemInfo": sip_address,
                }
            ],
            "acCSRFToken": self.acCSRFToken or "",
        }
        result = self.send_command('action.cgi?ActionID=WEB_SaveCfgParamAPI', payload)
        if result and result.get('success') == 1:
            return True

        time.sleep(0.5)
        return self.verify_sip_server() == sip_address

    def verify_sip_server(self) -> Optional[str]:
        """Прочитать текущий SIP-сервер из конфигурации."""
        payload = {
            "CfgIDString": ["sipserv_addr"],
            "acCSRFToken": self.acCSRFToken or "",
        }
        result = self.send_command('action.cgi?ActionID=WEB_GetCfgParamAPI', payload)
        if not result or result.get('success') != 1:
            return None

        data = result.get('data', {})
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return data or None

        if not isinstance(data, dict):
            return None

        value = data.get('sipserv_addr')
        return str(value) if value is not None else None

