from dataclasses import replace
import unittest

from core.exceptions import ProtocolError
from core.base_handler import BaseExtronMatrixHandler
from core.parser import ExtronMatrixDataParser, matrix_general_information_complete
from handlers.extron.matrix import (
    HDCP_PRESENT_HDCP, HDCP_PRESENT_NO_HDCP, IN1806_PART_NUMBER, XTP_PART_NUMBER_TO_MODEL,
    ExtronMatrixHandler, decode_hdcp, decode_xtp_input_board_symbol,
    decode_xtp_output_board_symbol, decode_xtp_ii_input_board_symbol,
    decode_xtp_ii_output_board_symbol, parse_signal_presence, parse_star_n,
    parse_xtp_topology,
    resolve_identity_token, resolve_matrix_capabilities,
    normalize_identity_response,
)


class RecordingMatrix(ExtronMatrixHandler):
    def __init__(self, identity, responses=None, expected_model=None):
        super().__init__("192.0.2.1", expected_model=expected_model)
        self.identity = identity
        self.responses = responses or {}
        self.commands = []

    def send_command(self, command, data=None, **kwargs):
        self.commands.append((command, kwargs.get("replay_safe", True)))
        is_dtp_identity = command == "I" and self.expected_model == "DTP CrossPoint 84"
        response = self.identity if command in {"1I", "N"} or is_dtp_identity else self.responses.get(command, "")
        return {"success": True, "response": response}


