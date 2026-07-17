import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PyQt5.QtWidgets import QMessageBox

from core.pdu import (
    COMMAND_ON,
    PDUOperationDescriptor,
    execute_pdu_command,
    pdu_credential_identity,
)
from gui.main_window import VCSDiagnosticApp
from gui.ui_states import UIState


class CredentialFallbackRetryTests(unittest.TestCase):
    def make_window(self):
        window = VCSDiagnosticApp.__new__(VCSDiagnosticApp)
        window._active_request = {"id": 1, "screen": None}
        window.current_credential_index = {}
        window.current_worker = None
        window.device_combo = SimpleNamespace(currentText=lambda: "Huawei TE40")
        window.hide_progress_dialog = Mock()
        window.set_ui_state = Mock()
        window.set_current_credential_index = Mock()
        for method_name in (
            "refresh_huawei_te20",
            "refresh_huawei_te40",
            "refresh_huawei_bar310",
            "refresh_polycom_rpg310",
            "refresh_extron_in1804",
            "refresh_aten_pdu",
            "refresh_biamp_tesira_forte_ci",
        ):
            setattr(window, method_name, Mock())
        window.finish_te20_terminal = Mock()
        window.finish_matrix_terminal = Mock()
        window.refresh_btn = Mock()
        window.is_vcs_codec_device = lambda device: device in {
            "Huawei TE20",
            "Huawei TE40",
            "CloudLink Bar 310",
            "Polycom RPG 310",
        }
        return window

    def worker(self, index=0, total=5):
        return SimpleNamespace(
            device_name="Huawei TE40",
            ip_address="192.0.2.10",
            current_idx=index,
            creds_list=[{"username": f"synthetic-{item}", "password": f"synthetic-password-{item}"} for item in range(total)],
        )

    def prepare_data_window(self, worker):
        window = self.make_window()
        window.current_worker = worker
        window.ip_entry = SimpleNamespace(text=lambda: worker.ip_address)
        window.screens = {}
        window.current_screen_type = None
        window.progress_dialog = None
        window.suppress_success_message_once = False
        window.update_time_display = Mock()
        window.set_device_connection_profile = Mock()
        window.show_progress_dialog = Mock()
        return window

    def test_authentication_failure_advances_once_and_uses_actual_chain_length(self):
        window = self.make_window()
        worker = self.worker(index=3, total=5)
        window.current_worker = worker

        def replace_worker(_ip_address):
            window.current_worker = object()

        window.refresh_huawei_te40.side_effect = replace_worker
        window.on_device_error(("authentication_error", "401", ""), worker, 1)
        window.on_device_error(("authentication_error", "401", ""), worker, 1)

        window.set_current_credential_index.assert_not_called()
        self.assertEqual(
            4,
            window._credential_attempt_plans[
                "Huawei TE40|192.0.2.10"
            ].current_index,
        )
        window.refresh_huawei_te40.assert_called_once_with("192.0.2.10")
        self.assertIn("5", window.set_ui_state.call_args.args[1])

    def test_non_authentication_error_does_not_retry(self):
        for message in (
            "timeout",
            "SSL handshake failed",
            "Connection refused",
            "parse error",
            "protocol error",
        ):
            with self.subTest(message=message):
                window = self.make_window()
                worker = self.worker()
                window.current_worker = worker
                with patch.object(QMessageBox, "critical"):
                    window.on_device_error(("request_error", message, ""), worker, 1)
                for method_name in (
                    "refresh_huawei_te20",
                    "refresh_huawei_te40",
                    "refresh_huawei_bar310",
                    "refresh_polycom_rpg310",
                    "refresh_extron_in1804",
                    "refresh_aten_pdu",
                    "refresh_biamp_tesira_forte_ci",
                ):
                    getattr(window, method_name).assert_not_called()
                window.set_current_credential_index.assert_not_called()
                self.assertEqual(UIState.REQUEST_ERROR, window.set_ui_state.call_args.args[0])

    def test_codec_retry_authority_ignores_auth_and_401_message_text(self):
        for error_type, message in (
            ("connection_error", "transport auth 401 failed"),
            ("protocol_error", "authentication response malformed"),
            ("command_error", "success: 0, code 403"),
        ):
            with self.subTest(error_type=error_type):
                window = self.make_window()
                worker = self.worker(index=0, total=2)
                window.current_worker = worker
                with patch.object(QMessageBox, "critical"):
                    window.on_device_error((error_type, message, ""), worker, 1)
                window.refresh_huawei_te40.assert_not_called()
                window.set_current_credential_index.assert_not_called()

    def test_exhausted_chain_emits_one_safe_terminal_authentication_message(self):
        window = self.make_window()
        worker = self.worker(index=4, total=5)
        window.current_worker = worker
        with patch.object(QMessageBox, "warning") as warning:
            window.on_device_error(
                ("authentication_error", "synthetic-password-4", ""), worker, 1
            )
        window.refresh_huawei_te40.assert_not_called()
        warning.assert_called_once()
        public_text = " ".join(str(value) for value in warning.call_args.args)
        self.assertNotIn("synthetic-password-4", public_text)

    def test_credential_indexes_are_isolated_by_device_and_ip(self):
        window = VCSDiagnosticApp.__new__(VCSDiagnosticApp)
        window.current_credential_index = {}

        VCSDiagnosticApp.set_current_credential_index(
            window, "Huawei TE40", 4, "192.0.2.10"
        )

        self.assertEqual(
            4,
            VCSDiagnosticApp.get_current_credential_index(
                window, "Huawei TE40", "192.0.2.10"
            ),
        )
        self.assertEqual(
            0,
            VCSDiagnosticApp.get_current_credential_index(
                window, "Huawei TE40", "192.0.2.11"
            ),
        )
        self.assertEqual({}, {
            key: value for key, value in window.current_credential_index.items()
            if key == "Huawei TE40"
        })

        VCSDiagnosticApp.set_current_credential_index(
            window, "Huawei TE40", 2, "192.0.2.11"
        )
        self.assertEqual(
            4,
            VCSDiagnosticApp.get_current_credential_index(
                window, "Huawei TE40", "192.0.2.10"
            ),
        )
        self.assertEqual(
            0,
            VCSDiagnosticApp.get_current_credential_index(
                window, "Extron IN1804", "192.0.2.10"
            ),
        )

        VCSDiagnosticApp.set_current_credential_index(window, "Huawei TE40", 3)
        self.assertEqual(
            0,
            VCSDiagnosticApp.get_current_credential_index(
                window, "Huawei TE40", "192.0.2.12"
            ),
        )

    def test_invalid_saved_index_starts_at_zero(self):
        window = VCSDiagnosticApp.__new__(VCSDiagnosticApp)
        window.current_credential_index = {"Huawei TE40|192.0.2.10": 7}

        self.assertEqual(
            0,
            VCSDiagnosticApp.get_valid_current_credential_index(
                window,
                "Huawei TE40",
                [{"password": "synthetic-password-a"}] * 3,
                "192.0.2.10",
            ),
        )

    def test_partial_result_does_not_cache_a_successful_candidate(self):
        window = VCSDiagnosticApp.__new__(VCSDiagnosticApp)
        window._active_request = None
        window.current_credential_index = {}
        window.device_combo = SimpleNamespace(currentText=lambda: "Huawei TE40")
        window.hide_progress_dialog = Mock()
        window.set_ui_state = Mock()
        window.update_time_display = Mock()
        window.progress_dialog = None
        window.current_screen_type = None
        window.screens = {}
        worker = self.worker(index=2, total=5)

        window.on_device_data_received(
            {"ip_address": "192.0.2.10", "status": "partial", "_partial_update": True},
            worker,
        )

        self.assertEqual({}, window.current_credential_index)

    def test_authentication_retry_dispatches_each_production_path(self):
        refresh_methods = {
            "Huawei TE20": "refresh_huawei_te20",
            "Huawei TE40": "refresh_huawei_te40",
            "CloudLink Bar 310": "refresh_huawei_bar310",
            "Polycom RPG 310": "refresh_polycom_rpg310",
            "Extron IN1804": "refresh_extron_in1804",
            "Aten PE8208AV": "refresh_aten_pdu",
            "Biamp Tesira Forte CI": "refresh_biamp_tesira_forte_ci",
        }
        for device_name, method_name in refresh_methods.items():
            with self.subTest(device=device_name):
                window = self.make_window()
                worker = self.worker(index=0, total=5)
                worker.device_name = device_name
                window.current_worker = worker
                refresh = Mock(side_effect=lambda _ip: setattr(window, "current_worker", object()))
                setattr(window, method_name, refresh)
                window.on_device_error(("authentication_error", "401", ""), worker, 1)

                refresh.assert_called_once_with("192.0.2.10")
                if device_name in {
                    "Huawei TE20",
                    "Huawei TE40",
                    "CloudLink Bar 310",
                    "Polycom RPG 310",
                }:
                    window.set_current_credential_index.assert_not_called()
                    self.assertEqual(
                        1,
                        window._credential_attempt_plans[
                            f"{device_name}|192.0.2.10"
                        ].current_index,
                    )
                else:
                    window.set_current_credential_index.assert_called_once_with(
                        device_name, 1, "192.0.2.10"
                    )

    def test_chain_length_ten_has_no_special_case_limit(self):
        window = self.make_window()
        worker = self.worker(index=8, total=10)
        window.current_worker = worker
        window.refresh_huawei_te40.side_effect = (
            lambda _ip: setattr(window, "current_worker", object())
        )

        window.on_device_error(("authentication_error", "401", ""), worker, 1)

        window.set_current_credential_index.assert_not_called()
        self.assertEqual(
            9,
            window._credential_attempt_plans[
                "Huawei TE40|192.0.2.10"
            ].current_index,
        )
        window.refresh_huawei_te40.assert_called_once_with("192.0.2.10")
        self.assertIn("10", window.set_ui_state.call_args.args[1])

    def test_saved_index_exhausts_only_remaining_suffix_without_wraparound(self):
        window = self.make_window()
        first_worker = self.worker(index=3, total=5)
        window.current_worker = first_worker
        attempted = [3]

        def start_next(_ip_address):
            next_index = window._credential_attempt_plans[
                "Huawei TE40|192.0.2.10"
            ].current_index
            next_worker = self.worker(index=next_index, total=5)
            attempted.append(next_index)
            window.current_worker = next_worker

        window.refresh_huawei_te40.side_effect = start_next

        window.on_device_error(
            ("authentication_error", "synthetic-password-3", ""), first_worker, 1
        )
        last_worker = window.current_worker
        with patch.object(QMessageBox, "warning") as warning:
            window.on_device_error(
                ("authentication_error", "synthetic-password-4", ""),
                last_worker,
                1,
            )

        self.assertEqual([3, 4], attempted)
        self.assertEqual(1, window.refresh_huawei_te40.call_count)
        warning.assert_called_once()

    def test_duplicate_terminal_error_from_one_worker_is_ignored(self):
        window = self.make_window()
        worker = self.worker(index=4, total=5)
        window.current_worker = worker

        with patch.object(QMessageBox, "warning") as warning:
            window.on_device_error(("authentication_error", "401", ""), worker, 1)
            window.on_device_error(("authentication_error", "401", ""), worker, 1)

        warning.assert_called_once()
        window.refresh_huawei_te40.assert_not_called()

    def test_stale_worker_error_does_not_retry_or_render(self):
        window = self.make_window()
        stale_worker = self.worker(index=0, total=5)
        window.current_worker = object()

        with patch.object(QMessageBox, "warning") as warning, patch.object(
            QMessageBox, "critical"
        ) as critical:
            window.on_device_error(
                ("authentication_error", "401", ""), stale_worker, 1
            )

        warning.assert_not_called()
        critical.assert_not_called()
        window.refresh_huawei_te40.assert_not_called()

    def test_success_in_middle_caches_index_and_starts_no_further_worker(self):
        worker = self.worker(index=2, total=5)
        window = self.prepare_data_window(worker)

        with patch.object(QMessageBox, "information"):
            window.on_device_data_received(
                {"ip_address": "192.0.2.10", "status": "ok"}, worker, 1
            )

        window.set_current_credential_index.assert_called_once_with(
            "Huawei TE40", 2, "192.0.2.10"
        )
        for method_name in (
            "refresh_huawei_te20",
            "refresh_huawei_te40",
            "refresh_huawei_bar310",
            "refresh_polycom_rpg310",
            "refresh_extron_in1804",
            "refresh_aten_pdu",
            "refresh_biamp_tesira_forte_ci",
        ):
            getattr(window, method_name).assert_not_called()

    def test_structured_error_outcome_cannot_cache_or_render_success(self):
        worker = self.worker(index=2, total=5)
        window = self.prepare_data_window(worker)

        with patch.object(QMessageBox, "critical") as critical, patch.object(
            QMessageBox, "information"
        ) as information:
            window.on_device_data_received(
                {
                    "_outcome": "error",
                    "error_type": "connection_error",
                    "error": "synthetic structured failure",
                    "ip_address": "192.0.2.10",
                },
                worker,
                1,
            )

        window.set_current_credential_index.assert_not_called()
        self.assertEqual(UIState.REQUEST_ERROR, window.set_ui_state.call_args.args[0])
        critical.assert_called_once()
        information.assert_not_called()

    def test_polycom_partial_then_error_never_caches_or_enters_connected(self):
        worker = self.worker(index=2, total=5)
        worker.device_name = "Polycom RPG 310"
        window = self.prepare_data_window(worker)
        window.device_combo = SimpleNamespace(currentText=lambda: "Polycom RPG 310")

        with patch.object(QMessageBox, "critical") as critical, patch.object(
            QMessageBox, "information"
        ) as information:
            window.on_device_data_received(
                {
                    "ip_address": "192.0.2.10",
                    "status": "partial",
                    "_partial_update": True,
                },
                worker,
                1,
            )
            self.assertEqual(UIState.LOADING, window.set_ui_state.call_args.args[0])
            window.on_device_error(
                ("connection_error", "ssh failed", "synthetic traceback"),
                worker,
                1,
            )

        window.set_current_credential_index.assert_not_called()
        self.assertEqual(UIState.REQUEST_ERROR, window.set_ui_state.call_args.args[0])
        critical.assert_called_once()
        information.assert_not_called()

    def test_te20_and_extron_terminal_errors_redact_every_candidate_secret(self):
        secrets = (
            "synthetic-user-a",
            "synthetic-password-a",
            "synthetic-bearer-token",
            "synthetic-session-value",
        )
        for device_name, terminal_method in {
            "Huawei TE20": "finish_te20_terminal",
            "Extron IN1804": "finish_matrix_terminal",
        }.items():
            with self.subTest(device=device_name):
                window = self.make_window()
                worker = SimpleNamespace(
                    device_name=device_name,
                    ip_address="192.0.2.10",
                    current_idx=1,
                    creds_list=[
                        {"username": secrets[0], "password": secrets[1]},
                        {"token": secrets[2], "session": secrets[3]},
                    ],
                )
                window.current_worker = worker
                window.finish_te20_terminal = Mock()
                window.finish_matrix_terminal = Mock()
                error_text = "Authorization: Bearer {} {} {} {}".format(*secrets)

                with patch.object(QMessageBox, "warning") as warning:
                    window.on_device_error(
                        ("authentication_error", error_text, ""), worker, 1
                    )

                terminal_text = " ".join(
                    str(value) for value in getattr(window, terminal_method).call_args.args
                )
                public_text = " ".join(
                    str(value)
                    for call in [warning.call_args, window.set_ui_state.call_args]
                    for value in call.args
                )
                for secret in secrets:
                    self.assertNotIn(secret, terminal_text)
                    self.assertNotIn(secret, public_text)
                self.assertIn("<redacted>", terminal_text)


