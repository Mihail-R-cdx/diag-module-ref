"""Capability-driven Extron Matrix SIS profiles.

Transport, authentication and framing remain in :mod:`core.base_handler`.
This module deliberately contains only exact model selection, SIS syntax and
normalisation rules; a model never becomes supported by a family substring.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import re
from typing import Tuple

from core.base_handler import BaseExtronMatrixHandler
from core.exceptions import AuthenticationError, CommandOutcomeUnknownError, ConnectionError, ProtocolError

HDCP_ABSENT = "ABSENT"
HDCP_PRESENT_HDCP = "PRESENT_HDCP"
HDCP_PRESENT_NO_HDCP = "PRESENT_NO_HDCP"
HDCP_UNKNOWN = "UNKNOWN"

@dataclass(frozen=True)
class MatrixCapabilities:
    family: str; exact_model: str; logical_input_ids: Tuple[int, ...]; logical_output_ids: Tuple[int, ...]
    available_input_ids: Tuple[int, ...]; available_output_ids: Tuple[int, ...]; physical_outputs: Tuple[str, ...]
    supports_signal_presence: bool; supports_input_hdcp: bool; supports_output_hdcp: bool; supports_hdcp_authorization: bool
    supports_input_names: bool; supports_output_names: bool; supports_temperature: bool
    route_profile: str; input_hdcp_profile: str; output_hdcp_profile: str
    @property
    def single_output(self): return self.available_output_ids == (1,)

def _ids(count): return tuple(range(1, count + 1))
def _fixed(family, model, inputs, outputs, *, physical=(), signal=True, input_hdcp=True, output_hdcp=True, auth=False, input_names=False, output_names=False, temperature=False, route="crosspoint", input_profile="modern", output_profile="dtp"):
    return MatrixCapabilities(family, model, _ids(inputs), _ids(outputs), _ids(inputs), _ids(outputs), tuple(physical) or tuple("Output %s" % i for i in _ids(outputs)), signal, input_hdcp, output_hdcp, auth, input_names, output_names, temperature, route, input_profile, output_profile)

_PROFILES = {
    "IN1804": _fixed("IN", "IN1804", 4, 1, physical=("Main Output",), auth=True, input_names=True, output_names=True, temperature=True, route="in1804", input_profile="legacy", output_profile="in"),
    "IN1808": _fixed("IN", "IN1808", 8, 1, physical=("Main Output", "Loop Out"), auth=True, input_names=True, output_names=True, temperature=True, route="in1808", input_profile="legacy", output_profile="in"),
    "IN1608 XI": _fixed("IN", "IN1608 xi", 8, 1, physical=("Main Output",), auth=True, input_names=True, temperature=True, route="in1608", input_profile="modern", output_profile="in"),
    "DTP CROSSPOINT 84": _fixed("DTP", "DTP CrossPoint 84", 8, 4, input_names=True, output_names=True),
    "DTP CROSSPOINT 82 4K": _fixed("DTP", "DTP CrossPoint 82 4K", 8, 2, input_names=True, output_names=True),
    "DTP CROSSPOINT 84 4K": _fixed("DTP", "DTP CrossPoint 84 4K", 8, 4, input_names=True, output_names=True),
    "DTP CROSSPOINT 86 4K": _fixed("DTP", "DTP CrossPoint 86 4K", 8, 6, input_names=True, output_names=True),
    "DTP CROSSPOINT 108 4K": _fixed("DTP", "DTP CrossPoint 108 4K", 10, 8, input_names=True, output_names=True),
}
_XTP_FIRST_GEN = frozenset({"XTP CROSSPOINT 1600", "XTP CROSSPOINT 3200", "XTP CROSSPOINT 6400"})
_XTP_II = frozenset({"XTP II CROSSPOINT 1600", "XTP II CROSSPOINT 3200", "XTP II CROSSPOINT 6400"})

def _identity_key(identity):
    if not isinstance(identity, str): return None
    text = " ".join(identity.strip().split())
    return (text[7:] if text.upper().startswith("EXTRON ") else text).upper()

def resolve_matrix_capabilities(identity):
    key = _identity_key(identity)
    if key in _PROFILES: return _PROFILES[key]
    if key in _XTP_FIRST_GEN: return _fixed("XTP", " ".join(identity.strip().split()), 0, 0, auth=False, input_names=False, output_names=False, temperature=False, route="crosspoint", input_profile="modern", output_profile="xtp")
    if key in _XTP_II: return _fixed("XTP II", " ".join(identity.strip().split()), 0, 0, auth=True, input_names=False, output_names=False, output_hdcp=False, temperature=False, route="crosspoint", input_profile="modern", output_profile="unproven")
    return None

def decode_hdcp(raw, profile):
    try: value = int(str(raw).strip())
    except (TypeError, ValueError): return HDCP_UNKNOWN
    if value == 0: return HDCP_ABSENT
    return ({1: HDCP_PRESENT_NO_HDCP, 2: HDCP_PRESENT_HDCP} if profile == "legacy" else {1: HDCP_PRESENT_HDCP, 2: HDCP_PRESENT_NO_HDCP}).get(value, HDCP_UNKNOWN)

def _response_lines(response): return [line.strip() for line in response.replace("\r", "\n").split("\n") if line.strip()] if isinstance(response, str) else []
def parse_route_response(response, output_id, input_ids):
    lines = _response_lines(response)
    if lines and lines[0] == "%s!" % output_id: lines.pop(0)
    if len(lines) != 1: return None, False
    line = lines[0]
    if line in {"0", "In00 All", "In00 Out%s" % output_id}: return None, True
    bare = re.fullmatch(r"([1-9]\d*)", line); routed = re.fullmatch(r"In([1-9]\d*) (?:All|Out([1-9]\d*))", line)
    value = int(bare.group(1)) if bare else int(routed.group(1)) if routed and (routed.group(2) is None or int(routed.group(2)) == output_id) else None
    return (value, True) if value in input_ids else (None, False)

def available_ids_from_slots(maximum, slots, channels_per_slot=4):
    if not isinstance(maximum, int) or maximum < 0: return ()
    return tuple(channel for slot, installed in enumerate(tuple(slots or ()), 1) if installed for channel in range((slot - 1) * channels_per_slot + 1, min(slot * channels_per_slot, maximum) + 1))
def parse_xtp_topology(dimensions, board_evidence):
    if isinstance(dimensions, str):
        found = re.search(r"(\d+)\s*[xX*]\s*(\d+)", dimensions); dimensions = (int(found.group(1)), int(found.group(2))) if found else None
    if not (isinstance(dimensions, tuple) and len(dimensions) == 2 and all(isinstance(x, int) and x >= 0 for x in dimensions)): return (), ()
    evidence = board_evidence if isinstance(board_evidence, dict) else {}
    if isinstance(board_evidence, str):
        def slots(prefix):
            match = re.search(prefix + r"\s*:\s*([01](?:\s*,\s*[01])*)", board_evidence, re.I); return tuple(x == "1" for x in match.group(1).split(",")) if match else ()
        evidence = {"input_slots": slots("I"), "output_slots": slots("O")}
    return available_ids_from_slots(dimensions[0], evidence.get("input_slots")), available_ids_from_slots(dimensions[1], evidence.get("output_slots"))

class ExtronMatrixHandler(BaseExtronMatrixHandler):
    """Exact-profile Matrix handler. Topology probes are read-only."""
    def __init__(self, ip_address, port=22023, username=None, password=None):
        super().__init__(ip_address, port, username, password); self.model = None; self.capabilities = None; self.inputs_num = None; self.outputs_num = None; self.strict_session_failures = True
    def send_command(self, command, data=None, **kwargs): kwargs.setdefault("response_required", True); return super().send_command(command, data, **kwargs)
    def get_status(self): return self.get_full_status()
    def _read(self, command, *, replay_safe=True): return self.send_command(command, replay_safe=replay_safe)
    def get_device_info(self):
        result = self._read("1I"); identity = result.get("response", "").strip() if result and result.get("success") else ""; profile = resolve_matrix_capabilities(identity)
        if profile is None: raise ProtocolError("Unsupported Extron Matrix identity: %s" % (identity or "<empty>"))
        self.model, self.capabilities = identity, profile
        if profile.family in {"XTP", "XTP II"}:
            available_inputs, available_outputs = parse_xtp_topology(self._read("I").get("response", ""), self._read("*N").get("response", ""))
            if not available_inputs or not available_outputs: raise ProtocolError("XTP topology evidence was unavailable or malformed")
            self.capabilities = replace(profile, logical_input_ids=tuple(range(1, max(available_inputs) + 1)), logical_output_ids=tuple(range(1, max(available_outputs) + 1)), available_input_ids=available_inputs, available_output_ids=available_outputs)
        self.inputs_num, self.outputs_num = len(self.capabilities.available_input_ids), len(self.capabilities.available_output_ids)
        temp = None
        if self.capabilities.supports_temperature:
            response = self._read("w20STAT").get("response", "").strip(); temp = int(response) if response.isdigit() else None
        return {"model": self.model, "temperature": temp}
    def _profile(self):
        if self.capabilities is None and self.model:
            self.capabilities = resolve_matrix_capabilities(self.model)
            if self.capabilities is not None:
                self.inputs_num, self.outputs_num = len(self.capabilities.available_input_ids), len(self.capabilities.available_output_ids)
        if self.capabilities is None: self.get_device_info()
        return self.capabilities
    def get_input_names(self):
        profile = self._profile(); names = {}
        for item in profile.available_input_ids if profile.supports_input_names else ():
            command = "w%sNI" % item if profile.route_profile == "in1608" or profile.family == "DTP" else "wI%sVNAM" % item; names[item] = self._read(command).get("response", "").strip() or None
        return names
    def get_output_names(self):
        profile = self._profile(); names = {}
        for item in profile.available_output_ids if profile.supports_output_names else ():
            command = "w%sNO" % item if profile.family == "DTP" else "wO%sVNAM" % item; names[item] = self._read(command).get("response", "").strip() or None
        return names
    def get_signal_status(self):
        profile = self._profile()
        if not profile.supports_signal_presence: return {}
        response = self._read("w0LS" if profile.family == "IN" else "0LS").get("response", ""); match = re.search(r"(?:In00\s+)?([01](?:\*[01])*)", response); states = match.group(1).split("*") if match else ()
        return {item: (states[index] == "1" if index < len(states) else None) for index, item in enumerate(profile.available_input_ids)}
    def get_hdcp_info(self):
        profile = self._profile(); states = {}; auth = {}; outputs = {}
        for item in profile.available_input_ids:
            if profile.supports_hdcp_authorization:
                value = self._read("wE%sHDCP" % item).get("response", "").strip(); auth[item] = int(value) if value in {"0", "1"} else None
            if profile.supports_input_hdcp: states[item] = decode_hdcp(self._read("wI%sHDCP" % item).get("response", ""), profile.input_hdcp_profile)
        if profile.supports_output_hdcp:
            for item in profile.available_output_ids:
                command = "w0%sHDCP" % item if profile.output_hdcp_profile == "xtp" else "wO%sHDCP" % item; outputs[item] = self._read(command).get("response", "").strip() or None
        return {"input_auth": auth, "input_status": states, "output_status": outputs}
    def get_routes(self, output_ids=None):
        profile = self._profile(); result = {}
        for output in tuple(output_ids or profile.available_output_ids):
            if output not in profile.available_output_ids: raise ValueError("Output number is outside Matrix capability")
            command = "!" if profile.route_profile in {"in1804", "in1608"} else "1!" if profile.route_profile == "in1808" else "%s!" % output; value, valid = parse_route_response(self._read(command).get("response", ""), output, profile.available_input_ids)
            if not valid: raise ProtocolError("Malformed or unavailable route evidence for output %s" % output)
            result[output] = value
        return result
    def get_connections(self):
        routes = self.get_routes(); return [routes[1]] if self.capabilities.single_output and routes.get(1) is not None else []
    def get_full_status(self):
        info = self.get_device_info(); profile = self._profile(); hdcp = self.get_hdcp_info()
        return {"device_info": info, "capabilities": profile, "input_names": self.get_input_names(), "output_names": self.get_output_names(), "signal_status": self.get_signal_status(), "input_hdcp_auth": hdcp["input_auth"], "input_hdcp_status": hdcp["input_status"], "output_hdcp": hdcp["output_status"], "routes": self.get_routes(), "inputs_num": len(profile.available_input_ids), "outputs_num": len(profile.available_output_ids), "connection_protocol": self.connection_protocol}
    def set_connection(self, output_num, input_num):
        profile = self._profile()
        if output_num not in profile.available_output_ids or input_num not in profile.available_input_ids: raise ValueError("Input or output number is outside Matrix capability")
        command = "%s!" % input_num if profile.route_profile == "in1608" else "%s*1!" % input_num if profile.route_profile in {"in1804", "in1808"} else "%s*%s!" % (input_num, output_num)
        try: self._read(command, replay_safe=False)
        except Exception as error: setattr(error, "_matrix_route_command_invoked", True); raise
        return True
    def untie(self, output_num):
        profile = self._profile()
        if profile.route_profile != "crosspoint" or output_num not in profile.available_output_ids: raise ValueError("Output cannot be untied")
        return self._read("0*%s!" % output_num, replay_safe=False)
