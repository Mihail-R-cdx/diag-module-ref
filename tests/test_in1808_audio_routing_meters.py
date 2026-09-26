import os
import re
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from core.exceptions import CommandOutcomeUnknownError, ProtocolError
from core.parser import ExtronMatrixDataParser
from handlers.extron.in1808_audio import (
    IN1808_PRODSP_PROFILE_MAPPING,
    INPUT_METER_GROUPS,
    IN1808AudioProfile,
    audio_name_command,
    dbfs_from_raw_meter,
    meter_enable_command,
    meter_read_command,
    mixpoint_oid,
    mixpoint_read_command,
    output_meter_groups,
    parse_audio_name,
    parse_meter_response,
    parse_mixpoint_response,
    parse_program_source,
    routing_columns,
    variant_for_identity,
)
from handlers.extron.matrix import ExtronMatrixHandler, resolve_matrix_capabilities


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class FakeAudioRead:
    def __init__(self, overrides=None):
        self.overrides = dict(overrides or {})
        self.commands = []

    def __call__(self, command, **kwargs):
        self.commands.append((command, kwargs.get("replay_safe", True)))
        value = self.overrides.get(command)
        if isinstance(value, list):
            value = value.pop(0)
        if isinstance(value, BaseException):
            raise value
        if callable(value):
            value = value(command, kwargs)
        if value is None:
            if re.fullmatch(r"WI\d+ANAM", command):
                value = f"Configured {command[2:-4]}"
            elif re.fullmatch(r"WO\d+ANAM", command):
                value = f"Output {command[2:-4]}"
            elif command == "1$":
                value = "3"
            elif re.fullmatch(r"M\d+AU", command):
                value = "0"
            elif re.fullmatch(r"V\d+\*1AU", command):
                oid = re.search(r"\d+", command).group(0)
                value = f"DsV{oid}*1"
            elif re.fullmatch(r"V\d+AU", command):
                value = "1*500"
            else:
                value = ""
        return {"success": True, "response": value}


