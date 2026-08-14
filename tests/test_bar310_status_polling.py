"""Regression coverage for the closed CloudLink 310 runtime contract."""

import unittest
import requests
from contextlib import nullcontext
from datetime import datetime
from unittest.mock import Mock
from unittest.mock import patch

from core.exceptions import (
    AuthenticationError,
    CodecFailureCategory,
    CommandError,
    ConnectionError,
    ParseError,
    ProtocolError,
    SessionInvalidError,
    classify_codec_failure,
)
from core.parser import HuaweiBar310DataParser
from core.workers.codec_polling import HuaweiBar310Worker
from handlers.huawei.bar310 import CloudLinkBar310Handler


def handler_with_observations(*, modern_actions=None, modern_state=None, legacy=None):
    handler = CloudLinkBar310Handler("192.0.2.10", username="assigned", password="assigned")
    calls = []
    modern_actions = modern_actions or {}
    legacy = legacy or {}

    def action(command):
        calls.append(("modern-action", command))
        return modern_actions[command]

    def modern(endpoint, method="GET", data=None, **_kwargs):
        calls.append(("modern", method, endpoint, data))
        if endpoint == "v1/login/status":
            return modern_state
        raise AssertionError(f"unexpected modern request: {endpoint}")

    def command(command, data=None):
        calls.append(("legacy", command))
        return legacy[command]

    handler._modern_action = action
    handler._modern_request = modern
    handler.send_command = command
    return handler, calls


