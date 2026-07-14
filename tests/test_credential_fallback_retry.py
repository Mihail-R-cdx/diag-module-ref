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


if __name__ == "__main__":
    unittest.main()
