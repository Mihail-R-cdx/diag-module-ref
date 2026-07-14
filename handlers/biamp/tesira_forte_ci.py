"""Read-only Biamp Tesira Forte CI audio signal status handler."""

from __future__ import annotations

from dataclasses import dataclass
import re
import socket
import time
from typing import Any, Protocol

from core.exceptions import AuthenticationError, CommandError, ConnectionError


class BiampSession(Protocol):
    transport: str
    port: int

    def send_command(self, command: str) -> str:
        """Send one LF-terminated Tesira Text Protocol command."""

    def close(self) -> None:
        """Close the session."""


class BiampSessionManager(Protocol):
    def connect(
        self,
        *,
        ip_address: str,
        username: str,
        password: str,
        timeout_seconds: float,
    ) -> BiampSession:
        """Connect through SSH first, then Telnet fallback."""


class BiampTesiraForteCIHandler:
    """Collect read-only Input/Meter subscription values from Tesira TTP."""

    model = "Biamp Tesira Forte CI"
    manufacturer = "Biamp"
    update_interval_ms = 500

    def __init__(
        self,
        ip_address: str,
        username: str,
        password: str,
        *,
        transport: BiampSessionManager | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.ip_address = ip_address
        self.username = username
        self.password = password
        self.timeout_seconds = timeout_seconds
        self.transport = transport or _DefaultBiampSessionManager()
        self._session: BiampSession | None = None
        self._cached_status: dict[str, Any] | None = None

    def connect(self) -> bool:
        if not self.username or not self.password:
            raise AuthenticationError("Credentials are required before connecting to Biamp.")
        self._session = self.transport.connect(
            ip_address=self.ip_address,
            username=self.username,
            password=self.password,
            timeout_seconds=self.timeout_seconds,
        )
        self._cached_status = None
        return True

    def get_status(self) -> dict[str, Any]:
        if self._session is None:
            raise ConnectionError("Biamp handler is not connected")
        if self._cached_status is None:
            self._cached_status = self._load_signal_sources(self._session)
        return dict(self._cached_status)

    def disconnect(self) -> None:
        if self._session is not None:
            self._session.close()
        self._session = None
        self._cached_status = None

    def _load_signal_sources(self, session: BiampSession) -> dict[str, Any]:
        alias_response = session.send_command("SESSION get aliases")
        aliases = _parse_aliases(alias_response)
        selected_aliases = [
            alias
            for alias in aliases
            if _is_candidate_source(alias) and not _is_output_alias(alias)
        ]
        issues: list[dict[str, str]] = []
        signal_sources: list[dict[str, Any]] = []

        for index, alias in enumerate(selected_aliases, start=1):
            subscribed = False
            for attribute in _attributes_for_alias(alias):
                label = _subscription_label(alias, attribute, index)
                command = f"{alias} subscribe {attribute} {label} {self.update_interval_ms}"
                response = session.send_command(command)
                if _is_error_response(response):
                    issues.append(_issue("unsupported_signal_source", alias))
                    continue
                values = _parse_subscription_values(response, expected_token=label)
                if not values:
                    issues.append(_issue("empty_signal_source", alias))
                    subscribed = True
                    break
                signal_sources.append(
                    {
                        "alias": alias,
                        "subscription_attribute": attribute,
                        "update_interval_ms": self.update_interval_ms,
                        "rows": [
                            {
                                "channel_number": channel_number,
                                "value": value,
                                "state": _state_for_value(value),
                            }
                            for channel_number, value in enumerate(values, start=1)
                        ],
                    }
                )
                subscribed = True
                break
            if not subscribed:
                issues.append(_issue("unsupported_signal_source", alias))

        if selected_aliases and not signal_sources:
            raise CommandError("Biamp selected Input/Meter sources returned no useful values")
        if not selected_aliases:
            raise CommandError("Biamp alias discovery found no approved Input/Meter sources")

        return {
            "device_info": {
                "model": self.model,
                "manufacturer": self.manufacturer,
                "ip_address": self.ip_address,
            },
            "signal_sources": signal_sources,
            "issues": issues,
            "ip_address": self.ip_address,
            "model": self.model,
            "manufacturer": self.manufacturer,
            "type": "audio_dsp",
            "connection_profile": {
                "protocol": session.transport,
                "port": session.port,
            },
        }


@dataclass
class _DefaultBiampSessionManager:
    ssh_port: int = 22
    telnet_port: int = 23

    def connect(
        self,
        *,
        ip_address: str,
        username: str,
        password: str,
        timeout_seconds: float,
    ) -> BiampSession:
        errors: list[str] = []
        try:
            return _ParamikoBiampSession.open(
                ip_address, self.ssh_port, username, password, timeout_seconds
            )
        except Exception as exc:
            errors.append(f"ssh:{self.ssh_port} {_safe_message(exc, password)}")
        try:
            return _TelnetBiampSession.open(
                ip_address, self.telnet_port, username, password, timeout_seconds
            )
        except Exception as exc:
            errors.append(f"telnet:{self.telnet_port} {_safe_message(exc, password)}")
        raise ConnectionError(
            "Biamp connection failed through approved transports: " + "; ".join(errors)
        )


class _ParamikoBiampSession:
    transport = "ssh"

    def __init__(self, client: Any, channel: Any, port: int, timeout_seconds: float) -> None:
        self.client = client
        self.channel = channel
        self.port = port
        self.timeout_seconds = timeout_seconds

    @classmethod
    def open(
        cls,
        ip_address: str,
        port: int,
        username: str,
        password: str,
        timeout_seconds: float,
    ) -> "_ParamikoBiampSession":
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            ip_address,
            port=port,
            username=username,
            password=password,
            timeout=timeout_seconds,
            banner_timeout=timeout_seconds,
            auth_timeout=timeout_seconds,
            look_for_keys=False,
            allow_agent=False,
        )
        channel = client.invoke_shell()
        channel.settimeout(timeout_seconds)
        return cls(client, channel, port, timeout_seconds)

    def send_command(self, command: str) -> str:
        self.channel.send((command.rstrip("\n") + "\n").encode("ascii"))
        return _read_until_ttp_complete(
            lambda: self.channel.recv(4096).decode("utf-8", errors="replace"),
            timeout_seconds=self.timeout_seconds,
        )

    def close(self) -> None:
        try:
            self.channel.close()
        finally:
            self.client.close()


