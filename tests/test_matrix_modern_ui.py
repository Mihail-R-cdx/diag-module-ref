"""Focused regressions for truthful Matrix room diagnostics."""

from __future__ import annotations

import os
import unittest
from threading import Event
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from core.parser import ExtronIN1804DataParser
from handlers.extron.in1804 import ExtronIN1804Handler
from gui.diagnostic_dispatch import dispatch_entry_for_model
from gui.room_diagnostic_tree import normalize_matrix_presentation

try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication, QPushButton, QTableWidget, QWidget
except ImportError:  # pragma: no cover
    QApplication = None


class MatrixNormalizationTests(unittest.TestCase):
    def test_exact_current_connection_grammar_is_fail_closed(self):
        accept = ExtronIN1804Handler._parse_current_connection
        for response, expected in (
            ("1", 1), ("4", 4), ("In1 All", 1), ("In4 All", 4),
            ("!\r\n1\r\n", 1), ("!\r\nIn1 All\r\n", 1),
        ):
            with self.subTest(response=response):
                self.assertEqual(expected, accept(response, 4))
        for response in (
            "", "!", "1\n2", "In1 All\nnoise", "result 1", "In01 All",
            "5", "In1 All 2", "In1All", "In 1 All", "!\n!\n1",
        ):
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

    def test_parser_keeps_general_information_unknown_until_current_evidence(self):
        parser = ExtronIN1804DataParser()
        for model, temperature in ((None, None), ("Unknown", None), ("", "bad")):
            with self.subTest(model=model, temperature=temperature):
                parsed = parser.parse({"device_info": {"model": model, "temperature": temperature}})
                self.assertIsNone(parsed["model"])
                self.assertIsNone(parsed["temperature"])

    def test_only_recognized_matching_model_capability_proves_input_count(self):
        parser = ExtronIN1804DataParser()
        cases = (
            (None, 8, None),
            ("Unknown", 8, None),
            ("Unrecognized Matrix", 8, None),
            ("Extron IN1804", 4, 4),
            ("Extron IN1804", 8, None),
        )
        for model, count, expected in cases:
            with self.subTest(model=model, count=count):
                data = parser.parse({"device_info": {"model": model}, "inputs_num": count})
                self.assertEqual(expected, data["inputs_num"])

    def test_handler_preserves_existing_hdcp_reads_and_status_unknown(self):
        handler = ExtronIN1804Handler("192.0.2.4")
        handler.inputs_num = 1
        commands = []

        def send(command, **_kwargs):
            commands.append(command)
            return {"success": True, "response": {"wE1HDCP": "1", "wI1HDCP": "2", "wO1HDCP": "1"}[command]}

        handler.send_command = send
        with patch("handlers.extron.in1804.time.sleep", lambda _value: None):
            evidence = handler.get_hdcp_info()
        self.assertEqual(["wE1HDCP", "wI1HDCP", "wO1HDCP"], commands)
        self.assertEqual([1], evidence["input_auth"])
        self.assertEqual(["2"], evidence["input_status"])
        self.assertEqual("1", evidence["output_status"])
        self.assertEqual(True, ExtronIN1804DataParser._normalize_hdcp(evidence["input_status"][0]))
        self.assertIsNone(ExtronIN1804DataParser._normalize_hdcp(None))


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
        intents = []
        widget.matrixRouteRequested.connect(lambda record_id, output, input_number: intents.append((record_id, output, input_number)))
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
        reboot.click()
        self.assertEqual([], intents)
        self.assertIsNone(projection.findChild(QPushButton, "roomMatrixExtendedButton"))
        table.cellClicked.emit(0, 4)
        self.assertEqual([], intents)
        table.cellClicked.emit(1, 4)
        self.assertEqual([(row.record_id, 1, 2)], intents)

        dashboard = projection.findChild(QWidget, "roomMatrixDashboard")
        widget.resize(1400, 800)
        widget.show()
        self.app.processEvents()
        dashboard.resize(1400, 400)
        dashboard.layout().setGeometry(dashboard.contentsRect())
        dashboard.layout().activate()
        info, matrix, actions = (dashboard.layout().itemAt(index).widget() for index in range(3))
        self.assertGreater(matrix.width(), info.width())
        self.assertGreater(matrix.width(), actions.width())
        widths = [table.columnWidth(column) / table.viewport().width() for column in range(5)]
        for actual, expected in zip(widths, (0.08, 0.19, 0.17, 0.27, 0.29)):
            self.assertAlmostEqual(expected, actual, delta=0.03)

        for changes in (
            {"stale": True},
            {"interaction_blocked": True},
            {"unconfirmed_after_command": True},
            {"network_actions_enabled": False},
        ):
            with self.subTest(changes=changes):
                row.stale = False
                row.interaction_blocked = False
                row.unconfirmed_after_command = False
                row.network_actions_enabled = True
                for attribute, value in changes.items():
                    setattr(row, attribute, value)
                widget.render(session)
                blocked_table = widget.tree.itemWidget(widget.tree.topLevelItem(0).child(0), 0).findChild(QTableWidget, "roomMatrixRouting")
                blocked_table.cellClicked.emit(1, 4)
                self.assertEqual([(row.record_id, 1, 2)], intents)

    @unittest.skipIf(QApplication is None, "PyQt5 is not installed")
    def test_standalone_unknown_input_count_has_no_rows_or_route_intent(self):
        from gui.screens.matrix_screen import MatrixScreen

        screen = MatrixScreen()
        self.addCleanup(screen.deleteLater)
        intents = []
        screen.routeRequested.connect(lambda output, input_number: intents.append((output, input_number)))
        self.assertEqual(0, screen.matrix_table.rowCount())
        screen.on_output_cell_clicked(0, 3)
        self.assertEqual([], intents)
        screen.update_data({"inputs_num": None, "current_connection": None})
        self.assertEqual(0, screen.matrix_table.rowCount())
        screen.on_output_cell_clicked(0, 3)
        self.assertEqual([], intents)
        screen.update_data({"inputs_num": 4, "input_names": ["A", "B", "C", "D"], "current_connection": 2})
        self.assertEqual(4, screen.matrix_table.rowCount())
        screen.on_output_cell_clicked(0, 3)
        self.assertEqual([(1, 1)], intents)
        screen.update_data({"inputs_num": None})
        self.assertEqual(0, screen.matrix_table.rowCount())
        screen.on_output_cell_clicked(0, 3)
        self.assertEqual([(1, 1)], intents)


class MatrixMutationOrderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if QApplication is not None:
            cls.app = QApplication.instance() or QApplication([])

    def test_pre_send_auth_rejection_is_published_after_handler_release(self):
        from core.exceptions import AuthenticationError
        from core.room_interaction import RoomInteractionContext, RoomInteractionKind
        from gui.room_diagnostic_controller import RoomAuthenticationRejected, RoomDiagnosticController

        events = []

        class Handler:
            def __init__(self, *_args, **_kwargs):
                events.append(f"acquire-{len([event for event in events if event.startswith('acquire')]) + 1}")

            def connect(self):
                raise AuthenticationError("typed rejection")

            def disconnect(self):
                events.append("release")

        context = RoomInteractionContext("inventory", 1, "record", "Extron IN1804", "192.0.2.4", 1, 1, 1, RoomInteractionKind.MUTATION)
        controller = RoomDiagnosticController(candidate_provider=lambda *_: (), ping=lambda _ip: True, persist_success=lambda *_: None, starting_index=lambda *_: 0)
        published = []

        def accepted(_context, success, data, _lost, _warning):
            events.append("published")
            published.append((success, data))
            Handler()  # Simulates composition acquiring candidate N+1 after the signal.

        controller.matrixMutationFinished.connect(accepted)
        with patch("gui.room_diagnostic_controller.ExtronIN1804Handler", Handler):
            controller._run_matrix_mutation(context, {"output_num": 1, "input_num": 1}, Event(), {"username": "u", "password": "p"}, 0)
        self.assertEqual(1, len(published))
        self.assertFalse(published[0][0])
        self.assertIsInstance(published[0][1], RoomAuthenticationRejected)
        self.assertEqual(["acquire-1", "release", "published", "acquire-2"], events)
        controller.deleteLater()


if __name__ == "__main__":
    unittest.main()
