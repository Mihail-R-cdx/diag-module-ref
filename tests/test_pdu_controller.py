import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtCore import QThreadPool
    from PyQt5.QtWidgets import QApplication, QMessageBox
except ImportError:
    QApplication = None

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
        self.window.device_combo.setCurrentText("Extron IPL T PCS4i")
        self.window.ip_entry.setText("192.0.2.44")
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


if __name__ == "__main__":
    unittest.main()
