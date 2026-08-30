"""Regression coverage for the common modern room foundation."""

from __future__ import annotations

import os
import unittest
from dataclasses import replace
from unittest.mock import patch

from core.call_activity import (
    CALL_ACTIVITY_EVIDENCE_KEY,
    CallActivity,
    normalize_call_activity,
)
from core.equipment_inventory import EquipmentInventory, EquipmentInventoryMetadata, EquipmentRecord
from core.room_diagnostic_tree import (
    DeviceRowStatus,
    RoomDiagnosticOrchestrator,
    RoomModelCapability,
    build_room_session_from_room,
)
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
    @staticmethod
    def _codec_cases():
        from core.parser import (
            HuaweiBar310DataParser,
            HuaweiTE20DataParser,
            HuaweiTE40DataParser,
            PolycomDataParser,
        )

        return (
            ("Huawei TE20", "huawei_call_activity", HuaweiTE20DataParser.parse_raw_data, {}, "Calling", "No Call"),
            ("Huawei TE40", "huawei_call_activity", HuaweiTE40DataParser.parse_raw_data, {}, "Calling", "No Call"),
            (
                "CloudLink Bar 310", "cloudlink_call_activity",
                HuaweiBar310DataParser.parse_raw_data,
                {"model": "Huawei CloudLink Bar 310", "version": "V1"}, "Connected", "No Call",
            ),
            (
                "CloudLink Box 310", "cloudlink_call_activity",
                lambda data: HuaweiBar310DataParser.parse_raw_data(data, "Huawei CloudLink Box 310"),
                {"model": "Huawei CloudLink Box 310", "version": "V1"}, "Connected", "No Call",
            ),
            ("Polycom RPG 310", "polycom_call_activity", PolycomDataParser.parse_raw_data, {}, "Active", "No Call"),
        )

    def test_registry_has_every_required_exact_binding(self):
        required = {"Huawei TE20", "Huawei TE40", "CloudLink Bar 310", "CloudLink Box 310", "Polycom RPG 310"}
        entries = {entry.diagnostic_model: entry for entry in dispatch_entries()}
        self.assertTrue(all(entries[name].call_activity_capability for name in required))
        self.assertTrue(all(entries[name].call_activity_binding_key for name in required))

    def test_production_parser_outputs_publish_typed_evidence_for_every_codec(self):
        for model, binding, parser, common, active, inactive in self._codec_cases():
            with self.subTest(model=model, state="active"):
                parsed = parser({**common, "call_status": active})
                self.assertIn(CALL_ACTIVITY_EVIDENCE_KEY, parsed)
                self.assertIs(CallActivity.ACTIVE, normalize_call_activity(binding, parsed))
            with self.subTest(model=model, state="inactive"):
                parsed = parser({**common, "call_status": inactive})
                self.assertIs(CallActivity.INACTIVE, normalize_call_activity(binding, parsed))
            with self.subTest(model=model, state="missing"):
                parsed = parser(dict(common))
                self.assertIs(CallActivity.UNKNOWN, normalize_call_activity(binding, parsed))
            with self.subTest(model=model, state="unrecognized"):
                parsed = parser({**common, "call_status": "Unexpected state"})
                self.assertIs(CallActivity.UNKNOWN, normalize_call_activity(binding, parsed))

    def test_redacted_worker_adapter_pipeline_preserves_exact_activity_tokens_for_every_codec(self):
        """Exercise the public worker boundary, where enums become ordinary strings."""
        from core.redaction import redact_data
        from core.workers.common import WorkerSignals
        from gui.room_one_shot_adapters import WorkerOneShotAdapter

        for model, binding, parser, common, active, inactive in self._codec_cases():
            for state, raw, expected in (
                ("active", active, CallActivity.ACTIVE),
                ("inactive", inactive, CallActivity.INACTIVE),
                ("missing", None, CallActivity.UNKNOWN),
                ("unrecognized", "Unexpected state", CallActivity.UNKNOWN),
            ):
                with self.subTest(model=model, state=state):
                    raw_snapshot = parser({**common, **({"call_status": raw} if raw is not None else {})})
                    transport_snapshot = redact_data(raw_snapshot)
                    if raw is None:
                        self.assertNotIn(CALL_ACTIVITY_EVIDENCE_KEY, transport_snapshot)
                    else:
                        self.assertEqual(expected.value, transport_snapshot[CALL_ACTIVITY_EVIDENCE_KEY])
                        self.assertIs(type(transport_snapshot[CALL_ACTIVITY_EVIDENCE_KEY]), str)

                    class ParsedWorker:
                        def __init__(self):
                            self.signals = WorkerSignals()

                        def run(self):
                            self.signals.result.emit(transport_snapshot)

                    inv = inventory(record("codec", room_id="room", name="Room", ip="192.0.2.10", model=model))
                    capabilities = {
                        model: RoomModelCapability(
                            model, "codec", "route", "codec_one_shot", call_activity_binding_key=binding
                        )
                    }
                    session = build_room_session_from_room(
                        inventory=inv, room_id="room", generation=1, capabilities=capabilities
                    )
                    RoomDiagnosticOrchestrator(
                        adapters={"codec_one_shot": WorkerOneShotAdapter(lambda _context: ParsedWorker())},
                        credential_candidates=lambda *_: ({"username": "operator"},),
                        ping=lambda _ip: True,
                    ).run(session)
                    row = session.row_for("codec")
                    self.assertEqual(DeviceRowStatus.CONNECTED, row.status)
                    self.assertIs(expected, row.call_activity)

        entries = {entry.diagnostic_model: entry for entry in dispatch_entries()}
        self.assertEqual(
            entries["CloudLink Bar 310"].call_activity_binding_key,
            entries["CloudLink Box 310"].call_activity_binding_key,
        )
        self.assertIsNot(entries["CloudLink Bar 310"], entries["CloudLink Box 310"])

    def test_room_normalizer_never_interprets_display_strings(self):
        self.assertIs(
            CallActivity.UNKNOWN,
            normalize_call_activity("huawei_call_activity", {"Статус звонка": "В звонке"}),
        )
        self.assertIs(
            CallActivity.UNKNOWN,
            normalize_call_activity("cloudlink_call_activity", {"call_status": "Calling"}),
        )

    def test_registry_validation_fails_closed_for_declared_unbound_capability(self):
        import gui.diagnostic_dispatch as dispatch

        original = dispatch.DISPATCH_REGISTRY
        invalid = replace(original[0], call_activity_binding_key=None)
        with patch.object(dispatch, "DISPATCH_REGISTRY", (invalid, *original[1:])):
            with self.assertRaisesRegex(ValueError, "call-activity binding is missing"):
                validate_dispatch_registry(
                    registered_screens={"codec", "matrix", "pdu", "audio_dsp"},
                    page_models_by_screen={
                        "codec": ("Huawei TE20", "Huawei TE40", "CloudLink Bar 310", "CloudLink Box 310", "Polycom RPG 310"),
                        "matrix": ("Extron IN1804",),
                        "pdu": ("Aten PE8208AV", "Extron IPL T PCS4i"),
                        "audio_dsp": ("Biamp Tesira Forte CI", "Extron DMP 64 Plus"),
                    },
                )


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
        session.room_vip = True
        session.rows[0].call_activity = CallActivity.ACTIVE
        widget = RoomDiagnosticTreeWidget()
        self.addCleanup(widget.deleteLater)
        widget.render(session)
        self.assertEqual("Gi1/0/1, Gi1/0/2", widget.network_tree.topLevelItem(0).text(1))
        self.assertEqual("Коммутатор не определён", widget.network_tree.topLevelItem(1).text(0))
        self.assertIn("Занято", widget.occupancy_label.text())
        self.assertEqual("Room", widget.room_name_label.text())
        self.assertEqual("Гарантия: Нет данных", widget.room_warranty_label.text())
        self.assertFalse(widget.vip_badge.isHidden())
        self.assertEqual("VIP", widget.vip_badge.text())
        self.assertNotIn("VIP:", widget.room_header.text())
        self.assertTrue(widget.room_card.header_widget.isHidden())
        self.assertTrue(widget.network_card.header_widget.isHidden())
        self.assertEqual(156, widget.upper_cards.height())
        self.assertTrue(widget.network_tree.isHeaderHidden())
        self.assertEqual(64, widget.tree.topLevelItem(0).sizeHint(0).height())
        self.assertEqual(48, widget.tree.iconSize().width())
        self.assertEqual("", widget.tree.topLevelItem(0).text(0))
        self.assertEqual("Статус подключения", widget.tree.headerItem().text(2))
        self.assertEqual(76, widget.tree.columnWidth(0))
        self.assertEqual(290, widget.tree.columnWidth(2))
        self.assertEqual(180, widget.tree.columnWidth(3))
        self.assertTrue(widget.tree.topLevelItem(0).child(0).isFirstColumnSpanned())

        session.rows[0].stale = True
        session.room_vip = False
        widget.render(session)
        self.assertIn("Нет данных", widget.occupancy_label.text())
        self.assertTrue(widget.vip_badge.isHidden())

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

    def test_failed_room_resolution_clears_old_room_authority_without_erasing_query(self):
        from gui.main_window import VCSDiagnosticApp

        old_inventory = inventory(
            record("A", room_id="old", name="Old room", ip="192.0.2.10", switch="10.0.0.1", port="Gi1/0/1")
        )
        with patch("gui.main_window.load_equipment_inventory", return_value=old_inventory):
            window = VCSDiagnosticApp()
        self.addCleanup(window.deleteLater)
        window.ip_entry.setText("No matching room")
        self._seed_old_room_presentation(window, old_inventory)
        with patch.object(window, "_start_selected_room_diagnostic_session") as start:
            window.refresh_data()

        self.assertEqual("No matching room", window.ip_entry.text())
        self._assert_room_presentation_cleared(window)
        self.assertIsNone(window._selected_room_result)
        self.assertTrue(window.selected_room_cue.isHidden())
        start.assert_not_called()

    def _seed_old_room_presentation(self, window, old_inventory):
        old_session = build_room_session_from_room(
            inventory=old_inventory,
            room_id=old_inventory.records[0].room_id,
            generation=1,
            capabilities={
                "Huawei TE40": RoomModelCapability(
                    "Huawei TE40", "codec", "route", "adapter", call_activity_binding_key="huawei_call_activity"
                )
            },
        )
        old_session.rows[0].status = DeviceRowStatus.CONNECTED
        old_session.rows[0].call_activity = CallActivity.ACTIVE
        window.room_diagnostic_session = old_session
        window.room_interaction_coordinator.bind_session(old_session)
        window.room_diagnostic_tree.render(old_session)
        self.assertTrue(window.room_diagnostic_tree.room_header.text())
        self.assertTrue(window.room_diagnostic_tree.occupancy_label.text())
        self.assertTrue(window.room_diagnostic_tree.global_status.text())
        self.assertGreater(window.room_diagnostic_tree.tree.topLevelItemCount(), 0)
        self.assertGreater(window.room_diagnostic_tree.network_tree.topLevelItemCount(), 0)

    def _assert_room_presentation_cleared(self, window):
        tree = window.room_diagnostic_tree
        self.assertIsNone(window.room_diagnostic_session)
        self.assertIsNone(window.room_interaction_coordinator.active_context)
        self.assertIsNone(tree._session)
        self.assertEqual("", tree.room_name_label.text())
        self.assertTrue(tree.vip_badge.isHidden())
        self.assertEqual("", tree.room_warranty_label.text())
        self.assertEqual("", tree.room_header.text())
        self.assertEqual("", tree.occupancy_label.text())
        self.assertEqual("", tree.global_status.text())
        self.assertEqual(0, tree.tree.topLevelItemCount())
        self.assertEqual(0, tree.network_tree.topLevelItemCount())

    def test_room_presentation_is_cleared_when_room_search_is_unavailable(self):
        from gui.main_window import VCSDiagnosticApp

        old_inventory = inventory(record("A", room_id="old", name="Old room", ip="192.0.2.10"))
        with patch("gui.main_window.load_equipment_inventory", return_value=old_inventory):
            window = VCSDiagnosticApp()
        self.addCleanup(window.deleteLater)
        window.ip_entry.setText("Room")
        self._seed_old_room_presentation(window, old_inventory)
        window.equipment_inventory = None
        with patch.object(window, "_start_selected_room_diagnostic_session") as start:
            window.refresh_data()
        self._assert_room_presentation_cleared(window)
        start.assert_not_called()

    def test_room_presentation_is_cleared_when_selected_room_disappears(self):
        from gui.main_window import VCSDiagnosticApp

        old_inventory = inventory(record("A", room_id="old", name="Old room", ip="192.0.2.10"))
        with patch("gui.main_window.load_equipment_inventory", return_value=old_inventory):
            window = VCSDiagnosticApp()
        self.addCleanup(window.deleteLater)
        window.ip_entry.setText("Old")
        window._on_room_completer_activated(window._room_completer_model.index(0, 0))
        self._seed_old_room_presentation(window, old_inventory)
        window.equipment_inventory = inventory(record("B", room_id="other", name="Other room", ip="192.0.2.20"))
        with patch.object(window, "_start_selected_room_diagnostic_session") as start:
            window.refresh_data()
        self._assert_room_presentation_cleared(window)
        self.assertIsNone(window._selected_room_result)
        start.assert_not_called()

    def test_stale_multi_room_selection_is_cleared_before_start(self):
        from gui.main_window import VCSDiagnosticApp

        initial = inventory(
            record("A", room_id="r1", name="Room", address="One", ip="192.0.2.1"),
            record("B", room_id="r2", name="Room", address="Two", ip="192.0.2.2"),
        )
        with patch("gui.main_window.load_equipment_inventory", return_value=initial):
            window = VCSDiagnosticApp()
        self.addCleanup(window.deleteLater)
        window.ip_entry.setText("Room")
        window._on_room_completer_activated(window._room_completer_model.index(0, 0))
        self._seed_old_room_presentation(window, initial)
        window.equipment_inventory = EquipmentInventory.from_records(
            (
                record("B", room_id="r2", name="Room", address="Two", ip="192.0.2.2"),
                record("C", room_id="r3", name="Room", address="Three", ip="192.0.2.3"),
            ),
            EquipmentInventoryMetadata(4, "sha256:" + "b" * 64),
        )
        with patch.object(window, "_start_selected_room_diagnostic_session") as start:
            window.refresh_data()

        self.assertEqual("Room", window.ip_entry.text())
        self._assert_room_presentation_cleared(window)
        self.assertIsNone(window._selected_room_result)
        self.assertTrue(window.selected_room_cue.isHidden())
        start.assert_not_called()
