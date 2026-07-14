import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PyQt5.QtWidgets import QMessageBox

from gui.main_window import VCSDiagnosticApp


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
        window.refresh_huawei_te40 = Mock()
        window.refresh_btn = Mock()
        window.is_vcs_codec_device = lambda _device: True
        return window

    def worker(self, index=0, total=5):
        return SimpleNamespace(
            device_name="Huawei TE40",
            ip_address="192.0.2.10",
            current_idx=index,
            creds_list=[{"username": f"synthetic-{item}", "password": f"synthetic-password-{item}"} for item in range(total)],
        )

    def test_authentication_failure_advances_once_and_uses_actual_chain_length(self):
        window = self.make_window()
        worker = self.worker(index=3, total=5)
        window.current_worker = worker

        def replace_worker(_ip_address):
            window.current_worker = object()

        window.refresh_huawei_te40.side_effect = replace_worker
        window.on_device_error(("authentication_error", "401", ""), worker, 1)
        window.on_device_error(("authentication_error", "401", ""), worker, 1)

        window.set_current_credential_index.assert_called_once_with(
            "Huawei TE40", 4, "192.0.2.10"
        )
        window.refresh_huawei_te40.assert_called_once_with("192.0.2.10")
        self.assertIn("5", window.set_ui_state.call_args.args[1])

    def test_non_authentication_error_does_not_retry(self):
        window = self.make_window()
        worker = self.worker()
        window.current_worker = worker
        with patch.object(QMessageBox, "critical"):
            window.on_device_error(("request_error", "timeout", ""), worker, 1)
        window.refresh_huawei_te40.assert_not_called()

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
            "Huawei TE40": "refresh_huawei_te40",
            "Extron IN1804": "refresh_extron_in1804",
            "Aten PE8208AV": "refresh_aten_pdu",
        }
        for device_name, method_name in refresh_methods.items():
            with self.subTest(device=device_name):
                window = self.make_window()
                worker = self.worker(index=0, total=5)
                worker.device_name = device_name
                window.current_worker = worker
                refresh = Mock(side_effect=lambda _ip: setattr(window, "current_worker", object()))
                setattr(window, method_name, refresh)
                window.finish_te20_terminal = Mock()
                window.finish_matrix_terminal = Mock()

                window.on_device_error(("authentication_error", "401", ""), worker, 1)

                refresh.assert_called_once_with("192.0.2.10")
                window.set_current_credential_index.assert_called_once_with(
                    device_name, 1, "192.0.2.10"
                )

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


if __name__ == "__main__":
    unittest.main()