class MatrixProtocolFixtureTests(unittest.TestCase):
    def test_in1806_uses_documented_part_number(self):
        self.assertEqual(IN1806_PART_NUMBER, "60-1663-01")

    XTP3200_PART = "60-1167-01"
    XTP3200_STAR_N = "60-1167-01.GGHFXFIHDDDEJXXM"

    def test_tagged_identity_grammars_are_command_specific_and_fail_closed(self):
        self.assertEqual("IN1808 IPCP SA", normalize_identity_response("1I", "Inf01*IN1808 IPCP SA"))
        self.assertEqual("60-1381-01", normalize_identity_response("N", "Pno60-1381-01"))
        for command, value in (("1I", "Pno60-1381-01"), ("N", "Inf01*IN1808"), ("1I", "Inf01*IN1808\njunk")):
            self.assertIsNone(normalize_identity_response(command, value))
        self.assertEqual("IN1808", RecordingMatrix("Inf01*IN1808 IPCP SA", expected_model="Extron IN1808").get_device_info()["model"])
        self.assertEqual("DTP CrossPoint 108 4K", RecordingMatrix("Pno60-1381-01", expected_model="DTP CrossPoint 108 4K").get_device_info()["model"])

    def test_approved_identity_extensions_are_exact(self):
        self.assertEqual("IN1806", RecordingMatrix("IN1806", expected_model="Extron IN1806").get_device_info()["model"])
        self.assertEqual((1, 2, 3, 4, 5, 6), resolve_matrix_capabilities("IN1806").available_input_ids)
        self.assertEqual("IN1608 xi", RecordingMatrix("IN1608 xi IPCP SA", expected_model="Extron IN1608 xi").get_device_info()["model"])
        self.assertEqual("DTP CrossPoint 108 4K", resolve_identity_token("60-1381-12", "DTP").exact_model)
        self.assertIsNone(resolve_identity_token("60-1381-13", "DTP"))

    def test_general_information_uses_only_current_inventory_and_sis_evidence(self):
        current = {
            "model": "IN1806", "firmware": "1.04", "temperature": 0,
        }
        self.assertTrue(matrix_general_information_complete(
            current, mac_address="aa:bb:cc:dd:ee:ff", serial_number="SERIAL-1"
        ))
        self.assertFalse(matrix_general_information_complete(
            current, mac_address="aa:bb:cc:dd:ee:ff", serial_number=None
        ))
        self.assertFalse(matrix_general_information_complete(
            {**current, "firmware": None}, mac_address="aa:bb:cc:dd:ee:ff", serial_number="SERIAL-1"
        ))

    def test_every_production_profile_acquires_firmware_and_temperature_exactly(self):
        fixtures = (
            ("Extron IN1804", "IN1804", "w20STAT", "20Stat*0"),
            ("Extron IN1806", "IN1806", "w20STAT", "20Stat*0"),
            ("Extron IN1808", "IN1808", "w20STAT", "20Stat*0"),
            ("Extron IN1608 xi", "IN1608 xi", "w20STAT", "20Stat*0"),
            ("DTP CrossPoint 84", "DTPCP84", "S", "12.125 57.000 0 0"),
            ("DTP CrossPoint 82 4K", "60-1583-01", "S", "12.125 57.000 0 0"),
            ("DTP CrossPoint 84 4K", "60-1515-01", "S", "12.125 57.000 0 0"),
            ("DTP CrossPoint 86 4K", "60-1382-01", "S", "12.125 57.000 0 0"),
            ("DTP CrossPoint 108 4K", "60-1381-12", "S", "12.125 57.000 0 0"),
        )
        for expected, identity, temperature_command, temperature_response in fixtures:
            with self.subTest(expected=expected):
                handler = RecordingMatrix(
                    identity, {"Q": "1.04", temperature_command: temperature_response}, expected_model=expected
                )
                info = handler.get_device_info()
                self.assertEqual(expected.removeprefix("Extron "), info["model"])
                self.assertEqual("1.04", info["firmware"])
                self.assertEqual(0 if temperature_command == "w20STAT" else 57, info["temperature"])
                self.assertTrue(matrix_general_information_complete(
                    info, mac_address="aa:bb:cc:dd:ee:ff", serial_number="SERIAL-1"
                ))

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
        self.assertTrue(decode_xtp_ii_input_board_symbol("G"))
        self.assertTrue(decode_xtp_ii_output_board_symbol("D"))
        self.assertTrue(decode_xtp_ii_input_board_symbol("x"))
        self.assertTrue(decode_xtp_ii_output_board_symbol("x"))

    def test_xtp_ii_exact_part_numbers_are_known_but_unknown_is_not(self):
        expected = {
            "60-2031-01": "XTP II CrossPoint 1600", "60-2031-11": "XTP II CrossPoint 1600",
            "60-1545-01": "XTP II CrossPoint 1600", "60-1545-11": "XTP II CrossPoint 1600",
            "60-1981-01": "XTP II CrossPoint 3200", "60-1546-01": "XTP II CrossPoint 3200",
            "60-1386-01": "XTP II CrossPoint 6400",
        }
        self.assertEqual(expected, {key: XTP_PART_NUMBER_TO_MODEL[key] for key in expected})
        self.assertIsNone(resolve_identity_token("60-1167-01", "XTP II"))

    def test_exact_documented_identities_and_unknowns(self):
        # DTP CP 84 guide documents I -> DTPCP84.  DTP CP 4K's SIS guide
        # documents N; Extron product pages identify these base part numbers.
        self.assertEqual("DTP CrossPoint 84", resolve_identity_token("DTPCP84", "DTP").exact_model)
        self.assertEqual("DTP CrossPoint 82 4K", resolve_identity_token("60-1583-01", "DTP").exact_model)
        self.assertEqual("DTP CrossPoint 84 4K", resolve_identity_token("60-1515-01", "DTP").exact_model)
        self.assertEqual("DTP CrossPoint 86 4K", resolve_identity_token("60-1382-01", "DTP").exact_model)
        self.assertEqual("DTP CrossPoint 108 4K", resolve_identity_token("60-1381-01", "DTP").exact_model)
        # The archived manufacturer price list identifies this exact legacy
        # IPCP MA 70 SKU.  Adjacent suffixes remain fail-closed.
        self.assertEqual("DTP CrossPoint 108 4K", resolve_identity_token("60-1381-23", "DTP").exact_model)
        self.assertIsNone(resolve_identity_token("60-1381-24", "DTP"))
        self.assertEqual(
            "DTP CrossPoint 108 4K",
            RecordingMatrix("60-1381-23", expected_model="DTP CrossPoint 108 4K").get_device_info()["model"],
        )
        with self.assertRaises(ProtocolError):
            RecordingMatrix("60-1381-23", expected_model="DTP CrossPoint 86 4K").get_device_info()
        # Extron XTP Systems brochure: 60-1250-01/-11 identify XTP CP 1600.
        self.assertEqual("XTP CrossPoint 1600", resolve_identity_token("60-1250-01", "XTP").exact_model)
        self.assertIsNone(resolve_identity_token("60-1167-01", "XTP II"))
        self.assertIsNone(resolve_identity_token("60-0000-01", "XTP"))
        self.assertEqual("DTP CrossPoint 108 4K", resolve_identity_token("DTPCP108", "DTP").exact_model)
        self.assertIsNone(resolve_matrix_capabilities("XTP CrossPoint 6400"))

    def test_signal_sequence_is_mapped_by_logical_position_not_available_order(self):
        profile = resolve_identity_token(self.XTP3200_PART, "XTP")
        profile = replace(profile, logical_input_ids=tuple(range(1, 17)), available_input_ids=(1, 2, 3, 4, 5, 6, 7, 8, 13, 14, 15, 16))
        # XTP CrossPoint SIS guide: bare 0LS response is one status bit per
        # logical input, beginning with input 1.
        states = parse_signal_presence("1000000000001000", profile, profile.available_input_ids)
        self.assertTrue(states[1]); self.assertTrue(states[13]); self.assertNotIn(9, states)
        self.assertEqual({item: None for item in profile.available_input_ids}, parse_signal_presence("In00 1000", profile, profile.available_input_ids))

    def test_xtp_ii_documented_case_sensitive_star_n_key_and_slot_gaps(self):
        # XTP II CrossPoint Series User Guide, SIS Configuration and Control
        # p.60: N is part number and *N is part.slot-symbols; 1600 has four
        # input and four output slots.  Symbols below are from its published
        # key (n/T and o/U); x is its documented no-board symbol.
        part = "60-2031-01"
        fixture = "60-2031-01.nTxxoUxx"
        self.assertEqual((tuple(range(1, 17)), tuple(range(1, 17))), parse_xtp_topology("16x16", "60-2031-01.nlaTomrM", "XTP II", part))
        self.assertEqual((tuple(range(1, 9)), tuple(range(1, 9))), parse_xtp_topology("16x16", fixture, "XTP II", part))
        self.assertEqual((tuple(range(1, 5)) + tuple(range(9, 13)), tuple(range(1, 5)) + tuple(range(9, 13))), parse_xtp_topology("16x16", "60-2031-01.nxTxoxUx", "XTP II", part))
        self.assertEqual((tuple(range(1, 5)), tuple(range(1, 5))), parse_xtp_topology("16x16", "60-2031-01.nxxxoxxx", "XTP II", part))
        self.assertEqual(((), ()), parse_xtp_topology("16x16", "60-2031-01.qTxxoUxx", "XTP II", part))
        self.assertEqual(((), ()), parse_xtp_topology("16x16", "60-2031-01.nTxxqUxx", "XTP II", part))
        self.assertEqual(((), ()), parse_xtp_topology("16x16", "60-2031-01.nTxxoUx", "XTP II", part))
        self.assertEqual(((), ()), parse_xtp_topology("16x16", fixture, "XTP II", "60-1981-01"))

    def test_documented_crosspoint_0ls_grammar_and_logical_positions(self):
        # DTP CP 84/4K and XTP II guides document one status per logical
        # input and show the status sequence with single-space separators.
        # DTP CP 84 has eight logical inputs.
        dtp = resolve_identity_token("DTPCP84", "DTP")
        expected_dtp = {1: False, 2: False, 3: False, 4: True, 5: True, 6: True, 7: False, 8: True}
        self.assertEqual(expected_dtp, parse_signal_presence("0 0 0 1 1 1 0 1", dtp, dtp.available_input_ids))
        self.assertEqual(expected_dtp, parse_signal_presence("Frq00*0 0 0 1 1 1 0 1", dtp, dtp.available_input_ids))
        self.assertEqual(expected_dtp, parse_signal_presence("0LS\r\nFrq00*0 0 0 1 1 1 0 1", dtp, dtp.available_input_ids))

        # XTP CrossPoint guide proves only the contiguous bare all-input form.
        xtp = resolve_identity_token(self.XTP3200_PART, "XTP")
        xtp = replace(xtp, logical_input_ids=tuple(range(1, 17)), available_input_ids=(1, 2, 3, 4, 5, 6, 7, 8, 13, 14, 15, 16))
        self.assertTrue(parse_signal_presence("0000000000001000", xtp, xtp.available_input_ids)[13])
        self.assertEqual({item: None for item in xtp.available_input_ids}, parse_signal_presence("Frq00*0000000000001000", xtp, xtp.available_input_ids))
        self.assertEqual({item: None for item in xtp.available_input_ids}, parse_signal_presence("0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0", xtp, xtp.available_input_ids))

        xtp_ii = resolve_identity_token("60-2031-01", "XTP II")
        xtp_ii = replace(xtp_ii, logical_input_ids=tuple(range(1, 17)), available_input_ids=(1, 2, 3, 4, 5, 6, 7, 8, 13, 14, 15, 16))
        expected_xtp_ii = {item: item == 13 for item in xtp_ii.available_input_ids}
        self.assertEqual(expected_xtp_ii, parse_signal_presence("0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0", xtp_ii, xtp_ii.available_input_ids))
        self.assertEqual(expected_xtp_ii, parse_signal_presence("Frq00*0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0", xtp_ii, xtp_ii.available_input_ids))
        self.assertTrue(parse_signal_presence("Frq00*0000000000001000", xtp_ii, xtp_ii.available_input_ids)[13])
        unknown = {item: None for item in xtp_ii.available_input_ids}
        for malformed in ("Frq00*0000", "Frq00*00000000000010000", "Frq00*0 1 A 0", "Frq00*001x01", "foo 0 1 0 1", "0,,1,,0", "0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 tail", "0 0\n0 1"):
            self.assertEqual(unknown, parse_signal_presence(malformed, xtp_ii, xtp_ii.available_input_ids), malformed)

    def test_expected_model_mismatch_fails_closed(self):
        wrong_dtp = RecordingMatrix("60-1381-01", expected_model="DTP CrossPoint 84 4K")
        with self.assertRaises(ProtocolError):
            wrong_dtp.get_device_info()
        wrong_xtp = RecordingMatrix("60-1981-01", expected_model="XTP II CrossPoint 1600")
        with self.assertRaises(ProtocolError):
            wrong_xtp.get_device_info()

    def test_in1804_documented_wire_identities_resolve_to_one_canonical_profile(self):
        for identity in ("IN1804", "IN1804 DI", "IN1804 DO", "IN1804 DI/DO"):
            with self.subTest(identity=identity):
                profile = resolve_matrix_capabilities(identity)
                self.assertEqual("IN1804", profile.exact_model)
                self.assertEqual((1, 2, 3, 4), profile.available_input_ids)
                self.assertEqual((1,), profile.available_output_ids)
                self.assertEqual("IN1804", RecordingMatrix(identity, expected_model="Extron IN1804").get_device_info()["model"])
        for identity in ("IN1804 DIO", "IN1804 DI DO", "IN1804 DI/DO EXTRA", "IN1808"):
            with self.subTest(unrelated_identity=identity):
                if identity == "IN1808":
                    with self.assertRaises(ProtocolError):
                        RecordingMatrix(identity, expected_model="Extron IN1804").get_device_info()
                else:
                    self.assertIsNone(resolve_matrix_capabilities(identity))

    def test_in1808_documented_wire_identities_and_mismatches_fail_closed(self):
        aliases = ("IN1808", "IN1808 IPCP SA", "IN1808 IPCP MA 70", "IN1808 IPCP Q SA", "IN1808 IPCP Q MA 70")
        for identity in aliases:
            with self.subTest(identity=identity):
                self.assertEqual("IN1808", resolve_matrix_capabilities(identity).exact_model)
                self.assertEqual("IN1808", RecordingMatrix(identity, expected_model="Extron IN1808").get_device_info()["model"])
        for identity in ("IN1808 IPCP", "IN1808 EXTRA", "IN1808 IPCP SA EXTRA"):
            self.assertIsNone(resolve_matrix_capabilities(identity))
        with self.assertRaises(ProtocolError): RecordingMatrix("IN1804", expected_model="Extron IN1808").get_device_info()
        with self.assertRaises(ProtocolError): RecordingMatrix("IN1808 IPCP SA", expected_model="Extron IN1804").get_device_info()

    def test_in1804_legacy_hdcp_shapes_normalize_at_matrix_parser_boundary(self):
        caps = resolve_matrix_capabilities("IN1804")
        parsed = ExtronMatrixDataParser.parse({"capabilities": caps, "device_info": {"model": "IN1804"}, "input_hdcp_status": ["2", "1", "0", None], "input_hdcp_auth": [1, 1, 0, None], "output_hdcp": "1", "routes": {1: 3}})
        self.assertEqual({1: "PRESENT_HDCP", 2: "PRESENT_NO_HDCP", 3: "ABSENT", 4: "UNKNOWN"}, parsed["input_hdcp"])
        self.assertEqual({1: 1, 2: 1, 3: 0, 4: None}, parsed["input_hdcp_auth"])
        self.assertEqual({1: "1"}, parsed["output_hdcp"])

    def test_recorded_in1804_and_in1808_hdcp_temperature_evidence_remains_canonical(self):
        fixtures = (
            ("IN1804", 59, ["0", "1", "0", "1"], {1: "ABSENT", 2: "PRESENT_NO_HDCP", 3: "ABSENT", 4: "PRESENT_NO_HDCP"}),
            ("IN1808", 47, ["0", "1", "1", "1", "0", "0", "0", "0"], {1: "ABSENT", 2: "PRESENT_NO_HDCP", 3: "PRESENT_NO_HDCP", 4: "PRESENT_NO_HDCP", 5: "ABSENT", 6: "ABSENT", 7: "ABSENT", 8: "ABSENT"}),
        )
        for model, temperature, raw_hdcp, expected_hdcp in fixtures:
            with self.subTest(model=model):
                caps = resolve_matrix_capabilities(model)
                parsed = ExtronMatrixDataParser.parse({
                    "capabilities": caps,
                    "device_info": {"model": model, "temperature": temperature},
                    "input_hdcp_status": raw_hdcp,
                })
                self.assertEqual(temperature, parsed["temperature"])
                self.assertEqual(expected_hdcp, parsed["input_hdcp"])

    def test_in1804_alias_full_refresh_normalizes_baseline_snapshot(self):
        responses = {
            "w20STAT": "25",
            "wI1VNAM": "Laptop", "wI2VNAM": "Camera", "wI3VNAM": "PC", "wI4VNAM": "Doc Cam",
            "wO1VNAM": "Projector", "w0LS": "In00 1*0*1*0", "!": "In3 All",
            "wE1HDCP": "1", "wE2HDCP": "1", "wE3HDCP": "0", "wE4HDCP": "1",
            "wI1HDCP": "2", "wI2HDCP": "1", "wI3HDCP": "0", "wI4HDCP": "bad", "wO1HDCP": "1",
        }
        handler = RecordingMatrix("IN1804 DI/DO", responses, expected_model="Extron IN1804")
        status = handler.get_full_status()
        parsed = ExtronMatrixDataParser.parse(status)
        self.assertEqual("IN1804", status["device_info"]["model"])
        self.assertEqual((1, 2, 3, 4), status["capabilities"].available_input_ids)
        self.assertEqual({1: 3}, status["routes"])
        self.assertEqual([1, 2, 3, 4], parsed["available_input_ids"])
        self.assertEqual([1], parsed["available_output_ids"])
        self.assertEqual({1: 3}, parsed["routes"])
        self.assertEqual(3, parsed["current_connection"])

    def test_transport_echo_removal_is_exact_before_identity_resolution(self):
        self.assertEqual("IN1804 DI", BaseExtronMatrixHandler._strip_command_echo("1I", "1I\r\nIN1804 DI\r\n"))
        self.assertEqual("other\n1I\nIN1804 DI", BaseExtronMatrixHandler._strip_command_echo("1I", "other\r\n1I\r\nIN1804 DI"))

    def test_hdcp_mapping_stays_profile_specific(self):
        self.assertEqual(HDCP_PRESENT_NO_HDCP, decode_hdcp("1", "legacy"))
        self.assertEqual(HDCP_PRESENT_HDCP, decode_hdcp("1", "modern"))

    def test_new_presentation_profiles_use_video_only_route_commands(self):
        in1806 = RecordingMatrix("IN1806", {"1%": "Vid3"})
        in1806.get_device_info()
        self.assertEqual({1: 3}, in1806.get_routes())
        in1806.set_connection(1, 3)
        self.assertIn(("1%", True), in1806.commands)
        self.assertIn(("3*1%", False), in1806.commands)
        self.assertNotIn(("1!", True), in1806.commands)

        in1808 = RecordingMatrix("IN1808", {"1%": "Vid3"})
        in1808.get_device_info()
        self.assertEqual({1: 3}, in1808.get_routes())
        in1808.set_connection(1, 3)
        self.assertIn(("1%", True), in1808.commands)
        self.assertIn(("3*1%", False), in1808.commands)
        self.assertNotIn(("1!", True), in1808.commands)

        in1608 = RecordingMatrix("IN1608 xi IPCP SA", {"&": "01"}, expected_model="Extron IN1608 xi")
        in1608.get_device_info()
        self.assertEqual({1: 1}, in1608.get_routes())
        in1608.set_connection(1, 1)
        self.assertIn(("&", True), in1608.commands)
        self.assertIn(("1&", False), in1608.commands)
        self.assertNotIn(("!", True), in1608.commands)

    def test_real_in1608_and_dtp_read_only_status_grammars_are_usable(self):
        in1608 = RecordingMatrix("IN1608 xi IPCP SA", {
            "Q": "2.01", "w20STAT": "20Stat*42", "w0LS": "1*1*1*1*1*1*1*1", "&": "01",
        }, expected_model="Extron IN1608 xi")
        in1608_status = in1608.get_full_status()
        self.assertEqual("IN1608 xi", in1608_status["device_info"]["model"])
        self.assertEqual({1: 1}, in1608_status["routes"])
        self.assertIn(("&", True), in1608.commands)
        self.assertNotIn(("!", True), in1608.commands)

        dtp = RecordingMatrix("60-1382-01", {
            "Q": "2.01", "S": "12.125 57.000 0 0", "0LS": "1*1*1*1*1*1*1*1",
            **{"%s%%" % output: "Vid1" for output in range(1, 7)},
        }, expected_model="DTP CrossPoint 86 4K")
        dtp_status = dtp.get_full_status()
        parsed = ExtronMatrixDataParser.parse(dtp_status)
        self.assertEqual("DTP CrossPoint 86 4K", dtp_status["device_info"]["model"])
        self.assertEqual("2.01", parsed["firmware"])
        self.assertEqual(57, parsed["temperature"])
        self.assertEqual({output: 1 for output in range(1, 7)}, parsed["routes"])
        self.assertEqual("60-1382-01", dtp.part_number)
        self.assertNotIn("serial_number", dtp_status["device_info"])
        self.assertFalse(matrix_general_information_complete(
            dtp_status["device_info"], mac_address="aa:bb:cc:dd:ee:ff", serial_number=None,
        ))
        self.assertIn(("N", True), dtp.commands)
        self.assertIn(("S", True), dtp.commands)
        self.assertIn(("1%", True), dtp.commands)
        self.assertNotIn(("1!", True), dtp.commands)

    def test_real_route_and_temperature_grammars_fail_closed_when_malformed(self):
        in1608 = RecordingMatrix("IN1608 xi IPCP SA", {"&": "1"}, expected_model="Extron IN1608 xi")
        in1608.get_device_info()
        with self.assertRaises(ProtocolError):
            in1608.get_routes()
        for response in ("status*27", "12.125 57.000 0", "12.125 57.000 0 1", "12.125 57 0 0", "12.125 57.000 0 0 extra"):
            with self.subTest(response=response):
                self.assertIsNone(ExtronMatrixHandler._parse_temperature(response, "DTP"))

    def test_dtp_route_and_output_hdcp_are_production_specific(self):
        dtp = RecordingMatrix("60-1381-01", expected_model="DTP CrossPoint 108 4K")
        dtp.get_device_info(); dtp.get_hdcp_info()
        self.assertIn(("wO1HDCP", True), dtp.commands)
        dtp.responses.update({"1%": "Vid3", "0*1%": ""})
        self.assertEqual({1: 3}, dtp.get_routes((1,)))
        dtp.set_connection(1, 3)
        dtp.untie(1)
        self.assertIn(("1%", True), dtp.commands)
        self.assertIn(("3*1%", False), dtp.commands)
        self.assertIn(("0*1%", False), dtp.commands)
        self.assertNotIn(("1!", True), dtp.commands)
        rejected = RecordingMatrix("60-1381-01", {"1%": "E13"}, expected_model="DTP CrossPoint 108 4K")
        rejected.get_device_info()
        with self.assertRaises(ProtocolError):
            rejected.get_routes((1,))
        self.assertIsNone(resolve_matrix_capabilities("XTP CrossPoint 3200"))

    def test_parser_keeps_multi_output_route_authority(self):
        caps = resolve_matrix_capabilities("DTP CrossPoint 108 4K")
        parsed = ExtronMatrixDataParser.parse({"capabilities": caps, "device_info": {"model": "DTP CrossPoint 108 4K"}, "routes": {1: 3, 2: 7, 3: 3, 4: None}})
        self.assertEqual({1: 3, 2: 7, 3: 3, 4: None, 5: None, 6: None, 7: None, 8: None}, parsed["routes"])
        self.assertNotIn("current_connection", parsed)


if __name__ == "__main__":
    unittest.main()
