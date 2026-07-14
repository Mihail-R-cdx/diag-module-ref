from __future__ import annotations

import os
import time
import unittest
from unittest.mock import patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtCore import QEvent, QTimer
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
                        "Huawei TE20",
                        "Huawei TE40",
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
        if self.screen is not None:
            self.screen.stop_te20_monitor_audio_polling()
            self.screen.close()
            self.screen.deleteLater()
        self.parent_widget.close()
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
            "Huawei TE20",
            "Huawei TE40",
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

        self._select_device("Huawei TE20")
        self.assertIn("Звук в помещении (микрофон)", self.screen.parameter_rows)
        self.assertIn(
            "Звук из динамиков (выход кодека)",
            self.screen.parameter_rows,
        )

        self._select_device("Huawei TE40")
        self.assertIn(
            "Звук в помещении (микрофон)",
            self.screen.parameter_rows,
        )
        self.assertIn(
            "Звук из динамиков (выход кодека)",
            self.screen.parameter_rows,
        )
        self.assertNotIn(
            "Звук в помещении (микрофон)",
            self.screen.wake_buttons,
        )

    def test_te20_monitor_audio_uses_web_cadence_and_direct_field_mapping(self):
        self._select_device("Huawei TE20")

        self.assertEqual(
            2000,
            self.screen.monitor_audio_timer.interval(),
        )

        self.screen._update_monitor_audio_display(
            mic_value=20,
            speaker_value=0,
        )

        self.assertEqual(
            "9%",
            self.screen.parameter_rows[
                "Звук в помещении (микрофон)"
            ].value_display.text(),
        )
        self.assertEqual(
            "0%",
            self.screen.parameter_rows[
                "Звук из динамиков (выход кодека)"
            ].value_display.text(),
        )

    def test_te40_periodic_monitor_audio_decodes_json_string_payload(self):
        self._select_device("Huawei TE40")
        self.parent_widget.ip_entry.setText("link.ru")
        self.parent_widget.device_credentials = {
            "Huawei TE40": [{"username": "admin", "password": "admin"}]
        }
        self.parent_widget.current_credential_index = {"Huawei TE40": 0}

        class Handler:
            @staticmethod
            def send_command(command):
                self.assertEqual("get_monitor_audio_params", command)
                return {
                    "success": 1,
                    "data": '{"MicValueIndex":60,"SpeakerValueIndex":220}',
                }

        with (
            patch.object(self.screen, "_is_codec_screen_active", return_value=True),
            patch.object(
                self.screen,
                "_get_or_create_volume_handler",
                return_value=Handler(),
            ),
            patch.object(self.screen, "_update_monitor_audio_display") as update_display,
        ):
            self.screen.poll_te20_monitor_audio()

        update_display.assert_called_once_with(
            mic_value=60,
            speaker_value=220,
        )

    def test_te20_initial_monitor_audio_values_use_web_meter_scale(self):
        from core.parser import HuaweiTE20DataParser

        parsed = HuaweiTE20DataParser.parse_raw_data(
            {
                "monitor_mic_value": 20,
                "monitor_speaker_value": 220,
            }
        )

        self.assertEqual(
            "9%",
            parsed["Звук в помещении (микрофон)"],
        )
        self.assertEqual(
            "100%",
            parsed["Звук из динамиков (выход кодека)"],
        )

    def test_update_data_updates_widgets_in_place_and_sip_state(self):
        self._select_device("Huawei TE40")
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
                "SIP адрес": "sip:1001@link.ru",
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
        self.assertTrue(sip_value.isHidden())
        self.assertEqual(
            "danger",
            self.screen.sip_status_indicators["SIP регистрация"].status(),
        )
        self.assertEqual(
            "×",
            self.screen.sip_status_indicators["SIP регистрация"].text(),
        )
        self.assertFalse(self.screen.sip_fix_buttons[0][1].isHidden())
        self.assertTrue(
            self.screen.presentation_buttons["Статус презентации"][
                "off"
            ].isChecked()
        )

        self.screen.update_data({"SIP регистрация": "Зарегистрирован"})
        self.assertEqual(
            "✓",
            self.screen.sip_status_indicators["SIP регистрация"].text(),
        )
        self.assertTrue(self.screen.sip_fix_buttons[0][1].isHidden())

    def test_controls_remain_connected_to_existing_handlers(self):
        self._select_device("Huawei TE40")
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

    def test_presentation_enable_timer_reenables_buttons(self):
        self._select_device("Huawei TE40")
        param_name = "Статус презентации"
        self.screen.set_presentation_state = lambda _direction: None

        self.screen.on_presentation_button_clicked(param_name, "on")

        timer = self.screen._presentation_enable_timers[param_name]
        self.assertTrue(timer.isActive())
        self.assertEqual(1500, timer.interval())
        self.assertFalse(
            self.screen.presentation_buttons[param_name]["on"].isEnabled()
        )

        timer.timeout.emit()

        self.assertNotIn(param_name, self.screen._presentation_enable_timers)
        self.assertTrue(
            self.screen.presentation_buttons[param_name]["on"].isEnabled()
        )

    def test_presentation_enable_timer_replaces_same_parameter_timer(self):
        first_timer = self.screen._schedule_presentation_buttons_enable(
            "first"
        )
        self.assertIsNone(first_timer)
        first_timer = self.screen._presentation_enable_timers["first"]

        self.screen._schedule_presentation_buttons_enable("first")
        second_timer = self.screen._presentation_enable_timers["first"]

        self.assertIsNot(first_timer, second_timer)
        self.assertFalse(first_timer.isActive())
        self.assertTrue(second_timer.isActive())

    def test_presentation_enable_timers_for_different_parameters_are_independent(self):
        self.screen._schedule_presentation_buttons_enable("first")
        self.screen._schedule_presentation_buttons_enable("second")

        first_timer = self.screen._presentation_enable_timers["first"]
        second_timer = self.screen._presentation_enable_timers["second"]
        first_timer.timeout.emit()

        self.assertNotIn("first", self.screen._presentation_enable_timers)
        self.assertIs(
            second_timer,
            self.screen._presentation_enable_timers["second"],
        )
        self.assertTrue(second_timer.isActive())

    def test_presentation_enable_timer_is_destroyed_with_screen(self):
        self._select_device("Huawei TE40")
        param_name = "Статус презентации"
        self.screen.set_presentation_state = lambda _direction: None

        self.screen.on_presentation_button_clicked(param_name, "on")
        self.assertTrue(
            self.screen._presentation_enable_timers[param_name].isActive()
        )

        screen = self.screen
        self.screen = None
        screen.close()
        screen.deleteLater()
        QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        QApplication.processEvents()

    def test_information_columns_stack_at_narrow_width(self):
        self.screen.scroll_area.resize(650, 700)
        self.screen._apply_responsive_layout()

        firmware_index = self.screen.info_grid.indexOf(
            self.screen.info_firmware_column
        )
        left_index = self.screen.info_grid.indexOf(self.screen.info_left_column)
        right_index = self.screen.info_grid.indexOf(self.screen.info_right_column)
        firmware_position = self.screen.info_grid.getItemPosition(
            firmware_index
        )
        left_row, left_column, _, _ = self.screen.info_grid.getItemPosition(
            left_index
        )
        right_row, right_column, _, _ = self.screen.info_grid.getItemPosition(
            right_index
        )

        self.assertEqual((0, 0, 1, 1), firmware_position)
        self.assertEqual((1, 0), (left_row, left_column))
        self.assertEqual((2, 0), (right_row, right_column))

    def test_firmware_spans_info_card_and_detail_rows_align(self):
        from gui.theme import apply_theme

        apply_theme(self.app)
        self.parent_widget.resize(1100, 900)
        self.screen.resize(1000, 800)
        self.parent_widget.show()
        self.screen.show()
        self.screen.sip_fix_buttons[0][1].setVisible(True)
        QApplication.processEvents()
        self.screen._apply_responsive_layout()
        QApplication.processEvents()

        firmware_index = self.screen.info_grid.indexOf(
            self.screen.info_firmware_column
        )
        self.assertEqual(
            (0, 0, 1, 2),
            self.screen.info_grid.getItemPosition(firmware_index),
        )

        firmware_value = self.screen.parameter_rows[
            "Версия прошивки"
        ].value_display
        model_value = self.screen.parameter_rows[
            "Модель кодеков"
        ].value_display
        sip_value = self.screen.parameter_rows[
            "SIP адрес"
        ].value_display
        common_parent = self.screen.info_columns_widget
        firmware_left = firmware_value.mapTo(
            common_parent,
            firmware_value.rect().topLeft(),
        ).x()
        firmware_right = firmware_left + firmware_value.width()
        model_left = model_value.mapTo(
            common_parent,
            model_value.rect().topLeft(),
        ).x()
        sip_left = sip_value.mapTo(
            common_parent,
            sip_value.rect().topLeft(),
        ).x()
        sip_right = sip_left + sip_value.width()

        self.assertEqual(model_left, firmware_left)
        self.assertEqual(sip_right, firmware_right)

        firmware_row = self.screen.parameter_rows["Версия прошивки"]
        model_row = self.screen.parameter_rows["Модель кодеков"]
        serial_row = self.screen.parameter_rows["Серийный номер"]
        firmware_top = firmware_row.mapTo(
            common_parent,
            firmware_row.rect().topLeft(),
        ).y()
        model_top = model_row.mapTo(
            common_parent,
            model_row.rect().topLeft(),
        ).y()
        serial_top = serial_row.mapTo(
            common_parent,
            serial_row.rect().topLeft(),
        ).y()
        self.assertEqual(
            serial_top - (model_top + model_row.height()),
            model_top - (firmware_top + firmware_row.height()),
        )

        aligned_pairs = (
            ("Модель кодеков", "SIP регистрация"),
            ("Серийный номер", "SIP адрес"),
            ("MAC адрес", "Время работы"),
        )
        for left_name, right_name in aligned_pairs:
            with self.subTest(left=left_name, right=right_name):
                left_row = self.screen.parameter_rows[left_name]
                right_row = self.screen.parameter_rows[right_name]
                self.assertEqual(left_row.y(), right_row.y())
                self.assertEqual(left_row.height(), right_row.height())

        detail_rows = [
            self.screen.parameter_rows[name]
            for pair in aligned_pairs
            for name in pair
        ]
        self.assertEqual(
            1,
            len(
                {
                    row.value_display.height()
                    for row in detail_rows
                    if not row.value_display.isHidden()
                }
            ),
        )

        sip_value_height = self.screen.parameter_rows[
            "SIP адрес"
        ].value_display.height()
        fix_button = self.screen.sip_fix_buttons[0][1]
        self.assertEqual(sip_value_height, fix_button.height())

    def test_information_rows_use_wider_compact_value_fields(self):
        firmware_row = self.screen.parameter_rows[
            "Версия прошивки"
        ]
        sip_address_row = self.screen.parameter_rows[
            "SIP адрес"
        ]
        uptime_row = self.screen.parameter_rows[
            "Время работы"
        ]
        control_row = self.screen.parameter_rows[
            "Статус звонка"
        ]

        self.assertEqual(216, firmware_row.value_display.minimumWidth())
        self.assertEqual(238, sip_address_row.value_display.minimumWidth())
        self.assertEqual(238, uptime_row.value_display.minimumWidth())
        self.assertEqual(16777215, firmware_row.value_display.maximumWidth())
        self.assertEqual(32, firmware_row.value_display.maximumHeight())
        self.assertEqual(8, firmware_row.layout().contentsMargins().top())
        self.assertEqual(4, firmware_row.layout().contentsMargins().bottom())
        self.assertEqual(110, control_row.value_display.minimumWidth())

    def test_control_rows_share_common_value_column_edges(self):
        self.screen.scroll_area.resize(900, 800)
        self.screen._apply_responsive_layout()
        QApplication.processEvents()

        control_rows = [
            row
            for row in self.screen.parameter_rows.values()
            if row.property("alignedControls")
        ]
        self.assertTrue(control_rows)
        label_widths = {row.name_label.width() for row in control_rows}
        self.assertEqual(1, len(label_widths))
        self.assertTrue(label_widths.issubset({240, 360}))
        self.assertEqual(
            {0},
            {row.layout().columnStretch(0) for row in control_rows},
        )
        self.assertEqual(
            {1},
            {row.layout().columnStretch(1) for row in control_rows},
        )
        self.assertEqual(
            {16777215},
            {row.value_display.maximumWidth() for row in control_rows},
        )

    def test_polycom_speaker_button_uses_device_supported_step(self):
        self._select_device("Polycom RPG 310")
        self.screen.volume_values["Громкость динамиков"] = 48
        changes = []
        self.screen.set_volume_value = (
            lambda param_name, value: changes.append((param_name, value))
        )

        self.screen.adjust_volume("Громкость динамиков", "up")

        self.assertEqual([("Громкость динамиков", 50)], changes)

    def test_polycom_control_click_wraps_command_in_progress_dialog(self):
        self._select_device("Polycom RPG 310")
        calls = []
        marker = object()
        self.screen._show_polycom_command_progress = (
            lambda message: calls.append(("show", message)) or marker
        )
        self.screen._hide_polycom_command_progress = (
            lambda dialog: calls.append(("hide", dialog))
        )
        self.screen.adjust_volume = (
            lambda param_name, direction: calls.append(
                ("command", param_name, direction)
            )
        )

        self.screen.on_volume_button_clicked("Громкость динамиков", "up")

        self.assertEqual("show", calls[0][0])
        self.assertEqual("command", calls[1][0])
        self.assertEqual(("hide", marker), calls[2])

    def test_polycom_hides_microphone_control_when_connection_is_unknown(self):
        self._select_device("Polycom RPG 310")

        self.screen.update_data(
            {
                "Статус микрофона": "Не определено",
                "Mute микрофона": "Unmuted",
                "mic_mute": "off",
            }
        )

        microphone_button = self.screen.mute_buttons[
            self.screen._microphone_param_name()
        ]
        self.assertTrue(microphone_button.isHidden())
        self.assertEqual(
            "Не определено",
            self.screen.parameter_rows[
                self.screen._microphone_param_name()
            ].value_display.text(),
        )

    def test_polycom_distinguishes_disconnected_microphone_from_mute(self):
        self._select_device("Polycom RPG 310")

        self.screen.update_data(
            {
                "Статус микрофона": "Не подключён",
                "Mute микрофона": "Unmuted",
                "mic_mute": "off",
            }
        )

        mute_row = self.screen.parameter_rows[
            self.screen._microphone_param_name()
        ]
        self.assertEqual("Не подключено", mute_row.value_display.text())
        self.assertTrue(
            self.screen.mute_buttons[
                self.screen._microphone_param_name()
            ].isHidden()
        )

    def test_polycom_call_log_worker_keeps_heartbeat_responsive(self):
        self._select_device("Polycom RPG 310")
        self.parent_widget.ip_entry.setText("link.ru")
        self.parent_widget.device_credentials = {
            "Polycom RPG 310": [
                {"username": "admin", "password": "admin"}
            ]
        }
        self.parent_widget.current_credential_index = {
            "Polycom RPG 310": 0
        }
        self.parent_widget.get_current_credential_index = (
            lambda *_args: 0
        )

        class SlowHandler:
            def __init__(self, **_kwargs):
                pass

            def connect(self):
                time.sleep(0.2)

            def get_call_records(self):
                return []

            def disconnect(self):
                pass

        ticks = []
        timer = QTimer()
        timer.setInterval(20)
        timer.timeout.connect(lambda: ticks.append(time.monotonic()))
        timer.start()
        with patch(
            "handlers.polycom.rpg310.PolycomRPG310Handler",
            SlowHandler,
        ):
            self.screen.open_call_log_window()
            deadline = time.monotonic() + 1
            while (
                getattr(self.screen, "_polycom_call_log_loading", False)
                and time.monotonic() < deadline
            ):
                QApplication.processEvents()
                time.sleep(0.005)
        timer.stop()
        QApplication.processEvents()

        self.assertGreaterEqual(len(ticks), 5)
        gaps = [
            current - previous
            for previous, current in zip(ticks, ticks[1:])
        ]
        self.assertLess(max(gaps, default=0), 0.1)


if __name__ == "__main__":
    unittest.main()
