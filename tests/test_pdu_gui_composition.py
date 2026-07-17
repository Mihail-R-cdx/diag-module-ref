import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtCore import QThreadPool
    from PyQt5.QtWidgets import QApplication, QMessageBox
except ImportError:
    QApplication = None

from core.exceptions import CredentialProfileNotFoundError
from core.pdu import COMMAND_ON, PDUOperationDescriptor


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class PDUGuiCompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")

    def setUp(self):
        from gui.main_window import VCSDiagnosticApp

        self.window = VCSDiagnosticApp()
        self.window.show()
        QApplication.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        QApplication.processEvents()

    def test_pcs4i_without_mapping_starts_one_credentialless_attempt(self):
        started = []
        self.window.device_combo.setCurrentText("Extron IPL T PCS4i")
        self.window.ip_entry.setText("192.0.2.44")
        self.window.credential_provider.resolve_candidates = self._missing_mapping
        self.window.ensure_ping_success = lambda _ip: True
        self.window.show_progress_dialog = lambda _message: None

        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append), \
                patch.object(QMessageBox, "warning"):
            self.window.refresh_data()

        self.assertEqual(1, len(started))
        worker = started[0]
        self.assertEqual([{}], worker.creds_list)
        self.assertEqual({}, worker.credentials)
        self.assertIsNone(worker.descriptor.credential_index)

    def test_non_pcs4i_missing_mapping_is_blocked_before_worker_creation(self):
        started = []
        self.window.device_combo.setCurrentText("Aten PE8208AV")
        self.window.ip_entry.setText("192.0.2.45")
        self.window.credential_provider.resolve_candidates = self._missing_mapping

        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append), \
                patch.object(QMessageBox, "warning"):
            self.window.refresh_data()

        self.assertEqual([], started)

    def test_pdu_context_includes_credential_context(self):
        self.window._active_request = {
            "id": 7,
            "device": "Extron IPL T PCS4i",
            "ip": "192.0.2.44",
            "credential_context": 100,
        }

        current = PDUOperationDescriptor(
            operation_id=1,
            generation=7,
            model="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            operation=COMMAND_ON,
            outlet_number=1,
            credential_context=100,
        )
        stale = PDUOperationDescriptor(
            operation_id=2,
            generation=7,
            model="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            operation=COMMAND_ON,
            outlet_number=1,
            credential_context=200,
        )

        self.assertTrue(self.window._pdu_context_is_current(current))
        self.assertFalse(self.window._pdu_context_is_current(stale))

    def test_distinct_pdu_command_operations_get_distinct_ids(self):
        self.window._request_serial = 11

        first = self.window._next_pdu_operation_id()
        second = self.window._next_pdu_operation_id()

        self.assertNotEqual(first, second)

    def test_indeterminate_pdu_command_uses_safe_ui_message(self):
        descriptor = PDUOperationDescriptor(
            operation_id=1,
            generation=3,
            model="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            operation=COMMAND_ON,
            outlet_number=1,
            credential_context=10,
        )
        self.window._active_request = {
            "id": 3,
            "device": "Extron IPL T PCS4i",
            "ip": "192.0.2.44",
            "credential_context": 10,
        }
        self.window.hide_progress_dialog = lambda: None

        with patch.object(QMessageBox, "warning") as warning, patch.object(
            QMessageBox, "critical"
        ) as critical:
            self.window.on_pdu_command_error(
                ("indeterminate_outcome", "raw transport exception", ""),
                SimpleNamespace(),
                descriptor,
            )

        critical.assert_not_called()
        warning.assert_called_once()
        self.assertIn("Не удалось достоверно определить итог команды", warning.call_args.args[2])

    @staticmethod
    def _missing_mapping(**_kwargs):
        raise CredentialProfileNotFoundError("missing mapping")


if __name__ == "__main__":
    unittest.main()