class _TelnetBiampSession:
    transport = "telnet"

    def __init__(self, tn: Any, port: int, timeout_seconds: float) -> None:
        self.tn = tn
        self.port = port
        self.timeout_seconds = timeout_seconds

    @classmethod
    def open(
        cls,
        ip_address: str,
        port: int,
        username: str,
        password: str,
        timeout_seconds: float,
    ) -> "_TelnetBiampSession":
        import telnetlib

        tn = telnetlib.Telnet(ip_address, port, timeout_seconds)
        _telnet_write_login(tn, username, password, timeout_seconds)
        return cls(tn, port, timeout_seconds)

    def send_command(self, command: str) -> str:
        self.tn.write((command.rstrip("\n") + "\n").encode("ascii"))
        return _read_until_ttp_complete(
            lambda: self.tn.read_very_eager().decode("utf-8", errors="replace"),
            timeout_seconds=self.timeout_seconds,
        )

    def close(self) -> None:
        self.tn.close()


def _telnet_write_login(tn: Any, username: str, password: str, timeout_seconds: float) -> None:
    banner = tn.read_until(b"login:", timeout_seconds)
    if b"login:" in banner.lower():
        tn.write(username.encode("ascii") + b"\n")
        tn.read_until(b"assword:", timeout_seconds)
        tn.write(password.encode("ascii") + b"\n")


def _read_until_ttp_complete(read_once: Any, *, timeout_seconds: float) -> str:
    deadline = time.monotonic() + timeout_seconds
    chunks: list[str] = []
    while time.monotonic() < deadline:
        try:
            chunk = read_once()
        except socket.timeout:
            chunk = ""
        if chunk:
            chunks.append(chunk)
            joined = "".join(chunks)
            if "+OK" in joined or "-ERR" in joined:
                return joined
        time.sleep(0.05)
    return "".join(chunks)


def _parse_aliases(text: str) -> list[str]:
    match = re.search(r'"list"\s*:\s*\[(?P<body>.*?)\]', text, re.DOTALL)
    if not match:
        raise CommandError("Biamp alias discovery did not return a list")
    return re.findall(r'"([^"]+)"', match.group("body"))


def _is_candidate_source(alias: str) -> bool:
    return any(token in alias for token in ("Input", "input", "Meter", "meter"))


def _is_output_alias(alias: str) -> bool:
    return re.fullmatch(r"Output\d*", alias) is not None


def _attributes_for_alias(alias: str) -> tuple[str, ...]:
    is_input = "Input" in alias or "input" in alias
    is_meter = "Meter" in alias or "meter" in alias
    if is_input and is_meter:
        return ("peaks", "levels")
    if is_input:
        return ("peaks",)
    if is_meter:
        return ("levels",)
    return ()


def _subscription_label(alias: str, attribute: str, index: int) -> str:
    safe_alias = re.sub(r"[^A-Za-z0-9]+", "", alias) or "Source"
    return f"Diag{index}{safe_alias}{attribute}"


def _is_error_response(text: str) -> bool:
    return "-ERR" in text


def _parse_subscription_values(text: str, *, expected_token: str) -> list[Any]:
    token_match = re.search(r'"publishToken"\s*:\s*"([^"]+)"', text)
    if token_match and token_match.group(1) != expected_token:
        return []
    value_match = re.search(r'"value"\s*:\s*\[(?P<body>.*?)\]', text, re.DOTALL)
    if value_match:
        return [_parse_scalar(item) for item in value_match.group("body").split()]
    scalar_match = re.search(r'"value"\s*:\s*(?P<value>[^\s\r\n]+)', text)
    if scalar_match:
        return [_parse_scalar(scalar_match.group("value"))]
    return []


def _parse_scalar(value: str) -> Any:
    stripped = value.strip().strip('"')
    lowered = stripped.lower()
    if lowered == "false":
        return False
    if lowered == "true":
        return True
    try:
        if "." in stripped:
            return float(stripped)
        return int(stripped)
    except ValueError:
        return stripped


def _state_for_value(value: Any) -> str | None:
    if isinstance(value, bool):
        return "present" if value else "absent"
    if value is None:
        return "unknown"
    return None


def _issue(code: str, source: str) -> dict[str, str]:
    return {"code": code, "message": f"Biamp signal source issue: {source}", "source": source}


def _safe_message(exc: BaseException, password: str) -> str:
    message = str(exc)
    if password:
        message = message.replace(password, "***")
    return message


__all__ = ["BiampSession", "BiampSessionManager", "BiampTesiraForteCIHandler"]
