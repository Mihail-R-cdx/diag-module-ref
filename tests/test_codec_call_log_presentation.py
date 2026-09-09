from datetime import datetime, timedelta
import unittest

from PyQt5.QtWidgets import QApplication

from core.codec_call_history import CallDirection, CallRecord, snapshot_from_records
from gui.dialogs.call_log_window import CallLogWindow


class CallLogPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_preview_and_collapsed_journal_keep_latest_twenty_without_refetch(self):
        now = datetime(2026, 6, 10, 12)
        records = tuple(
            CallRecord(
                f"record-{index}", now - timedelta(minutes=index), 60,
                room_number=str(index), start_display=f"start-{index}",
                duration_display="Активный" if index == 1 else "00:01:00",
                active=index == 1,
            )
            for index in range(25)
        )
        dialog = CallLogWindow()
        dialog.set_snapshot(snapshot_from_records(records, reference_now=now, source_ended=True))

        self.assertEqual(2, dialog.preview_table.rowCount())
        self.assertEqual(20, dialog.table.rowCount())
        self.assertFalse(dialog.table.isVisible())
        self.assertEqual("Активный", dialog.preview_table.item(1, 2).text())

        dialog.journal_toggle.click()
        self.assertFalse(dialog.table.isHidden())
        self.assertEqual(20, dialog.table.rowCount())
        dialog.clear_records()
        self.assertTrue(dialog.table.isHidden())
        dialog.close()

    def test_fewer_than_twenty_records_have_no_padding(self):
        now = datetime(2026, 6, 10, 12)
        dialog = CallLogWindow()
        dialog.set_snapshot(snapshot_from_records(
            [CallRecord(str(index), now, 60) for index in range(3)],
            reference_now=now,
            source_ended=True,
        ))
        self.assertEqual(2, dialog.preview_table.rowCount())
        self.assertEqual(3, dialog.table.rowCount())
        dialog.close()

    def test_direction_text_hides_unknown_without_reclassifying_typed_record(self):
        now = datetime(2026, 6, 10, 12)
        incoming = CallRecord("incoming", now, 60, direction=CallDirection.INCOMING)
        outgoing = CallRecord("outgoing", now, 60, direction=CallDirection.OUTGOING)
        unknown = CallRecord("unknown", now, 60, direction=CallDirection.UNKNOWN)
        snapshot = snapshot_from_records((incoming, outgoing, unknown), reference_now=now, source_ended=True)
        dialog = CallLogWindow()
        self.addCleanup(dialog.close)
        dialog.set_snapshot(snapshot)

        self.assertIs(CallDirection.UNKNOWN, snapshot.records[2].direction)
        self.assertEqual("Входящий", dialog._direction_text(CallDirection.INCOMING))
        self.assertEqual("Исходящий", dialog._direction_text(CallDirection.OUTGOING))
        self.assertEqual("", dialog._direction_text(CallDirection.UNKNOWN))
        self.assertEqual("", dialog.normalize_record(object(), 0)[4])
        self.assertEqual("", dialog.normalize_record({"direction": "unrecognized"}, 0)[4])
        self.assertEqual("", dialog.table.item(2, 4).text())
        self.assertNotIn(dialog.table.item(2, 4).text(), {"Направление неизвестно", "—", "Нет данных"})

    def test_polycom_like_sixteen_record_source_limited_batch_shows_every_record(self):
        now = datetime(2026, 6, 10, 12)
        snapshot = snapshot_from_records(
            [
                CallRecord(
                    f"polycom-{index}", now - timedelta(minutes=index), 60,
                    room_number=f"room-{index}",
                )
                for index in reversed(range(16))
            ],
            reference_now=now,
        )
        dialog = CallLogWindow()
        dialog.set_snapshot(snapshot)

        self.assertEqual(2, dialog.preview_table.rowCount())
        self.assertEqual("room-0", dialog.preview_table.item(0, 0).text())
        self.assertEqual("room-1", dialog.preview_table.item(1, 0).text())
        self.assertEqual(16, dialog.table.rowCount())
        self.assertEqual("room-0", dialog.table.item(0, 0).text())
        self.assertEqual("room-1", dialog.table.item(1, 0).text())
        dialog.close()

    def test_out_of_order_source_records_render_true_newest_preview(self):
        now = datetime(2026, 6, 10, 12)
        dialog = CallLogWindow()
        dialog.set_snapshot(snapshot_from_records(
            [
                CallRecord("old", now - timedelta(hours=3), 60, room_number="old"),
                CallRecord("new", now - timedelta(minutes=5), 60, room_number="new"),
                CallRecord("middle", now - timedelta(hours=1), 60, room_number="middle"),
            ],
            reference_now=now,
            source_ended=True,
        ))
        self.assertEqual("new", dialog.preview_table.item(0, 0).text())
        self.assertEqual("middle", dialog.preview_table.item(1, 0).text())
        dialog.close()

    def test_weekend_warning_is_kept_in_non_modal_dialog_status(self):
        now = datetime(2026, 6, 7, 12)  # Sunday
        dialog = CallLogWindow()
        dialog.status_label.setText("Загрузка журнала звонков...")
        dialog.set_snapshot(snapshot_from_records(
            [
                CallRecord(f"weekend-{index}", now - timedelta(hours=2), 3600)
                for index in range(100)
            ],
            reference_now=now,
        ))
        self.assertIn("период не содержит рабочих дней", dialog.status_label.text())
        self.assertNotIn("Расчёт статистики использования", dialog.status_label.text())
        dialog.close()


if __name__ == "__main__":
    unittest.main()
