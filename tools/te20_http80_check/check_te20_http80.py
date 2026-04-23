import argparse
import csv
import http.client
import json
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


SESSION_ACTION = "WEB_RequestSessionIDAPI"
TOKEN_ACTION = "WEB_RequestCertificateAPI"


def load_ip_list(path: Path) -> list[str]:
    ips: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        value = line.strip()
        if value:
            ips.append(value)
    return ips


def load_credentials(path: Path) -> tuple[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if isinstance(payload, dict):
        username = payload.get("username")
        password = payload.get("password")
        if isinstance(username, str) and isinstance(password, str):
            return username, password
    raise ValueError("Credentials JSON must be an object with 'username' and 'password' string fields")


def tcp_probe(host: str, port: int, timeout: float) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def ping_probe(host: str, timeout: float) -> tuple[bool, str]:
    timeout_ms = max(1000, int(timeout * 1000))
    command = ["ping", "-n", "1", "-w", str(timeout_ms), host]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(2.0, timeout + 1.0),
        )
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"

    if completed.returncode == 0:
        return True, ""
    stderr = completed.stderr.strip()
    stdout = completed.stdout.strip()
    return False, stderr or stdout or f"ping exited with code {completed.returncode}"


def http_post(host: str, port: int, path: str, body: str, headers: dict[str, str], timeout: float) -> tuple[int, str]:
    connection = http.client.HTTPConnection(host, port=port, timeout=timeout)
    try:
        connection.request("POST", path, body=body.encode("utf-8"), headers=headers)
        response = connection.getresponse()
        data = response.read().decode("utf-8", errors="replace")
        return response.status, data
    finally:
        connection.close()


def parse_json(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def build_action_path(action_id: str) -> str:
    return "/action.cgi?" + urlencode({"ActionID": action_id})


def probe_te20_http(host: str, username: str, password: str, timeout: float) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ip": host,
        "ping_ok": False,
        "tcp_open": False,
        "session_status": "",
        "session_http_status": "",
        "session_body": "",
        "token_status": "",
        "token_http_status": "",
        "token_body": "",
        "overall": "unknown",
        "final_status": "",
        "error": "",
    }

    ping_ok, ping_error = ping_probe(host, timeout)
    result["ping_ok"] = ping_ok
    if not ping_ok:
        result["overall"] = "no_ping"
        result["final_status"] = f"{host} - err (no ping)"
        result["error"] = ping_error
        return result

    tcp_ok, tcp_error = tcp_probe(host, 80, timeout)
    result["tcp_open"] = tcp_ok
    if not tcp_ok:
        result["overall"] = "port_closed"
        result["final_status"] = f"{host} - err (no 80)"
        result["error"] = tcp_error
        return result

    common_headers = {
        "Content-Type": "application/json",
        "Accept": "*/*",
    }

    try:
        session_status, session_body = http_post(
            host,
            80,
            build_action_path(SESSION_ACTION),
            "",
            common_headers,
            timeout,
        )
        result["session_http_status"] = session_status
        result["session_body"] = session_body

        session_json = parse_json(session_body)
        if session_json is None:
            result["session_status"] = "non_json"
        elif session_json.get("success") == 1:
            result["session_status"] = "ok"
        else:
            result["session_status"] = "rejected"

        token_payload = json.dumps({"user": username, "password": password}, ensure_ascii=False)
        token_status, token_body = http_post(
            host,
            80,
            build_action_path(TOKEN_ACTION),
            token_payload,
            common_headers,
            timeout,
        )
        result["token_http_status"] = token_status
        result["token_body"] = token_body

        token_json = parse_json(token_body)
        if token_json is None:
            result["token_status"] = "non_json"
        elif token_json.get("success") == 1:
            result["token_status"] = "ok"
        else:
            result["token_status"] = "rejected"

        if result["session_status"] == "ok" or result["token_status"] == "ok":
            result["overall"] = "api_available"
            result["final_status"] = f"{host} - ok"
        elif session_json and session_json.get("exception", {}).get("id") == 4 and token_json and token_json.get("exception", {}).get("id") == 4:
            result["overall"] = "http_disabled"
            result["final_status"] = f"{host} - err (http off)"
        elif token_json and token_json.get("success") == 0:
            result["overall"] = "bad_password"
            result["final_status"] = f"{host} - err (password)"
        elif result["session_http_status"] or result["token_http_status"]:
            result["overall"] = "http_open_but_api_rejected"
            result["final_status"] = f"{host} - err (http off)"
        else:
            result["overall"] = "http_failed"
            result["final_status"] = f"{host} - err (no 80)"
        return result
    except Exception as exc:
        result["overall"] = "http_failed"
        result["final_status"] = f"{host} - err (no 80)"
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


def write_reports(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "results.json"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_path = output_dir / "results.csv"
    fieldnames = [
        "ip",
        "ping_ok",
        "tcp_open",
        "overall",
        "final_status",
        "session_status",
        "session_http_status",
        "token_status",
        "token_http_status",
        "error",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})

    txt_path = output_dir / "summary.txt"
    lines = []
    for row in rows:
        lines.append(row["final_status"])
    txt_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check TE20 HTTP:80 availability for a list of IPs.")
    parser.add_argument("--ips", required=True, help="Path to txt file with IP addresses, one per line.")
    parser.add_argument("--creds", required=True, help="Path to JSON file with username/password.")
    parser.add_argument("--timeout", type=float, default=5.0, help="TCP/HTTP timeout in seconds.")
    parser.add_argument("--output-dir", help="Optional directory for reports.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ips_path = Path(args.ips)
    creds_path = Path(args.creds)

    if not ips_path.exists():
        print(f"[error] IP list file not found: {ips_path}", file=sys.stderr)
        return 1
    if not creds_path.exists():
        print(f"[error] Credentials file not found: {creds_path}", file=sys.stderr)
        return 1

    try:
        ips = load_ip_list(ips_path)
        username, password = load_credentials(creds_path)
    except Exception as exc:
        print(f"[error] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if not ips:
        print("[error] IP list is empty", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else Path(__file__).resolve().parent / "output" / datetime.now().strftime("%Y%m%d_%H%M%S")

    rows: list[dict[str, Any]] = []
    total = len(ips)
    for index, ip in enumerate(ips, start=1):
        print(f"[{index}/{total}] probing {ip}:80")
        row = probe_te20_http(ip, username, password, args.timeout)
        rows.append(row)
        print(f"  {row['final_status']}")
        if row.get("error"):
            print(f"  error={row['error']}")

    write_reports(output_dir, rows)
    print(f"[done] Reports saved to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
