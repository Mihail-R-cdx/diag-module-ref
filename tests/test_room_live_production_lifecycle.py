"""Production-composition regressions for exact-row model live retirement."""

from __future__ import annotations

import time
import unittest
from dataclasses import replace
from unittest.mock import Mock, patch

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication, QProgressBar

from core.equipment_inventory import EquipmentInventory, EquipmentInventoryMetadata, EquipmentRecord
from core.exceptions import CodecFailureCategory
from core.room_diagnostic_tree import DeviceRowStatus, RoomCycleStatus, build_room_session, resolve_room_source
from core.room_interaction import RoomInteractionKind
from gui.diagnostic_dispatch import dispatch_entry_for_model, room_model_capabilities
from gui.room_diagnostic_tree import RoomReadOnlyPresentation
from handlers.huawei.te40 import HuaweiTE40Handler


def _record(record_id, model, ip):
    return EquipmentRecord(record_id, model, model, ip, None, None, "R-1", "Room", "other")


def _inventory(*records):
    return EquipmentInventory.from_records(
        records,
        EquipmentInventoryMetadata(4, "sha256:" + "b" * 64),
    )


class _CloudSessionSignals(QObject):
    shutdown_finished = pyqtSignal(dict)


class _TeSessionSignals(QObject):
    result = pyqtSignal(dict)
    error = pyqtSignal(dict)
    shutdown_finished = pyqtSignal(dict)


class ControlledCloudSession:
    instances = []

    def __init__(self, _parent=None):
        self.signals = _CloudSessionSignals()
        self.activated = None
        self.invalidated = False
        self.shutdown_requested = False
        self.__class__.instances.append(self)

    def activate_context(self, model, ip, candidates, start_index, profile):
        self.activated = (model, ip, tuple(candidates), start_index, profile)
        return 17

    def invalidate_context(self):
        self.invalidated = True

    def shutdown(self, *, wait=False):
        self.shutdown_requested = True

    def finish_cleanup(self):
        self.signals.shutdown_finished.emit({"generation": 18})


class ControlledTeSession:
    instances = []

    def __init__(self, _parent=None):
        self.signals = _TeSessionSignals()
        self.activated = None
        self.submitted = []
        self.invalidated = False
        self.shutdown_requested = False
        self.__class__.instances.append(self)

    def activate_context(self, model, ip, candidates, start_index, profile):
        self.activated = (model, ip, tuple(candidates), start_index, profile)
        return 29

    def submit(self, operation, *, generation=None):
        self.submitted.append((operation, generation))
        return len(self.submitted)

    def invalidate_context(self):
        self.invalidated = True

    def shutdown(self, *, wait=False):
        self.shutdown_requested = True

    def finish_cleanup(self):
        self.signals.shutdown_finished.emit({"generation": 30})


class ControlledRejectedSubmitTeSession(ControlledTeSession):
    def submit(self, operation, *, generation=None):
        self.submitted.append((operation, generation))
        return None


class ControlledCloudMeter(QObject):
    accepted = pyqtSignal(dict, dict)
    terminal = pyqtSignal(dict)
    instances = []

    def __init__(self, _parent=None, *, session=None):
        super().__init__()
        self.session = session
        self.started = None
        self.stopped = False
        self.__class__.instances.append(self)

    def start(self, model, ip, candidates, start_index, profile, **identity):
        self.started = (model, ip, tuple(candidates), start_index, profile, identity)
        return True

    def stop(self):
        self.stopped = True


class ControlledMatrix(QObject):
    resultAccepted = pyqtSignal(dict, object)
    errorAccepted = pyqtSignal(tuple, object)
    progressAccepted = pyqtSignal(int, object)
    statusAccepted = pyqtSignal(str, object)
    terminalAccepted = pyqtSignal(str, object)
    finishedAccepted = pyqtSignal(object)
    cleanupFinished = pyqtSignal(object)
    routeAccepted = pyqtSignal(int)
    routeError = pyqtSignal(str)
    instances = []

    def __init__(self, **_kwargs):
        super().__init__()
        self.started = None
        self.shutdown_requested = False
        self.__class__.instances.append(self)

    def request_full_refresh(self, ip, candidates, candidate_index):
        self.started = (ip, tuple(candidates), candidate_index)

    def request_route(self, *_args):
        pass

    def request_status_refresh(self):
        pass

    def invalidate_context(self):
        pass

    def shutdown(self):
        self.shutdown_requested = True

    def finish_cleanup(self):
        self.cleanupFinished.emit(object())