class PCS4iCredentialFallbackRetryTests(unittest.TestCase):
    def make_window(self):
        window = VCSDiagnosticApp.__new__(VCSDiagnosticApp)
        window._active_request = {"id": 1, "screen": None}
        window.current_credential_index = {}
        window.current_worker = None
        window.device_combo = SimpleNamespace(currentText=lambda: "Extron IPL T PCS4i")
        window.ip_entry = SimpleNamespace(text=lambda: "192.0.2.44")
        window.hide_progress_dialog = Mock()
        window.show_progress_dialog = Mock()
        window.set_ui_state = Mock()
        window.set_current_credential_index = Mock()
        window.refresh_pdu = Mock()
        window.refresh_btn = Mock()
        window.screens = {}
        window.current_screen_type = None
        window.progress_dialog = None
        window.suppress_success_message_once = False
        window.update_time_display = Mock()
        window.set_device_connection_profile = Mock()
        window.validate_ip_address = Mock(return_value=True)
        window._pdu_context_is_current = Mock(return_value=True)
        window._request_serial = 1
        window.is_vcs_codec_device = lambda _device: False
        return window

    def worker(self, index=0, total=3):
        return SimpleNamespace(
            device_name="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            current_idx=index,
            creds_list=[
                {"password": f"synthetic-password-{item}"}
                for item in range(total)
            ],
        )

    def context_window(self):
        window = VCSDiagnosticApp.__new__(VCSDiagnosticApp)
        window._active_request = {
            "id": 1,
            "device": "Extron IPL T PCS4i",
            "ip": "192.0.2.44",
            "screen": None,
            "credential_context": 10,
            "credential_index": None,
            "credential_identity": None,
        }
        window._pdu_context_revision = 10
        window._credential_attempt_plans = {}
        window.current_credential_index = {}
        window.current_worker = None
        window.screens = {
            "pdu": SimpleNamespace(set_outlet_command_state=Mock())
        }
        window.hide_progress_dialog = Mock()
        window.refresh_data = Mock()
        window.set_ui_state = Mock()
        window.set_current_credential_index = Mock()
        window.is_vcs_codec_device = lambda _device: False
        return window

    def pdu_descriptor(self, index, operation_id=501):
        creds = {"password": f"synthetic-password-{index}"}
        return PDUOperationDescriptor(
            operation_id=operation_id,
            generation=1,
            model="Extron IPL T PCS4i",
            ip_address="192.0.2.44",
            operation=COMMAND_ON,
            outlet_number=1,
            credential_index=index,
            credential_context=10,
            credential_identity=pdu_credential_identity(
                "Extron IPL T PCS4i",
                creds,
                index,
            ),
        )

    def activate_pdu_candidate(self, window, index):
        descriptor = self.pdu_descriptor(index)
        window._set_active_pdu_credential_context(
            descriptor.model,
            descriptor.ip_address,
            descriptor.credential_index,
            descriptor.credential_identity,
        )
        return descriptor

    def test_first_candidate_auth_failure_starts_second_without_persisting(self):
        window = self.make_window()
        worker = self.worker(index=0, total=3)
        window.current_worker = worker

        window.on_device_error(("authentication_error", "rejected", ""), worker, 1)

        window.set_current_credential_index.assert_not_called()
        window.refresh_pdu.assert_called_once_with("192.0.2.44", "Extron IPL T PCS4i")
        self.assertEqual(
            1,
            window._credential_attempt_plans[
                "Extron IPL T PCS4i|192.0.2.44"
            ].current_index,
        )

        success_worker = self.worker(index=1, total=3)
        window.current_worker = success_worker
        with patch.object(QMessageBox, "information"):
            window.on_device_data_received(
                {
                    "ip_address": "192.0.2.44",
                    "status": "ok",
                    "_credential_used": True,
                },
                success_worker,
                1,
            )

        window.set_current_credential_index.assert_called_once_with(
            "Extron IPL T PCS4i", 1, "192.0.2.44"
        )

    def test_old_candidate_descriptor_is_stale_after_fallback_advances_context(self):
        window = self.context_window()
        creds = self.worker(total=2).creds_list
        old_descriptor = self.activate_pdu_candidate(window, 0)
        self.assertTrue(window._pdu_context_is_current(old_descriptor))

        next_index = window._advance_request_credential_attempt(
            "Extron IPL T PCS4i",
            creds,
            "192.0.2.44",
            0,
            old_descriptor.operation_id,
        )
        retry_descriptor = self.pdu_descriptor(next_index, old_descriptor.operation_id)
        window._set_active_pdu_credential_context(
            retry_descriptor.model,
            retry_descriptor.ip_address,
            retry_descriptor.credential_index,
            retry_descriptor.credential_identity,
        )
        acquired = []

        result = execute_pdu_command(
            descriptor=old_descriptor,
            credentials=creds[0],
            is_current=window._pdu_context_is_current,
            handler_factory=lambda *_args: acquired.append(True),
        )

        self.assertEqual({"_outcome": "stale", "operation": COMMAND_ON}, result)
        self.assertEqual([], acquired)

    def test_retry_candidate_descriptor_remains_current_with_same_operation_id(self):
        window = self.context_window()
        creds = self.worker(total=2).creds_list
        old_descriptor = self.activate_pdu_candidate(window, 0)
        next_index = window._advance_request_credential_attempt(
            "Extron IPL T PCS4i",
            creds,
            "192.0.2.44",
            0,
            old_descriptor.operation_id,
        )
        retry_descriptor = self.pdu_descriptor(next_index, old_descriptor.operation_id)
        window._set_active_pdu_credential_context(
            retry_descriptor.model,
            retry_descriptor.ip_address,
            retry_descriptor.credential_index,
            retry_descriptor.credential_identity,
        )

        self.assertTrue(window._pdu_context_is_current(retry_descriptor))
        self.assertEqual(old_descriptor.operation_id, retry_descriptor.operation_id)
        window.set_current_credential_index.assert_not_called()

    def test_successful_candidate_context_makes_old_queued_candidate_stale(self):
        window = self.context_window()
        old_descriptor = self.activate_pdu_candidate(window, 0)
        successful_descriptor = self.pdu_descriptor(1, operation_id=777)
        window._set_active_pdu_credential_context(
            successful_descriptor.model,
            successful_descriptor.ip_address,
            successful_descriptor.credential_index,
            successful_descriptor.credential_identity,
        )
        acquired = []

        result = execute_pdu_command(
            descriptor=old_descriptor,
            credentials={"password": "synthetic-password-0"},
            is_current=window._pdu_context_is_current,
            handler_factory=lambda *_args: acquired.append(True),
        )

        self.assertEqual({"_outcome": "stale", "operation": COMMAND_ON}, result)
        self.assertEqual([], acquired)

    def test_stale_command_callbacks_do_not_mutate_new_credential_context(self):
        window = self.context_window()
        old_descriptor = self.activate_pdu_candidate(window, 0)
        current_descriptor = self.pdu_descriptor(1, operation_id=old_descriptor.operation_id)
        window._set_active_pdu_credential_context(
            current_descriptor.model,
            current_descriptor.ip_address,
            current_descriptor.credential_index,
            current_descriptor.credential_identity,
        )
        worker = SimpleNamespace(current_idx=0, creds_list=self.worker(total=2).creds_list)
        window.current_worker = worker

        with patch.object(QMessageBox, "information") as information, \
                patch.object(QMessageBox, "warning") as warning, \
                patch.object(QMessageBox, "critical") as critical:
            window.on_pdu_command_result(
                {
                    "success": True,
                    "operation": COMMAND_ON,
                    "outlet_number": 1,
                    "_credential_used": True,
                },
                worker,
                old_descriptor,
            )
            window.on_pdu_command_error(
                ("authentication_error", "stale rejected", ""),
                worker,
                old_descriptor,
            )
            window.on_pdu_command_finished(worker, old_descriptor)

        window.set_current_credential_index.assert_not_called()
        window.refresh_data.assert_not_called()
        window.hide_progress_dialog.assert_not_called()
        information.assert_not_called()
        warning.assert_not_called()
        critical.assert_not_called()

    def test_all_pcs4i_candidates_fail_once_without_wraparound_or_persist(self):
        window = self.make_window()
        attempts = [0]
        first_worker = self.worker(index=0, total=3)
        window.current_worker = first_worker

        def start_next(_ip_address, _device_name):
            next_index = window._credential_attempt_plans[
                "Extron IPL T PCS4i|192.0.2.44"
            ].current_index
            attempts.append(next_index)
            window.current_worker = self.worker(index=next_index, total=3)

        window.refresh_pdu.side_effect = start_next
        window.on_device_error(("authentication_error", "bad 0", ""), first_worker, 1)
        second_worker = window.current_worker
        window.on_device_error(("authentication_error", "bad 1", ""), second_worker, 1)
        third_worker = window.current_worker

        with patch.object(QMessageBox, "warning") as warning:
            window.on_device_error(("authentication_error", "bad 2", ""), third_worker, 1)

        self.assertEqual([0, 1, 2], attempts)
        self.assertEqual(2, window.refresh_pdu.call_count)
        warning.assert_called_once()
        window.set_current_credential_index.assert_not_called()

    def test_pcs4i_non_auth_structured_error_stops_fallback(self):
        window = self.make_window()
        worker = self.worker(index=0, total=3)
        window.current_worker = worker

        with patch.object(QMessageBox, "critical"):
            window.on_device_error(
                ("connection_error", "auth password 401 403 transport text", ""),
                worker,
                1,
            )

        window.refresh_pdu.assert_not_called()
        window.set_current_credential_index.assert_not_called()

    def test_pcs4i_credential_required_does_not_trigger_fallback(self):
        window = self.make_window()
        worker = self.worker(index=0, total=3)
        window.current_worker = worker

        with patch.object(QMessageBox, "critical"):
            window.on_device_error(("credential_required", "Password requested", ""), worker, 1)

        window.refresh_pdu.assert_not_called()
        window.set_current_credential_index.assert_not_called()

    def test_pcs4i_protocol_error_with_misleading_auth_text_is_not_retry_authority(self):
        window = self.make_window()
        worker = self.worker(index=0, total=3)
        window.current_worker = worker

        with patch.object(QMessageBox, "critical"):
            window.on_device_error(
                ("protocol_error", "malformed auth password 401 403", ""),
                worker,
                1,
            )

        window.refresh_pdu.assert_not_called()
        window.set_current_credential_index.assert_not_called()

    def test_pcs4i_passwordless_success_with_assigned_candidate_does_not_persist(self):
        window = self.make_window()
        worker = self.worker(index=1, total=3)
        window.current_worker = worker

        with patch.object(QMessageBox, "information"):
            window.on_device_data_received(
                {
                    "ip_address": "192.0.2.44",
                    "status": "ok",
                    "_credential_used": False,
                },
                worker,
                1,
            )

        window.set_current_credential_index.assert_not_called()

    def test_pcs4i_successful_used_credential_is_persisted_after_success(self):
        window = self.make_window()
        first_worker = self.worker(index=0, total=3)
        window.current_worker = first_worker
        window.on_device_error(("authentication_error", "bad 0", ""), first_worker, 1)
        window.set_current_credential_index.assert_not_called()

        success_worker = self.worker(index=1, total=3)
        window.current_worker = success_worker
        with patch.object(QMessageBox, "information"):
            window.on_device_data_received(
                {
                    "ip_address": "192.0.2.44",
                    "status": "ok",
                    "_credential_used": True,
                },
                success_worker,
                1,
            )

        window.set_current_credential_index.assert_called_once_with(
            "Extron IPL T PCS4i", 1, "192.0.2.44"
        )
        self.assertEqual(1, window.refresh_pdu.call_count)

    def test_pcs4i_refresh_pdu_uses_existing_attempt_plan_after_fallback(self):
        window = self.make_window()
        window._active_request_credentials = self.worker(total=3).creds_list
        first_worker = self.worker(index=0, total=3)
        window.current_worker = first_worker
        window.on_device_error(("authentication_error", "bad 0", ""), first_worker, 1)
        started = []

        with patch("gui.main_window.QThreadPool.globalInstance") as pool:
            pool.return_value.start.side_effect = started.append
            VCSDiagnosticApp.refresh_pdu(window, "192.0.2.44", "Extron IPL T PCS4i")

        self.assertEqual(1, len(started))
        next_worker = started[0]
        self.assertEqual(1, next_worker.current_idx)
        self.assertEqual({"password": "synthetic-password-1"}, next_worker.credentials)
        self.assertEqual(1, next_worker.descriptor.credential_index)
        window.set_current_credential_index.assert_not_called()


if __name__ == "__main__":
    unittest.main()
