import unittest
from unittest.mock import Mock

from core.parser import HuaweiTE40DataParser
from core.cloudlink_microphone_meter import SUPPORTED_CLOUDLINK_METER_MODELS
from core.room_diagnostic_tree import DeviceRowState, DeviceRowStatus, RoomCycleStatus, RoomDiagnosticSession, RoomDiagnosticSessionIdentity
from core.room_interaction import RoomInteractionBindings, RoomInteractionCoordinator
from core.exceptions import ConnectionError
from gui.diagnostic_dispatch import dispatch_entry_for_model, normalize_codec_audio_projection
from handlers.huawei.te40 import HuaweiTE40Handler


def microphone_state(mic1=18, *, complete=True):
    values = {"micall": 1}
    values.update({f"mic{index}": 1 for index in range(1, 19)})
    values.update({f"mic{index}Value": index for index in range(1, 19)})
    values["mic1Value"] = mic1
    if not complete:
        values.pop("mic18Value")
    return {"success": 1, "data": values}


class CodecInteractionParityTests(unittest.TestCase):
    def test_te40_numeric_gain_and_mute_are_independent(self):
        snapshot = HuaweiTE40DataParser.parse_raw_data({"mic_volume": 18, "mic_mute": "Off"})
        audio = normalize_codec_audio_projection(snapshot, "Huawei TE40")
        self.assertEqual(18, audio.microphone_volume)
        self.assertEqual(6, audio.microphone_volume - 12)
        self.assertEqual("UNMUTED", audio.microphone_mute_state.value)

        zero = HuaweiTE40DataParser.parse_raw_data({"mic_volume": 0, "mic_mute": "Off"})
        zero_audio = normalize_codec_audio_projection(zero, "Huawei TE40")
        self.assertEqual(0, zero_audio.microphone_volume)
        self.assertEqual("UNMUTED", zero_audio.microphone_mute_state.value)

    def test_te40_gain_uses_fresh_full_state_and_preserves_collateral(self):
        handler = HuaweiTE40Handler("192.0.2.10", username="u", password="p")
        pre = microphone_state(18)
        post = microphone_state(19)
        handler.send_command = Mock(side_effect=[pre, {"success": 1, "data": ""}, post])

        result = handler.set_microphone_gain(19)

        self.assertEqual({"confirmed": True, "microphone_volume": 19}, result)
        action, payload = handler.send_command.call_args_list[1].args
        self.assertEqual("WEB_SaveAudioMicCtrlParams", action)
        self.assertEqual(19, payload["mic1Value"])
        self.assertEqual(pre["data"]["mic2Value"], payload["mic2Value"])
        self.assertEqual(set(handler._MICROPHONE_SAVE_FIELDS), set(payload))

    def test_te40_incomplete_pre_read_sends_no_save(self):
        handler = HuaweiTE40Handler("192.0.2.10", username="u", password="p")
        handler.send_command = Mock(return_value=microphone_state(18, complete=False))
        self.assertEqual({"pre_submit_failure": True}, handler.set_microphone_gain(19))
        handler.send_command.assert_called_once_with("get_audio_status")

    def test_te40_collateral_mismatch_is_not_confirmed(self):
        handler = HuaweiTE40Handler("192.0.2.10", username="u", password="p")
        post = microphone_state(19)
        post["data"]["mic2Value"] = 99
        handler.send_command = Mock(side_effect=[microphone_state(18), {"success": 1}, post])
        with self.assertRaises(Exception):
            handler.set_microphone_gain(19)
        self.assertEqual("WEB_SaveAudioMicCtrlParams", handler.send_command.call_args_list[1].args[0])

    def test_te40_pre_read_transport_failure_is_definite_no_send(self):
        handler = HuaweiTE40Handler("192.0.2.10", username="u", password="p")
        handler.send_command = Mock(side_effect=ConnectionError("offline"))
        stages = []

        result = handler.set_microphone_gain(19, stage_callback=stages.append)

        self.assertTrue(result["pre_submit_failure"])
        self.assertTrue(result["connection_lost"])
        self.assertEqual([], stages)
        handler.send_command.assert_called_once_with("get_audio_status")

    def test_te40_possible_send_stage_precedes_ambiguous_post_failure(self):
        handler = HuaweiTE40Handler("192.0.2.10", username="u", password="p")
        handler.send_command = Mock(side_effect=[microphone_state(18), ConnectionError("timeout")])
        stages = []

        with self.assertRaises(ConnectionError):
            handler.set_microphone_gain(19, stage_callback=stages.append)

        self.assertEqual(["post_may_have_been_sent"], stages)
        self.assertEqual("WEB_SaveAudioMicCtrlParams", handler.send_command.call_args_list[1].args[0])

    def test_possible_send_stage_marks_composition_before_terminal_callback(self):
        from gui.main_window import VCSDiagnosticApp

        context = object()
        window = type("Window", (), {"_room_codec_mutations": {context: {"command_submitted": False}}})()
        VCSDiagnosticApp._on_room_codec_mutation_stage(
            window, context, "microphone_gain", {"stage": "post_may_have_been_sent"},
        )
        self.assertTrue(window._room_codec_mutations[context]["command_submitted"])

    def test_preterminal_codec_expansion_waits_for_preview_cleanup_before_live(self):
        entry = dispatch_entry_for_model("CloudLink Bar 310")
        row = DeviceRowState("bar", "CloudLink Bar 310", "192.0.2.10", "CloudLink Bar 310", DeviceRowStatus.CONNECTED, capability=entry.room_capability(), accepted_snapshot={})
        session = RoomDiagnosticSession(RoomDiagnosticSessionIdentity("s", 1, None, None, "r"), "r", None, None, [row], status=RoomCycleStatus.ACTIVE)
        calls = []
        bindings = RoomInteractionBindings(
            live=lambda _context: calls.append("live"),
            auxiliary=lambda _context, action: calls.append(action),
            cancel=lambda _context: None,
            cleanup=lambda _context: False,
        )
        coordinator = RoomInteractionCoordinator(bindings_for_model=lambda _model: bindings)
        coordinator.bind_session(session)

        coordinator.expand("bar")
        self.assertEqual([], calls)
        session.status = RoomCycleStatus.COMPLETE
        coordinator.cycle_finished(session)
        self.assertEqual(["call_log_preview"], calls)
        preview = coordinator.active_context
        coordinator.complete(preview, success=True, data={})
        self.assertEqual(["call_log_preview"], calls)
        coordinator.cleanup_finished(preview)
        self.assertEqual(["call_log_preview", "live"], calls)

    def test_terminal_preview_marker_allows_live_but_not_second_preview_after_reexpand(self):
        entry = dispatch_entry_for_model("CloudLink Bar 310")
        row = DeviceRowState("bar", "CloudLink Bar 310", "192.0.2.10", "CloudLink Bar 310", DeviceRowStatus.CONNECTED, capability=entry.room_capability(), accepted_snapshot={})
        session = RoomDiagnosticSession(RoomDiagnosticSessionIdentity("s", 1, None, None, "r"), "r", None, None, [row], status=RoomCycleStatus.COMPLETE)
        calls = []
        bindings = RoomInteractionBindings(
            live=lambda _context: calls.append("live"),
            auxiliary=lambda _context, action: calls.append(action),
            cancel=lambda _context: None,
            cleanup=lambda _context: False,
        )
        coordinator = RoomInteractionCoordinator(bindings_for_model=lambda _model: bindings)
        coordinator.bind_session(session)
        coordinator.expand("bar")
        preview = coordinator.active_context
        coordinator.complete(preview, success=True, data={})
        coordinator.cleanup_finished(preview)
        live = coordinator.active_context
        coordinator.collapse("bar")
        coordinator.cleanup_finished(live)
        coordinator.expand("bar")

        self.assertEqual(["call_log_preview", "live", "live"], calls)

    def test_te40_camera_accepts_one_entry(self):
        handler = HuaweiTE40Handler("192.0.2.10", username="u", password="p")

        def response(command, _data=None):
            if command == "get_camera_status":
                return {"success": 1, "data": {"itemList": [{"itemState": 1, "itemID": 1}]}}
            if command == "WEB_GetCamTypeByPort":
                return {"success": 1, "data": {"Param1": 0}}
            return {"success": 0}

        handler.send_command = Mock(side_effect=response)
        status = handler.get_status()
        self.assertEqual("On", status["camera_status"])
        self.assertIn("C500", status["camera_connection_status"])

    def test_box_has_no_live_but_keeps_generation_preview(self):
        entry = dispatch_entry_for_model("CloudLink Box 310")
        self.assertIsNone(entry.live_binding_key)
        self.assertNotIn("CloudLink Box 310", SUPPORTED_CLOUDLINK_METER_MODELS)
        row = DeviceRowState("box", "CloudLink Box 310", "192.0.2.10", "CloudLink Box 310", DeviceRowStatus.CONNECTED, capability=entry.room_capability(), accepted_snapshot={})
        session = RoomDiagnosticSession(RoomDiagnosticSessionIdentity("s", 1, None, None, "r"), "r", None, None, [row], status=RoomCycleStatus.COMPLETE)
        calls = []
        coordinator = RoomInteractionCoordinator(bindings_for_model=lambda _model: RoomInteractionBindings(auxiliary=lambda _context, action: calls.append(action)))
        coordinator.bind_session(session)
        coordinator.expand("box")
        coordinator.request_codec_preview()
        self.assertEqual(["call_log_preview"], calls)
        preview = coordinator.active_context
        coordinator.complete(preview, success=True, data={})
        coordinator.cleanup_finished(preview)
        self.assertIsNone(coordinator.active_context)
        self.assertEqual(["call_log_preview"], calls)


if __name__ == "__main__":
    unittest.main()