class IN1808AudioDomainTests(unittest.TestCase):
    def test_wire_variants_are_closed_and_preserve_amplifier_capability(self):
        expected = {
            "IN1808": "base",
            "IN1808 IPCP SA": "stereo_amplifier",
            "IN1808 IPCP MA 70": "mono_amplifier",
            "IN1808 IPCP Q SA": "stereo_amplifier",
            "IN1808 IPCP Q MA 70": "mono_amplifier",
        }
        self.assertEqual(expected, {identity: variant_for_identity(identity) for identity in expected})
        self.assertIsNone(variant_for_identity("IN1808 IPCP"))
        self.assertIsNone(variant_for_identity("IN1808 IPCP SA EXTRA"))

    def test_variant_filtering_happens_before_meter_or_route_generation(self):
        self.assertEqual(7, len(output_meter_groups("IN1808")))
        self.assertEqual((60010,), tuple(oid for _, oid in output_meter_groups("IN1808 IPCP MA 70")[-1].components))
        self.assertEqual((60010, 60011), tuple(oid for _, oid in output_meter_groups("IN1808 IPCP SA")[-1].components))
        self.assertEqual(10, len(routing_columns("IN1808")))
        self.assertEqual(11, len(routing_columns("IN1808 IPCP MA 70")))
        self.assertEqual(12, len(routing_columns("IN1808 IPCP SA")))

    def test_audio_name_commands_use_stable_one_based_ids(self):
        self.assertEqual("WI1ANAM", audio_name_command("input", 1))
        self.assertEqual("WI15ANAM", audio_name_command("input", 15))
        self.assertEqual("WO1ANAM", audio_name_command("output", 1))
        self.assertEqual("WO7ANAM", audio_name_command("output", 7))
        for kind, value in (("input", 0), ("input", 16), ("output", 8)):
            with self.subTest(kind=kind, value=value), self.assertRaises(ValueError):
                audio_name_command(kind, value)

    def test_audio_name_parser_uses_deterministic_fallback(self):
        self.assertEqual("Desk", parse_audio_name("Desk", command="WI1ANAM", fallback="DP 1")["value"])
        for value in ("", "   ", "E13", "one\ntwo", "\x00bad"):
            with self.subTest(value=value):
                parsed = parse_audio_name(value, command="WI1ANAM", fallback="DP 1")
                self.assertEqual("DP 1", parsed["value"])
                self.assertEqual("FALLBACK", parsed["outcome"])

    def test_meter_topology_is_exact_and_stable(self):
        input_oids = tuple(oid for group in INPUT_METER_GROUPS for _channel, oid in group.components)
        self.assertEqual(tuple(range(30000, 30018)) + tuple(range(40000, 40006)), input_oids)
        base_output_oids = tuple(oid for group in output_meter_groups("IN1808") for _channel, oid in group.components)
        self.assertEqual(tuple(range(60000, 60010)), base_output_oids)

    def test_meter_commands_accept_only_approved_oids(self):
        self.assertEqual("V30000AU", meter_read_command(30000))
        self.assertEqual("V60011*1AU", meter_enable_command(60011))
        for oid in (29999, 30018, 39999, 40006, 59999, 60012):
            with self.subTest(oid=oid), self.assertRaises(ValueError):
                meter_read_command(oid)

    def test_raw_meter_is_preserved_with_approved_dbfs_conversion(self):
        parsed = parse_meter_response("1*972", "V40000AU")
        self.assertEqual(972, parsed["raw_meter"])
        self.assertEqual(-97.2, parsed["dbfs"])
        self.assertEqual(-12.3, dbfs_from_raw_meter(123))
        self.assertTrue(parsed["available"])

    def test_inactive_or_malformed_meter_does_not_fabricate_zero_dbfs(self):
        inactive = parse_meter_response("0*988")
        malformed = parse_meter_response("bad")
        self.assertEqual(988, inactive["raw_meter"])
        self.assertNotIn("dbfs", inactive)
        self.assertIsNone(malformed["raw_meter"])
        self.assertNotIn("dbfs", malformed)

    def test_stereo_aggregation_uses_louder_side_and_retains_components(self):
        reader = FakeAudioRead({"V30000AU": "1*500", "V30001AU": "1*300"})
        meters = IN1808AudioProfile("IN1808").poll_meters(reader, is_current=lambda: True)
        group = meters["input_meters"][0]
        self.assertEqual(-30.0, group["display_dbfs"])
        self.assertEqual([500, 300], [item["raw_meter"] for item in group["components"]])
        self.assertEqual("VALID", group["outcome"])

    def test_partial_stereo_uses_valid_side_without_substituting_zero(self):
        reader = FakeAudioRead({"V30000AU": "1*450", "V30001AU": "E13"})
        group = IN1808AudioProfile("IN1808").poll_meters(reader, is_current=lambda: True)["input_meters"][0]
        self.assertEqual(-45.0, group["display_dbfs"])
        self.assertEqual("PARTIAL", group["outcome"])
        self.assertIsNone(group["components"][1]["raw_meter"])

    def test_state_zero_enables_once_then_reconciles_with_read(self):
        reader = FakeAudioRead({"V40000AU": ["0*900", "1*400", "0*900"]})
        profile = IN1808AudioProfile("IN1808")
        profile.poll_meters(reader, is_current=lambda: True)
        profile.poll_meters(reader, is_current=lambda: True)
        commands = [command for command, _safe in reader.commands]
        self.assertEqual(1, commands.count("V40000*1AU"))
        self.assertEqual(False, next(safe for command, safe in reader.commands if command == "V40000*1AU"))

    def test_state_one_never_sends_redundant_enable(self):
        reader = FakeAudioRead()
        IN1808AudioProfile("IN1808 IPCP SA").poll_meters(reader, is_current=lambda: True)
        self.assertFalse(any("*1AU" in command for command, _safe in reader.commands))

    def test_profile_can_generate_neither_dmp_two_nor_cleanup_zero(self):
        reader = FakeAudioRead({"V30000AU": ["0*900", "1*500"]})
        profile = IN1808AudioProfile("IN1808")
        profile.poll_meters(reader, is_current=lambda: True)
        before = tuple(reader.commands)
        profile.cleanup_subcontext()
        self.assertEqual(before, tuple(reader.commands))
        self.assertFalse(any("*2AU" in command or "*0AU" in command for command, _safe in reader.commands))

    def test_ambiguous_enable_is_not_replayed_and_reconciles_once_when_current(self):
        calls = {"enable": 0}

        def ambiguous(_command, _kwargs):
            calls["enable"] += 1
            raise CommandOutcomeUnknownError("possible send")

        reader = FakeAudioRead({"V30000AU": ["0*900", "1*350"], "V30000*1AU": ambiguous})
        group = IN1808AudioProfile("IN1808").poll_meters(reader, is_current=lambda: True)["input_meters"][0]
        self.assertEqual(1, calls["enable"])
        self.assertEqual(-35.0, group["components"][0]["dbfs"])

    def test_ambiguous_enable_does_not_reconcile_after_currentness_loss(self):
        current = [True]

        def ambiguous(_command, _kwargs):
            current[0] = False
            raise CommandOutcomeUnknownError("possible send")

        reader = FakeAudioRead({"V30000AU": "0*900", "V30000*1AU": ambiguous})
        group = IN1808AudioProfile("IN1808").poll_meters(reader, is_current=lambda: current[0])["input_meters"][0]
        commands = [command for command, _safe in reader.commands]
        self.assertEqual(1, commands.count("V30000AU"))
        self.assertEqual("AMBIGUOUS_ENABLE", group["components"][0]["outcome"])

    def test_program_source_maps_one_through_nine_and_fails_closed(self):
        expected = ("DP 1", "HDMI 2", "HDMI 3", "HDMI 4", "HDMI 5", "HDMI 6", "TP 7", "TP 8", "Aux In")
        self.assertEqual(expected, tuple(parse_program_source(str(value))["label"] for value in range(1, 10)))
        for value in ("0", "10", "E13", "bad", "", "1%\n3"):
            with self.subTest(value=value):
                self.assertEqual("UNKNOWN", parse_program_source(value)["label"])

    def test_audio_entry_reads_one_dollar_and_never_video_one_percent(self):
        reader = FakeAudioRead()
        IN1808AudioProfile("IN1808").acquire_entry_snapshot(reader, is_current=lambda: True)
        commands = [command for command, _safe in reader.commands]
        self.assertIn("1$", commands)
        self.assertNotIn("1%", commands)
        self.assertNotIn("1!", commands)

    def test_mixpoint_formula_and_bounds_are_exact(self):
        self.assertEqual(20000, mixpoint_oid(0, 0))
        self.assertEqual(20711, mixpoint_oid(7, 11))
        self.assertEqual("M20711AU", mixpoint_read_command(7, 11))
        for row, column in ((-1, 0), (8, 0), (0, -1), (0, 12)):
            with self.subTest(row=row, column=column), self.assertRaises(ValueError):
                mixpoint_oid(row, column)

    def test_mixpoint_normalization_is_three_state(self):
        self.assertEqual("ACTIVE", parse_mixpoint_response("0"))
        self.assertEqual("INACTIVE", parse_mixpoint_response("1"))
        for value in ("2", "E13", "", "0\n1"):
            self.assertEqual("UNKNOWN", parse_mixpoint_response(value))

    def test_routing_snapshot_preserves_mapping_basis_and_is_read_only(self):
        reader = FakeAudioRead()
        snapshot = IN1808AudioProfile("IN1808 IPCP MA 70").acquire_entry_snapshot(reader, is_current=lambda: True)
        routing = snapshot["routing"]
        self.assertEqual(IN1808_PRODSP_PROFILE_MAPPING, routing["mapping_basis"])
        self.assertEqual(8 * 11, len(routing["cells"]))
        commands = [command for command, _safe in reader.commands]
        self.assertFalse(any(re.fullmatch(r"M\d+\*.*", command) for command in commands))

    def test_routing_is_entry_snapshot_not_part_of_meter_cycle(self):
        reader = FakeAudioRead()
        profile = IN1808AudioProfile("IN1808")
        profile.acquire_entry_snapshot(reader, is_current=lambda: True)
        entry_route_reads = sum(command.startswith("M") for command, _safe in reader.commands)
        reader.commands.clear()
        profile.poll_meters(reader, is_current=lambda: True)
        self.assertEqual(80, entry_route_reads)
        self.assertFalse(any(command.startswith("M") for command, _safe in reader.commands))

    def test_unknown_identity_cannot_construct_audio_profile(self):
        with self.assertRaises(ProtocolError):
            IN1808AudioProfile("IN1808 UNKNOWN")


