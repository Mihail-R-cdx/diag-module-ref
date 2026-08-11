"""
Обработчик для Huawei CloudLink Bar 310.
Реализует протокол взаимодействия с устройством через HTTPS API.
"""

import builtins
import requests
import json
import time
import urllib3
from datetime import datetime
from collections.abc import Mapping
from numbers import Real
from typing import Dict, Any, Optional
from requests.auth import HTTPBasicAuth
from core.base_handler import BaseHuaweiCodecHandler
from core.exceptions import (
    AuthenticationError,
    CommandError,
    ConnectionError,
    ProtocolError,
    SessionInvalidError,
)
from core.redaction import redact_diagnostic
from utils.ssl_adapter import SSLAdapter, create_legacy_ssl_context

# Отключаем предупреждения о самоподписанных сертификатах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MICROPHONE_DISPLAY_CEILING = 20.0
BOX_MICROPHONE_FIELDS = (
    "mic1ValueIndex", "mic2ValueIndex", "mic3ValueIndex", "mic4ValueIndex",
    "micArray1_01ValIdx", "micArray1_02ValIdx", "micArray1_03ValIdx",
    "micArray2_01ValIdx", "micArray2_02ValIdx", "micArray2_03ValIdx",
    "micArray3_01ValIdx", "micArray3_02ValIdx", "micArray3_03ValIdx",
)

def unavailable_microphone_sample() -> Dict[str, Any]:
    return {"available": False, "raw_level": None, "fraction": None}

def normalize_microphone_sample(values) -> Dict[str, Any]:
    valid = [value for value in values if isinstance(value, Real) and not isinstance(value, bool) and value >= 0]
    if not valid:
        return unavailable_microphone_sample()
    raw = max(valid)
    return {"available": True, "raw_level": raw, "fraction": min(float(raw) / MICROPHONE_DISPLAY_CEILING, 1.0)}

def normalize_cloudlink_bar_microphone_sample(data) -> Dict[str, Any]:
    if not isinstance(data, Mapping) or not isinstance(data.get("curMicVouumeList"), list):
        return unavailable_microphone_sample()
    return normalize_microphone_sample(entry.get("curVolume") for entry in data["curMicVouumeList"] if isinstance(entry, Mapping))

def normalize_cloudlink_box_microphone_sample(data) -> Dict[str, Any]:
    return normalize_microphone_sample(data.get(field) for field in BOX_MICROPHONE_FIELDS) if isinstance(data, Mapping) else unavailable_microphone_sample()


