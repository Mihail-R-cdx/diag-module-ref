"""Extron IPL T PCS4i Telnet/SIS handler."""

from __future__ import annotations

import re
import socket
import time
from typing import Any, Callable, Mapping, Optional

import requests

from core.exceptions import (
    AuthenticationError,
    CommandError,
    CommandOutcomeUnknownError,
    ConnectionError,
    CredentialRequired,
    ParseError,
    ProtocolError,
)


ESC = b"\x1b"
CR = b"\r"
LF = b"\n"


class SocketTelnetTransport:
    def __init__(self, ip_address: str, port: int, timeout: float):
        self.socket = socket.create_connection((ip_address, port), timeout=timeout)
        self.socket.settimeout(timeout)

    def recv(self, size: int = 4096) -> bytes:
        return self.socket.recv(size)

    def sendall(self, data: bytes) -> None:
        self.socket.sendall(data)

    def close(self) -> None:
        self.socket.close()


class ExtronIPLTPCS4iHandler:
    """Handler for PCS4i authoritative Telnet control and optional HTTP names."""

    OUTLET_COUNT = 4
    MODEL = "Extron IPL T PCS4i"
    HTTP_NAME_PATH: Optional[str] = None

    def __init__(
        self,
        ip_address: str,
        port: int = 23,
        password: str | None = None,
        timeout: float = 5.0,
        transport_factory: Callable[[str, int, float], Any] | None = None,
        http_get: Callable[[str, float], str] | None = None,
        http_name_path: str | None = None,
    ):
        self.ip_address = ip_address
        self.port = port
        self.password = password
        self.timeout = timeout
        self.transport_factory = transport_factory or SocketTelnetTransport
        self.http_get = http_get
        self.http_name_path = http_name_path if http_name_path is not None else self.HTTP_NAME_PATH
        self.transport = None
        self.connected = False
        self.credential_used = False

    def connect(self) -> bool:
        try:
            self.transport = self.transport_factory(self.ip_address, self.port, self.timeout)
            self._establish_session()
            self.connected = True
            return True
        except (AuthenticationError, CredentialRequired):
            self.connected = False
            self.disconnect()
            raise
        except Exception as error:
            self.connected = False
            self.disconnect()
            if isinstance(error, (ConnectionError, ProtocolError, ParseError)):
                raise
            raise ConnectionError(f"PCS4i connection failed: {type(error).__name__}") from error

    def disconnect(self) -> None:
        transport = self.transport
        self.transport = None
        self.connected = False
        if transport is not None:
            close = getattr(transport, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass

    def get_device_info(self) -> dict[str, Any]:
        self._require_connected()
        info = {
            "model": self._query_text(b"1I\r") or self.MODEL,
            "manufacturer": "Extron",
            "ip_address": self.ip_address,
            "connected": True,
        }
        description = self._query_text(b"2I\r")
        part_number = self._query_text(b"N\r")
        firmware = self._query_text(b"Q\r")
        security_level = self._query_text(ESC + b"CK" + CR)
        if description:
            info["description"] = description
        if part_number:
            info["part_number"] = part_number
        if firmware:
            info["firmware"] = firmware
        if security_level:
            info["security_level"] = security_level
        return info

    def get_outlets_status(self) -> list[dict[str, Any]]:
        self._require_connected()
        outlets = []
        for number in range(1, self.OUTLET_COUNT + 1):
            power_on = self._read_power_state(number)
            outlets.append(
                {
                    "number": number,
                    "status": "on" if power_on else "off",
                    "name": f"Receptacle {number}",
                }
            )
        for number, name in self._load_http_outlet_names().items():
            if 1 <= number <= self.OUTLET_COUNT and name:
                outlets[number - 1]["name"] = name
        return outlets

    def turn_on(self, outlet_number: int) -> bool:
        return self._set_power_state(outlet_number, True)

    def turn_off(self, outlet_number: int) -> bool:
        return self._set_power_state(outlet_number, False)

    def _set_power_state(self, outlet_number: int, target_on: bool) -> bool:
        self._require_connected()
        self._validate_outlet(outlet_number)
        pre_state = self._try_read_power_state(outlet_number)

        ambiguous = False
        try:
            self._send_power_command(outlet_number, target_on)
        except CommandOutcomeUnknownError:
            ambiguous = True

        post_state = self._try_read_power_state(outlet_number)
        if post_state is target_on:
            return True
        if pre_state is None:
            raise CommandOutcomeUnknownError("PCS4i final state is indeterminate.")
        if post_state is pre_state:
            resend_ambiguous = False
            try:
                self._send_power_command(outlet_number, target_on)
            except CommandOutcomeUnknownError:
                resend_ambiguous = True
            terminal_state = self._try_read_power_state(outlet_number)
            if terminal_state is target_on:
                return True
            if terminal_state is pre_state:
                return False
            if resend_ambiguous:
                raise CommandOutcomeUnknownError(
                    "PCS4i controlled resend acknowledgement was ambiguous and terminal confirmation is indeterminate."
                )
            raise CommandOutcomeUnknownError("PCS4i terminal confirmation is indeterminate.")
        if ambiguous:
            raise CommandOutcomeUnknownError("PCS4i delivery was ambiguous and readback was not the target.")
        return False

    def _establish_session(self) -> None:
        initial = self._read_phase()
        if self._has_password_prompt(initial):
            self._password_flow()
            return
        try:
            self._verified_readiness_probe()
        except CredentialRequired:
            self._password_flow()

    def _password_flow(self) -> None:
        if not self.password:
            raise CredentialRequired("PCS4i requested Password but no password was assigned.")
        self._send_password()
        post_first = self._read_phase()
        if self._has_password_prompt(post_first):
            self._send_password()
            post_second = self._read_phase()
            if self._has_password_prompt(post_second):
                raise AuthenticationError("PCS4i rejected the assigned password.")
            if not self._phase_has_ready_evidence(post_second):
                self._verified_readiness_probe()
            return
        if not self._phase_has_ready_evidence(post_first):
            self._verified_readiness_probe()

    def _verified_readiness_probe(self) -> None:
        response = self._query_raw(ESC + b"CK" + CR)
        if self._has_password_prompt(response):
            raise CredentialRequired("PCS4i requested Password during readiness probe.")
        text = self._clean_text(response)
        if not re.search(r"\b(11|12)\b", text):
            raise ProtocolError("PCS4i readiness probe did not return a security level.")

    def _send_password(self) -> None:
        self.credential_used = True
        self._send((self.password or "").encode("utf-8") + CR)

    @staticmethod
    def _has_password_prompt(data: bytes) -> bool:
        return b"Password" in data

    @staticmethod
    def _phase_has_ready_evidence(data: bytes) -> bool:
        text = ExtronIPLTPCS4iHandler._clean_text(data)
        return any(marker in text for marker in ("Login Administrator", "Login User")) or bool(
            re.search(r"\b(11|12)\b", text)
        )

    def _query_text(self, command: bytes) -> str:
        return self._clean_text(self._query_raw(command))

    def _query_raw(self, command: bytes) -> bytes:
        self._send(command)
        return self._read_phase()

    def _read_power_state(self, outlet_number: int) -> bool:
        self._validate_outlet(outlet_number)
        response = self._query_raw(ESC + str(outlet_number).encode("ascii") + b"PC" + CR)
        text = self._clean_text(response)
        values = re.findall(r"\b[01]\b", text)
        if len(set(values)) != 1:
            raise ParseError("PCS4i PC readback was unavailable, malformed, or conflicting.")
        return values[0] == "1"

    def _try_read_power_state(self, outlet_number: int) -> Optional[bool]:
        try:
            return self._read_power_state(outlet_number)
        except Exception:
            return None

    def get_threshold_state(self, outlet_number: int) -> str:
        self._validate_outlet(outlet_number)
        response = self._query_raw(ESC + str(outlet_number).encode("ascii") + b"PS" + CR)
        text = self._clean_text(response)
        values = re.findall(r"\b[012]\b", text)
        if len(set(values)) != 1:
            raise ParseError("PCS4i PS readback was unavailable or malformed.")
        return {"0": "clear", "1": "standby", "2": "full"}[values[0]]

    def _send_power_command(self, outlet_number: int, target_on: bool) -> None:
        value = b"1" if target_on else b"0"
        expected = f"Cpn{outlet_number} Ppc{value.decode('ascii')}"
        command = ESC + str(outlet_number).encode("ascii") + b"*" + value + b"PC" + CR
        try:
            response = self._query_raw(command)
        except Exception as error:
            raise CommandOutcomeUnknownError("PCS4i command delivery acknowledgement is unknown.") from error
        if expected not in self._clean_text(response):
            raise CommandOutcomeUnknownError("PCS4i command acknowledgement was not confirmed.")

    def _send(self, data: bytes) -> None:
        if self.transport is None:
            raise ConnectionError("PCS4i Telnet transport is not connected.")
        self.transport.sendall(data)

    def _read_phase(self) -> bytes:
        if self.transport is None:
            raise ConnectionError("PCS4i Telnet transport is not connected.")
        chunks = []
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            try:
                chunk = self.transport.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            chunks.append(chunk)
            if chunk.endswith((CR, LF)) or b"Password" in b"".join(chunks):
                break
        return b"".join(chunks)

    def _load_http_outlet_names(self) -> dict[int, str]:
        if not self.http_name_path:
            return {}
        try:
            if self.http_get is not None:
                body = self.http_get(self.http_name_path, self.timeout)
            else:
                response = requests.get(
                    f"http://{self.ip_address}{self.http_name_path}",
                    timeout=self.timeout,
                )
                if response.status_code in (401, 403):
                    return {}
                response.raise_for_status()
                body = response.text
            return self.parse_http_outlet_names(body)
        except Exception:
            return {}

    @staticmethod
    def parse_http_outlet_names(body: str) -> dict[int, str]:
        names: dict[int, str] = {}
        for match in re.finditer(r"xName([1-4])\s*=\s*['\"]([^'\"]*)['\"]", body):
            name = match.group(2).strip()
            if name:
                names[int(match.group(1))] = name
        return names

    @classmethod
    def _validate_outlet(cls, outlet_number: int) -> None:
        if outlet_number not in range(1, cls.OUTLET_COUNT + 1):
            raise ValueError("PCS4i outlet number must be in range 1..4.")

    def _require_connected(self) -> None:
        if self.transport is None or not self.connected:
            raise ConnectionError("PCS4i handler is not connected.")

    @staticmethod
    def _clean_text(data: bytes) -> str:
        return data.decode("utf-8", errors="ignore").replace("\x1b", "").strip()
