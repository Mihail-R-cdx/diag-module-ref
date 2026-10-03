"""Read-only exact-IN1808 probe for homogeneous Video command-family batches.

Production authority remains sequential.  This evidence helper tests only three
same-family candidates:

* input names:             wI#VNAM
* input HDCP authorization: wE#HDCP
* input HDCP status:        wI#HDCP

For each family the helper first captures standalone input-1..8 baseline
responses.  It then sends one 9-command CR-separated batch whose first command
duplicates input 1 as a sacrificial first position, followed by useful
input-1..8 queries.  Raw framing and an exact baseline comparison are printed.

No route mutation, Audio meter activation, or other state-changing command is
sent.
"""

from __future__ import annotations

import argparse
from getpass import getpass
from pathlib import Path
import sys
import time
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from handlers.extron.in1804 import ExtronIN1804Handler  # noqa: E402
from handlers.extron.matrix import (  # noqa: E402
    normalize_identity_response,
    resolve_matrix_capabilities,
)


RECORD_SEPARATOR = b"\r\r\n"

FAMILY_PROBES = (
    ("input_names", tuple(f"wI{index}VNAM" for index in range(1, 9))),
    (
        "input_hdcp_authorization",
        tuple(f"wE{index}HDCP" for index in range(1, 9)),
    ),
    (
        "input_hdcp_status",
        tuple(f"wI{index}HDCP" for index in range(1, 9)),
    ),
)


def _raw_bytes(result: dict) -> bytes:
    raw = result.get("raw_response", b"") if isinstance(result, dict) else b""
    if isinstance(raw, bytes):
        return raw
    return str(raw).encode("utf-8", errors="replace")


def _response_text(result: dict) -> str:
    if not isinstance(result, dict) or not result.get("success"):
        return ""
    return str(result.get("response", "")).strip()


def _chunks(raw: bytes) -> list[bytes]:
    return [chunk for chunk in raw.split(RECORD_SEPARATOR) if chunk]


def _emit_raw(
    emit: Callable[[str], None],
    label: str,
    result: dict,
    *,
    elapsed: float | None = None,
) -> tuple[bytes, list[bytes]]:
    raw = _raw_bytes(result)
    chunks = _chunks(raw)
    lines = [f"=== {label} ==="]
    if elapsed is not None:
        lines.append(f"elapsed_seconds={elapsed:.3f}")
    lines.extend(
        (
            f"success={bool(result.get('success')) if isinstance(result, dict) else False}",
            f"raw_length={len(raw)}",
            f"raw_repr={raw!r}",
            f"observed_double_crlf_chunks={len(chunks)}",
        )
    )
    for index, chunk in enumerate(chunks, 1):
        lines.append(f"chunk[{index:02d}]={chunk!r}")
    emit("\n".join(lines))
    return raw, chunks


def _decode_payload_chunks(chunks: list[bytes]) -> list[str]:
    if len(chunks) < 2:
        return []
    values = []
    for chunk in chunks[1:]:
        values.append(chunk.decode("utf-8", errors="replace").strip())
    return values


def run_probe(handler: ExtronIN1804Handler, emit: Callable[[str], None] = print) -> bool:
    identity_result = handler.send_command("1I")
    _emit_raw(emit, "IDENTITY BEFORE FAMILY PROBES", identity_result)
    identity = normalize_identity_response(
        "1I",
        identity_result.get("response", "") if identity_result else "",
    )
    profile = resolve_matrix_capabilities(identity)
    emit(
        f"normalized_identity={identity!r}\n"
        f"resolved_model={getattr(profile, 'exact_model', None)!r}"
    )
    if profile is None or profile.exact_model != "IN1808":
        raise RuntimeError("Exact IN1808 identity gate failed; family probes were NOT sent.")

    all_passed = True
    for family_name, commands in FAMILY_PROBES:
        emit(f"\n######## FAMILY {family_name} ########")
        baseline = []
        baseline_started = time.monotonic()
        for index, command in enumerate(commands, 1):
            result = handler.send_command(command)
            value = _response_text(result)
            baseline.append(value)
            emit(
                f"standalone[{index}] command={command!r} "
                f"success={bool(result.get('success')) if isinstance(result, dict) else False} "
                f"value={value!r}"
            )
        baseline_elapsed = time.monotonic() - baseline_started
        emit(f"standalone_elapsed_seconds={baseline_elapsed:.3f}")

        batch_commands = (commands[0],) + commands
        batch = "\r".join(batch_commands)
        emit("=== FAMILY BATCH COMMAND LIST ===")
        for index, command in enumerate(batch_commands, 1):
            suffix = "  [sacrificial duplicate]" if index == 1 else ""
            emit(f"{index:02d}: {command}{suffix}")
        emit(
            f"family={family_name}\n"
            f"batch_command_count={len(batch_commands)}\n"
            f"expected_useful_payload_count={len(commands)}\n"
            f"batch_wire_repr={(batch + chr(13))!r}"
        )

        started = time.monotonic()
        batch_result = handler.send_command(batch)
        elapsed = time.monotonic() - started
        _raw, chunks = _emit_raw(
            emit,
            f"{family_name} BATCH RAW RESPONSE",
            batch_result,
            elapsed=elapsed,
        )
        observed = _decode_payload_chunks(chunks)
        exact_match = observed == baseline
        emit(
            f"family={family_name}\n"
            f"observed_useful_payload_count={len(observed)}\n"
            f"payloads_match_standalone_exactly={exact_match}"
        )
        for index in range(max(len(baseline), len(observed))):
            expected = baseline[index] if index < len(baseline) else "<missing>"
            actual = observed[index] if index < len(observed) else "<missing>"
            emit(
                f"compare[{index + 1}] expected={expected!r} "
                f"observed={actual!r} match={expected == actual}"
            )

        followup = handler.send_command("1I")
        _emit_raw(emit, f"IDENTITY AFTER {family_name}", followup)
        followup_identity = normalize_identity_response(
            "1I",
            followup.get("response", "") if followup else "",
        )
        identity_match = bool(
            followup_identity
            and identity
            and followup_identity.upper() == identity.upper()
        )
        emit(
            f"post_family_normalized_identity={followup_identity!r}\n"
            f"post_family_identity_matches={identity_match}"
        )

        family_passed = (
            bool(batch_result.get("success"))
            and len(observed) == len(commands)
            and exact_match
            and identity_match
        )
        emit(f"family_result={'PASS' if family_passed else 'FAIL'}")
        all_passed = all_passed and family_passed

    emit(f"\nOVERALL_RESULT={'PASS' if all_passed else 'FAIL'}")
    return all_passed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe exact IN1808 homogeneous read-only Video family batches."
    )
    parser.add_argument("ip", help="IN1808 IP address")
    parser.add_argument("--username", help="Matrix username; prompted when omitted")
    parser.add_argument("--port", type=int, default=22023, help="Matrix SIS port")
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
        passed = run_probe(handler)
        print("\nProbe complete. Copy the full console output back into the review chat.")
        return 0 if passed else 2
    finally:
        try:
            handler.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
