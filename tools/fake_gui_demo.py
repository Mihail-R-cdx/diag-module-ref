"""Launch the GUI with representative local data and no device I/O."""

from __future__ import annotations

import sys

from PyQt5.QtWidgets import QApplication

from gui.main_window import VCSDiagnosticApp
from gui.theme import apply_theme


class FakeCodecHandler:
    def __init__(self):
        self.command_logger = None
        self.speaker_volume = 12
        self.microphone_volume = 8
        self.presentation = "Stop"

    def connect(self):
        return True

    def disconnect(self):
        return None

    def set_speaker_volume(self, value):
        self.speaker_volume = value
        return True

    def get_speaker_volume(self):
        return self.speaker_volume

    def set_microphone_volume(self, value):
        self.microphone_volume = value
        return True

    def get_microphone_volume(self):
        return self.microphone_volume

    def get_audio_status(self):
        return {
            "microphone_volume": self.microphone_volume,
            "mute": "Off",
        }

    def set_presentation(self, command):
        self.presentation = command
        return True

    def get_presentation_status(self):
        return self.presentation

    def get_sleep_mode(self):
        return "Off"

    def wake_up(self):
        return True

    def get_call_records(self):
        return [
            {
                "room_number": f"Переговорная {number}",
                "start_time": f"29.06.2026 {9 + number:02d}:15",
                "duration": f"00:{4 + number:02d}:20",
                "speed": "2048 kbps",
            }
            for number in range(1, 7)
        ]


class FakeMatrixHandler:
    def __init__(self):
        self.current_input = 3

    def is_connected(self):
        return True

    def set_connection(self, output_number, input_number):
        self.current_input = input_number

    def get_connections(self):
        return [self.current_input]

    def send_command(self, command):
        return {"success": True, "command": command}

    def disconnect(self):
        return None


class FakeDataApp(VCSDiagnosticApp):
    def __init__(self):
        self.fake_codec_handler = FakeCodecHandler()
        self.fake_matrix_handler = FakeMatrixHandler()
        super().__init__()
        self.device_combo.currentTextChanged.connect(self.load_fake_data)
        self.refresh_btn.clicked.disconnect()
        self.refresh_btn.clicked.connect(self.load_fake_data)
        self.ip_entry.returnPressed.disconnect()
        self.ip_entry.returnPressed.connect(self.load_fake_data)
        self.device_combo.setCurrentText("Huawei TE40")
        self.load_fake_data()

    def refresh_data(self):
        self.load_fake_data()

    def ensure_matrix_persistent_handler(self, **kwargs):
        return self.fake_matrix_handler

    def control_pdu_outlet(self, outlet_num, command):
        screen = self.screens["pdu"]
        for outlet in screen.outlets:
            if outlet.get("number") != outlet_num:
                continue
            if command == "on":
                outlet["status"] = "on"
            elif command == "off":
                outlet["status"] = "off"
            elif command == "reboot":
                outlet["status"] = "on"
            break
        screen.update_outlets_table()
        self.set_connection_status(
            "success",
            f"Демо-команда {command!r} для розетки {outlet_num}",
        )

    def load_fake_data(self, *_args):
        device_name = self.device_combo.currentText()
        screen_type = self.device_to_screen.get(device_name)
        if screen_type is None:
            return

        if screen_type == "codec":
            screen = self.screens["codec"]
            screen._get_or_create_volume_handler = (
                lambda *args, **kwargs: self.fake_codec_handler
            )
            screen.update_data(self._codec_data(device_name))
        elif screen_type == "matrix":
            screen = self.screens["matrix"]
            screen.update_data(self._matrix_data())
        elif screen_type == "pdu":
            screen = self.screens["pdu"]
            screen.update_data(self._pdu_data())
        else:
            screen = self.screens["audio_dsp"]
            screen.update_data(self._audio_dsp_data())

        self.current_screen_type = screen_type
        self.current_screen = screen
        self.screen_container.setCurrentWidget(screen)
        self.set_connection_status(
            "success",
            f"Демонстрационные данные: {device_name}",
        )
        self.setWindowTitle(
            f"Диагностический модуль ММК — ДЕМО БЕЗ СЕТИ — {device_name}"
        )

    @staticmethod
    def _codec_data(device_name):
        model_names = {
            "Huawei TE20": "HUAWEI TE20",
            "Huawei TE40": "HUAWEI TE40",
            "CloudLink Bar 310": "CloudLink Bar 310",
            "Polycom RPG 310": "RealPresence Group 310",
        }
        return {
            "Версия ПО": "V3.1.5678",
            "Модель": model_names.get(device_name, device_name),
            "Серийный номер": "DEMO-2026-0629",
            "MAC адрес": "00:1A:2B:3C:4D:5E",
            "SIP регистрация": "Зарегистрирован",
            "SIP адрес": "sip:1001@link.ru",
            "Время работы": "15 дн. 04:32:18",
            "Температура": "42°C",
            "Скорость сети": "1000 Мбит/с",
            "Статус звонка": "Не в звонке",
            "Режим презентации": "Stop",
            "Громкость динамиков": "12",
            "Громкость микрофона": "8",
            "Mute микрофона": "Unmuted",
            "Статус микрофона": "Включен",
            "Статус камеры": "Подключена",
            "Звук в помещении (микрофон)": "-38.2 dB",
            "Звук из динамиков (выход кодека)": "-24.7 dB",
            "power_status": "On",
        }

    @staticmethod
    def _matrix_data():
        return {
            "inputs_num": 8,
            "input_names": [
                "Ноутбук 1",
                "Ноутбук 2",
                "Apple TV",
                "ВКС система",
                "Документ-камера",
                "Системный ПК",
                "Резерв 1",
                "Резерв 2",
            ],
            "output_names": ["Главный экран"],
            "current_connection": 3,
            "signal_status": {
                number: {"has_signal": number in {1, 3, 4, 6}}
                for number in range(1, 9)
            },
            "input_hdcp_status": ["2", "0", "2", "2", "0", "2", "0", "0"],
            "input_hdcp_auth": [1, 0, 1, 1, 0, 1, 0, 0],
            "model": "Extron IN1804",
            "temperature": 41,
            "connection_protocol": "SSH · DEMO",
        }

    @staticmethod
    def _pdu_data():
        names = [
            "Кодек",
            "Основной дисплей",
            "Резервный дисплей",
            "Матрица",
            "Audio DSP",
            "Камера",
            "Системный ПК",
            "Резерв",
        ]
        return {
            "device_info": {
                "model": "Aten PE8208AV",
                "ip_address": "link.ru",
                "firmware": "2.4.1-demo",
                "connected": True,
            },
            "outlets": [
                {
                    "number": number,
                    "name": names[number - 1],
                    "status": "on" if number not in {3, 8} else "off",
                }
                for number in range(1, 9)
            ],
        }

    @staticmethod
    def _audio_dsp_data():
        return {
            "device_info": {
                "model": "Biamp Tesira Forte CI",
                "ip_address": "link.ru",
            },
            "signal_sources": [
                {
                    "alias": "AecInput1",
                    "subscription_attribute": "peaks",
                    "rows": [
                        {"channel_number": 1, "value": True},
                        {"channel_number": 2, "value": False},
                    ],
                },
                {
                    "alias": "AudioMeter1",
                    "subscription_attribute": "levels",
                    "rows": [
                        {"channel_number": 1, "value": -32.5},
                        {"channel_number": 2, "value": -47.1},
                    ],
                },
            ],
        }


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    apply_theme(app)
    window = FakeDataApp()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