class CloudLinkBar310Handler(BaseHuaweiCodecHandler):
    """Обработчик для Huawei CloudLink Bar 310"""
    
    def __init__(self, ip_address: str, port: int = 443,
                 username: str = None, password: str = None,
                 use_ssl: bool = True, verify_ssl: bool = False,
                 expected_identity: str = 'Huawei CloudLink Bar 310'):
        print(f"=== CloudLinkBar310Handler.__init__ для {ip_address} ===")
        print("[INIT] Credentials загружены (значения скрыты)")
        super().__init__(ip_address, port, username, password, use_ssl, verify_ssl)
        self.device_model = expected_identity
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
        if message.startswith("[payload]"):
            message = "[payload] <redacted>"
        elif message.startswith("[response]"):
            parts = message.split(maxsplit=2)
            message = " ".join(parts[:2]) + " <body redacted>"
        else:
            for secret in (
                self.username,
                self.password,
                getattr(self, "acCSRFToken", None),
            ):
                if secret:
                    message = message.replace(str(secret), "<redacted>")
        logger = getattr(self, 'command_logger', None)
        if callable(logger):
            logger(message)
        
    def connect(self) -> bool:
        if not self.username or not self.password:
            raise AuthenticationError("Credentials are required before connecting to CloudLink Bar 310.")
        def print(*args, **kwargs):
            secrets = (self.username, self.password, self.acCSRFToken, self.session_cookie)
            if self.acCSRFToken:
                secrets += (self.acCSRFToken[:20],)
            return builtins.print(*(redact_diagnostic(value, secrets) for value in args), **kwargs)

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
                raise ProtocolError(
                    "CloudLink Bar 310 returned an unsuccessful session response"
                )
            
            # 2. Получаем CSRF Token
            endpoint = "action.cgi?ActionID=WEB_RequestCertificateAPI"
            data = {
                "user": self.username,
                "password": self.password
            }
            self._log_command(f"[request] POST {self.base_url}/{endpoint}")
            self._log_command("[payload] <redacted credentials>")
            
            print("🔐 Попытка аутентификации (credentials скрыты)")
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
                    raise ProtocolError("CloudLink Bar 310 returned no CSRF token")
            else:
                error_msg = result.get('message', 'Неизвестная ошибка') if result else 'Нет ответа'
                print(f"✗ Ошибка аутентификации: {error_msg}")
                raise ProtocolError(
                    "CloudLink Bar 310 returned an unsuccessful certificate response"
                )
                
        except (AuthenticationError, ProtocolError):
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
            self.session = None
        
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
        def print(*args, **kwargs):
            secrets = (self.username, self.password, self.acCSRFToken, self.session_cookie)
            return builtins.print(*(redact_diagnostic(value, secrets) for value in args), **kwargs)

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
                print("  -> Данные: <redacted>")
                self._log_command(f"[payload] {request_data}")
            
            response = self.session.request(
                method=method,
                url=url,
                data=request_data,
                headers=headers,
                timeout=5
            )
            self._log_command(f"[response] {response.status_code} {response.text}")
            
            print(
                f"  ! Ответ устройства (статус {response.status_code}, "
                f"тело скрыто)"
            )
            
            if response.status_code == 200:
                # Парсим ответ
                parsed_response = self._parse_response(response.text)
                if parsed_response is None:
                    raise ProtocolError("CloudLink Bar 310 returned malformed JSON")
                return parsed_response
            else:
                print(f"  ! HTTP ошибка {response.status_code}")
                if response.status_code in (401, 403):
                    login_endpoint = endpoint.endswith(
                        ("WEB_RequestSessionIDAPI", "WEB_RequestCertificateAPI")
                    )
                    error_class = AuthenticationError if login_endpoint else SessionInvalidError
                    raise error_class(
                        f"HTTP {response.status_code}: Bar 310 request was rejected"
                    )
                raise CommandError(
                    f"HTTP {response.status_code}: Bar 310 request failed"
                )
                
        except requests.exceptions.RequestException as e:
            self._log_command(f"[error] RequestException: {str(e)}")
            print(f"  ! Ошибка запроса: {e}")
            raise ConnectionError("CloudLink Bar 310 transport request failed") from e
    

    def send_command(self, command: str, data: Optional[Dict] = None) -> Dict:
        def print(*args, **kwargs):
            secrets = (self.username, self.password, self.acCSRFToken, self.session_cookie)
            return builtins.print(*(redact_diagnostic(value, secrets) for value in args), **kwargs)

        """Отправить команду устройству"""
        if not self.is_connected() or not self.acCSRFToken:
            raise ConnectionError("CloudLink Bar 310 session is not connected")
        
        endpoint = self.command_map.get(command, command)
        
        # Подготавливаем данные
        request_data = data or {}
        
        # Добавляем CSRF токен для всех action.cgi запросов
        if self.acCSRFToken and 'acCSRFToken' not in request_data:
            request_data['acCSRFToken'] = self.acCSRFToken
        
        result = self._make_request(endpoint, data=request_data if request_data else None)
        
        if result is None:
            raise ProtocolError("CloudLink Bar 310 returned no response")
        return result

    def get_live_microphone_sample(self) -> Dict[str, Any]:
        """Return the closed, model-specific live microphone observation.

        This deliberately stays outside ``get_status``: a missing telemetry
        observation is not a diagnostic-status failure.
        """
        if not self.is_connected():
            raise ConnectionError("CloudLink Bar 310 session is not connected")
        if self.device_model == "Huawei CloudLink Box 310":
            response = self.send_command("action.cgi?ActionID=WEB_GetCurrentAudioParam")
            return normalize_cloudlink_box_microphone_sample(response.get("data"))
        response = self._make_request(
            "v1/mediacontrol/mic/current-volume", method="GET"
        )
        if not isinstance(response, Mapping) or response.get("success") != 1:
            return unavailable_microphone_sample()
        return normalize_cloudlink_bar_microphone_sample(response.get("data"))


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
            raise SessionInvalidError(
                f"HTTP {response.status_code}: established Bar 310 session was rejected"
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


    @staticmethod
    def _optional_data(response: Any, endpoint: str) -> Mapping:
        if not isinstance(response, Mapping):
            raise ProtocolError(f"Bar 310 {endpoint} response is not an object")
        if response.get("success") != 1:
            raise CommandError(f"Bar 310 {endpoint} response was unsuccessful")
        data = response.get("data")
        if not isinstance(data, Mapping):
            raise ProtocolError(f"Bar 310 {endpoint} data is not an object")
        return data

    @staticmethod
    def _normalize_presentation(value: Any) -> str:
        values = {"auxOpen": "Start", "auxClose": "Stop"}
        if value not in values:
            raise ProtocolError("Bar 310 presentation state is unsupported")
        return values[value]

    @staticmethod
    def _normalize_sleep_mode(value: Any) -> str:
        values = {"sleep": "On", "unsleep": "Off"}
        if value not in values:
            raise ProtocolError("Bar 310 sleep state is unsupported")
        return values[value]

    @staticmethod
    def _nonempty_value(data: Mapping, key: str):
        value = data.get(key)
        if isinstance(value, str):
            return value if value.strip() else None
        return value if value is not None else None

    def _collect_optional(self, command: str, collector, status: Dict[str, Any]) -> None:
        try:
            observed = collector()
        except (CommandError, ProtocolError) as error:
            self._log_command(
                f"[optional] {command} unavailable: {type(error).__name__}"
            )
            return
        status.update(observed)

    def _collect_mac(self) -> Dict[str, Any]:
        data = self._optional_data(self.send_command("get_mac"), "get_mac")
        for key in ("system_wanMAC_addr", "system_lanMAC_addr"):
            value = self._nonempty_value(data, key)
            if value is not None:
                return {"mac_address": value}
        return {}

    def _collect_audio(self) -> Dict[str, Any]:
        data = self._optional_data(
            self.send_command("get_audio_status"), "get_audio_status"
        )
        observed = {}
        if data.get("MicSwitch") in (0, 1):
            observed["mic_mute"] = "On" if data["MicSwitch"] == 0 else "Off"
        if data.get("SpeakerSwitch") in (0, 1):
            observed["speaker_mute"] = "On" if data["SpeakerSwitch"] == 1 else "Off"
        if "speakerValue" in data and data["speakerValue"] is not None:
            observed["speaker_volume"] = data["speakerValue"]
        return observed

    def _collect_line_state(self) -> Dict[str, Any]:
        data = self._optional_data(self.send_command("get_line_state"), "get_line_state")
        observed = {}
        try:
            durations = [int(data[key]) for key in ("runDay", "runHour", "runMin")]
        except (KeyError, TypeError, ValueError):
            durations = None
        if durations is not None and all(value >= 0 for value in durations):
            labels = ("д", "ч", "мин")
            parts = [f"{value} {label}" for value, label in zip(durations, labels) if value]
            observed["uptime"] = " ".join(parts) if parts else "0 мин"
        for source, target in (("sipAddr", "sip_server"), ("sipNumber", "sip_number")):
            value = self._nonempty_value(data, source)
            if value is not None:
                observed[target] = value
        sip_values = {"SIP_STATE_OK": "On", "EMPTY": "Off"}
        if data.get("sipStatusTxStr") in sip_values:
            observed["sip_status"] = sip_values[data["sipStatusTxStr"]]
        return observed

    def _collect_call_status(self) -> Dict[str, Any]:
        data = self._optional_data(self.send_command("get_call_status"), "get_call_status")
        state = data.get("state")
        if not isinstance(state, Mapping):
            raise ProtocolError("Bar 310 call state is not an object")
        observed = {}
        call_states = {0: "No Call", 1: "Calling", 2: "Disconnected", 3: "Connected"}
        if state.get("callstate") in call_states:
            observed["call_status"] = call_states[state["callstate"]]
        sip_values = {1: "On", 0: "Off"}
        if state.get("sip") in sip_values:
            observed["sip_status"] = sip_values[state["sip"]]
        return observed

    def _collect_presentation(self) -> Dict[str, Any]:
        data = self._optional_data(
            self.send_command("get_presentation"), "get_presentation"
        )
        return {"presentation": self._normalize_presentation(data.get("isSendAux"))}

    def _collect_sleep_mode(self) -> Dict[str, Any]:
        data = self._optional_data(self.send_command("get_sleep_mode"), "get_sleep_mode")
        return {"sleep_mode": self._normalize_sleep_mode(data.get("isSystemSleep"))}

    def _collect_camera_status(self) -> Dict[str, Any]:
        data = self._optional_data(
            self.send_command("get_camera_status"), "get_camera_status"
        )
        source = data.get("localInMainSource")
        if source == 255:
            return {"camera_status": "On"}
        if source == 0:
            return {"camera_status": "Off"}
        raise ProtocolError("Bar 310 camera source is unsupported")

    def _collect_hd_ai_microphones(self) -> Dict[str, Any]:
        data = self._optional_data(
            self._make_request("v1/mediacontrol/mic/devices", method="GET"),
            "HD-AI microphone status",
        )
        devices = data.get("deviceList")
        if not isinstance(devices, list):
            raise ProtocolError("Bar 310 microphone device list is not a list")
        microphone = next(
            (
                item for item in devices
                if isinstance(item, Mapping) and item.get("groupName") == "HD-AI"
            ),
            None,
        )
        if microphone is None:
            return {"mic_connection_status": "Микрофон не подключён"}
        plug_status = str(microphone.get("plugStatus"))
        if plug_status == "0":
            return {"mic_connection_status": "Микрофон не подключён"}
        if plug_status != "1":
            raise ProtocolError("Bar 310 microphone plug status is unsupported")
        if "gainVolume" not in microphone or microphone["gainVolume"] is None:
            raise ProtocolError("Bar 310 connected microphone has no gain")
        return {
            "mic_connection_status": "Подключён",
            "mic_volume": microphone["gainVolume"],
        }

    def get_status(self) -> Dict[str, Any]:
        """Collect the reviewed, read-only CloudLink Bar 310 status plan."""
        response = self.send_command("get_version")
        if not isinstance(response, Mapping):
            raise ProtocolError("Bar 310 version response is not an object")
        if response.get("success") != 1:
            raise CommandError("Bar 310 version response was unsuccessful")
        data = response.get("data")
        if not isinstance(data, Mapping):
            raise ProtocolError("Bar 310 version data is not an object")
        if "softVersion" not in data or not isinstance(data["softVersion"], str):
            raise ProtocolError("Bar 310 version evidence is missing or invalid")
        version = data["softVersion"].strip()
        if not version or version.casefold() == "unknown":
            raise ProtocolError("Bar 310 version evidence is unusable")

        status = {"model": self.device_model, "version": version}
        for source, target in (("lisence", "serial_number"), ("micVersion", "mic_version")):
            value = self._nonempty_value(data, source)
            if value is not None:
                status[target] = value

        self._collect_optional("get_mac", self._collect_mac, status)
        self._collect_optional("get_audio_status", self._collect_audio, status)
        self._collect_optional("get_line_state", self._collect_line_state, status)

        call_status = {}
        self._collect_optional("get_call_status", self._collect_call_status, call_status)
        if "call_status" in call_status:
            status["call_status"] = call_status["call_status"]
        if "sip_status" not in status and "sip_status" in call_status:
            status["sip_status"] = call_status["sip_status"]

        self._collect_optional("get_presentation", self._collect_presentation, status)
        self._collect_optional("get_sleep_mode", self._collect_sleep_mode, status)
        self._collect_optional("get_camera_status", self._collect_camera_status, status)
        self._collect_optional(
            "HD-AI microphone status", self._collect_hd_ai_microphones, status
        )
        return status
  
    # Реализация абстрактных методов
    def get_device_info(self) -> Dict[str, str]:
        """Получить информацию об устройстве"""
        status = self.get_status()
        return {
            'model': status.get('model', self.device_model),
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
        data = self._optional_data(
            self.send_command('get_presentation'), 'get_presentation'
        )
        return self._normalize_presentation(data.get('isSendAux'))
    
    def get_sleep_mode(self) -> str:
        """Получить режим сна"""
        data = self._optional_data(
            self.send_command('get_sleep_mode'), 'get_sleep_mode'
        )
        return self._normalize_sleep_mode(data.get('isSystemSleep'))

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
                    "Нет видеосигнала на презентационном входе Bar310. "
                    "Подключите источник и повторите попытку "
                    "(id 100666941, code 100687877)."
                )

        # One state-changing send only; an authoritative readback may confirm it.
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

    def set_sip_server(self, sip_address: str = "link.ru") -> bool:
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
