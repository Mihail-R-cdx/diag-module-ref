from datetime import datetime, timedelta
import unittest

from core.codec_call_history import (
    CallRecord, MAX_ACCEPTED_RECORDS, TerminationReason, calculate_usage,
    normal_period, snapshot_from_display_records, snapshot_from_records,
    touched_weekday_hours,
)


def record(start, duration=3600, **kwargs):
    return CallRecord("id-" + start.isoformat(), start, duration, **kwargs)


class CodecCallHistoryTests(unittest.TestCase):
    def test_normal_windows_include_today_and_boundary_overlap(self):
        now = datetime(2026, 6, 30, 15)
        start, end = normal_period(now, 30)
        self.assertEqual(datetime(2026, 6, 1), start)
        snap = snapshot_from_records([record(start - timedelta(hours=1), 7200)], reference_now=now, source_ended=True)
        row = calculate_usage(snap)[0]
        self.assertEqual(1.0, row.hours)
        self.assertEqual(176.0, touched_weekday_hours(start, end))

    def test_overlap_is_literal_and_weekend_is_not_removed_from_numerator(self):
        now = datetime(2026, 6, 7, 12)  # Sunday
        second = CallRecord("separate-overlap", datetime(2026, 6, 6, 22), 7200)
        snap = snapshot_from_records([
            record(datetime(2026, 6, 6, 22), 7200),
            second,
        ], reference_now=now, source_ended=True)
        row = calculate_usage(snap)[0]
        self.assertEqual(4.0, row.hours)
        self.assertIsNotNone(row.percentage)

    def test_active_and_malformed_records_remain_visible_but_do_not_count(self):
        now = datetime(2026, 6, 9, 12)
        snap = snapshot_from_records([
            record(datetime(2026, 6, 9, 8), None, active=True),
            record(datetime(2026, 6, 9, 9), None),
            record(datetime(2026, 6, 9, 10), 3600),
        ], reference_now=now, source_ended=True)
        self.assertEqual(1.0, calculate_usage(snap)[0].hours)
        self.assertTrue(any("длительностей" in warning for warning in snap.warnings))

    def test_old_start_is_not_coverage_proof(self):
        snap = snapshot_from_records([record(datetime(2026, 6, 1, 9), 1200)], reference_now=datetime(2026, 6, 2, 12))
        self.assertEqual(TerminationReason.SOURCE_HISTORY_LIMITED, snap.termination_reason)
        self.assertEqual((), calculate_usage(snap))

    def test_hard_cap_stops_at_exactly_100_and_uses_47_day_period(self):
        now = datetime(2026, 6, 30, 12)
        records = [record(now - timedelta(days=46, minutes=index), 60) for index in range(MAX_ACCEPTED_RECORDS + 1)]
        snap = snapshot_from_records(records, reference_now=now)
        self.assertEqual(MAX_ACCEPTED_RECORDS, len(snap.records))
        self.assertEqual(TerminationReason.PRODUCT_LIMIT_REACHED, snap.termination_reason)
        self.assertEqual((30, 47), tuple(row.days for row in calculate_usage(snap)))

    def test_hard_cap_under_30_days_shows_one_actual_row_and_partial_monday_is_full_capacity(self):
        now = datetime(2026, 6, 26, 12)  # Friday
        monday_at_15 = datetime(2026, 6, 8, 15)
        records = [record(monday_at_15 + timedelta(minutes=index), 3600) for index in range(MAX_ACCEPTED_RECORDS)]
        snap = snapshot_from_records(records, reference_now=now)
        rows = calculate_usage(snap)
        self.assertEqual(1, len(rows))
        self.assertEqual(19, rows[0].days)
        self.assertEqual(120.0, touched_weekday_hours(monday_at_15, now))

    def test_zero_weekday_capacity_is_safe(self):
        now = datetime(2026, 6, 7, 12)  # Sunday
        records = [CallRecord(f"weekend-{index}", datetime(2026, 6, 7, 9), 60) for index in range(MAX_ACCEPTED_RECORDS)]
        snap = snapshot_from_records(records, reference_now=now)
        row = calculate_usage(snap)[0]
        self.assertIsNone(row.percentage)

    def test_clean_empty_journal_produces_complete_zero_rows(self):
        snap = snapshot_from_records([], reference_now=datetime(2026, 6, 10, 12))
        self.assertEqual(TerminationReason.SOURCE_ENDED, snap.termination_reason)
        self.assertEqual((30, 90), tuple(row.days for row in calculate_usage(snap)))
        self.assertEqual((0.0, 0.0), tuple(row.hours for row in calculate_usage(snap)))

    def test_hard_cap_over_90_days_keeps_normal_rows_and_allows_over_100_percent(self):
        now = datetime(2026, 6, 30, 12)
        records = [record(now - timedelta(days=95), 24 * 3600)] + [
            record(now - timedelta(hours=24, seconds=index), 24 * 3600)
            for index in range(MAX_ACCEPTED_RECORDS)
        ]
        snap = snapshot_from_records(records, reference_now=now)
        rows = calculate_usage(snap)
        self.assertEqual((30, 90), tuple(row.days for row in rows))
        self.assertGreater(rows[0].percentage, 100)
        self.assertEqual(MAX_ACCEPTED_RECORDS, len(snap.records))

    def test_source_history_limit_preserves_only_interval_safely_proven_target(self):
        now = datetime(2026, 6, 30, 12)
        coverage = datetime(2026, 6, 1)
        snap = snapshot_from_records(
            [record(datetime(2026, 6, 29, 9), 3600)],
            reference_now=now,
            coverage_lower_bound=coverage,
            termination_reason=TerminationReason.SOURCE_HISTORY_LIMITED,
        )
        self.assertEqual(TerminationReason.SOURCE_HISTORY_LIMITED, snap.termination_reason)
        self.assertEqual((30,), tuple(row.days for row in calculate_usage(snap)))

    def test_operational_failure_preserves_only_proven_row(self):
        now = datetime(2026, 6, 30, 12)
        snap = snapshot_from_records(
            [record(datetime(2026, 6, 29, 9), 3600)],
            reference_now=now,
            coverage_lower_bound=datetime(2026, 6, 1),
            termination_reason=TerminationReason.OPERATIONAL_FAILURE,
        )
        self.assertEqual((30,), tuple(row.days for row in calculate_usage(snap)))
        self.assertTrue(any("не завершилось" in warning for warning in snap.warnings))

    def test_duplicate_source_identity_is_suppressed_but_overlapping_calls_are_not(self):
        now = datetime(2026, 6, 10, 12)
        start = datetime(2026, 6, 10, 9)
        snap = snapshot_from_records(
            [
                CallRecord("page-1", start, 3600),
                CallRecord("page-1", start, 3600),
                CallRecord("page-2", start, 3600),
            ],
            reference_now=now,
            source_ended=True,
        )
        self.assertEqual(2, len(snap.records))
        self.assertEqual(2.0, calculate_usage(snap)[0].hours)

    def test_display_only_record_is_visible_but_never_parsed_back_for_usage(self):
        snap = snapshot_from_display_records(
            [{"room_number": "101", "start_time": "10.06.2026 09:00:00", "duration": "01:00:00"}],
            reference_now=datetime(2026, 6, 10, 12),
        )
        self.assertIsNone(snap.records[0].duration_seconds)
        self.assertEqual((), calculate_usage(snap))

    def test_negative_duration_is_malformed_not_zero_duration(self):
        snap = snapshot_from_display_records(
            [{"_raw_start": 1781082000, "_duration_seconds": -1, "duration": "00:00:00"}],
            reference_now=datetime(2026, 6, 10, 12),
        )
        self.assertIsNone(snap.records[0].duration_seconds)
        self.assertTrue(any("длительностей" in warning for warning in snap.warnings))


if __name__ == "__main__":
    unittest.main()
