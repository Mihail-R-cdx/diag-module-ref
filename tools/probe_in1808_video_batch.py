"""Read-only hardware probe for exact IN1808 mixed Video-status batching.

This helper is intentionally not a production polling path.  It captures the
wire evidence required by the active OpenSpec change:

    1I                         -- standalone exact-identity gate
    1I + <30 Video status reads> -- one CR-separated read-only write
    1I                         -- post-batch session-usability check

The leading in-batch 1I is a read-only framing guard.  Two real hardware probes
showed that the first query in a CR-separated multi-query write is echoed but
its payload is omitted, while every later payload remains ordered.  The guard is
therefore intentionally expendable; the following 30 payloads are the evidence
under test.

No route mutation, Audio meter activation, or other state-changing command is
sent.
"""

from __future__ import annotations

import argparse
from getpass import getpass
from pathlib import Path
import sys
import time


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from handlers.extron.in1804 import ExtronIN1804Handler  # noqa: E402
from handlers.extron.matrix import (  # noqa: E402
    normalize_identity_response,
    resolve_matrix_capabilities,
)


BATCH_GUARD_COMMAND = "1I"

VIDEO_STATUS_COMMANDS = (
    "Q",
    "w20STAT",
    "wE1HDCP",
    "wI1HDCP",
    "wE2HDCP",
    "wI2HDCP",
    "wE3HDCP",
    "wI3HDCP",
    "wE4HDCP",
    "wI4HDCP",
    "wE5HDCP",
    "wI5HDCP",
    "wE6HDCP",
    "wI6HDCP",
    "wE7HDCP",
    "wI7HDCP",
    "wE8HDCP",
    "wI8HDCP",
    "wO1HDCP",
    "wI1VNAM",
    "wI2VNAM",
    "wI3VNAM",
    "wI4VNAM",
    "wI5VNAM",
    "wI6VNAM",
    "wI7VNAM",
    "wI8VNAM",
    "wO1VNAM",
    "w0LS",
    "1%",
)


def _raw_bytes(result: dict) -> bytes:
    raw = result.get("raw_response", b"") if isinstance(result, dict) else b""
    if isinstance(raw, bytes):
        return raw
    return str(raw).encode("utf-8", errors="replace")


def _print_result(label: str, result: dict, elapsed: float | None = None) -> bytes:
    raw = _raw_bytes(result)
    print(f"\n=== {label} ===")
    if elapsed is not None:
        print(f"elapsed_seconds={elapsed:.3f}")
    print(f"success={bool(result.get('success')) if isinstance(result, dict) else False}")
    print(f"raw_length={len(raw)}")
    print(f"raw_repr={raw!r}")
    decoded = raw.decode("utf-8", errors="replace")
    print(f"decoded_repr={decoded!r}")

    # This split is evidence display only.  It deliberately does not claim the
    # framing contract that the hardware probe is intended to establish.
    chunks = [chunk for chunk in raw.split(b"\r\r\n") if chunk]
    print(f"observed_double_crlf_chunks={len(chunks)}")
    for index, chunk in enumerate(chunks, 1):
        print(f"chunk[{index:02d}]={chunk!r}")
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe exact IN1808 read-only Video batching and print raw responses."
    )
    parser.add_argument("ip", help="IN1808 IP address")
    parser.add_argument("--username", help="Matrix username; prompted when omitted")
    parser.add_argument("--port", type=int, default=22023, help="Matrix SIS port (default: 22023)")
    args = parser.parse_args()

    username = args.username
    if username is None:
        username = input("Username: ").strip()
    password = getpass("Password: ")

    handler = ExtronIN1804Handler(
        args.ip,
        port=args.port,
        username=username,
        password=password,
        expected_model="Extron IN1808",
    )

    try:
        print("Connecting to exact IN1808...")
        handler.connect()

        identity_result = handler.send_command("1I")
        _print_result("IDENTITY BEFORE BATCH", identity_result)

        identity = normalize_identity_response(
            "1I",
            identity_result.get("response", "") if identity_result else "",
        )
        profile = resolve_matrix_capabilities(identity)
        print(f"normalized_identity={identity!r}")
        print(f"resolved_model={getattr(profile, 'exact_model', None)!r}")
        if profile is None or profile.exact_model != "IN1808":
            raise RuntimeError(
                "Exact IN1808 identity gate failed; batch was NOT sent."
            )

        probe_commands = (BATCH_GUARD_COMMAND,) + VIDEO_STATUS_COMMANDS
        batch = "\r".join(probe_commands)
        print("\n=== BATCH COMMAND LIST ===")
        for index, command in enumerate(probe_commands, 1):
            suffix = "  [framing guard]" if index == 1 else ""
            print(f"{index:02d}: {command}{suffix}")
        print(f"batch_command_count={len(probe_commands)}")
        print(f"expected_status_payload_count={len(VIDEO_STATUS_COMMANDS)}")
        print(f"batch_wire_repr={(batch + chr(13))!r}")

        started = time.monotonic()
        batch_result = handler.send_command(batch)
        elapsed = time.monotonic() - started
        _print_result("VIDEO BATCH RAW RESPONSE", batch_result, elapsed)

        followup = handler.send_command("1I")
        _print_result("IDENTITY AFTER BATCH", followup)

        followup_identity = normalize_identity_response(
            "1I",
            followup.get("response", "") if followup else "",
        )
        print(f"post_batch_normalized_identity={followup_identity!r}")
        print("\nProbe complete. Copy the full console output back into the review chat.")
        return 0
    finally:
        try:
            handler.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
