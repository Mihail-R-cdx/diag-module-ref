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
_XTP_FIRST_GEN = frozenset({"XTP CROSSPOINT 1600", "XTP CROSSPOINT 3200"})
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

# Exact documented compact identity tokens/part numbers.  Wire identity is
# evidence, not a marketing string; unknown tokens deliberately do not select
# a near profile.  The DTP CP 84 programming guide documents its ``I`` reply;
# the DTP CP 4K programming guide documents ``N`` as the part-number reply and
# Extron's product pages identify the exact base-frame part numbers below.
DTP_IDENTITY_TOKENS = {
    "DTPCP84": "DTP CrossPoint 84",
    "DTPCP108": "DTP CrossPoint 108 4K",
    "60-1583-01": "DTP CrossPoint 82 4K", "60-1583-92": "DTP CrossPoint 82 4K", "60-1583-92A": "DTP CrossPoint 82 4K", "60-1583-93": "DTP CrossPoint 82 4K", "60-1583-93A": "DTP CrossPoint 82 4K",
    "60-1515-01": "DTP CrossPoint 84 4K", "60-1515-92": "DTP CrossPoint 84 4K", "60-1515-92A": "DTP CrossPoint 84 4K", "60-1515-93": "DTP CrossPoint 84 4K", "60-1515-93A": "DTP CrossPoint 84 4K",
    "60-1382-01": "DTP CrossPoint 86 4K", "60-1382-92": "DTP CrossPoint 86 4K", "60-1382-92A": "DTP CrossPoint 86 4K", "60-1382-93": "DTP CrossPoint 86 4K", "60-1382-93A": "DTP CrossPoint 86 4K",
    "60-1381-01": "DTP CrossPoint 108 4K", "60-1381-92": "DTP CrossPoint 108 4K", "60-1381-92A": "DTP CrossPoint 108 4K", "60-1381-93": "DTP CrossPoint 108 4K", "60-1381-93A": "DTP CrossPoint 108 4K",
}
XTP_PART_NUMBER_TO_MODEL = {
    "60-1250-01": "XTP CrossPoint 1600", "60-1250-11": "XTP CrossPoint 1600",
    "60-1167-01": "XTP CrossPoint 3200",
    "60-2031-01": "XTP II CrossPoint 1600", "60-2031-11": "XTP II CrossPoint 1600",
    "60-1545-01": "XTP II CrossPoint 1600", "60-1545-11": "XTP II CrossPoint 1600",
    "60-1981-01": "XTP II CrossPoint 3200", "60-1546-01": "XTP II CrossPoint 3200",
    "60-1386-01": "XTP II CrossPoint 6400",
}

def resolve_identity_token(token, family):
    key = _identity_key(token)
    mapping = DTP_IDENTITY_TOKENS if family == "DTP" else XTP_PART_NUMBER_TO_MODEL
    model = mapping.get(key)
    profile = resolve_matrix_capabilities(model) if model else None
    # A documented part number identifies one generation only.  Do not allow
    # the compact XTP and XTP II probes to select one another's profile.
    return profile if profile is not None and profile.family == family else None

def decode_hdcp(raw, profile):
    try: value = int(str(raw).strip())
    except (TypeError, ValueError): return HDCP_UNKNOWN
    if value == 0: return HDCP_ABSENT
    return ({1: HDCP_PRESENT_NO_HDCP, 2: HDCP_PRESENT_HDCP} if profile == "legacy" else {1: HDCP_PRESENT_HDCP, 2: HDCP_PRESENT_NO_HDCP}).get(value, HDCP_UNKNOWN)

def _unknown_signal_states(ids):
    return {item: None for item in ids}

def _parse_documented_status_sequence(payload, *, allow_verbose, allow_spaces):
    """Validate a whole documented ``0LS`` status payload and return bits."""
    prefix = r"(?:Frq00\*)?" if allow_verbose else ""
    values = r"([01]+|[01](?: [01])*)" if allow_spaces else r"([01]+)"
    match = re.fullmatch(prefix + values, payload)
    return match.group(1).replace(" ", "") if match else None

