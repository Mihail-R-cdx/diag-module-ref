import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtCore import QThreadPool
    from PyQt5.QtWidgets import QApplication, QMessageBox
except ImportError:
    QApplication = None

from core.exceptions import CodecFailureCategory
from core.pdu import COMMAND_ON, REFRESH, PDUOperationDescriptor


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class PDUControllerLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")

    def setUp(self):
        from gui.main_window import VCSDiagnosticApp

        self.window = VCSDiagnosticApp()
        self.window.show()
        self.window.ip_entry.setText("192.0.2.44")
        self.window._accept_test_diagnostic_model("Extron IPL T PCS4i")
        self.window.show_progress_dialog = Mock()
        self.window.hide_progress_dialog = Mock()
        self.window._active_request_credentials = [{}]
        self.window._active_request = {
            "id": 100,
            "device": "Extron IPL T PCS4i",
            "ip": "192.0.2.44",
            "screen": self.window.screens["pdu"],
            "credential_context": self.window._pdu_context_token(),
            "credential_index": None,
        }
        QApplication.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        QApplication.processEvents()

    def test_refresh_lane_does_not_invalidate_active_mutation_lane(self):
        started = []
        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append):
            self.assertTrue(self.window.control_pdu_outlet(1, "on"))
            mutation_worker = started[-1]
            mutation_lane = self.window.pdu_controller._mutation_lane

            self.assertTrue(self.window.refresh_pdu("192.0.2.44", "Extron IPL T PCS4i"))
            refresh_worker = started[-1]

        self.assertIsNotNone(mutation_lane)
        self.assertEqual(
            mutation_lane.operation_id,
            self.window.pdu_controller._mutation_lane.operation_id,
        )
        self.window.on_pdu_refresh_finished(refresh_worker, refresh_worker.descriptor)
        self.assertTrue(self.window.screens["pdu"].mutation_busy)
        self.assertTrue(
            self.window.pdu_controller.is_mutation_descriptor_current(
                mutation_worker.descriptor,
                "individual",
                mutation_worker,
            )
        )

    def test_screen_refresh_signal_preserves_active_mutation_context_and_skips_ping(self):
        started = []
        self.window.ensure_ping_success = Mock(return_value=True)
        self.window.ping_device = Mock(return_value=True)

        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append), \
                patch.object(QMessageBox, "information"):
            self.assertTrue(self.window.control_pdu_outlet(1, "on"))
            mutation_worker = started[-1]
            mutation_lane = self.window.pdu_controller._mutation_lane
            generation = self.window._active_request["id"]

            self.window.screens["pdu"].refresh()
            refresh_worker = started[-1]

            self.assertEqual(generation, self.window._active_request["id"])
            self.assertEqual(
                mutation_lane.operation_id,
                self.window.pdu_controller._mutation_lane.operation_id,
            )
            self.assertTrue(
                self.window.pdu_controller.is_mutation_descriptor_current(
                    mutation_worker.descriptor,
                    "individual",
                    mutation_worker,
                )
            )
            self.assertTrue(
                self.window.pdu_controller.is_refresh_descriptor_current(
                    refresh_worker.descriptor,
                    refresh_worker,
                )
            )
            self.assertTrue(self.window.screens["pdu"].mutation_busy)
            self.assertFalse(hasattr(refresh_worker, "creds_list"))
            self.assertFalse(hasattr(refresh_worker, "current_idx"))

            self.window.on_pdu_refresh_finished(refresh_worker, refresh_worker.descriptor)
            self.assertTrue(self.window.screens["pdu"].mutation_busy)

            self.window.on_pdu_command_result(
                {
                    "success": True,
                    "operation": COMMAND_ON,
                    "outlet_number": 1,
                    "state_changing_send_attempted": True,
                },
                mutation_worker,
                mutation_worker.descriptor,
            )

        self.assertFalse(self.window.screens["pdu"].mutation_busy)
        self.window.ensure_ping_success.assert_not_called()
        self.window.ping_device.assert_not_called()
        self.assertGreaterEqual(len(started), 3)

    def test_different_lane_credential_indices_do_not_invalidate_each_other(self):
        controller = self.window.pdu_controller
        mutation = PDUOperationDescriptor(
            operation_id=1,
            generation=100,
            model="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            operation=COMMAND_ON,
            outlet_number=1,
            credential_context=self.window._pdu_context_token(),
            credential_index=1,
        )
        mutation_worker = object()
        controller.set_mutation_busy(mutation, "individual", True, mutation_worker)

        refresh_worker = controller._build_refresh_worker(
            device_name="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            creds_list=({"password": "a"}, {"password": "b"}),
            current_idx=0,
            operation_id=2,
            generation=100,
            state_epoch=controller._state_epoch,
            originating_mutation_operation_id=None,
        )

        self.assertEqual(0, refresh_worker.descriptor.credential_index)
        self.assertEqual(0, self.window._active_request["credential_index"])
        self.assertTrue(
            controller.is_mutation_descriptor_current(
                mutation,
                "individual",
                mutation_worker,
            )
        )
        self.assertTrue(
            controller.is_refresh_descriptor_current(
                refresh_worker.descriptor,
                refresh_worker,
            )
        )

        self.window.on_pdu_refresh_finished(refresh_worker, refresh_worker.descriptor)

        self.assertTrue(self.window.screens["pdu"].mutation_busy)
        self.assertTrue(
            controller.is_mutation_descriptor_current(
                mutation,
                "individual",
                mutation_worker,
            )
        )

    def test_pre_mutation_refresh_result_cannot_overwrite_mutation_epoch_state(self):
        started = []
        self.window.on_device_data_received = Mock()
        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append):
            self.assertTrue(self.window.refresh_pdu("192.0.2.44", "Extron IPL T PCS4i"))
            refresh_worker = started[-1]
            self.assertTrue(self.window.control_pdu_outlet(1, "on"))

        self.window.on_pdu_refresh_result(
            {"outlets": [{"number": 1, "status": "off"}]},
            refresh_worker,
            refresh_worker.descriptor,
        )

        self.window.on_device_data_received.assert_not_called()

    def test_reconciliation_is_refresh_lane_bound_to_originating_mutation(self):
        started = []
        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append), \
                patch.object(QMessageBox, "information"):
            self.assertTrue(self.window.control_pdu_outlet(1, "on"))
            mutation_worker = started[-1]
            self.window.on_pdu_command_result(
                {
                    "success": True,
                    "operation": COMMAND_ON,
                    "outlet_number": 1,
                    "state_changing_send_attempted": True,
                },
                mutation_worker,
                mutation_worker.descriptor,
            )

        self.assertEqual(2, len(started))
        reconciliation = started[-1]
        self.assertEqual(REFRESH, reconciliation.descriptor.operation)
        self.assertEqual(mutation_worker.descriptor.generation, reconciliation.descriptor.generation)
        self.assertEqual(mutation_worker.descriptor.model, reconciliation.descriptor.model)
        self.assertEqual(mutation_worker.descriptor.ip_address, reconciliation.descriptor.ip_address)
        self.assertEqual(
            mutation_worker.descriptor.operation_id,
            self.window.pdu_controller._refresh_lane.originating_mutation_operation_id,
        )

    def test_stale_finished_cannot_clear_newer_mutation_busy_state(self):
        old = PDUOperationDescriptor(
            operation_id=1,
            generation=100,
            model="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            operation=COMMAND_ON,
            outlet_number=1,
            credential_context=self.window._pdu_context_token(),
        )
        new = PDUOperationDescriptor(
            operation_id=2,
            generation=100,
            model="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            operation=COMMAND_ON,
            outlet_number=2,
            credential_context=self.window._pdu_context_token(),
        )
        old_worker = object()
        new_worker = object()

        self.window.pdu_controller.set_mutation_busy(old, "individual", True, old_worker)
        self.window.pdu_controller.set_mutation_busy(new, "individual", True, new_worker)
        self.window.on_pdu_command_finished(old_worker, old)

        screen = self.window.screens["pdu"]
        self.assertTrue(screen.mutation_busy)
        self.assertEqual(2, screen.mutation_context)
        self.assertTrue(
            self.window.pdu_controller.is_mutation_descriptor_current(
                new,
                "individual",
                new_worker,
            )
        )

    def test_aten_refresh_structured_auth_retries_and_persists_only_after_success(self):
        started = []
        self.window.ip_entry.setText("192.0.2.45")
        self.window._accept_test_diagnostic_model("Aten PE8208AV")
        self.window._active_request_credentials = [
            {"username": "u", "password": "a"},
            {"username": "u", "password": "b"},
        ]
        self.window.set_current_credential_index("Aten PE8208AV", 0, "192.0.2.45")

        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append), \
                patch.object(QMessageBox, "critical"), \
                patch.object(QMessageBox, "information"):
            self.assertTrue(self.window.screens["pdu"].refreshRequested.emit() is None)
            first = started[-1]
            self.window.on_pdu_refresh_error(
                (
                    CodecFailureCategory.AUTHENTICATION.value,
                    "rejected",
                    "",
                    {"state_changing_send_attempted": False},
                ),
                first,
                first.descriptor,
            )

            retry = started[-1]
            self.assertEqual(1, retry.descriptor.credential_index)
            self.assertEqual(
                0,
                self.window.get_current_credential_index("Aten PE8208AV", "192.0.2.45"),
            )
            self.assertFalse(hasattr(retry, "creds_list"))

            self.window.on_pdu_refresh_result(
                {
                    "device_info": {"model": "PE8208AV"},
                    "outlets": [{"number": 1, "status": "on"}],
                    "ip_address": "192.0.2.45",
                },
                retry,
                retry.descriptor,
            )

        self.assertEqual(
            1,
            self.window.get_current_credential_index("Aten PE8208AV", "192.0.2.45"),
        )

    def test_pcs4i_refresh_retry_success_becomes_next_refresh_starting_index(self):
        started = []
        self.window._active_request_credentials = [
            {"password": "a"},
            {"password": "b"},
        ]
        self.window.set_current_credential_index("Extron IPL T PCS4i", 0, "192.0.2.44")

        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append), \
                patch.object(QMessageBox, "critical"), \
                patch.object(QMessageBox, "information"):
            self.window.screens["pdu"].refresh()
            first = started[-1]
            self.assertEqual(0, first.descriptor.credential_index)

            self.window.on_pdu_refresh_error(
                (
                    CodecFailureCategory.AUTHENTICATION.value,
                    "rejected",
                    "",
                    {"state_changing_send_attempted": False},
                ),
                first,
                first.descriptor,
            )
            retry = started[-1]
            self.assertEqual(1, retry.descriptor.credential_index)
            self.assertEqual(
                0,
                self.window.get_current_credential_index(
                    "Extron IPL T PCS4i",
                    "192.0.2.44",
                ),
            )

            self.window.on_pdu_refresh_result(
                {
                    "device_info": {"model": "IPL T PCS4i"},
                    "outlets": [{"number": 1, "status": "on"}],
                    "ip_address": "192.0.2.44",
                    "_credential_used": True,
                },
                retry,
                retry.descriptor,
            )
            self.assertEqual(
                1,
                self.window.get_current_credential_index(
                    "Extron IPL T PCS4i",
                    "192.0.2.44",
                ),
            )

            self.window.screens["pdu"].refresh()
            next_refresh = started[-1]

        self.assertEqual(3, len(started))
        self.assertEqual(1, next_refresh.descriptor.credential_index)
        self.assertEqual({"password": "b"}, next_refresh.credentials)
        self.assertNotEqual({"password": "a"}, next_refresh.credentials)

    def test_pcs4i_refresh_saved_last_candidate_does_not_wrap_after_auth_failure(self):
        started = []
        self.window._active_request_credentials = [
            {"password": "a"},
            {"password": "b"},
        ]
        self.window.set_current_credential_index("Extron IPL T PCS4i", 1, "192.0.2.44")

        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append), \
                patch.object(QMessageBox, "critical"):
            self.window.screens["pdu"].refresh()
            first = started[-1]
            self.assertEqual(1, first.descriptor.credential_index)

            self.window.on_pdu_refresh_error(
                (
                    CodecFailureCategory.AUTHENTICATION.value,
                    "rejected",
                    "",
                    {"state_changing_send_attempted": False},
                ),
                first,
                first.descriptor,
            )

        self.assertEqual(1, len(started))
        self.assertEqual(
            1,
            self.window.get_current_credential_index(
                "Extron IPL T PCS4i",
                "192.0.2.44",
            ),
        )
        self.assertNotIn(
            "Extron IPL T PCS4i|192.0.2.44|operation:"
            f"{first.descriptor.operation_id}",
            self.window.__dict__.get("_credential_attempt_plans", {}),
        )

    def test_aten_refresh_auth_looking_text_does_not_retry_or_persist(self):
        started = []
        self.window.ip_entry.setText("192.0.2.45")
        self.window._accept_test_diagnostic_model("Aten PE8208AV")
        self.window._active_request_credentials = [
            {"username": "u", "password": "a"},
            {"username": "u", "password": "b"},
        ]
        self.window.set_current_credential_index("Aten PE8208AV", 0, "192.0.2.45")

        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append), \
                patch.object(QMessageBox, "critical"):
            self.window.screens["pdu"].refresh()
            first = started[-1]
            self.window.on_pdu_refresh_error(
                (
                    "connection_error",
                    "HTTP 401-like proxy auth text",
                    "",
                    {"state_changing_send_attempted": False},
                ),
                first,
                first.descriptor,
            )

        self.assertEqual(1, len(started))
        self.assertEqual(
            0,
            self.window.get_current_credential_index("Aten PE8208AV", "192.0.2.45"),
        )

    def test_stale_refresh_auth_error_does_not_retry_or_mutate_ui(self):
        started = []
        self.window.set_ui_state = Mock()
        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append):
            self.window.screens["pdu"].refresh()
            worker = started[-1]

        self.window.set_ui_state.reset_mock()
        self.window.pdu_controller.invalidate_context()
        self.window.on_pdu_refresh_error(
            (
                CodecFailureCategory.AUTHENTICATION.value,
                "rejected",
                "",
                {"state_changing_send_attempted": False},
            ),
            worker,
            worker.descriptor,
        )

        self.assertEqual(1, len(started))
        self.window.set_ui_state.assert_not_called()

    def test_accepted_user_refresh_never_publishes_legacy_room_codec_context(self):
        accepted = []
        superseded = []
        self.window.pdu_controller._accepted_refresh_callback = accepted.append
        self.window.pdu_controller._superseded_callback = superseded.append
        self.window.on_device_data_received = Mock()
        started = []

        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append):
            self.window.screens["pdu"].refresh()
            worker = started[-1]

        self.assertEqual([], superseded)
        self.window.on_pdu_refresh_result(
            {
                "device_info": {"model": "IPL T PCS4i"},
                "outlets": [{"number": 1, "status": "on"}],
                "ip_address": "192.0.2.44",
            },
            worker,
            worker.descriptor,
        )

        self.assertEqual([], accepted)

    def test_reconciliation_refresh_does_not_publish_enrichment_trigger(self):
        accepted = []
        self.window.pdu_controller._accepted_refresh_callback = accepted.append
        started = []
        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append), \
                patch.object(QMessageBox, "information"):
            self.assertTrue(self.window.control_pdu_outlet(1, "on"))
            mutation_worker = started[-1]
            self.window.on_pdu_command_result(
                {
                    "success": True,
                    "operation": COMMAND_ON,
                    "outlet_number": 1,
                    "state_changing_send_attempted": True,
                },
                mutation_worker,
                mutation_worker.descriptor,
            )

            reconciliation = started[-1]
            self.window.on_pdu_refresh_result(
                {
                    "device_info": {"model": "IPL T PCS4i"},
                    "outlets": [{"number": 1, "status": "on"}],
                    "ip_address": "192.0.2.44",
                },
                reconciliation,
                reconciliation.descriptor,
            )
            self.window.on_pdu_refresh_finished(reconciliation, reconciliation.descriptor)

        self.assertEqual([], accepted)


if __name__ == "__main__":
    unittest.main()
