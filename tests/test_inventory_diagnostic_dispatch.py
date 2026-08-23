import os
import unittest
from unittest.mock import ANY, Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtWidgets import QApplication, QLabel
    from PyQt5.QtCore import QThreadPool
except ImportError:  # pragma: no cover
    QApplication = None
    QThreadPool = None

from core.equipment_inventory import (
    EquipmentInventory,
    EquipmentInventoryLoadError,
    EquipmentInventoryMetadata,
    EquipmentRecord,
    InventoryLoadFailure,
)
from gui.diagnostic_dispatch import (
    ActionBinding,
    DiagnosticActionPurpose,
    ModelResolutionStatus,
    dispatch_entries,
    dispatch_entry_for_model,
    dispatch_model_names,
    resolve_exact_model_for_ip,
    validate_dispatch_registry,
)
from gui.equipment_pages import EQUIPMENT_PAGE_REGISTRY
from gui.ui_states import UIState


def record(record_id, *, ip_address="192.0.2.10", diagnostic_model="Huawei TE40", device_kind="other", room_id=None):
    return EquipmentRecord(
        record_id=record_id,
        source_model="Synthetic",
        diagnostic_model=diagnostic_model,
        ip_address=ip_address,
        mac_address=None,
        serial_number=None,
        room_id=room_id,
        room_name="Room",
        device_kind=device_kind,
        room_vip=None,
    )


def inventory(records):
    return EquipmentInventory.from_records(
        tuple(records),
        EquipmentInventoryMetadata(schema_version=2, snapshot_id="sha256:" + "2" * 64),
    )


class DispatchRegistryTests(unittest.TestCase):
    def test_registry_has_all_models_once_and_no_unknown_default(self):
        expected = (
            "Huawei TE20",
            "Huawei TE40",
            "CloudLink Bar 310",
            "CloudLink Box 310",
            "Polycom RPG 310",
            "Extron IN1804",
            "Aten PE8208AV",
            "Extron IPL T PCS4i",
            "Biamp Tesira Forte CI",
            "Extron DMP 64 Plus",
        )
        self.assertEqual(expected, dispatch_model_names())
        self.assertEqual(len(expected), len(set(dispatch_model_names())))
        self.assertIsNone(dispatch_entry_for_model("Unknown Model"))

    def test_registry_integrity_checks_registered_screens(self):
        validate_dispatch_registry(
            registered_screens={"codec", "matrix", "pdu", "audio_dsp"},
            page_models_by_screen={
                registration.screen_key: registration.device_models
                for registration in EQUIPMENT_PAGE_REGISTRY
            },
        )
        for entry in dispatch_entries():
            self.assertNotIn("password", entry.__dict__)
            self.assertNotIn("handler", entry.__dict__)

    def test_registry_rejects_unbound_room_adapter_key(self):
        with self.assertRaisesRegex(ValueError, "room adapter is not bound"):
            validate_dispatch_registry(
                registered_screens={"codec", "matrix", "pdu", "audio_dsp"},
                page_models_by_screen={
                    registration.screen_key: registration.device_models
                    for registration in EQUIPMENT_PAGE_REGISTRY
                },
                available_room_adapter_keys={"codec_one_shot"},
            )

    def test_room_interaction_capabilities_are_declared_by_exact_registry_entries(self):
        entries = {entry.diagnostic_model: entry for entry in dispatch_entries()}
        for entry in entries.values():
            self.assertEqual("room_one_shot_refresh", entry.local_refresh_binding_key)
            self.assertEqual("room_one_shot_cleanup", entry.cleanup_binding_key)
        self.assertEqual("room_codec_call_log", entries["Huawei TE40"].auxiliary_binding_key)
        self.assertEqual("room_pdu_mutation", entries["Aten PE8208AV"].mutation_binding_key)
        self.assertEqual("room_one_shot_refresh", entries["Aten PE8208AV"].reconciliation_binding_key)
        self.assertEqual("room_periodic_live", entries["Extron DMP 64 Plus"].live_binding_key)


class ExactModelResolverTests(unittest.TestCase):
    def resolve(self, records, ip="192.0.2.10"):
        return resolve_exact_model_for_ip(
            purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
            normalized_ip=ip,
            inventory=inventory(records) if records is not None else None,
        )

    def test_resolution_outcomes_preserve_cardinality_before_model_inspection(self):
        self.assertEqual(ModelResolutionStatus.INVENTORY_UNAVAILABLE, self.resolve(None).status)
        self.assertEqual(ModelResolutionStatus.IP_NOT_FOUND, self.resolve([]).status)
        self.assertEqual(
            ModelResolutionStatus.AMBIGUOUS_IP,
            self.resolve(
                [
                    record("A", diagnostic_model="Huawei TE40", device_kind="video_codec"),
                    record("B", diagnostic_model="Aten PE8208AV", device_kind="other"),
                ]
            ).status,
        )

    def test_exact_model_routes_without_kind_authority(self):
        cases = {
            "Aten PE8208AV": "pdu",
            "Extron IPL T PCS4i": "pdu",
            "Huawei TE40": "codec",
            "Extron IN1804": "matrix",
            "Biamp Tesira Forte CI": "audio_dsp",
            "Extron DMP 64 Plus": "audio_dsp",
        }
        for model, screen in cases.items():
            with self.subTest(model=model):
                result = self.resolve([record("A", diagnostic_model=model, device_kind="other")])
                self.assertEqual(ModelResolutionStatus.RESOLVED, result.status)
                self.assertEqual(screen, result.entry.screen_key)

    def test_null_and_unsupported_model_do_not_default(self):
        self.assertEqual(
            ModelResolutionStatus.MODEL_UNMAPPED,
            self.resolve([record("A", diagnostic_model=None, device_kind="video_codec")]).status,
        )
        inv = inventory(
            [
                EquipmentRecord(
                    record_id="A",
                    source_model="Synthetic",
                    diagnostic_model="Future Model",
                    ip_address="192.0.2.10",
                    mac_address=None,
                    serial_number=None,
                    room_id="ROOM-1",
                    room_name="Room",
                    device_kind="video_codec",
                    room_vip=None,
                )
            ]
        )
        result = resolve_exact_model_for_ip(
            purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
            normalized_ip="192.0.2.10",
            inventory=inv,
        )
        self.assertEqual(ModelResolutionStatus.MODEL_UNSUPPORTED, result.status)
        self.assertIsNone(result.entry)