def _documented_crosspoint_signal_bits(response, profile):
    """Return only the documented all-input ``0LS`` payload.

    DTP and XTP II programming guides specify a bare sequence of one status
    bit per logical input, or ``Frq00*`` followed by that sequence in verbose
    modes 2/3.  Their documented presentation also permits one ASCII space
    between adjacent status values.  The first-generation XTP guide proves
    only the bare contiguous form, so it remains deliberately narrower.  An
    echoed ``0LS`` command can precede the response on some transports.  No
    inferred labels (for example ``In00``) are accepted.
    """
    lines = _response_lines(response)
    if lines and lines[0] == "0LS":
        lines.pop(0)
    if len(lines) != 1:
        return None
    if profile.family == "DTP":
        return _parse_documented_status_sequence(lines[0], allow_verbose=True, allow_spaces=True)
    if profile.family == "XTP":
        return _parse_documented_status_sequence(lines[0], allow_verbose=False, allow_spaces=False)
    if profile.family == "XTP II":
        return _parse_documented_status_sequence(lines[0], allow_verbose=True, allow_spaces=True)
    return None

def parse_signal_presence(response, profile, available_input_ids):
    ids = tuple(available_input_ids or ())
    if not isinstance(response, str): return _unknown_signal_states(ids)
    if profile.family in {"DTP", "XTP", "XTP II"}:
        states = _documented_crosspoint_signal_bits(response, profile)
        max_id = max(getattr(profile, "logical_input_ids", ids) or ids, default=0)
        if states is None or len(states) != max_id:
            return _unknown_signal_states(ids)
        return {item: states[item - 1] == "1" for item in ids}
    lines = _response_lines(response)
    if lines and lines[0] in {"0LS", "w0LS"}: lines.pop(0)
    if len(lines) != 1: return _unknown_signal_states(ids)
    payload = lines[0]
    match = re.fullmatch(r"(?:In00\s+)?([01](?:\*[01])*)", payload)
    if not match: return _unknown_signal_states(ids)
    states = match.group(1).split("*")
    return {item: states[index] == "1" if index < len(states) else None for index, item in enumerate(ids)}

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
XTP_INPUT_SYMBOLS = frozenset("AFGHIKNPS")
XTP_OUTPUT_SYMBOLS = frozenset("BDEJMOU")
# XTP II CrossPoint Series User Guide, SIS Configuration and Control,
# Information requests / ``*N``: these symbols are case-sensitive.  They are
# intentionally independent of first-generation XTP's symbol domains.
XTP_II_INPUT_SYMBOLS = frozenset("nlaTPGFkIHjN")
XTP_II_OUTPUT_SYMBOLS = frozenset("omrMbUhOJED")

XTP_FRAME_SLOT_COUNTS = {
    "XTP CrossPoint 1600": (4, 4),
    "XTP CrossPoint 3200": (8, 8),
    "XTP II CrossPoint 1600": (4, 4),
    "XTP II CrossPoint 3200": (8, 8),
    "XTP II CrossPoint 6400": (16, 16),
}

def parse_star_n(response):
    match = re.fullmatch(r"\s*(60-\d{4}-\d{2})\.([A-Za-z]+)\s*", response or "")
    # Board symbols are case-sensitive in XTP II's official ``*N`` key.
    return (match.group(1).upper(), match.group(2)) if match else (None, None)
def decode_xtp_input_board_symbol(symbol): return symbol == "X" or symbol in XTP_INPUT_SYMBOLS
def decode_xtp_output_board_symbol(symbol): return symbol == "X" or symbol in XTP_OUTPUT_SYMBOLS
def decode_xtp_ii_input_board_symbol(symbol): return symbol == "x" or symbol in XTP_II_INPUT_SYMBOLS
def decode_xtp_ii_output_board_symbol(symbol): return symbol == "x" or symbol in XTP_II_OUTPUT_SYMBOLS
def parse_matrix_dimensions(response):
    if isinstance(response, str):
        found = re.search(r"(\d+)\s*[xX*]\s*(\d+)", response)
        return (int(found.group(1)), int(found.group(2))) if found else None
    return response if isinstance(response, tuple) and len(response) == 2 else None
