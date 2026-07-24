from __future__ import annotations

import os
import unittest
from unittest.mock import patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import (
        QApplication,
        QComboBox,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QTableWidget,
        QWidget,
    )
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class DeviceScreensOffscreenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")

    def setUp(self):
        from gui.theme import legacy_colors

        class FakeMatrixHandler:
            def __init__(self):
                self.switches = []

            def set_connection(self, output_number, input_number):
                self.switches.append((output_number, input_number))

            def get_connections(self):
                return [2]

        class Parent(QWidget):
            def __init__(self):
                super().__init__()
                self.colors = legacy_colors()
                self.device_combo = QComboBox(self)
                self.device_combo.addItems(
                    (
                        "Extron IN1804",
                        "Aten PE8208AV",
                        "Extron IPL T PCS4i",
                        "Biamp Tesira Forte CI",
                    )
                )
                self.ip_entry = QLineEdit("link.ru", self)
                self.device_credentials = {
                    "Extron IN1804": [
                        {"username": "admin", "password": "admin"}
                    ]
                }
                self.matrix_handler = FakeMatrixHandler()
                self.pdu_commands = []
                self.refresh_calls = 0

            def get_current_credential_index(self, device_name, ip_address):
                return 0

            def ensure_matrix_persistent_handler(self, **kwargs):
                return self.matrix_handler

            def control_pdu_outlet(self, number, command):
                self.pdu_commands.append((number, command))

            def refresh_data(self):
                self.refresh_calls += 1

        self.parent_widget = Parent()
        self.widgets = []

    def tearDown(self):
        for widget in self.widgets:
            widget.close()
            widget.deleteLater()
        self.parent_widget.close()
        self.parent_widget.deleteLater()
        QApplication.processEvents()

    def _track(self, widget):
        self.widgets.append(widget)
        widget.resize(950, 950)
        widget.show()
        QApplication.processEvents()
        return widget

    def test_matrix_updates_cards_and_emits_route_intent(self):
        from gui.components import SectionCard
        from gui.screens.matrix_screen import MatrixScreen

        screen = self._track(MatrixScreen(self.parent_widget))
        screen.update_data(
            {
                "inputs_num": 8,
                "input_names": [f"Input {number}" for number in range(1, 9)],
                "output_names": ["Main Output"],
                "current_connection": 3,
                "signal_status": {
                    1: {"has_signal": True},
                    2: {"has_signal": False},
                },
                "input_hdcp_status": ["2"] * 8,
                "input_hdcp_auth": [1] * 8,
                "model": "IN1804",
                "temperature": 41,
                "connection_protocol": "SSH",
            }
        )

        self.assertEqual(2, len(screen.findChildren(SectionCard)))
        self.assertEqual("IN1804", screen.model_value.text())
        self.assertEqual("41°C", screen.temp_value.text())
        self.assertEqual("SSH", screen.protocol_value.text())
        self.assertEqual("●", screen.matrix_table.item(2, 3).text())
        self.assertEqual("", screen.matrix_table.styleSheet())

        intents = []
        screen.routeRequested.connect(lambda output, input_: intents.append((output, input_)))
        screen.on_output_cell_clicked(4, 3)
        self.assertEqual([(1, 5)], intents)
        self.assertEqual([], self.parent_widget.matrix_handler.switches)

    def test_pdu_updates_statuses_and_preserves_all_commands(self):
        from gui.components import SectionCard, StatusIndicator
        from gui.screens.pdu_screen import PDUScreen

        self.parent_widget.device_combo.setCurrentText("Aten PE8208AV")
        screen = self._track(PDUScreen(self.parent_widget))
        screen.update_data(
            {
                "device_info": {
                    "model": "PE8208AV",
                    "ip_address": "link.ru",
                    "firmware": "2.4.1",
                    "connected": True,
                },
                "outlets": [
                    {"number": 1, "name": "Codec", "status": "on"},
                    {"number": 2, "name": "Display", "status": "off"},
                ],
            }
        )

        self.assertEqual(3, len(screen.findChildren(SectionCard)))
        self.assertEqual("2.4.1", screen.info_labels["firmware"].text())
        self.assertEqual("Подключено", screen.info_labels["status"].text())
        self.assertEqual(
            "success",
            screen.outlets_table.cellWidget(0, 1).property("status"),
        )
        self.assertIsInstance(
            screen.outlets_table.cellWidget(1, 1), StatusIndicator
        )

        captured_intents = []
        screen.outletMutationRequested.connect(
            lambda outlet, command: captured_intents.append((outlet, command))
        )
        expected = ((3, "on"), (4, "off"), (5, "reboot"))
        with patch.object(
            QMessageBox, "question", return_value=QMessageBox.Yes
        ):
            for column, command in expected:
                button = screen.outlets_table.cellWidget(0, column)
                self.assertIsInstance(button, QPushButton)
                button.click()
        self.assertEqual(
            [(1, "on"), (1, "off"), (1, "reboot")],
            captured_intents,
        )
        self.assertEqual([], self.parent_widget.pdu_commands)
        self.assertEqual("", screen.outlets_table.styleSheet())

    def test_pcs4i_pdu_renders_four_outlets_without_reboot_control(self):
        from gui.screens.pdu_screen import PDUScreen

        self.parent_widget.device_combo.setCurrentText("Extron IPL T PCS4i")
        screen = self._track(PDUScreen(self.parent_widget))
        screen.update_data(
            {
                "device_info": {
                    "model": "IPL T PCS4i",
                    "ip_address": "192.0.2.44",
                    "connected": True,
                },
                "capabilities": {
                    "refresh": True,
                    "on": True,
                    "off": True,
                    "reboot": False,
                },
                "outlets": [
                    {"number": number, "name": f"Receptacle {number}", "status": "off"}
                    for number in range(1, 5)
                ],
            }
        )

        self.assertEqual(4, screen.outlets_table.rowCount())
        self.assertTrue(screen.outlets_table.isColumnHidden(5))
        self.assertIsInstance(screen.outlets_table.cellWidget(0, 3), QPushButton)
        self.assertIsInstance(screen.outlets_table.cellWidget(0, 4), QPushButton)
        self.assertIsNone(screen.outlets_table.cellWidget(0, 5))

    def test_pdu_reboot_column_tracks_model_capabilities(self):
        from gui.screens.pdu_screen import PDUScreen

        screen = self._track(PDUScreen(self.parent_widget))
        aten_data = {
            "capabilities": {"refresh": True, "on": True, "off": True, "reboot": True},
            "outlets": [{"number": 1, "name": "Outlet 1", "status": "off"}],
        }
        pcs4i_data = {
            "capabilities": {"refresh": True, "on": True, "off": True, "reboot": False},
            "outlets": [{"number": 1, "name": "Розетка 1", "status": "off"}],
        }

        screen.update_data(aten_data)
        self.assertFalse(screen.outlets_table.isColumnHidden(5))
        self.assertIsInstance(screen.outlets_table.cellWidget(0, 5), QPushButton)

        screen.update_data(pcs4i_data)
        self.assertTrue(screen.outlets_table.isColumnHidden(5))
        self.assertIsNone(screen.outlets_table.cellWidget(0, 5))

        screen.update_data(aten_data)
        self.assertFalse(screen.outlets_table.isColumnHidden(5))
        self.assertIsInstance(screen.outlets_table.cellWidget(0, 5), QPushButton)

    def test_pdu_bulk_buttons_align_with_action_columns_and_keep_command_mapping(self):
        from gui.screens.pdu_screen import PDUScreen

        screen = self._track(PDUScreen(self.parent_widget))
        aten_data = {
            "capabilities": {"refresh": True, "on": True, "off": True, "reboot": True},
            "outlets": [{"number": 1, "name": "Outlet 1", "status": "off"}],
        }
        pcs4i_data = {
            "capabilities": {"refresh": True, "on": True, "off": True, "reboot": False},
            "outlets": [{"number": 1, "name": "Receptacle 1", "status": "off"}],
        }

        screen.update_data(aten_data)
        action_width = screen.ACTION_BUTTON_WIDTH
        on_button = screen.outlets_table.cellWidget(0, 3)
        off_button = screen.outlets_table.cellWidget(0, 4)
        reboot_button = screen.outlets_table.cellWidget(0, 5)

        self.assertEqual(0, screen.bulk_layout.horizontalSpacing())
        self.assertIs(screen.bulk_layout.itemAtPosition(0, 3).widget(), screen.btn_bulk_on)
        self.assertIs(screen.bulk_layout.itemAtPosition(0, 4).widget(), screen.btn_bulk_off)
        for button in (on_button, off_button, screen.btn_bulk_on, screen.btn_bulk_off):
            self.assertEqual(action_width, button.minimumWidth())
            self.assertEqual(action_width, button.maximumWidth())
        self.assertEqual(action_width, reboot_button.minimumWidth())
        self.assertEqual(action_width, screen.outlets_table.columnWidth(3))
        self.assertEqual(action_width, screen.outlets_table.columnWidth(4))
        self.assertEqual(action_width, screen.outlets_table.columnWidth(5))

        captured = []
        screen.bulk_control_signal.connect(captured.append)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            screen.btn_bulk_on.click()
            screen.btn_bulk_off.click()
        self.assertEqual(["on", "off"], captured)

        screen.update_data(pcs4i_data)
        self.assertTrue(screen.outlets_table.isColumnHidden(5))
        self.assertIs(screen.bulk_layout.itemAtPosition(0, 3).widget(), screen.btn_bulk_on)
        self.assertIs(screen.bulk_layout.itemAtPosition(0, 4).widget(), screen.btn_bulk_off)
        self.assertEqual(action_width, screen.outlets_table.columnWidth(3))
        self.assertEqual(action_width, screen.outlets_table.columnWidth(4))
        self.assertEqual(0, screen.bulk_layout.columnMinimumWidth(5))

    def test_pdu_outlet_name_column_is_center_aligned(self):
        from gui.screens.pdu_screen import PDUScreen

        screen = self._track(PDUScreen(self.parent_widget))
        screen.update_data(
            {
                "outlets": [
                    {"number": 1, "name": "Codec", "status": "on"},
                ]
            }
        )

        name_item = screen.outlets_table.item(0, 2)
        self.assertIsNotNone(name_item)
        alignment = int(name_item.textAlignment())
        self.assertTrue(alignment & int(Qt.AlignHCenter))
        self.assertTrue(alignment & int(Qt.AlignVCenter))

    def test_audio_dsp_is_read_only_and_rebuilds_source_cards(self):
        from gui.components import EmptyState, SectionCard
        from gui.screens.audio_dsp_screen import AudioDSPScreen

        screen = self._track(AudioDSPScreen(self.parent_widget))
        payload = {
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
                },
                {
                    "alias": "AudioMeter1",
                    "subscription_attribute": "levels",
                    "rows": [{"channel_number": 1, "value": -42.5}],
                },
            ],
        }
        screen.update_data(payload)

        self.assertEqual(2, len(screen.source_cards))
        self.assertTrue(
            all(isinstance(card, SectionCard) for card in screen.source_cards)
        )
        self.assertEqual(
            2, len(screen.findChildren(QTableWidget))
        )
        self.assertEqual([], screen.findChildren(QPushButton))
        self.assertTrue(screen.model_value.isReadOnly())
        self.assertTrue(screen.ip_value.isReadOnly())
        self.assertEqual(
            "", screen.findChild(QTableWidget).styleSheet()
        )

        screen.clear_data()
        screen.update_data(
            {"device_info": payload["device_info"], "signal_sources": []}
        )
        self.assertEqual(0, len(screen.source_cards))
        self.assertIsNotNone(screen.findChild(EmptyState))

    def test_tables_fit_base_screen_width_without_horizontal_scroll(self):
        from gui.screens.matrix_screen import MatrixScreen
        from gui.screens.pdu_screen import PDUScreen

        matrix = self._track(MatrixScreen(self.parent_widget))
        pdu = self._track(PDUScreen(self.parent_widget))
        pdu.update_data(
            {
                "outlets": [
                    {"number": number, "status": "on", "name": f"Outlet {number}"}
                    for number in range(1, 9)
                ]
            }
        )
        QApplication.processEvents()

        self.assertEqual(
            Qt.ScrollBarAlwaysOff,
            matrix.matrix_table.horizontalScrollBarPolicy(),
        )
        self.assertEqual(
            Qt.ScrollBarAlwaysOff,
            pdu.outlets_table.horizontalScrollBarPolicy(),
        )


if __name__ == "__main__":
    unittest.main()
