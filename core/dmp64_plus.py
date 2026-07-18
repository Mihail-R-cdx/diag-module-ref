"""Extron DMP 64 Plus meter protocol helpers.

The parser works on clean SIS frames only. SSH, PTY echo, stream buffering, and
transaction timeouts are handled here before meter payload conversion.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import socket
import time
import threading
from typing import Any, Callable, Iterable

from core.exceptions import AuthenticationError, ConnectionError, TimeoutError as DeviceTimeoutError


SELECTOR_MODEL = "Extron DMP 64 Plus"
MANUFACTURER = "Extron"
SIS_PORT = 22023
ESC = b"\x1b"
CR = b"\r"
SUPPORTED_VARIANTS = frozenset(
    {
        "DMP 64 Plus C",
        "DMP 64 Plus C AT",
        "DMP 64 Plus C V",
        "DMP 64 Plus C V AT",
    }
)


@dataclass(frozen=True)
class DMPMeterChannel:
    section: str
    name: str
    oid: int


DMP_METER_CHANNELS: tuple[DMPMeterChannel, ...] = (
    *(DMPMeterChannel("Inputs", f"Input {number}", 40000 + number - 1) for number in range(1, 7)),
    *(DMPMeterChannel("Outputs", f"Output {number}", 60000 + number - 1) for number in range(1, 5)),
)

INPUT_OIDS = tuple(channel.oid for channel in DMP_METER_CHANNELS if channel.section == "Inputs")
OUTPUT_OIDS = tuple(channel.oid for channel in DMP_METER_CHANNELS if channel.section == "Outputs")


class DMPCancelled(ConnectionError):
    """The application-owned polling context was cancelled or superseded."""


class DMPTransactionTimeout(DeviceTimeoutError):
    """A SIS transaction timed out; the current session must be abandoned."""


class DMPSessionPoisoned(ConnectionError):
    """The SIS stream can no longer safely map untagged meter payloads."""


class DMPCancellationToken:
    """Small thread-safe cancellation handle owned by the composition layer."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled():
            raise DMPCancelled("DMP polling context was cancelled.")

    def wait(self, timeout: float) -> bool:
        return self._event.wait(timeout)


def is_supported_dmp64_plus_variant(model: str | None) -> bool:
    return str(model or "").strip() in SUPPORTED_VARIANTS


def build_read_command(oid: int) -> bytes:
    return ESC + f"V{int(oid)}AU".encode("ascii") + CR


def build_recovery_command(oid: int) -> bytes:
    return ESC + f"V{int(oid)}*2AU".encode("ascii") + CR


def dbfs_from_raw_meter(raw_meter: int) -> float:
    return -(int(raw_meter) / 10.0)


def normalize_dbfs(db_value: float | int | None) -> float | None:
    if db_value is None:
        return None
    return max(0.0, min(1.0, (float(db_value) + 60.0) / 72.0))


def parse_meter_payload(payload: str) -> dict[str, Any]:
    clean = str(payload or "").strip()
    if clean == "E13":
        return {"kind": "sis_protocol_error", "code": clean, "available": False}
    match = re.fullmatch(r"(?P<state>[012])\*(?P<raw>\d+)", clean)
    if not match:
        return {"kind": "malformed_payload", "payload": clean, "available": False}
    state = int(match.group("state"))
    raw_meter = int(match.group("raw"))
    if state == 0 and raw_meter == 0:
        return {"kind": "unavailable", "state": state, "raw_meter": raw_meter, "available": False}
    if state not in {1, 2}:
        return {"kind": "malformed_payload", "payload": clean, "available": False}
    dbfs = dbfs_from_raw_meter(raw_meter)
    return {
        "kind": "valid",
        "state": state,
        "raw_meter": raw_meter,
        "dbfs": dbfs,
        "normalized": normalize_dbfs(dbfs),
        "available": True,
    }


def _clean_frame(frame: str | bytes) -> str:
    if isinstance(frame, bytes):
        text = frame.decode("utf-8", errors="ignore")
    else:
        text = str(frame)
    return text.replace("\x1b", "").strip()


def _clean_command_echo(command: bytes) -> str:
    return _clean_frame(command.rstrip(CR + b"\n"))


class DMPStreamFramer:
    """Frame CR/LF-delimited PTY stream data and filter command echo."""

    def __init__(self) -> None:
        self._buffer = ""

    def feed(self, data: bytes | str, *, command_echo: bytes | None = None) -> list[str]:
        if isinstance(data, bytes):
            text = data.decode("utf-8", errors="ignore")
        else:
            text = str(data)
        self._buffer += text
        frames: list[str] = []
        echo = _clean_command_echo(command_echo) if command_echo else None

        while True:
            indexes = [idx for idx in (self._buffer.find("\r"), self._buffer.find("\n")) if idx >= 0]
            if not indexes:
                break
            split_at = min(indexes)
            raw_frame = self._buffer[:split_at]
            self._buffer = self._buffer[split_at + 1 :]
            clean = _clean_frame(raw_frame)
            if not clean or (echo and clean == echo):
                continue
            frames.append(clean)
        return frames


