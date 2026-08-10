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
    def test_bar_and_box_connection_profiles_are_isolated_at_same_ip(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp.__new__(VCSDiagnosticApp)
        window.device_connection_profiles = {}
        VCSDiagnosticApp.set_device_connection_profile(window, "CloudLink Bar 310", {"port": 443}, "192.0.2.10")
        self.assertIsNone(VCSDiagnosticApp.get_device_connection_profile(window, "CloudLink Box 310", "192.0.2.10"))
        VCSDiagnosticApp.set_device_connection_profile(window, "CloudLink Box 310", {"port": 443, "label": "box"}, "192.0.2.10")
        self.assertEqual({"port": 443}, VCSDiagnosticApp.get_device_connection_profile(window, "CloudLink Bar 310", "192.0.2.10"))
        self.assertEqual({"port": 443, "label": "box"}, VCSDiagnosticApp.get_device_connection_profile(window, "CloudLink Box 310", "192.0.2.10"))
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
            0,
            window.get_current_credential_index("Huawei TE40", "192.0.2.10"),
        )
        self.assertNotIn("Huawei TE40|192.0.2.10", window.current_credential_index)
        self.assertEqual(
            {"transport": "ssh"},
            window.get_device_connection_profile("Huawei TE40", "192.0.2.10"),
        )

    def test_password_confirmation_does_not_publish_credential_values(self):
        from PyQt5.QtWidgets import QLineEdit
        from gui.main_window import VCSDiagnosticApp
        from tests.test_inventory_diagnostic_dispatch import inventory, record

        username = "SENTINEL-USERNAME-NOT-FOR-OUTPUT"
        password = "SENTINEL-PASSWORD-NOT-FOR-OUTPUT"
        public_output = []

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.equipment_inventory = inventory(
            [record("A", ip_address="192.0.2.10", diagnostic_model="Huawei TE40")]
        )
        window.ip_entry.setText("192.0.2.10")
        original_set_ui_state = window.set_ui_state

        def capture_state(state, text=None, screen=None):
            if text is not None:
                public_output.append(str(text))
            return original_set_ui_state(state, text, screen)

        def accept_with_sentinel_credentials(dialog):
            entries = dialog.findChildren(QLineEdit)
            entries[0].setText(username)
            entries[1].setText(password)
            return QDialog.Accepted

        def capture_information(_parent, title, text):
            public_output.extend([str(title), str(text)])

        window.set_ui_state = capture_state
        with patch("gui.main_window.QDialog.exec_", accept_with_sentinel_credentials), \
                patch("gui.main_window.QMessageBox.information", capture_information), \
                patch("builtins.print", lambda *args, **_kwargs: public_output.append(" ".join(map(str, args)))):
            window.show_password_dialog()

        self.assertIn(
            {"username": username, "password": password},
            window.device_credentials["Huawei TE40"],
        )
        rendered = "\n".join(public_output)
        self.assertNotIn(username, rendered)
        self.assertNotIn(password, rendered)

    def test_password_configuration_does_not_ping(self):
        from PyQt5.QtWidgets import QLineEdit
        from gui.main_window import VCSDiagnosticApp
        from tests.test_inventory_diagnostic_dispatch import inventory, record

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.equipment_inventory = inventory(
            [record("A", ip_address="192.0.2.44", diagnostic_model="Aten PE8208AV")]
        )
        window.ip_entry.setText("192.0.2.44")
        window.ensure_ping_success = Mock(side_effect=AssertionError("credential config must not ping"))
        window.configure_credential_candidate = Mock(return_value=True)

        def accept_with_credentials(dialog):
            entries = dialog.findChildren(QLineEdit)
            entries[0].setText("operator")
            entries[1].setText("secret-password")
            return QDialog.Accepted

        with patch("gui.main_window.QDialog.exec_", accept_with_credentials), \
                patch("gui.main_window.QMessageBox.information"), \
                patch("builtins.print"):
            window.show_password_dialog()

        window.ensure_ping_success.assert_not_called()
        window.configure_credential_candidate.assert_called_once()

    def test_pdu_credential_configuration_error_title_is_not_mojibake(self):
        import inspect
        import gui.main_window as main_window
        from core.exceptions import CredentialConfigurationError
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window._resolve_pdu_attempt_credentials = Mock(
            side_effect=CredentialConfigurationError("safe error")
        )
        with patch("gui.main_window.QMessageBox.warning") as warning:
            prepared = window._prepare_diagnostic_credentials_before_reachability(
                device_name="Aten PE8208AV",
                ip_address="192.0.2.44",
            )

        self.assertFalse(prepared)
        self.assertEqual("Настройка credentials", warning.call_args.args[1])
        source = inspect.getsource(
            main_window.VCSDiagnosticApp._prepare_diagnostic_credentials_before_reachability
        )
        for marker in ("Р Сњ", "Р В°", "РЎРѓ", "РЎвЂљ"):
            self.assertNotIn(marker, source)

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
            0,
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

    def test_generic_credential_store_mutation_does_not_globally_invalidate(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window._related_codec_credential_context_revision = 3
        window._equipment_room_credential_context_revision = 4
        window._matrix_credential_context_revision = 5
        window._invalidate_pdu_context = Mock()
        window._publish_current_equipment_room_context = Mock()
        window.pdu_room_codec_enrichment_controller.invalidate_context = Mock()
        window.matrix_controller.invalidate_context = Mock()

        window.device_credentials["Huawei TE40"] = [
            {"username": "operator", "password": "secret"}
        ]
        window.device_credentials.setdefault("Aten PE8208AV", [{"password": "secret"}])

        self.assertEqual(3, window._related_codec_credential_context_revision)
        self.assertEqual(4, window._equipment_room_credential_context_revision)
        self.assertEqual(5, window._matrix_credential_context_revision)
        window._invalidate_pdu_context.assert_not_called()
        window._publish_current_equipment_room_context.assert_not_called()
        window.pdu_room_codec_enrichment_controller.invalidate_context.assert_not_called()
        window.matrix_controller.invalidate_context.assert_not_called()

    def test_scoped_credential_mutation_invalidates_only_exact_context(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.current_credential_index["Huawei TE40|192.0.2.10"] = 2
        window.device_connection_profiles[("Huawei TE40", "192.0.2.10")] = {"transport": "ssh"}
        window._active_request = {
            "id": 1,
            "device": "Aten PE8208AV",
            "ip": "192.0.2.44",
            "screen": None,
        }
        window._invalidate_pdu_context = Mock()

        inserted = window.configure_credential_candidate(
            "Huawei TE40",
            "192.0.2.10",
            {"username": "operator", "password": "secret"},
        )

        self.assertTrue(inserted)
        window._invalidate_pdu_context.assert_not_called()
        self.assertEqual(0, window.get_current_credential_index("Huawei TE40", "192.0.2.10"))
        self.assertNotIn("Huawei TE40|192.0.2.10", window.current_credential_index)
        self.assertEqual(
            {"transport": "ssh"},
            window.get_device_connection_profile("Huawei TE40", "192.0.2.10"),
        )

        window.configure_credential_candidate(
            "Aten PE8208AV",
            "192.0.2.44",
            {"username": "operator", "password": "secret"},
        )
        window._invalidate_pdu_context.assert_called_once()

    def test_candidate_reorder_remaps_successful_identity_on_promote_and_insert(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.device_credentials["Huawei TE40"] = [
            {"username": "a", "password": "a"},
            {"username": "b", "password": "b"},
        ]
        window.current_credential_index["Huawei TE40|192.0.2.10"] = 1

        inserted = window.configure_credential_candidate(
            "Huawei TE40",
            "192.0.2.10",
            {"username": "b", "password": "b"},
        )

        self.assertFalse(inserted)
        self.assertEqual(
            [{"username": "b", "password": "b"}, {"username": "a", "password": "a"}],
            window.device_credentials["Huawei TE40"],
        )
        self.assertEqual(0, window.get_current_credential_index("Huawei TE40", "192.0.2.10"))

        window.device_credentials["Huawei TE40"] = [
            {"username": "a", "password": "a"},
            {"username": "b", "password": "b"},
        ]
        window.current_credential_index["Huawei TE40|192.0.2.10"] = 1
        inserted = window.configure_credential_candidate(
            "Huawei TE40",
            "192.0.2.10",
            {"username": "c", "password": "c"},
        )

        self.assertTrue(inserted)
        self.assertEqual(2, window.get_current_credential_index("Huawei TE40", "192.0.2.10"))

    def test_candidate_reorder_preserves_multiple_ip_success_identities(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.device_credentials["Huawei TE40"] = [
            {"username": "a", "password": "a"},
            {"username": "b", "password": "b"},
            {"username": "c", "password": "c"},
        ]
        window.current_credential_index["Huawei TE40|192.0.2.10"] = 0
        window.current_credential_index["Huawei TE40|192.0.2.11"] = 1
        window.device_connection_profiles[("Huawei TE40", "192.0.2.10")] = {"transport": "https"}

        window.configure_credential_candidate(
            "Huawei TE40",
            "192.0.2.12",
            {"username": "b", "password": "b"},
        )

        self.assertEqual(1, window.get_current_credential_index("Huawei TE40", "192.0.2.10"))
        self.assertEqual(0, window.get_current_credential_index("Huawei TE40", "192.0.2.11"))
        self.assertNotIn("Huawei TE40|192.0.2.12", window.current_credential_index)
        self.assertEqual(
            {"transport": "https"},
            window.get_device_connection_profile("Huawei TE40", "192.0.2.10"),
        )
        self.assertIsNone(window.get_device_connection_profile("Huawei TE40", "192.0.2.12"))

    def test_candidate_reorder_deletes_ambiguous_invalid_or_removed_success_identity(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.device_credentials["Huawei TE40"] = [
            {"username": "dup", "password": "same"},
            {"username": "dup", "password": "same"},
            {"username": "gone", "password": "gone"},
        ]
        window.current_credential_index["Huawei TE40|192.0.2.10"] = 0
        window.current_credential_index["Huawei TE40|192.0.2.11"] = 9
        window.current_credential_index["Huawei TE40|192.0.2.12"] = 2

        window.configure_credential_candidate(
            "Huawei TE40",
            "192.0.2.10",
            {"username": "new", "password": "new"},
        )

        self.assertNotIn("Huawei TE40|192.0.2.10", window.current_credential_index)
        self.assertNotIn("Huawei TE40|192.0.2.11", window.current_credential_index)
        self.assertEqual(3, window.get_current_credential_index("Huawei TE40", "192.0.2.12"))

        window.device_credentials["Huawei TE40"] = [
            {"username": "a", "password": "a"},
            {"username": "b", "password": "b"},
        ]
        window.current_credential_index["Huawei TE40|192.0.2.13"] = 1
        window._remap_successful_credential_indexes_after_reorder(
            "Huawei TE40",
            [{"username": "a", "password": "a"}, {"username": "b", "password": "b"}],
            [{"username": "a", "password": "a"}],
        )
        self.assertNotIn("Huawei TE40|192.0.2.13", window.current_credential_index)

    def test_attempt_plan_starts_with_remapped_successful_candidate(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.device_credentials["Huawei TE40"] = [
            {"username": "a", "password": "a"},
            {"username": "b", "password": "b"},
        ]
        window.current_credential_index["Huawei TE40|192.0.2.10"] = 1

        window.configure_credential_candidate(
            "Huawei TE40",
            "192.0.2.10",
            {"username": "b", "password": "b"},
        )
        plan = window._credential_attempt_plan(
            "Huawei TE40",
            window.device_credentials["Huawei TE40"],
            "192.0.2.10",
        )

        self.assertEqual(0, plan.current_index)
        self.assertEqual({"username": "b", "password": "b"}, plan.current_candidate)

    def test_scoped_pdu_mutation_discards_only_exact_model_ip_attempt_plan(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window._credential_attempt_plan(
            "Aten PE8208AV",
            [{"username": "a", "password": "a"}],
            "192.0.2.44",
        )
        window._credential_attempt_plan(
            "Aten PE8208AV",
            [{"username": "b", "password": "b"}],
            "192.0.2.45",
        )
        window._credential_attempt_plan(
            "Extron IPL T PCS4i",
            [{"password": "c"}],
            "192.0.2.44",
        )

        window.configure_credential_candidate(
            "Aten PE8208AV",
            "192.0.2.44",
            {"username": "operator", "password": "secret"},
        )

        self.assertNotIn("Aten PE8208AV|192.0.2.44", window._credential_attempt_plans)
        self.assertIn("Aten PE8208AV|192.0.2.45", window._credential_attempt_plans)
        self.assertIn("Extron IPL T PCS4i|192.0.2.44", window._credential_attempt_plans)


if __name__ == "__main__":
    unittest.main()
