import argparse
import getpass
import json
import os
import queue
import re
import subprocess
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple


ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
PLACEHOLDER_CHARS = set("<>[]()|")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text).replace("\r", "")


def prompt_value(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def build_output_dir(base_dir: Path, host: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_host = host.replace(":", "_")
    output_dir = base_dir / "output" / f"plink_{safe_host}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


class ReaderThread(threading.Thread):
    def __init__(self, stream, output_queue: queue.Queue[str]) -> None:
        super().__init__(daemon=True)
        self.stream = stream
        self.output_queue = output_queue

    def run(self) -> None:
        while True:
            chunk = self.stream.read(1)
            if not chunk:
                break
            self.output_queue.put(chunk)


class InteractivePlinkSession:
    def __init__(self, plink_path: str, host: str, username: str, password: str, port: int, idle_timeout: float):
        self.plink_path = plink_path
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.idle_timeout = idle_timeout
        self.process: subprocess.Popen | None = None
        self.output_queue: queue.Queue[str] = queue.Queue()
        self.stdout_thread: ReaderThread | None = None
        self.stderr_thread: ReaderThread | None = None

    def start(self) -> str:
        cmd = [
            self.plink_path,
            "-ssh",
            "-t",
            "-P",
            str(self.port),
            "-l",
            self.username,
            "-pw",
            self.password,
            self.host,
        ]
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=0,
        )
        self.stdout_thread = ReaderThread(self.process.stdout, self.output_queue)
        self.stderr_thread = ReaderThread(self.process.stderr, self.output_queue)
        self.stdout_thread.start()
        self.stderr_thread.start()
        time.sleep(1.2)
        return self.read_until_idle()

    def stop(self) -> str:
        tail = ""
        if self.process is None:
            return tail

        try:
            self.send_line("\x03")
            time.sleep(0.2)
            self.send_line("exit")
            time.sleep(0.2)
            self.send_line("quit")
            time.sleep(0.2)
            self.send_line("logout")
        except Exception:
            pass

        time.sleep(0.8)
        tail = self.read_until_idle()

        if self.process.poll() is None:
            self.process.kill()
        self.process.wait(timeout=5)
        tail += self.read_until_idle()
        return tail

    def send(self, text: str) -> None:
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("plink process is not running")
        self.process.stdin.write(text)
        self.process.stdin.flush()

    def send_line(self, text: str) -> None:
        self.send(text + "\r")

    def read_until_idle(self) -> str:
        pieces: List[str] = []
        last_data_at = time.monotonic()
        saw_data = False

        while True:
            try:
                chunk = self.output_queue.get(timeout=0.1)
                pieces.append(chunk)
                saw_data = True
                last_data_at = time.monotonic()
            except queue.Empty:
                if saw_data and (time.monotonic() - last_data_at) >= self.idle_timeout:
                    break
                if not saw_data and self.process is not None and self.process.poll() is not None:
                    break
                if not saw_data and (time.monotonic() - last_data_at) >= self.idle_timeout:
                    break

        return strip_ansi("".join(pieces))


class PlinkHelpCollector:
    def __init__(
        self,
        plink_path: str,
        host: str,
        username: str,
        password: str,
        port: int,
        max_depth: int,
        idle_timeout: float,
    ) -> None:
        self.plink_path = plink_path
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.max_depth = max_depth
        self.idle_timeout = idle_timeout

    @staticmethod
    def parse_candidates(prefix: str, raw_output: str) -> List[str]:
        candidates: List[str] = []
        seen: Set[str] = set()

        for line in raw_output.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped == "?" or stripped.endswith("?"):
                continue
            if stripped.startswith(("Info:", "Warning:", "Error:", "FATAL ERROR:")):
                continue
            if stripped.startswith(("login as", "Using username", "Access granted")):
                continue
            if stripped.startswith(("<", "[", "*", "^")):
                continue

            token = stripped.split()[0]
            if token in {"?", "<cr>"}:
                continue
            if any(ch in PLACEHOLDER_CHARS for ch in token):
                continue
            if token == prefix.strip():
                continue
            if token not in seen:
                seen.add(token)
                candidates.append(token)

        return candidates

    def query_help(self, prefix: str) -> str:
        session = InteractivePlinkSession(
            plink_path=self.plink_path,
            host=self.host,
            username=self.username,
            password=self.password,
            port=self.port,
            idle_timeout=self.idle_timeout,
        )

        transcript = session.start()
        session.send("\x15")
        time.sleep(0.2)
        transcript += session.read_until_idle()

        query = f"{prefix}?".strip() if prefix else "?"
        session.send(query)
        time.sleep(1.0)
        transcript += session.read_until_idle()

        session.send("\r")
        time.sleep(0.8)
        transcript += session.read_until_idle()
        transcript += session.stop()
        return transcript

    def collect(self) -> Dict[str, Dict[str, object]]:
        results: Dict[str, Dict[str, object]] = {}
        visited: Set[str] = set()
        queue_items: deque[Tuple[str, int]] = deque([("", 0)])

        while queue_items:
            prefix, depth = queue_items.popleft()
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
                    queue_items.append((next_prefix, depth + 1))

        return results


def write_outputs(output_dir: Path, results: Dict[str, Dict[str, object]], meta: Dict[str, object]) -> None:
    (output_dir / "session.json").write_text(
        json.dumps({"meta": meta, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines: List[str] = []
    lines.append("TE20 SSH help dump via interactive plink")
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
    parser = argparse.ArgumentParser(description="Collect TE20 SSH help using interactive plink.")
    parser.add_argument("--plink-path", required=True, help="Full path to plink.exe")
    parser.add_argument("--host", help="Endpoint IP or hostname.")
    parser.add_argument("--username", help="SSH username.")
    parser.add_argument("--password", help="SSH password.")
    parser.add_argument("--port", type=int, default=22, help="SSH port. Default: 22")
    parser.add_argument("--max-depth", type=int, default=3, help="Maximum recursion depth.")
    parser.add_argument("--idle-timeout", type=float, default=1.0, help="Seconds to wait for CLI output to go idle.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    host = args.host or prompt_value("TE20 IP")
    username = args.username or prompt_value("SSH username", "debug")
    password = args.password or getpass.getpass("SSH password: ")

    plink_path = os.path.expandvars(args.plink_path)
    if not Path(plink_path).exists():
        print(f"[error] plink.exe not found: {plink_path}", file=sys.stderr)
        return 1

    script_dir = Path(__file__).resolve().parent
    output_dir = build_output_dir(script_dir, host)

    collector = PlinkHelpCollector(
        plink_path=plink_path,
        host=host,
        username=username,
        password=password,
        port=args.port,
        max_depth=args.max_depth,
        idle_timeout=args.idle_timeout,
    )

    try:
        print(f"[connect] plink ssh://{host}:{args.port}")
        results = collector.collect()
    except Exception as exc:
        print(f"[debug] exception_type={type(exc).__name__}", file=sys.stderr)
        if hasattr(exc, "args"):
            print(f"[debug] exception_args={exc.args}", file=sys.stderr)
        print(f"[error] plink collection failed: {exc}", file=sys.stderr)
        return 1

    meta = {
        "host": host,
        "port": args.port,
        "username": username,
        "max_depth": args.max_depth,
        "idle_timeout": args.idle_timeout,
        "plink_path": plink_path,
        "collected_at": datetime.now().isoformat(timespec="seconds"),
    }
    write_outputs(output_dir, results, meta)

    print(f"[done] Saved help dump to {output_dir}")
    print(f"[done] Text report: {output_dir / 'session.txt'}")
    print(f"[done] JSON report: {output_dir / 'session.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
