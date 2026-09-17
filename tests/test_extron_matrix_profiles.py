import unittest

from core.parser import ExtronMatrixDataParser
from handlers.extron.matrix import (
    HDCP_PRESENT_HDCP,
    HDCP_PRESENT_NO_HDCP,
    ExtronMatrixHandler,
    decode_hdcp,
    parse_xtp_topology,
    resolve_matrix_capabilities,
)


class RecordingMatrix(ExtronMatrixHandler):
    def __init__(self, identity, responses=None):
        super().__init__("192.0.2.1")
        self.identity = identity
        self.responses = responses or {}
        self.commands = []

    def send_command(self, command, data=None, **kwargs):
        self.commands.append((command, kwargs.get("replay_safe", True)))
        response = self.identity if command == "1I" else self.responses.get(command, "")
        return {"success": True, "response": response}


class MatrixProfileTests(unittest.TestCase):
    def test_exact_model_registry_rejects_nearest_names(self):
        self.assertIsNotNone(resolve_matrix_capabilities("Extron DTP CrossPoint 84 4K"))
        self.assertIsNone(resolve_matrix_capabilities("DTP2 CrossPoint 84 4K"))
        self.assertIsNone(resolve_matrix_capabilities("XTP CrossPoint 1234"))

    def test_in1808_and_in1608_route_commands_are_distinct(self):
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

    def test_dtp_and_xtp_output_hdcp_syntax_never_crosses(self):
        dtp = RecordingMatrix("DTP CrossPoint 84")
        dtp.get_device_info(); dtp.get_hdcp_info()
        self.assertIn(("wO1HDCP", True), dtp.commands)
        xtp = RecordingMatrix("XTP CrossPoint 1600", {"I": "4x4", "*N": "I: 1; O: 1"})
        xtp.get_device_info(); xtp.get_hdcp_info()
        self.assertIn(("w01HDCP", True), xtp.commands)
        self.assertNotIn(("wO1HDCP", True), xtp.commands)
        xtp_ii = RecordingMatrix("XTP II CrossPoint 1600", {"I": "4x4", "*N": "I: 1; O: 1"})
        xtp_ii.get_device_info(); xtp_ii.get_hdcp_info()
        self.assertFalse(any("O1HDCP" in item[0] or "01HDCP" in item[0] for item in xtp_ii.commands))

    def test_xtp_board_gaps_are_not_compressed(self):
        inputs, outputs = parse_xtp_topology((20, 20), {"input_slots": (True, True, False, False, True), "output_slots": (True, True, True, False, True)})
        self.assertEqual((1, 2, 3, 4, 5, 6, 7, 8, 17, 18, 19, 20), inputs)
        self.assertEqual((1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 17, 18, 19, 20), outputs)

    def test_hdcp_decoding_is_profile_specific(self):
        self.assertEqual(HDCP_PRESENT_NO_HDCP, decode_hdcp("1", "legacy"))
        self.assertEqual(HDCP_PRESENT_HDCP, decode_hdcp("1", "modern"))

    def test_parser_keeps_multi_output_route_authority(self):
        caps = resolve_matrix_capabilities("DTP CrossPoint 84")
        parsed = ExtronMatrixDataParser.parse({"capabilities": caps, "device_info": {"model": "DTP CrossPoint 84"}, "routes": {1: 3, 2: 7, 3: 3, 4: None}})
        self.assertEqual({1: 3, 2: 7, 3: 3, 4: None}, parsed["routes"])
        self.assertNotIn("current_connection", parsed)


if __name__ == "__main__":
    unittest.main()
