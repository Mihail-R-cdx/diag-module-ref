import copy
import os
import re
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

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
        handler._read_in1808_audio("1$")
        handler._read_in1808_audio("WI1ANAM")
        handler._read_in1808_audio("V30000AU")
        handler._read_in1808_audio("M20000AU")
        self.assertEqual(
            ["1$", "WI1ANAM", "WV30000AU", "WM20000AU"],
            [command for command, _safe in handler.commands],
        )

    def test_production_meter_snapshot_uses_one_read_only_batch(self):
        handler = RecordingIN1808("IN1808")
        handler.model = "IN1808"
        handler.capabilities = resolve_matrix_capabilities("IN1808")
        handler.wire_identity = "IN1808"
        handler.send_command = Mock(return_value={
            "success": True,
            "response": "\n".join("1*500" for _ in range(34)),
        })

        snapshot = handler.get_in1808_audio_meter_snapshot(is_current=lambda: True)

        handler.send_command.assert_called_once()
        wire_batch = handler.send_command.call_args.args[0]
        self.assertEqual(34, len(wire_batch.split("\r")))
        self.assertTrue(all(command.startswith("WV") for command in wire_batch.split("\r")))
        self.assertEqual(14, len(snapshot["input_meters"]))
        self.assertEqual(7, len(snapshot["output_meters"]))

    def test_production_audio_entry_batches_each_read_only_family(self):
        handler = RecordingIN1808("IN1808")
        handler.model = "IN1808"
        handler.capabilities = resolve_matrix_capabilities("IN1808")
        handler.wire_identity = "IN1808"

        def response_for_batch(command, **_kwargs):
            commands = command.split("\r")
            if commands == ["1$"]:
                payloads = ["3"]
            elif all(re.fullmatch(r"WI\d+ANAM", item) for item in commands):
                payloads = [f"Input {index}" for index in range(1, len(commands) + 1)]
            elif all(re.fullmatch(r"WO\d+ANAM", item) for item in commands):
                payloads = [f"Output {index}" for index in range(1, len(commands) + 1)]
            elif all(re.fullmatch(r"WM\d+AU", item) for item in commands):
                payloads = ["0"] * len(commands)
            else:
                self.assertTrue(all(re.fullmatch(r"WV\d+AU", item) for item in commands))
                payloads = ["1*500"] * len(commands)
            return {"success": True, "response": "\n".join(payloads)}

        handler.send_command = Mock(side_effect=response_for_batch)

        snapshot = handler.get_in1808_audio_entry_snapshot(is_current=lambda: True)

        batch_sizes = [len(call.args[0].split("\r")) for call in handler.send_command.call_args_list]
        self.assertEqual([15, 7, 1, 80, 34], batch_sizes)
        self.assertEqual("HDMI 3", snapshot["program_source"]["label"])
        self.assertEqual(80, len(snapshot["routing"]["cells"]))

    def test_production_inactive_meters_use_bounded_enable_and_read_batches(self):
        handler = RecordingIN1808("IN1808")
        handler.model = "IN1808"
        handler.capabilities = resolve_matrix_capabilities("IN1808")
        handler.wire_identity = "IN1808"
        handler.send_command = Mock(side_effect=(
            {"success": True, "response": "\n".join("0*900" for _ in range(34))},
            {"success": True, "response": "\n".join(
                f"DsV{oid}*1" for oid in (
                    list(range(30000, 30018))
                    + list(range(40000, 40006))
                    + list(range(60000, 60010))
                )
            )},
            {"success": True, "response": "\n".join("1*400" for _ in range(34))},
        ))

        snapshot = handler.get_in1808_audio_meter_snapshot(is_current=lambda: True)

        self.assertEqual(3, handler.send_command.call_count)
        self.assertFalse(handler.send_command.call_args_list[1].kwargs["replay_safe"])
        sent = "\n".join(call.args[0] for call in handler.send_command.call_args_list)
        self.assertNotIn("*2AU", sent)
        self.assertNotIn("*0AU", sent)
        self.assertTrue(all(meter["available"] for meter in snapshot["input_meters"]))

    def test_batch_correlates_echoes_and_fails_closed_on_incomplete_cardinality(self):
        handler = RecordingIN1808("IN1808")
        commands = ("V30000AU", "V30001AU")
        handler.send_command = Mock(return_value={
            "success": True,
            "response": "WV30000AU\n1*400\nWV30001AU\n1*500",
        })
        results = handler._read_in1808_audio_batch(commands)
        self.assertEqual(["1*400", "1*500"], [item["response"] for item in results])

        handler.send_command = Mock(return_value={"success": True, "response": "1*400"})
        results = handler._read_in1808_audio_batch(commands)
        self.assertEqual([False, False], [item["success"] for item in results])
        with self.assertRaises(CommandOutcomeUnknownError):
            handler._read_in1808_audio_batch(
                ("V30000*1AU", "V30001*1AU"), replay_safe=False
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
    from PyQt5.QtWidgets import QApplication, QFrame, QGridLayout, QLabel, QPushButton, QTableWidget, QWidget
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
    def make_session(*, model="Extron IN1808", audio=True, wire_identity="IN1808"):
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
                "wire_identity": wire_identity,
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
            raw_rows = (
                "Program L", "Program R", "Mic/Line 1", "Mic/Line 2",
                "Line In 3", "Line In 4", "File Player L", "File Player R",
            )
            raw_columns = routing_columns(wire_identity)
            route_cells = [
                {
                    "row": raw_row,
                    "column": raw_column,
                    "state": (
                        "ACTIVE"
                        if (raw_row, raw_column) in {(0, 0), (1, 1)}
                        else "INACTIVE"
                    ),
                }
                for raw_row in range(8)
                for raw_column in range(len(raw_columns))
            ]
            row.matrix_audio_snapshot = {
                "wire_identity": wire_identity,
                "variant": variant_for_identity(wire_identity),
                "mapping_basis": IN1808_PRODSP_PROFILE_MAPPING,
                "program_source": {"input_id": 3, "label": "HDMI 3", "outcome": "VALID"},
                "input_names": {
                    3: {"id": 3, "value": "Lectern HDMI", "outcome": "VALID"},
                    10: {"id": 10, "value": "Table Mic", "outcome": "VALID"},
                    14: {"id": 14, "value": "Left Feed", "outcome": "VALID"},
                    15: {"id": 15, "value": "Right Feed", "outcome": "VALID"},
                },
                "output_names": {
                    1: {"id": 1, "value": "Main HDMI", "outcome": "VALID"},
                },
                "input_meters": [{
                    "key": "hdmi_3", "fallback_label": "HDMI 3",
                    "display_dbfs": -20.0, "normalized": 0.5,
                    "available": True, "outcome": "VALID",
                    "components": (
                        {"channel": "L", "oid": 30004, "dbfs": -20.0, "available": True},
                        {"channel": "R", "oid": 30005, "dbfs": -28.0, "available": True},
                    ),
                }],
                "output_meters": [{
                    "key": "hdmi_1a", "fallback_label": "HDMI 1A",
                    "display_dbfs": None, "normalized": None,
                    "available": False, "outcome": "UNAVAILABLE",
                }],
                "routing": {
                    "mapping_basis": IN1808_PRODSP_PROFILE_MAPPING,
                    "rows": raw_rows,
                    "columns": raw_columns,
                    "cells": route_cells,
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

    def test_first_audio_click_renders_complete_neutral_grid_before_controller_exists(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        session, row = self.make_session(audio=False)
        window.room_diagnostic_session = session
        window.room_interaction_coordinator.bind_session(session)

        window._on_room_matrix_mode_requested(row.record_id, "audio")

        self.assertEqual("audio", row.matrix_view_mode)
        self.assertIsNone(row.matrix_audio_snapshot)
        self.assertEqual(
            "Видео",
            window.room_diagnostic_tree.findChild(QPushButton, "roomMatrixAudioModeButton").text(),
        )
        self.assertIsNotNone(window.room_diagnostic_tree.findChild(QWidget, "roomIN1808SharedGridSurface"))
        self.assertEqual(6, len(window.room_diagnostic_tree.findChildren(QLabel, "roomIN1808InputHeader")))
        self.assertEqual(7, len(window.room_diagnostic_tree.findChildren(QLabel, "roomIN1808OutputHeader")))

    def test_first_audio_click_stays_visible_while_serialized_controller_is_busy(self):
        window, _session, row, context, controller = self.make_live_window(audio=False)
        controller.request_in1808_audio_entry.return_value = False
        window._schedule_room_matrix_audio_operation = Mock()

        window._on_room_matrix_mode_requested(row.record_id, "audio")
        self.app.processEvents()

        self.assertEqual("audio", row.matrix_view_mode)
        self.assertEqual(
            "Видео",
            window.room_diagnostic_tree.findChild(QPushButton, "roomMatrixAudioModeButton").text(),
        )
        self.assertIsNotNone(window.room_diagnostic_tree.findChild(QWidget, "roomIN1808SharedGridSurface"))
        window._schedule_room_matrix_audio_operation.assert_called_once_with(
            context, "audio_entry", interval_ms=100
        )

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

    def test_audio_grid_is_marker_only_read_only_and_discloses_mapping_basis(self):
        from gui.room_diagnostic_tree import RoomDiagnosticTreeWidget

        session, _row = self.make_session()
        widget = RoomDiagnosticTreeWidget()
        widget.render(session)
        self.assertIsNone(widget.findChild(QTableWidget, "roomIN1808Routing"))
        cells = widget.findChildren(QLabel, "roomIN1808RouteCell")
        self.assertEqual(6 * 7, len(cells))
        self.assertTrue({cell.text() for cell in cells} <= {"●", "○", "◐", "—"})
        self.assertEqual("FULL", cells[0].property("routeOutcome"))
        visible_text = " ".join(label.text() for label in widget.findChildren(QLabel))
        for forbidden in ("ACTIVE", "INACTIVE", "MIXED", "VALID", "INVALID"):
            self.assertNotIn(forbidden, visible_text)
        self.assertIn("Program L → HDMI L: ACTIVE", cells[0].toolTip())
        self.assertEqual("Карта каналов: профиль IN1808", widget.findChild(QLabel, "roomIN1808MappingBasis").text())

    def test_shared_grid_owns_meter_and_route_alignment(self):
        from gui.room_diagnostic_tree import RoomDiagnosticTreeWidget

        session, _row = self.make_session()
        widget = RoomDiagnosticTreeWidget()
        widget.render(session)
        surface = widget.findChild(QWidget, "roomIN1808SharedGridSurface")
        grid = surface.layout()
        self.assertIsInstance(grid, QGridLayout)
        self.assertEqual("roomIN1808SharedGrid", grid.objectName())
        spacer = widget.findChild(QWidget, "roomIN1808TopLeftSpacer")
        self.assertEqual((0, 0, 2, 2), grid.getItemPosition(grid.indexOf(spacer)))

        input_header = widget.findChildren(QLabel, "roomIN1808InputHeader")[0]
        input_meter = next(
            meter for meter in widget.findChildren(QFrame, "roomIN1808LogicalMeter")
            if meter.property("meterOrientation") == "horizontal" and meter.property("logicalRow") == 0
        )
        first_cell = next(
            cell for cell in widget.findChildren(QLabel, "roomIN1808RouteCell")
            if cell.property("logicalRow") == 0 and cell.property("logicalColumn") == 0
        )
        self.assertEqual(grid.getItemPosition(grid.indexOf(input_header))[0], grid.getItemPosition(grid.indexOf(input_meter))[0])
        self.assertEqual(grid.getItemPosition(grid.indexOf(input_header))[0], grid.getItemPosition(grid.indexOf(first_cell))[0])

        output_header = widget.findChildren(QLabel, "roomIN1808OutputHeader")[0]
        output_meter = next(
            meter for meter in widget.findChildren(QFrame, "roomIN1808LogicalMeter")
            if meter.property("meterOrientation") == "vertical" and meter.property("logicalColumn") == 0
        )
        self.assertEqual(grid.getItemPosition(grid.indexOf(output_header))[1], grid.getItemPosition(grid.indexOf(output_meter))[1])
        self.assertEqual(grid.getItemPosition(grid.indexOf(output_header))[1], grid.getItemPosition(grid.indexOf(first_cell))[1])

    def test_logical_meters_use_twenty_segments_orientations_and_no_duplicate_labels(self):
        from gui.room_diagnostic_tree import RoomDiagnosticTreeWidget

        session, _row = self.make_session()
        widget = RoomDiagnosticTreeWidget()
        widget.render(session)
        meters = widget.findChildren(QFrame, "roomIN1808LogicalMeter")
        self.assertEqual(13, len(meters))
        self.assertEqual(6, sum(meter.property("meterOrientation") == "horizontal" for meter in meters))
        self.assertEqual(7, sum(meter.property("meterOrientation") == "vertical" for meter in meters))
        segments = widget.findChildren(QFrame, "roomAudioDspMeterSegment")
        self.assertEqual(13 * 20, len(segments))
        values = [label.text() for label in widget.findChildren(QLabel, "roomIN1808MeterDbfs")]
        self.assertIn("-20.0 dBFS", values)
        self.assertIn("— dBFS", values)
        self.assertNotIn("0 dBFS", values)
        self.assertEqual([], widget.findChildren(QLabel, "roomIN1808MeterLabel"))
        self.assertEqual([], widget.findChildren(QLabel, "roomIN1808MeterOutcome"))

    def test_program_meter_uses_one_dollar_source_and_names_remain_secondary(self):
        from gui.room_diagnostic_tree import RoomDiagnosticTreeWidget

        session, row = self.make_session()
        original_snapshot = copy.deepcopy(row.matrix_audio_snapshot)
        widget = RoomDiagnosticTreeWidget()
        widget.render(session)
        program_header = next(
            header for header in widget.findChildren(QLabel, "roomIN1808InputHeader")
            if header.text() == "Program L/R"
        )
        program_meter = next(
            meter for meter in widget.findChildren(QFrame, "roomIN1808LogicalMeter")
            if meter.property("structuralLabel") == "Program L/R"
        )
        mic_header = next(
            header for header in widget.findChildren(QLabel, "roomIN1808InputHeader")
            if header.text() == "Mic/Line 1"
        )
        file_header = next(
            header for header in widget.findChildren(QLabel, "roomIN1808InputHeader")
            if header.text() == "File Player L/R"
        )
        self.assertIn("источник: HDMI 3", program_header.toolTip())
        self.assertIn("ANAM: Lectern HDMI", program_header.toolTip())
        self.assertIn("-20.0 dBFS", [label.text() for label in program_meter.findChildren(QLabel, "roomIN1808MeterDbfs")])
        self.assertEqual("Mic/Line 1", mic_header.text())
        self.assertIn("ANAM: Table Mic", mic_header.toolTip())
        self.assertIn("ANAM: L: Left Feed; R: Right Feed", file_header.toolTip())
        self.assertEqual(original_snapshot, row.matrix_audio_snapshot)

    def test_program_unknown_never_uses_video_route_as_meter_fallback(self):
        from gui.room_diagnostic_tree import RoomDiagnosticTreeWidget

        session, row = self.make_session()
        row.matrix_audio_snapshot["program_source"] = {"input_id": None, "label": "UNKNOWN", "outcome": "UNKNOWN"}
        row.accepted_snapshot["routes"] = {1: 3}
        widget = RoomDiagnosticTreeWidget()
        widget.render(session)
        program_meter = next(
            meter for meter in widget.findChildren(QFrame, "roomIN1808LogicalMeter")
            if meter.property("structuralLabel") == "Program L/R"
        )
        self.assertEqual("— dBFS", program_meter.findChild(QLabel, "roomIN1808MeterDbfs").text())

    def test_variant_filters_amplifier_column_without_empty_base_slot(self):
        from gui.room_diagnostic_tree import RoomDiagnosticTreeWidget

        expected = (("IN1808", 7, False), ("IN1808 IPCP SA", 8, True), ("IN1808 IPCP MA 70", 8, True))
        for wire_identity, count, has_amplifier in expected:
            with self.subTest(wire_identity=wire_identity):
                session, _row = self.make_session(wire_identity=wire_identity)
                widget = RoomDiagnosticTreeWidget()
                widget.render(session)
                headers = [label.text() for label in widget.findChildren(QLabel, "roomIN1808OutputHeader")]
                self.assertEqual(count, len(headers))
                self.assertEqual(has_amplifier, "Amplifier" in headers)

    def test_route_grouping_is_topology_aware_and_preserves_raw_evidence(self):
        from gui.room_diagnostic_tree import project_in1808_logical_routes

        def outcome(row_label, column_label, states):
            cells = [
                {"row": raw_row, "column": raw_column, "state": state}
                for (raw_row, raw_column), state in states.items()
            ]
            snapshot = {"routing": {"cells": cells}}
            original = copy.deepcopy(snapshot)
            result = next(
                cell for cell in project_in1808_logical_routes(snapshot, "base")
                if cell["row_label"] == row_label and cell["column_label"] == column_label
            )
            self.assertEqual(original, snapshot)
            return result["outcome"]

        stereo_stereo = {(0, 0): "ACTIVE", (0, 1): "INACTIVE", (1, 0): "INACTIVE", (1, 1): "ACTIVE"}
        self.assertEqual("FULL", outcome("Program L/R", "HDMI 1A", stereo_stereo))
        self.assertEqual("INACTIVE", outcome("Program L/R", "HDMI 1A", {key: "INACTIVE" for key in stereo_stereo}))
        self.assertEqual("MIXED", outcome("Program L/R", "HDMI 1A", {key: "ACTIVE" if key == (0, 0) else "INACTIVE" for key in stereo_stereo}))
        self.assertEqual("MIXED", outcome("Program L/R", "HDMI 1A", {key: "ACTIVE" if key in {(0, 1), (1, 0)} else "INACTIVE" for key in stereo_stereo}))
        self.assertEqual("MIXED", outcome("Program L/R", "HDMI 1A", {key: "ACTIVE" for key in stereo_stereo}))
        self.assertEqual("UNKNOWN", outcome("Program L/R", "HDMI 1A", {**stereo_stereo, (1, 1): "UNKNOWN"}))

        self.assertEqual("FULL", outcome("Program L/R", "Line Out 1", {(0, 6): "ACTIVE", (1, 6): "ACTIVE"}))
        self.assertEqual("INACTIVE", outcome("Program L/R", "Line Out 1", {(0, 6): "INACTIVE", (1, 6): "INACTIVE"}))
        self.assertEqual("MIXED", outcome("Program L/R", "Line Out 1", {(0, 6): "ACTIVE", (1, 6): "INACTIVE"}))
        self.assertEqual("UNKNOWN", outcome("Program L/R", "Line Out 1", {(0, 6): "ACTIVE", (1, 6): "UNKNOWN"}))
        self.assertEqual("FULL", outcome("Mic/Line 1", "HDMI 1A", {(2, 0): "ACTIVE", (2, 1): "ACTIVE"}))
        self.assertEqual("INACTIVE", outcome("Mic/Line 1", "HDMI 1A", {(2, 0): "INACTIVE", (2, 1): "INACTIVE"}))
        self.assertEqual("MIXED", outcome("Mic/Line 1", "HDMI 1A", {(2, 0): "ACTIVE", (2, 1): "INACTIVE"}))
        self.assertEqual("UNKNOWN", outcome("Mic/Line 1", "HDMI 1A", {(2, 0): "ACTIVE", (2, 1): "UNKNOWN"}))
        self.assertEqual("FULL", outcome("Mic/Line 1", "Line Out 1", {(2, 6): "ACTIVE"}))
        self.assertEqual("INACTIVE", outcome("Mic/Line 1", "Line Out 1", {(2, 6): "INACTIVE"}))
        self.assertEqual("UNKNOWN", outcome("Mic/Line 1", "Line Out 1", {(2, 6): "UNKNOWN"}))

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

    def test_temporary_matrix_busy_state_retries_entry_and_meter_without_backlog(self):
        for kind in ("audio_entry", "audio_meters"):
            with self.subTest(kind=kind):
                window, _session, row, context, controller = self.make_live_window(audio=True)
                operation = SimpleNamespace(operation_id=101 if kind == "audio_entry" else 102)
                request = (
                    controller.request_in1808_audio_entry
                    if kind == "audio_entry"
                    else controller.request_in1808_audio_meters
                )
                request.side_effect = [False, operation]
                window._schedule_room_matrix_audio_operation = Mock()

                self.assertFalse(window._submit_room_matrix_audio(context, row, kind))
                window._schedule_room_matrix_audio_operation.assert_called_once_with(
                    context, kind, interval_ms=100
                )
                self.assertNotIn(context, window._room_matrix_audio_inflight)

                window._run_room_matrix_audio_operation(context, kind)
                self.assertIn(context, window._room_matrix_audio_inflight)
                self.assertEqual(
                    (row.matrix_audio_generation, kind),
                    window._room_matrix_audio_requests[(context, operation.operation_id)],
                )
                self.assertEqual(2, request.call_count)

    def test_meter_cadence_accounts_for_completed_cycle_duration(self):
        window, _session, row, context, controller = self.make_live_window(audio=True)
        operation = SimpleNamespace(operation_id=103)
        controller.request_in1808_audio_meters.return_value = operation
        window._schedule_room_matrix_audio_meter = Mock()
        handle = SimpleNamespace(matrix_context=operation)

        with patch("gui.main_window.time.monotonic", side_effect=(10.0, 10.25)):
            self.assertTrue(
                window._submit_room_matrix_audio(context, row, "audio_meters")
            )
            window._finish_room_matrix_audio_operation(context, handle)

        window._schedule_room_matrix_audio_meter.assert_called_once_with(
            context, interval_ms=750
        )


if __name__ == "__main__":
    unittest.main()