class CloudLink310StatusTests(unittest.TestCase):
    def test_closed_status_routing_preserves_legacy_and_modern_boundaries(self):
        handler, calls = handler_with_observations(
            modern_actions={
                "get_version": {"success": 1, "data": {
                    "softVersion": " V1 ", "cameraVersion": [],
                    "micVersion": [{"version": " A "}, {"version": "A"}, {"version": "B"}],
                }},
                "get_mac": {"success": 1, "data": {"system_wanMAC_addr": "WAN", "system_lanMAC_addr": "LAN"}},
                "get_call_status": {"success": 1, "data": {"state": {"sip": 0}}},
            },
            modern_state={"success": 1, "data": {"state": {"isSleep": 0, "callState": 2}}},
            legacy={
                "get_audio_status": {"success": 1, "data": {"speakerValue": 0}},
                "get_line_state": {"success": 1, "data": {"sipStatusTxStr": "SIP_STATE_OK"}},
                "get_presentation": {"success": 1, "data": {"isSendAux": "auxClose"}},
                "get_camera_status": {"success": 1, "data": {"localInMainSource": 255}},
            },
        )

        status = handler.get_status()

        self.assertEqual("V1", status["version"])
        self.assertEqual("WAN", status["mac_address"])
        self.assertEqual("On", status["sip_status"])
        self.assertEqual("Connected", status["call_status"])
        self.assertEqual("Off", status["sleep_mode"])
        self.assertEqual("Встроенная камера", status["camera_version"])
        self.assertEqual("A; B", status["mic_version"])
        self.assertNotIn("mic_connection_status", status)
        self.assertNotIn("mic_volume", status)
        self.assertEqual(
            [entry[:2] for entry in calls],
            [("modern-action", "get_version"), ("modern-action", "get_mac"),
             ("legacy", "get_audio_status"), ("legacy", "get_line_state"),
             ("modern-action", "get_call_status"), ("modern", "GET"),
             ("legacy", "get_presentation"), ("legacy", "get_camera_status")],
        )

    def test_mailbox_sip_is_only_fallback_and_modern_call_state_is_case_sensitive(self):
        modern = {
            "get_version": {"success": 1, "data": {"softVersion": "V1"}},
            "get_mac": {"success": 1, "data": {}},
            "get_call_status": {"success": 1, "data": {"state": {"sip": 0, "callstate": 3}}},
        }
        legacy = {
            "get_audio_status": {"success": 1, "data": {}},
            "get_line_state": {"success": 1, "data": {}},
            "get_presentation": {"success": 0, "data": {}},
            "get_camera_status": {"success": 0, "data": {}},
        }
        handler, _ = handler_with_observations(
            modern_actions=modern, modern_state={"success": 1, "data": {"state": {"isSleep": 1, "callState": 3}}}, legacy=legacy,
        )
        status = handler.get_status()
        self.assertEqual("Off", status["sip_status"])
        self.assertEqual("Disconnected", status["call_status"])
        self.assertEqual("On", handler.get_sleep_mode())

    def test_malformed_peripheral_list_is_unavailable_not_partially_rendered(self):
        handler, _ = handler_with_observations(
            modern_actions={
                "get_version": {"success": 1, "data": {"softVersion": "V1", "cameraVersion": [{"version": "ok"}, {"name": "bad"}], "micVersion": "bad"}},
                "get_mac": {"success": 1, "data": {}}, "get_call_status": {"success": 1, "data": {"state": {}}},
            }, modern_state={"success": 1, "data": {"state": {"isSleep": 0}}},
            legacy={"get_audio_status": {"success": 0, "data": {}}, "get_line_state": {"success": 0, "data": {}}, "get_presentation": {"success": 0, "data": {}}, "get_camera_status": {"success": 0, "data": {}}},
        )
        status = handler.get_status()
        self.assertNotIn("camera_version", status)
        self.assertNotIn("mic_version", status)

    def test_malformed_presentation_is_optional_and_preserves_core_status(self):
        for malformed in ([], {}):
            with self.subTest(malformed=malformed):
                handler, _ = handler_with_observations(
                    modern_actions={
                        "get_version": {"success": 1, "data": {"softVersion": "V1"}},
                        "get_mac": {"success": 1, "data": {}},
                        "get_call_status": {"success": 1, "data": {"state": {}}},
                    },
                    modern_state={"success": 1, "data": {"state": {"isSleep": 0}}},
                    legacy={
                        "get_audio_status": {"success": 1, "data": {}},
                        "get_line_state": {"success": 1, "data": {}},
                        "get_presentation": {"success": 1, "data": {"isSendAux": malformed}},
                        "get_camera_status": {"success": 1, "data": {"localInMainSource": 0}},
                    },
                )

                status = handler.get_status()

                self.assertEqual("V1", status["version"])
                self.assertEqual("Off", status["sleep_mode"])
                self.assertNotIn("presentation", status)

    def test_malformed_optional_sip_enums_do_not_abort_status(self):
        handler, _ = handler_with_observations(
            modern_actions={
                "get_version": {"success": 1, "data": {"softVersion": "V1"}},
                "get_mac": {"success": 1, "data": {}},
                "get_call_status": {"success": 1, "data": {"state": {"sip": {}}}},
            },
            modern_state={"success": 1, "data": {"state": {"isSleep": 0}}},
            legacy={
                "get_audio_status": {"success": 1, "data": {}},
                "get_line_state": {"success": 1, "data": {"sipStatusTxStr": []}},
                "get_presentation": {"success": 1, "data": {"isSendAux": "auxClose"}},
                "get_camera_status": {"success": 1, "data": {"localInMainSource": 0}},
            },
        )

        status = handler.get_status()

        self.assertEqual("V1", status["version"])
        self.assertNotIn("sip_status", status)

    def test_modern_state_fields_are_independently_fail_closed(self):
        cases = (
            ({"callState": 2}, {"call_status": "Connected"}),
            ({"isSleep": {}, "callState": 2}, {"call_status": "Connected"}),
            ({"isSleep": 0, "callState": []}, {"sleep_mode": "Off"}),
            ({"isSleep": {}, "callState": []}, {}),
            ({"isSleep": False, "callState": True}, {}),
        )
        for state, expected in cases:
            with self.subTest(state=state):
                handler, _ = handler_with_observations(
                    modern_actions={
                        "get_version": {"success": 1, "data": {"softVersion": "V1"}},
                        "get_mac": {"success": 1, "data": {}},
                        "get_call_status": {"success": 1, "data": {"state": {}}},
                    },
                    modern_state={"success": 1, "data": {"state": state}},
                    legacy={
                        "get_audio_status": {"success": 1, "data": {}},
                        "get_line_state": {"success": 1, "data": {}},
                        "get_presentation": {"success": 1, "data": {"isSendAux": "auxClose"}},
                        "get_camera_status": {"success": 1, "data": {"localInMainSource": 0}},
                    },
                )

                status = handler.get_status()

                for field, value in expected.items():
                    self.assertEqual(value, status[field])
                for field in {"sleep_mode", "call_status"} - expected.keys():
                    self.assertNotIn(field, status)

    def test_optional_collection_does_not_swallow_terminal_failures(self):
        handler = CloudLinkBar310Handler("192.0.2.10", username="assigned", password="assigned")
        for error in (
            AuthenticationError("rejected"),
            SessionInvalidError("expired"),
            ConnectionError("offline"),
        ):
            with self.subTest(error=type(error).__name__), self.assertRaises(type(error)):
                handler._collect_optional("synthetic", lambda error=error: (_ for _ in ()).throw(error), {})

    def _call_history_handler(self, response=None, error=None):
        handler = CloudLinkBar310Handler("192.0.2.10", username="assigned", password="assigned")
        handler.is_connected = Mock(return_value=True)
        handler.acCSRFToken = "synthetic-token"
        handler.modern_session = Mock()
        if error is not None:
            handler.modern_session.get.side_effect = error
        else:
            handler.modern_session.get.return_value = response
        return handler

    def test_call_history_success_zero_is_command_failure_not_authentication(self):
        response = Mock(status_code=200, text='{"success": 0}')
        handler = self._call_history_handler(response)

        with self.assertRaises(CommandError) as raised:
            handler.get_call_records()

        self.assertEqual(CodecFailureCategory.COMMAND, classify_codec_failure(raised.exception))

    def test_call_history_malformed_http_200_response_is_protocol_failure(self):
        for text in ("not json", "[]"):
            with self.subTest(text=text):
                handler = self._call_history_handler(Mock(status_code=200, text=text))
                with self.assertRaises(ProtocolError):
                    handler.get_call_records()

    def test_call_history_session_and_transport_failures_remain_typed(self):
        for status_code in (401, 403):
            with self.subTest(status_code=status_code):
                handler = self._call_history_handler(Mock(status_code=status_code, text="{}"))
                with self.assertRaises(SessionInvalidError):
                    handler.get_call_records()

        handler = self._call_history_handler(Mock(status_code=500, text="{}"))
        with self.assertRaises(CommandError):
            handler.get_call_records()

        handler = self._call_history_handler(error=requests.exceptions.Timeout("synthetic"))
        with self.assertRaises(ConnectionError):
            handler.get_call_records()

    def test_sleep_readback_rejects_unproved_values(self):
        handler, _ = handler_with_observations(
            modern_state={"success": 1, "data": {"state": {"isSleep": "0"}}}
        )
        with self.assertRaises(ProtocolError):
            handler.get_sleep_mode()

    def test_gain_is_disabled_before_network_io_for_both_exact_models(self):
        for identity in ("Huawei CloudLink Bar 310", "Huawei CloudLink Box 310"):
            with self.subTest(identity=identity):
                handler = CloudLinkBar310Handler("192.0.2.10", username="u", password="p", expected_identity=identity)
                handler.connect = Mock(side_effect=AssertionError("must not connect"))
                handler._make_request = Mock(side_effect=AssertionError("must not request"))
                self.assertFalse(handler.set_microphone_volume(4))
                handler.connect.assert_not_called()
                handler._make_request.assert_not_called()

    def test_modern_action_allowlist_rejects_unverified_legacy_audio_read(self):
        handler = CloudLinkBar310Handler("192.0.2.10", username="u", password="p")
        with self.assertRaises(ProtocolError):
            handler._modern_action("get_audio_status")

    def test_codec_reference_now_uses_approved_structured_calendar_fields(self):
        handler = CloudLinkBar310Handler("192.0.2.10", username="u", password="p")
        handler._modern_request = Mock(return_value={
            "success": 1,
            "data": {
                "year": "2026", "month": 8, "day": 14,
                "hour": 0, "minute": "00", "second": 0,
            },
        })

        self.assertEqual(datetime(2026, 8, 14, 0, 0, 0), handler._get_codec_reference_now())

    def test_codec_reference_now_rejects_missing_or_invalid_calendar_fields(self):
        invalid_data = (
            {"year": 2026, "month": 13, "day": 14, "hour": 9, "minute": 0, "second": 0},
            {"year": 2026, "month": 8, "day": 32, "hour": 9, "minute": 0, "second": 0},
            {"year": 2026, "month": 8, "day": 14, "hour": 24, "minute": 0, "second": 0},
            {"year": 2026, "month": 8, "day": 14, "hour": 9, "minute": 0},
        )
        for data in invalid_data:
            with self.subTest(data=data):
                handler = CloudLinkBar310Handler("192.0.2.10", username="u", password="p")
                handler._modern_request = Mock(return_value={"success": 1, "data": data})
                self.assertIsNone(handler._get_codec_reference_now())

    def test_codec_reference_time_snapshot_marks_only_real_system_fallback(self):
        device_now = datetime(2026, 8, 14, 10, 30, 45)
        handler = CloudLinkBar310Handler("192.0.2.10", username="u", password="p")
        handler.get_call_records = Mock(return_value=[])
        handler._get_codec_reference_now = Mock(return_value=device_now)
        device_snapshot = handler.get_call_history_snapshot()
        self.assertEqual(device_now, device_snapshot.reference_now)
        self.assertEqual("device", device_snapshot.reference_time_source)
        self.assertFalse(any("системное время" in warning.lower() for warning in device_snapshot.warnings))

        handler._get_codec_reference_now = Mock(return_value=None)
        fallback_snapshot = handler.get_call_history_snapshot()
        self.assertEqual("system_fallback", fallback_snapshot.reference_time_source)
        self.assertTrue(any("системное время" in warning.lower() for warning in fallback_snapshot.warnings))

    def test_codec_reference_time_does_not_swallow_session_invalid(self):
        handler = CloudLinkBar310Handler("192.0.2.10", username="u", password="p")
        handler._modern_request = Mock(side_effect=SessionInvalidError("expired"))
        with self.assertRaises(SessionInvalidError):
            handler._get_codec_reference_now()

    def test_parser_renders_proved_peripheral_labels(self):
        parsed = HuaweiBar310DataParser.parse_raw_data({
            "model": "Huawei CloudLink Bar 310", "version": "V1",
            "camera_version": "Встроенная камера", "mic_version": "A; B", "sleep_mode": "Off",
        })
        self.assertEqual("Встроенная камера", parsed["Версия камеры"])
        self.assertEqual("A; B", parsed["Версия микрофона"])
        self.assertEqual("Выключен", parsed["Режим сна"])


