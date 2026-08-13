from datetime import datetime
import unittest

from core.codec_call_history import (
    CallRecord, TerminationReason, snapshot_from_display_records,
    snapshot_from_records,
)
from core.exceptions import ProtocolError
from core.workers.codec_call_logs import PolycomCallLogWorker
from handlers.huawei.bar310 import CloudLinkBar310Handler
from handlers.huawei.te20 import HuaweiTE20Handler
from handlers.huawei.te40 import HuaweiTE40Handler
from handlers.polycom.rpg310 import PolycomRPG310Handler


class CodecCallLogHandlerTests(unittest.TestCase):
    def test_all_supported_parsers_preserve_more_than_ten_source_records(self):
        te_calls = [
            {
                "id": str(index),
                "StartTime": f"10/06/2026 09:00:{index:02d}",
                "StopTime": f"10/06/2026 09:01:{index:02d}",
            }
            for index in range(12)
        ]
        bar_calls = [
            {"id": str(index), "startTime": 1781082000 + index, "endTime": 1781082060 + index}
            for index in range(12)
        ]
        polycom_calls = [
            {"id": str(index), "startTime": 1781082000 + index, "duration": 60}
            for index in range(12)
        ]

        te20 = object.__new__(HuaweiTE20Handler)
        te40 = object.__new__(HuaweiTE40Handler)
        bar = object.__new__(CloudLinkBar310Handler)
        polycom = object.__new__(PolycomRPG310Handler)
        parsed = (
            te20._parse_p2p_call_records({"CallList": te_calls}),
            te40._parse_p2p_call_records({"CallList": te_calls}),
            bar._parse_call_records({"callRecordList": bar_calls}),
            polycom._parse_call_records(polycom_calls),
        )

        for records in parsed:
            self.assertEqual(12, len(records))
            self.assertEqual("0", records[0]["source_identity"])
            self.assertIn("_raw_start", records[0])

    def test_polycom_worker_publishes_typed_snapshot_from_dedicated_worker(self):
        snapshot = snapshot_from_records(
            [CallRecord("record", datetime(2026, 6, 10, 9), 60)],
            reference_now=datetime(2026, 6, 10, 12),
            source_ended=True,
        )

        class Handler:
            disconnected = False

            def __init__(self, **_kwargs):
                pass

            def connect(self):
                return True

            def get_call_history_snapshot(self):
                return snapshot

            def disconnect(self):
                self.disconnected = True

        worker = PolycomCallLogWorker(Handler, {})
        results = []
        worker.signals.result.connect(results.append)
        worker.run()

        self.assertEqual(1, len(results))
        self.assertIs(snapshot, results[0]["snapshot"])
        self.assertEqual(list(snapshot.records), results[0]["records"])

    def test_valid_empty_journals_are_clean_eoj_but_malformed_shapes_raise_protocol_error(self):
        te20 = object.__new__(HuaweiTE20Handler)
        te40 = object.__new__(HuaweiTE40Handler)
        bar = object.__new__(CloudLinkBar310Handler)
        polycom = object.__new__(PolycomRPG310Handler)

        empty_parsers = (
            (te20._parse_p2p_call_records, {"CallList": []}),
            (te40._parse_p2p_call_records, {"CallList": []}),
            (bar._parse_call_records, {"callRecordList": []}),
            (polycom._parse_call_records, []),
        )
        for parser, payload in empty_parsers:
            with self.subTest(payload=payload):
                self.assertEqual([], parser(payload))
                snapshot = snapshot_from_display_records(
                    parser(payload), source_ended=True,
                )
                self.assertEqual(TerminationReason.SOURCE_ENDED, snapshot.termination_reason)

        malformed_parsers = (
            (te20._parse_p2p_call_records, {}),
            (te40._parse_p2p_call_records, {"CallList": {}}),
            (bar._parse_call_records, {"callRecordList": {}}),
            (polycom._parse_call_records, {"entries": []}),
        )
        for parser, payload in malformed_parsers:
            with self.subTest(payload=payload):
                with self.assertRaises(ProtocolError):
                    parser(payload)


if __name__ == "__main__":
    unittest.main()
