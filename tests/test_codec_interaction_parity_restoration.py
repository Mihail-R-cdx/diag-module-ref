import unittest
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PyQt5.QtCore import QObject, pyqtSignal

from core.equipment_inventory import EquipmentInventory, EquipmentInventoryMetadata, EquipmentRecord
from core.parser import HuaweiTE40DataParser
from core.cloudlink_microphone_meter import SUPPORTED_CLOUDLINK_METER_MODELS
from core.room_diagnostic_tree import (
    DeviceRowState, DeviceRowStatus, RoomCycleStatus, RoomDiagnosticSession,
    RoomDiagnosticSessionIdentity, build_room_session, resolve_room_source,
)
from core.room_interaction import RoomInteractionBindings, RoomInteractionCoordinator
from core.exceptions import ConnectionError, ProtocolError
from gui.diagnostic_dispatch import dispatch_entry_for_model, normalize_codec_audio_projection, room_model_capabilities
from handlers.huawei.te20 import HuaweiTE20Handler
from handlers.huawei.te40 import HuaweiTE40Handler, extract_te40_current_audio_microphone_level


def microphone_state(mic1=18, *, complete=True):
    values = {"micall": 1}
    values.update({f"mic{index}": 1 for index in range(1, 19)})
    values.update({f"mic{index}Value": index for index in range(1, 19)})
    values["mic1Value"] = mic1
    if not complete:
        values.pop("mic18Value")
    return {"success": 1, "data": values}


