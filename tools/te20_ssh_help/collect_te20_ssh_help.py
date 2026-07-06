import argparse
import getpass
import json
import re
import socket
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

import paramiko


ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
PLACEHOLDER_CHARS = set("<>[]()|")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text).replace("\r", "")


def prompt_value(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


class SSHHelpCollector:
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int,
        timeout: float,
        idle_timeout: float,
        max_depth: int,
    ) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.idle_timeout = idle_timeout
        self.max_depth = max_depth
        self.client: paramiko.SSHClient | None = None
        self.channel: paramiko.Channel | None = None
        self.transport: paramiko.Transport | None = None
        self.remote_banner: str = ""

    @staticmethod
    def _prefer_supported(current: Tuple[str, ...], preferred: Tuple[str, ...]) -> Tuple[str, ...]:
        ordered: List[str] = []
        for algo in preferred:
            if algo in current and algo not in ordered:
                ordered.append(algo)
        for algo in current:
            if algo not in ordered:
                ordered.append(algo)
        return tuple(ordered)

    def connect(self) -> None:
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        sock.settimeout(self.timeout)

        self.transport = paramiko.Transport(sock)
        security = self.transport.get_security_options()
        security.kex = self._prefer_supported(
            security.kex,
            (
                "diffie-hellman-group1-sha1",
                "diffie-hellman-group14-sha1",
                "diffie-hellman-group14-sha256",
                "diffie-hellman-group-exchange-sha1",
                "diffie-hellman-group-exchange-sha256",
                "ecdh-sha2-nistp256",
            ),
        )
        security.ciphers = self._prefer_supported(
            security.ciphers,
            (
                "aes128-cbc",
                "aes256-cbc",
                "3des-cbc",
                "aes128-ctr",
                "aes256-ctr",
            ),
        )
        security.key_types = self._prefer_supported(
            security.key_types,
            (
                "ssh-rsa",
                "ssh-dss",
            ),
        )

        self.transport.start_client(timeout=self.timeout)
        self.remote_banner = self.transport.remote_version or ""
        self.transport.auth_password(self.username, self.password)
        if not self.transport.is_authenticated():
            raise paramiko.AuthenticationException("SSH password authentication was not accepted")

        self.channel = self.transport.open_session(timeout=self.timeout)
        self.channel.get_pty(width=160, height=4000)
        self.channel.invoke_shell()
        self.channel.settimeout(self.timeout)
        time.sleep(1.0)
        self._read_until_idle()
        self._clear_current_line()

    def close(self) -> None:
        if self.channel is not None:
            self.channel.close()
            self.channel = None
        if self.transport is not None:
            self.transport.close()
            self.transport = None
        if self.client is not None:
            self.client.close()
            self.client = None

    def _read_until_idle(self) -> str:
        if self.channel is None:
            raise RuntimeError("SSH channel is not connected")

        chunks: List[str] = []
        last_data_at = time.monotonic()
        started_at = time.monotonic()

        while True:
            if self.channel.recv_ready():
                data = self.channel.recv(65535).decode("utf-8", errors="replace")
                chunks.append(data)
                last_data_at = time.monotonic()
                continue

            now = time.monotonic()
            if chunks and now - last_data_at >= self.idle_timeout:
                break
            if now - started_at >= self.timeout:
                break
            time.sleep(0.1)

        return strip_ansi("".join(chunks))

    def _send(self, data: str) -> None:
        if self.channel is None:
            raise RuntimeError("SSH channel is not connected")
        self.channel.send(data)

    def _clear_current_line(self) -> str:
        self._send("\x15")
        time.sleep(0.1)
        self._send("\x03")
        time.sleep(0.1)
        self._send("\r")
        return self._read_until_idle()

    def query_help(self, prefix: str) -> str:
        self._clear_current_line()
        query = f"{prefix}?" if prefix else "?"
        self._send(query)
        time.sleep(0.4)
        output = self._read_until_idle()
        self._clear_current_line()
        return output

    @staticmethod
    def _looks_like_placeholder(token: str) -> bool:
        return any(ch in PLACEHOLDER_CHARS for ch in token)

    def parse_candidates(self, prefix: str, raw_output: str) -> List[str]:
        candidates: List[str] = []
        seen: Set[str] = set()

        for line in raw_output.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped == "?" or stripped.endswith("?"):
                continue
            if stripped.startswith(("Info:", "Warning:", "Error:")):
                continue
            if stripped.startswith(("<", "[", "*", "^")):
                continue

            token = stripped.split()[0]
            if token in {"?", "<cr>"}:
                continue
            if self._looks_like_placeholder(token):
                continue
            if token == prefix.strip():
                continue
            if token not in seen:
                seen.add(token)
                candidates.append(token)

        return candidates

    def collect(self) -> Dict[str, Dict[str, object]]:
        results: Dict[str, Dict[str, object]] = {}
        visited: Set[str] = set()
        queue: deque[Tuple[str, int]] = deque([("", 0)])

        while queue:
            prefix, depth = queue.popleft()
            if prefix in visited:
                continue
            visited.add(prefix)

            print(f"[scan] depth={depth} prefix={prefix or '<root>'}")
            raw_output = self.query_help(prefix)
            candidates = self.parse_candidates(prefix, raw_output)
            results[prefix] = {
                "depth": depth,
                "candidates": candidates,
                "raw_output": raw_output,
            }

            if depth >= self.max_depth:
                continue

            for candidate in candidates:
                next_prefix = f"{prefix}{candidate} ".strip() + " "
                if next_prefix not in visited:
                    queue.append((next_prefix, depth + 1))

        return results


