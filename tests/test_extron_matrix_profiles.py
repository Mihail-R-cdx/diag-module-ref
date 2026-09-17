from dataclasses import replace
import unittest

from core.exceptions import ProtocolError
from core.parser import ExtronMatrixDataParser
from handlers.extron.matrix import (
    HDCP_PRESENT_HDCP, HDCP_PRESENT_NO_HDCP, XTP_PART_NUMBER_TO_MODEL,
    ExtronMatrixHandler, decode_hdcp, decode_xtp_input_board_symbol,
    decode_xtp_output_board_symbol, decode_xtp_ii_input_board_symbol,
    decode_xtp_ii_output_board_symbol, parse_signal_presence, parse_star_n,
    parse_xtp_topology,
    resolve_identity_token, resolve_matrix_capabilities,
)


class RecordingMatrix(ExtronMatrixHandler):
    def __init__(self, identity, responses=None, expected_model=None):
        super().__init__("192.0.2.1", expected_model=expected_model)
        self.identity = identity
        self.responses = responses or {}
        self.commands = []

    def send_command(self, command, data=None, **kwargs):
        self.commands.append((command, kwargs.get("replay_safe", True)))
        is_dtp_identity = command == "I" and self.expected_model == "DTP CrossPoint 108 4K"
        response = self.identity if command in {"1I", "N"} or is_dtp_identity else self.responses.get(command, "")
        return {"success": True, "response": response}