class CodecInteractionParityTests(unittest.TestCase):
    def test_initial_expanded_waiting_source_admits_one_preview_after_terminal_cycle(self):
        """Source expansion is adopted at bind; neither bind nor rendering signals start I/O."""
        record = EquipmentRecord(
            "te40", "Huawei TE40", "Huawei TE40", "192.0.2.10",
            None, None, "R-1", "Room", "other",
        )
        inventory = EquipmentInventory.from_records(
            (record,), EquipmentInventoryMetadata(1, "sha256:" + "a" * 64),
        )
        session = build_room_session(
            inventory=inventory,
            source=resolve_room_source(inventory, record.ip_address, room_model_capabilities()),
            generation=7,
            capabilities=room_model_capabilities(),
        )
        row = session.row_for(record.record_id)
        self.assertEqual(DeviceRowStatus.WAITING, row.status)
        self.assertEqual(record.record_id, session.expanded_record_id)
        calls = []
        bindings = RoomInteractionBindings(
            auxiliary=lambda _context, action: calls.append(action),
            live=lambda _context: calls.append("live"),
            cancel=lambda _context: None,
            cleanup=lambda _context: False,
        )
        coordinator = RoomInteractionCoordinator(bindings_for_model=lambda _model: bindings)

        coordinator.bind_session(session)

        self.assertEqual(record.record_id, coordinator._expanded_record_id)
        self.assertEqual([], calls)  # Bind has no preview/device I/O.
        self.assertIsNone(coordinator.active_context)

        # The regular room cycle, not a synthetic Qt expansion event, makes
        # the source row usable and reaches the terminal admission boundary.
        row.status = DeviceRowStatus.CONNECTED
        row.accepted_snapshot = {}
        session.status = RoomCycleStatus.COMPLETE
        coordinator.cycle_finished(session)
        self.assertEqual(["call_log_preview"], calls)
        preview = coordinator.active_context
        self.assertIsNotNone(preview)
        coordinator.complete(preview, success=True, data={})
        self.assertEqual(["call_log_preview"], calls)
        coordinator.cleanup_finished(preview)
        self.assertEqual(["call_log_preview", "live"], calls)

        # A same-generation repaint/collapse/re-expand cannot consume a
        # second automatic preview; explicit journal acquisition is covered
        # by the separate fresh-action regressions.
        live = coordinator.active_context
        coordinator.collapse(record.record_id)
        coordinator.cleanup_finished(live)
        coordinator.expand(record.record_id)
        self.assertEqual(["call_log_preview", "live", "live"], calls)

    def test_te40_current_audio_microphone_extractor_aggregates_only_valid_exact_fields(self):
        cases = (
            ({"MicValueIndex": 41}, 41),
            ({"mic1ValueIndex": 37}, 37),
            ({"mic1ValueIndex": 37, "mic2ValueIndex": 41}, 41),
            ({"micArray1_01ValIdx": 17, "micArray1_02ValIdx": 83, "micArray1_03ValIdx": 41}, 83),
            ({"MicValueIndex": 20, "mic1ValueIndex": 37, "micArray1_01ValIdx": 70}, 70),
            ({"micArray1_01ValIdx": 70, "micArray2_03ValIdx": 91}, 91),
            ({"MicValueIndex": 20, "SpeakerValueIndex": 220}, 20),
            ({"MicValueIndex": 20, "trsInput": 220, "rcaInput": 220, "hdmiInput": 220,
              "dviInput": 220, "dpInput": 220, "pstnInput": 220, "sdiInput": 220}, 20),
            ({"micArray1_01ValIdx": 0}, 0),
            ({
                "MicValueIndex": None, "mic1ValueIndex": {}, "micArray1_01ValIdx": True,
                "micArray1_02ValIdx": "83", "micArray1_03ValIdx": float("nan"),
                "micArray2_01ValIdx": float("inf"), "micArray2_02ValIdx": [],
            }, None),
            ({
                "mic1Value": 99, "micXValueIndex": 99, "mic19ValueIndexx": 99,
                "micArray1_01Value": 99, "micArrayX_01ValIdx": 99,
                "micArray1_xxValIdx": 99, "unrelated": 99,
            }, None),
        )
        for payload, expected in cases:
            with self.subTest(payload=payload):
                self.assertEqual(expected, extract_te40_current_audio_microphone_level(payload))

    def test_te40_current_audio_seed_and_live_use_the_same_extractor(self):
        payload = {
            "mic1ValueIndex": 37, "micArray1_01ValIdx": 25,
            "micArray1_02ValIdx": 12, "micArray1_03ValIdx": 37,
            "SpeakerValueIndex": 220,
        }
        handler = HuaweiTE40Handler("192.0.2.10", username="u", password="p")

        def response(action, request_payload=None):
            if action == "get_current_audio_params":
                self.assertEqual({"acCSRFToken": ""}, request_payload)
                return {"success": 1, "data": json.dumps(payload)}
            return {"success": 0, "data": {}}

        handler.send_command = Mock(side_effect=response)
        seed = handler.get_status()["monitor_mic_value"]
        handler.get_sleep_mode = Mock(return_value="Off")
        live = handler.get_live_audio_status()["microphone"]

        self.assertEqual(37, seed)
        self.assertEqual(seed, live)
        self.assertTrue(all(
            call.args[0] != "get_monitor_audio_params"
            for call in handler.send_command.call_args_list
        ))

    def test_te40_current_audio_request_is_post_with_rmd_and_existing_session_material(self):
        handler = HuaweiTE40Handler("192.0.2.10", username="u", password="p")
        handler.is_connected = Mock(return_value=True)
        handler.session_id = "session-id"
        handler.csrf_token = "csrf-token"
        handler.opener = Mock()
        handler.opener.open.return_value = SimpleNamespace(
            read=lambda: b'{"success": 1, "data": "{}"}'
        )

        with patch("handlers.huawei.te40.random.random", return_value=0.25):
            self.assertEqual({}, handler._get_current_audio_params())

        request = handler.opener.open.call_args.args[0]
        self.assertEqual("POST", request.get_method())
        self.assertIn("ActionID=WEB_GetCurrentAudioParam", request.full_url)
        self.assertIn("rmd=0.25", request.full_url)
        self.assertIn(b'"acCSRFToken": "csrf-token"', request.data)

    def test_te40_current_audio_malformed_or_non_object_data_is_typed_protocol_failure(self):
        handler = HuaweiTE40Handler("192.0.2.10", username="u", password="p")
        handler.get_sleep_mode = Mock(return_value="Off")
        for data in ("{bad json", "[]"):
            with self.subTest(data=data):
                handler.send_command = Mock(return_value={"success": 1, "data": data})
                with self.assertRaises(ProtocolError):
                    handler.get_live_audio_status()

    def test_te20_live_remains_primary_micvalueindex_only(self):
        handler = HuaweiTE20Handler("192.0.2.10", username="u", password="p")
        handler.get_sleep_mode = Mock(return_value="Off")
        handler.send_command = Mock(return_value={"success": 1, "data": {
            "MicValueIndex": 20,
            "micArray1_01ValIdx": 220,
        }})

        live = handler.get_live_audio_status()

        self.assertEqual(20, live["audio"]["MicValueIndex"])
        self.assertNotIn("microphone", live)
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

    def test_te40_mic1_status_value_is_canonical_gain_when_micvalue_is_absent(self):
        handler = HuaweiTE40Handler("192.0.2.10", username="u", password="p")
        handler.send_command = Mock(side_effect=lambda action, _payload=None: (
            {"success": 1, "data": {"micall": 1, "mic1": 1, "mic1Value": 18}}
            if action == "get_audio_status" else {"success": 0, "data": {}}
        ))

        status = handler.get_status()
        parsed = HuaweiTE40DataParser.parse_raw_data(status)

        self.assertEqual(18, status["mic_volume"])
        self.assertEqual(18, parsed["microphone_volume"])
        self.assertEqual("6", parsed["Громкость микрофона"])

    def test_te40_parser_publishes_rich_statuses_and_uptime_without_new_io(self):
        parsed = HuaweiTE40DataParser.parse_raw_data({
            "mic_connection_status": "Микрофон C500 подключён",
            "camera_connection_status": "Камера C500 подключена",
            "mic_mute": "Off",
            "uptime": "12 дней 4 часов 37 минут",
        })

        self.assertEqual("Микрофон C500 подключён", parsed["microphone_status"])
        self.assertEqual("Камера C500 подключена", parsed["camera_status"])
        self.assertEqual("12 дней 4 часов 37 минут", parsed["uptime"])
        self.assertFalse(parsed["microphone_muted"])

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

    def test_terminal_preview_connection_failure_degrades_row_and_prevents_first_live(self):
        entry = dispatch_entry_for_model("CloudLink Bar 310")
        row = DeviceRowState("bar", "CloudLink Bar 310", "192.0.2.10", "CloudLink Bar 310", DeviceRowStatus.CONNECTED, capability=entry.room_capability(), accepted_snapshot={"cached": True})
        session = RoomDiagnosticSession(RoomDiagnosticSessionIdentity("s", 1, None, None, "r"), "r", None, None, [row], status=RoomCycleStatus.COMPLETE)
        calls = []
        bindings = RoomInteractionBindings(
            live=lambda _context: calls.append("live"),
            auxiliary=lambda _context, action: calls.append(action),
            cancel=lambda _context: calls.append("cancel"),
            cleanup=lambda _context: False,
        )
        coordinator = RoomInteractionCoordinator(bindings_for_model=lambda _model: bindings)
        coordinator.bind_session(session)
        coordinator.expand("bar")
        preview = coordinator.active_context

        coordinator.complete(
            preview, success=False, connection_lost=True,
            warning="Credentials отклонены",
        )

        self.assertEqual(DeviceRowStatus.DEGRADED, row.status)
        self.assertTrue(row.interaction_blocked)
        self.assertFalse(row.network_actions_enabled)
        self.assertEqual(["call_log_preview", "cancel"], calls)
        coordinator.cleanup_finished(preview)
        self.assertIsNone(coordinator.active_context)
        self.assertEqual(["call_log_preview", "cancel"], calls)

        # A late completion from the retired preview must not reopen the row
        # or admit the first LIVE owner.
        coordinator.complete(preview, success=True, data={"late": True})
        self.assertEqual(DeviceRowStatus.DEGRADED, row.status)
        self.assertTrue(row.interaction_blocked)
        self.assertEqual(["call_log_preview", "cancel"], calls)

    def test_ordinary_preview_failure_remains_non_degrading_and_live_can_start(self):
        entry = dispatch_entry_for_model("CloudLink Bar 310")
        row = DeviceRowState("bar", "CloudLink Bar 310", "192.0.2.10", "CloudLink Bar 310", DeviceRowStatus.CONNECTED, capability=entry.room_capability(), accepted_snapshot={})
        session = RoomDiagnosticSession(RoomDiagnosticSessionIdentity("s", 1, None, None, "r"), "r", None, None, [row], status=RoomCycleStatus.COMPLETE)
        calls = []
        bindings = RoomInteractionBindings(
            live=lambda _context: calls.append("live"),
            auxiliary=lambda _context, action: calls.append(action),
            cleanup=lambda _context: False,
        )
        coordinator = RoomInteractionCoordinator(bindings_for_model=lambda _model: bindings)
        coordinator.bind_session(session)
        coordinator.expand("bar")
        preview = coordinator.active_context

        coordinator.complete(preview, success=False, warning="Нет данных")
        coordinator.cleanup_finished(preview)

        self.assertEqual(DeviceRowStatus.CONNECTED, row.status)
        self.assertFalse(row.interaction_blocked)
        self.assertEqual(["call_log_preview", "live"], calls)

    def test_preview_auth_retry_persists_success_authority_before_live_handoff(self):
        from gui.main_window import VCSDiagnosticApp
        from gui.room_codec_call_log_controller import RoomCodecCallLogController

        class Signals(QObject):
            result = pyqtSignal(dict)
            error = pyqtSignal(dict)

        class ControlledSession:
            instances = []

            def __init__(self, *_args):
                self.signals = Signals()
                self.submitted = []
                self.shutdowns = 0
                self.__class__.instances.append(self)

            def activate_context(self, *_args):
                return 1

            def submit(self, operation, **_kwargs):
                self.submitted.append(operation)
                return 1

            def invalidate_context(self):
                pass

            def wait_until_idle(self, **_kwargs):
                pass

            def shutdown(self, **_kwargs):
                self.shutdowns += 1

        class ImmediatePool:
            def start(self, worker):
                worker.run()

        entry = dispatch_entry_for_model("Huawei TE40")
        row = DeviceRowState("te40", "Huawei TE40", "192.0.2.10", "Huawei TE40", DeviceRowStatus.CONNECTED, capability=entry.room_capability(), accepted_snapshot={})
        session = RoomDiagnosticSession(RoomDiagnosticSessionIdentity("s", 1, None, None, "r"), "r", None, None, [row], status=RoomCycleStatus.COMPLETE)
        candidates = ({"username": "first"}, {"username": "second"})
        persisted = {"credential_index": None, "profile": None}
        live_authority = []
        controller = RoomCodecCallLogController(thread_pool=ImmediatePool())
        bindings = RoomInteractionBindings(
            live=lambda _context: live_authority.append((
                window.get_current_credential_index("Huawei TE40", "192.0.2.10"),
                window.get_device_connection_profile("Huawei TE40", "192.0.2.10"),
                "get_live_audio_status",
            )),
            auxiliary=lambda _context, _action: None,
            cancel=controller.cancel,
            cleanup=lambda _context: False,
        )
        coordinator = RoomInteractionCoordinator(bindings_for_model=lambda _model: bindings)
        coordinator.bind_session(session)
        window = SimpleNamespace(
            room_interaction_coordinator=coordinator,
            room_diagnostic_session=session,
            room_call_log_controller=controller,
            _room_call_log_actions={},
            _room_call_log_windows={},
            _room_credential_attempts={},
            set_current_credential_index=lambda _model, index, _ip: persisted.update(credential_index=index),
            set_device_connection_profile=lambda _model, profile, _ip: persisted.update(profile=profile),
            get_current_credential_index=lambda _model, _ip: persisted["credential_index"],
            get_device_connection_profile=lambda _model, _ip: persisted["profile"],
        )
        def retry(current):
            window._room_credential_attempts[current] = (candidates, 1, None)
            controller.start(current, (candidates[1],), 0)
            return True
        window._retry_room_authentication = retry
        controller.operationFinished.connect(
            lambda *args: VCSDiagnosticApp._on_room_call_log_finished(window, *args)
        )

        coordinator.expand("te40")
        preview = coordinator.active_context
        window._room_call_log_actions[preview] = "call_log_preview"
        window._room_credential_attempts[preview] = (candidates, 0, None)
        with patch(
            "gui.room_codec_call_log_controller.InteractiveSessionController", ControlledSession
        ):
            controller.start(preview, (candidates[0],), 0)
            ControlledSession.instances[0].signals.error.emit({"category": "authentication"})
            self.assertEqual([], live_authority)
            self.assertIs(coordinator.active_context, preview)
            profile = {"protocol": "https", "port": 443}
            ControlledSession.instances[1].signals.result.emit({
                "value": {"records": []}, "credential_index": 0,
                "connection_profile": profile,
            })

        self.assertEqual([(1, profile, "get_live_audio_status")], live_authority)
        self.assertIsNotNone(coordinator.active_context)
        self.assertEqual("LIVE", coordinator.active_context.kind.value)

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
