from __future__ import annotations

import os
import unittest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtCore import QEvent
    from PyQt5.QtWidgets import QApplication, QComboBox, QLineEdit, QWidget
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class CodecScreenOffscreenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")

    def setUp(self):
        from gui.theme import legacy_colors

        class Parent(QWidget):
            def __init__(self):
                super().__init__()
                self.colors = legacy_colors()
                self.device_combo = QComboBox(self)
                self.device_combo.addItems(
                    (
                        "Huawei TE-20",
                        "Huawei TE-40",
                        "CloudLink Bar 310",
                        "Polycom RPG 310",
                    )
                )
                self.ip_entry = QLineEdit(self)
                self.current_screen_type = None
                self.device_credentials = {}

        from gui.screens.codec_screen import CodecScreen

        self.parent_widget = Parent()
        self.screen = CodecScreen(self.parent_widget)
        self.screen.resize(900, 800)
        QApplication.processEvents()

    def tearDown(self):
        self.screen.stop_te20_monitor_audio_polling()
        self.screen.close()
        self.parent_widget.close()
        self.screen.deleteLater()
        self.parent_widget.deleteLater()
        QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        QApplication.processEvents()

    def _select_device(self, device_name):
        self.parent_widget.device_combo.setCurrentText(device_name)
        self.screen.update_parameters_display()
        QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        QApplication.processEvents()

    def test_all_codec_models_build_cards_and_keep_unique_rows(self):
        from gui.components import ParameterRow, SectionCard

        for device_name in (
            "Huawei TE-20",
            "Huawei TE-40",
            "CloudLink Bar 310",
            "Polycom RPG 310",
        ):
            with self.subTest(device=device_name):
                self._select_device(device_name)
                self.assertEqual(2, len(self.screen.findChildren(SectionCard)))
                names = list(self.screen.parameter_rows)
                self.assertEqual(len(names), len(set(names)))
                self.assertNotIn("Доп. параметр 15", names)
                self.assertIn("Журнал звонков", names)
                self.assertEqual(
                    len(names),
                    len(self.screen.findChildren(ParameterRow)),
                )

        self._select_device("Huawei TE-20")
        self.assertIn("Звук в помещении (микрофон)", self.screen.parameter_rows)
        self.assertIn(
            "Звук из динамиков (выход кодека)",
            self.screen.parameter_rows,
        )

    def test_update_data_updates_widgets_in_place_and_sip_state(self):
        self._select_device("Huawei TE-40")
        firmware_widget = self.screen.parameter_rows[
            "Версия прошивки"
        ].value_display

        self.screen.update_data(
            {
                "Версия ПО": "V3.1",
                "Модель": "TE40",
                "Серийный номер": "SERIAL",
                "MAC адрес": "00:11:22:33:44:55",
                "SIP регистрация": "Не зарегистрирован",
                "SIP адрес": "sip:1001@example.test",
                "Время работы": "5 дней",
                "Режим презентации": "Stop",
                "Громкость динамиков": "7",
                "Mute микрофона": "Unmuted",
            }
        )

        self.assertIs(
            firmware_widget,
            self.screen.parameter_rows["Версия прошивки"].value_display,
        )
        self.assertEqual("V3.1", firmware_widget.text())
        sip_value = self.screen.parameter_rows["SIP регистрация"].value_display
        self.assertEqual("error", sip_value.property("uiState"))
        self.assertEqual(
            "danger",
            self.screen.sip_status_indicators["SIP регистрация"].status(),
        )
        self.assertFalse(self.screen.sip_fix_buttons[0][1].isHidden())
        self.assertTrue(
            self.screen.presentation_buttons["Статус презентации"][
                "off"
            ].isChecked()
        )

    def test_controls_remain_connected_to_existing_handlers(self):
        self._select_device("Huawei TE-40")
        volume_calls = []
        presentation_calls = []
        self.screen.adjust_volume = (
            lambda param_name, direction: volume_calls.append(
                (param_name, direction)
            )
        )
        self.screen.set_presentation_state = presentation_calls.append

        self.screen.volume_buttons["Громкость динамиков"]["up"].click()
        self.screen.presentation_buttons["Статус презентации"]["on"].click()

        self.assertEqual(
            [("Громкость динамиков", "up")],
            volume_calls,
        )
        self.assertEqual(["on"], presentation_calls)

    def test_information_columns_stack_at_narrow_width(self):
        self.screen.scroll_area.resize(650, 700)
        self.screen._apply_responsive_layout()

        left_index = self.screen.info_grid.indexOf(self.screen.info_left_column)
        right_index = self.screen.info_grid.indexOf(self.screen.info_right_column)
        left_row, left_column, _, _ = self.screen.info_grid.getItemPosition(
            left_index
        )
        right_row, right_column, _, _ = self.screen.info_grid.getItemPosition(
            right_index
        )

        self.assertEqual((0, 0), (left_row, left_column))
        self.assertEqual((1, 0), (right_row, right_column))


if __name__ == "__main__":
    unittest.main()
