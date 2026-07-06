from __future__ import annotations

import os
import unittest
from unittest.mock import patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtWidgets import (
        QApplication,
        QComboBox,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QWidget,
    )
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class UIStatesOffscreenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")

    def tearDown(self):
        if hasattr(self, "window"):
            if hasattr(self.window, "close"):
                self.window.close()
            if hasattr(self.window, "deleteLater"):
                self.window.deleteLater()
        QApplication.processEvents()

    def _make_main_window_harness(self):
        from gui.main_window import VCSDiagnosticApp
        from gui.ui_states import UIState

        class Style:
            def unpolish(self, widget):
                pass

            def polish(self, widget):
                pass

        class Control:
            def __init__(self, text=""):
                self._text = text
                self._enabled = True
                self._status = "inactive"
                self._style = Style()

            def setText(self, text):
                self._text = text

            def text(self):
                return self._text

            def setEnabled(self, enabled):
                self._enabled = enabled

            def isEnabled(self):
                return self._enabled

            def set_status(self, status):
                self._status = status

            def style(self):
                return self._style

            def update(self):
                pass

        class Harness:
            set_connection_status = VCSDiagnosticApp.set_connection_status
            set_ui_state = VCSDiagnosticApp.set_ui_state
            _begin_request = VCSDiagnosticApp._begin_request
            _request_is_current = VCSDiagnosticApp._request_is_current
            on_device_data_received = VCSDiagnosticApp.on_device_data_received
            on_device_error = VCSDiagnosticApp.on_device_error
            on_worker_finished = VCSDiagnosticApp.on_worker_finished
            hide_progress_dialog = VCSDiagnosticApp.hide_progress_dialog
            update_time_display = VCSDiagnosticApp.update_time_display
            is_authentication_error = VCSDiagnosticApp.is_authentication_error
            is_vcs_codec_device = VCSDiagnosticApp.is_vcs_codec_device
            get_current_credential_index = (
                VCSDiagnosticApp.get_current_credential_index
            )
            get_credential_key = VCSDiagnosticApp.get_credential_key
            set_current_credential_index = (
                VCSDiagnosticApp.set_current_credential_index
            )
            set_device_connection_profile = (
                VCSDiagnosticApp.set_device_connection_profile
            )

            def setProperty(self, name, value):
                setattr(self, name, value)

        window = Harness()
        window.ui_state = UIState.IDLE
        window._request_serial = 0
        window._active_request = None
        window.current_worker = None
        window.progress_dialog = None
        window.last_update_time = None
        window.screens = {}
        window.device_to_screen = {"Huawei TE40": "codec"}
        window.current_credential_index = {"Huawei TE40": 0}
        window.device_connection_profiles = {}
        window.connection_indicator = Control()
        window.connection_status = Control()
        window.refresh_btn = Control("Обновить данные")
        window.device_combo = Control("Huawei TE40")
        window.device_combo.currentText = window.device_combo.text
        window.ip_entry = Control("link.ru")
        window.time_display = Control("Никогда")
        return window

    def test_state_vocabulary_has_a_text_and_non_color_cue(self):
        from gui.ui_states import STATE_SPECS, UIState

        self.assertEqual(set(UIState), set(STATE_SPECS))
        for state in UIState:
            spec = STATE_SPECS[state]
            self.assertTrue(spec.default_text)
            self.assertIn(
                spec.indicator,
                {"inactive", "loading", "success", "danger", "warning"},
            )

    def test_screen_loading_unavailable_and_disabled_are_reversible(self):
        from gui.components import ParameterRow, SemanticButton
        from gui.screens.base_screen import BaseScreen
        from gui.ui_states import UIState

        class Screen(BaseScreen):
            def init_ui(screen):
                screen.row = ParameterRow("Параметр", "42", screen)
                screen.button = SemanticButton("Команда", parent=screen)

            def update_data(screen, data):
                screen.row.set_value(data["value"])

        self.window = Screen()
        self.window.set_ui_state(UIState.LOADING)
        self.assertEqual("Загрузка данных…", self.window.row.value_display.text())
        self.window.set_ui_state(UIState.UNAVAILABLE)
        self.assertEqual("—", self.window.row.value_display.text())
        self.window.set_ui_state(UIState.DISABLED)
        self.assertFalse(self.window.button.isEnabled())
        self.window.set_ui_state(UIState.IDLE)
        self.assertTrue(self.window.button.isEnabled())

    def test_newer_request_rejects_stale_result_error_and_finished(self):
        from gui.ui_states import UIState

        class Screen:
            def __init__(self):
                self.updates = []
                self.states = []

            def set_ui_state(self, state, message=None):
                self.states.append(state)

            def update_data(self, data):
                self.updates.append(data)

        class Worker:
            device_name = "Huawei TE40"
            current_idx = 0
            creds_list = []
            ip_address = "link.ru"

        self.window = self._make_main_window_harness()
        old_screen = Screen()
        new_screen = Screen()
        old_worker = Worker()
        new_worker = Worker()

        old_request = self.window._begin_request(
            "Huawei TE40", "link.ru", old_screen
        )
        new_request = self.window._begin_request(
            "Huawei TE40", "link.ru", new_screen
        )
        self.window.current_worker = new_worker
        self.window.refresh_btn.setEnabled(False)

        with patch.object(QMessageBox, "critical"), patch.object(
            QMessageBox, "warning"
        ):
            self.window.on_device_data_received(
                {"model": "stale"}, old_worker, old_request["id"]
            )
            self.window.on_device_error(
                ("request_error", "stale", ""), old_worker, old_request["id"]
            )
            self.window.on_worker_finished(old_worker, old_request["id"])

        self.assertEqual([], old_screen.updates)
        self.assertFalse(self.window.refresh_btn.isEnabled())
        self.assertEqual(UIState.LOADING, self.window.ui_state)

        with patch.object(QMessageBox, "information"):
            self.window.on_device_data_received(
                {"model": "fresh"}, new_worker, new_request["id"]
            )
        self.assertEqual([{"model": "fresh"}], new_screen.updates)
        self.assertEqual(UIState.CONNECTED, self.window.ui_state)

    def test_authentication_and_request_errors_leave_loading(self):
        from gui.ui_states import UIState

        class Worker:
            device_name = "Huawei TE40"
            current_idx = 0
            creds_list = []
            ip_address = "link.ru"

        self.window = self._make_main_window_harness()
        self.window.screens["codec"] = object()
        worker = Worker()
        request = self.window._begin_request(
            worker.device_name,
            worker.ip_address,
            self.window.screens["codec"],
        )
        self.window.current_worker = worker

        with patch.object(QMessageBox, "warning"):
            self.window.on_device_error(
                ("authentication_error", "401", ""),
                worker,
                request["id"],
            )
        self.assertEqual(UIState.AUTH_ERROR, self.window.ui_state)
        self.assertTrue(self.window.refresh_btn.isEnabled())

        request = self.window._begin_request(
            worker.device_name,
            worker.ip_address,
            self.window.screens["codec"],
        )
        self.window.current_worker = worker
        with patch.object(QMessageBox, "critical"):
            self.window.on_device_error(
                ("request_error", "timeout", ""),
                worker,
                request["id"],
            )
        self.assertEqual(UIState.REQUEST_ERROR, self.window.ui_state)


if __name__ == "__main__":
    unittest.main()