def build_output_dir(base_dir: Path, host: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_host = host.replace(":", "_")
    output_dir = base_dir / "output" / f"{safe_host}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_outputs(output_dir: Path, results: Dict[str, Dict[str, object]], meta: Dict[str, object]) -> None:
    (output_dir / "session.json").write_text(
        json.dumps({"meta": meta, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines: List[str] = []
    lines.append("TE20 SSH help dump")
    lines.append("")
    for key, value in meta.items():
        lines.append(f"{key}: {value}")
    lines.append("")

    for prefix, entry in results.items():
        label = prefix or "<root>"
        lines.append(f"=== {label} ===")
        lines.append(f"depth: {entry['depth']}")
        lines.append("candidates: " + ", ".join(entry["candidates"]))
        lines.append("")
        raw_output = str(entry["raw_output"]).rstrip()
        lines.append(raw_output if raw_output else "<no output>")
        lines.append("")

    (output_dir / "session.txt").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect TE20 SSH help using '?' prompts.")
    parser.add_argument("--host", help="Endpoint IP or hostname.")
    parser.add_argument("--username", help="SSH username.")
    parser.add_argument("--password", help="SSH password.")
    parser.add_argument("--port", type=int, default=22, help="SSH port. Default: 22")
    parser.add_argument("--timeout", type=float, default=8.0, help="Socket timeout in seconds.")
    parser.add_argument(
        "--idle-timeout",
        type=float,
        default=0.8,
        help="How long to wait for shell output to go idle.",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Maximum recursion depth for help traversal.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    host = args.host or prompt_value("TE20 IP")
    username = args.username or prompt_value("SSH username", "debug")
    password = args.password or getpass.getpass("SSH password: ")

    script_dir = Path(__file__).resolve().parent
    output_dir = build_output_dir(script_dir, host)

    collector = SSHHelpCollector(
        host=host,
        username=username,
        password=password,
        port=args.port,
        timeout=args.timeout,
        idle_timeout=args.idle_timeout,
        max_depth=args.max_depth,
    )

    try:
        print(f"[connect] ssh://{host}:{args.port}")
        collector.connect()
        if collector.remote_banner:
            print(f"[debug] remote_banner={collector.remote_banner}")
        results = collector.collect()
    except paramiko.AuthenticationException as exc:
        print(f"[debug] exception_type={type(exc).__name__}", file=sys.stderr)
        print(f"[error] Authentication failed: {exc}", file=sys.stderr)
        return 1
    except (paramiko.SSHException, socket.error, TimeoutError) as exc:
        print(f"[debug] exception_type={type(exc).__name__}", file=sys.stderr)
        if hasattr(exc, "args"):
            print(f"[debug] exception_args={exc.args}", file=sys.stderr)
        print(f"[error] SSH connection failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[debug] exception_type={type(exc).__name__}", file=sys.stderr)
        if hasattr(exc, "args"):
            print(f"[debug] exception_args={exc.args}", file=sys.stderr)
        print(f"[error] Unexpected failure: {exc}", file=sys.stderr)
        return 1
    finally:
        collector.close()

    meta = {
        "host": host,
        "port": args.port,
        "username": username,
        "max_depth": args.max_depth,
        "timeout": args.timeout,
        "idle_timeout": args.idle_timeout,
        "collected_at": datetime.now().isoformat(timespec="seconds"),
    }
    write_outputs(output_dir, results, meta)

    print(f"[done] Saved help dump to {output_dir}")
    print(f"[done] Text report: {output_dir / 'session.txt'}")
    print(f"[done] JSON report: {output_dir / 'session.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
