"""Focused regressions for truthful Matrix room diagnostics."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from core.parser import ExtronIN1804DataParser
from handlers.extron.in1804 import ExtronIN1804Handler
from gui.diagnostic_dispatch import dispatch_entry_for_model
from gui.room_diagnostic_tree import normalize_matrix_presentation

try:
    from PyQt5.QtWidgets import QApplication, QPushButton, QTableWidget, QWidget
except ImportError:  # pragma: no cover
    QApplication = None


class MatrixNormalizationTests(unittest.TestCase):
    def test_exact_current_connection_grammar_is_fail_closed(self):
        accept = ExtronIN1804Handler._parse_current_connection
        for response, expected in (("1", 1), ("In4 All", 4), ("!\r\nIn1 All\r\n", 1)):
            with self.subTest(response=response):
                self.assertEqual(expected, accept(response, 4))
        for response in ("", "!", "1\n2", "In1 All\nnoise", "result 1", "In01 All", "5", "In1 All 2"):
            with self.subTest(response=response):
                self.assertIsNone(accept(response, 4))

    def test_parser_removes_fabricated_defaults_and_keeps_real_zero(self):
        parser = ExtronIN1804DataParser()
        unknown = parser.parse({"device_info": {}, "inputs_num": 8, "connections": []})
        self.assertIsNone(unknown["model"])
        self.assertIsNone(unknown["temperature"])
        self.assertIsNone(unknown["inputs_num"])
        self.assertIsNone(unknown["current_connection"])
        accepted = parser.parse({
            "device_info": {"model": "IN1804", "temperature": 0},
            "inputs_num": 4,
            "connections": [1],
            "input_hdcp_status": ["2", "1", "0", "bad"],
        })
        self.assertEqual(0, accepted["temperature"])
        self.assertEqual(4, accepted["inputs_num"])
        self.assertEqual(1, accepted["current_connection"])
        self.assertEqual([True, False, False, None], accepted["hdcp_present"])


class MatrixPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if QApplication is not None:
            cls.app = QApplication.instance() or QApplication([])

    def test_rows_use_proven_count_and_presence_only_hdcp(self):
        self.assertEqual([], normalize_matrix_presentation({"inputs_num": None}))
        rows = normalize_matrix_presentation({
            "inputs_num": 2,
            "input_names": ["Laptop", "Camera"],
            "signal_status": {1: {"has_signal": True}, 2: {"has_signal": None}},
            "hdcp_present": [True, None],
            "current_connection": 1,
        })
        self.assertEqual((1, "есть", "есть", "Laptop", "активен"), rows[0])
        self.assertEqual((2, "Нет данных", "Нет данных", "Camera", "не выбран"), rows[1])

    def test_exact_registry_declares_matrix_room_bindings(self):
        entry = dispatch_entry_for_model("Extron IN1804")
        self.assertEqual("matrix_room_route", entry.mutation_binding_key)
        self.assertEqual("matrix_room_route_reconcile", entry.reconciliation_binding_key)

    @unittest.skipIf(QApplication is None, "PyQt5 is not installed")
    def test_room_dashboard_has_three_cards_and_truthful_table(self):
        from core.equipment_inventory import EquipmentInventory, EquipmentInventoryMetadata, EquipmentRecord
        from core.room_diagnostic_tree import DeviceRowStatus, RoomModelCapability, build_room_session_from_room
        from gui.room_diagnostic_tree import RoomDiagnosticTreeWidget

        record = EquipmentRecord("matrix", "Extron IN1804", "Extron IN1804", "192.0.2.4", None, None, "r", "Room", "matrix", None, None, None, None)
        inventory = EquipmentInventory.from_records((record,), EquipmentInventoryMetadata(4, "sha256:" + "a" * 64))
        session = build_room_session_from_room(
            inventory=inventory, room_id="r", generation=1,
            capabilities={"Extron IN1804": RoomModelCapability("Extron IN1804", "matrix", "matrix_controller", "matrix_one_shot")},
        )
        row = session.rows[0]
        row.status = DeviceRowStatus.CONNECTED
        row.network_actions_enabled = True
        row.accepted_snapshot = {
            "model": "IN1804", "inputs_num": 2, "input_names": ["Laptop", "Camera"],
            "output_names": ["Projector"], "signal_status": {1: {"has_signal": True}},
            "hdcp_present": [True, False], "current_connection": 1,
        }
        session.expanded_record_id = row.record_id
        widget = RoomDiagnosticTreeWidget()
        self.addCleanup(widget.deleteLater)
        widget.render(session)
        projection = widget.tree.itemWidget(widget.tree.topLevelItem(0).child(0), 0)
        self.assertIsNotNone(projection.findChild(QTableWidget, "roomMatrixRouting"))
        table = projection.findChild(QTableWidget, "roomMatrixRouting")
        self.assertEqual(["№", "Сигнал", "HDCP", "Входы", "Projector"], [table.horizontalHeaderItem(i).text() for i in range(5)])
        self.assertEqual("есть", table.item(0, 2).text())
        self.assertEqual("нет", table.item(1, 2).text())
        self.assertIsNotNone(projection.findChild(QWidget, "roomMatrixDashboard"))
        reboot = projection.findChild(QPushButton, "roomMatrixRebootButton")
        self.assertIsNotNone(reboot)
        self.assertFalse(reboot.isEnabled())


if __name__ == "__main__":
    unittest.main()
