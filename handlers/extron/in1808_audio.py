"""Read-only Extron IN1808 Audio DSP protocol and normalized domain profile.

This module is deliberately separate from both the generic Matrix video
profile and the DMP 64 Plus meter profile.  In particular, IN1808 meter
instrumentation uses ``*1`` only, never DMP's ``*2``, and cleanup performs no
device command while update-state ownership remains unknown.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable, Mapping

from core.exceptions import CommandOutcomeUnknownError, ProtocolError


IN1808_PRODSP_PROFILE_MAPPING = "IN1808_PRODSP_PROFILE_MAPPING"
IN1808_AUDIO_CAPABILITY = "in1808_audio_routing_meters"

IN1808_WIRE_VARIANTS = {
    "IN1808": "base",
    "IN1808 IPCP SA": "stereo_amplifier",
    "IN1808 IPCP MA 70": "mono_amplifier",
    "IN1808 IPCP Q SA": "stereo_amplifier",
    "IN1808 IPCP Q MA 70": "mono_amplifier",
}

PROGRAM_SOURCES = {
    1: "DP 1",
    2: "HDMI 2",
    3: "HDMI 3",
    4: "HDMI 4",
    5: "HDMI 5",
    6: "HDMI 6",
    7: "TP 7",
    8: "TP 8",
    9: "Aux In",
}

ROUTING_ROWS = (
    "Program L",
    "Program R",
    "Mic/Line 1",
    "Mic/Line 2",
    "Line In 3",
    "Line In 4",
    "File Player L",
    "File Player R",
)

_BASE_ROUTING_COLUMNS = (
    "HDMI L",
    "HDMI R",
    "TP/DTP L",
    "TP/DTP R",
    "DTP Analog L",
    "DTP Analog R",
    "Line Out 1",
    "Line Out 2",
    "Line Out 3",
    "Line Out 4",
)


@dataclass(frozen=True)
class MeterGroup:
    key: str
    fallback_label: str
    name_ids: tuple[int, ...]
    components: tuple[tuple[str, int], ...]


INPUT_METER_GROUPS = (
    MeterGroup("dp_1", "DP 1", (1,), (("L", 30000), ("R", 30001))),
    MeterGroup("hdmi_2", "HDMI 2", (2,), (("L", 30002), ("R", 30003))),
    MeterGroup("hdmi_3", "HDMI 3", (3,), (("L", 30004), ("R", 30005))),
    MeterGroup("hdmi_4", "HDMI 4", (4,), (("L", 30006), ("R", 30007))),
    MeterGroup("hdmi_5", "HDMI 5", (5,), (("L", 30008), ("R", 30009))),
    MeterGroup("hdmi_6", "HDMI 6", (6,), (("L", 30010), ("R", 30011))),
    MeterGroup("tp_7", "TP 7", (7,), (("L", 30012), ("R", 30013))),
    MeterGroup("tp_8", "TP 8", (8,), (("L", 30014), ("R", 30015))),
    MeterGroup("aux_in", "Aux In", (9,), (("L", 30016), ("R", 30017))),
    MeterGroup("mic_line_1", "Mic/Line 1", (10,), (("MONO", 40000),)),
    MeterGroup("mic_line_2", "Mic/Line 2", (11,), (("MONO", 40001),)),
    MeterGroup("line_in_3", "Line In 3", (12,), (("MONO", 40002),)),
    MeterGroup("line_in_4", "Line In 4", (13,), (("MONO", 40003),)),
    MeterGroup("file_player", "File Player", (14, 15), (("L", 40004), ("R", 40005))),
)

_BASE_OUTPUT_METER_GROUPS = (
    MeterGroup("hdmi_1a", "HDMI 1A", (1,), (("L", 60000), ("R", 60001))),
    MeterGroup("tp_dtp_1b", "TP/DTP 1B", (2,), (("L", 60002), ("R", 60003))),
    MeterGroup("dtp_analog", "DTP Analog", (3,), (("L", 60004), ("R", 60005))),
    MeterGroup("line_out_1", "Line Out 1", (4,), (("MONO", 60006),)),
    MeterGroup("line_out_2", "Line Out 2", (5,), (("MONO", 60007),)),
    MeterGroup("line_out_3", "Line Out 3", (6,), (("MONO", 60008),)),
    MeterGroup("line_out_4", "Line Out 4", (7,), (("MONO", 60009),)),
)


def _identity_key(identity: Any) -> str:
    text = " ".join(str(identity or "").strip().split()).upper()
    return text[7:] if text.startswith("EXTRON ") else text


def variant_for_identity(identity: Any) -> str | None:
    """Return only an exact closed IN1808 variant capability."""
    return IN1808_WIRE_VARIANTS.get(_identity_key(identity))


def output_meter_groups(identity: Any) -> tuple[MeterGroup, ...]:
    variant = variant_for_identity(identity)
    if variant == "stereo_amplifier":
        return _BASE_OUTPUT_METER_GROUPS + (
            MeterGroup("amplifier", "Amplifier", (), (("L", 60010), ("R", 60011))),
        )
    if variant == "mono_amplifier":
        return _BASE_OUTPUT_METER_GROUPS + (
            MeterGroup("amplifier", "Amplifier", (), (("MONO", 60010),)),
        )
    return _BASE_OUTPUT_METER_GROUPS


def routing_columns(identity: Any) -> tuple[str, ...]:
    variant = variant_for_identity(identity)
    if variant == "stereo_amplifier":
        return _BASE_ROUTING_COLUMNS + ("Amplifier L", "Amplifier R")
    if variant == "mono_amplifier":
        return _BASE_ROUTING_COLUMNS + ("Amplifier Mono",)
    return _BASE_ROUTING_COLUMNS


def meter_read_command(oid: int) -> str:
    return f"V{_approved_meter_oid(oid)}AU"


def meter_enable_command(oid: int) -> str:
    return f"V{_approved_meter_oid(oid)}*1AU"


def audio_name_command(kind: str, name_id: int) -> str:
    if kind not in {"input", "output"}:
        raise ValueError("Audio name kind must be input or output")
    maximum = 15 if kind == "input" else 7
    if isinstance(name_id, bool) or not isinstance(name_id, int) or not 1 <= name_id <= maximum:
        raise ValueError("Audio name ID is outside the IN1808 profile")
    return f"W{'I' if kind == 'input' else 'O'}{name_id}ANAM"


def mixpoint_oid(row: int, column: int) -> int:
    if any(isinstance(value, bool) or not isinstance(value, int) for value in (row, column)):
        raise ValueError("IN1808 mix-point coordinates must be integers")
    if not 0 <= row <= 7 or not 0 <= column <= 11:
        raise ValueError("IN1808 mix-point coordinates are outside the adopted profile")
    return 20000 + row * 100 + column


def mixpoint_read_command(row: int, column: int) -> str:
    return f"M{mixpoint_oid(row, column)}AU"


def dbfs_from_raw_meter(raw_meter: int) -> float:
    if isinstance(raw_meter, bool) or not isinstance(raw_meter, int) or raw_meter < 0:
        raise ValueError("IN1808 raw meter evidence must be a non-negative integer")
    return -(raw_meter / 10.0)


def normalize_dbfs(dbfs: float) -> float:
    return max(0.0, min(1.0, (float(dbfs) + 60.0) / 72.0))


def parse_meter_response(response: Any, command: str | None = None) -> dict[str, Any]:
    line = _single_response_line(response, command)
    match = re.fullmatch(r"([01])\*(\d+)", line or "")
    if match is None:
        return {"available": False, "outcome": "UNKNOWN", "state": None, "raw_meter": None}
    state, raw_meter = int(match.group(1)), int(match.group(2))
    result = {
        "available": state == 1,
        "outcome": "VALID" if state == 1 else "INACTIVE",
        "state": state,
        "raw_meter": raw_meter,
    }
    if state == 1:
        dbfs = dbfs_from_raw_meter(raw_meter)
        result.update(dbfs=dbfs, normalized=normalize_dbfs(dbfs))
    return result


def parse_meter_enable_response(response: Any, oid: int, command: str | None = None) -> bool:
    return _single_response_line(response, command) == f"DsV{_approved_meter_oid(oid)}*1"


def parse_audio_name(response: Any, *, command: str, fallback: str) -> dict[str, Any]:
    line = _single_response_line(response, command)
    verbose = re.fullmatch(r"(?:Anam[io]\d+\*)?([^\x00-\x1f\x7f]+)", line or "", re.IGNORECASE)
    value = verbose.group(1).strip() if verbose else ""
    if not value or re.fullmatch(r"E\d+", value):
        return {"value": fallback, "outcome": "FALLBACK", "raw": line}
    return {"value": value, "outcome": "VALID", "raw": line}


def parse_program_source(response: Any, command: str = "1$") -> dict[str, Any]:
    line = _single_response_line(response, command)
    match = re.fullmatch(r"(?:Aud1\*)?([1-9])", line or "", re.IGNORECASE)
    input_id = int(match.group(1)) if match else None
    label = PROGRAM_SOURCES.get(input_id)
    return {
        "input_id": input_id if label is not None else None,
        "label": label or "UNKNOWN",
        "outcome": "VALID" if label is not None else "UNKNOWN",
    }


def parse_mixpoint_response(response: Any, command: str | None = None) -> str:
    line = _single_response_line(response, command)
    if line == "0":
        return "ACTIVE"
    if line == "1":
        return "INACTIVE"
    return "UNKNOWN"


class IN1808AudioProfile:
    """One exact Audio subcontext over an already-owned Matrix session."""

    def __init__(self, wire_identity: str):
        normalized = _identity_key(wire_identity)
        if variant_for_identity(normalized) is None:
            raise ProtocolError("Unsupported IN1808 audio wire identity")
        self.wire_identity = normalized
        self.variant = variant_for_identity(normalized)
        self._activation_attempted: set[int] = set()

    def begin_subcontext(self) -> None:
        self._activation_attempted.clear()

    def cleanup_subcontext(self) -> None:
        """Forget local instrumentation authority; deliberately send nothing."""
        self._activation_attempted.clear()

    def acquire_entry_snapshot(
        self,
        read: Callable[..., Mapping[str, Any]],
        *,
        is_current: Callable[[], bool],
    ) -> dict[str, Any]:
        self.begin_subcontext()
        input_names = self._read_names(read, "input", range(1, 16), INPUT_METER_GROUPS, is_current)
        output_names = self._read_names(read, "output", range(1, 8), _BASE_OUTPUT_METER_GROUPS, is_current)
        if not is_current():
            raise ProtocolError("IN1808 Audio subcontext was superseded")
        source_response = read("1$")
        program_source = parse_program_source(_response(source_response))
        routing = self._read_routing(read, is_current)
        meters = self.poll_meters(read, is_current=is_current, input_names=input_names, output_names=output_names)
        return {
            "wire_identity": self.wire_identity,
            "variant": self.variant,
            "mapping_basis": IN1808_PRODSP_PROFILE_MAPPING,
            "input_names": input_names,
            "output_names": output_names,
            "program_source": program_source,
            "routing": routing,
            **meters,
        }

    def poll_meters(
        self,
        read: Callable[..., Mapping[str, Any]],
        *,
        is_current: Callable[[], bool],
        input_names: Mapping[int, Mapping[str, Any]] | None = None,
        output_names: Mapping[int, Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        input_names = input_names or {}
        output_names = output_names or {}
        component_results: dict[int, dict[str, Any]] = {}
        groups = INPUT_METER_GROUPS + output_meter_groups(self.wire_identity)
        for group in groups:
            for _channel, oid in group.components:
                if oid in component_results:
                    continue
                if not is_current():
                    component_results[oid] = _unavailable_meter(oid, "SUPERSEDED")
                    continue
                command = meter_read_command(oid)
                parsed = parse_meter_response(_response(read(command)), command)
                parsed["oid"] = oid
                if parsed.get("state") == 0 and oid not in self._activation_attempted:
                    self._activation_attempted.add(oid)
                    parsed = self._activate_meter(read, oid, parsed, is_current)
                component_results[oid] = parsed
        return {
            "input_meters": [
                _combine_group(group, component_results, input_names) for group in INPUT_METER_GROUPS
            ],
            "output_meters": [
                _combine_group(group, component_results, output_names)
                for group in output_meter_groups(self.wire_identity)
            ],
        }

    def _activate_meter(self, read, oid, inactive, is_current):
        command = meter_enable_command(oid)
        try:
            enabled = parse_meter_enable_response(
                _response(read(command, replay_safe=False)), oid, command
            )
        except CommandOutcomeUnknownError:
            if not is_current():
                return _unavailable_meter(oid, "AMBIGUOUS_ENABLE")
            # Reconcile once on the exact same current session.  The mutating
            # command itself is never replayed.
            reconcile_command = meter_read_command(oid)
            reconciled = parse_meter_response(
                _response(read(reconcile_command)), reconcile_command
            )
            reconciled["oid"] = oid
            if reconciled.get("state") == 1:
                return reconciled
            return _unavailable_meter(oid, "AMBIGUOUS_ENABLE", reconciled)
        if not enabled or not is_current():
            return _unavailable_meter(oid, "ENABLE_UNCONFIRMED", inactive)
        follow_up = meter_read_command(oid)
        parsed = parse_meter_response(_response(read(follow_up)), follow_up)
        parsed["oid"] = oid
        return parsed

    def _read_names(self, read, kind, ids, groups, is_current):
        fallbacks: dict[int, str] = {}
        for group in groups:
            for name_id in group.name_ids:
                fallbacks[name_id] = group.fallback_label
        names = {}
        for name_id in ids:
            if not is_current():
                break
            command = audio_name_command(kind, name_id)
            fallback = fallbacks.get(name_id, f"{'Input' if kind == 'input' else 'Output'} {name_id}")
            names[name_id] = {
                "id": name_id,
                **parse_audio_name(_response(read(command)), command=command, fallback=fallback),
            }
        for name_id in ids:
            names.setdefault(name_id, {
                "id": name_id,
                "value": fallbacks.get(name_id, f"{'Input' if kind == 'input' else 'Output'} {name_id}"),
                "outcome": "FALLBACK",
                "raw": None,
            })
        return names

    def _read_routing(self, read, is_current):
        columns = routing_columns(self.wire_identity)
        cells = []
        for row, row_label in enumerate(ROUTING_ROWS):
            for column, column_label in enumerate(columns):
                oid = mixpoint_oid(row, column)
                state = "UNKNOWN"
                if is_current():
                    command = mixpoint_read_command(row, column)
                    state = parse_mixpoint_response(_response(read(command)), command)
                cells.append({
                    "row": row,
                    "column": column,
                    "oid": oid,
                    "row_label": row_label,
                    "column_label": column_label,
                    "state": state,
                    "mapping_basis": IN1808_PRODSP_PROFILE_MAPPING,
                })
        return {
            "mapping_basis": IN1808_PRODSP_PROFILE_MAPPING,
            "rows": tuple(ROUTING_ROWS),
            "columns": columns,
            "cells": cells,
        }


def _approved_meter_oid(oid: Any) -> int:
    approved = {
        *(range(30000, 30018)),
        *(range(40000, 40006)),
        *(range(60000, 60012)),
    }
    if isinstance(oid, bool) or not isinstance(oid, int) or oid not in approved:
        raise ValueError("Meter OID is outside the approved IN1808 topology")
    return oid


def _response(result: Any) -> Any:
    if isinstance(result, Mapping):
        return result.get("response", "") if result.get("success", True) else ""
    return result


def _single_response_line(response: Any, command: str | None = None) -> str | None:
    if not isinstance(response, str):
        return None
    lines = [line.strip() for line in response.replace("\r", "\n").split("\n") if line.strip()]
    if lines and command and lines[0] in {command, f"W{command}"}:
        lines.pop(0)
    return lines[0] if len(lines) == 1 else None


def _unavailable_meter(oid: int, outcome: str, evidence: Mapping[str, Any] | None = None):
    return {
        "oid": oid,
        "available": False,
        "outcome": outcome,
        "state": None if evidence is None else evidence.get("state"),
        "raw_meter": None if evidence is None else evidence.get("raw_meter"),
    }


def _combine_group(group, components, names):
    evidence = []
    available_dbfs = []
    for channel, oid in group.components:
        component = dict(components.get(oid) or _unavailable_meter(oid, "UNKNOWN"))
        component["channel"] = channel
        evidence.append(component)
        if component.get("available") and isinstance(component.get("dbfs"), (int, float)):
            available_dbfs.append(component["dbfs"])
    name_components = [dict(names[name_id]) for name_id in group.name_ids if name_id in names]
    configured = [item.get("value") for item in name_components if item.get("outcome") == "VALID"]
    label = configured[0] if len(set(configured)) == 1 else group.fallback_label
    valid_count = len(available_dbfs)
    outcome = "VALID" if valid_count == len(evidence) else "PARTIAL" if valid_count else "UNAVAILABLE"
    result = {
        "key": group.key,
        "label": label,
        "fallback_label": group.fallback_label,
        "name_ids": group.name_ids,
        "name_components": name_components,
        "components": evidence,
        "available": bool(available_dbfs),
        "outcome": outcome,
        "display_dbfs": max(available_dbfs) if available_dbfs else None,
    }
    result["normalized"] = normalize_dbfs(result["display_dbfs"]) if available_dbfs else None
    return result


__all__ = [
    "IN1808_AUDIO_CAPABILITY",
    "IN1808_PRODSP_PROFILE_MAPPING",
    "IN1808_WIRE_VARIANTS",
    "INPUT_METER_GROUPS",
    "IN1808AudioProfile",
    "PROGRAM_SOURCES",
    "ROUTING_ROWS",
    "audio_name_command",
    "dbfs_from_raw_meter",
    "meter_enable_command",
    "meter_read_command",
    "mixpoint_oid",
    "mixpoint_read_command",
    "output_meter_groups",
    "parse_audio_name",
    "parse_meter_response",
    "parse_mixpoint_response",
    "parse_program_source",
    "routing_columns",
    "variant_for_identity",
]
