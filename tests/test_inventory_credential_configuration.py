import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtWidgets import QApplication, QDialog
except ImportError:  # pragma: no cover
    QApplication = None

from gui.device_model_fallback_dialog import DeviceModelFallbackDialog
from gui.diagnostic_dispatch import (
    DiagnosticActionPurpose,
    ModelResolutionStatus,
    dispatch_model_names,
)


@unittest.skipIf(QApplication is None, "PyQt5 is unavailable")
class DeviceModelFallbackDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_no_first_or_previous_selection_is_accepted(self):
        dialog = DeviceModelFallbackDialog(
            purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
            generation=1,
            binding_id="binding",
            safe_reason="safe reason",
            model_choices=dispatch_model_names(),
        )
        self.addCleanup(dialog.close)
        self.assertIsNone(dialog.selected_model())
        self.assertFalse(dialog.confirm_button.isEnabled())
        dialog.accept()
        self.assertNotEqual(QDialog.Accepted, dialog.result())

    def test_purpose_specific_confirmation_and_selection_payload(self):
        dialog = DeviceModelFallbackDialog(
            purpose=DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION,
            generation=3,
            binding_id="credential:3",
            safe_reason="safe reason",
            model_choices=dispatch_model_names(),
        )
        self.addCleanup(dialog.close)
        self.assertEqual("Продолжить", dialog.confirm_button.text())
        dialog.model_list.setCurrentRow(1)
        self.assertTrue(dialog.confirm_button.isEnabled())
        selection = dialog.selection()
        self.assertEqual(DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION, selection.purpose)
        self.assertEqual(3, selection.generation)
        self.assertEqual("credential:3", selection.binding_id)
        self.assertEqual("Huawei TE40", selection.diagnostic_model)


@unittest.skipIf(QApplication is None, "PyQt5 is unavailable")
class CredentialConfigurationFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_password_action_uses_credential_purpose_generation(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.ip_entry.setText("192.0.2.10")
        generation = window._next_action_generation(
            DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION
        )
        self.assertEqual(generation, window._credential_action_generation)
        self.assertIsNone(window.current_device_name())

    def test_credential_unresolved_outcomes_are_distinct(self):
        from gui.diagnostic_dispatch import resolve_exact_model_for_ip

        result = resolve_exact_model_for_ip(
            purpose=DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION,
            normalized_ip="192.0.2.10",
            inventory=None,
        )
        self.assertEqual(ModelResolutionStatus.INVENTORY_UNAVAILABLE, result.status)
        self.assertEqual(DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION, result.purpose)


if __name__ == "__main__":
    unittest.main()
