import unittest

try:
    from PyQt5.QtCore import QObject, pyqtSignal
    from PyQt5.QtTest import QTest
    from PyQt5.QtWidgets import QApplication
except ImportError:
    QApplication = None

from handlers.huawei.bar310 import (
    normalize_cloudlink_bar_microphone_sample,
    normalize_cloudlink_box_microphone_sample,
)


class CloudLinkLiveMicrophoneMeteringTests(unittest.TestCase):
    def test_bar_uses_maximum_from_every_device_including_18(self):
        sample = normalize_cloudlink_bar_microphone_sample({"curMicVouumeList": [
            {"deviceId": 18, "curVolume": 21}, {"deviceId": 2, "curVolume": 3},
        ]})
        self.assertEqual({"available": True, "raw_level": 21, "fraction": 1.0}, sample)

    def test_bar_zero_is_available_but_malformed_and_empty_are_not(self):
        self.assertEqual(0.0, normalize_cloudlink_bar_microphone_sample({"curMicVouumeList": [{"curVolume": 0}]} )["fraction"])
        for payload in ({}, {"curMicVouumeList": []}, {"curMicVouumeList": [{"curVolume": -1}, {"curVolume": "3"}]}):
            self.assertFalse(normalize_cloudlink_bar_microphone_sample(payload)["available"])

    def test_box_accepts_only_closed_microphone_fields(self):
        sample = normalize_cloudlink_box_microphone_sample({
            "mic1ValueIndex": 10, "micArray3_03ValIdx": 15,
            "trsValueIndex": 99, "hdmiValueIndex": 98, "blueToothIn": 97, "uacValueIndex": 96,
        })
        self.assertEqual(15, sample["raw_level"])
        self.assertEqual(0.75, sample["fraction"])

    def test_box_missing_or_invalid_fields_are_unavailable(self):
        self.assertFalse(normalize_cloudlink_box_microphone_sample({"mic1ValueIndex": -1})["available"])
        self.assertFalse(normalize_cloudlink_box_microphone_sample(None)["available"])


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class CloudLinkMeterLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_serial_cadence_rejects_stale_callbacks_and_never_overlaps(self):
        from core.cloudlink_microphone_meter import CloudLinkMicrophoneMeter

        class Signals(QObject):
            result = pyqtSignal(dict)
            error = pyqtSignal(dict)
            dropped = pyqtSignal(dict)

        class Session:
            def __init__(self):
                self.signals = Signals()
                self.submits = []

            def submit(self, operation, *, generation):
                self.submits.append((operation, generation))
                return len(self.submits)

        session = Session()
        meter = CloudLinkMicrophoneMeter(session=session)
        received = []
        meter.sample.connect(received.append)
        self.assertTrue(meter.start("CloudLink Bar 310", "192.0.2.10", (), generation=4, token=9))
        self.assertEqual(1, len(session.submits))
        QApplication.processEvents()
        self.assertEqual(1, len(session.submits))
        session.signals.result.emit({"kind": "cloudlink_microphone_meter", "generation": 4, "client_token": 9, "value": {"available": True, "raw_level": 0, "fraction": 0.0}})
        self.assertEqual([0], [sample["raw_level"] for sample in received])
        QTest.qWait(1050)
        self.assertEqual(2, len(session.submits))
        meter.stop()
        session.signals.result.emit({"kind": "cloudlink_microphone_meter", "generation": 4, "client_token": 9, "value": {"available": True, "raw_level": 20, "fraction": 1.0}})
        self.assertEqual([0], [sample["raw_level"] for sample in received])


if __name__ == "__main__":
    unittest.main()
