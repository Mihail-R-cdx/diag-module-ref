"""Regression coverage for the common modern room foundation."""

from __future__ import annotations

import unittest
import os
from unittest.mock import patch

from core.call_activity import CallActivity, normalize_call_activity
from core.equipment_inventory import EquipmentInventory, EquipmentInventoryMetadata, EquipmentRecord
from core.room_diagnostic_tree import DeviceRowStatus, RoomModelCapability, build_room_session_from_room
from gui.diagnostic_dispatch import dispatch_entries, validate_dispatch_registry

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PyQt5.QtWidgets import QApplication, QTableWidget
except ImportError:  # pragma: no cover
    QApplication = None


def record(record_id, *, room_id, name, address=None, ip=None, port=None, switch=None, model="Huawei TE40"):
    return EquipmentRecord(record_id, model, model, ip, None, None, room_id, name, "video_codec", None, address, switch, port)


def inventory(*records):
    return EquipmentInventory.from_records(
        tuple(records), EquipmentInventoryMetadata(4, "sha256:" + "a" * 64)
    )


class RoomSearchTests(unittest.TestCase):
    def test_search_is_casefolded_distinct_and_disambiguated(self):
        inv = inventory(
            record("B", room_id="r2", name="Переговорная", address="Б", ip="192.0.2.2"),
            record("A", room_id="r1", name="ПЕРЕГОВОРНАЯ", address="А", ip="192.0.2.1"),
            record("C", room_id="r3", name="Переговорная", address="А", ip="192.0.2.3"),
        )
        results = inv.find_rooms_by_name(" говор ")
        self.assertEqual(["r1", "r3", "r2"], [item.room_id for item in results])
        self.assertIn("Вариант 1", results[0].selection_label)
        self.assertIn("Вариант 2", results[1].selection_label)
        self.assertEqual((), inv.find_rooms_by_name("   "))

    def test_search_normalizes_unicode_and_deduplicates_conflicting_room_records(self):
        inv = inventory(
            record("A", room_id="r1", name="Cafe\u0301", address="A", ip="192.0.2.1"),
            record("B", room_id="r1", name="Auxiliary name", address="B", ip="192.0.2.2"),
            record("C", room_id="r2", name="CAFÉ", address="C", ip="192.0.2.3"),
        )
        results = inv.find_rooms_by_name("  café  ")
        self.assertEqual(["r1", "r2"], [item.room_id for item in results])
        self.assertEqual("Café", results[0].display_name)
        self.assertEqual("Café — A", results[0].selection_label)
        self.assertEqual((), inv.find_rooms_by_name("no such room"))

    def test_source_less_session_is_canonical_ordered_and_collapsed(self):
        inv = inventory(
            record("Z", room_id="r", name="Room", ip="192.0.2.2"),
            record("A", room_id="r", name="Room", ip="192.0.2.1"),
        )
        caps = {"Huawei TE40": RoomModelCapability("Huawei TE40", "codec", "route", "adapter")}
        session = build_room_session_from_room(inventory=inv, room_id="r", generation=3, capabilities=caps)
        self.assertIsNone(session.identity.source_record_id)
        self.assertEqual(["A", "Z"], [row.record_id for row in session.rows])
        self.assertIsNone(session.expanded_record_id)