class _DmpSignals(QObject):
    result = pyqtSignal(dict)
    error = pyqtSignal(tuple)
    finished = pyqtSignal()


class ControlledDmpWorker:
    instances = []

    def __init__(self, *, ip_address, cancellation, **credential):
        self.ip_address = ip_address
        self.cancellation = cancellation
        self.credential = credential
        self.signals = _DmpSignals()
        self.current_idx = 0
        self.device_name = ""
        self.__class__.instances.append(self)


class ControlledPool:
    instance = None

    def __init__(self):
        self.started = []

    @classmethod
    def globalInstance(cls):
        if cls.instance is None:
            cls.instance = cls()
        return cls.instance

    def start(self, worker):
        self.started.append(worker)


class RoomLiveProductionLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        ControlledCloudSession.instances.clear()
        ControlledCloudMeter.instances.clear()
        ControlledMatrix.instances.clear()
        ControlledDmpWorker.instances.clear()
        ControlledPool.instance = None

    def _window_session(self, model, *, rows=1):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        records = tuple(
            _record(chr(ord("a") + index), model, f"192.0.2.{10 + index}")
            for index in range(rows)
        )
        stock = _inventory(*records)
        session = build_room_session(
            inventory=stock,
            source=resolve_room_source(stock, records[0].ip_address, room_model_capabilities()),
            generation=41,
            capabilities=room_model_capabilities(),
        )
        session.status = RoomCycleStatus.COMPLETE
        for row in session.rows:
            row.status = DeviceRowStatus.CONNECTED
            row.accepted_snapshot = {"record": row.record_id}
        session.expanded_record_id = records[0].record_id
        window.room_diagnostic_session = session
        window.room_diagnostic_tree.render(session)
        window.room_interaction_coordinator.bind_session(session)
        # These production-owner tests exercise LIVE retirement, fallback and
        # mutation handoff after the mandatory automatic preview has already
        # completed for the current generation.  Preview admission/order is
        # asserted separately in the coordinator-focused regression tests.
        if dispatch_entry_for_model(model).screen_key == "codec":
            window.room_interaction_coordinator._codec_preview_attempts.update(
                (session.identity, row.record_id) for row in session.rows
            )
        window.device_credentials[model] = (
            {"username": "first", "password": "one"},
            {"username": "second", "password": "two"},
        )
        return window, session

    def _wait_for(self, predicate, timeout=0.5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not predicate():
            self.app.processEvents()
            time.sleep(0.002)
        self.app.processEvents()
        self.assertTrue(predicate())

    def test_cloudlink_local_refresh_waits_for_executor_handler_release(self):
        with patch("gui.main_window.InteractiveSessionController", ControlledCloudSession), patch(
            "gui.main_window.CloudLinkMicrophoneMeter", ControlledCloudMeter
        ):
            window, session = self._window_session("CloudLink Bar 310")
            window.room_diagnostic_controller.start_local_refresh = Mock()
            window.room_interaction_coordinator.cycle_finished(session)
            live = window.room_interaction_coordinator.active_context

            self.assertIsNone(window.room_interaction_coordinator.request_local_refresh())
            self.assertTrue(ControlledCloudSession.instances[0].shutdown_requested)
            window.room_diagnostic_controller.start_local_refresh.assert_not_called()

            ControlledCloudSession.instances[0].finish_cleanup()
            window.room_diagnostic_controller.start_local_refresh.assert_called_once()
            self.assertNotEqual(live, window.room_interaction_coordinator.active_context)

    def test_te_live_audio_uses_room_owned_two_second_binding_and_keeps_both_values(self):
        ControlledTeSession.instances.clear()
        with patch("gui.main_window.InteractiveSessionController", ControlledTeSession):
            window, session = self._window_session("Huawei TE20")
            window.room_interaction_coordinator.cycle_finished(session)
            live = window.room_interaction_coordinator.active_context
            owner = ControlledTeSession.instances[0]
            self.assertEqual("Huawei TE20", owner.activated[0])
            self.assertEqual("get_live_audio_status", owner.submitted[0][0].method)
            self.assertEqual(2000, window._room_te_live[live][1].interval())

            owner.signals.result.emit({
                "value": {"audio": {"MicValueIndex": 11, "SpeakerValueIndex": 22}},
                "connection_profile": {"protocol": "https", "port": 443},
            })
            self.assertEqual(
                {"microphone": 11, "speaker": 22},
                session.row_for("a").accepted_snapshot["live_audio"],
            )

            window.room_interaction_coordinator.request_auxiliary("call_log")
            self.assertTrue(owner.shutdown_requested)
            owner.finish_cleanup()
            self.assertEqual("AUXILIARY_READ", window.room_interaction_coordinator.active_context.kind.value)

    def test_te40_backed_current_audio_handler_result_reaches_room_snapshot_and_meter(self):
        for model in ("Huawei TE40", "Huawei TE50"):
            with self.subTest(model=model), patch("gui.main_window.InteractiveSessionController", ControlledTeSession):
                window, session = self._window_session(model)
                window.room_interaction_coordinator.cycle_finished(session)
                live = window.room_interaction_coordinator.active_context
                handler = HuaweiTE40Handler("192.0.2.10", username="u", password="p")
                handler.get_sleep_mode = Mock(return_value="Off")
                handler.send_command = Mock(return_value={"success": 1, "data": """
                    {"mic1ValueIndex": 37, "rcaLInValueIndex": 62,
                     "rcaRInValueIndex": 0,
                     "SpeakerValueIndex": 220}
                """})

                ControlledTeSession.instances[-1].signals.result.emit({
                    "value": handler.get_live_audio_status(),
                    "connection_profile": {"protocol": "https", "port": 443},
                })
                snapshot = session.row_for("a").accepted_snapshot
                presentation = RoomReadOnlyPresentation(session.row_for("a"))
                self.addCleanup(presentation.deleteLater)

                self.assertEqual(live, window.room_interaction_coordinator.active_context)
                self.assertEqual(62, snapshot["live_audio"]["microphone"])
                self.assertEqual(28, presentation.findChild(QProgressBar, "roomCodecMicrophoneMeter").value())

    def test_te_live_authentication_fallback_waits_for_owner_cleanup(self):
        for model in ("Huawei TE20", "Huawei TE40"):
            with self.subTest(model=model), patch("gui.main_window.InteractiveSessionController", ControlledTeSession):
                window, session = self._window_session(model)
                window.room_interaction_coordinator.cycle_finished(session)
                first = ControlledTeSession.instances[-1]
                first.signals.error.emit({"category": CodecFailureCategory.AUTHENTICATION.value})
                self.assertIs(first, ControlledTeSession.instances[-1])
                self.assertTrue(first.shutdown_requested)
                first.finish_cleanup()
                second = ControlledTeSession.instances[-1]
                self.assertEqual("second", second.activated[2][0]["username"])
                second.signals.result.emit({
                    "value": {"audio": {"MicValueIndex": 2, "SpeakerValueIndex": 3}},
                    "connection_profile": {"protocol": "https", "port": 443},
                })
                self.assertEqual(1, window.get_current_credential_index(model, "192.0.2.10"))
                self.assertEqual({"microphone": 2, "speaker": 3}, session.row_for("a").accepted_snapshot["live_audio"])

    def test_te_live_exhausted_authentication_does_not_loop_or_resurrect(self):
        with patch("gui.main_window.InteractiveSessionController", ControlledTeSession):
            window, session = self._window_session("Huawei TE20")
            window.room_interaction_coordinator.cycle_finished(session)
            first = ControlledTeSession.instances[-1]
            first.signals.error.emit({"category": CodecFailureCategory.AUTHENTICATION.value})
            first.finish_cleanup()
            second = ControlledTeSession.instances[-1]
            second.signals.error.emit({"category": CodecFailureCategory.AUTHENTICATION.value})
            self.assertTrue(second.shutdown_requested)
            owner_count = len(ControlledTeSession.instances)
            second.finish_cleanup()
            self.assertEqual(owner_count, len(ControlledTeSession.instances))
            self.assertEqual(DeviceRowStatus.DEGRADED, session.row_for("a").status)

    def test_te_live_non_auth_canonical_categories_never_advance_credentials(self):
        for category in (
            CodecFailureCategory.TRANSPORT.value,
            CodecFailureCategory.SESSION_INVALID.value,
            CodecFailureCategory.PROTOCOL.value,
            CodecFailureCategory.COMMAND.value,
        ):
            with self.subTest(category=category), patch("gui.main_window.InteractiveSessionController", ControlledTeSession):
                window, session = self._window_session("Huawei TE20")
                window.room_interaction_coordinator.cycle_finished(session)
                owner = ControlledTeSession.instances[-1]
                owner_count = len(ControlledTeSession.instances)
                owner.signals.error.emit({"category": category, "message": "authentication 401 text is not authority"})
                self.assertTrue(owner.shutdown_requested)
                owner.finish_cleanup()
                self.assertEqual(owner_count, len(ControlledTeSession.instances))
                self.assertEqual(DeviceRowStatus.DEGRADED, session.row_for("a").status)

    def test_codec_mutation_cleanup_timeout_blocks_row_and_late_callback_is_powerless(self):
        with patch("gui.main_window.InteractiveSessionController", ControlledTeSession):
            window, session = self._window_session("Huawei TE20")
            window.room_codec_mutation_cleanup_timeout_ms = 20
            row = session.row_for("a")
            context = window.room_interaction_coordinator._new_context(row, RoomInteractionKind.MUTATION)
            window.room_interaction_coordinator._active = context
            window._start_room_codec_mutation_attempt(
                context, {"operation": "speaker_volume", "target": 7},
                {"username": "first", "password": "one"}, 0,
            )
            owner = ControlledTeSession.instances[-1]
            owner.signals.result.emit({"value": 7})
            self._wait_for(lambda: window.room_interaction_coordinator.active_context is None)
            self.assertTrue(row.interaction_blocked)
            self.assertNotEqual(7, row.accepted_snapshot.get("speaker_volume"))
            owner.finish_cleanup()
            self.assertTrue(row.interaction_blocked)

    def test_codec_mutation_error_cleanup_timeout_releases_lane_without_retry(self):
        with patch("gui.main_window.InteractiveSessionController", ControlledTeSession):
            window, session = self._window_session("Huawei TE20")
            window.room_codec_mutation_cleanup_timeout_ms = 20
            row = session.row_for("a")
            context = window.room_interaction_coordinator._new_context(row, RoomInteractionKind.MUTATION)
            window.room_interaction_coordinator._active = context
            window._start_room_codec_mutation_attempt(
                context, {"operation": "speaker_volume", "target": 7},
                {"username": "first", "password": "one"}, 0,
            )
            owner = ControlledTeSession.instances[-1]
            owner_count = len(ControlledTeSession.instances)
            owner.signals.error.emit({"category": CodecFailureCategory.TRANSPORT.value, "message": "synthetic"})
            self._wait_for(lambda: window.room_interaction_coordinator.active_context is None)
            self.assertTrue(row.interaction_blocked)
            self.assertEqual(owner_count, len(ControlledTeSession.instances))

    def test_codec_mutation_submit_none_is_safe_pre_submit_failure(self):
        with patch("gui.main_window.InteractiveSessionController", ControlledRejectedSubmitTeSession):
            window, session = self._window_session("Huawei TE20")
            row = session.row_for("a")
            row.network_actions_enabled = True
            context = window.room_interaction_coordinator._new_context(row, RoomInteractionKind.MUTATION)
            window.room_interaction_coordinator._active = context
            window._start_room_codec_mutation_attempt(
                context, {"operation": "speaker_volume", "target": 7},
                {"username": "first", "password": "one"}, 0,
            )
            owner = ControlledRejectedSubmitTeSession.instances[-1]
            self.assertFalse(window._room_codec_mutations[context]["command_submitted"])
            self.assertTrue(owner.shutdown_requested)
            session.expanded_record_id = None
            window.room_interaction_coordinator._expanded_record_id = None
            owner.finish_cleanup()
            self.assertFalse(row.interaction_blocked)
            self.assertFalse(row.unconfirmed_after_command)
            self.assertFalse(row.stale)
            self.assertTrue(row.network_actions_enabled)
            self.assertNotEqual(7, row.accepted_snapshot.get("speaker_volume"))

    def test_te40_pre_submit_connection_failure_degrades_without_unconfirmed_command(self):
        with patch("gui.main_window.InteractiveSessionController", ControlledTeSession):
            window, session = self._window_session("Huawei TE40")
            row = session.row_for("a")
            context = window.room_interaction_coordinator.confirm_mutation(
                {"operation": "microphone_gain", "target": 19}
            )
            owner = ControlledTeSession.instances[-1]

            self.assertEqual("set_microphone_gain", owner.submitted[0][0].method)
            owner.signals.result.emit({"value": {
                "pre_submit_failure": True, "connection_lost": True,
            }})
            self.assertTrue(owner.shutdown_requested)
            owner.finish_cleanup()

            self.assertEqual(DeviceRowStatus.DEGRADED, row.status)
            self.assertTrue(row.interaction_blocked)
            self.assertFalse(row.unconfirmed_after_command)
            self.assertFalse(row.network_actions_enabled)
            self.assertIsNone(window.room_interaction_coordinator.active_context)
            self.assertIsNone(window.room_interaction_coordinator.confirm_mutation(
                {"operation": "microphone_gain", "target": 20}
            ))
            self.assertEqual(context.kind, RoomInteractionKind.MUTATION)

    def test_te40_ordinary_pre_submit_failure_is_safe_and_releases_lane(self):
        with patch("gui.main_window.InteractiveSessionController", ControlledTeSession):
            window, session = self._window_session("Huawei TE40")
            row = session.row_for("a")
            window.room_interaction_coordinator.confirm_mutation(
                {"operation": "microphone_gain", "target": 19}
            )
            owner = ControlledTeSession.instances[-1]

            owner.signals.error.emit({
                "category": CodecFailureCategory.PROTOCOL.value,
                "message": "fresh pre-read malformed",
            })
            owner.finish_cleanup()

            self.assertEqual(DeviceRowStatus.CONNECTED, row.status)
            self.assertFalse(row.interaction_blocked)
            self.assertFalse(row.unconfirmed_after_command)
            # Normal cleanup may immediately re-admit the already eligible
            # TE40 LIVE owner; it must not leave an unconfirmed/blocked row.
            self.assertEqual(
                RoomInteractionKind.LIVE,
                window.room_interaction_coordinator.active_context.kind,
            )

    def test_te40_post_possible_send_cancellation_blocks_and_late_success_is_powerless(self):
        with patch("gui.main_window.InteractiveSessionController", ControlledTeSession):
            window, session = self._window_session("Huawei TE40")
            row = session.row_for("a")
            context = window.room_interaction_coordinator.confirm_mutation(
                {"operation": "microphone_gain", "target": 19}
            )
            owner = ControlledTeSession.instances[-1]
            window._on_room_codec_mutation_stage(
                context, "microphone_gain", {"stage": "post_may_have_been_sent"}
            )

            window.room_interaction_coordinator.collapse("a")
            owner.finish_cleanup()
            owner.signals.result.emit({"value": {"confirmed": True, "microphone_volume": 19}})

            self.assertTrue(row.interaction_blocked)
            self.assertTrue(row.unconfirmed_after_command)
            self.assertNotEqual(19, row.accepted_snapshot.get("microphone_volume"))
            self.assertIsNone(window.room_interaction_coordinator.active_context)

    def test_te40_post_possible_send_timeout_and_failed_readback_remain_unconfirmed(self):
        with patch("gui.main_window.InteractiveSessionController", ControlledTeSession):
            window, session = self._window_session("Huawei TE40")
            window.room_codec_mutation_cleanup_timeout_ms = 20
            row = session.row_for("a")
            context = window.room_interaction_coordinator.confirm_mutation(
                {"operation": "microphone_gain", "target": 19}
            )
            owner = ControlledTeSession.instances[-1]
            window._on_room_codec_mutation_stage(
                context, "microphone_gain", {"stage": "post_may_have_been_sent"}
            )
            owner.signals.error.emit({
                "category": CodecFailureCategory.PROTOCOL.value,
                "message": "authoritative readback malformed",
            })

            self._wait_for(lambda: window.room_interaction_coordinator.active_context is None)

            self.assertTrue(row.interaction_blocked)
            self.assertTrue(row.unconfirmed_after_command)
            self.assertEqual(1, len(owner.submitted))
            owner.signals.result.emit({"value": {"confirmed": True, "microphone_volume": 19}})
            self.assertNotEqual(19, row.accepted_snapshot.get("microphone_volume"))

    def test_cancelled_codec_mutation_timeout_releases_retired_lane_and_late_callbacks_are_powerless(self):
        with patch("gui.main_window.InteractiveSessionController", ControlledTeSession):
            window, session = self._window_session("Huawei TE20")
            window.room_codec_mutation_cleanup_timeout_ms = 20
            row = session.row_for("a")
            context = window.room_interaction_coordinator._new_context(row, RoomInteractionKind.MUTATION)
            window.room_interaction_coordinator._active = context
            window._start_room_codec_mutation_attempt(
                context, {"operation": "speaker_volume", "target": 7},
                {"username": "first", "password": "one"}, 0,
            )
            owner = ControlledTeSession.instances[-1]
            window.room_interaction_coordinator.collapse("a")
            self.assertTrue(owner.invalidated)
            self.assertTrue(owner.shutdown_requested)
            self._wait_for(lambda: window.room_interaction_coordinator.active_context is None)
            self.assertNotIn(context, window._room_codec_mutations)
            self.assertNotIn(context, window._room_codec_mutation_cleanup_timers)
            self.assertNotEqual(7, row.accepted_snapshot.get("speaker_volume"))
            self.assertTrue(row.interaction_blocked)
            self.assertTrue(row.unconfirmed_after_command)
            self.assertTrue(row.stale)
            self.assertFalse(row.network_actions_enabled)
            owner.signals.result.emit({"value": 7})
            owner.signals.error.emit({"category": CodecFailureCategory.AUTHENTICATION.value})
            owner.finish_cleanup()
            self.assertNotEqual(7, row.accepted_snapshot.get("speaker_volume"))
            self.assertIsNone(window.room_interaction_coordinator.active_context)

    def test_cancelled_codec_mutation_physical_cleanup_stops_timeout_without_double_complete(self):
        with patch("gui.main_window.InteractiveSessionController", ControlledTeSession):
            window, session = self._window_session("Huawei TE20")
            window.room_codec_mutation_cleanup_timeout_ms = 20
            row = session.row_for("a")
            context = window.room_interaction_coordinator._new_context(row, RoomInteractionKind.MUTATION)
            window.room_interaction_coordinator._active = context
            window._start_room_codec_mutation_attempt(
                context, {"operation": "speaker_volume", "target": 7},
                {"username": "first", "password": "one"}, 0,
            )
            owner = ControlledTeSession.instances[-1]
            window.room_interaction_coordinator.collapse("a")
            owner.finish_cleanup()
            self.assertNotIn(context, window._room_codec_mutations)
            self.assertNotIn(context, window._room_codec_mutation_cleanup_timers)
            self.assertIsNone(window.room_interaction_coordinator.active_context)
            self.assertTrue(row.interaction_blocked)
            self.assertTrue(row.unconfirmed_after_command)
            self.assertTrue(row.stale)
            self.assertFalse(row.network_actions_enabled)
            self._wait_for(lambda: True, timeout=0.04)
            self.assertIsNone(window.room_interaction_coordinator.active_context)

    def test_top_refresh_waits_for_cloudlink_live_cleanup_before_room_replacement(self):
        with patch("gui.main_window.InteractiveSessionController", ControlledCloudSession), patch(
            "gui.main_window.CloudLinkMicrophoneMeter", ControlledCloudMeter
        ):
            window, session = self._window_session("CloudLink Bar 310")
            stock = _inventory(_record("new", "CloudLink Bar 310", "192.0.2.10"))
            window.equipment_inventory = stock
            window.ip_entry.setText("192.0.2.10")
            # Setting the target is itself a boundary; install the current
            # room authority after it to model a top Refresh on the same target.
            window.room_diagnostic_session = session
            window.room_interaction_coordinator.bind_session(session)
            window.room_interaction_coordinator._codec_preview_attempts.add(
                (session.identity, "a")
            )
            window.room_interaction_coordinator.cycle_finished(session)
            live = window.room_interaction_coordinator.active_context
            window._start_room_diagnostic_session = Mock()

            window.refresh_data()
            window.refresh_data()

            self.assertTrue(window.room_interaction_coordinator.is_retiring(live))
            self.assertTrue(ControlledCloudSession.instances[0].shutdown_requested)
            window._start_room_diagnostic_session.assert_not_called()

            ControlledCloudSession.instances[0].finish_cleanup()

            window._start_room_diagnostic_session.assert_called_once()
            self.assertIsNone(window.room_interaction_coordinator.active_context)

    def test_matrix_local_refresh_waits_for_session_owner_release(self):
        with patch("gui.main_window.MatrixController", ControlledMatrix):
            window, session = self._window_session("Extron IN1804")
            window.room_diagnostic_controller.start_local_refresh = Mock()
            window.room_interaction_coordinator.cycle_finished(session)

            self.assertIsNone(window.room_interaction_coordinator.request_local_refresh())
            self.assertTrue(ControlledMatrix.instances[-1].shutdown_requested)
            window.room_diagnostic_controller.start_local_refresh.assert_not_called()
            ControlledMatrix.instances[-1].finish_cleanup()
            window.room_diagnostic_controller.start_local_refresh.assert_called_once()

    def test_dmp_local_refresh_waits_for_worker_disconnect_and_finished(self):
        with patch("gui.main_window.ExtronDMP64PlusMeterWorker", ControlledDmpWorker), patch(
            "gui.main_window.QThreadPool", ControlledPool
        ):
            window, session = self._window_session("Extron DMP 64 Plus")
            window.room_diagnostic_controller.start_local_refresh = Mock()
            window.room_interaction_coordinator.cycle_finished(session)
            worker = ControlledDmpWorker.instances[0]

            self.assertIsNone(window.room_interaction_coordinator.request_local_refresh())
            self.assertTrue(worker.cancellation.is_cancelled())
            window.room_diagnostic_controller.start_local_refresh.assert_not_called()
            worker.signals.finished.emit()
            window.room_diagnostic_controller.start_local_refresh.assert_called_once()

    def test_rapid_a_b_c_starts_only_c_after_a_physical_cleanup(self):
        with patch("gui.main_window.InteractiveSessionController", ControlledCloudSession), patch(
            "gui.main_window.CloudLinkMicrophoneMeter", ControlledCloudMeter
        ):
            window, session = self._window_session("CloudLink Bar 310", rows=3)
            window.room_interaction_coordinator.cycle_finished(session)
            window.room_interaction_coordinator.expand("b")
            window.room_interaction_coordinator.expand("c")
            self.assertEqual(["192.0.2.10"], [owner.activated[1] for owner in ControlledCloudSession.instances])

            ControlledCloudSession.instances[0].finish_cleanup()
            self.assertEqual(
                ["192.0.2.10", "192.0.2.12"],
                [owner.activated[1] for owner in ControlledCloudSession.instances],
            )

    def test_cleanup_timeout_abandons_old_owner_and_late_success_is_powerless(self):
        with patch("gui.main_window.InteractiveSessionController", ControlledCloudSession), patch(
            "gui.main_window.CloudLinkMicrophoneMeter", ControlledCloudMeter
        ):
            window, session = self._window_session("CloudLink Bar 310", rows=2)
            window.room_live_cleanup_timeout_ms = 20
            window.room_interaction_coordinator.cycle_finished(session)
            old_meter = ControlledCloudMeter.instances[0]
            old_key = window.get_credential_key("CloudLink Bar 310", "192.0.2.10")
            window.room_interaction_coordinator.expand("b")
            self.assertEqual(1, len(ControlledCloudSession.instances))

            self._wait_for(lambda: len(ControlledCloudSession.instances) == 2)
            self.assertTrue(session.row_for("a").interaction_blocked)
            self.assertTrue(session.post_cycle_problem)
            old_meter.accepted.emit(
                {"available": True},
                {"connection_profile": {"protocol": "late"}},
            )
            self.assertNotIn(old_key, window.current_credential_index)
            self.assertIsNone(window.get_device_connection_profile("CloudLink Bar 310", "192.0.2.10"))

    def test_confirmed_mutation_waits_for_live_cleanup_and_timeout_never_sends(self):
        cloud_entry = dispatch_entry_for_model("CloudLink Bar 310")
        combined = replace(
            cloud_entry,
            mutation_binding_key="room_pdu_mutation",
            reconciliation_binding_key="room_one_shot_refresh",
        )
        with patch("gui.main_window.dispatch_entry_for_model", return_value=combined), patch(
            "gui.main_window.InteractiveSessionController", ControlledCloudSession
        ), patch("gui.main_window.CloudLinkMicrophoneMeter", ControlledCloudMeter):
            window, session = self._window_session("CloudLink Bar 310")
            window.room_diagnostic_controller.start_pdu_mutation = Mock()
            window.room_interaction_coordinator.cycle_finished(session)
            window.room_interaction_coordinator.confirm_mutation({"operation": "on"})
            window.room_diagnostic_controller.start_pdu_mutation.assert_not_called()
            ControlledCloudSession.instances[0].finish_cleanup()
            window.room_diagnostic_controller.start_pdu_mutation.assert_called_once()
            mutation = window.room_interaction_coordinator.active_context
            window.room_interaction_coordinator.complete(
                mutation,
                success=False,
                unconfirmed=True,
            )

            window2, session2 = self._window_session("CloudLink Bar 310")
            window2.room_live_cleanup_timeout_ms = 20
            window2.room_diagnostic_controller.start_pdu_mutation = Mock()
            window2.room_interaction_coordinator.cycle_finished(session2)
            window2.room_interaction_coordinator.confirm_mutation({"operation": "off"})
            self._wait_for(lambda: window2.room_interaction_coordinator.active_context is None)
            window2.room_diagnostic_controller.start_pdu_mutation.assert_not_called()

    def test_cloudlink_fallback_success_persists_exact_candidate_and_profile(self):
        with patch("gui.main_window.InteractiveSessionController", ControlledCloudSession), patch(
            "gui.main_window.CloudLinkMicrophoneMeter", ControlledCloudMeter
        ):
            window, session = self._window_session("CloudLink Bar 310")
            window.room_interaction_coordinator.cycle_finished(session)
            first_meter = ControlledCloudMeter.instances[0]
            first_meter.terminal.emit({"category": "authentication_error"})
            self.assertEqual(1, len(ControlledCloudMeter.instances))
            ControlledCloudSession.instances[0].finish_cleanup()
            self.assertEqual(2, len(ControlledCloudMeter.instances))

            profile = {"protocol": "https", "port": 443}
            ControlledCloudMeter.instances[1].accepted.emit(
                {"available": True, "raw_level": -12.0},
                {"credential_index": 0, "connection_profile": profile},
            )
            self.assertEqual(1, window.get_current_credential_index("CloudLink Bar 310", "192.0.2.10"))
            self.assertEqual(profile, window.get_device_connection_profile("CloudLink Bar 310", "192.0.2.10"))
            ControlledCloudMeter.instances[1].accepted.emit(
                {"available": True, "raw_level": -8.0},
                {"credential_index": 0, "connection_profile": profile},
            )
            self.assertEqual(
                -8.0,
                session.row_for("a").accepted_snapshot["live_microphone"]["raw_level"],
            )

            window.room_interaction_coordinator.collapse("a")
            ControlledCloudSession.instances[1].finish_cleanup()
            window.room_interaction_coordinator.expand("a")
            next_activation = ControlledCloudSession.instances[2].activated
            self.assertEqual("second", next_activation[2][0]["username"])
            self.assertEqual(profile, next_activation[4])

    def test_matrix_and_dmp_first_current_success_persist_assigned_candidate(self):
        for model, patches in (
            ("Extron IN1804", (patch("gui.main_window.MatrixController", ControlledMatrix),)),
            (
                "Extron DMP 64 Plus",
                (
                    patch("gui.main_window.ExtronDMP64PlusMeterWorker", ControlledDmpWorker),
                    patch("gui.main_window.QThreadPool", ControlledPool),
                ),
            ),
        ):
            with self.subTest(model=model):
                for active_patch in patches:
                    active_patch.start()
                    self.addCleanup(active_patch.stop)
                window, session = self._window_session(model)
                key = window.get_credential_key(model, "192.0.2.10")
                window.current_credential_index[key] = 1
                window.room_interaction_coordinator.cycle_finished(session)
                window.current_credential_index.pop(key)
                if model == "Extron IN1804":
                    ControlledMatrix.instances[-1].resultAccepted.emit({"matrix": "ok"}, object())
                else:
                    ControlledDmpWorker.instances[-1].signals.result.emit({"meter": "ok"})
                self.assertEqual(1, window.get_current_credential_index(model, "192.0.2.10"))
                for active_patch in reversed(patches):
                    active_patch.stop()

    def test_real_accordion_switch_closes_and_cancels_a_children(self):
        window, session = self._window_session("Huawei TE40", rows=2)
        window.room_call_log_controller.start = Mock()
        window.room_call_log_controller.cancel = Mock()
        auxiliary = window.room_interaction_coordinator.request_auxiliary("call_log")
        call_log = window._room_call_log_windows[auxiliary]
        window._on_room_debug_requested("a")
        debug = window._room_debug_windows["a"]

        window.room_diagnostic_tree._by_record["b"].setExpanded(True)
        self.app.processEvents()

        self.assertEqual("b", session.expanded_record_id)
        self.assertNotIn(auxiliary, window._room_call_log_windows)
        self.assertNotIn("a", window._room_debug_windows)
        self.assertFalse(call_log.isVisible())
        self.assertFalse(debug.isVisible())
        window.room_call_log_controller.cancel.assert_called_once_with(auxiliary)
        window._on_room_call_log_finished(auxiliary, True, {"records": ["late"]}, False, None)
        self.assertNotIn(auxiliary, window._room_call_log_windows)
        self.assertTrue(window.room_diagnostic_tree._by_record["b"].isExpanded())

    def test_real_accordion_collapse_closes_and_cancels_call_log(self):
        window, _session = self._window_session("Huawei TE40")
        window.room_call_log_controller.start = Mock()
        window.room_call_log_controller.cancel = Mock()
        auxiliary = window.room_interaction_coordinator.request_auxiliary("call_log")
        call_log = window._room_call_log_windows[auxiliary]

        window.room_diagnostic_tree._by_record["a"].setExpanded(False)
        self.app.processEvents()

        self.assertFalse(call_log.isVisible())
        self.assertNotIn(auxiliary, window._room_call_log_windows)
        window.room_call_log_controller.cancel.assert_called_once_with(auxiliary)


if __name__ == "__main__":
    unittest.main()