@unittest.skipIf(QApplication is None, "PyQt5 is unavailable")
class MainPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_main_panel_has_no_persistent_model_selector(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        self.assertFalse(hasattr(window, "device_combo"))
        self.assertEqual([], window.findChildren(type(window.ip_entry), "deviceCombo"))
        labels = [label.text() for label in window.connection_panel.findChildren(QLabel)]
        self.assertNotIn("Устройство", labels)
        self.assertIn("IP-адрес", labels)


@unittest.skipIf(QApplication is None, "PyQt5 is unavailable")
class FailClosedProductionRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_bind_worker_with_unknown_model_does_not_create_codec_request(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        worker = Mock()
        worker.device_name = "Future Model"
        worker.ip_address = "192.0.2.10"
        worker.signals.result.connect = Mock()
        worker.signals.error.connect = Mock()
        worker.signals.progress.connect = Mock()
        worker.signals.status.connect = Mock()
        worker.signals.finished.connect = Mock()
        window._fail_request_start = Mock()

        window._bind_worker(worker)

        self.assertIsNone(window._active_request)
        window._fail_request_start.assert_called_once()
        worker.signals.result.connect.assert_not_called()

    def test_on_device_change_unknown_model_does_not_switch_to_codec(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.current_screen_type = "matrix"
        before_widget = window.screen_container.currentWidget()
        window.matrix_controller.invalidate_context = Mock()

        changed = window.on_device_change("Future Model")

        self.assertFalse(changed)
        self.assertEqual("matrix", window.current_screen_type)
        self.assertIs(before_widget, window.screen_container.currentWidget())
        window.matrix_controller.invalidate_context.assert_not_called()

    def test_unknown_screen_key_does_not_select_codec(self):
        from gui.main_window import VCSDiagnosticApp
        from gui.diagnostic_dispatch import DiagnosticDispatchEntry

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.ip_entry.setText("192.0.2.10")
        bad_entry = DiagnosticDispatchEntry(
            "Huawei TE40",
            "unknown_screen",
            "huawei_te40",
        )
        window._resolve_model_for_action = Mock(
            return_value=type(
                "Resolution",
                (),
                {
                    "resolved": True,
                    "entry": bad_entry,
                    "status": ModelResolutionStatus.RESOLVED,
                },
            )()
        )
        window.ensure_ping_success = Mock(return_value=True)
        window.device_credentials["Huawei TE40"] = [
            {"username": "operator", "password": "secret-password"}
        ]
        before_widget = window.screen_container.currentWidget()

        with patch("gui.main_window.QMessageBox.warning"):
            window.refresh_data()

        self.assertIsNone(window._active_request)
        self.assertIs(before_widget, window.screen_container.currentWidget())


class CapturingReachabilityPool:
    def __init__(self):
        self.runnables = []

    def start(self, runnable):
        self.runnables.append(runnable)


class FailingReachabilityPool:
    def start(self, runnable):
        raise RuntimeError("thread-pool unavailable")


@unittest.skipIf(QApplication is None, "PyQt5 is unavailable")
class AsyncReachabilityDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _window_for_model(self, model, *, ip="192.0.2.10"):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.equipment_inventory = inventory(
            [record("A", ip_address=ip, diagnostic_model=model)]
        )
        window.ip_entry.setText(ip)
        window.device_credentials[model] = [
            {"username": "operator", "password": "secret-password"}
        ]
        if model == "Extron IPL T PCS4i":
            window.device_credentials[model] = [{"password": "secret-password"}]
        pool = CapturingReachabilityPool()
        window._reachability_thread_pool = lambda: pool
        window._reachability_ping_callable = Mock(return_value=True)
        return window, pool

    def _finish_reachability(self, window, worker, *, reachable=True):
        window._on_reachability_finished(
            {
                "operation_id": worker.operation_id,
                "ip_address": worker.ip_address,
                "reachable": reachable,
            }
        )

    def _reachability_plan_key(self, window, model, ip, worker):
        return window._credential_attempt_plan_key(
            model,
            ip,
            worker.operation_id,
        )

    def _assert_no_reachability_plan(self, window, model, ip, worker):
        self.assertNotIn(
            self._reachability_plan_key(window, model, ip, worker),
            window.__dict__.get("_credential_attempt_plans", {}),
        )

    def _assert_terminal_reachability_cleanup(self, window):
        self.assertIsNone(window._current_reachability_context)
        self.assertIsNone(window._current_reachability_worker)
        self.assertIsNone(window._reachability_presentation_operation_id)
        self.assertEqual({}, window._diagnostic_credential_snapshots)
        self.assertTrue(window.refresh_btn.isEnabled())
        self.assertEqual("Обновить данные", window.refresh_btn.text())
        self.assertNotEqual(UIState.LOADING, window.ui_state)
        status_text = window.connection_status.text()
        self.assertNotIn("Проверка...", status_text)
        self.assertNotIn("Проверка доступности", status_text)
        self.assertNotIn("LOADING", status_text)

    def test_refresh_submits_reachability_without_sync_subprocess_or_lifecycle(self):
        window, pool = self._window_for_model("Huawei TE40")
        window.refresh_huawei_te40 = Mock()
        before_widget = window.screen_container.currentWidget()

        with patch("gui.main_window.subprocess.run") as subprocess_run:
            window.refresh_data()

        subprocess_run.assert_not_called()
        self.assertEqual(1, len(pool.runnables))
        worker = pool.runnables[0]
        self.assertEqual("192.0.2.10", worker.ip_address)
        self.assertFalse(hasattr(worker, "credentials"))
        self.assertFalse(hasattr(worker, "creds_list"))
        self.assertIsNone(window._active_request)
        self.assertIsNone(window._active_diagnostic_model_context)
        self.assertIs(before_widget, window.screen_container.currentWidget())
        window.refresh_huawei_te40.assert_not_called()
        self._assert_no_reachability_plan(
            window,
            "Huawei TE40",
            "192.0.2.10",
            worker,
        )

    def test_reachability_stage_does_not_retain_operation_plan_or_grow_registry(self):
        window, pool = self._window_for_model("Huawei TE40")
        window.refresh_huawei_te40 = Mock()
        unrelated_key = window._credential_attempt_plan_key(
            "Huawei TE20",
            "192.0.2.20",
        )
        window._credential_attempt_plan(
            "Huawei TE20",
            ({"username": "other", "password": "unrelated"},),
            "192.0.2.20",
        )

        with patch("gui.main_window.QMessageBox.warning"):
            for _ in range(3):
                window.refresh_data()
                worker = pool.runnables[-1]
                self._assert_no_reachability_plan(
                    window,
                    "Huawei TE40",
                    "192.0.2.10",
                    worker,
                )
                self.assertEqual(
                    [unrelated_key],
                    list(window._credential_attempt_plans),
                )
                self._finish_reachability(window, worker, reachable=False)
                self._assert_terminal_reachability_cleanup(window)

        self.assertEqual([unrelated_key], list(window._credential_attempt_plans))

    def test_successful_reachability_continues_exact_route_groups(self):
        cases = (
            ("Huawei TE20", "refresh_huawei_te20"),
            ("Huawei TE40", "refresh_huawei_te40"),
            ("CloudLink Bar 310", "refresh_huawei_bar310"),
            ("Polycom RPG 310", "refresh_polycom_rpg310"),
            ("Extron IN1804", "refresh_extron_in1804"),
            ("Aten PE8208AV", "pdu"),
            ("Extron IPL T PCS4i", "pdu"),
            ("Biamp Tesira Forte CI", "refresh_biamp_tesira_forte_ci"),
            ("Extron DMP 64 Plus", "refresh_extron_dmp64_plus"),
        )
        for model, route in cases:
            with self.subTest(model=model):
                window, pool = self._window_for_model(model)
                if route == "pdu":
                    window.pdu_controller.refresh_pdu = Mock()
                else:
                    setattr(window, route, Mock())

                window.refresh_data()
                self._finish_reachability(window, pool.runnables[0], reachable=True)

                self.assertEqual(model, window._active_diagnostic_model_context["model"])
                if route == "pdu":
                    window.pdu_controller.refresh_pdu.assert_called_once_with(
                        "192.0.2.10",
                        model,
                        credential_snapshot=ANY,
                    )
                else:
                    getattr(window, route).assert_called_once_with(
                        "192.0.2.10",
                        credential_snapshot=ANY,
                    )

    def test_empty_credential_chain_blocks_auth_required_models_before_reachability(self):
        cases = (
            ("Huawei TE40", "refresh_huawei_te40"),
            ("Extron IN1804", "refresh_extron_in1804"),
            ("Aten PE8208AV", "pdu"),
            ("Biamp Tesira Forte CI", "refresh_biamp_tesira_forte_ci"),
            ("Extron DMP 64 Plus", "refresh_extron_dmp64_plus"),
        )
        for model, route in cases:
            with self.subTest(model=model):
                window, pool = self._window_for_model(model)
                before_widget = window.screen_container.currentWidget()
                window.device_credentials[model] = []
                window._reachability_ping_callable = Mock(
                    side_effect=AssertionError("ping must not run")
                )
                if route == "pdu":
                    window.pdu_controller.refresh_pdu = Mock()
                else:
                    setattr(window, route, Mock())

                with patch("gui.main_window.QMessageBox.warning"):
                    window.refresh_data()

                self.assertEqual([], pool.runnables)
                window._reachability_ping_callable.assert_not_called()
                self.assertEqual({}, window._diagnostic_credential_snapshots)
                self.assertIsNone(window._current_reachability_context)
                self.assertIsNone(window._current_reachability_worker)
                self.assertIsNone(window._reachability_presentation_operation_id)
                self.assertIsNone(window._active_request)
                self.assertIs(before_widget, window.screen_container.currentWidget())
                self.assertEqual(UIState.REQUEST_ERROR, window.ui_state)
                self.assertTrue(window.refresh_btn.isEnabled())
                self.assertEqual("Обновить данные", window.refresh_btn.text())
                status_text = window.connection_status.text()
                self.assertIn(model, status_text)
                self.assertNotIn("secret-password", status_text)
                self.assertNotIn("operator", status_text)
                if route == "pdu":
                    window.pdu_controller.refresh_pdu.assert_not_called()
                else:
                    getattr(window, route).assert_not_called()

    def test_empty_credential_preflight_reads_store_once(self):
        window, pool = self._window_for_model("Huawei TE40")
        window.refresh_huawei_te40 = Mock()
        window.device_credentials["Huawei TE40"] = []
        original_get = window.device_credentials.get
        reads = 0

        def guarded_get(*args, **kwargs):
            nonlocal reads
            reads += 1
            if reads > 1:
                raise AssertionError("store must not be read after configuration failure")
            return original_get(*args, **kwargs)

        with patch.object(window.device_credentials, "get", side_effect=guarded_get):
            with patch("gui.main_window.QMessageBox.warning"):
                window.refresh_data()

        self.assertEqual(1, reads)
        self.assertEqual([], pool.runnables)
        self.assertEqual({}, window._diagnostic_credential_snapshots)
        self.assertIsNone(window._active_request)
        window.refresh_huawei_te40.assert_not_called()

    def test_pcs4i_without_configured_credentials_reaches_with_passwordless_snapshot(self):
        for configured_chain in (None, []):
            with self.subTest(configured_chain=configured_chain):
                window, pool = self._window_for_model("Extron IPL T PCS4i")
                if configured_chain is None:
                    window.device_credentials.pop("Extron IPL T PCS4i", None)
                else:
                    window.device_credentials["Extron IPL T PCS4i"] = configured_chain
                window.pdu_controller.refresh_pdu = Mock()

                window.refresh_data()

                self.assertEqual(1, len(pool.runnables))
                self.assertEqual(1, len(window._diagnostic_credential_snapshots))
                snapshot = next(iter(window._diagnostic_credential_snapshots.values()))
                self.assertEqual(({},), tuple(dict(candidate) for candidate in snapshot.candidates))
                self._finish_reachability(window, pool.runnables[0], reachable=True)

                _, args, kwargs = window.pdu_controller.refresh_pdu.mock_calls[0]
                self.assertEqual(("192.0.2.10", "Extron IPL T PCS4i"), args)
                handed_snapshot = kwargs["credential_snapshot"]
                self.assertEqual(({},), tuple(dict(candidate) for candidate in handed_snapshot.candidates))
                self.assertEqual({}, window._diagnostic_credential_snapshots)
                self.assertIsNone(window._reachability_presentation_operation_id)

    def test_all_routes_receive_prepared_snapshot_after_store_mutation(self):
        cases = (
            ("Huawei TE20", "refresh_huawei_te20", {"username": "first", "password": "old-1"}),
            ("Huawei TE40", "refresh_huawei_te40", {"username": "first", "password": "old-1"}),
            ("CloudLink Bar 310", "refresh_huawei_bar310", {"username": "first", "password": "old-1"}),
            ("Polycom RPG 310", "refresh_polycom_rpg310", {"username": "first", "password": "old-1"}),
            ("Extron IN1804", "refresh_extron_in1804", {"username": "first", "password": "old-1"}),
            ("Aten PE8208AV", "pdu", {"username": "first", "password": "old-1"}),
            ("Extron IPL T PCS4i", "pdu", {"password": "old-1"}),
            ("Biamp Tesira Forte CI", "refresh_biamp_tesira_forte_ci", {"username": "first", "password": "old-1"}),
            ("Extron DMP 64 Plus", "refresh_extron_dmp64_plus", {"username": "first", "password": "old-1"}),
        )
        for model, route, first_candidate in cases:
            with self.subTest(model=model):
                window, pool = self._window_for_model(model)
                second_candidate = dict(first_candidate)
                second_candidate["password"] = "old-2"
                window.device_credentials[model] = [
                    first_candidate,
                    second_candidate,
                ]
                window.set_current_credential_index(model, 1, "192.0.2.10")
                if route == "pdu":
                    window.pdu_controller.refresh_pdu = Mock()
                else:
                    setattr(window, route, Mock())

                window.refresh_data()
                self.assertEqual(1, len(window._diagnostic_credential_snapshots))
                snapshot = next(iter(window._diagnostic_credential_snapshots.values()))
                self.assertEqual(model, snapshot.diagnostic_model)
                self.assertEqual("192.0.2.10", snapshot.ip_address)
                self.assertEqual(1, snapshot.starting_successful_index)
                self.assertEqual("old-2", snapshot.candidates[1]["password"])
                with self.assertRaises(TypeError):
                    snapshot.candidates[0]["password"] = "mutated"
                self._assert_no_reachability_plan(
                    window,
                    model,
                    "192.0.2.10",
                    pool.runnables[0],
                )

                window.device_credentials[model] = [
                    {"username": "new", "password": "new-secret"}
                ]
                with patch.object(
                    window.device_credentials,
                    "get",
                    side_effect=AssertionError("store must not be read after reachability"),
                ):
                    self._finish_reachability(window, pool.runnables[0], reachable=True)

                self.assertEqual({}, window._diagnostic_credential_snapshots)
                self._assert_no_reachability_plan(
                    window,
                    model,
                    "192.0.2.10",
                    pool.runnables[0],
                )
                if route == "pdu":
                    _, args, kwargs = window.pdu_controller.refresh_pdu.mock_calls[0]
                    self.assertEqual(("192.0.2.10", model), args)
                else:
                    _, args, kwargs = getattr(window, route).mock_calls[0]
                    self.assertEqual(("192.0.2.10",), args)
                handed_snapshot = kwargs["credential_snapshot"]
                self.assertIs(handed_snapshot, snapshot)
                self.assertEqual("old-2", handed_snapshot.candidates[1]["password"])

    def test_actual_startup_uses_snapshot_candidates_for_representative_lifecycles(self):
        cases = (
            "Huawei TE40",
            "Biamp Tesira Forte CI",
            "Extron IN1804",
            "Aten PE8208AV",
            "Extron IPL T PCS4i",
            "Extron DMP 64 Plus",
        )
        for model in cases:
            with self.subTest(model=model):
                window, reachability_pool = self._window_for_model(model)
                if model == "Extron IPL T PCS4i":
                    candidates = [{"password": "old-1"}, {"password": "old-2"}]
                    replacement = [{"password": "new-secret"}]
                else:
                    candidates = [
                        {"username": "first", "password": "old-1"},
                        {"username": "second", "password": "old-2"},
                    ]
                    replacement = [{"username": "new", "password": "new-secret"}]
                window.device_credentials[model] = candidates
                window.set_current_credential_index(model, 1, "192.0.2.10")
                device_pool = CapturingReachabilityPool()
                window.matrix_controller._thread_pool = device_pool
                window.pdu_controller._thread_pool = device_pool
                window.dmp_polling_controller._thread_pool = device_pool

                window.refresh_data()
                window.device_credentials[model] = replacement
                with patch.object(
                    window.device_credentials,
                    "get",
                    side_effect=AssertionError("store must not be read for startup"),
                ), patch.object(
                    QThreadPool.globalInstance(),
                    "start",
                    side_effect=device_pool.start,
                ):
                    self._finish_reachability(
                        window,
                        reachability_pool.runnables[0],
                        reachable=True,
                    )

                if model == "Extron IN1804":
                    context = window.matrix_controller._active_context
                    self.assertEqual(1, context.candidate_index)
                    matrix_candidates = window.matrix_controller._candidate_snapshots[
                        context.operation_id
                    ]
                    self.assertEqual("old-2", matrix_candidates[1]["password"])
                    continue

                self.assertEqual(1, len(device_pool.runnables))
                worker = device_pool.runnables[0]
                self.assertEqual(model, getattr(worker, "device_name", model))
                self.assertEqual(1, getattr(worker, "current_idx", 1))
                if model == "Extron IPL T PCS4i":
                    self.assertEqual("old-2", getattr(worker, "password", None))
                    self.assertFalse(getattr(worker, "username", None))
                else:
                    self.assertEqual("second", getattr(worker, "username", None))
                    self.assertEqual("old-2", getattr(worker, "password", None))

    def test_exact_credential_mutation_supersedes_pending_reachability_only_for_same_model_ip(self):
        window, pool = self._window_for_model("Huawei TE40")
        window.refresh_huawei_te40 = Mock()
        window.device_credentials["Huawei TE20"] = [
            {"username": "te20", "password": "unchanged"}
        ]

        window.refresh_data()
        worker = pool.runnables[0]
        self.assertIsNotNone(window._current_reachability_context)
        self.assertEqual(1, len(window._diagnostic_credential_snapshots))

        window.configure_credential_candidate(
            "Huawei TE20",
            "192.0.2.10",
            {"username": "te20", "password": "new"},
        )
        self.assertIsNotNone(window._current_reachability_context)
        self.assertEqual(1, len(window._diagnostic_credential_snapshots))

        window.configure_credential_candidate(
            "Huawei TE40",
            "192.0.2.10",
            {"username": "operator", "password": "replacement"},
        )
        self._assert_terminal_reachability_cleanup(window)
        self._assert_no_reachability_plan(
            window,
            "Huawei TE40",
            "192.0.2.10",
            worker,
        )

        self._finish_reachability(window, worker, reachable=True)
        window.refresh_huawei_te40.assert_not_called()

    def test_stale_current_reachability_callback_performs_controlled_cleanup(self):
        window, pool = self._window_for_model("Huawei TE40")
        window.refresh_huawei_te40 = Mock()

        window.refresh_data()
        worker = pool.runnables[0]
        window._diagnostic_action_generation += 1

        self._finish_reachability(window, worker, reachable=True)

        self._assert_terminal_reachability_cleanup(window)
        self._assert_no_reachability_plan(
            window,
            "Huawei TE40",
            "192.0.2.10",
            worker,
        )
        self.assertIsNone(window._active_request)
        window.refresh_huawei_te40.assert_not_called()

    def test_malformed_current_reachability_callback_wrong_ip_cleans_loading(self):
        window, pool = self._window_for_model("Huawei TE40")
        window.refresh_huawei_te40 = Mock()

        window.refresh_data()
        worker = pool.runnables[0]
        window._on_reachability_finished(
            {
                "operation_id": worker.operation_id,
                "ip_address": "192.0.2.99",
                "reachable": True,
            }
        )

        self._assert_terminal_reachability_cleanup(window)
        self._assert_no_reachability_plan(
            window,
            "Huawei TE40",
            "192.0.2.10",
            worker,
        )
        self.assertIsNone(window._active_request)
        window.refresh_huawei_te40.assert_not_called()

    def test_old_callback_does_not_clear_newer_reachability_operation(self):
        window, pool = self._window_for_model("Huawei TE40")
        window.refresh_huawei_te40 = Mock()

        window.refresh_data()
        old_worker = pool.runnables[0]
        window.refresh_data()
        new_context = window._current_reachability_context
        new_worker = pool.runnables[1]

        self._finish_reachability(window, old_worker, reachable=False)

        self.assertIs(window._current_reachability_context, new_context)
        self.assertEqual(new_worker.operation_id, new_context["operation_id"])
        self.assertFalse(window.refresh_btn.isEnabled())
        self.assertEqual(
            new_worker.operation_id,
            window._reachability_presentation_operation_id,
        )
        self.assertEqual(1, len(window._diagnostic_credential_snapshots))
        self._assert_no_reachability_plan(
            window,
            "Huawei TE40",
            "192.0.2.10",
            old_worker,
        )
        window.refresh_huawei_te40.assert_not_called()

    def test_reachability_submission_error_restores_ui_and_clears_snapshot(self):
        window, _pool = self._window_for_model("Huawei TE40")
        window._reachability_thread_pool = lambda: FailingReachabilityPool()

        with patch("gui.main_window.QMessageBox.warning"):
            window.refresh_data()

        self._assert_terminal_reachability_cleanup(window)
        self.assertEqual(UIState.REQUEST_ERROR, window.ui_state)

    def test_reachability_invalidation_without_pending_context_preserves_lifecycle_ui(self):
        window, _pool = self._window_for_model("Huawei TE40")
        window.refresh_btn.setEnabled(False)
        window.refresh_btn.setText("Подключение...")
        window.set_ui_state(UIState.LOADING, "Подключение к Huawei TE40 (192.0.2.10)...")

        self.assertFalse(window._invalidate_reachability_context("ip_changed"))

        self.assertEqual(UIState.LOADING, window.ui_state)
        self.assertFalse(window.refresh_btn.isEnabled())
        self.assertEqual("Подключение...", window.refresh_btn.text())
        self.assertIn("Подключение к Huawei TE40", window.connection_status.text())

    def test_supersede_after_reachability_handoff_preserves_active_lifecycle_ui(self):
        cases = (
            ("Huawei TE40", "refresh_huawei_te40"),
            ("Extron IN1804", "refresh_extron_in1804"),
            ("Aten PE8208AV", "pdu"),
            ("Biamp Tesira Forte CI", "refresh_biamp_tesira_forte_ci"),
            ("Extron DMP 64 Plus", "refresh_extron_dmp64_plus"),
        )
        for model, route in cases:
            with self.subTest(model=model):
                window, pool = self._window_for_model(model)
                if route == "pdu":
                    window.pdu_controller.refresh_pdu = Mock()
                else:
                    setattr(window, route, Mock())

                window.refresh_data()
                self._finish_reachability(window, pool.runnables[0], reachable=True)
                self.assertIsNone(window._current_reachability_context)
                self.assertIsNone(window._reachability_presentation_operation_id)

                window.refresh_btn.setEnabled(False)
                window.refresh_btn.setText("Подключение...")
                window.set_ui_state(UIState.LOADING, f"Подключение к {model} (192.0.2.10)...")
                window._supersede_model_actions("ip_changed")

                self.assertEqual(UIState.LOADING, window.ui_state)
                self.assertFalse(window.refresh_btn.isEnabled())
                self.assertEqual("Подключение...", window.refresh_btn.text())
                self.assertIn(f"Подключение к {model}", window.connection_status.text())

    def test_inventory_replacement_supersedes_pending_reachability(self):
        window, pool = self._window_for_model("Huawei TE40")
        window.refresh_huawei_te40 = Mock()

        window.refresh_data()
        worker = pool.runnables[0]
        replacement = EquipmentInventory.from_records(
            (record("B", ip_address="192.0.2.10", diagnostic_model="Huawei TE40"),),
            EquipmentInventoryMetadata(
                schema_version=2,
                snapshot_id="sha256:" + "3" * 64,
            ),
        )

        window.set_equipment_inventory(replacement)

        self._assert_terminal_reachability_cleanup(window)
        self._finish_reachability(window, worker, reachable=True)
        window.refresh_huawei_te40.assert_not_called()

    def test_inventory_failure_category_change_supersedes_pending_reachability(self):
        window, pool = self._window_for_model("Huawei TE40")
        window.refresh_huawei_te40 = Mock()

        window.refresh_data()
        worker = pool.runnables[0]
        window.set_equipment_inventory_failure(
            EquipmentInventoryLoadError(
                InventoryLoadFailure.INVALID_SNAPSHOT,
                "synthetic",
            )
        )

        self._assert_terminal_reachability_cleanup(window)
        self._finish_reachability(window, worker, reachable=False)
        window.refresh_huawei_te40.assert_not_called()

    def test_async_flow_source_has_no_mojibake_markers(self):
        with open("gui/main_window.py", encoding="utf-8") as source_file:
            source = source_file.read()
        for marker in ("РћР±", "РџР°", "РЈС", "Ð", "Ñ"):
            self.assertNotIn(marker, source)

    def test_refresh_text_is_russian_after_async_cleanup_paths(self):
        window, pool = self._window_for_model("Huawei TE40")
        window.refresh_huawei_te40 = Mock()
        window.refresh_data()
        self.assertEqual("Проверка...", window.refresh_btn.text())

        with patch("gui.main_window.QMessageBox.warning"):
            self._finish_reachability(window, pool.runnables[0], reachable=False)
        self.assertEqual("Обновить данные", window.refresh_btn.text())

        window, pool = self._window_for_model("Huawei TE40")
        window.refresh_huawei_te40 = Mock()
        window.refresh_data()
        window._diagnostic_action_generation += 1
        self._finish_reachability(window, pool.runnables[0], reachable=True)
        self.assertEqual("Обновить данные", window.refresh_btn.text())
        self.assertNotEqual(UIState.LOADING, window.ui_state)

        window, _pool = self._window_for_model("Huawei TE40")
        window._reachability_thread_pool = lambda: FailingReachabilityPool()
        with patch("gui.main_window.QMessageBox.warning"):
            window.refresh_data()
        self.assertEqual("Обновить данные", window.refresh_btn.text())
        self.assertNotEqual(UIState.LOADING, window.ui_state)

    def test_failed_reachability_blocks_all_lifecycle_categories(self):
        cases = (
            ("Huawei TE40", "refresh_huawei_te40"),
            ("Extron IN1804", "refresh_extron_in1804"),
            ("Aten PE8208AV", "pdu"),
            ("Extron IPL T PCS4i", "pdu"),
            ("Biamp Tesira Forte CI", "refresh_biamp_tesira_forte_ci"),
            ("Extron DMP 64 Plus", "refresh_extron_dmp64_plus"),
        )
        for model, route in cases:
            with self.subTest(model=model):
                window, pool = self._window_for_model(model)
                before_widget = window.screen_container.currentWidget()
                window._begin_request = Mock(side_effect=AssertionError("request must not start"))
                if route == "pdu":
                    window.pdu_controller.refresh_pdu = Mock()
                    window.pdu_controller._ensure_common_request = Mock(
                        side_effect=AssertionError("PDU request must not start")
                    )
                else:
                    setattr(window, route, Mock())

                with patch("gui.main_window.QMessageBox.warning"):
                    window.refresh_data()
                    self._finish_reachability(window, pool.runnables[0], reachable=False)

                self.assertIsNone(window._active_request)
                self.assertIsNone(window._active_diagnostic_model_context)
                self.assertIs(before_widget, window.screen_container.currentWidget())
                if route == "pdu":
                    window.pdu_controller.refresh_pdu.assert_not_called()
                    window.pdu_controller._ensure_common_request.assert_not_called()
                else:
                    getattr(window, route).assert_not_called()

    def test_stale_reachability_completion_after_ip_change_reset_or_shutdown_is_ignored(self):
        window, pool = self._window_for_model("Huawei TE40")
        window.refresh_huawei_te40 = Mock()

        window.refresh_data()
        worker = pool.runnables[0]
        window.ip_entry.setText("192.0.2.11")
        self._finish_reachability(window, worker, reachable=True)
        window.refresh_huawei_te40.assert_not_called()
        self.assertIsNone(window._active_request)

        window, pool = self._window_for_model("Huawei TE40")
        window.refresh_huawei_te40 = Mock()
        window.refresh_data()
        worker = pool.runnables[0]
        window._supersede_model_actions("reset")
        self._finish_reachability(window, worker, reachable=True)
        window.refresh_huawei_te40.assert_not_called()
        self.assertIsNone(window._active_request)

        window, pool = self._window_for_model("Huawei TE40")
        window.refresh_huawei_te40 = Mock()
        window.refresh_data()
        worker = pool.runnables[0]
        window._supersede_model_actions("shutdown")
        self._finish_reachability(window, worker, reachable=True)
        window.refresh_huawei_te40.assert_not_called()
        self.assertIsNone(window._active_request)


@unittest.skipIf(QApplication is None, "PyQt5 is unavailable")
class ActionBindingCurrentnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _binding(self, window, purpose, generation, *, ip="192.0.2.10", model=None,
                 fallback_dialog_id=None, credential_dialog_id=None):
        entry = dispatch_entry_for_model(model) if model else None
        if entry is None:
            return window._binding_id(
                purpose=purpose,
                generation=generation,
                normalized_ip=ip,
                resolution_status=ModelResolutionStatus.IP_NOT_FOUND.value,
                fallback_dialog_id=fallback_dialog_id,
                credential_dialog_id=credential_dialog_id,
            )
        return window._accepted_action_binding(
            purpose=purpose,
            generation=generation,
            normalized_ip=ip,
            resolution_status=ModelResolutionStatus.RESOLVED.value,
            source="AUTO_INVENTORY",
            entry=entry,
            fallback_dialog_id=fallback_dialog_id,
            credential_dialog_id=credential_dialog_id,
        )

    def test_old_diagnostic_fallback_after_new_fallback_is_not_current(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.ip_entry.setText("192.0.2.10")
        generation = window._next_action_generation(DiagnosticActionPurpose.DIAGNOSTIC_START)
        old = self._binding(
            window,
            DiagnosticActionPurpose.DIAGNOSTIC_START,
            generation,
            fallback_dialog_id=1,
        )
        new = self._binding(
            window,
            DiagnosticActionPurpose.DIAGNOSTIC_START,
            generation,
            fallback_dialog_id=2,
        )

        window._publish_current_dialog_binding("diagnostic_fallback", old)
        window._publish_current_dialog_binding("diagnostic_fallback", new)

        self.assertFalse(
            window._is_action_binding_current(
                purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
                generation=generation,
                normalized_ip="192.0.2.10",
                binding_id=old,
            )
        )
        self.assertTrue(
            window._is_action_binding_current(
                purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
                generation=generation,
                normalized_ip="192.0.2.10",
                binding_id=new,
            )
        )

    def test_old_credential_fallback_and_dialog_after_new_same_stage_are_not_current(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.ip_entry.setText("192.0.2.10")
        generation = window._next_action_generation(
            DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION
        )
        old_fallback = self._binding(
            window,
            DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION,
            generation,
            fallback_dialog_id=1,
        )
        new_fallback = self._binding(
            window,
            DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION,
            generation,
            fallback_dialog_id=2,
        )
        old_dialog = self._binding(
            window,
            DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION,
            generation,
            model="Huawei TE40",
            credential_dialog_id=1,
        )
        new_dialog = self._binding(
            window,
            DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION,
            generation,
            model="Huawei TE40",
            credential_dialog_id=2,
        )

        window._publish_current_dialog_binding("credential_fallback", old_fallback)
        window._publish_current_dialog_binding("credential_fallback", new_fallback)
        window._publish_current_dialog_binding("credential_dialog", old_dialog)
        window._publish_current_dialog_binding("credential_dialog", new_dialog)

        self.assertFalse(
            window._is_action_binding_current(
                purpose=DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION,
                generation=generation,
                normalized_ip="192.0.2.10",
                binding_id=old_fallback,
            )
        )
        self.assertFalse(
            window._is_action_binding_current(
                purpose=DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION,
                generation=generation,
                normalized_ip="192.0.2.10",
                binding_id=old_dialog,
            )
        )
        self.assertTrue(
            window._is_action_binding_current(
                purpose=DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION,
                generation=generation,
                normalized_ip="192.0.2.10",
                binding_id=new_dialog,
            )
        )

    def test_arbitrary_dialog_id_and_cross_purpose_binding_are_rejected(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.ip_entry.setText("192.0.2.10")
        generation = window._next_action_generation(DiagnosticActionPurpose.DIAGNOSTIC_START)
        arbitrary = self._binding(
            window,
            DiagnosticActionPurpose.DIAGNOSTIC_START,
            generation,
            model="Huawei TE40",
            fallback_dialog_id=404,
        )
        credential_binding = ActionBinding(
            purpose=DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION,
            generation=generation,
            normalized_ip="192.0.2.10",
            inventory_context_identity=arbitrary.inventory_context_identity,
            resolution_status=arbitrary.resolution_status,
            selection_source=arbitrary.selection_source,
            accepted_model=arbitrary.accepted_model,
            screen_key=arbitrary.screen_key,
            lifecycle_route=arbitrary.lifecycle_route,
            fallback_dialog_id=404,
        )

        self.assertFalse(
            window._is_action_binding_current(
                purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
                generation=generation,
                normalized_ip="192.0.2.10",
                binding_id=arbitrary,
            )
        )
        window._publish_current_dialog_binding("credential_fallback", credential_binding)
        self.assertFalse(
            window._is_action_binding_current(
                purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
                generation=generation,
                normalized_ip="192.0.2.10",
                binding_id=credential_binding,
            )
        )

    def test_binding_rejected_after_ip_inventory_reset_and_shutdown(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.equipment_inventory = inventory(
            [record("A", ip_address="192.0.2.10", diagnostic_model="Huawei TE40")]
        )
        window.ip_entry.setText("192.0.2.10")
        generation = window._next_action_generation(DiagnosticActionPurpose.DIAGNOSTIC_START)
        binding = self._binding(
            window,
            DiagnosticActionPurpose.DIAGNOSTIC_START,
            generation,
            fallback_dialog_id=1,
        )
        window._publish_current_dialog_binding("diagnostic_fallback", binding)

        window.ip_entry.setText("192.0.2.11")
        self.assertFalse(
            window._is_action_binding_current(
                purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
                generation=generation,
                normalized_ip="192.0.2.10",
                binding_id=binding,
            )
        )

        window.ip_entry.setText("192.0.2.10")
        generation = window._next_action_generation(DiagnosticActionPurpose.DIAGNOSTIC_START)
        binding = self._binding(
            window,
            DiagnosticActionPurpose.DIAGNOSTIC_START,
            generation,
            fallback_dialog_id=2,
        )
        window._publish_current_dialog_binding("diagnostic_fallback", binding)
        window.equipment_inventory = EquipmentInventory.from_records(
            (record("B", ip_address="192.0.2.10", diagnostic_model="Huawei TE40"),),
            EquipmentInventoryMetadata(
                schema_version=2,
                snapshot_id="sha256:" + "3" * 64,
            ),
        )
        self.assertFalse(
            window._is_action_binding_current(
                purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
                generation=generation,
                normalized_ip="192.0.2.10",
                binding_id=binding,
            )
        )

        window.equipment_inventory = None
        generation = window._next_action_generation(DiagnosticActionPurpose.DIAGNOSTIC_START)
        binding = self._binding(
            window,
            DiagnosticActionPurpose.DIAGNOSTIC_START,
            generation,
            fallback_dialog_id=3,
        )
        window._publish_current_dialog_binding("diagnostic_fallback", binding)
        window._supersede_model_actions("reset")
        self.assertFalse(
            window._is_action_binding_current(
                purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
                generation=generation,
                normalized_ip="192.0.2.10",
                binding_id=binding,
            )
        )

        generation = window._next_action_generation(DiagnosticActionPurpose.DIAGNOSTIC_START)
        binding = self._binding(
            window,
            DiagnosticActionPurpose.DIAGNOSTIC_START,
            generation,
            fallback_dialog_id=4,
        )
        window._publish_current_dialog_binding("diagnostic_fallback", binding)
        window.close()
        self.assertFalse(
            window._is_action_binding_current(
                purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
                generation=generation,
                normalized_ip="192.0.2.10",
                binding_id=binding,
            )
        )

    def test_old_dialog_clear_does_not_remove_newer_binding(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.ip_entry.setText("192.0.2.10")
        generation = window._next_action_generation(DiagnosticActionPurpose.DIAGNOSTIC_START)
        old = self._binding(
            window,
            DiagnosticActionPurpose.DIAGNOSTIC_START,
            generation,
            fallback_dialog_id=1,
        )
        new = self._binding(
            window,
            DiagnosticActionPurpose.DIAGNOSTIC_START,
            generation,
            fallback_dialog_id=2,
        )
        window._publish_current_dialog_binding("diagnostic_fallback", old)
        window._publish_current_dialog_binding("diagnostic_fallback", new)

        window._clear_current_dialog_binding("diagnostic_fallback", old)

        self.assertEqual(
            new,
            window._current_dialog_binding(
                DiagnosticActionPurpose.DIAGNOSTIC_START,
                "diagnostic_fallback",
            ),
        )


if __name__ == "__main__":
    unittest.main()
