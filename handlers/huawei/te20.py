import requests
import json
import re
import time
import sys
import io
import os
import ssl
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional
from core.base_handler import BaseHuaweiCodecHandler
from core.exceptions import AuthenticationError, ConnectionError
from utils.ssl_adapter import SSLAdapter, create_legacy_ssl_context

try:
    import pycurl
except ImportError:
    pycurl = None

# Настройка вывода для Windows-консоли. В GUI/IDE sys.stdout может быть
# перенаправлен в текстовый поток (например, TTYOutStream) без атрибута buffer.
def _configure_stdout_utf8() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if not callable(reconfigure):
        return

    try:
        reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, TypeError, ValueError):
        # Кодировка вывода не должна мешать импорту обработчика.
        pass


_configure_stdout_utf8()

class HuaweiTE20Handler(BaseHuaweiCodecHandler):
    @staticmethod
    def inspect_https_stack() -> Dict[str, Any]:
        """Return TE20 HTTPS transport diagnostics before any network activity starts."""
        result = {
            "ready": False,
            "transport": "requests/OpenSSL",
            "details": ssl.OPENSSL_VERSION,
            "warning": "",
        }

        if pycurl is None:
            result["warning"] = (
                "Для TE20 по HTTPS требуется pycurl с backend Schannel. "
                "В текущем Python модуль pycurl не найден."
            )
            return result

        pycurl_version = pycurl.version
        result["details"] = pycurl_version

        if os.name == "nt":
            if "Schannel" in pycurl_version:
                result["ready"] = True
                result["transport"] = "pycurl/Schannel"
                return result

            result["transport"] = "pycurl"
            result["warning"] = (
                "Для TE20 по HTTPS на Windows требуется pycurl, собранный с Schannel. "
                f"Текущий backend: {pycurl_version}"
            )
            return result

        result["transport"] = "pycurl"
        result["warning"] = (
            "Текущий HTTPS transport для TE20 проверен только на Windows с pycurl/Schannel. "
            f"Текущий backend: {pycurl_version}"
        )
        return result
    """Обработчик для Huawei TE20 с рабочей реализацией подключения"""
    
    def __init__(self, ip_address: str, port: int = 80,
                 username: str = None, password: str = None,
                 use_ssl: bool = False, verify_ssl: bool = False):
        super().__init__(ip_address, port, username, password, use_ssl, verify_ssl)
        self.device_model = 'Huawei TE20'
        self.session_id = None
        self.csrf_token = None
        self.session = None
        self._cookie_jar_path = None
        self._use_pycurl_transport = bool(self.use_ssl and pycurl is not None)
        
        # В базовом классе credentials хранятся в self.credentials
        # а username/password как отдельные атрибуты не сохраняются!
        auth_username = username
        auth_password = password
        
        self._init_http_session()
        self._connected = False
        
        protocol = 'https' if use_ssl else 'http'
        self.base_url = f"{protocol}://{ip_address}:{port}"

    def _init_http_session(self) -> None:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.session = requests.Session()
        self.session.verify = self.verify_ssl
        self.session.headers.update({"Content-Type": "application/json"})
        if self.use_ssl:
            legacy_context = create_legacy_ssl_context(verify_ssl=self.verify_ssl)
            self.session.mount("https://", SSLAdapter(ssl_context=legacy_context))

    @staticmethod
    def _decode_response_text(response: requests.Response) -> str:
        """Decode TE20 responses as UTF-8 because the device often omits charset metadata."""
        return response.content.decode('utf-8', errors='replace')

    def _parse_json_response(self, response: requests.Response) -> Dict[str, Any]:
        """Parse JSON from raw response bytes to avoid requests charset guesswork."""
        return json.loads(self._decode_response_text(response))

    def _ensure_cookie_jar(self) -> str:
        if self._cookie_jar_path and os.path.exists(self._cookie_jar_path):
            return self._cookie_jar_path

        fd, cookie_jar_path = tempfile.mkstemp(prefix="te20_cookie_", suffix=".txt")
        os.close(fd)
        self._cookie_jar_path = cookie_jar_path
        return cookie_jar_path

    def _pycurl_request(
        self,
        url: str,
        *,
        data: str = "",
        headers: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        if pycurl is None:
            raise ConnectionError("pycurl недоступен для HTTPS транспорта TE20")

        body = io.BytesIO()
        response_headers = io.BytesIO()
        curl = pycurl.Curl()
        cookie_jar_path = self._ensure_cookie_jar()

        curl.setopt(pycurl.URL, url)
        curl.setopt(pycurl.POST, 1)
        curl.setopt(pycurl.POSTFIELDS, data)
        curl.setopt(pycurl.SSL_VERIFYPEER, 1 if self.verify_ssl else 0)
        curl.setopt(pycurl.SSL_VERIFYHOST, 2 if self.verify_ssl else 0)
        curl.setopt(pycurl.CONNECTTIMEOUT, 10)
        curl.setopt(pycurl.TIMEOUT, 20)
        curl.setopt(pycurl.HEADERFUNCTION, response_headers.write)
        curl.setopt(pycurl.WRITEFUNCTION, body.write)
        curl.setopt(pycurl.COOKIEFILE, cookie_jar_path)
        curl.setopt(pycurl.COOKIEJAR, cookie_jar_path)
        curl.setopt(pycurl.FOLLOWLOCATION, 0)
        curl.setopt(pycurl.HTTP_VERSION, pycurl.CURL_HTTP_VERSION_1_1)
        curl.setopt(pycurl.USERAGENT, "TE20Diag/1.0")

        if headers:
            curl.setopt(pycurl.HTTPHEADER, headers)

        try:
            curl.perform()
            return {
                "status_code": curl.getinfo(pycurl.RESPONSE_CODE),
                "text": body.getvalue().decode("utf-8", errors="replace"),
                "headers": response_headers.getvalue().decode("utf-8", errors="replace"),
            }
        except pycurl.error as e:
            raise ConnectionError(str(e)) from e
        finally:
            curl.close()

    def _parse_json_text(self, response_text: str) -> Dict[str, Any]:
        return json.loads(response_text)

    def _get_session_cookie(self) -> str:
        if not self.session:
            return ""
        return self.session.cookies.get("SessionID", "")

    def _get_session_cookie_from_jar(self) -> str:
        cookie_jar_path = self._cookie_jar_path
        if not cookie_jar_path or not os.path.exists(cookie_jar_path):
            return ""

        try:
            with open(cookie_jar_path, "r", encoding="utf-8", errors="replace") as cookie_file:
                for line in cookie_file:
                    if line.startswith("#") or not line.strip():
                        continue
                    parts = line.strip().split("\t")
                    if len(parts) >= 7 and parts[-2] == "SessionID":
                        return parts[-1]
        except OSError:
            return ""

        return ""

    def _refresh_session_id_from_cookie(self) -> None:
        cookie_session_id = self._get_session_cookie()
        if cookie_session_id:
            self.session_id = cookie_session_id

    def _refresh_session_id(self) -> None:
        if self._use_pycurl_transport:
            cookie_session_id = self._get_session_cookie_from_jar()
            if cookie_session_id:
                self.session_id = cookie_session_id
            return
        self._refresh_session_id_from_cookie()

    def _build_session_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.session_id:
            headers["Sessionid"] = self.session_id
        return headers

    def _change_session_id(self) -> bool:
        action_id = "WEB_ChangeSessionID" if self._use_pycurl_transport else "WEB_ChangeSessionIDAPI"
        change_url = f"{self.base_url}/action.cgi?ActionID={action_id}"
        self._log_command(f"[request] POST {change_url}")

        if self._use_pycurl_transport:
            response = self._pycurl_request(change_url, headers=self._build_web_headers())
            status_code = response["status_code"]
            response_text = response["text"]
            result = self._parse_json_text(response_text)
        else:
            response_raw = self.session.post(change_url, data="", headers=self._build_session_headers(), timeout=10)
            status_code = response_raw.status_code
            response_text = self._decode_response_text(response_raw)
            result = self._parse_json_response(response_raw)

        self._log_command(f"[response] {status_code} {response_text}")

        if status_code in (401, 403):
            raise AuthenticationError(
                f"HTTP {status_code}: Ошибка аутентификации при смене Session ID"
            )

        if result.get("success") != 1:
            error_info = result.get("error", result.get("exception", "Unknown error"))
            self._log_command(f"[warn] Session ID rotation failed: {error_info}")
            return False

        previous_session_id = self.session_id
        self._refresh_session_id()
        if self.session_id and self.session_id != previous_session_id:
            self._log_command("[state] Session ID cookie rotated successfully")
        return bool(self.session_id)

    def _build_web_headers(self, *, include_json: bool = False) -> list[str]:
        headers = [
            "Accept: */*",
            "X-Requested-With: XMLHttpRequest",
            "userType: web",
            f"Origin: {self.base_url}",
            f"Referer: {self.base_url}/login.html",
        ]
        if include_json:
            headers.append("Content-Type: application/json")
        return headers

    def _connect_https_pycurl(self) -> bool:
        auth_username = self.credentials.get('username', 'api')
        auth_password = self.credentials.get('password', '')

        session_url = f"{self.base_url}/action.cgi?ActionID=Web_RequestSessionID"
        self._log_command(f"[request] POST {session_url}")
        try:
            session_response = self._pycurl_request(session_url, headers=self._build_web_headers())
            self._log_command(f"[response] {session_response['status_code']} {session_response['text']}")
            result = self._parse_json_text(session_response["text"])
            self._refresh_session_id()
            if result.get("success") != 1:
                self._log_command(f"[warn] Session ID request returned unsuccessful result: {result.get('error', result.get('exception', result))}")
            if self.session_id:
                self._log_command("[state] Session ID cookie was received")
            else:
                self._log_command("[state] Session ID cookie was not received")
        except Exception as e:
            self._log_command(f"[error] {type(e).__name__} while requesting Session ID: {e}")
            self.session_id = ""

        token_url = f"{self.base_url}/action.cgi?ActionID=Web_RequestCertificate"
        token_data = {"user": auth_username, "password": auth_password}
        self._log_command(f"[request] POST {token_url}")
        self._log_command("[payload] <redacted credentials>")
        try:
            token_response = self._pycurl_request(
                token_url,
                data=json.dumps(token_data, ensure_ascii=False),
                headers=self._build_web_headers(include_json=True),
            )
            self._log_command(f"[response] {token_response['status_code']} {token_response['text']}")
            token_result = self._parse_json_text(token_response["text"])
            if token_result.get("success") == 1 and token_result.get("data"):
                token_data_parsed = json.loads(token_result["data"])
                self.csrf_token = token_data_parsed.get("acCSRFToken")
            else:
                error_info = token_result.get("error", token_result.get("exception", token_result))
                error_str = str(error_info).lower()
                error_code = error_info.get("code") if isinstance(error_info, dict) else None
                error_id = error_info.get("id") if isinstance(error_info, dict) else None
                if (
                    "authentication" in error_str
                    or "auth" in error_str
                    or "401" in error_str
                    or error_code == 16781315
                    or error_id == 100666780
                ):
                    raise AuthenticationError(f"Ошибка аутентификации при получении CSRF токена: {error_info}")
                self.csrf_token = None
                self._log_command(f"[warn] CSRF request returned unsuccessful result: {error_info}")
        except AuthenticationError:
            raise
        except Exception as e:
            self._log_command(f"[error] {type(e).__name__} while requesting CSRF token: {e}")
            self.csrf_token = None

        if self.csrf_token:
            try:
                if not self._change_session_id():
                    self._log_command("[warn] Session ID change did not return a new cookie")
            except Exception as e:
                self._log_command(f"[warn] Session ID change failed: {type(e).__name__}: {e}")

        if not self.session_id and not self.csrf_token:
            self._connected = False
            self._log_command("[connect] device responded but returned neither SessionID cookie nor CSRF token")
            return False

        self._connected = True
        return True
    
    def connect(self) -> bool:
        """Установка соединения с кодеком Huawei TE20"""
        try:
            if self._use_pycurl_transport:
                return self._connect_https_pycurl()

            if self.session is None:
                self._init_http_session()
            print(f"Подключаюсь к {self.base_url}/")
            
            # Получаем логин и пароль из credentials базового класса
            auth_username = self.credentials.get('username', 'api')
            auth_password = self.credentials.get('password', '')
            
            print("Использую credentials: <redacted>")
            
            # 1. Получение SessionID
            try:
                session_url = f"{self.base_url}/action.cgi?ActionID=WEB_RequestSessionIDAPI"
                self._log_command(f"[request] POST {session_url}")
                session_response = self.session.post(session_url, data="", timeout=10)
                session_response_text = self._decode_response_text(session_response)
                self._log_command(f"[response] {session_response.status_code} {session_response_text}")
                print(f"Ответ Session ID: {session_response_text}")
                
                # Проверяем HTTP статус код
                if session_response.status_code == 401 or session_response.status_code == 403:
                    raise AuthenticationError(f"HTTP {session_response.status_code}: Ошибка аутентификации при получении Session ID")
                
                result = self._parse_json_response(session_response)
                
                self._refresh_session_id()

                # Проверяем наличие поля data
                if 'data' in result and result['data']:
                    try:
                        data = json.loads(result['data'])
                        self.session_id = self.session_id or data.get("acSessionId", "")
                    except json.JSONDecodeError:
                        print("[WARN] Не удалось распарсить Session ID data как JSON")
                        self._refresh_session_id()
                else:
                    print("[WARN] Поле data отсутствует или пустое в ответе Session ID")
                    self._refresh_session_id()
                
                # Проверяем наличие ошибки в ответе
                if 'code' in result:
                    error_code = result['code']
                    error_msg = result.get('msg', '')
                    if error_code == 16781313:  # Превышение лимита пользователей
                        print(f"[ERROR] Ошибка подключения: {error_msg} (код: {error_code})")
                        print("[ERROR] Превышен лимит активных сессий. Попробуйте позже.")
                        self.session_id = ""
                        return False
                    elif error_code != 0:
                        print(f"[WARN] Ошибка при получении Session ID (код: {error_code}): {error_msg}")

                error_info = result.get('error') if isinstance(result, dict) else None
                if isinstance(error_info, dict):
                    error_code = error_info.get('code')
                    error_msg = error_info.get('msg') or error_info.get('id', '')
                    if error_code == 16781313:
                        print(f"[ERROR] Ошибка подключения: {error_msg} (код: {error_code})")
                        print("[ERROR] Переполнен лимит активных сессий на устройстве.")
                        self.session_id = ""
                        return False
                    elif error_code not in (None, 0):
                        print(f"[WARN] Ошибка при получении Session ID (код: {error_code}): {error_msg}")
                
                if self.session_id:
                    print(f"[OK] SessionID получен: {self.session_id}")
                    self._log_command("[state] Session ID cookie was received")
                else:
                    self._log_command("[state] Session ID cookie was not received")
                
            except requests.exceptions.HTTPError as e:
                self._log_command(f"[error] HTTPError while requesting Session ID: {e}")
                if e.response.status_code in (401, 403):
                    raise AuthenticationError(f"HTTP {e.response.status_code}: Ошибка аутентификации при получении Session ID")
                raise ConnectionError(f"HTTP ошибка при получении Session ID: {e}")
            except Exception as e:
                self._log_command(f"[error] {type(e).__name__} while requesting Session ID: {e}")
                # Проверяем, не ошибка ли это аутентификации по тексту ошибки
                error_str = str(e).lower()
                if "authentication" in error_str or "401" in error_str or "403" in error_str:
                    raise AuthenticationError(f"Ошибка аутентификации при получении Session ID: {str(e)}")
                print(f"[WARN] Ошибка получения Session ID (не критично): {type(e).__name__}: {str(e)}")
                self._refresh_session_id()
            
            # 2. Получение CSRF токена
            try:
                print("Получаю CSRF Token...")
                token_url = f"{self.base_url}/action.cgi?ActionID=WEB_RequestCertificateAPI"
                token_data = {"user": auth_username, "password": auth_password}
                self._log_command(f"[request] POST {token_url}")
                self._log_command("[payload] <redacted credentials>")
                
                token_response = self.session.post(
                    token_url,
                    json=token_data,
                    headers=self._build_session_headers(),
                    timeout=10,
                )
                token_response_text = self._decode_response_text(token_response)
                self._log_command(f"[response] {token_response.status_code} {token_response_text}")
                
                # Проверяем HTTP статус код
                if token_response.status_code == 401 or token_response.status_code == 403:
                    raise AuthenticationError(f"HTTP {token_response.status_code}: Ошибка аутентификации при получении CSRF токена")
                
                print(f"Ответ CSRF Token: {token_response_text}")
                
                token_result = self._parse_json_response(token_response)
                
                # Проверяем успешность запроса
                if token_result.get('success') == 1:
                    # Если есть поле data и оно не пустое
                    if 'data' in token_result and token_result['data']:
                        try:
                            token_data_parsed = json.loads(token_result['data'])
                            self.csrf_token = token_data_parsed.get("acCSRFToken")
                            print(f"[OK] CSRF токен получен: {self.csrf_token}")
                        except json.JSONDecodeError:
                            print("[WARN] Не удалось распарсить CSRF data как JSON")
                            self.csrf_token = None
                    else:
                        print("[WARN] Поле data отсутствует или пустое в ответе CSRF")
                        self.csrf_token = None
                else:
                    # Запрос не успешен - проверяем, не ошибка ли это аутентификации
                    error_info = token_result.get('error', token_result.get('exception', 'Unknown error'))
                    error_str = str(error_info).lower()
                    error_code = error_info.get('code') if isinstance(error_info, dict) else None
                    error_id = error_info.get('id') if isinstance(error_info, dict) else None
                    if (
                        "authentication" in error_str
                        or "auth" in error_str
                        or "401" in error_str
                        or error_code == 16781315
                        or error_id == 100666780
                    ):
                        raise AuthenticationError(f"Ошибка аутентификации при получении CSRF токена: {error_info}")
                    print(f"[WARN] CSRF Token запрос не успешен: {error_info}")
                    self.csrf_token = None
                    
            except requests.exceptions.HTTPError as e:
                self._log_command(f"[error] HTTPError while requesting CSRF token: {e}")
                if e.response.status_code in (401, 403):
                    raise AuthenticationError(f"HTTP {e.response.status_code}: Ошибка аутентификации при получении CSRF токена")
                print(f"[WARN] HTTP ошибка при получении CSRF токена: {e}")
                self.csrf_token = None
            except Exception as e:
                self._log_command(f"[error] {type(e).__name__} while requesting CSRF token: {e}")
                # Проверяем, не ошибка ли это аутентификации
                error_str = str(e).lower()
                if "authentication" in error_str or "401" in error_str or "403" in error_str:
                    raise AuthenticationError(f"Ошибка аутентификации при получении CSRF токена: {str(e)}")
                print(f"[WARN] Ошибка получения CSRF токена: {type(e).__name__}: {str(e)}")
                self.csrf_token = None

            # HTTPS web transport needs session rotation; HTTP:80 follows the reference driver
            # and keeps using the Sessionid returned by WEB_RequestSessionIDAPI.
            if self.csrf_token and self._use_pycurl_transport:
                try:
                    if not self._change_session_id():
                        self._log_command("[warn] Session ID change did not return a new cookie")
                except AuthenticationError:
                    raise
                except Exception as e:
                    self._log_command(f"[warn] Session ID change failed: {type(e).__name__}: {e}")

            if not self.csrf_token:
                self._connected = False
                print("[WARN] Устройство ответило, но не выдало CSRF token")
                return False

            self._connected = True
            if self.session_id and self.csrf_token:
                print("[OK] Подключение к устройству установлено, Session ID и CSRF token получены")
            elif self.csrf_token:
                print("[OK] Подключение к устройству установлено по CSRF token")
            else:
                print("[OK] Подключение к устройству установлено по Session ID")
            return True
            
        except AuthenticationError:
            # Пробрасываем AuthenticationError дальше
            raise
        except Exception as e:
            print(f"[ERROR] Критическая ошибка подключения: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise ConnectionError(f"Ошибка подключения: {str(e)}")

    def disconnect(self) -> None:
        """Разорвать соединение"""
        if self._use_pycurl_transport:
            self._connected = False
            self.session_id = None
            self.csrf_token = None
            if self._cookie_jar_path:
                try:
                    os.remove(self._cookie_jar_path)
                except OSError:
                    pass
                self._cookie_jar_path = None
            return

        # Отправляем запрос на выход из сессии
        if self._connected and self.session_id:
            try:
                print("Выхожу из сессии...")
                logout_url = f"{self.base_url}/action.cgi?ActionID=WEB_LogoutAPI"
                
                # Отправляем запрос без обработки ошибок, так как это финальный вызов
                self.session.post(logout_url, headers=self._build_session_headers(), timeout=5)
                print("[OK] Выход из сессии выполнен")
            except Exception as e:
                print(f"[WARN] Ошибка при выходе из сессии: {type(e).__name__}: {str(e)}")
        
        self._connected = False
        self.session_id = None
        self.csrf_token = None
        if self.session:
            self.session.close()
            self.session = None
        if self._cookie_jar_path:
            try:
                os.remove(self._cookie_jar_path)
            except OSError:
                pass
            self._cookie_jar_path = None
    
    def _clean_version_string(self, version_string: str) -> str:
        """Очистка строки версии от служебных символов"""
        if not version_string:
            return "Unknown"
        # Заменяем проблемные escape последовательности
        cleaned = re.sub(r'\\[a-zA-Z]', '', version_string)
        # Удаляем TE20 из начала строки если есть
        cleaned = cleaned.replace("TE20 ", "")
        # Удаляем лишние пробелы
        cleaned = ' '.join(cleaned.split())
        return cleaned.strip()

    def _log_command(self, message: str) -> None:
        if message.startswith("[payload]"):
            message = "[payload] <redacted>"
        elif message.startswith("[response]"):
            parts = message.split(maxsplit=2)
            message = " ".join(parts[:2]) + " <body redacted>"
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
            logger(message)

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

        duration = ended_at - started_at
        total_seconds = max(0, int(duration.total_seconds()))
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
            data = json.loads(data)
        if not isinstance(data, dict):
            return []

        call_list = data.get("CallList", [])
        records = []
        for item in call_list[:10]:
            if not isinstance(item, dict):
                continue
            start_time = item.get("StartTime", "")
            stop_time = item.get("StopTime", "")
            room_number = item.get("aucCallCode") or item.get("aucRcdName") or ""
            records.append({
                "room_number": room_number,
                "start_time": self._format_call_start_time(start_time),
                "duration": self._format_call_duration(start_time, stop_time),
                "speed": self._format_call_rate(item.get("uwCallRate")),
            })
        return records

    def get_call_records(self) -> list[Dict[str, str]]:
        """Download and parse the latest TE20 call records."""
        if not self._connected:
            if not self.connect():
                raise ConnectionError("Не удалось подключиться к TE-20 для получения журнала звонков")

        rmd = f"{time.time() % 1:.16f}".rstrip("0")
        url = f"{self.base_url}/action.cgi?ActionID=WEB_GetP2PCallRecordsAPI?rmd={rmd}"
        payload = {"acCSRFToken": self.csrf_token or ""}
        self._log_command(f"[request] POST {url}")
        self._log_command(f"[payload] {json.dumps(payload, ensure_ascii=False)}")

        if self._use_pycurl_transport:
            response = self._pycurl_request(
                url,
                data=json.dumps(payload, ensure_ascii=False),
                headers=self._build_web_headers(include_json=True),
            )
            status_code = response["status_code"]
            response_text = response["text"]
        else:
            response = self.session.post(
                url,
                json=payload,
                headers=self._build_session_headers(),
                timeout=20,
            )
            status_code = response.status_code
            response_text = self._decode_response_text(response)

        self._log_command(f"[response] {status_code} {response_text[:500]}")
        if status_code in (401, 403):
            raise AuthenticationError(f"HTTP {status_code}: Ошибка аутентификации при получении журнала звонков")
        if status_code >= 400:
            raise ConnectionError(f"HTTP {status_code}: ошибка получения журнала звонков")

        result = json.loads(response_text)
        if result.get("success") != 1:
            raise ConnectionError(f"Кодек не вернул журнал звонков: {result.get('exception', result)}")

        return self._parse_p2p_call_records(result.get("data", {}))


    def send_command(self, command: str, data: Optional[Dict] = None) -> Dict:
        """Отправить команду устройству"""
        
        # Пытаемся подключиться, если еще не подключены
        if not self._connected:
            try:
                if not self.connect():
                    # Если не удалось подключиться, возвращаем ошибку
                    print(f"[WARN] Не удалось подключиться для команды {command}")
                    return {'success': 0, 'error': 'Not connected', 'data': {}}
            except AuthenticationError as e:
                # Пробрасываем AuthenticationError для обработки на верхнем уровне
                raise
        
        try:
            # Маппинг команд на ActionID для TE-20
            command_map = {
                'get_version': 'WEB_GetVersionInfoAPI',
                'get_call_status': 'WEB_GetMailboxDataAPI',
                'get_sip_status': 'WEB_GetLineStateInfoAPI',
                'get_audio_status': 'WEB_InitAudioCtrlParamsAPI',
                'get_monitor_audio_params': 'WEB_GetMonitorAudioParam',
                'get_presentation_local': 'WEB_IsSendAuxStreamAPI',
                'get_presentation_remote': 'WEB_IsReceiveRemAuxStrmAPI',
                'get_camera_mute': 'WEB_IsSendBlueScreen',
                'get_camera_list': 'WEB_GetLocalCameraList',
                'get_mac': 'WEB_GetSystemMacAddrAPI',
                'get_system_sleep': 'WEB_IsSystemSleepAPI',
            }
            
            action = command_map.get(command, command)
            
            url = f"{self.base_url}/action.cgi?ActionID={action}"
            
            print(f"Отправка команды {command} на {url}")
            self._log_command(f"[request] POST {url}")
            
            # Подготавливаем данные
            request_data = data or {}
            # Добавляем CSRF токен только если он есть
            if hasattr(self, 'csrf_token') and self.csrf_token and 'acCSRFToken' not in request_data:
                request_data['acCSRFToken'] = self.csrf_token
            if request_data:
                self._log_command(f"[payload] {json.dumps(request_data, ensure_ascii=False)}")
            
            # Отправляем запрос
            try:
                if self._use_pycurl_transport:
                    request_data = data or {}
                    if hasattr(self, 'csrf_token') and self.csrf_token and 'acCSRFToken' not in request_data:
                        request_data['acCSRFToken'] = self.csrf_token
                    payload = json.dumps(request_data, ensure_ascii=False) if request_data else ""
                    if request_data:
                        self._log_command(f"[payload] {payload}")
                    response = self._pycurl_request(
                        url,
                        data=payload,
                        headers=self._build_web_headers(include_json=bool(request_data)),
                    )
                    status_code = response["status_code"]
                    response_text = response["text"]
                    if status_code in (401, 403):
                        raise AuthenticationError(f"HTTP {status_code}: Ошибка аутентификации при выполнении команды {command}")
                    self._log_command(f"[response] {status_code} {response_text}")
                    print(f"Ответ {command}: {response_text[:200]}...")
                    result = self._parse_json_text(response_text)
                    if result.get('success') == 1:
                        if 'data' in result and isinstance(result['data'], str):
                            try:
                                parsed_data = json.loads(result['data'])
                                return {'success': 1, 'data': parsed_data}
                            except json.JSONDecodeError:
                                return result
                        if 'data' in result:
                            return result
                        return result

                    error_info = result.get('error', result.get('exception', ''))
                    error_str = str(error_info).lower()
                    if "authentication" in error_str or "auth" in error_str:
                        raise AuthenticationError(f"Ошибка аутентификации: {error_info}")
                    print(f"[WARN] Команда {command} вернула success=0")
                    return result

                if request_data:
                    response = self.session.post(
                        url,
                        json=request_data,
                        headers=self._build_session_headers(),
                        timeout=10,
                    )
                else:
                    response = self.session.post(url, headers=self._build_session_headers(), timeout=10)
                
                # Проверяем HTTP статус код
                if response.status_code == 401 or response.status_code == 403:
                    # Это ошибка аутентификации
                    raise AuthenticationError(f"HTTP {response.status_code}: Ошибка аутентификации при выполнении команды {command}")
                
                response_text = self._decode_response_text(response)
                self._log_command(f"[response] {response.status_code} {response_text}")
                print(f"Ответ {command}: {response_text[:200]}...")
                
                try:
                    result = self._parse_json_response(response)
                    
                    # Проверяем успешность запроса
                    if result.get('success') == 1:
                        # Пытаемся распарсить data если это строка
                        if 'data' in result and isinstance(result['data'], str):
                            try:
                                parsed_data = json.loads(result['data'])
                                return {'success': 1, 'data': parsed_data}
                            except json.JSONDecodeError:
                                # Если не парсится, возвращаем как есть
                                return result
                        elif 'data' in result:
                            # Если data уже объект, возвращаем как есть
                            return result
                        else:
                            # Если нет поля data, возвращаем весь результат
                            return result
                    else:
                        # Запрос не успешен - проверяем, не ошибка ли это аутентификации
                        error_info = result.get('error', result.get('exception', ''))
                        error_str = str(error_info).lower()
                        if "authentication" in error_str or "auth" in error_str:
                            raise AuthenticationError(f"Ошибка аутентификации: {error_info}")
                        print(f"[WARN] Команда {command} вернула success=0")
                        return result
                        
                except json.JSONDecodeError:
                    print(f"[WARN] Ответ не в JSON формате: {response_text[:100]}")
                    return {'success': 0, 'data': response_text}
                    
            except requests.exceptions.HTTPError as e:
                if e.response.status_code in (401, 403):
                    raise AuthenticationError(f"HTTP {e.response.status_code}: Ошибка аутентификации при выполнении команды {command}")
                self._log_command(f"[error] HTTPError {command}: {str(e)}")
                print(f"[WARN] Ошибка HTTP запроса для команды {command}: {type(e).__name__}: {str(e)}")
                return {'success': 0, 'error': str(e), 'data': {}}
            except Exception as e:
                # Проверяем, не ошибка ли это аутентификации
                error_str = str(e).lower()
                if "authentication" in error_str or "401" in str(e) or "403" in str(e):
                    raise AuthenticationError(f"Ошибка аутентификации при выполнении команды {command}: {str(e)}")
                self._log_command(f"[error] {type(e).__name__} {command}: {str(e)}")
                print(f"[WARN] Ошибка выполнения команды {command}: {type(e).__name__}: {str(e)}")
                return {'success': 0, 'error': str(e), 'data': {}}
            
        except AuthenticationError:
            # Пробрасываем AuthenticationError дальше
            raise
        except Exception as e:
            print(f"[WARN] Ошибка выполнения команды {command}: {type(e).__name__}: {str(e)}")
            return {'success': 0, 'error': str(e), 'data': {}}

    def get_status(self) -> Dict[str, Any]:
        """Получение полного статуса устройства"""
        status = {}
        
        try:
            print("Начинаю сбор статуса TE-20...")
            
            # 1. Получаем информацию о версии
            print("Запрос версии...")
            result = self.send_command('get_version')
            if result and result.get('success') == 1:
                data = result.get('data', {})
                # Проверяем тип data
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except json.JSONDecodeError:
                        print("[WARN] Не удалось распарсить version data как JSON")
                        data = {}
                elif not isinstance(data, dict):
                    data = {}
                
                if data:
                    soft_version = self._clean_version_string(data.get('softVersion', 'Unknown'))
                    status['version'] = soft_version
                    status['model'] = data.get('model', 'Huawei TE20')
                    status['serial_number'] = data.get('lisence', 'Unknown')
                    status['hard_version'] = data.get('hardVersion', 'N/A')
                    status['logic_version'] = data.get('logicVersion', 'N/A')
                    status['mic_version'] = data.get('micVersion', [])
                    print(f"Модель: {status.get('model')}, Версия: {soft_version}")
            
            # 2. Получаем MAC адрес
            print("Запрос MAC...")
            mac_result = self.send_command('get_mac')
            if mac_result and mac_result.get('success') == 1:
                mac_data = mac_result.get('data', {})
                # Проверяем тип mac_data
                if isinstance(mac_data, str):
                    try:
                        mac_data = json.loads(mac_data)
                    except json.JSONDecodeError:
                        print("[WARN] Не удалось распарсить mac data как JSON")
                        mac_data = {}
                elif not isinstance(mac_data, dict):
                    mac_data = {}
                
                if mac_data:
                    status['wan_mac'] = mac_data.get('system_wanMAC_addr', 'N/A')
                    status['lan_mac'] = mac_data.get('system_lanMAC_addr', 'N/A')
                    print(f"MAC WAN: {status.get('wan_mac')}")
            
            # 3. Получаем SIP информацию
            print("Запрос SIP...")
            sip_result = self.send_command('get_sip_status')
            if sip_result and sip_result.get('success') == 1:
                sip_data = sip_result.get('data', {})
                # Проверяем тип sip_data
                if isinstance(sip_data, str):
                    try:
                        sip_data = json.loads(sip_data)
                    except json.JSONDecodeError:
                        print("[WARN] Не удалось распарсить sip data как JSON")
                        sip_data = {}
                elif not isinstance(sip_data, dict):
                    sip_data = {}
                
                if sip_data:
                    sip_status = sip_data.get('sipStatusTxStr', 'EMPTY')
                    status['sip_status'] = 'On' if sip_status == 'SIP_STATE_OK' else 'Off'
                    status['sip_address'] = sip_data.get('sipAddr', 'N/A')
                    status['sip_number'] = sip_data.get('sipNumber', 'N/A')
                    status['number'] = sip_data.get('number', 'N/A')
                    status['gk_status'] = sip_data.get('gkStatusTxStr', 'N/A')
                    
                    # IP адреса
                    status['wan_ipv4'] = sip_data.get('wan_IPv4', 'N/A')
                    status['wan_ipv6'] = sip_data.get('wan_IPv6', 'N/A')
                    status['wlan_ipv4'] = sip_data.get('wlan_IPv4', 'N/A')
                    status['wlan_ipv6'] = sip_data.get('wlan_IPv6', 'N/A')
                    
                    # Время работы
                    run_day = int(sip_data.get('runDay', 0))
                    run_hour = int(sip_data.get('runHour', 0))
                    run_min = int(sip_data.get('runMin', 0))
                    
                    uptime_parts = []
                    if run_day > 0:
                        uptime_parts.append(f"{run_day} дн")
                    if run_hour > 0:
                        uptime_parts.append(f"{run_hour} ч")
                    if run_min > 0:
                        uptime_parts.append(f"{run_min} мин")
                    
                    status['uptime'] = ' '.join(uptime_parts) if uptime_parts else '0 мин'
                    
                    print(f"SIP статус: {status.get('sip_status')}")
            
            # 4. Получаем статус звонка
            print("Запрос статуса звонка...")
            call_result = self.send_command('get_call_status')
            if call_result and call_result.get('success') == 1:
                call_data = call_result.get('data', {})
                # Проверяем тип call_data
                if isinstance(call_data, str):
                    try:
                        call_data = json.loads(call_data)
                    except json.JSONDecodeError:
                        print("[WARN] Не удалось распарсить call data как JSON")
                        call_data = {}
                elif not isinstance(call_data, dict):
                    call_data = {}
                
                if call_data and 'state' in call_data:
                    state = call_data['state']
                    
                    call_status_map = {
                        0: "Нет звонка",
                        1: "Вызов",
                        2: "Отключен"
                    }
                    
                    conference_type_map = {
                        0: "Нет вызова",
                        1: "Точка-точка",
                        2: "Удаленная многоточечная",
                        3: "Локальная многоточечная",
                        4: "Каскадная"
                    }
                    
                    status['call_status'] = call_status_map.get(state.get('callstate', 0), "Неизвестно")
                    status['conference_type'] = conference_type_map.get(state.get('conftype', 0), "Неизвестно")
                    status['remote_mic_status'] = "Приглушен" if state.get('RemoteMicStates') == 1 else "Не приглушен"
                    
                    print(f"Статус звонка: {status.get('call_status')}")
            
            # 5. Получаем аудио статус
            print("Запрос аудио статуса...")
            audio_result = self.send_command('get_audio_status')
            if audio_result and audio_result.get('success') == 1:
                audio_data = audio_result.get('data', {})
                # Проверяем тип audio_data
                if isinstance(audio_data, str):
                    try:
                        audio_data = json.loads(audio_data)
                    except json.JSONDecodeError:
                        print("[WARN] Не удалось распарсить audio data как JSON")
                        audio_data = {}
                elif not isinstance(audio_data, dict):
                    audio_data = {}
                
                if audio_data:
                    mic_mute_map = {
                        0: "On (Выключен)",
                        1: "Off (Включен)"
                    }
                    
                    status['mic_mute'] = mic_mute_map.get(audio_data.get('MicSwitch', 0), "Unknown")
                    status['speaker_mute'] = mic_mute_map.get(audio_data.get('SpeakerSwitch', 0), "Unknown")
                    status['speaker_volume'] = audio_data.get('speakerValue', 0)
                    
                    # Детальная информация по микрофонам
                    mic_status = []
                    for i in range(1, 4):
                        try:
                            mic_gain = int(audio_data.get(f'mic{i}Value', 12)) - 12
                        except (TypeError, ValueError):
                            mic_gain = None
                        mic_status.append({
                            "mic": f"Mic {i}",
                            "mute_status": mic_mute_map.get(audio_data.get(f'mic{i}', 0), "Unknown"),
                            "gain": mic_gain
                        })
                        if i == 1 and mic_gain is not None:
                            status['mic_volume'] = mic_gain
                    status['microphones'] = mic_status
                    
                    print(f"Аудио статус получен")

            print("Запрос monitor audio params...")
            monitor_audio_result = self.send_command('get_monitor_audio_params')
            if monitor_audio_result and monitor_audio_result.get('success') == 1:
                monitor_audio_data = monitor_audio_result.get('data', {})
                if isinstance(monitor_audio_data, str):
                    try:
                        monitor_audio_data = json.loads(monitor_audio_data)
                    except json.JSONDecodeError:
                        print("[WARN] Не удалось распарсить monitor audio data как JSON")
                        monitor_audio_data = {}
                elif not isinstance(monitor_audio_data, dict):
                    monitor_audio_data = {}

                if monitor_audio_data:
                    status['monitor_mic_value'] = monitor_audio_data.get('MicValueIndex')
                    status['monitor_speaker_value'] = monitor_audio_data.get('SpeakerValueIndex')
                    print(
                        "Monitor audio params: "
                        f"mic={status.get('monitor_mic_value')}, "
                        f"speaker={status.get('monitor_speaker_value')}"
                    )
            
            # 6. Получаем статус презентации (локальной)
            print("Запрос локальной презентации...")
            pres_local_result = self.send_command('get_presentation_local')
            if pres_local_result and pres_local_result.get('success') == 1:
                pres_local_data = pres_local_result.get('data', {})
                # Проверяем тип pres_local_data
                if isinstance(pres_local_data, str):
                    try:
                        pres_local_data = json.loads(pres_local_data)
                    except json.JSONDecodeError:
                        print("[WARN] Не удалось распарсить presentation local data как JSON")
                        pres_local_data = {}
                elif not isinstance(pres_local_data, dict):
                    pres_local_data = {}
                
                if pres_local_data:
                    presentation = pres_local_data.get('isSendAux', 'auxClose')
                    status['presentation_local'] = 'Started' if presentation == 'auxOpen' else 'Stopped'
                    print(f"Локальная презентация: {status.get('presentation_local')}")
            
            # 7. Получаем статус презентации (удаленной)
            print("Запрос удаленной презентации...")
            pres_remote_result = self.send_command('get_presentation_remote')
            if pres_remote_result and pres_remote_result.get('success') == 1:
                pres_remote_data = pres_remote_result.get('data', {})
                # Проверяем тип pres_remote_data
                if isinstance(pres_remote_data, str):
                    try:
                        pres_remote_data = json.loads(pres_remote_data)
                    except json.JSONDecodeError:
                        print("[WARN] Не удалось распарсить presentation remote data как JSON")
                        pres_remote_data = {}
                elif not isinstance(pres_remote_data, dict):
                    pres_remote_data = {}
                
                if pres_remote_data:
                    presentation = pres_remote_data.get('isSendAux', 'auxClose')
                    status['presentation_remote'] = 'Receiving' if presentation == 'auxOpen' else 'Not Receiving'
                    print(f"Удаленная презентация: {status.get('presentation_remote')}")
            
            # 8. Получаем статус камеры (mute)
            print("Запрос mute камеры...")
            camera_mute_result = self.send_command('get_camera_mute')
            if camera_mute_result and camera_mute_result.get('success') == 1:
                camera_mute_data = camera_mute_result.get('data', {})
                # Проверяем тип camera_mute_data
                if isinstance(camera_mute_data, str):
                    try:
                        camera_mute_data = json.loads(camera_mute_data)
                    except json.JSONDecodeError:
                        print("[WARN] Не удалось распарсить camera mute data как JSON")
                        camera_mute_data = {}
                elif not isinstance(camera_mute_data, dict):
                    camera_mute_data = {}
                
                if camera_mute_data:
                    status['camera_mute'] = 'On (Выключена)' if camera_mute_data.get('Param1') == 1 else 'Off (Включена)'
                    print(f"Mute камеры: {status.get('camera_mute')}")
            
            # 9. Получаем список камер
            print("Запрос списка камер...")
            camera_list_result = self.send_command('get_camera_list')
            if camera_list_result and camera_list_result.get('success') == 1:
                camera_list_data = camera_list_result.get('data', {})
                # Проверяем тип camera_list_data
                if isinstance(camera_list_data, str):
                    try:
                        camera_list_data = json.loads(camera_list_data)
                    except json.JSONDecodeError:
                        print("[WARN] Не удалось распарсить camera list data как JSON")
                        camera_list_data = {}
                elif not isinstance(camera_list_data, dict):
                    camera_list_data = {}
                
                if camera_list_data:
                    item_list = camera_list_data.get('itemList', [])
                    if item_list and len(item_list) > 0:
                        status['camera_connected'] = item_list[0].get('itemState', 0) == 1
                        print(f"Камера подключена: {status.get('camera_connected')}")
            
            # 10. Получаем статус системы (сон/не сон)
            print("Запрос статуса питания...")
            sleep_result = self.send_command('get_system_sleep')
            if sleep_result and sleep_result.get('success') == 1:
                sleep_data = sleep_result.get('data', {})
                # Проверяем тип sleep_data
                if isinstance(sleep_data, str):
                    try:
                        sleep_data = json.loads(sleep_data)
                    except json.JSONDecodeError:
                        print("[WARN] Не удалось распарсить sleep data как JSON")
                        sleep_data = {}
                elif not isinstance(sleep_data, dict):
                    sleep_data = {}
                
                if sleep_data:
                    status['power_status'] = 'On' if sleep_data.get('isSystemSleep') == 'unsleep' else 'Sleep'
                    print(f"Статус питания: {status.get('power_status')}")
            
            print(f"Сбор статуса TE-20 завершен. Получено полей: {len(status)}")
            
        except Exception as e:
            print(f"Ошибка получения статуса: {e}")
            import traceback
            traceback.print_exc()
        
        return status


    # Реализация абстрактных методов
    def get_device_info(self) -> Dict[str, str]:
        """Получить информацию об устройстве"""
        status = self.get_status()
        return {
            'model': status.get('model', 'Huawei TE20'),
            'serial': status.get('serial_number', 'N/A'),
            'version': status.get('version', 'N/A'),
            'mac': status.get('wan_mac', 'N/A'),
            'ip': self.ip_address
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Получить системную информацию"""
        status = self.get_status()
        return {
            'uptime': status.get('uptime', 'N/A'),
            'power_status': status.get('power_status', 'N/A'),
            'temperature': 'N/A'
        }
    
    def get_call_status(self) -> Dict[str, Any]:
        """Получить статус вызова"""
        status = self.get_status()
        return {
            'status': status.get('call_status', 'Нет звонка'),
            'type': status.get('conference_type', 'none'),
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
            'wan_ipv4': status.get('wan_ipv4', 'N/A'),
            'wan_ipv6': status.get('wan_ipv6', 'N/A'),
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
            'microphone_volume': status.get('mic_volume'),
            'microphones': status.get('microphones', [])
        }
    
    def get_video_status(self) -> Dict[str, Any]:
        """Получить статус видео"""
        status = self.get_status()
        return {
            'presentation_local': status.get('presentation_local', 'Stopped'),
            'presentation_remote': status.get('presentation_remote', 'Not Receiving'),
            'camera_connected': status.get('camera_connected', False),
            'camera_mute': status.get('camera_mute', 'Off'),
            'format': '',
            'resolution': ''
        }
    
    def get_mac_address(self) -> str:
        """Получение MAC адреса"""
        device_info = self.get_device_info()
        return device_info.get('mac', 'N/A')

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
        """Получить текущий статус локальной презентации."""
        result = self.send_command('get_presentation_local')
        if not result or result.get('success') != 1:
            return 'Stopped'

        data = result.get('data', {})
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return 'Stopped'

        if not isinstance(data, dict):
            return 'Stopped'

        return 'Started' if data.get('isSendAux') == 'auxOpen' else 'Stopped'

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

        # Некоторые TE20 не выставляют success=1 для команды, но меняют состояние.
        time.sleep(0.5)
        expected_state = 'Started' if value == 'Start' else 'Stopped'
        return self.get_presentation_status() == expected_state

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

    def set_microphone_mute(self, muted: bool) -> bool:
        action = 'WEB_CloseMicAPI' if muted else 'WEB_OpenMicAPI'
        payload = {
            "audioinall": 1,
            "MicSwitch": 1 if muted else 0,
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
        # TE20 web API exposes microphone mute, not a separate microphone gain command.
        # The UI uses value 0 as muted and any positive value as unmuted.
        return self.set_microphone_mute(int(value) <= 0)

    def get_microphone_volume(self) -> Optional[int]:
        audio_status = self.get_audio_status()
        volume = audio_status.get('microphone_volume')
        try:
            return int(volume)
        except (TypeError, ValueError):
            return None
