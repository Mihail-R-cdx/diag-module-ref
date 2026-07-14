import json
import re
import ssl
import time
from http.cookiejar import CookieJar
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPSHandler, HTTPCookieProcessor, Request, build_opener

import paramiko

from core.exceptions import AuthenticationError, CommandError, ConnectionError


class PolycomRPG310Handler:
    """Handler for Polycom RealPresence Group 310 over HTTPS REST."""

    CONFIG_NAMES = [
        "softupdate.webui.systemimage",
        "system.info.humanreadableversion",
        "system.info.systemname",
        "system.network.wired.ipv4nic.address",
        "system.network.wired.ethernet.macaddress",
        "comm.nics.sipnic.sipusername",
        "comm.callpreference.sipenable",
        "comm.nics.h323nic.h323extension",
        "system.info.serialnumber",
        "system.info.model",
        "system.info.humanreadablemodel",
    ]

    def __init__(
        self,
        ip_address: str,
        port: int = 443,
        username: str = "admin",
        password: str = None,
        timeout: int = 10,
    ):
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.base_url = f"https://{self.ip_address}" if self.port == 443 else f"https://{self.ip_address}:{self.port}"
        self.opener = None
        self.authenticated = False
        self.ssh_port = 22
        self.ssh_client: Optional[paramiko.SSHClient] = None
        self.ssh_channel: Optional[paramiko.Channel] = None
        self.buffer_size = 65535
        self.regex_patterns = {
            "volume": re.compile(r"volume\s+(\d+)", re.IGNORECASE),
            "mic_mute": re.compile(r"mute near\s+(on|off)", re.IGNORECASE),
            "camera_source": re.compile(r"camera near source\s+(-?\d)", re.IGNORECASE),
            "camera_mute": re.compile(r"videomute near\s+(on|off)", re.IGNORECASE),
        }

    def _log_command(self, message: str) -> None:
        if message.startswith("[payload]"):
            message = "[payload] <redacted>"
        elif message.startswith("[response]"):
            parts = message.split(maxsplit=2)
            prefix = " ".join(parts[:2]) if len(parts) > 1 else "[response]"
            message = f"{prefix} <body redacted>"
        elif message.startswith("[error] HTTP") and ":" in message:
            message = message.split(":", 1)[0] + ": <body redacted>"

        for secret in (self.username, self.password):
            if secret and len(str(secret)) >= 4:
                message = message.replace(str(secret), "<redacted>")

        logger = getattr(self, "command_logger", None)
        if callable(logger):
            logger(message)

    def _request_json(
        self,
        path: str,
        method: str = "GET",
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        require_auth: bool = True,
    ) -> Any:
        if self.opener is None:
            raise ConnectionError("HTTPS session is not initialized")
        if require_auth and not self.authenticated:
            raise AuthenticationError("Polycom HTTPS session is not authenticated")

        url = path if path.startswith("http") else f"{self.base_url}{path}"
        body = None
        request_headers = {
            "Accept": "*/*",
            "X-Requested-With": "XMLHttpRequest",
        }
        if headers:
            request_headers.update(headers)
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            request_headers["Content-Type"] = "application/json"

        self._log_command(f"[request] {method} {url}")
        request = Request(url, data=body, headers=request_headers, method=method)
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8-sig")
                self._log_command(f"[response] {response.status} {raw[:1000]}")
                if not raw:
                    return None
                return json.loads(raw)
        except HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            self._log_command(f"[error] HTTP {error.code} {error.reason}: {details}")
            if error.code in (401, 403):
                raise AuthenticationError(f"HTTP {error.code}: authentication failed")
            raise CommandError(f"HTTP {error.code} {error.reason}: {details}")
        except URLError as error:
            self._log_command(f"[error] connection: {error.reason}")
            raise ConnectionError(f"HTTPS connection error: {error.reason}")
        except TimeoutError:
            self._log_command("[error] connection timeout")
            raise ConnectionError("HTTPS connection timeout")
        except json.JSONDecodeError as error:
            raise CommandError(f"Invalid JSON response from Polycom: {error}")

    def connect(self) -> bool:
        if not self.username or not self.password:
            raise AuthenticationError("Credentials are required before connecting to Polycom RPG 310.")
        try:
            self._log_command(f"[connect] HTTPS:{self.port} {self.ip_address}")
            context = ssl._create_unverified_context()
            self.opener = build_opener(
                HTTPSHandler(context=context),
                HTTPCookieProcessor(CookieJar()),
            )

            result = self._request_json(
                "/rest/session",
                method="POST",
                payload={"action": "Login", "user": self.username, "password": self.password},
                headers={"Origin": self.base_url, "Referer": f"{self.base_url}/login.html"},
                require_auth=False,
            )
            if isinstance(result, dict) and result.get("success") is False:
                raise AuthenticationError("Polycom login returned success=false")

            self.authenticated = True
            self._log_command("[connect] HTTPS session established")
            return True
        except AuthenticationError:
            self.disconnect()
            raise
        except ConnectionError:
            self.disconnect()
            raise
        except Exception as error:
            self.disconnect()
            raise ConnectionError(f"Polycom HTTPS connection failed: {error}")

    def disconnect(self):
        try:
            if self.opener is not None and self.authenticated:
                try:
                    self._request_json(
                        "/rest/session",
                        method="POST",
                        payload={"action": "Logout"},
                        headers={
                            "Origin": self.base_url,
                            "Referer": f"{self.base_url}/index.html",
                        },
                    )
                    self._log_command("[disconnect] server session logged out")
                except Exception as error:
                    self._log_command(
                        "[warn] server logout failed: "
                        f"{type(error).__name__}: {error}"
                    )
        finally:
            self.opener = None
            self.authenticated = False
            self._disconnect_ssh()
            self._log_command("[disconnect] HTTPS session closed")

    def is_connected(self) -> bool:
        return bool(self.opener and self.authenticated)

    def _disconnect_ssh(self) -> None:
        try:
            if self.ssh_channel:
                self.ssh_channel.close()
            if self.ssh_client:
                self.ssh_client.close()
        finally:
            self.ssh_channel = None
            self.ssh_client = None

    def _is_ssh_connected(self) -> bool:
        return bool(self.ssh_client and self.ssh_channel and not self.ssh_channel.closed)

    def _connect_ssh(self) -> bool:
        if self._is_ssh_connected():
            return True

        try:
            self._log_command(f"[connect] ssh://{self.ip_address}:{self.ssh_port}")
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(
                hostname=self.ip_address,
                port=self.ssh_port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False,
            )
            self.ssh_channel = self.ssh_client.invoke_shell()
            time.sleep(2)
            self._clear_ssh_buffer()
            output = self._read_ssh_channel()
            if "password failed" in output.lower():
                self._disconnect_ssh()
                raise AuthenticationError("SSH authentication failed")
            self._log_command("[connect] SSH session established")
            return True
        except paramiko.AuthenticationException as error:
            self._disconnect_ssh()
            raise AuthenticationError(f"SSH authentication failed: {error}")
        except paramiko.SSHException as error:
            self._disconnect_ssh()
            raise ConnectionError(f"SSH error: {error}")
        except Exception as error:
            self._disconnect_ssh()
            raise ConnectionError(f"SSH connection failed: {error}")

    def _clear_ssh_buffer(self) -> None:
        if self.ssh_channel and self.ssh_channel.recv_ready():
            self.ssh_channel.recv(self.buffer_size)

    def _read_ssh_channel(self) -> str:
        output = ""
        if self.ssh_channel and self.ssh_channel.recv_ready():
            data = self.ssh_channel.recv(self.buffer_size)
            output = data.decode("utf-8", errors="ignore")
        return output

    def send_command(self, command: str, wait_time: float = 2.0) -> str:
        if not self._is_ssh_connected():
            self._connect_ssh()

        try:
            self._clear_ssh_buffer()
            self._log_command(f"[request] SSH {command.strip()}")
            self.ssh_channel.send(command + "\r")
            time.sleep(wait_time)
            output = self._read_ssh_channel()
            lines = output.split("\n")
            if lines and command.strip() in lines[0]:
                output = "\n".join(lines[1:])
            output = output.strip()
            self._log_command(f"[response] {output}")
            return output
        except Exception as error:
            self._log_command(f"[error] SSH {command}: {type(error).__name__}: {error}")
            raise CommandError(f"SSH command failed '{command}': {error}")

    def _ensure_connected(self) -> None:
        if not self.is_connected():
            self.connect()

    def _get_config(self, names: List[str]) -> Dict[str, Any]:
        self._ensure_connected()
        query = urlencode({"_dc": int(time.time() * 1000)})
        data = self._request_json(
            f"/rest/config?{query}",
            method="POST",
            payload={"names": names},
            headers={"Origin": self.base_url, "Referer": f"{self.base_url}/index.html"},
        )
        values: Dict[str, Any] = {}
        for item in (data or {}).get("vars", []):
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if name:
                values[name] = item.get("value")
        return values

    @staticmethod
    def _as_bool(value: Any) -> Optional[bool]:
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in {"true", "1", "yes", "on", "enabled"}:
            return True
        if text in {"false", "0", "no", "off", "disabled"}:
            return False
        return None

    def _get_conferences(self) -> Any:
        query = urlencode({"_dc": int(time.time() * 1000), "page": 1, "start": 0, "limit": 25})
        return self._request_json(f"/rest/conferences?{query}", headers={"Referer": f"{self.base_url}/index.html"})

    def _get_system_status(self) -> Any:
        query = urlencode({"_dc": int(time.time() * 1000), "page": 1, "start": 0, "limit": 25})
        return self._request_json(f"/rest/system/status?{query}", headers={"Referer": f"{self.base_url}/index.html"})

    def _get_uptime_seconds(self) -> Optional[int]:
        query = urlencode({"_dc": int(time.time() * 1000)})
        data = self._request_json(f"/rest/system/uptime?{query}", headers={"Referer": f"{self.base_url}/index.html"})
        try:
            return int(data)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _format_uptime(seconds: Optional[int]) -> Optional[str]:
        if seconds is None:
            return None
        seconds = max(0, int(seconds))
        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{days} дней {hours} часов {minutes} минут"

    @staticmethod
    def _find_status_item(data: Any, name: str) -> Optional[Dict[str, Any]]:
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = []
            for key in ("status", "items", "data", "rows"):
                value = data.get(key)
                if isinstance(value, list):
                    items = value
                    break
        else:
            items = []

        for item in items:
            if isinstance(item, dict) and item.get("name") == name:
                return item
        return None

    @staticmethod
    def _first_state_value(item: Optional[Dict[str, Any]]) -> Optional[str]:
        if not item:
            return None
        state = item.get("state")
        if isinstance(state, list) and state:
            return str(state[0]).strip().lower()
        if state is not None:
            return str(state).strip().lower()
        return None

    def _get_sip_status(self) -> Optional[str]:
        item = self._find_status_item(self._get_system_status(), "system.status.sipserver")
        state = self._first_state_value(item)
        if state == "up":
            return "online"
        if state == "down":
            return "offline"
        return state if state else None

    def _get_call_status(self) -> Optional[str]:
        item = self._find_status_item(self._get_system_status(), "system.status.inacall")
        state = self._first_state_value(item)
        if state == "on":
            return "Active"
        if state == "off":
            return "No Call"
        return state if state else None

    @staticmethod
    def _format_call_start_time(raw_value: Any) -> str:
        if raw_value in (None, ""):
            return ""
        try:
            timestamp = int(raw_value)
            if timestamp > 10_000_000_000:
                timestamp = timestamp // 1000
            return time.strftime("%d.%m.%Y %H:%M:%S", time.localtime(timestamp))
        except (TypeError, ValueError, OSError):
            return str(raw_value)

    @staticmethod
    def _format_call_duration(seconds: Any) -> str:
        try:
            seconds_int = max(0, int(seconds or 0))
        except (TypeError, ValueError):
            return ""
        hours, remainder = divmod(seconds_int, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def _format_call_rate(rate: Any) -> str:
        if rate in (None, ""):
            return ""
        try:
            return f"{int(rate)} kbps"
        except (TypeError, ValueError):
            return str(rate)

    def _parse_call_records(self, entries: Any) -> List[Dict[str, str]]:
        records = []
        if not isinstance(entries, list):
            return records

        for entry in entries[:10]:
            if not isinstance(entry, dict):
                continue
            room_number = entry.get("address") or entry.get("name") or entry.get("number") or ""
            records.append({
                "room_number": str(room_number),
                "start_time": self._format_call_start_time(entry.get("startTime")),
                "duration": self._format_call_duration(entry.get("duration")),
                "speed": self._format_call_rate(entry.get("rate")),
            })
        return records

    def get_call_records(self) -> List[Dict[str, str]]:
        self._ensure_connected()
        query = urlencode({"_dc": int(time.time() * 1000), "limit": 10})
        entries = self._request_json(
            f"/rest/calllog/entries?{query}",
            headers={"Referer": f"{self.base_url}/index.html"},
        )
        return self._parse_call_records(entries)

    def _get_audio_muted(self) -> Optional[bool]:
        query = urlencode({"_dc": int(time.time() * 1000)})
        return self._as_bool(
            self._request_json(f"/rest/audio/muted?{query}", headers={"Referer": f"{self.base_url}/index.html"})
        )

    def _get_video_muted(self) -> Optional[bool]:
        query = urlencode({"_dc": int(time.time() * 1000)})
        return self._as_bool(
            self._request_json(f"/rest/video/local/mute?{query}", headers={"Referer": f"{self.base_url}/index.html"})
        )

    @staticmethod
    def _has_active_conference(data: Any) -> bool:
        if isinstance(data, list):
            return len(data) > 0
        if isinstance(data, dict):
            for key in ("conferences", "items", "data", "rows"):
                value = data.get(key)
                if isinstance(value, list):
                    return len(value) > 0
            total = data.get("total") or data.get("totalCount")
            if isinstance(total, int):
                return total > 0
        return False

    def _populate_cli_status(self, status: Dict[str, Any], progress_callback=None, status_callback=None) -> None:
        def report(progress, message):
            if callable(status_callback):
                status_callback(message)
            if callable(progress_callback):
                progress_callback(progress)

        report(72, "Подключение по SSH: громкость динамиков...")
        try:
            response = self.send_command("volume get", wait_time=2.0)
            volume_match = self.regex_patterns["volume"].search(response)
            if volume_match:
                status["speaker_volume"] = int(volume_match.group(1)) * 2
        except Exception as error:
            self._log_command(f"[warn] SSH speaker volume failed: {error}")

        report(78, "Подключение по SSH: mute микрофона...")
        try:
            response = self.send_command("mute near get", wait_time=2.0)
            mic_match = self.regex_patterns["mic_mute"].search(response)
            if mic_match:
                status["mic_mute"] = mic_match.group(1).lower()
        except Exception as error:
            self._log_command(f"[warn] SSH microphone mute failed: {error}")

        report(84, "Подключение по SSH: статус презентации...")
        try:
            presentation_status = self.get_presentation_status()
            if presentation_status:
                status["presentation"] = presentation_status
        except Exception as error:
            self._log_command(f"[warn] SSH presentation status failed: {error}")

        report(90, "Подключение по SSH: статус камеры...")
        try:
            response = self.send_command("camera near source", wait_time=2.0)
            source_match = self.regex_patterns["camera_source"].search(response)
            if source_match:
                status["camera_source"] = int(source_match.group(1))

            response = self.send_command("videomute near get", wait_time=2.0)
            camera_match = self.regex_patterns["camera_mute"].search(response)
            if camera_match:
                status["camera_status"] = camera_match.group(1).lower()
        except Exception as error:
            self._log_command(f"[warn] SSH camera status failed: {error}")

    def get_https_status(self) -> Dict[str, Any]:
        status = {
            "model": "Polycom RealPresence Group 310",
            "ip_address": self.ip_address,
        }

        try:
            self._ensure_connected()
            config = self._get_config(self.CONFIG_NAMES)

            status["version"] = (
                config.get("system.info.humanreadableversion")
                or config.get("softupdate.webui.systemimage")
            )
            status["serial_number"] = config.get("system.info.serialnumber")
            status["mac_address"] = config.get("system.network.wired.ethernet.macaddress")
            status["sip_address"] = config.get("comm.nics.sipnic.sipusername")
            status["system_name"] = config.get("system.info.systemname")
            status["model"] = (
                config.get("system.info.humanreadablemodel")
                or config.get("system.info.model")
                or status["model"]
            )

            try:
                sip_status = self._get_sip_status()
            except Exception as error:
                self._log_command(f"[warn] SIP status failed: {error}")
                sip_status = None
            if sip_status:
                status["sip_status"] = sip_status
            else:
                sip_enabled = self._as_bool(config.get("comm.callpreference.sipenable"))
                status["sip_status"] = "N/A" if sip_enabled is None else ("online" if sip_enabled else "offline")

            try:
                uptime = self._format_uptime(self._get_uptime_seconds())
                if uptime:
                    status["uptime"] = uptime
            except Exception as error:
                self._log_command(f"[warn] uptime failed: {error}")

            try:
                call_status = self._get_call_status()
                status["call_status"] = call_status or (
                    "Active" if self._has_active_conference(self._get_conferences()) else "No Call"
                )
            except Exception as error:
                self._log_command(f"[warn] call status failed: {error}")
                status["call_status"] = "N/A"

        except Exception as error:
            status["error"] = str(error)
        return status

    def get_status(self) -> Dict[str, Any]:
        status = self.get_https_status()
        self._populate_cli_status(status)
        return status

    def get_device_info(self) -> Dict[str, Any]:
        info = {
            "model": "Polycom RealPresence Group 310",
            "ip_address": self.ip_address,
        }
        try:
            config = self._get_config([
                "system.info.model",
                "system.info.humanreadablemodel",
                "system.info.humanreadableversion",
                "softupdate.webui.systemimage",
            ])
            info["model"] = config.get("system.info.humanreadablemodel") or config.get("system.info.model") or info["model"]
            info["version"] = (
                config.get("system.info.humanreadableversion")
                or config.get("softupdate.webui.systemimage")
            )
        except Exception as error:
            self._log_command(f"[warn] device info failed: {error}")
        return info

    def get_volume_range(self):
        return 0, 100

    def set_presentation(self, value: str) -> bool:
        command_map = {
            "Start": "vcbutton play",
            "Stop": "vcbutton stop",
        }
        command = command_map.get(value)
        if not command:
            raise ValueError("Presentation value must be 'Start' or 'Stop'")

        response = self.send_command(command, wait_time=2.0)
        response_lower = response.lower()
        if "invalid" in response_lower or "error" in response_lower:
            return False
        time.sleep(0.5)
        return self.get_presentation_status() == value

    def get_presentation_status(self) -> Optional[str]:
        response = self.send_command("vcbutton get", wait_time=2.0)
        response_lower = response.lower()
        if "vcbutton play" in response_lower:
            return "Start"
        if "vcbutton stop" in response_lower:
            return "Stop"
        return None

    def set_speaker_volume(self, value: int) -> bool:
        min_value, max_value = self.get_volume_range()
        gui_value = int(value)
        if not min_value <= gui_value <= max_value:
            raise ValueError(f"Speaker volume must be in range {min_value}..{max_value}")

        device_value = round(gui_value / 2)
        response = self.send_command(f"volume set {device_value}", wait_time=2.0)
        response_lower = response.lower()
        if "invalid" in response_lower or "error" in response_lower:
            return False
        time.sleep(0.5)
        return self.get_speaker_volume() == gui_value

    def get_speaker_volume(self) -> Optional[int]:
        response = self.send_command("volume get", wait_time=2.0)
        volume_match = self.regex_patterns["volume"].search(response)
        if not volume_match:
            return None
        return int(volume_match.group(1)) * 2

    def set_microphone_mute(self, muted: bool) -> bool:
        state = "on" if muted else "off"
        response = self.send_command(f"mute near {state}", wait_time=2.0)
        response_lower = response.lower()
        if "invalid" in response_lower or "error" in response_lower:
            return False
        time.sleep(0.5)
        current_state = self.get_microphone_mute()
        return current_state == ("Muted" if muted else "Unmuted")

    def get_microphone_mute(self) -> Optional[str]:
        response = self.send_command("mute near get", wait_time=2.0)
        mic_match = self.regex_patterns["mic_mute"].search(response)
        if not mic_match:
            return None
        return "Muted" if mic_match.group(1).lower() == "on" else "Unmuted"

    def set_microphone_volume(self, value: int) -> bool:
        return self.set_microphone_mute(int(value) <= 0)

    def get_audio_status(self) -> Dict[str, Any]:
        return {"mute": self.get_microphone_mute()}

    def get_microphone_volume(self) -> Optional[str]:
        return self.get_microphone_mute()

    def verify_sip_server(self) -> Optional[str]:
        return None

    def set_sip_server(self, sip_address: str = "link.ru") -> bool:
        raise CommandError("Polycom SIP server update over HTTPS REST is not implemented yet")


PolycomRPG310Handler = PolycomRPG310Handler
