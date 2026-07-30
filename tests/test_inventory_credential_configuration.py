import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtWidgets import QApplication, QDialog
except ImportError:  # pragma: no cover
    QApplication = None

from gui.device_model_fallback_dialog import DeviceModelFallbackDialog
from gui.diagnostic_dispatch import (
    ActionBinding,
    DiagnosticActionPurpose,
    ModelResolutionStatus,
    dispatch_model_names,
)


def binding_for(purpose, generation=1, *, ip="192.0.2.10", fallback_dialog_id=None):
    return ActionBinding(
        purpose=purpose,
        generation=generation,
        normalized_ip=ip,
        inventory_context_identity="sha256:" + "2" * 64,
        resolution_status=ModelResolutionStatus.IP_NOT_FOUND.value,
        selection_source=None,
        accepted_model=None,
        screen_key=None,
        lifecycle_route=None,
        fallback_dialog_id=fallback_dialog_id,
        credential_dialog_id=None,
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
            binding_id=binding_for(DiagnosticActionPurpose.DIAGNOSTIC_START),
            safe_reason="safe reason",
            model_choices=dispatch_model_names(),
        )
        self.addCleanup(dialog.close)
        self.assertIsNone(dialog.selected_model())
        self.assertFalse(dialog.confirm_button.isEnabled())
        dialog.accept()
        self.assertNotEqual(QDialog.Accepted, dialog.result())

    def test_purpose_specific_confirmation_and_selection_payload(self):
        binding = binding_for(
            DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION,
            generation=3,
            fallback_dialog_id=7,
        )
        dialog = DeviceModelFallbackDialog(
            purpose=DiagnosticActionPurpose.CREDENTIAL_CONFIGURATION,
            generation=3,
            binding_id=binding,
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
        self.assertIs(binding, selection.binding_id)
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

    def test_password_confirmation_adds_candidate_without_success_index_or_profile(self):
        from PyQt5.QtWidgets import QLineEdit
        from gui.main_window import VCSDiagnosticApp
        from tests.test_inventory_diagnostic_dispatch import inventory, record

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.equipment_inventory = inventory(
            [record("A", ip_address="192.0.2.10", diagnostic_model="Huawei TE40")]
        )
        window.ip_entry.setText("192.0.2.10")
        window.current_credential_index["Huawei TE40|192.0.2.10"] = 2
        window.device_connection_profiles[("Huawei TE40", "192.0.2.10")] = {"transport": "ssh"}

        def accept_with_credentials(dialog):
            entries = dialog.findChildren(QLineEdit)
            entries[0].setText("operator")
            entries[1].setText("secret-password")
            return QDialog.Accepted

        with patch("gui.main_window.QDialog.exec_", accept_with_credentials), \
                patch("gui.main_window.QMessageBox.information"):
            window.show_password_dialog()

        self.assertEqual(
            [{"username": "operator", "password": "secret-password"}],
            window.device_credentials["Huawei TE40"],
        )
        self.assertEqual(
            2,
            window.get_current_credential_index("Huawei TE40", "192.0.2.10"),
        )
        self.assertEqual(
            {"transport": "ssh"},
            window.get_device_connection_profile("Huawei TE40", "192.0.2.10"),
        )

    def test_password_confirmation_promotes_existing_candidate_without_success_index(self):
        from PyQt5.QtWidgets import QLineEdit
        from gui.main_window import VCSDiagnosticApp
        from tests.test_inventory_diagnostic_dispatch import inventory, record

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.equipment_inventory = inventory(
            [record("A", ip_address="192.0.2.10", diagnostic_model="Huawei TE40")]
        )
        window.ip_entry.setText("192.0.2.10")
        window.device_credentials["Huawei TE40"] = [
            {"username": "first", "password": "first-password"},
            {"username": "operator", "password": "secret-password"},
        ]
        window.current_credential_index["Huawei TE40|192.0.2.10"] = 1

        def accept_with_existing_credentials(dialog):
            entries = dialog.findChildren(QLineEdit)
            entries[0].setText("operator")
            entries[1].setText("secret-password")
            return QDialog.Accepted

        with patch("gui.main_window.QDialog.exec_", accept_with_existing_credentials), \
                patch("gui.main_window.QMessageBox.information"):
            window.show_password_dialog()

        self.assertEqual(
            [
                {"username": "operator", "password": "secret-password"},
                {"username": "first", "password": "first-password"},
            ],
            window.device_credentials["Huawei TE40"],
        )
        self.assertEqual(
            1,
            window.get_current_credential_index("Huawei TE40", "192.0.2.10"),
        )

    def test_stale_credential_dialog_does_not_mutate_candidates_index_or_profile(self):
        from PyQt5.QtWidgets import QLineEdit
        from gui.main_window import VCSDiagnosticApp
        from tests.test_inventory_diagnostic_dispatch import inventory, record

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.equipment_inventory = inventory(
            [record("A", ip_address="192.0.2.10", diagnostic_model="Huawei TE40")]
        )
        window.ip_entry.setText("192.0.2.10")
        window.device_credentials["Huawei TE40"] = [
            {"username": "first", "password": "first-password"}
        ]
        window.current_credential_index["Huawei TE40|192.0.2.10"] = 1
        window.device_connection_profiles[("Huawei TE40", "192.0.2.10")] = {"transport": "ssh"}

        def accept_after_ip_change(dialog):
            entries = dialog.findChildren(QLineEdit)
            entries[0].setText("operator")
            entries[1].setText("secret-password")
            window.ip_entry.setText("192.0.2.99")
            return QDialog.Accepted

        with patch("gui.main_window.QDialog.exec_", accept_after_ip_change), \
                patch("gui.main_window.QMessageBox.information") as information:
            window.show_password_dialog()

        self.assertEqual(
            [{"username": "first", "password": "first-password"}],
            window.device_credentials["Huawei TE40"],
        )
        self.assertEqual(
            1,
            window.get_current_credential_index("Huawei TE40", "192.0.2.10"),
        )
        self.assertEqual(
            {"transport": "ssh"},
            window.get_device_connection_profile("Huawei TE40", "192.0.2.10"),
        )
        information.assert_not_called()

    def test_exact_credential_invalidation_preserves_unrelated_contexts(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window._active_request = {
            "id": 1,
            "device": "Aten PE8208AV",
            "ip": "192.0.2.44",
            "screen": None,
        }
        window._equipment_room_context_binding = (
            "Extron IN1804",
            "192.0.2.55",
            "snapshot",
            "matrix",
            0,
        )
        window._related_codec_credential_context_revision = 3
        window._equipment_room_credential_context_revision = 4
        window._invalidate_pdu_context = Mock()
        window._publish_current_equipment_room_context = Mock()
        window.pdu_room_codec_enrichment_controller.invalidate_context = Mock()
        window.matrix_controller.invalidate_context = Mock()

        window._on_credential_configuration_changed("Huawei TE40", "192.0.2.10")

        self.assertEqual(3, window._related_codec_credential_context_revision)
        self.assertEqual(4, window._equipment_room_credential_context_revision)
        window._invalidate_pdu_context.assert_not_called()
        window._publish_current_equipment_room_context.assert_not_called()
        window.pdu_room_codec_enrichment_controller.invalidate_context.assert_not_called()
        window.matrix_controller.invalidate_context.assert_not_called()

    def test_exact_credential_invalidation_affects_matching_context(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window._active_request = {
            "id": 1,
            "device": "Aten PE8208AV",
            "ip": "192.0.2.44",
            "screen": None,
        }
        window._invalidate_pdu_context = Mock()

        window._on_credential_configuration_changed("Aten PE8208AV", "192.0.2.44")

        window._invalidate_pdu_context.assert_called_once()


if __name__ == "__main__":
    unittest.main()
