import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtCore import QThreadPool
    from PyQt5.QtWidgets import QApplication, QMessageBox
except ImportError:
    QApplication = None

from core.exceptions import CredentialProfileNotFoundError


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

    @staticmethod
    def _missing_mapping(**_kwargs):
        raise CredentialProfileNotFoundError("missing mapping")


if __name__ == "__main__":
    unittest.main()
