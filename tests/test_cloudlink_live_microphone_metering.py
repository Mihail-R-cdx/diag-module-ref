import json
import unittest

try:
    from PyQt5.QtCore import QObject, pyqtSignal
    from PyQt5.QtTest import QTest
    from PyQt5.QtWidgets import QApplication
except ImportError:
    QApplication = None

from handlers.huawei.bar310 import (
    BOX_MICROPHONE_FIELDS,
    CloudLinkBar310Handler,
    normalize_cloudlink_bar_microphone_sample,
    normalize_cloudlink_box_microphone_sample,
)
from core.exceptions import SessionInvalidError


class CloudLinkLiveMicrophoneMeteringTests(unittest.TestCase):
    class _Response:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self.text = json.dumps(payload)

    class _EstablishedSession:
        def __init__(self, response):
            self.response = response
            self.calls = []

        def request(self, **kwargs):
            self.calls.append(kwargs)
            return self.response

    def _established_bar(self, response):
        handler = CloudLinkBar310Handler("192.0.2.10", username="user", password="secret")
        established = self._EstablishedSession(response)
        handler.modern_session = established
        handler._connected = True
        handler.acCSRFToken = "existing-modern-token"
        return handler, established

    def test_bar_meter_uses_established_modern_session_and_access_token(self):
        handler, established = self._established_bar(self._Response(200, {
            "success": 1, "data": {"curMicVouumeList": [{"deviceId": 18, "curVolume": 4}]},
        }))

        sample = handler.get_live_microphone_sample()

        self.assertEqual(4, sample["raw_level"])
        self.assertEqual(1, len(established.calls))
        request = established.calls[0]
        self.assertIs(established, handler.modern_session)
        self.assertEqual("GET", request["method"])
        self.assertEqual("https://192.0.2.10:443/v1/mediacontrol/mic/current-volume", request["url"])
        self.assertEqual("existing-modern-token", request["headers"]["X-Access-Token"])
        self.assertIsNone(request["data"])
        self.assertNotIn("X-Access-Token", request["url"])

    def test_bar_established_modern_session_rejection_remains_typed(self):
        handler, established = self._established_bar(self._Response(403, {"success": 0}))

        with self.assertRaises(SessionInvalidError):
            handler.get_live_microphone_sample()

        self.assertEqual(1, len(established.calls))
        request = established.calls[0]
        self.assertEqual("existing-modern-token", request["headers"]["X-Access-Token"])
        self.assertNotIn("X-Access-Token", request["url"])
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

    def test_bar_accepts_all_numeric_entries_and_ignores_invalid_values(self):
        sample = normalize_cloudlink_bar_microphone_sample({"curMicVouumeList": [
            {"deviceId": 999, "curVolume": 0}, {"deviceId": -5, "curVolume": 7.5},
            {"deviceId": 18, "curVolume": 20}, {"curVolume": True},
            {"curVolume": -1}, {"curVolume": "21"}, {}, None,
        ]})
        self.assertEqual({"available": True, "raw_level": 20, "fraction": 1.0}, sample)

    def test_box_every_approved_field_participates_and_closed_set_excludes_inputs(self):
        for field in BOX_MICROPHONE_FIELDS:
            with self.subTest(field=field):
                payload = {field: 6, "trsValueIndex": 99, "rcaValueIndex": 98,
                           "hdmiValueIndex": 97, "blueToothInValueIndex": 96,
                           "uacValueIndex": 95, "m220w_porwer_hint": 94}
                self.assertEqual(6, normalize_cloudlink_box_microphone_sample(payload)["raw_level"])

    def test_box_mixed_values_keeps_zero_and_rejects_invalid_only_payload(self):
        self.assertEqual(0, normalize_cloudlink_box_microphone_sample({"mic2ValueIndex": 0})["raw_level"])
        self.assertFalse(normalize_cloudlink_box_microphone_sample({
            "mic1ValueIndex": True, "mic2ValueIndex": -1, "mic3ValueIndex": "3"
        })["available"])


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

    def test_protocol_failure_is_sample_local_and_auth_failure_is_terminal(self):
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
                self.submits.append((operation, generation)); return len(self.submits)

        session = Session(); meter = CloudLinkMicrophoneMeter(session=session); samples = []; terminals = []
        meter.sample.connect(samples.append)
        meter.terminal.connect(terminals.append)
        meter.start("CloudLink Bar 310", "192.0.2.10", (), generation=7, token=3)
        session.signals.error.emit({"kind": "cloudlink_microphone_meter", "generation": 7, "client_token": 3, "category": "protocol_error"})
        QTest.qWait(1050)
        self.assertEqual(2, len(session.submits))
        self.assertFalse(samples[-1]["available"])
        session.signals.error.emit({"kind": "cloudlink_microphone_meter", "generation": 7, "client_token": 3, "category": "authentication_error"})
        QTest.qWait(1050)
        self.assertEqual(2, len(session.submits))
        self.assertEqual(["authentication_error"], [outcome["category"] for outcome in terminals])
        self.assertFalse(meter._active)

    def test_sample_local_failure_allows_later_success_without_persistence(self):
        from core.cloudlink_microphone_meter import CloudLinkMicrophoneMeter

        class Signals(QObject):
            result = pyqtSignal(dict); error = pyqtSignal(dict); dropped = pyqtSignal(dict)

        class Session:
            def __init__(self): self.signals = Signals(); self.submits = []
            def submit(self, operation, *, generation): self.submits.append((operation, generation)); return len(self.submits)

        session = Session(); meter = CloudLinkMicrophoneMeter(session=session); samples = []
        meter.sample.connect(samples.append)
        meter.start("CloudLink Bar 310", "192.0.2.10", (), generation=5, token=6)
        session.signals.error.emit({"kind": "cloudlink_microphone_meter", "generation": 5,
                                    "client_token": 6, "category": "protocol_error"})
        QTest.qWait(1050)
        session.signals.result.emit({"kind": "cloudlink_microphone_meter", "generation": 5,
                                     "client_token": 6, "value": {"available": True, "raw_level": 7, "fraction": .35}})
        self.assertEqual([False, True], [sample["available"] for sample in samples])
        self.assertEqual(7, samples[-1]["raw_level"])
        self.assertTrue(meter._active)
        self.assertEqual(2, len(session.submits))

    def test_typed_terminal_failure_stops_after_existing_bounded_recovery(self):
        from core.exceptions import SessionInvalidError
        from core.interactive_session import InteractiveSessionController
        from core.cloudlink_microphone_meter import CloudLinkMicrophoneMeter

        attempts = []

        class Handler:
            def connect(self): return True
            def disconnect(self): pass
            def get_live_microphone_sample(self):
                attempts.append("sample")
                raise SessionInvalidError("synthetic established-session rejection")

        session = InteractiveSessionController(handler_factory=lambda *_args: Handler())
        meter = CloudLinkMicrophoneMeter(session=session); samples = []
        meter.sample.connect(samples.append)
        generation = session.activate_context("CloudLink Bar 310", "192.0.2.10", ({"username": "u", "password": "p"},))
        meter.start("CloudLink Bar 310", "192.0.2.10", (), generation=generation, token=8)
        session.wait_until_idle(2); QApplication.processEvents()
        QTest.qWait(20); QApplication.processEvents()
        try:
            self.assertEqual(["sample", "sample"], attempts)
            self.assertEqual([False], [sample["available"] for sample in samples])
            self.assertFalse(meter._active)
        finally:
            session.shutdown(wait=True)


if __name__ == "__main__":
    unittest.main()
