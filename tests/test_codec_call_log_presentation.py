from datetime import datetime, timedelta
import unittest

from PyQt5.QtWidgets import QApplication

from core.codec_call_history import CallRecord, snapshot_from_records
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


if __name__ == "__main__":
    unittest.main()