class RecordingIN1808(ExtronMatrixHandler):
    def __init__(self, identity):
        super().__init__("192.0.2.20", expected_model="Extron IN1808")
        self.identity = identity
        self.commands = []

    def send_command(self, command, data=None, **kwargs):
        self.commands.append((command, kwargs.get("replay_safe", True)))
        response = self.identity if command == "1I" else "1.0" if command == "Q" else "20Stat*42" if command == "w20STAT" else ""
        return {"success": True, "response": response}


class IN1808IdentityAndCapabilityTests(unittest.TestCase):
    def test_handler_preserves_wire_identity_without_relabeling_model(self):
        handler = RecordingIN1808("IN1808 IPCP Q SA")
        info = handler.get_device_info()
        self.assertEqual("IN1808", info["model"])
        self.assertEqual("IN1808 IPCP Q SA", info["wire_identity"])

    def test_parser_preserves_wire_identity_as_variant_evidence(self):
        caps = resolve_matrix_capabilities("IN1808")
        parsed = ExtronMatrixDataParser.parse({
            "capabilities": caps,
            "device_info": {"model": "IN1808", "wire_identity": "IN1808 IPCP MA 70"},
            "routes": {1: 2},
        })
        self.assertEqual("IN1808", parsed["model"])
        self.assertEqual("IN1808 IPCP MA 70", parsed["wire_identity"])

    def test_non_in1808_handler_has_no_audio_profile(self):
        handler = ExtronMatrixHandler("192.0.2.30", expected_model="Extron IN1804")
        handler.model = "IN1804"
        handler.capabilities = resolve_matrix_capabilities("IN1804")
        handler.wire_identity = "IN1804"
        with self.assertRaises(ProtocolError):
            handler.get_in1808_audio_meter_snapshot()

    def test_production_handler_adds_web_sis_prefix_once(self):
        handler = RecordingIN1808("IN1808")
        handler.model = "IN1808"
        handler.capabilities = resolve_matrix_capabilities("IN1808")
        handler.wire_identity = "IN1808"
        handler._read_in1808_audio("WI1ANAM")
        handler._read_in1808_audio("V30000AU")
        handler._read_in1808_audio("M20000AU")
        self.assertEqual(
            ["WI1ANAM", "WV30000AU", "WM20000AU"],
            [command for command, _safe in handler.commands],
        )

    def test_dispatch_capability_is_exact_application_owned(self):
        from gui.diagnostic_dispatch import dispatch_entry_for_model

        self.assertTrue(dispatch_entry_for_model("Extron IN1808").in1808_audio_capability)
        for model in (
            "Extron IN1804", "Extron IN1806", "Extron IN1608 xi",
            "Extron DTP CrossPoint 84", "Extron DMP 64 Plus", "Biamp Tesira Forte CI",
        ):
            with self.subTest(model=model):
                self.assertFalse(dispatch_entry_for_model(model).in1808_audio_capability)