def parse_xtp_topology(dimensions, board_evidence, family="XTP", expected_part_number=None):
    dimensions = parse_matrix_dimensions(dimensions)
    if not (isinstance(dimensions, tuple) and len(dimensions) == 2 and all(isinstance(x, int) and x >= 0 for x in dimensions)): return (), ()
    if family not in {"XTP", "XTP II"}: return (), ()
    part_number, sequence = parse_star_n(board_evidence)
    if not part_number or part_number != expected_part_number: return (), ()
    profile = resolve_identity_token(part_number, family)
    slot_counts = XTP_FRAME_SLOT_COUNTS.get(profile.exact_model) if profile else None
    if slot_counts is None: return (), ()
    logical_inputs, logical_outputs = dimensions
    input_slots, output_slots = slot_counts
    if (logical_inputs % 4 or logical_outputs % 4 or
            logical_inputs > input_slots * 4 or logical_outputs > output_slots * 4): return (), ()
    if len(sequence) != input_slots + output_slots: return (), ()
    in_symbols, out_symbols = sequence[:input_slots], sequence[input_slots:]
    decode_input = decode_xtp_ii_input_board_symbol if family == "XTP II" else decode_xtp_input_board_symbol
    decode_output = decode_xtp_ii_output_board_symbol if family == "XTP II" else decode_xtp_output_board_symbol
    if not all(decode_input(symbol) for symbol in in_symbols) or not all(decode_output(symbol) for symbol in out_symbols): return (), ()
    empty = "x" if family == "XTP II" else "X"
    return available_ids_from_slots(logical_inputs, tuple(symbol != empty for symbol in in_symbols)), available_ids_from_slots(logical_outputs, tuple(symbol != empty for symbol in out_symbols))

class ExtronMatrixHandler(BaseExtronMatrixHandler):
    """Exact-profile Matrix handler. Topology probes are read-only."""
    def __init__(self, ip_address, port=22023, username=None, password=None, expected_model=None):
        super().__init__(ip_address, port, username, password); self.model = None; self.part_number = None; self.expected_model = expected_model; self.capabilities = None; self.inputs_num = None; self.outputs_num = None; self.strict_session_failures = True
    def send_command(self, command, data=None, **kwargs): kwargs.setdefault("response_required", True); return super().send_command(command, data, **kwargs)
    def get_status(self): return self.get_full_status()
    def _read(self, command, *, replay_safe=True): return self.send_command(command, replay_safe=replay_safe)
    def get_device_info(self):
        requested = resolve_matrix_capabilities(self.expected_model)
        family = requested.family if requested is not None else "IN"
        # The legacy DTP CP 84 guide documents its exact ``I`` token.  The
        # DTP CP 4K guide documents ``N`` as the exact frame part-number
        # response; use it for the remaining fixed DTP models so CP 84's
        # overlapping product spelling cannot be guessed from a token.
        command = "1I" if family == "IN" else (
            "I" if family == "DTP" and requested and requested.exact_model == "DTP CrossPoint 84" else
            "N" if family in {"DTP", "XTP", "XTP II"} else "I"
        )
        result = self._read(command); identity = result.get("response", "").strip() if result and result.get("success") else ""
        profile = resolve_matrix_capabilities(identity) if family == "IN" else resolve_identity_token(identity, family)
        if profile is None: raise ProtocolError("Unsupported Extron Matrix identity: %s" % (identity or "<empty>"))
        if requested is not None and profile.exact_model != requested.exact_model:
            raise ProtocolError("Extron Matrix identity does not match expected model")
        self.model, self.part_number, self.capabilities = profile.exact_model, identity.upper() if family != "IN" else None, profile
        if profile.family in {"XTP", "XTP II"}:
            dimensions = parse_matrix_dimensions(self._read("I").get("response", ""))
            available_inputs, available_outputs = parse_xtp_topology(dimensions, self._read("*N").get("response", ""), profile.family, self.part_number)
            if not available_inputs or not available_outputs: raise ProtocolError("XTP topology evidence was unavailable or malformed")
            self.capabilities = replace(profile, logical_input_ids=_ids(dimensions[0]), logical_output_ids=_ids(dimensions[1]), available_input_ids=available_inputs, available_output_ids=available_outputs)
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
        response = self._read("w0LS" if profile.family == "IN" else "0LS").get("response", "")
        return parse_signal_presence(response, profile, profile.available_input_ids)
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