class MatrixProtocolFixtureTests(unittest.TestCase):
    XTP3200_PART = "60-1167-01"
    XTP3200_STAR_N = "60-1167-01.GGHFXFIHDDDEJXXM"

    def test_xtp3200_documented_part_identity_and_compact_star_n(self):
        profile = resolve_identity_token(self.XTP3200_PART, "XTP")
        self.assertEqual("XTP CrossPoint 3200", profile.exact_model)
        self.assertEqual((self.XTP3200_PART, "GGHFXFIHDDDEJXXM"), parse_star_n(self.XTP3200_STAR_N))
        inputs, outputs = parse_xtp_topology("32x32", self.XTP3200_STAR_N, "XTP", self.XTP3200_PART)
        self.assertEqual(tuple(range(1, 17)) + tuple(range(21, 33)), inputs)
        self.assertEqual((1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 29, 30, 31, 32), outputs)

    def test_xtp_part_and_star_n_mismatch_or_bad_symbols_fail_closed(self):
        self.assertEqual(((), ()), parse_xtp_topology("32x32", self.XTP3200_STAR_N, "XTP", "60-9999-01"))
        self.assertEqual(((), ()), parse_xtp_topology("32x32", "60-1167-01.GGHQXFIHDDDEJXXM", "XTP", self.XTP3200_PART))
        self.assertEqual(((), ()), parse_xtp_topology("32x32", "60-1167-01.GGHFXFIHDDDEJXXMB", "XTP", self.XTP3200_PART))
        self.assertEqual(((), ()), parse_xtp_topology("32x32", "60-1167-01.GGHFXFIHDDDEJXX", "XTP", self.XTP3200_PART))
        self.assertIsNone(resolve_identity_token("60-9999-01", "XTP"))
        mismatch = RecordingMatrix(self.XTP3200_PART, {"I": "32x32", "*N": "60-9999-01.GGHFXFIHDDDEJXXM"}, expected_model="XTP CrossPoint 3200")
        with self.assertRaises(ProtocolError):
            mismatch.get_device_info()

    def test_documented_first_generation_symbol_domains_are_separate(self):
        self.assertTrue(all(decode_xtp_input_board_symbol(symbol) for symbol in "AFGHIKNPSX"))
        self.assertTrue(all(decode_xtp_output_board_symbol(symbol) for symbol in "BDEJMOUX"))
        self.assertFalse(decode_xtp_input_board_symbol("B"))
        self.assertFalse(decode_xtp_output_board_symbol("G"))
        self.assertFalse(decode_xtp_ii_input_board_symbol("G"))
        self.assertFalse(decode_xtp_ii_output_board_symbol("D"))
        self.assertTrue(decode_xtp_ii_input_board_symbol("X"))
        self.assertTrue(decode_xtp_ii_output_board_symbol("X"))

    def test_xtp_ii_exact_part_numbers_are_known_but_unknown_is_not(self):
        expected = {
            "60-2031-01": "XTP II CrossPoint 1600", "60-2031-11": "XTP II CrossPoint 1600",
            "60-1545-01": "XTP II CrossPoint 1600", "60-1545-11": "XTP II CrossPoint 1600",
            "60-1981-01": "XTP II CrossPoint 3200", "60-1546-01": "XTP II CrossPoint 3200",
            "60-1386-01": "XTP II CrossPoint 6400",
        }
        self.assertEqual(expected, {key: XTP_PART_NUMBER_TO_MODEL[key] for key in expected})
        self.assertIsNone(resolve_identity_token("60-1167-01", "XTP II"))

    def test_unproven_identities_fail_closed(self):
        self.assertIsNone(resolve_identity_token("60-1167-01", "XTP II"))
        self.assertIsNone(resolve_identity_token("60-0000-01", "XTP"))
        self.assertIsNone(resolve_identity_token("DTPCP84", "DTP"))
        self.assertEqual("DTP CrossPoint 108 4K", resolve_identity_token("DTPCP108", "DTP").exact_model)
        self.assertIsNone(resolve_matrix_capabilities("XTP CrossPoint 6400"))

    def test_signal_sequence_is_mapped_by_logical_position_not_available_order(self):
        profile = resolve_identity_token(self.XTP3200_PART, "XTP")
        profile = replace(profile, logical_input_ids=tuple(range(1, 17)), available_input_ids=(1, 2, 3, 4, 5, 6, 7, 8, 13, 14, 15, 16))
        states = parse_signal_presence("In00 1000000000001000", profile, profile.available_input_ids)
        self.assertTrue(states[1]); self.assertTrue(states[13]); self.assertNotIn(9, states)
        self.assertEqual({item: None for item in profile.available_input_ids}, parse_signal_presence("1*0*1", profile, profile.available_input_ids))

    def test_hdcp_mapping_stays_profile_specific(self):
        self.assertEqual(HDCP_PRESENT_NO_HDCP, decode_hdcp("1", "legacy"))
        self.assertEqual(HDCP_PRESENT_HDCP, decode_hdcp("1", "modern"))

    def test_in1808_and_in1608_route_commands_remain_distinct(self):
        in1808 = RecordingMatrix("IN1808", {"1!": "In3 All"})
        in1808.get_device_info()
        self.assertEqual({1: 3}, in1808.get_routes())
        in1808.set_connection(1, 3)
        self.assertIn(("1!", True), in1808.commands)
        self.assertIn(("3*1!", False), in1808.commands)
        in1608 = RecordingMatrix("IN1608 xi", {"!": "In3 All"})
        in1608.get_device_info()
        in1608.set_connection(1, 3)
        self.assertIn(("3!", False), in1608.commands)

    def test_dtp_and_xtp_output_hdcp_syntax_remains_separate(self):
        dtp = RecordingMatrix("DTPCP108", expected_model="DTP CrossPoint 108 4K")
        dtp.get_device_info(); dtp.get_hdcp_info()
        self.assertIn(("wO1HDCP", True), dtp.commands)
        xtp = RecordingMatrix(self.XTP3200_PART, {"I": "32x32", "*N": self.XTP3200_STAR_N}, expected_model="XTP CrossPoint 3200")
        xtp.get_device_info(); xtp.get_hdcp_info()
        self.assertIn(("w01HDCP", True), xtp.commands)
        self.assertNotIn(("wO1HDCP", True), xtp.commands)

    def test_parser_keeps_multi_output_route_authority(self):
        caps = resolve_matrix_capabilities("DTP CrossPoint 108 4K")
        parsed = ExtronMatrixDataParser.parse({"capabilities": caps, "device_info": {"model": "DTP CrossPoint 108 4K"}, "routes": {1: 3, 2: 7, 3: 3, 4: None}})
        self.assertEqual({1: 3, 2: 7, 3: 3, 4: None, 5: None, 6: None, 7: None, 8: None}, parsed["routes"])
        self.assertNotIn("current_connection", parsed)


if __name__ == "__main__":
    unittest.main()
