"""Focused room-mode regression coverage for the modern PDU dashboard."""

import os
import threading
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication, QPushButton, QTableWidget, QWidget
except ImportError:
    QApplication = None

from core.room_diagnostic_tree import (
    DeviceRowState,
    DeviceRowStatus,
    RoomCycleStatus,
    RoomDiagnosticSession,
    RoomDiagnosticSessionIdentity,
    RoomModelCapability,
)
from core.room_interaction import RoomInteractionContext, RoomInteractionKind
from gui.room_diagnostic_controller import RoomDiagnosticController
from gui.room_diagnostic_tree import RoomDiagnosticTreeWidget, RoomReadOnlyPresentation
from gui.components import ParameterRow, SectionCard, SemanticButton


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class ModernPDUDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _row(self, *, model="Aten PE8208AV", serial="SN-1", mac="aa:bb:cc:dd:ee:ff"):
        return DeviceRowState(
            "pdu-1",
            model,
            "192.0.2.44",
            model,
            DeviceRowStatus.CONNECTED,
            RoomModelCapability(model, "pdu", "route", "adapter"),
            accepted_snapshot={
                "outlets": [
                    {"number": 8, "name": "Eight", "status": "off"},
                    {"number": 2, "name": "Two", "status": "on"},
                    {"number": 1, "name": "One", "status": None},
                ]
            },
            serial_number=serial,
            mac_address=mac,
        )

    def _presentation(self, row=None, **callbacks):
        row = row or self._row()
        return RoomReadOnlyPresentation(
            row,
            request_local_refresh=callbacks.get("refresh", lambda: None),
            request_mutation=callbacks.get("mutation", lambda _number, _command: None),
            request_bulk_mutation=callbacks.get("bulk", lambda _command: None),
            local_refresh_allowed=True,
            mutation_allowed=True,
        )

    def test_two_cards_use_exact_information_and_five_column_table(self):
        presentation = self._presentation()
        self.assertEqual(
            ["Основная информация", "Управление розетками"],
            [card.title_label.text() for card in presentation.findChildren(SectionCard)],
        )
        table = presentation.findChild(QTableWidget, "roomPduOutlets")
        self.assertEqual(
            ["Розетка", "Имя розетки", "Состояние", "Текущая мощность", "Действия"],
            [table.horizontalHeaderItem(index).text() for index in range(table.columnCount())],
        )
        self.assertEqual(["1", "2", "8"], [table.item(index, 0).text() for index in range(table.rowCount())])
        self.assertTrue(all(table.item(index, 3).text() == "—" for index in range(table.rowCount())))
        self.assertEqual(
            ["Модель", "Серийный номер", "MAC-адрес"],
            [row.name_label.text() for row in presentation.findChildren(ParameterRow)],
        )
        self.assertTrue(
            all(
                not row.value_display.hasFrame()
                and row.value_display.alignment() == (Qt.AlignRight | Qt.AlignVCenter)
                and row.value_display.minimumWidth() == 143
                and row.value_display.maximumWidth() == 468
                for row in presentation.findChildren(ParameterRow)
            )
        )

    def test_information_metadata_and_outlet_semantics_are_exact(self):
        presentation = self._presentation(self._row(serial=None, mac=""))
        info_rows = [
            widget for widget in presentation.findChildren(ParameterRow)
            if widget.objectName() == "roomPduInfoRow"
        ]
        self.assertEqual(
            [("Модель", "Aten PE8208AV"), ("Серийный номер", "—"), ("MAC-адрес", "—")],
            [(widget.name_label.text(), widget.value_display.text()) for widget in info_rows],
        )
        table = presentation.findChild(QTableWidget, "roomPduOutlets")
        self.assertEqual(["—", "ON", "OFF"], [table.cellWidget(index, 2).text().replace("●  ", "") for index in range(3)])
        actions = table.cellWidget(0, 4).findChildren(SemanticButton)
        self.assertEqual(["Вкл", "Выкл", "Перезапуск"], [button.text() for button in actions])
        self.assertEqual(["success", "danger", "secondary"], [button.role() for button in actions])
        top_actions = presentation.findChild(QWidget, "roomPduTopActions")
        self.assertEqual(26, top_actions.maximumHeight())
        outlet_card = presentation.findChild(SectionCard, "roomPduOutletCard")
        self.assertIs(top_actions.parentWidget(), outlet_card.header_widget)
        self.assertFalse(presentation.findChild(QPushButton, "roomLocalDebugButton"))
        self.assertEqual((9, 31, 12, 20, 28), table.column_ratios)
        self.assertFalse(outlet_card.icon_label.pixmap().isNull())

    def test_arbitrary_outlets_scroll_without_power_acquisition(self):
        row = self._row()
        row.accepted_snapshot = {
            "outlets": [{"number": number, "name": str(number), "status": "on"} for number in range(1, 13)]
        }
        presentation = self._presentation(row)
        presentation.resize(1200, 700)
        presentation.show()
        self.app.processEvents()
        table = presentation.findChild(QTableWidget, "roomPduOutlets")
        self.assertEqual(12, table.rowCount())
        self.assertGreater(table.verticalScrollBar().maximum(), 0)
        self.assertTrue(all(table.item(index, 3).text() == "—" for index in range(table.rowCount())))

    def test_expanded_pdu_has_only_card_refresh_and_no_header_action(self):
        row = self._row()
        session = RoomDiagnosticSession(
            RoomDiagnosticSessionIdentity("snapshot", 1, "192.0.2.44", "pdu-1", "room"),
            "Room",
            None,
            None,
            [row],
            status=RoomCycleStatus.COMPLETE,
            expanded_record_id="pdu-1",
        )
        tree = RoomDiagnosticTreeWidget()
        tree.render(session)
        self.assertIsNotNone(tree.findChild(QTableWidget, "roomPduOutlets"))
        presentation = tree.findChild(RoomReadOnlyPresentation)
        self.assertIsNotNone(presentation.findChild(SemanticButton, "roomPduRefreshButton"))
        self.assertFalse(any(button.text() == "Локальный опрос" for button in presentation.findChildren(QPushButton)))
        session.expanded_record_id = None
        tree.render(session)
        self.assertIsNone(tree.tree.itemWidget(tree.tree.topLevelItem(0), 4))

    def test_card_refresh_publishes_the_exact_row_intent(self):
        row = self._row()
        session = RoomDiagnosticSession(
            RoomDiagnosticSessionIdentity("snapshot", 1, "192.0.2.44", "pdu-1", "room"),
            "Room", None, None, [row], status=RoomCycleStatus.COMPLETE,
            expanded_record_id="pdu-1",
        )
        tree = RoomDiagnosticTreeWidget()
        received = []
        tree.localRefreshRequested.connect(received.append)
        tree.render(session)
        tree.findChild(SemanticButton, "roomPduRefreshButton").clicked.emit()
        self.assertEqual(["pdu-1"], received)

    def test_room_bulk_mutation_reuses_core_bulk_operation(self):
        controller = RoomDiagnosticController(
            candidate_provider=lambda *_args: (),
            ping=lambda _ip: True,
            persist_success=lambda _evidence: None,
            starting_index=lambda *_args: 0,
        )
        context = RoomInteractionContext(
            "snapshot", 1, "pdu-1", "Aten PE8208AV", "192.0.2.44", 4, 5, 6,
            RoomInteractionKind.MUTATION,
        )
        received = []
        controller.pduMutationFinished.connect(lambda *args: received.append(args))
        with patch("gui.room_diagnostic_controller.execute_pdu_bulk", return_value={"success": True, "operation": "bulk_on"}) as execute:
            controller._run_pdu_mutation(
                context,
                {"operation": "bulk_on", "outlet_sequence": (2, 1)},
                threading.Event(),
                credential={"username": "operator", "password": "secret"},
                candidate_index=0,
            )
        execute.assert_called_once()
        self.assertEqual((2, 1), execute.call_args.kwargs["descriptor"].outlet_sequence)
        self.assertTrue(received[-1][1])

    def test_pcs4i_reboot_is_rejected_before_room_mutation_admission(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.deleteLater)
        row = self._row(model="Extron IPL T PCS4i")
        session = RoomDiagnosticSession(
            RoomDiagnosticSessionIdentity("snapshot", 1, "192.0.2.44", "pdu-1", "room"),
            "Room", None, None, [row], status=RoomCycleStatus.COMPLETE,
            expanded_record_id="pdu-1",
        )
        window.room_diagnostic_session = session
        window.room_interaction_coordinator.bind_session(session)
        with patch("gui.main_window.QMessageBox.information") as popup, \
                patch.object(window.room_interaction_coordinator, "confirm_mutation") as admit, \
                patch.object(window.room_diagnostic_controller, "start_pdu_mutation") as start:
            window._on_room_pdu_mutation_requested("pdu-1", 1, "reboot")
        popup.assert_called_once()
        admit.assert_not_called()
        start.assert_not_called()