class DMPTransportSession:
    """Serialized SIS transaction layer for one DMP SSH channel/session."""

    def __init__(
        self,
        channel: Any,
        *,
        close_callback: Callable[[], Any] | None = None,
        transaction_timeout: float = 1.5,
        sleep_interval: float = 0.01,
    ) -> None:
        self.channel = channel
        self.close_callback = close_callback
        self.transaction_timeout = transaction_timeout
        self.sleep_interval = sleep_interval
        self.framer = DMPStreamFramer()
        self.recovered_oids: set[int] = set()
        self.poisoned = False
        self.sent_commands: list[bytes] = []

    def close(self) -> None:
        if self.close_callback is not None:
            self.close_callback()

    def read_meter(self, oid: int, cancellation: DMPCancellationToken | None = None) -> dict[str, Any]:
        frame = self._transaction(
            build_read_command(oid),
            lambda clean: _is_meter_terminal(clean),
            cancellation,
        )
        parsed = parse_meter_payload(frame)
        parsed["payload"] = frame
        return parsed

    def recover_meter(self, oid: int, cancellation: DMPCancellationToken | None = None) -> dict[str, Any]:
        expected = f"DsV{int(oid)}*2"
        frame = self._transaction(
            build_recovery_command(oid),
            lambda clean: clean == expected or _is_sis_error(clean),
            cancellation,
        )
        if frame == expected:
            self.recovered_oids.add(int(oid))
            return {"kind": "recovery_ack", "oid": int(oid), "available": False}
        return {"kind": "sis_protocol_error", "code": frame, "available": False}

    def _transaction(
        self,
        command: bytes,
        is_expected: Callable[[str], bool],
        cancellation: DMPCancellationToken | None,
    ) -> str:
        if self.poisoned:
            raise DMPSessionPoisoned("DMP SIS session is unsafe after a transaction timeout.")
        if cancellation is not None:
            cancellation.raise_if_cancelled()

        self._send(command)
        deadline = time.monotonic() + self.transaction_timeout
        while time.monotonic() < deadline:
            if cancellation is not None:
                cancellation.raise_if_cancelled()
            try:
                chunk = self.channel.recv(4096)
            except socket.timeout:
                chunk = b""
            except Exception as error:
                raise ConnectionError(f"DMP SIS transport read failed: {type(error).__name__}") from error
            if chunk:
                for frame in self.framer.feed(chunk, command_echo=command):
                    if is_expected(frame):
                        return frame
            else:
                time.sleep(self.sleep_interval)

        self.poisoned = True
        raise DMPTransactionTimeout("DMP SIS transaction timed out; abandoning current session.")

    def _send(self, command: bytes) -> None:
        try:
            if hasattr(self.channel, "sendall"):
                self.channel.sendall(command)
            else:
                self.channel.send(command)
            self.sent_commands.append(command)
        except Exception as error:
            raise ConnectionError(f"DMP SIS transport send failed: {type(error).__name__}") from error


def _is_sis_error(frame: str) -> bool:
    return re.fullmatch(r"E\d+", frame) is not None


def _is_meter_terminal(frame: str) -> bool:
    if frame.startswith("DsV"):
        return False
    return _is_sis_error(frame) or re.fullmatch(r"\S+\*\S+", frame) is not None


def build_meter_snapshot(
    session: DMPTransportSession,
    *,
    ip_address: str,
    cancellation: DMPCancellationToken | None = None,
) -> dict[str, Any]:
    channels_by_section: dict[str, list[dict[str, Any]]] = {"Inputs": [], "Outputs": []}
    attempted_oids: list[int] = []

    for channel in DMP_METER_CHANNELS:
        if cancellation is not None:
            cancellation.raise_if_cancelled()
        parsed = session.read_meter(channel.oid, cancellation)
        attempted_oids.append(channel.oid)

        if parsed["kind"] == "unavailable" and channel.oid not in session.recovered_oids:
            if cancellation is not None:
                cancellation.raise_if_cancelled()
            recovery = session.recover_meter(channel.oid, cancellation)
            if recovery["kind"] == "recovery_ack":
                if cancellation is not None:
                    cancellation.raise_if_cancelled()
                parsed = session.read_meter(channel.oid, cancellation)

        channels_by_section[channel.section].append(_channel_result(channel, parsed))

    return {
        "device_info": {
            "model": SELECTOR_MODEL,
            "manufacturer": MANUFACTURER,
            "ip_address": ip_address,
        },
        "meter_sections": [
            {"title": "Inputs", "channels": channels_by_section["Inputs"]},
            {"title": "Outputs", "channels": channels_by_section["Outputs"]},
        ],
        "attempted_oids": attempted_oids,
        "complete": len(attempted_oids) == len(DMP_METER_CHANNELS),
        "ip_address": ip_address,
        "model": SELECTOR_MODEL,
        "manufacturer": MANUFACTURER,
        "type": "audio_dsp",
        "connection_profile": {"protocol": "sis-over-ssh", "port": SIS_PORT},
    }


def _channel_result(channel: DMPMeterChannel, parsed: dict[str, Any]) -> dict[str, Any]:
    result = {
        "name": channel.name,
        "section": channel.section,
        "oid": channel.oid,
        "available": bool(parsed.get("available")),
        "outcome": parsed.get("kind"),
    }
    if parsed.get("available"):
        result.update(
            {
                "dbfs": parsed["dbfs"],
                "raw_meter": parsed["raw_meter"],
                "state": parsed["state"],
                "normalized": parsed["normalized"],
            }
        )
    else:
        result["normalized"] = None
    if parsed.get("code"):
        result["error_code"] = parsed["code"]
    return result


def wait_cancelable(token: DMPCancellationToken | None, seconds: float) -> None:
    if seconds <= 0:
        return
    if token is None:
        time.sleep(seconds)
    elif token.wait(seconds):
        raise DMPCancelled("DMP polling context was cancelled.")


def require_assigned_credentials(username: str | None, password: str | None) -> None:
    if not username or not password:
        raise AuthenticationError("Credentials are required for Extron DMP 64 Plus before connecting.")


def flatten_snapshot_channels(snapshot: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for section in snapshot.get("meter_sections") or ():
        for channel in section.get("channels") or ():
            yield channel
