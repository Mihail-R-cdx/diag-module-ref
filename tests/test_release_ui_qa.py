from __future__ import annotations

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
        self.assertEqual(7, len(selectable_devices))

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
        self.window.device_combo.setCurrentText("Huawei TE-40")
        codec.update_data(
            {
                "Версия ПО": "V3.1",
                "Модель": "TE40",
                "Серийный номер": "QA-SERIAL",
                "MAC адрес": "00:11:22:33:44:55",
                "SIP регистрация": "Зарегистрирован",
                "SIP адрес": "sip:qa@example.test",
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
                    "ip_address": "192.0.2.10",
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
                    "ip_address": "192.0.2.42",
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

        for device_name in (
            "Huawei TE-20",
            "Extron IN1804",
            "Aten PE8208AV",
        ):
            with self.subTest(device=device_name):
                self.window.device_combo.setCurrentText(device_name)
                self.window.show_debug_window()
                QApplication.processEvents()

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


if __name__ == "__main__":
    unittest.main()
