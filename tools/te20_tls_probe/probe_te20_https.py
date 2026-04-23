import argparse
import ssl
import sys
from pathlib import Path

import urllib3


def build_legacy_context() -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    if hasattr(ssl, "TLSVersion"):
        try:
            ctx.minimum_version = ssl.TLSVersion.TLSv1
        except ValueError:
            pass
        try:
            ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        except ValueError:
            pass

    for option_name in (
        "OP_LEGACY_SERVER_CONNECT",
        "OP_ALLOW_UNSAFE_LEGACY_RENEGOTIATION",
    ):
        option_value = getattr(ssl, option_name, None)
        if option_value:
            ctx.options |= option_value

    try:
        ctx.set_ciphers("DEFAULT@SECLEVEL=0")
    except ssl.SSLError:
        ctx.set_ciphers("DEFAULT")

    return ctx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe Huawei TE20 HTTPS using urllib3 and a legacy SSL context.")
    parser.add_argument("--host", required=True, help="TE20 IP address or hostname.")
    parser.add_argument("--port", type=int, default=443, help="HTTPS port. Default: 443")
    parser.add_argument("--path", default="/", help="Path to request. Default: /")
    parser.add_argument("--timeout", type=float, default=5.0, help="Request timeout in seconds.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    url = f"https://{args.host}:{args.port}{args.path}"
    print(f"[probe] GET {url}")

    try:
        http = urllib3.PoolManager(ssl_context=build_legacy_context())
        response = http.request("GET", url, timeout=args.timeout)
        body_preview = response.data[:500]
        print(f"[result] status={response.status}")
        print(f"[result] headers={dict(response.headers)}")
        print(f"[result] body_preview={body_preview!r}")
        return 0
    except Exception as exc:
        print(f"[error] {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