class CloudLink310WorkerStatusTests(unittest.TestCase):
    """Keep the worker's status-validation boundary under regression coverage."""

    def test_worker_rejects_unusable_raw_status_as_protocol_error(self):
        for payload in ({}, [], {"ip_address": "metadata"}, {"model": "wrong", "version": "V1"}):
            with self.subTest(payload=payload):
                self._assert_worker_outcome(payload, expect_result=False)

    def test_worker_classifies_parser_contract_failure_as_protocol_error(self):
        self._assert_worker_outcome(
            {"model": "Huawei CloudLink Bar 310", "version": "V1"},
            expect_result=False, parser_error=ParseError("synthetic parser contract failure"),
        )

    def test_worker_rejects_invalid_parser_mappings_as_protocol_error(self):
        raw_status = {"model": "Huawei CloudLink Bar 310", "version": "V1"}
        for parsed in ({}, {"Модель": "Huawei CloudLink Bar 310"}, {"Модель": "wrong", "Версия ПО": "V1"}, {"Модель": "Huawei CloudLink Bar 310", "Версия ПО": ""}):
            with self.subTest(parsed=parsed):
                self._assert_worker_outcome(raw_status, expect_result=False, parser_result=parsed)

    def test_worker_emits_usable_partial_status_then_cleans_up(self):
        events, results, errors = self._assert_worker_outcome(
            {"model": "Huawei CloudLink Bar 310", "version": "V1", "speaker_volume": 0}, expect_result=True,
        )
        self.assertFalse(errors)
        self.assertEqual("0", results[0]["Громкость динамиков"])
        self.assertLess(events.index("result"), events.index("disconnected"))
        self.assertLess(events.index("disconnected"), events.index("finished"))

    def _assert_worker_outcome(self, payload, expect_result, parser_error=None, parser_result=None):
        class FakeHandler:
            port = 443
            use_ssl = True

            def __init__(self, **_kwargs):
                pass

            def connect(self):
                return True

            def get_status(self):
                return payload

            def disconnect(self):
                return None

        worker = HuaweiBar310Worker("synthetic-host", username="assigned", password="assigned")
        events, results, errors = [], [], []
        worker.signals.result.connect(lambda value: (events.append("result"), results.append(value)))
        worker.signals.error.connect(lambda value: (events.append("error"), errors.append(value)))
        worker.signals.disconnected.connect(lambda: events.append("disconnected"))
        worker.signals.finished.connect(lambda: events.append("finished"))
        parser_context = (
            patch("core.workers.codec_polling.HuaweiBar310DataParser.parse_raw_data", side_effect=parser_error)
            if parser_error is not None else
            patch("core.workers.codec_polling.HuaweiBar310DataParser.parse_raw_data", return_value=parser_result)
            if parser_result is not None else nullcontext()
        )
        with patch("core.workers.codec_polling.CloudLinkBar310Handler", FakeHandler), parser_context:
            worker.run()
        if expect_result:
            self.assertEqual(1, len(results))
        else:
            self.assertFalse(results)
            self.assertEqual("protocol_error", errors[0][0])
            self.assertLess(events.index("error"), events.index("disconnected"))
        self.assertEqual("finished", events[-1])
        return events, results, errors


if __name__ == "__main__":
    unittest.main()
