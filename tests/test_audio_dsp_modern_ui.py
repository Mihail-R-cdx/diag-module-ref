from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtWidgets import QApplication, QPushButton, QTableWidget, QWidget
except ImportError:  # pragma: no cover
    QApplication = None

from core.equipment_inventory import EquipmentInventory, EquipmentInventoryMetadata, EquipmentRecord
from core.room_diagnostic_tree import (
    DeviceRowStatus,
    RoomModelCapability,
    build_room_session,
    resolve_room_source,
)


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class ModernAudioDspRoomPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _session(self, *, generation=1, snapshot=None):
        record = EquipmentRecord(
            "dmp-record", "Fixture", "Extron DMP 64 Plus", "192.0.2.64", None, None,
            "Fixture Room", "Fixture Room", "audio", False, "Fixture address",
        )
        inventory = EquipmentInventory.from_records(
            [record], EquipmentInventoryMetadata(1, "sha256:" + "a" * 64)
        )
        capability = RoomModelCapability(
            "Extron DMP 64 Plus", "audio_dsp", "dmp_polling_controller", "dmp_one_shot"
        )
        session = build_room_session(
            inventory=inventory,
            source=resolve_room_source(inventory, record.ip_address, {record.diagnostic_model: capability}),
            generation=generation,
            capabilities={record.diagnostic_model: capability},
        )
        row = session.rows[0]
        row.status = DeviceRowStatus.CONNECTED
        row.accepted_snapshot = snapshot or self._dmp_snapshot()
        return session

    @staticmethod
    def _dmp_snapshot():
        return {
            "device_info": {"model": "DMP 64 Plus", "ip_address": "192.0.2.64"},
            "meter_sections": [
                {"title": "Inputs", "channels": [
                    {"name": f"Input {index}", "section": "Inputs", "oid": 40000 + index - 1,
                     "available": True, "dbfs": -42.0 + index, "normalized": index / 10, "outcome": "valid"}
                    for index in range(1, 7)
                ]},
                {"title": "Outputs", "channels": [
                    {"name": f"Output {index}", "section": "Outputs", "oid": 60000 + index - 1,
                     "available": True, "dbfs": -12.0 + index, "normalized": 0.5, "outcome": "valid"}
                    for index in range(1, 5)
                ]},
            ],
        }

    def _render(self, session):
        from gui.room_diagnostic_tree import RoomDiagnosticTreeWidget

        widget = RoomDiagnosticTreeWidget()
        self.addCleanup(widget.deleteLater)
        widget.render(session)
        item = widget.tree.topLevelItem(0)
        item.setExpanded(True)
        QApplication.processEvents()
        return widget

    @staticmethod
    def _current_presentation(widget):
        return widget.tree.itemWidget(widget.tree.topLevelItem(0).child(0), 0)

    def test_room_exact_row_renders_ordered_twenty_segment_dmp_meters(self):
        widget = self._render(self._session())
        presentation = widget.tree.itemWidget(widget.tree.topLevelItem(0).child(0), 0)
        from PyQt5.QtWidgets import QWidget
        meters = presentation.findChild(QWidget, "roomAudioDspMeters")
        self.assertIsNotNone(meters)
        sections = meters.findChildren(QWidget, "roomAudioDspMeterSection")
        self.assertEqual(["Inputs", "Outputs"], [section.property("meterSection") for section in sections])
        channels = meters.findChildren(QWidget, "roomAudioDspChannel")
        self.assertEqual(10, len(channels))
        self.assertEqual("Input 1", channels[0].findChild(QWidget, "roomAudioDspChannelLabel").text())
        self.assertEqual("Output 1", channels[6].findChild(QWidget, "roomAudioDspChannelLabel").text())
        first_segments = channels[0].findChildren(QWidget, "roomAudioDspMeterSegment")
        self.assertEqual(20, len(first_segments))
        self.assertEqual(2, sum(bool(segment.property("meterFilled")) for segment in first_segments))
        self.assertEqual("-41.0 dBFS", channels[0].findChild(QWidget, "roomAudioDspDbfs").text())

    def test_quantization_clamps_and_uses_round_half_up_boundaries(self):
        from gui.room_diagnostic_tree import quantize_meter_segments

        self.assertEqual(0, quantize_meter_segments(-1))
        self.assertEqual(0, quantize_meter_segments(0))
        self.assertEqual(0, quantize_meter_segments((0.5 / 20) - 0.0001))
        self.assertEqual(1, quantize_meter_segments(0.5 / 20))
        self.assertEqual(1, quantize_meter_segments((0.5 / 20) + 0.0001))
        self.assertEqual(10, quantize_meter_segments(0.5))
        self.assertEqual(20, quantize_meter_segments(0.999))
        self.assertEqual(20, quantize_meter_segments(1))
        self.assertEqual(20, quantize_meter_segments(2))

    def test_fixed_physical_segment_zones_do_not_follow_channel_value(self):
        from gui.room_diagnostic_tree import meter_segment_zone

        self.assertEqual("success", meter_segment_zone(11))
        self.assertEqual("warning", meter_segment_zone(12))
        self.assertEqual("warning", meter_segment_zone(14))
        self.assertEqual("elevated", meter_segment_zone(15))

    def test_unavailable_channel_keeps_safe_detail_without_numeric_reuse(self):
        snapshot = self._dmp_snapshot()
        channel = snapshot["meter_sections"][1]["channels"][0]
        channel.update({"available": False, "normalized": None, "dbfs": -3.0, "outcome": "sis_protocol_error", "error_code": "E14"})
        widget = self._render(self._session(snapshot=snapshot))
        from PyQt5.QtWidgets import QWidget
        unavailable = widget.findChildren(QWidget, "roomAudioDspChannel")[6]
        self.assertEqual("— dBFS", unavailable.findChild(QWidget, "roomAudioDspDbfs").text())
        self.assertEqual(0, sum(bool(segment.property("meterFilled")) for segment in unavailable.findChildren(QWidget, "roomAudioDspMeterSegment")))
        detail = unavailable.findChild(QWidget, "roomAudioDspUnavailableDetail")
        self.assertIn("sis_protocol_error", detail.toolTip())
        self.assertIn("E14", detail.toolTip())

    def test_selection_persists_only_for_current_record_and_existing_channel(self):
        session = self._session()
        widget = self._render(session)
        from PyQt5.QtWidgets import QWidget
        channel = widget.findChildren(QWidget, "roomAudioDspChannel")[1]
        channel.selected.emit("Inputs", "40001")
        QApplication.processEvents()
        self.assertEqual(("dmp-record", "Inputs", "40001"), widget._audio_selection)
        self.assertTrue(any(bool(item.property("audioSelected")) for item in widget.findChildren(QWidget, "roomAudioDspChannel")))
        self.assertEqual(
            "Inputs · Input 2",
            self._current_presentation(widget).findChild(QWidget, "roomAudioDspSelectedChannelContext").text(),
        )
        session.rows[0].accepted_snapshot["meter_sections"][0]["channels"][1]["name"] = "Input 2 current"
        widget.render(session)
        self.assertEqual(("dmp-record", "Inputs", "40001"), widget._audio_selection)
        self.assertEqual(
            "Inputs · Input 2 current",
            self._current_presentation(widget).findChild(QWidget, "roomAudioDspSelectedChannelContext").text(),
        )
        session.rows[0].accepted_snapshot["meter_sections"][0]["channels"] = []
        widget.render(session)
        self.assertIsNone(widget._audio_selection)
        self.assertEqual(
            "Выберите канал",
            self._current_presentation(widget).findChild(QWidget, "roomAudioDspSelectedChannelContext").text(),
        )
        widget.render(self._session(generation=2))
        self.assertIsNone(widget._audio_selection)

    def test_invalid_current_numeric_evidence_never_fills_or_displays_a_level(self):
        invalid_cases = (
            ("dbfs", None),
            ("normalized", None),
            ("dbfs", "bad"),
            ("normalized", "bad"),
            ("dbfs", float("nan")),
            ("normalized", float("inf")),
        )
        for field, invalid_value in invalid_cases:
            with self.subTest(field=field, invalid_value=repr(invalid_value)):
                snapshot = self._dmp_snapshot()
                snapshot["meter_sections"][0]["channels"][0][field] = invalid_value
                widget = self._render(self._session(snapshot=snapshot))
                channel = widget.findChildren(QWidget, "roomAudioDspChannel")[0]
                track = channel.findChild(QWidget, "roomAudioDspMeterTrack")
                self.assertTrue(track.property("meterAvailable"))
                self.assertFalse(track.property("numericMeterValid"))
                self.assertEqual("— dBFS", channel.findChild(QWidget, "roomAudioDspDbfs").text())
                self.assertEqual(
                    0,
                    sum(
                        bool(segment.property("meterFilled"))
                        for segment in channel.findChildren(QWidget, "roomAudioDspMeterSegment")
                    ),
                )

    def test_all_invalid_current_meter_sections_fail_closed_to_safe_table(self):
        snapshot = self._dmp_snapshot()
        for section in snapshot["meter_sections"]:
            for channel in section["channels"]:
                channel["dbfs"] = None
        widget = self._render(self._session(snapshot=snapshot))
        self.assertIsNone(widget.findChild(QWidget, "roomAudioDspMeters"))
        table = widget.findChild(QTableWidget, "roomAudioMeasurements")
        self.assertIsNotNone(table)
        self.assertEqual("— dBFS (valid)", table.item(0, 2).text())

    def test_future_controls_are_disabled_and_biamp_stays_a_table(self):
        widget = self._render(self._session())
        for name in ("roomAudioDspGainDown", "roomAudioDspGainValue", "roomAudioDspGainUp", "roomAudioDspMute"):
            self.assertFalse(widget.findChild(QPushButton, name).isEnabled())
        from gui.room_diagnostic_tree import RoomReadOnlyPresentation
        row = self._session().rows[0]
        row.accepted_snapshot = {"signal_sources": [{"alias": "Aec", "rows": [{"channel_number": 1, "value": True}]}]}
        presentation = RoomReadOnlyPresentation(row)
        self.addCleanup(presentation.deleteLater)
        table = presentation.findChild(QTableWidget, "roomAudioMeasurements")
        self.assertIsNotNone(table)
        self.assertEqual("True", table.item(0, 2).text())


if __name__ == "__main__":
    unittest.main()
