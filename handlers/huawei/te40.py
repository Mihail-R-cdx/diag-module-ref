import requests
import json
import ssl
import http.cookiejar
import urllib.request
import urllib.error
import urllib.parse
import re
import random
import time
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from core.codec_call_history import snapshot_from_display_records
from core.base_handler import BaseHuaweiCodecHandler
from core.exceptions import (
    AuthenticationError,
    CommandError,
    ConnectionError,
    ProtocolError,
    SessionInvalidError,
)
from core.redaction import redact_diagnostic

class HuaweiTE40Handler(BaseHuaweiCodecHandler):
    """Обработчик для Huawei TE40 с рабочей реализацией подключения"""

    CAMERA_TYPE_MODELS = {
        0: 'C500',
        1: 'VPC500',
        2: 'VPC520',
        3: 'SONY EVI-HD1',
        4: 'SONY EVI-D100',
        5: 'SONY EVI-D70',
        6: 'SONY D30/D31',
        7: 'SONY BRC-300P',
        8: 'SONY BRC-H700',
        9: 'CANON V50',
        10: 'CANON VCC1',
        11: 'CANON VCC4',
        12: '3CCD',
        13: 'C200',
        14: 'GPT CAM',
        15: 'KX',
        16: 'PELCO',
        17: 'PTC100',
        18: 'SYYT',
        19: 'TAC',
        20: 'VCC-SW80P',
        21: 'VCC-HD90P',
        22: 'VPC500S',
        23: 'VPC500E',
        24: 'VPC600/VPC620',
        28: 'SONY BRC-Z330',
        29: 'VPC800',
        30: 'VPT300',
    }
    _MICROPHONE_SAVE_FIELDS = (
        "micall",
        *(f"mic{index}" for index in range(1, 19)),
        *(f"mic{index}Value" for index in range(1, 19)),
    )
    
    def __init__(self, ip_address: str, port: int = 443,
                 username: str = None, password: str = None,
                 use_ssl: bool = True, verify_ssl: bool = False):
        super().__init__(ip_address, port, username, password, use_ssl, verify_ssl)
        self.device_model = 'Huawei TE40'
        self.session_id = None
        self.csrf_token = None
        self.opener = None
        self.cookie_jar = http.cookiejar.CookieJar()
        self.uses_cookie_session = False
        self._connected = False
        self.last_presentation_error_message = None
        
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
            urllib.request.HTTPCookieProcessor(self.cookie_jar)
        )

    @staticmethod
    def _extract_microphone_models(mic_version) -> list[str]:
        values = []
        if isinstance(mic_version, (list, tuple)):
            for item in mic_version:
                values.extend(
                    HuaweiTE40Handler._extract_microphone_models(item)
                )
        elif isinstance(mic_version, dict):
            values.extend(
                HuaweiTE40Handler._extract_microphone_models(
                    mic_version.get('micVersion')
                )
            )
        elif mic_version not in (None, '', 'N/A'):
            model = str(mic_version).strip().split(maxsplit=1)[0]
            if model:
                values.append(model)

        return list(dict.fromkeys(values))

    @staticmethod
    def _resolve_microphone_connection_status(
        mic_version,
        audio_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        microphone_models = (
            HuaweiTE40Handler._extract_microphone_models(mic_version)
        )
        if microphone_models:
            return (
                'Микрофон подключён. Модель '
                + ', '.join(microphone_models)
            )

        if isinstance(audio_data, dict) and any(
            key in audio_data
            for key in (
                'MicSwitch',
                'micall',
                'mic1',
                'mic2',
                'mic3',
                'USBMICIn',
            )
        ):
            return 'Микрофон подключён'

        return 'Не определено'

    @classmethod
    def _format_camera_connection_status(cls, camera_type) -> str:
        try:
            camera_type_code = int(camera_type)
        except (TypeError, ValueError):
            return 'Камера подключена. Модель неизвестна'

        model = cls.CAMERA_TYPE_MODELS.get(camera_type_code)
        if model:
            return f'Камера подключена. Модель {model}'
        return (
            'Камера подключена. '
            f'Модель неизвестна (код {camera_type_code})'
        )

    def _log_command(self, message: str) -> None:
        if message.startswith("[payload]"):
            message = "[payload] <redacted>"
        else:
            for secret in (
                self.credentials.get("username"),
                self.credentials.get("password"),
                getattr(self, "session_id", None),
                getattr(self, "csrf_token", None),
            ):
                if secret:
                    message = message.replace(str(secret), "<redacted>")
        logger = getattr(self, 'command_logger', None)
        if callable(logger):
            logger(str(self._redact(message)))

    def _log_response(self, status: int, body: Any) -> None:
        """Log a parsed, structurally redacted response without retaining raw text."""
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except (TypeError, ValueError):
                self._log_command(f"[response] {status} <non-json body omitted>")
                return

        safe_body = redact_diagnostic(body, self._secret_values())
        self._log_command(
            f"[response] {status} {json.dumps(safe_body, ensure_ascii=False, sort_keys=True)}"
        )

    def _secret_values(self):
        """Return request-scoped values that must never cross a diagnostic boundary."""
        values = [
            self.credentials.get('username'), self.credentials.get('password'),
            self.session_id, self.csrf_token,
        ]
        values.extend(cookie.value for cookie in self.cookie_jar if cookie.value)
        return values

    def _redact(self, value):
        return redact_diagnostic(value, self._secret_values())

    def _debug(self, value) -> None:
        print(self._redact(value))

    def _report_exception(self, operation: str, exc: Exception) -> None:
        """Emit redacted diagnostics for a public operation failure."""
        safe_error = self._redact(str(exc))
        safe_traceback = self._redact(traceback.format_exc())
        self._debug(f"{operation} failed: {type(exc).__name__}: {safe_error}")
        self._log_command(f"[error] {operation}: {safe_traceback}")

    def _get_session_cookie(self) -> Optional[str]:
        for cookie in self.cookie_jar:
            if cookie.name.lower() == 'sessionid' and cookie.value:
                return cookie.value
        return None

    def _browser_headers(self, json_payload: bool = False) -> Dict[str, str]:
        headers = {
            'Accept': '*/*',
            'Origin': self.base_url,
            'Referer': f"{self.base_url}/login.html",
            'User-Agent': 'Mozilla/5.0',
            'X-Requested-With': 'XMLHttpRequest',
            'userType': 'web',
        }
        if json_payload:
            headers['Content-Type'] = 'application/json'
        return headers

    def _open_json_request(self, url: str, data: Optional[bytes], headers: Dict[str, str], method: str = 'POST') -> Dict[str, Any]:
        self._log_command(f"[request] {method} {url}")
        if data:
            self._log_command(f"[payload] {data.decode('utf-8', errors='ignore')}")
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        response = self.opener.open(request, timeout=10)
        response_text = response.read().decode('utf-8')
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            self._log_response(200, response_text)
            raise
        self._log_response(200, result)
        return result

    def _connect_browser_login(self) -> bool:
        """Fallback login flow used by TE40 web UI on some firmware versions."""
        self._debug("Пробую браузерный flow подключения TE40...")

        session_url = f"{self.base_url}/action.cgi?ActionID=Web_RequestSessionID&rmd={random.random()}"
        session_result = self._open_json_request(
            session_url,
            data=None,
            headers=self._browser_headers(),
            method='POST'
        )
        if session_result.get('success') != 1:
            if self._is_authentication_response(session_result):
                raise AuthenticationError("Ошибка аутентификации при Web_RequestSessionID")
            return False

        self.session_id = self._get_session_cookie() or self.session_id

        token_url = f"{self.base_url}/action.cgi?ActionID=Web_RequestCertificate&rmd={random.random()}"
        token_data = json.dumps({
            "password": self.credentials.get('password'),
            "user": self.credentials.get('username'),
        }).encode('utf-8')
        token_result = self._open_json_request(
            token_url,
            data=token_data,
            headers=self._browser_headers(json_payload=True),
            method='POST'
        )
        if token_result.get('success') != 1:
            if self._is_authentication_response(token_result):
                raise AuthenticationError("Ошибка аутентификации при Web_RequestCertificate")
            return False

        token_payload = self._parse_json_data(token_result.get('data', {}))
        self.csrf_token = token_payload.get('acCSRFToken') or self.csrf_token
        self.session_id = self._get_session_cookie() or self.session_id

        change_url = f"{self.base_url}/action.cgi?ActionID=WEB_ChangeSessionID&rmd={random.random()}"
        change_result = self._open_json_request(
            change_url,
            data=None,
            headers=self._browser_headers(),
            method='POST'
        )
        if change_result.get('success') != 1:
            return False

        self.session_id = self._get_session_cookie() or self.session_id
        self.uses_cookie_session = True
        self._connected = True
        self._debug("✓ Браузерный flow подключения TE40 успешен")
        return True

    def _is_authentication_response(self, result: Dict[str, Any]) -> bool:
        if not isinstance(result, dict):
            return False

        auth_codes = {401, 403}
        auth_code_strings = {str(code) for code in auth_codes}
        values = [result.get('error'), result.get('code'), result.get('id')]

        for key in ('error', 'exception'):
            details = result.get(key)
            if isinstance(details, dict):
                values.extend([details.get('id'), details.get('code')])

        if any(value in auth_codes or str(value) in auth_code_strings for value in values):
            return True
        return False
    
    def connect(self) -> bool:
        """Установка соединения с кодеком Huawei TE40"""
        try:
            if not self.credentials.get('username') or not self.credentials.get('password'):
                raise AuthenticationError("Credentials are required for Huawei TE-40 before connecting.")
            self._debug(f"Подключаюсь к {self.base_url}/")
            
            # 1. Получаем Session ID
            session_url = f"{self.base_url}/action.cgi?ActionID=WEB_RequestSessionIDAPI"
            session_request = urllib.request.Request(session_url, method='POST')
            self._log_command(f"[request] POST {session_url}")
            
            try:
                session_response = self.opener.open(session_request, timeout=10)
                session_response_text = session_response.read().decode('utf-8')
                result = json.loads(session_response_text)
                self._log_response(200, result)
                
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
                    
                    self._debug("✓ Session ID получен")
                else:
                    self._debug(f"✗ Session ID не получен: {result}")
                    # Проверяем, не ошибка ли это аутентификации
                    if self._is_authentication_response(result):
                        raise AuthenticationError(f"Ошибка аутентификации: {result.get('message', 'Неверные учетные данные')}")
                    return self._connect_browser_login()
                    
            except urllib.error.HTTPError as e:
                if e.code == 401 or e.code == 403:
                    raise AuthenticationError(f"HTTP {e.code}: Ошибка аутентификации")
                raise ConnectionError(f"HTTP ошибка: {e.code}")
            except json.JSONDecodeError as e:
                raise ProtocolError("Malformed session response from Huawei TE-40") from e
            except AuthenticationError:
                raise
            except ProtocolError:
                raise
            except Exception as e:
                raise ConnectionError("Ошибка подключения при получении Session ID")
            
            # 2. Получаем CSRF Token
            self._debug("Получаю CSRF Token...")
            token_url = f"{self.base_url}/action.cgi?ActionID=WEB_RequestCertificateAPI"
            certificate_ok = False
            
            data = json.dumps({
                "user": self.credentials.get('username'),
                "password": self.credentials.get('password')
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
                token_result = json.loads(token_response_text)
                self._log_response(200, token_result)
                
                if token_result.get('success') == 1:
                    certificate_ok = True
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
                        self._debug("✓ CSRF Token получен")
                    else:
                        self._debug("⚠ CSRF Token не получен (пустой ответ)")
                else:
                    self._debug(f"✗ CSRF Token запрос неуспешен: {token_result}")
                    # Проверяем, не ошибка ли это аутентификации
                    if self._is_authentication_response(token_result):
                        raise AuthenticationError(f"Ошибка аутентификации при получении CSRF токена")
                    self.csrf_token = None
                    
            except urllib.error.HTTPError as e:
                if e.code == 401 or e.code == 403:
                    raise AuthenticationError(f"HTTP {e.code}: Ошибка аутентификации при получении CSRF токена")
                raise ConnectionError(f"HTTP ошибка при получении CSRF токена: {e.code}")
            except json.JSONDecodeError as e:
                raise ProtocolError("Malformed certificate response from Huawei TE-40") from e
            except AuthenticationError:
                raise
            except ProtocolError:
                raise
            except Exception as e:
                self._debug(f"Ошибка получения CSRF Token: {type(e).__name__}")
                self.csrf_token = None
            
            # 3. Проверяем подключение
            if self.session_id and certificate_ok:
                self._connected = True
                self._debug("✓ Подключение установлено")
                return True
            else:
                if self._connect_browser_login():
                    return True
                self._debug("✗ Не удалось установить подключение")
                return False
                
        except (AuthenticationError, ProtocolError):
            # Пробрасываем AuthenticationError дальше
            raise
        except Exception as e:
            self._debug(f"Ошибка подключения: {type(e).__name__}")
            raise ConnectionError("Ошибка подключения к Huawei TE-40")


    
    def disconnect(self) -> None:
        """Разорвать соединение"""
        self._connected = False
        self.session_id = None
        self.csrf_token = None
        self.uses_cookie_session = False
        self.opener = None
        try:
            self.cookie_jar.clear()
        except Exception:
            self.cookie_jar = http.cookiejar.CookieJar()
    
    def send_command(self, command: str, data: Optional[Dict] = None) -> Dict:
        """Отправить команду устройству"""
        if not self.is_connected() or (not self.session_id and not self.uses_cookie_session):
            raise ConnectionError("Huawei TE40 session is not connected")
        
        try:
            # Маппинг команд на ActionID
            command_map = {
                'get_version': 'WEB_GetVersionInfoAPI',
                'get_call_status': 'WEB_GetMailboxDataAPI',
                'get_sip_status': 'WEB_GetLineStateInfoAPI',
                'get_audio_status': 'WEB_InitAudioCtrlParamsAPI',
                'get_monitor_audio_params': 'WEB_GetMonitorAudioParam',
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
            
            self._debug(f"Отправка команды {command} на {url}")
            
            # Подготавливаем заголовки
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
            if self.session_id:
                headers['Sessionid'] = self.session_id
            if self.uses_cookie_session:
                headers.update(self._browser_headers(json_payload=bool(data)))
            
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
            
            try:
                result = json.loads(response_text)
                self._log_response(200, result)
                self._debug(f"Ответ {command} получен")
                return result
            except json.JSONDecodeError as error:
                self._log_response(200, response_text)
                self._debug("Получен не-JSON ответ")
                raise ProtocolError(
                    f"Huawei TE40 returned malformed JSON for {command}"
                ) from error
            
        except urllib.error.HTTPError as e:
            self._log_command(f"[error] HTTP {e.code} {command}")
            if e.code in (401, 403):
                raise SessionInvalidError(
                    f"HTTP {e.code}: established TE40 session was rejected"
                ) from e
            raise CommandError(f"HTTP {e.code}: TE40 command failed") from e
        except urllib.error.URLError as e:
            self._log_command(f"[error] transport {command}")
            raise ConnectionError(f"TE40 transport failed for {command}") from e
        except (SessionInvalidError, ProtocolError, CommandError, ConnectionError):
            raise
        except Exception as e:
            self._log_command(f"[error] {type(e).__name__} {command}")
            self._debug(f"Ошибка выполнения команды {command}: {type(e).__name__}")
            raise ConnectionError(f"TE40 command failed for {command}") from e

    @staticmethod
    def _format_call_start_time(raw_value: str) -> str:
        if not raw_value:
            return ""
        try:
            parsed = datetime.strptime(raw_value, "%d/%m/%Y %H:%M:%S")
            return parsed.strftime("%d.%m.%Y %H:%M:%S")
        except ValueError:
            return raw_value

    @staticmethod
    def _format_call_duration(start_value: str, end_value: str) -> str:
        if not start_value or not end_value:
            return ""
        try:
            started_at = datetime.strptime(start_value, "%d/%m/%Y %H:%M:%S")
            ended_at = datetime.strptime(end_value, "%d/%m/%Y %H:%M:%S")
        except ValueError:
            return ""

        total_seconds = max(0, int((ended_at - started_at).total_seconds()))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @staticmethod
    def _format_call_rate(rate_value) -> str:
        rate_map = {
            159: "1920 kbps",
            160: "2048 kbps",
        }
        try:
            rate_key = int(rate_value)
        except (TypeError, ValueError):
            return str(rate_value or "")
        return rate_map.get(rate_key, f"{rate_key} kbps")

    def _parse_p2p_call_records(self, data) -> list[Dict[str, str]]:
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as error:
                raise ProtocolError("TE40 call-history payload is not valid JSON") from error
        if not isinstance(data, dict):
            raise ProtocolError("TE40 call-history payload is not an object")

        if "CallList" not in data or not isinstance(data["CallList"], list):
            raise ProtocolError("TE40 call-history payload has no CallList array")
        records = []
        for item in data["CallList"]:
            if not isinstance(item, dict):
                raise ProtocolError("TE40 call-history CallList contains a non-object record")
            start_time = item.get("StartTime", "")
            stop_time = item.get("StopTime", "")
            records.append({
                "room_number": item.get("aucCallCode") or item.get("aucRcdName") or "",
                "start_time": self._format_call_start_time(start_time),
                "duration": self._format_call_duration(start_time, stop_time),
                "speed": self._format_call_rate(item.get("uwCallRate")),
                "_raw_start": start_time,
                "_raw_end": stop_time,
                "source_identity": item.get("id") or item.get("recordId"),
                "_active": bool(item.get("active") or item.get("isActive")),
                "_direction": item.get("direction") or item.get("callDirection"),
            })
        return records

    def get_call_records(self) -> list[Dict[str, str]]:
        """Получить последние записи журнала звонков TE-40."""
        result = self.send_command(
            "WEB_GetP2PCallRecordsAPI",
            {"acCSRFToken": self.csrf_token or ""},
        )
        if not result or result.get("success") != 1:
            raise ConnectionError(f"Кодек не вернул журнал звонков: {result.get('exception', result) if isinstance(result, dict) else result}")
        return self._parse_p2p_call_records(result.get("data", {}))

    def get_call_history_snapshot(self):
        """Return typed history; only a validated empty list proves clean EoJ."""
        records = self.get_call_records()
        return snapshot_from_display_records(records, source_ended=not records)

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
                    status['model'] = processed_data.get('model', 'Huawei TE40')
                    status['serial_number'] = processed_data.get('lisence', 'Unknown')
                    mic_version = processed_data.get('micVersion')
                    status['mic_version'] = mic_version
                    status['mic_connection_status'] = (
                        self._resolve_microphone_connection_status(
                            mic_version
                        )
                    )
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
                self._report_exception("Call-status request", e)
            
            # 5. Получаем аудио статус
            print("Запрос аудио статуса...")
            try:
                audio_result = self.send_command('get_audio_status')
                if audio_result and audio_result.get('success') == 1:
                    audio_data = self._parse_json_data(audio_result.get('data', '{}'))
                    if audio_data:
                        status['mic_connection_status'] = (
                            self._resolve_microphone_connection_status(
                                status.get('mic_version'),
                                audio_data,
                            )
                        )
                        status['mic_mute'] = 'On' if audio_data.get('MicSwitch', 0) == 0 else 'Off'
                        status['speaker_mute'] = 'On' if audio_data.get('SpeakerSwitch', 0) == 1 else 'Off'
                        status['speaker_volume'] = audio_data.get('speakerValue', 0)
                        if 'micValue' in audio_data:
                            status['mic_volume'] = audio_data.get('micValue')
                        print(f"Аудио статус получен")
            except Exception as e:
                self._report_exception("Audio-status request", e)

            print("Запрос monitor audio params...")
            try:
                monitor_audio_result = self.send_command(
                    'get_monitor_audio_params'
                )
                if (
                    monitor_audio_result
                    and monitor_audio_result.get('success') == 1
                ):
                    monitor_audio_data = self._parse_json_data(
                        monitor_audio_result.get('data', {})
                    )
                    if monitor_audio_data:
                        status['monitor_mic_value'] = (
                            monitor_audio_data.get('MicValueIndex')
                        )
                        status['monitor_speaker_value'] = (
                            monitor_audio_data.get('SpeakerValueIndex')
                        )
            except Exception as e:
                self._report_exception("Monitor-audio request", e)
            
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
                self._report_exception("Presentation-status request", e)
            
            # 7. Получаем статус камеры
            print("Запрос статуса камеры...")
            try:
                camera_result = self.send_command('get_camera_status')
                if camera_result and camera_result.get('success') == 1:
                    camera_data = self._parse_json_data(camera_result.get('data', '{}'))
                    if camera_data:
                        item_list = camera_data.get('itemList', [])
                        if isinstance(item_list, list):
                            camera_states = []
                            active_camera_models = []
                            for camera_item in item_list:
                                if not isinstance(camera_item, dict):
                                    continue
                                camera_states.append('On' if camera_item.get('itemState', 0) == 1 else 'Off')
                                if camera_item.get('itemState', 0) != 1:
                                    continue
                                camera_type_result = self.send_command(
                                    'WEB_GetCamTypeByPort',
                                    {
                                        'videosource': camera_item.get(
                                            'itemID',
                                            0,
                                        )
                                    },
                                )
                                if (
                                    camera_type_result
                                    and camera_type_result.get('success') == 1
                                ):
                                    camera_type_data = self._parse_json_data(
                                        camera_type_result.get('data', {})
                                    )
                                    camera_type = camera_type_data.get(
                                        'Param1'
                                    )
                                    active_camera_models.append(
                                        self._format_camera_connection_status(
                                            camera_type
                                        )
                                    )
                            if camera_states:
                                status['camera_status'] = ''.join(camera_states)
                            if active_camera_models:
                                status['camera_connection_status'] = (
                                    '; '.join(
                                        dict.fromkeys(
                                            active_camera_models
                                        )
                                    )
                                )
                            elif camera_states and not any(state == 'On' for state in camera_states):
                                status['camera_connection_status'] = (
                                    'Камера не подключена'
                                )
                            print(f"Статус камеры: {status.get('camera_status')}")
            except Exception as e:
                self._report_exception("Camera-status request", e)
            
            print(f"Сбор статуса завершен. Получено полей: {len(status)}")
            
        except Exception as e:
            self._report_exception("Status collection", e)
        
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
            'model': status.get('model', 'Huawei TE40'),
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
    
    
    def set_sip_server(self, sip_address="link.ru") -> bool:
        """
        Установка адреса SIP сервера на кодеке Huawei TE40
        """
        self._debug("\n=== set_sip_server called ===")
        self._debug(f"IP: {self.ip_address}")
        self._debug(f"Session ID: {self.session_id}")
        self._debug(f"CSRF Token: {self.csrf_token}")
        self._debug(f"SIP Address: {sip_address}")
        
        if not self.is_connected():
            self._debug("Not connected, trying to connect...")
            if not self.connect():
                self._debug("Failed to connect")
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
                self._debug("CSRF token added to request data")
            else:
                self._debug("No CSRF token available")
            
            self._debug({"request_data": data})
            
            # Отправляем команду сохранения конфигурации
            url = f"{self.base_url}/action.cgi?ActionID=WEB_SaveCfgParamAPI&rmd={random.random()}"
            self._debug(f"Request URL: {url}")
            
            headers = {
                'Content-Type': 'application/json',
                'Sessionid': self.session_id
            }
            self._debug({"headers": headers})
            
            data_bytes = json.dumps(data).encode('utf-8')
            self._debug(f"Data bytes length: {len(data_bytes)}")
            
            request = urllib.request.Request(
                url,
                data=data_bytes,
                headers=headers,
                method='POST'
            )
            
            self._debug("Sending request...")
            response = self.opener.open(request, timeout=10)
            response_text = response.read().decode('utf-8')
            result = json.loads(response_text)
            self._log_response(200, result)
            self._debug({"response": result})
            
            if result and result.get('success') == 1:
                self._debug(f"✓ SIP server set successfully: {sip_address}")
                return True
            else:
                self._debug({"set_sip_server_result": result})
                return False
                
        except Exception as e:
            self._report_exception("SIP-server update", e)
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
            self._log_response(200, result)
            
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
            self._report_exception("SIP-server verification", e)
            return None

    def get_volume_range(self):
        return 0, 21

    def get_sleep_mode(self) -> str:
        """Получить режим сна."""
        result = self.send_command('get_system_sleep')
        if not result or result.get('success') != 1:
            raise CommandError("TE40 sleep state is unavailable")

        data = result.get('data', {})
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as error:
                raise ProtocolError("TE40 sleep state is malformed") from error

        if not isinstance(data, dict):
            raise ProtocolError("TE40 sleep state is not an object")

        return 'On' if data.get('isSystemSleep') == 'sleep' else 'Off'

    def get_live_audio_status(self) -> Dict[str, Any]:
        """Return one authoritative sleep/audio sample for interactive polling."""
        sleep_mode = self.get_sleep_mode()
        result = self.send_command("get_monitor_audio_params")
        if not isinstance(result, dict) or result.get("success") != 1:
            raise CommandError("TE40 live-audio read was rejected")
        data = result.get("data", {})
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as error:
                raise ProtocolError("TE40 live-audio data is malformed") from error
        if not isinstance(data, dict):
            raise ProtocolError("TE40 live-audio data is not an object")
        return {"sleep_mode": sleep_mode, "audio": data}

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
            raise CommandError("TE40 presentation state is unavailable")

        data = result.get('data', {})
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as error:
                raise ProtocolError("TE40 presentation state is malformed") from error

        if not isinstance(data, dict):
            raise ProtocolError("TE40 presentation state is not an object")

        return 'Start' if data.get('isSendAux') == 'auxOpen' else 'Stop'

    def set_presentation(self, value: str) -> bool:
        command_map = {
            'Start': 'WEB_StartSendAuxStreamAPI',
            'Stop': 'WEB_StopSendAuxStreamAPI',
        }
        command = command_map.get(value)
        if not command:
            raise ValueError("Presentation value must be 'Start' or 'Stop'")

        self.last_presentation_error_message = None
        payload = {
            "acCSRFToken": self.csrf_token or "",
        }
        result = self.send_command(command, payload)
        if result and result.get('success') == 1:
            return True

        # Некоторые TE40 меняют статус, но не возвращают success=1 на set-команду.
        time.sleep(0.5)
        if self.get_presentation_status() == value:
            return True

        error = result.get('error', {}) if isinstance(result, dict) else {}
        error_id = error.get('id') if isinstance(error, dict) else None
        error_code = error.get('code') if isinstance(error, dict) else None
        if (
            value == 'Start'
            and error_id == 100666963
            and error_code == 100687877
        ):
            self.last_presentation_error_message = (
                "Нет видеосигнала на презентационном входе TE-40. "
                "Подключите источник и повторите попытку "
                "(id 100666963, code 100687877)."
            )
        elif error_id is not None or error_code is not None:
            self.last_presentation_error_message = (
                "TE-40 не подтвердил команду презентации "
                f"(id {error_id}, code {error_code})."
            )
        else:
            self.last_presentation_error_message = (
                "TE-40 не подтвердил команду презентации."
            )
        return False

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
        expected_state = 'Muted' if muted else 'Unmuted'
        return self.get_microphone_volume() == expected_state

    def _read_full_microphone_state(self) -> Dict[str, Any] | None:
        """Read the only safe authority for a TE40 full-state save."""
        result = self.send_command('get_audio_status')
        if not isinstance(result, dict) or result.get('success') != 1:
            return None
        data = self._parse_json_data(result.get('data', {}))
        if not isinstance(data, dict):
            return None
        return data

    @classmethod
    def _complete_microphone_save_state(cls, data: Dict[str, Any] | None) -> bool:
        return isinstance(data, dict) and all(key in data for key in cls._MICROPHONE_SAVE_FIELDS)

    def set_microphone_gain(self, target_wire: int) -> Dict[str, Any]:
        """Set TE40 MIC1 gain by one already-resolved wire target.

        The method owns a fresh full pre-read and post-read so that no caller
        can accidentally build a native full-state payload from dashboard
        cache.  A pre-submit failure is returned distinctly; any failure after
        the save may have changed device state and is raised for fail-closed
        mutation handling.
        """
        if isinstance(target_wire, bool) or not isinstance(target_wire, int) or not 0 <= target_wire <= 21:
            raise CommandError('TE40 MIC1 gain target is outside 0..21')
        baseline = self._read_full_microphone_state()
        if not self._complete_microphone_save_state(baseline):
            return {'pre_submit_failure': True}
        payload = {key: baseline[key] for key in self._MICROPHONE_SAVE_FIELDS}
        payload['mic1Value'] = target_wire
        acknowledgement = self.send_command('WEB_SaveAudioMicCtrlParams', payload)
        if not isinstance(acknowledgement, dict) or acknowledgement.get('success') != 1:
            raise CommandError('TE40 microphone gain command was not acknowledged')
        observed = self._read_full_microphone_state()
        if not self._complete_microphone_save_state(observed):
            raise CommandError('TE40 microphone gain readback is incomplete')
        if observed.get('mic1Value') != target_wire:
            raise CommandError('TE40 microphone gain readback did not confirm MIC1')
        for key in self._MICROPHONE_SAVE_FIELDS:
            if key == 'mic1Value':
                continue
            if observed.get(key) != baseline.get(key):
                raise CommandError('TE40 microphone gain readback found collateral change')
        return {'confirmed': True, 'microphone_volume': target_wire}

    def set_microphone_volume(self, value: int) -> bool:
        # Legacy screen compatibility only.  Room MIC1 gain uses the safe
        # full-state method above and never maps numeric value to mute.
        return self.set_microphone_mute(int(value) <= 0)

    def get_microphone_volume(self) -> Optional[str]:
        """Return authoritative TE40 microphone mute state for reconciliation."""

        result = self.send_command('get_audio_status')
        if not isinstance(result, dict) or result.get('success') != 1:
            return None

        audio_data = result.get('data')
        if isinstance(audio_data, str):
            try:
                audio_data = json.loads(audio_data)
            except json.JSONDecodeError as error:
                raise ProtocolError("TE40 audio-status data is malformed") from error
        if not isinstance(audio_data, dict) or 'MicSwitch' not in audio_data:
            return None

        mic_switch = audio_data['MicSwitch']
        if isinstance(mic_switch, bool):
            return None
        if mic_switch in (0, '0'):
            return 'Muted'
        if mic_switch in (1, '1'):
            return 'Unmuted'
        return None
