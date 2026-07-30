import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtCore import QThreadPool
    from PyQt5.QtWidgets import QApplication, QMessageBox
except ImportError:
    QApplication = None

from core.exceptions import CredentialProfileNotFoundError
from core.pdu import (
    BULK_COMMAND_OFF,
    BULK_COMMAND_ON,
    COMMAND_OFF,
    COMMAND_ON,
    PDUOperationDescriptor,
    REFRESH,
    execute_pdu_command,
)


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
        self.window.ip_entry.setText("192.0.2.44")
        self.window._accept_test_diagnostic_model("Extron IPL T PCS4i")
        self.window.credential_provider.resolve_candidates = self._missing_mapping
        self.window.ensure_ping_success = lambda _ip: True
        self.window.show_progress_dialog = lambda _message: None

        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append), \
                patch.object(QMessageBox, "warning"):
            self.window.refresh_data()

        self.assertEqual(1, len(started))
        worker = started[0]
        self.assertFalse(hasattr(worker, "creds_list"))
        self.assertFalse(hasattr(worker, "current_idx"))
        self.assertEqual({}, worker.credentials)
        self.assertIsNone(worker.descriptor.credential_index)

    def test_non_pcs4i_missing_mapping_is_blocked_before_worker_creation(self):
        started = []
        self.window.ip_entry.setText("192.0.2.45")
        self.window._accept_test_diagnostic_model("Aten PE8208AV")
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
        self.window.refresh_data = Mock()

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
        self.window.refresh_data.assert_not_called()

    def test_pcs4i_on_auth_failure_retries_same_command_next_candidate(self):
        self._assert_pcs4i_command_auth_retry(COMMAND_ON, 2)

    def test_pcs4i_off_auth_failure_retries_same_command_next_candidate(self):
        self._assert_pcs4i_command_auth_retry(COMMAND_OFF, 3)

    def _assert_pcs4i_command_auth_retry(self, command, outlet_number):
        descriptor = PDUOperationDescriptor(
            operation_id=42,
            generation=9,
            model="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            operation=command,
            outlet_number=outlet_number,
            credential_index=0,
            credential_context=self.window._pdu_context_token(),
        )
        self.window._active_request = {
            "id": 9,
            "device": "Extron IPL T PCS4i",
            "ip": "192.0.2.44",
            "credential_context": descriptor.credential_context,
            "credential_index": descriptor.credential_index,
        }
        creds = [
            {"password": "synthetic-password-a"},
            {"password": "synthetic-password-b"},
        ]
        self._seed_pdu_attempt(descriptor, creds, 0, "individual")
        worker = SimpleNamespace(
            device_name="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
        )
        self.window.current_worker = worker
        self.window.hide_progress_dialog = Mock()
        started = []

        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append):
            self.window.on_pdu_command_error(
                (
                    "authentication_error",
                    "rejected",
                    "",
                    {"state_changing_send_attempted": False},
                ),
                worker,
                descriptor,
            )

        self.assertEqual(1, len(started))
        retry = started[0]
        self.assertEqual(42, retry.descriptor.operation_id)
        self.assertEqual(command, retry.descriptor.operation)
        self.assertEqual(outlet_number, retry.descriptor.outlet_number)
        self.assertEqual(1, retry.descriptor.credential_index)
        self.assertFalse(hasattr(retry, "creds_list"))
        self.assertFalse(hasattr(retry, "current_idx"))
        self.assertEqual({"password": "synthetic-password-b"}, retry.credentials)
        self.assertNotIn("username", retry.credentials)
        self.assertEqual({}, self.window.current_credential_index)

    def test_pcs4i_command_indeterminate_does_not_retry_credentials(self):
        descriptor = PDUOperationDescriptor(
            operation_id=1,
            generation=3,
            model="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            operation=COMMAND_ON,
            outlet_number=1,
            credential_context=self.window._pdu_context_token(),
        )
        self.window._active_request = {
            "id": 3,
            "device": "Extron IPL T PCS4i",
            "ip": "192.0.2.44",
            "credential_context": descriptor.credential_context,
            "credential_index": descriptor.credential_index,
        }
        worker = SimpleNamespace(
            device_name="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
        )
        self.window.current_worker = worker
        self.window.hide_progress_dialog = Mock()
        self.window.refresh_data = Mock()

        with patch.object(QThreadPool.globalInstance(), "start") as start, \
                patch.object(QMessageBox, "warning"):
            self.window.on_pdu_command_error(
                ("indeterminate_outcome", "unknown", ""),
                worker,
                descriptor,
            )

        start.assert_not_called()
        self.window.refresh_data.assert_not_called()
        self.assertNotIn("Extron IPL T PCS4i|192.0.2.44", self.window._credential_attempt_plans)

    def test_pcs4i_command_auth_after_possible_send_does_not_retry_or_advance(self):
        descriptor = PDUOperationDescriptor(
            operation_id=43,
            generation=10,
            model="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            operation=COMMAND_ON,
            outlet_number=1,
            credential_index=0,
            credential_context=self.window._pdu_context_token(),
        )
        self._activate_pdu_request(descriptor)
        worker = SimpleNamespace(
            device_name="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
        )
        self.window.current_worker = worker
        self.window.hide_progress_dialog = Mock()
        self.window.refresh_data = Mock()

        with patch.object(QThreadPool.globalInstance(), "start") as start, \
                patch.object(QMessageBox, "critical"):
            self.window.on_pdu_command_error(
                (
                    "authentication_error",
                    "post-send auth",
                    "",
                    {"state_changing_send_attempted": True},
                ),
                worker,
                descriptor,
            )

        start.assert_not_called()
        self.window.refresh_data.assert_not_called()
        self.assertNotIn(
            "Extron IPL T PCS4i|192.0.2.44|operation:43",
            self.window._credential_attempt_plans,
        )
        self.assertEqual({}, self.window.current_credential_index)

    def test_stale_pdu_refresh_result_is_ignored_after_context_change(self):
        descriptor = self._pdu_descriptor(REFRESH, operation_id=10, generation=4, context=30)
        worker = SimpleNamespace(device_name="Extron IPL T PCS4i")
        self._activate_pdu_request(descriptor)
        self.window._invalidate_pdu_context()
        self.window._active_request["credential_context"] = self.window._pdu_context_token()
        self.window.on_device_data_received = Mock()
        self.window.set_current_credential_index = Mock()

        self.window.on_pdu_refresh_result({"outlets": []}, worker, descriptor)

        self.window.on_device_data_received.assert_not_called()
        self.window.set_current_credential_index.assert_not_called()

    def test_stale_pdu_refresh_auth_error_does_not_retry_or_update_ui(self):
        descriptor = self._pdu_descriptor(REFRESH, operation_id=11, generation=5, context=40)
        worker = SimpleNamespace(device_name="Extron IPL T PCS4i")
        self._activate_pdu_request(descriptor)
        self.window._invalidate_pdu_context()
        self.window._active_request["credential_context"] = self.window._pdu_context_token()
        self.window.on_device_error = Mock()

        with patch.object(QThreadPool.globalInstance(), "start") as start:
            self.window.on_pdu_refresh_error(
                ("authentication_error", "stale auth failure", ""),
                worker,
                descriptor,
            )

        self.window.on_device_error.assert_not_called()
        start.assert_not_called()

    def test_stale_pdu_refresh_finished_does_not_restore_controls(self):
        descriptor = self._pdu_descriptor(REFRESH, operation_id=12, generation=6, context=50)
        worker = SimpleNamespace(device_name="Extron IPL T PCS4i")
        self._activate_pdu_request(descriptor)
        self.window._invalidate_pdu_context()
        self.window._active_request["credential_context"] = self.window._pdu_context_token()
        self.window.on_worker_finished = Mock()

        self.window.on_pdu_refresh_finished(worker, descriptor)

        self.window.on_worker_finished.assert_not_called()

    def test_refresh_pdu_production_binding_ignores_stale_result_and_error(self):
        started = []
        self.window._accept_test_diagnostic_model("Extron IPL T PCS4i")
        self.window._begin_request(
            "Extron IPL T PCS4i",
            "192.0.2.44",
            self.window.screens["pdu"],
        )
        self.window._active_request_credentials = [{}]
        self.window.show_progress_dialog = Mock()
        self.window.on_device_data_received = Mock()
        self.window.on_device_error = Mock()

        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append):
            self.window.refresh_pdu("192.0.2.44", "Extron IPL T PCS4i")

        self.assertEqual(1, len(started))
        worker = started[0]
        self.window._invalidate_pdu_context()
        self.window._active_request["credential_context"] = self.window._pdu_context_token()

        worker.signals.result.emit({"outlets": [], "ip_address": "192.0.2.44"})
        worker.signals.error.emit(("authentication_error", "stale", ""))
        QApplication.processEvents()

        self.window.on_device_data_received.assert_not_called()
        self.window.on_device_error.assert_not_called()
        self.assertEqual(1, len(started))

    def test_biamp_refresh_uses_generic_worker_binding(self):
        started = []
        self.window._accept_test_diagnostic_model("Biamp Tesira Forte CI")
        self.window.device_credentials["Biamp Tesira Forte CI"] = [
            {"username": "synthetic-user", "password": "synthetic-password"}
        ]
        self.window.show_progress_dialog = Mock()
        self.window.show_codec_poll_terminal = Mock()
        self.window._bind_worker = Mock()
        self.window._bind_pdu_refresh_worker = Mock(
            side_effect=AssertionError("Biamp refresh must not use PDU binding")
        )

        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append):
            self.window.refresh_biamp_tesira_forte_ci("192.0.2.46")

        self.window._bind_worker.assert_called_once_with(started[0])
        self.window._bind_pdu_refresh_worker.assert_not_called()
        self.assertEqual(1, len(started))

    def test_huawei_bar310_refresh_uses_generic_worker_binding(self):
        started = []
        self.window._accept_test_diagnostic_model("CloudLink Bar 310")
        self.window.device_credentials["CloudLink Bar 310"] = [
            {"username": "synthetic-user", "password": "synthetic-password"}
        ]
        self.window.show_progress_dialog = Mock()
        self.window.show_codec_poll_terminal = Mock()
        self.window._bind_worker = Mock()
        self.window._bind_pdu_refresh_worker = Mock(
            side_effect=AssertionError("Bar 310 refresh must not use PDU binding")
        )

        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append):
            self.window.refresh_huawei_bar310("192.0.2.47")

        self.window._bind_worker.assert_called_once_with(started[0])
        self.window._bind_pdu_refresh_worker.assert_not_called()
        self.assertEqual(1, len(started))

    def test_pcs4i_command_plan_is_discarded_after_indeterminate_operation(self):
        creds = [{"password": "a"}, {"password": "b"}]
        self.window.set_current_credential_index("Extron IPL T PCS4i", 0, "192.0.2.44")
        self.assertEqual(
            1,
            self.window._advance_request_credential_attempt(
                "Extron IPL T PCS4i",
                creds,
                "192.0.2.44",
                0,
                101,
            ),
        )
        descriptor = self._pdu_descriptor(COMMAND_ON, operation_id=101, generation=7, context=60)
        self._activate_pdu_request(descriptor)
        self.window.hide_progress_dialog = Mock()
        self.window.refresh_data = Mock()

        with patch.object(QMessageBox, "warning"):
            self.window.on_pdu_command_error(
                ("indeterminate_outcome", "unknown", ""),
                SimpleNamespace(device_name="Extron IPL T PCS4i"),
                descriptor,
            )

        self.assertNotIn(
            "Extron IPL T PCS4i|192.0.2.44|operation:101",
            self.window._credential_attempt_plans,
        )
        self.assertEqual(
            0,
            self.window._credential_attempt_index(
                "Extron IPL T PCS4i",
                creds,
                "192.0.2.44",
                102,
            ),
        )
        self.window.refresh_data.assert_not_called()

    def test_pcs4i_success_persists_used_candidate_for_next_operation(self):
        self.window.set_current_credential_index("Extron IPL T PCS4i", 0, "192.0.2.44")
        descriptor = self._pdu_descriptor(
            COMMAND_ON,
            operation_id=201,
            generation=8,
            context=70,
            credential_index=1,
        )
        self._activate_pdu_request(descriptor)
        self.window.hide_progress_dialog = Mock()
        self.window.refresh_data = Mock()

        with patch.object(QMessageBox, "information"):
            self.window.on_pdu_command_result(
                {
                    "success": True,
                    "operation": COMMAND_ON,
                    "outlet_number": 1,
                    "_credential_used": True,
                },
                SimpleNamespace(),
                descriptor,
            )

        self.assertEqual(
            1,
            self.window.get_current_credential_index(
                "Extron IPL T PCS4i",
                "192.0.2.44",
            ),
        )
        self.assertEqual(
            1,
            self.window._credential_attempt_index(
                "Extron IPL T PCS4i",
                [{"password": "a"}, {"password": "b"}],
                "192.0.2.44",
                202,
            ),
        )

    def test_pcs4i_command_auth_retry_does_not_require_current_worker_identity(self):
        descriptor = self._pdu_descriptor(
            COMMAND_OFF,
            operation_id=301,
            generation=9,
            context=80,
            credential_index=0,
        )
        self._activate_pdu_request(descriptor)
        self._seed_pdu_attempt(
            descriptor,
            [{"password": "a"}, {"password": "b"}],
            0,
            "individual",
        )
        worker = SimpleNamespace(
            device_name="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
        )
        self.window.current_worker = SimpleNamespace()
        self.window.hide_progress_dialog = Mock()

        with patch.object(QThreadPool.globalInstance(), "start") as start:
            self.window.on_pdu_command_error(
                (
                    "authentication_error",
                    "rejected",
                    "",
                    {"state_changing_send_attempted": False},
                ),
                worker,
                descriptor,
            )

        start.assert_called_once()
        self.assertEqual(301, start.call_args.args[0].descriptor.operation_id)
        self.assertEqual(1, start.call_args.args[0].descriptor.credential_index)

    def test_ip_change_invalidates_queued_pdu_operation(self):
        self.window._pdu_context_revision = 10
        self.window._active_request = {
            "id": 7,
            "device": "Extron IPL T PCS4i",
            "ip": "192.0.2.44",
            "credential_context": 10,
            "credential_index": None,
        }
        descriptor = PDUOperationDescriptor(
            operation_id=1,
            generation=7,
            model="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            operation=COMMAND_ON,
            outlet_number=1,
            credential_context=10,
        )

        self.window.ip_entry.setText("192.0.2.45")

        self.assertFalse(self.window._pdu_context_is_current(descriptor))

    def test_same_credentials_list_mutation_invalidates_old_descriptor(self):
        creds = [{"password": "old"}]
        self.window._active_request_credentials = creds
        self.window._pdu_context_revision = 20
        self.window._active_request = {
            "id": 8,
            "device": "Extron IPL T PCS4i",
            "ip": "192.0.2.44",
            "credential_context": 20,
            "credential_index": None,
        }
        descriptor = PDUOperationDescriptor(
            operation_id=1,
            generation=8,
            model="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            operation=COMMAND_ON,
            outlet_number=1,
            credential_context=20,
        )

        creds.insert(0, {"password": "new"})
        self.window._invalidate_pdu_context()
        self.window._active_request["credential_context"] = self.window._pdu_context_token()

        self.assertFalse(self.window._pdu_context_is_current(descriptor))

    def test_pdu_credential_replacement_discards_cached_credentials_for_new_command(self):
        old_credential = {"password": "credential-a"}
        new_credential = {"password": "credential-b"}
        self.window.ip_entry.setText("192.0.2.44")
        self.window._accept_test_diagnostic_model("Extron IPL T PCS4i")
        self.window.show_progress_dialog = lambda _message: None
        self.window._request_serial = 8
        self.window._pdu_context_revision = 20
        self.window._active_request_credentials = [old_credential]
        self.window._active_request = {
            "id": 8,
            "device": "Extron IPL T PCS4i",
            "ip": "192.0.2.44",
            "credential_context": 20,
            "credential_index": 0,
        }
        old_descriptor = PDUOperationDescriptor(
            operation_id=1,
            generation=8,
            model="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            operation=COMMAND_ON,
            outlet_number=1,
            credential_index=0,
            credential_context=20,
        )
        self.window._credential_attempt_plan(
            "Extron IPL T PCS4i",
            [old_credential],
            "192.0.2.44",
            old_descriptor.operation_id,
        )

        self.window.device_credentials["Extron IPL T PCS4i"] = [new_credential]

        acquired = []
        result = execute_pdu_command(
            descriptor=old_descriptor,
            credentials=old_credential,
            is_current=self.window._pdu_context_is_current,
            handler_factory=lambda *_args: acquired.append(True),
        )
        self.assertEqual({"_outcome": "stale", "operation": COMMAND_ON}, result)
        self.assertEqual([], acquired)
        self.assertNotIn("_active_request_credentials", self.window.__dict__)
        self.assertNotIn(
            "Extron IPL T PCS4i|192.0.2.44|operation:1",
            self.window._credential_attempt_plans,
        )

        started = []
        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append):
            self.assertTrue(self.window.control_pdu_outlet(1, "on"))

        self.assertEqual(1, len(started))
        worker = started[0]
        self.assertTrue(self.window._pdu_context_is_current(worker.descriptor))
        self.assertEqual(new_credential, worker.credentials)
        self.assertNotEqual(old_credential, worker.credentials)

    def test_pdu_credential_chain_replacement_discards_obsolete_attempt_plan(self):
        old_chain = [{"password": "credential-a"}, {"password": "credential-b"}]
        new_chain = [{"password": "credential-c"}, {"password": "credential-d"}]
        self.window.ip_entry.setText("192.0.2.44")
        self.window._accept_test_diagnostic_model("Extron IPL T PCS4i")
        self.window.show_progress_dialog = lambda _message: None
        self.window.validate_ip_address = lambda _ip: True
        self.window._active_request_credentials = old_chain
        self.window._credential_attempt_plan(
            "Extron IPL T PCS4i",
            old_chain,
            "192.0.2.44",
        )
        self.window._advance_request_credential_attempt(
            "Extron IPL T PCS4i",
            old_chain,
            "192.0.2.44",
            0,
        )
        self.assertEqual(
            1,
            self.window._credential_attempt_plans[
                "Extron IPL T PCS4i|192.0.2.44"
            ].current_index,
        )

        self.window.device_credentials["Extron IPL T PCS4i"] = new_chain

        self.assertNotIn("_active_request_credentials", self.window.__dict__)
        self.assertNotIn(
            "Extron IPL T PCS4i|192.0.2.44",
            self.window._credential_attempt_plans,
        )
        started = []
        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append):
            self.window.refresh_pdu("192.0.2.44", "Extron IPL T PCS4i")

        self.assertEqual(1, len(started))
        worker = started[0]
        self.assertFalse(hasattr(worker, "creds_list"))
        self.assertFalse(hasattr(worker, "current_idx"))
        self.assertEqual(new_chain[0], worker.credentials)
        self.assertNotIn(worker.credentials, old_chain)

    def test_bulk_dispatch_starts_one_worker_with_immutable_ordered_sequence_and_lock(self):
        started = []
        self.window.ip_entry.setText("192.0.2.44")
        self.window._accept_test_diagnostic_model("Extron IPL T PCS4i")
        self.window.show_progress_dialog = Mock()
        self.window._active_request_credentials = [{}]
        self.window._active_request = {
            "id": 12,
            "device": "Extron IPL T PCS4i",
            "ip": "192.0.2.44",
            "credential_context": self.window._pdu_context_token(),
            "credential_index": None,
        }
        screen = self.window.screens["pdu"]
        self._mark_pdu_outlets_current(
            "Extron IPL T PCS4i",
            "192.0.2.44",
            12,
            self.window._pdu_context_token(),
            None,
            [{"number": 2, "status": "off"}, {"number": 1, "status": "off"}],
            {"on": True, "off": True, "reboot": False},
        )

        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append):
            self.assertTrue(self.window.control_pdu_outlets_bulk("on"))

        self.assertEqual(1, len(started))
        worker = started[0]
        self.assertEqual(BULK_COMMAND_ON, worker.descriptor.operation)
        self.assertEqual((1, 2), worker.descriptor.outlet_sequence)
        self.assertTrue(screen.bulk_busy)
        self.assertFalse(screen.btn_bulk_on.isEnabled())
        self.assertFalse(screen.btn_bulk_off.isEnabled())

        screen.outlets[0]["number"] = 4
        self.assertEqual((1, 2), worker.descriptor.outlet_sequence)

    def test_bulk_lock_blocks_parallel_bulk_and_individual_command(self):
        started = []
        self.window.ip_entry.setText("192.0.2.44")
        self.window._accept_test_diagnostic_model("Extron IPL T PCS4i")
        self.window.show_progress_dialog = Mock()
        self.window._active_request_credentials = [{}]
        self.window._active_request = {
            "id": 13,
            "device": "Extron IPL T PCS4i",
            "ip": "192.0.2.44",
            "credential_context": self.window._pdu_context_token(),
            "credential_index": None,
        }
        self._mark_pdu_outlets_current(
            "Extron IPL T PCS4i",
            "192.0.2.44",
            13,
            self.window._pdu_context_token(),
            None,
            [{"number": 1}],
            {"on": True, "off": True},
        )

        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append), \
                patch.object(QMessageBox, "warning") as warning:
            self.assertTrue(self.window.control_pdu_outlets_bulk("off"))
            self.assertFalse(self.window.control_pdu_outlets_bulk("on"))
            self.assertFalse(self.window.control_pdu_outlet(1, "on"))

        self.assertEqual(1, len(started))
        self.assertEqual(2, warning.call_count)

    def test_individual_command_lock_blocks_bulk_command(self):
        started = []
        self.window.ip_entry.setText("192.0.2.44")
        self.window._accept_test_diagnostic_model("Extron IPL T PCS4i")
        self.window.show_progress_dialog = Mock()
        self.window._active_request_credentials = [{}]
        self.window._active_request = {
            "id": 31,
            "device": "Extron IPL T PCS4i",
            "ip": "192.0.2.44",
            "credential_context": self.window._pdu_context_token(),
            "credential_index": None,
        }
        self._mark_pdu_outlets_current(
            "Extron IPL T PCS4i",
            "192.0.2.44",
            31,
            self.window._pdu_context_token(),
            None,
            [{"number": 1}],
            {"on": True, "off": True},
        )
        screen = self.window.screens["pdu"]

        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append), \
                patch.object(QMessageBox, "warning") as warning:
            self.assertTrue(self.window.control_pdu_outlet(1, "on"))
            self.assertFalse(self.window.control_pdu_outlets_bulk("off"))

        self.assertEqual(1, len(started))
        warning.assert_called_once()
        self.assertFalse(screen.btn_bulk_on.isEnabled())
        self.assertFalse(screen.btn_bulk_off.isEnabled())

    def test_stale_outlet_context_after_ip_change_blocks_bulk_dispatch(self):
        started = []
        self.window.ip_entry.setText("192.0.2.44")
        self.window._accept_test_diagnostic_model("Extron IPL T PCS4i")
        self.window.show_progress_dialog = Mock()
        self.window._active_request_credentials = [{}]
        self.window._active_request = {
            "id": 32,
            "device": "Extron IPL T PCS4i",
            "ip": "192.0.2.44",
            "credential_context": self.window._pdu_context_token(),
            "credential_index": None,
        }
        self._mark_pdu_outlets_current(
            "Extron IPL T PCS4i",
            "192.0.2.44",
            32,
            self.window._pdu_context_token(),
            None,
            [{"number": 1}],
            {"on": True, "off": True},
        )

        self.window.ip_entry.setText("192.0.2.45")

        with patch.object(QThreadPool.globalInstance(), "start", side_effect=started.append), \
                patch.object(QMessageBox, "warning") as warning:
            self.assertFalse(self.window.control_pdu_outlets_bulk("on"))

        self.assertEqual([], started)
        warning.assert_called_once()
        self.assertFalse(self.window.screens["pdu"].btn_bulk_on.isEnabled())

    def test_bulk_button_asks_one_confirmation_dialog(self):
        screen = self.window.screens["pdu"]
        captured = []
        screen.bulk_control_signal.connect(captured.append)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes) as question:
            screen.on_bulk_button_click("off")

        question.assert_called_once()
        self.assertEqual(["off"], captured)

    def test_bulk_auth_retry_requires_structured_zero_send_metadata(self):
        descriptor = PDUOperationDescriptor(
            operation_id=77,
            generation=14,
            model="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            operation=BULK_COMMAND_ON,
            credential_index=0,
            credential_context=self.window._pdu_context_token(),
            outlet_sequence=(1, 2),
        )
        self._activate_pdu_request(descriptor)
        self._seed_pdu_attempt(
            descriptor,
            [{"password": "a"}, {"password": "b"}],
            0,
            "bulk",
        )
        worker = SimpleNamespace(
            device_name="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
        )
        self.window.current_worker = worker
        self.window.hide_progress_dialog = Mock()
        self.window.refresh_data = Mock()

        with patch.object(QThreadPool.globalInstance(), "start") as start:
            self.window.on_pdu_bulk_error(
                (
                    "authentication_error",
                    "rejected",
                    "",
                    {"state_changing_send_attempted": False},
                ),
                worker,
                descriptor,
            )

        start.assert_called_once()
        retry = start.call_args.args[0]
        self.assertEqual(BULK_COMMAND_ON, retry.descriptor.operation)
        self.assertEqual((1, 2), retry.descriptor.outlet_sequence)
        self.assertEqual(1, retry.descriptor.credential_index)
        self.assertFalse(hasattr(retry, "creds_list"))

    def test_aten_bulk_auth_retry_uses_next_candidate_and_persists_only_full_success(self):
        self.window.set_current_credential_index("Aten PE8208AV", 0, "192.0.2.45")
        descriptor = PDUOperationDescriptor(
            operation_id=177,
            generation=34,
            model="Aten PE8208AV",
            ip_address="192.0.2.45",
            operation=BULK_COMMAND_ON,
            credential_index=0,
            credential_context=self.window._pdu_context_token(),
            outlet_sequence=(1, 2),
        )
        self._activate_pdu_request(descriptor)
        creds = [
            {"username": "u", "password": "a"},
            {"username": "u", "password": "b"},
        ]
        self._seed_pdu_attempt(descriptor, creds, 0, "bulk")
        worker = SimpleNamespace(
            device_name="Aten PE8208AV",
            ip_address="192.0.2.45",
        )
        self.window.current_worker = worker
        self.window.hide_progress_dialog = Mock()

        with patch.object(QThreadPool.globalInstance(), "start") as start:
            self.window.on_pdu_bulk_error(
                (
                    "authentication_error",
                    "rejected",
                    "",
                    {"state_changing_send_attempted": False},
                ),
                worker,
                descriptor,
            )

        start.assert_called_once()
        retry = start.call_args.args[0]
        self.assertEqual(1, retry.descriptor.credential_index)
        self.assertEqual(0, self.window.get_current_credential_index("Aten PE8208AV", "192.0.2.45"))

        self._activate_pdu_request(retry.descriptor)
        self.window.refresh_data = Mock()
        with patch.object(QMessageBox, "information"):
            self.window.on_pdu_bulk_result(
                {
                    "success": True,
                    "successful_outlets": (1, 2),
                    "terminal_state": "full_success",
                },
                retry,
                retry.descriptor,
            )

        self.assertEqual(1, self.window.get_current_credential_index("Aten PE8208AV", "192.0.2.45"))
        self.window.refresh_data.assert_not_called()

    def test_bulk_auth_error_after_possible_send_does_not_retry(self):
        descriptor = PDUOperationDescriptor(
            operation_id=78,
            generation=15,
            model="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            operation=BULK_COMMAND_OFF,
            credential_index=0,
            credential_context=self.window._pdu_context_token(),
            outlet_sequence=(1, 2),
        )
        self._activate_pdu_request(descriptor)
        worker = SimpleNamespace(
            device_name="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
        )
        self.window.current_worker = worker
        self.window.hide_progress_dialog = Mock()
        self.window.refresh_data = Mock()

        with patch.object(QThreadPool.globalInstance(), "start") as start, \
                patch.object(QMessageBox, "critical"):
            self.window.on_pdu_bulk_error(
                (
                    "authentication_error",
                    "rejected",
                    "",
                    {"state_changing_send_attempted": True},
                ),
                worker,
                descriptor,
            )

        start.assert_not_called()
        self.window.refresh_data.assert_not_called()

    def test_bulk_success_persists_used_credential_but_partial_does_not(self):
        self.window.set_current_credential_index("Extron IPL T PCS4i", 0, "192.0.2.44")
        descriptor = PDUOperationDescriptor(
            operation_id=79,
            generation=16,
            model="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            operation=BULK_COMMAND_ON,
            credential_index=1,
            credential_context=self.window._pdu_context_token(),
            outlet_sequence=(1, 2),
        )
        self._activate_pdu_request(descriptor)
        self.window.hide_progress_dialog = Mock()
        self.window.refresh_data = Mock()

        with patch.object(QMessageBox, "information"):
            self.window.on_pdu_bulk_result(
                {
                    "success": True,
                    "successful_outlets": (1, 2),
                    "_credential_used": True,
                    "terminal_state": "full_success",
                },
                SimpleNamespace(),
                descriptor,
            )

        self.assertEqual(
            1,
            self.window.get_current_credential_index("Extron IPL T PCS4i", "192.0.2.44"),
        )

        partial = PDUOperationDescriptor(
            **{**descriptor.__dict__, "operation_id": 80, "credential_index": 0}
        )
        self._activate_pdu_request(partial)
        with patch.object(QMessageBox, "warning"):
            self.window.on_pdu_bulk_result(
                {
                    "success": False,
                    "successful_outlets": (1,),
                    "stopping_outlet": 2,
                    "terminal_state": "partial_failure",
                },
                SimpleNamespace(),
                partial,
            )

        self.assertEqual(
            1,
            self.window.get_current_credential_index("Extron IPL T PCS4i", "192.0.2.44"),
        )

    def test_stale_bulk_completion_cannot_unlock_new_context_bulk_controls(self):
        old = PDUOperationDescriptor(
            operation_id=81,
            generation=17,
            model="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            operation=BULK_COMMAND_ON,
            credential_context=100,
            outlet_sequence=(1,),
        )
        self._activate_pdu_request(old)
        screen = self.window.screens["pdu"]
        screen.set_bulk_operation_state(200, True)
        self.window._active_pdu_bulk_context = PDUOperationDescriptor(
            **{**old.__dict__, "operation_id": 200, "credential_context": 101}
        )
        self.window._active_request["credential_context"] = 101
        self.window.current_worker = SimpleNamespace()

        self.window.on_pdu_bulk_finished(self.window.current_worker, old)

        self.assertTrue(screen.bulk_busy)
        self.assertEqual(200, screen.bulk_context)

    @staticmethod
    def _missing_mapping(**_kwargs):
        raise CredentialProfileNotFoundError("missing mapping")

    def _seed_pdu_attempt(self, descriptor, creds, current_index, lane):
        self.window.pdu_controller._record_attempt_state(
            descriptor,
            creds,
            current_index,
            lane,
        )

    def _activate_pdu_request(self, descriptor):
        self.window._active_request = {
            "id": descriptor.generation,
            "device": descriptor.model,
            "ip": descriptor.ip_address,
            "credential_context": descriptor.credential_context,
            "credential_index": descriptor.credential_index,
        }

    def _mark_pdu_outlets_current(
        self,
        model,
        ip_address,
        generation,
        context,
        credential_index,
        outlets,
        capabilities=None,
    ):
        descriptor = PDUOperationDescriptor(
            operation_id=0,
            generation=generation,
            model=model,
            ip_address=ip_address,
            operation=REFRESH,
            credential_index=credential_index,
            credential_context=context,
        )
        self.window._remember_pdu_outlet_context({"outlets": outlets}, descriptor)
        self.window.screens["pdu"].update_data(
            {
                "capabilities": capabilities or {"on": True, "off": True},
                "outlets": [dict(outlet) for outlet in outlets],
            }
        )

    @staticmethod
    def _pdu_descriptor(
        operation,
        *,
        operation_id,
        generation,
        context,
        credential_index=None,
    ):
        return PDUOperationDescriptor(
            operation_id=operation_id,
            generation=generation,
            model="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            operation=operation,
            outlet_number=None if operation == REFRESH else 1,
            credential_index=credential_index,
            credential_context=context,
        )


if __name__ == "__main__":
    unittest.main()