class CallActivityTests(unittest.TestCase):
    def test_registry_has_every_required_exact_binding(self):
        required = {"Huawei TE20", "Huawei TE40", "CloudLink Bar 310", "CloudLink Box 310", "Polycom RPG 310"}
        entries = {entry.diagnostic_model: entry for entry in dispatch_entries()}
        self.assertTrue(all(entries[name].call_activity_binding_key for name in required))

    def test_explicit_normalization_defaults_to_unknown(self):
        self.assertIs(CallActivity.ACTIVE, normalize_call_activity("huawei_call_activity", {"call_status": "Calling"}))
        self.assertIs(CallActivity.ACTIVE, normalize_call_activity("huawei_call_activity", {"call_status": "Вызов"}))
        self.assertIs(CallActivity.INACTIVE, normalize_call_activity("polycom_call_activity", {"call_status": "No Call"}))
        self.assertIs(CallActivity.UNKNOWN, normalize_call_activity("cloudlink_call_activity", {"call_status": "???"}))
        self.assertIs(CallActivity.UNKNOWN, normalize_call_activity(None, {"call_status": "Calling"}))


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class RoomPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_network_card_keeps_partial_evidence_and_busy_is_typed(self):
        from gui.room_diagnostic_tree import RoomDiagnosticTreeWidget

        inv = inventory(
            record("A", room_id="r", name="Room", ip="192.0.2.1", switch="10.0.0.1", port="Gi1/0/1"),
            record("B", room_id="r", name="Room", ip="192.0.2.2", switch="10.0.0.1", port="Gi1/0/2"),
            record("C", room_id="r", name="Room", ip="192.0.2.3", port="Gi1/0/3"),
        )
        caps = {"Huawei TE40": RoomModelCapability("Huawei TE40", "codec", "route", "adapter", call_activity_binding_key="huawei_call_activity")}
        session = build_room_session_from_room(inventory=inv, room_id="r", generation=1, capabilities=caps)
        session.rows[0].call_activity = CallActivity.ACTIVE
        widget = RoomDiagnosticTreeWidget()
        self.addCleanup(widget.deleteLater)
        widget.render(session)
        self.assertEqual("Gi1/0/1, Gi1/0/2", widget.network_tree.topLevelItem(0).text(1))
        self.assertEqual("Коммутатор не определён", widget.network_tree.topLevelItem(1).text(0))
        self.assertIn("Занято", widget.occupancy_label.text())
        self.assertEqual(56, widget.tree.topLevelItem(0).sizeHint(0).height())

    def test_pdu_room_projection_opens_with_live_actions_available(self):
        from gui.room_diagnostic_tree import RoomDiagnosticTreeWidget

        inv = inventory(
            record(
                "PDU-A", room_id="r", name="Room", ip="192.0.2.9",
                model="Aten PE8208AV",
            )
        )
        caps = {"Aten PE8208AV": RoomModelCapability("Aten PE8208AV", "pdu", "route", "adapter")}
        session = build_room_session_from_room(inventory=inv, room_id="r", generation=1, capabilities=caps)
        session.rows[0].status = DeviceRowStatus.CONNECTED
        session.rows[0].accepted_snapshot = {"outlets": [{"number": 1, "status": "on", "name": "Display"}]}
        widget = RoomDiagnosticTreeWidget()
        self.addCleanup(widget.deleteLater)
        widget.render(session)
        projection = widget.tree.itemWidget(widget.tree.topLevelItem(0).child(0), 0)
        self.assertIsNotNone(projection.findChild(QTableWidget, "roomPduOutlets"))

    def test_completion_keeps_operator_query_visible(self):
        from gui.main_window import RoomSearchCompleter
        from PyQt5.QtCore import QStringListModel
        from PyQt5.QtWidgets import QLineEdit

        editor = QLineEdit("Перег")
        completer = RoomSearchCompleter(QStringListModel(["Переговорная — этаж 3"]), editor)
        editor.setCompleter(completer)
        self.assertEqual("Перег", completer.pathFromIndex(completer.completionModel().index(0, 0)))

    def test_selection_cue_keeps_raw_query_and_refresh_uses_selected_room(self):
        from gui.main_window import VCSDiagnosticApp

        inv = inventory(
            record("A", room_id="r1", name="Переговорная", address="Этаж 1", ip="192.0.2.1"),
            record("B", room_id="r2", name="Переговорная", address="Этаж 2", ip="192.0.2.2"),
        )
        with patch("gui.main_window.load_equipment_inventory", return_value=inv):
            window = VCSDiagnosticApp()
        self.addCleanup(window.deleteLater)
        window.ip_entry.setText("Перег")
        label, selected = next(iter(window._room_search_results_by_label.items()))
        self.assertEqual(label, window._room_completer_model.index(0, 0).data())
        window._on_room_completer_activated(window._room_completer_model.index(0, 0))
        self.assertEqual("Перег", window.ip_entry.text())
        self.assertTrue(window.selected_room_cue.isVisible() or not window.selected_room_cue.isHidden())
        with patch.object(window, "_start_selected_room_diagnostic_session") as start:
            window.refresh_data()
        start.assert_called_once_with(selected.room_id, unittest.mock.ANY)
