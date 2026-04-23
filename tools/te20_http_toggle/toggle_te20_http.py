import argparse
import getpass
import json
import random
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, List

import requests
import urllib3

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.ssl_adapter import SSLAdapter, create_legacy_ssl_context


SECURITY_CFG_KEYS = [
    "enabletelnet",
    "enable_ssh",
    "h235_policy",
    "ocs_srtp_policy",
    "web_expired_time",
    "wirelessAuxPwd_lasttime",
    "wirelessAux_OnlyForWifi",
    "wirelessAux_MoblPwdLen",
    "wirelessAux_ShdowMethod",
    "wirelessAux_conMethod",
    "code_complexity",
    "lock_user_time",
    "login_errortimes",
    "enable_http",
    "enable_3rdapicookie",
]


def prompt_value(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


class Te20HttpToggleClient:
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        verify_ssl: bool = False,
    ) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.session: requests.Session | None = None
        self.base_url = ""
        self.csrf_token = ""
        self.session_id = ""

    def _build_session(self, use_ssl: bool) -> requests.Session:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        session = requests.Session()
        session.verify = self.verify_ssl
        session.headers.update({"Content-Type": "application/json"})
        if use_ssl:
            legacy_context = create_legacy_ssl_context(verify_ssl=self.verify_ssl)
            session.mount("https://", SSLAdapter(ssl_context=legacy_context))
        return session

    @staticmethod
    def _decode_response_text(response: requests.Response) -> str:
        return response.content.decode("utf-8", errors="replace")

    def _parse_json_response(self, response: requests.Response) -> Dict[str, Any]:
        return json.loads(self._decode_response_text(response))

    def _extract_data(self, result: Dict[str, Any]) -> Dict[str, Any]:
        data = result.get("data", {})
        if isinstance(data, str):
            return json.loads(data)
        if isinstance(data, dict):
            return data
        return {}

    def _log(self, message: str) -> None:
        print(message)

    def _request(self, action_id: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        if self.session is None:
            raise RuntimeError("Session is not initialized")
        url = f"{self.base_url}/action.cgi?ActionID={action_id}&rmd={random.random()}"
        self._log(f"[request] POST {url}")
        if payload is not None:
            self._log(f"[payload] {json.dumps(payload, ensure_ascii=False)}")
            response = self.session.post(url, json=payload, timeout=10)
        else:
            response = self.session.post(url, data="", timeout=10)
        text = self._decode_response_text(response)
        self._log(f"[response] {response.status_code} {text}")
        response.raise_for_status()
        return self._parse_json_response(response)

    def _connect_once(self, use_ssl: bool) -> bool:
        scheme = "https" if use_ssl else "http"
        port = 443 if use_ssl else 80
        self.base_url = f"{scheme}://{self.host}:{port}"
        self.session = self._build_session(use_ssl=use_ssl)
        self.csrf_token = ""
        self.session_id = ""
        self._log(f"[connect] trying {self.base_url}")

        session_result = self._request("WEB_RequestSessionIDAPI")
        session_data = self._extract_data(session_result)
        self.session_id = self.session.cookies.get("SessionID", "") or session_data.get("acSessionId", "")

        token_result = self._request(
            "WEB_RequestCertificateAPI",
            {"user": self.username, "password": self.password},
        )
        token_data = self._extract_data(token_result)
        self.csrf_token = token_data.get("acCSRFToken", "")

        if self.csrf_token:
            try:
                self._request("WEB_ChangeSessionIDAPI")
                self.session_id = self.session.cookies.get("SessionID", "") or self.session_id
            except Exception as exc:
                self._log(f"[warn] WEB_ChangeSessionIDAPI failed: {type(exc).__name__}: {exc}")

        return bool(self.csrf_token)

    def connect(self, scheme: str) -> bool:
        attempts: List[bool]
        if scheme == "http":
            attempts = [False]
        elif scheme == "https":
            attempts = [True]
        else:
            attempts = [False, True]

        last_error: Exception | None = None
        for use_ssl in attempts:
            try:
                if self._connect_once(use_ssl=use_ssl):
                    return True
            except Exception as exc:
                last_error = exc
                self._log(f"[warn] {type(exc).__name__}: {exc}")

        if last_error is not None:
            raise last_error
        return False

    def get_security_config(self) -> Dict[str, int]:
        if not self.csrf_token:
            raise RuntimeError("CSRF token was not obtained")
        result = self._request(
            "WEB_GetCfgParamAPI",
            {"CfgIDString": SECURITY_CFG_KEYS, "acCSRFToken": self.csrf_token},
        )
        data = self._extract_data(result)
        return {key: int(data[key]) for key in SECURITY_CFG_KEYS if key in data}

    def save_security_config(self, config: Dict[str, int]) -> Dict[str, Any]:
        payload = {
            "CfgItemInt": [{"CfgItemID": key, "CfgItemInfo": int(value)} for key, value in config.items()],
            "CfgItemString": [],
            "acCSRFToken": self.csrf_token,
        }
        return self._request("WEB_SaveCfgParamAPI", payload)

    def close(self) -> None:
        if self.session is not None:
            self.session.close()
            self.session = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enable or disable TE20 HTTP via WEB_SaveCfgParamAPI.")
    parser.add_argument("--host", help="TE20 IP address or hostname.")
    parser.add_argument("--username", help="API username.")
    parser.add_argument("--password", help="API password.")
    parser.add_argument("--scheme", choices=["auto", "http", "https"], default="auto")
    parser.add_argument("--mode", choices=["enable", "disable"], help="Target HTTP state.")
    parser.add_argument("--verify-ssl", action="store_true", help="Verify HTTPS certificate.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    host = args.host or prompt_value("TE20 IP")
    username = args.username or prompt_value("API username", "api")
    password = args.password or getpass.getpass("API password: ")
    mode = args.mode or prompt_value("Mode", "enable").lower()
    if mode not in {"enable", "disable"}:
        print("[error] Mode must be 'enable' or 'disable'")
        return 1

    client = Te20HttpToggleClient(
        host=host,
        username=username,
        password=password,
        verify_ssl=args.verify_ssl,
    )

    try:
        if not client.connect(args.scheme):
            print("[error] Could not establish a TE20 API session")
            return 1

        current = client.get_security_config()
        if "enable_http" not in current:
            print("[error] enable_http was not returned by WEB_GetCfgParamAPI")
            return 1

        target_value = 1 if mode == "enable" else 0
        print(f"[state] current enable_http={current['enable_http']}")
        if current["enable_http"] == target_value:
            print("[done] enable_http already has the requested value")
            return 0

        updated = dict(current)
        updated["enable_http"] = target_value
        save_result = client.save_security_config(updated)
        if save_result.get("success") != 1:
            print(f"[error] Save failed: {save_result}")
            return 1

        verified = client.get_security_config()
        print(f"[state] new enable_http={verified.get('enable_http')}")
        if verified.get("enable_http") != target_value:
            print("[error] Verification failed: enable_http did not change")
            return 1

        print(f"[done] enable_http set to {target_value}")
        return 0
    except Exception as exc:
        print(f"[error] {type(exc).__name__}: {exc}")
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