try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QTableWidget
except ImportError:
    QApplication = None


class CapturingPool:
    def __init__(self):
        self.runnables = []

    def start(self, runnable):
        self.runnables.append(runnable)


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class IN1808AudioControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_controller(self):
        from gui.matrix_controller import MatrixController

        pool = CapturingPool()
        state = {"model": "Extron IN1808", "ip": "192.0.2.50"}
        controller = MatrixController(
            context_provider=lambda: (state["model"], state["ip"]),
            credential_candidates_provider=lambda _model, _ip: ({"username": "u", "password": "p"},),
            credential_index_provider=lambda *_args: 0,
            credential_advance_provider=lambda *_args: None,
            credential_revision_provider=lambda: 1,
            thread_pool=pool,
        )
        return controller, state, pool

    def test_audio_request_is_exact_model_gated_and_only_queues_background_work(self):
        controller, state, pool = self.make_controller()
        context = controller.request_in1808_audio_entry()
        self.assertEqual("audio_entry", context.operation_kind)
        self.assertEqual(1, len(pool.runnables))
        state["model"] = "Extron IN1806"
        controller.cancel_in1808_audio_subcontext()
        self.assertFalse(controller.request_in1808_audio_entry())

    def test_only_one_audio_cycle_can_be_outstanding(self):
        controller, _state, pool = self.make_controller()
        self.assertTrue(controller.request_in1808_audio_entry())
        self.assertFalse(controller.request_in1808_audio_meters())
        self.assertEqual(1, len(pool.runnables))

    def test_cancel_rejects_stale_publication_but_reports_quiescence(self):
        controller, _state, _pool = self.make_controller()
        accepted, finished = [], []
        controller.audioResultAccepted.connect(lambda data, _handle: accepted.append(data))
        controller.audioFinished.connect(lambda handle: finished.append(handle.matrix_context.operation_kind))
        context = controller.request_in1808_audio_entry()
        controller.cancel_in1808_audio_subcontext()
        controller._on_result(context, {"program_source": {"label": "DP 1"}})
        controller._on_finished(context)
        self.assertEqual([], accepted)
        self.assertEqual(["audio_entry"], finished)

    def test_audio_operation_reuses_acquired_handler_and_has_no_gui_thread_io(self):
        controller, _state, pool = self.make_controller()
        context = controller.request_in1808_audio_entry()

        class Handler:
            def __init__(self):
                self.calls = 0

            def get_in1808_audio_entry_snapshot(self, *, is_current):
                self.calls += 1
                self.assert_current = is_current()
                return {"mapping_basis": IN1808_PRODSP_PROFILE_MAPPING}

        handler = Handler()
        controller._acquire_session = lambda *_args, **_kwargs: handler
        accepted = []
        controller.audioResultAccepted.connect(lambda data, _handle: accepted.append(data))
        self.assertEqual(0, handler.calls)
        pool.runnables.pop().run()
        self.app.processEvents()
        self.assertEqual(1, handler.calls)
        self.assertTrue(handler.assert_current)
        self.assertEqual(IN1808_PRODSP_PROFILE_MAPPING, accepted[0]["mapping_basis"])


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class IN1808AudioRoomPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def make_session(*, model="Extron IN1808", audio=True):
        from core.room_diagnostic_tree import (
            DeviceRowState,
            DeviceRowStatus,
            RoomCycleStatus,
            RoomDiagnosticSession,
            RoomDiagnosticSessionIdentity,
        )
        from gui.diagnostic_dispatch import dispatch_entry_for_model

        entry = dispatch_entry_for_model(model)
        row = DeviceRowState(
            record_id="RID-1",
            diagnostic_model=model,
            ip_address="192.0.2.60",
            source_model=model,
            status=DeviceRowStatus.CONNECTED,
            capability=entry.room_capability(),
            accepted_snapshot={
                "model": model.removeprefix("Extron "),
                "firmware": "1.0",
                "temperature": 42,
                "inputs_num": 8,
                "available_input_ids": list(range(1, 9)),
                "available_output_ids": [1],
                "routes": {1: 1},
            },
            serial_number="SERIAL",
            mac_address="aa:bb:cc:dd:ee:ff",
            network_actions_enabled=True,
        )
        if audio:
            row.matrix_view_mode = "audio"
            row.matrix_audio_snapshot = {
                "mapping_basis": IN1808_PRODSP_PROFILE_MAPPING,
                "program_source": {"label": "HDMI 3", "outcome": "VALID"},
                "input_meters": [{
                    "label": "DP 1", "display_dbfs": -20.0, "normalized": 0.5,
                    "available": True, "outcome": "PARTIAL",
                }],
                "output_meters": [{
                    "label": "HDMI 1A", "display_dbfs": None, "normalized": None,
                    "available": False, "outcome": "UNAVAILABLE",
                }],
                "routing": {
                    "mapping_basis": IN1808_PRODSP_PROFILE_MAPPING,
                    "rows": ("Program L", "Program R"),
                    "columns": ("HDMI L", "HDMI R"),
                    "cells": [
                        {"row": 0, "column": 0, "state": "ACTIVE"},
                        {"row": 0, "column": 1, "state": "INACTIVE"},
                        {"row": 1, "column": 0, "state": "UNKNOWN"},
                        {"row": 1, "column": 1, "state": "ACTIVE"},
                    ],
                },
            }
        identity = RoomDiagnosticSessionIdentity("SNAP", 1, row.ip_address, row.record_id, "ROOM")
        return RoomDiagnosticSession(
            identity=identity,
            room_name="Room",
            room_address="Address",
            room_vip=False,
            rows=[row],
            status=RoomCycleStatus.COMPLETE,
            expanded_record_id=row.record_id,
        ), row

    def make_live_window(self, *, audio=False):
        from core.room_interaction import RoomInteractionKind
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        session, row = self.make_session(audio=audio)
        window.room_diagnostic_session = session
        window.room_interaction_coordinator.bind_session(session)
        context = window.room_interaction_coordinator._new_context(
            row, RoomInteractionKind.LIVE
        )
        window.room_interaction_coordinator._active = context
        controller = Mock()
        window._room_matrix_live[context] = controller
        return window, session, row, context, controller

    def test_exact_in1808_header_has_audio_video_toggle(self):
        from gui.room_diagnostic_tree import RoomDiagnosticTreeWidget

        session, _row = self.make_session(audio=False)
        widget = RoomDiagnosticTreeWidget()
        widget.render(session)
        button = widget.findChild(QPushButton, "roomMatrixAudioModeButton")
        self.assertIsNotNone(button)
        self.assertEqual("Аудио", button.text())
        emitted = []
        widget.matrixModeRequested.connect(lambda record_id, mode: emitted.append((record_id, mode)))
        button.click()
        self.assertEqual([("RID-1", "audio")], emitted)

    def test_other_matrix_header_has_no_audio_toggle(self):
        from gui.room_diagnostic_tree import RoomDiagnosticTreeWidget

        session, _row = self.make_session(model="Extron IN1806", audio=False)
        widget = RoomDiagnosticTreeWidget()
        widget.render(session)
        self.assertIsNone(widget.findChild(QPushButton, "roomMatrixAudioModeButton"))

    def test_audio_mode_preserves_general_information_and_swaps_only_right_tile(self):
        from gui.room_diagnostic_tree import RoomDiagnosticTreeWidget

        session, _row = self.make_session()
        widget = RoomDiagnosticTreeWidget()
        widget.render(session)
        self.assertEqual("IN1808", widget.findChild(QLabel, "roomMatrixModelValue").text())
        self.assertEqual("SERIAL", widget.findChild(QLabel, "roomMatrixSerialValue").text())
        self.assertIsNotNone(widget.findChild(QLabel, "roomIN1808ProgramSource"))
        self.assertIsNone(widget.findChild(QTableWidget, "roomMatrixRouting"))

    def test_audio_grid_is_noninteractive_and_has_non_color_states_and_basis(self):
        from gui.room_diagnostic_tree import RoomDiagnosticTreeWidget

        session, _row = self.make_session()
        widget = RoomDiagnosticTreeWidget()
        widget.render(session)
        table = widget.findChild(QTableWidget, "roomIN1808Routing")
        self.assertEqual(QTableWidget.NoEditTriggers, table.editTriggers())
        self.assertEqual(QTableWidget.NoSelection, table.selectionMode())
        self.assertEqual(
            {"● ACTIVE", "○ INACTIVE", "? UNKNOWN"},
            {table.item(row, column).text() for row in range(2) for column in range(2)},
        )
        self.assertEqual("Карта каналов: профиль IN1808", widget.findChild(QLabel, "roomIN1808MappingBasis").text())

    def test_meter_uses_twenty_segments_and_unavailable_is_not_zero_dbfs(self):
        from gui.room_diagnostic_tree import RoomDiagnosticTreeWidget

        session, _row = self.make_session()
        widget = RoomDiagnosticTreeWidget()
        widget.render(session)
        segments = widget.findChildren(QFrame, "roomAudioDspMeterSegment")
        self.assertEqual(40, len(segments))
        values = [label.text() for label in widget.findChildren(QLabel, "roomIN1808MeterDbfs")]
        self.assertIn("-20.0 dBFS", values)
        self.assertIn("— dBFS", values)
        self.assertNotIn("0 dBFS", values)

    def test_audio_error_does_not_replace_general_or_video_snapshot(self):
        from gui.room_diagnostic_tree import RoomDiagnosticTreeWidget

        session, row = self.make_session()
        original_video = dict(row.accepted_snapshot)
        row.matrix_audio_snapshot = None
        row.matrix_audio_error = "Аудио: нет подтверждённых данных"
        widget = RoomDiagnosticTreeWidget()
        widget.render(session)
        self.assertEqual(original_video, row.accepted_snapshot)
        self.assertEqual("IN1808", widget.findChild(QLabel, "roomMatrixModelValue").text())
        self.assertEqual("Аудио: нет подтверждённых данных", widget.findChild(QLabel, "roomIN1808AudioError").text())


    def test_video_route_ui_stays_locked_until_audio_is_quiescent(self):
        from gui.room_diagnostic_tree import RoomReadOnlyPresentation

        _session, row = self.make_session(audio=False)
        row.matrix_audio_quiescent = False
        row.network_actions_enabled = False
        requested = []
        presentation = RoomReadOnlyPresentation(
            row,
            request_matrix_route=lambda output, input_id: requested.append((output, input_id)),
            live_here=True,
        )
        table = presentation.findChild(QTableWidget, "roomMatrixRouting")
        table.cellClicked.emit(1, 4)
        self.assertEqual([], requested)

        row.matrix_audio_quiescent = True
        row.network_actions_enabled = True
        presentation = RoomReadOnlyPresentation(
            row,
            request_matrix_route=lambda output, input_id: requested.append((output, input_id)),
            live_here=True,
        )
        table = presentation.findChild(QTableWidget, "roomMatrixRouting")
        table.cellClicked.emit(1, 4)
        self.assertEqual([(1, 2)], requested)

    def test_video_mode_acceptance_does_not_start_audio_polling(self):
        window, _session, _row, context, controller = self.make_live_window(audio=False)
        window._accept_room_model_live_success = Mock(return_value=True)
        self.assertTrue(window._accept_room_matrix_result(context, {"model": "IN1808"}))
        self.app.processEvents()
        controller.request_in1808_audio_entry.assert_not_called()
        controller.request_in1808_audio_meters.assert_not_called()

    def test_audio_to_video_waits_for_worker_quiescence(self):
        window, _session, row, context, controller = self.make_live_window(audio=True)
        row.matrix_audio_generation = 4
        window._room_matrix_audio_inflight.add(context)
        controller.cancel_in1808_audio_subcontext.return_value = True

        window._on_room_matrix_mode_requested(row.record_id, "video")

        controller.cancel_in1808_audio_subcontext.assert_called_once_with()
        self.assertFalse(row.matrix_audio_quiescent)
        self.assertFalse(row.network_actions_enabled)

        handle = SimpleNamespace(matrix_context=SimpleNamespace(operation_id=91))
        window._finish_room_matrix_audio_operation(context, handle)
        self.assertTrue(row.matrix_audio_quiescent)
        self.assertTrue(row.network_actions_enabled)

    def test_stale_audio_callback_cannot_replace_current_audio_evidence(self):
        window, _session, row, context, _controller = self.make_live_window(audio=True)
        row.matrix_audio_generation = 8
        row.matrix_audio_snapshot = {"program_source": {"label": "DP 1"}}
        operation = SimpleNamespace(operation_id=92)
        window._room_matrix_audio_requests[(context, 92)] = (7, "audio_entry")

        window._accept_room_matrix_audio_result(
            context,
            {"program_source": {"label": "HDMI 2"}},
            SimpleNamespace(matrix_context=operation),
        )

        self.assertEqual("DP 1", row.matrix_audio_snapshot["program_source"]["label"])


if __name__ == "__main__":
    unittest.main()
