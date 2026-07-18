from __future__ import annotations

import ast
import inspect
import os
import unittest
from unittest.mock import patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtCore import QEvent
    from PyQt5.QtWidgets import QApplication, QDialog
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class ReleaseUIOffscreenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        from gui.main_window import VCSDiagnosticApp

        self.app.setQuitOnLastWindowClosed(False)
        self.window = VCSDiagnosticApp()
        self.window.show()
        QApplication.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        QApplication.processEvents()

    def test_every_selectable_device_switches_to_its_expected_screen(self):
        selectable_devices = tuple(self.window.device_to_screen)
        self.assertEqual(9, len(selectable_devices))

        for device_name in selectable_devices:
            with self.subTest(device=device_name):
                self.window.device_combo.setCurrentText(device_name)
                QApplication.processEvents()
                expected_type = self.window.device_to_screen[device_name]
                self.assertEqual(expected_type, self.window.current_screen_type)
                self.assertIs(
                    self.window.placeholder_widget,
                    self.window.screen_container.currentWidget(),
                )

                target = self.window.screens[expected_type]
                self.window.screen_container.setCurrentWidget(target)
                self.assertIs(
                    target,
                    self.window.screen_container.currentWidget(),
                )

    def test_representative_payloads_and_all_states_render(self):
        from gui.ui_states import STATE_SPECS, UIState

        codec = self.window.screens["codec"]
        self.window.device_combo.setCurrentText("Huawei TE40")
        codec.update_data(
            {
                "Версия ПО": "V3.1",
                "Модель": "TE40",
                "Серийный номер": "QA-SERIAL",
                "MAC адрес": "00:11:22:33:44:55",
                "SIP регистрация": "Зарегистрирован",
                "SIP адрес": "sip:qa@link.ru",
                "Время работы": "5 дней",
                "Режим презентации": "Start",
                "Громкость динамиков": "7",
                "Mute микрофона": "Unmuted",
            }
        )

        matrix = self.window.screens["matrix"]
        matrix.update_data(
            {
                "inputs_num": 8,
                "input_names": [f"Input {number}" for number in range(1, 9)],
                "output_names": ["Main Output"],
                "current_connection": 2,
                "signal_status": {1: {"has_signal": True}},
                "input_hdcp_status": ["2"] * 8,
                "input_hdcp_auth": [1] * 8,
                "model": "IN1804",
                "temperature": 41,
                "connection_protocol": "SSH",
            }
        )

        pdu = self.window.screens["pdu"]
        pdu.update_data(
            {
                "device_info": {
                    "model": "PE8208AV",
                    "ip_address": "link.ru",
                    "firmware": "2.4.1",
                    "connected": True,
                },
                "outlets": [
                    {
                        "number": number,
                        "name": f"Outlet {number}",
                        "status": "on" if number % 2 else "off",
                    }
                    for number in range(1, 9)
                ],
            }
        )

        audio = self.window.screens["audio_dsp"]
        audio.update_data(
            {
                "device_info": {
                    "model": "Biamp Tesira Forte CI",
                    "ip_address": "link.ru",
                },
                "signal_sources": [
                    {
                        "alias": "AecInput1",
                        "subscription_attribute": "peaks",
                        "rows": [
                            {"channel_number": 1, "value": False},
                            {"channel_number": 2, "value": True},
                        ],
                    }
                ],
            }
        )

        for state in UIState:
            with self.subTest(state=state.value):
                self.window.set_ui_state(state, screen=codec)
                QApplication.processEvents()
                self.assertEqual(state, self.window.ui_state)
                self.assertEqual(state, codec.ui_state)
                self.assertEqual(
                    STATE_SPECS[state].indicator,
                    self.window.connection_indicator.status(),
                )

    def test_password_terminal_and_call_log_dialogs_construct_safely(self):
        from gui.dialogs import CallLogWindow

        with patch.object(QDialog, "exec_", return_value=QDialog.Rejected):
            self.window.show_password_dialog()

        with patch.object(self.window, "show_debug_window") as show_debug_window:
            for device_name in (
                "Huawei TE20",
                "Extron IN1804",
                "Aten PE8208AV",
            ):
                with self.subTest(device=device_name):
                    self.window.device_combo.setCurrentText(device_name)
                    self.window.show_debug_window()
                    QApplication.processEvents()

            self.assertEqual(3, show_debug_window.call_count)

        call_log = CallLogWindow(self.window, self.window.colors)
        call_log.set_call_records(
            [
                {
                    "room_number": f"Room {number}",
                    "start_time": "2026-06-29 12:00",
                    "duration": "00:05:00",
                    "speed": "2048",
                }
                for number in range(12)
            ]
        )
        self.assertEqual(call_log.MAX_ROWS, call_log.table.rowCount())
        self.assertEqual(
            f"Показаны последние {call_log.MAX_ROWS} звонков.",
            call_log.status_label.text(),
        )
        call_log.close()
        call_log.deleteLater()

class SavedPasswordDisclosureRegressionTest(unittest.TestCase):
    def test_legacy_saved_password_disclosure_path_is_absent(self):
        from gui.main_window import VCSDiagnosticApp

        synthetic_credential = {
            "username": "synthetic-gui-user",
            "password": "synthetic-gui-password",
        }

        with patch("gui.main_window.QMessageBox.information") as information:
            self.assertFalse(
                callable(getattr(VCSDiagnosticApp, "show_saved_passwords", None))
            )

        information.assert_not_called()
        self.assertNotIn(
            synthetic_credential["password"],
            str(information.call_args_list),
        )

    def test_main_window_prints_never_interpolate_password_values(self):
        import gui.main_window as main_window

        tree = ast.parse(inspect.getsource(main_window))
        password_prints = []
        for call in (
            node for node in ast.walk(tree) if isinstance(node, ast.Call)
        ):
            if not isinstance(call.func, ast.Name) or call.func.id != "print":
                continue
            if any(
                isinstance(node, ast.Name) and node.id == "password"
                for argument in (*call.args, *(item.value for item in call.keywords))
                for node in ast.walk(argument)
            ):
                password_prints.append(call.lineno)

        self.assertEqual([], password_prints)


if __name__ == "__main__":
    unittest.main()
