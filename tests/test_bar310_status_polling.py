"""Synthetic regression coverage for the Bar 310 status polling contract."""

import unittest
from contextlib import nullcontext
from unittest.mock import patch

from core.exceptions import (
    AuthenticationError,
    CommandError,
    ConnectionError,
    ParseError,
    ProtocolError,
    SessionInvalidError,
)
from core.parser import HuaweiBar310DataParser
from core.workers.codec_polling import HuaweiBar310Worker
from handlers.huawei.bar310 import CloudLinkBar310Handler


CORE = {"success": 1, "data": {"softVersion": "  V1.2.3  "}}


def handler_with_responses(responses, microphone_response=None):
    handler = CloudLinkBar310Handler("synthetic-host", username="assigned", password="assigned")
    calls = []

    def send_command(command, data=None):
        calls.append(command)
        response = responses.get(command)
        if isinstance(response, BaseException):
            raise response
        return response

    def microphone_request(endpoint, method="POST", data=None):
        calls.append((method, endpoint))
        if isinstance(microphone_response, BaseException):
            raise microphone_response
        return microphone_response

    handler.send_command = send_command
    handler._make_request = microphone_request
    return handler, calls


class Bar310StatusPollingTests(unittest.TestCase):
    def test_closed_plan_collects_only_reviewed_endpoints(self):
        responses = {
            "get_version": {"success": 1, "data": {"softVersion": " V1 "}},
            "get_mac": {"success": 1, "data": {"system_wanMAC_addr": "WAN", "system_lanMAC_addr": "LAN"}},
            "get_audio_status": {"success": 1, "data": {"MicSwitch": 0, "SpeakerSwitch": 1, "speakerValue": 0}},
            "get_line_state": {"success": 1, "data": {"runDay": 0, "runHour": 1, "runMin": 2, "sipStatusTxStr": "SIP_STATE_OK"}},
            "get_call_status": {"success": 1, "data": {"state": {"callstate": 0, "sip": 0}}},
            "get_presentation": {"success": 1, "data": {"isSendAux": "auxClose"}},
            "get_sleep_mode": {"success": 1, "data": {"isSystemSleep": "unsleep"}},
            "get_camera_status": {"success": 1, "data": {"localInMainSource": 255}},
            "get_config": {"success": 1, "data": {}},
            "get_config_default": {"success": 1, "data": {}},
            "future_mutation": {"success": 1, "data": {}},
        }
        handler, calls = handler_with_responses(
            responses, {"success": 1, "data": {"deviceList": []}}
        )

        status = handler.get_status()

        self.assertEqual(status["model"], "Huawei CloudLink Bar 310")
        self.assertEqual(status["version"], "V1")
        self.assertEqual(status["mac_address"], "WAN")
        self.assertEqual(status["speaker_volume"], 0)
        self.assertEqual(status["sip_status"], "On")
        self.assertEqual(status["presentation"], "Stop")
        self.assertEqual(status["sleep_mode"], "Off")
        self.assertEqual(status["camera_status"], "On")
        self.assertEqual(status["mic_connection_status"], "Микрофон не подключён")
        self.assertNotIn("mic_volume", status)
        self.assertEqual(
            calls,
            [
                "get_version", "get_mac", "get_audio_status", "get_line_state",
                "get_call_status", "get_presentation", "get_sleep_mode",
                "get_camera_status", ("GET", "v1/mediacontrol/mic/devices"),
            ],
        )

    def test_required_core_gate_is_exact(self):
        invalid_data = [
            {}, {"otherVersion": "V1"}, {"softVersion": None},
            {"softVersion": 1}, {"softVersion": ""},
            {"softVersion": "   "}, {"softVersion": "uNkNoWn"},
        ]
        for data in invalid_data:
            with self.subTest(data=data):
                handler, _ = handler_with_responses({"get_version": {"success": 1, "data": data}})
                with self.assertRaises(ProtocolError):
                    handler.get_status()
        handler, _ = handler_with_responses({"get_version": {"success": 0, "data": {}}})
        with self.assertRaises(CommandError):
            handler.get_status()
        handler, _ = handler_with_responses({"get_version": []})
        with self.assertRaises(ProtocolError):
            handler.get_status()

    def test_optional_failure_preserves_core_and_owned_fields_only(self):
        responses = {
            "get_version": CORE,
            "get_mac": {"success": 1, "data": {"system_lanMAC_addr": "LAN"}},
            "get_audio_status": {"success": 1, "data": {"speakerValue": 0}},
            "get_line_state": {"success": 1, "data": {}},
            "get_call_status": {"success": 1, "data": {"state": {"sip": 1}}},
            "get_presentation": {"success": 1, "data": {"isSendAux": "bad"}},
            "get_sleep_mode": {"success": 0, "data": {}},
            "get_camera_status": {"success": 1, "data": {"localInMainSource": 17}},
        }
        handler, _ = handler_with_responses(responses, {"success": 1, "data": {"deviceList": "bad"}})
        status = handler.get_status()

        self.assertEqual(status["version"], "V1.2.3")
        self.assertEqual(status["mac_address"], "LAN")
        self.assertEqual(status["speaker_volume"], 0)
        self.assertEqual(status["sip_status"], "On")
        for key in ("presentation", "sleep_mode", "camera_status", "mic_connection_status", "mic_volume"):
            self.assertNotIn(key, status)

    def test_terminal_optional_failures_propagate(self):
        for error_type in (AuthenticationError, SessionInvalidError, ConnectionError):
            with self.subTest(error_type=error_type):
                handler, _ = handler_with_responses(
                    {"get_version": CORE, "get_mac": error_type("synthetic terminal failure")}
                )
                with self.assertRaises(error_type):
                    handler.get_status()

    def test_line_sip_wins_and_call_sip_falls_back_only_when_needed(self):
        common = {
            "get_version": CORE, "get_mac": {"success": 1, "data": {}},
            "get_audio_status": {"success": 1, "data": {}},
            "get_presentation": {"success": 0, "data": {}}, "get_sleep_mode": {"success": 0, "data": {}},
            "get_camera_status": {"success": 0, "data": {}},
        }
        responses = dict(common, get_line_state={"success": 1, "data": {"sipStatusTxStr": "SIP_STATE_OK"}}, get_call_status={"success": 1, "data": {"state": {"sip": 0}}})
        handler, _ = handler_with_responses(responses, {"success": 0, "data": {}})
        self.assertEqual(handler.get_status()["sip_status"], "On")
        responses["get_line_state"] = {"success": 1, "data": {}}
        handler, _ = handler_with_responses(responses, {"success": 0, "data": {}})
        self.assertEqual(handler.get_status()["sip_status"], "Off")

    def test_hd_ai_and_camera_observations_remain_distinct_from_unavailable(self):
        base = {
            "get_version": CORE, "get_mac": {"success": 0, "data": {}}, "get_audio_status": {"success": 0, "data": {}},
            "get_line_state": {"success": 0, "data": {}}, "get_call_status": {"success": 0, "data": {}},
            "get_presentation": {"success": 0, "data": {}}, "get_sleep_mode": {"success": 0, "data": {}},
            "get_camera_status": {"success": 1, "data": {"localInMainSource": 0}},
        }
        handler, _ = handler_with_responses(base, {"success": 1, "data": {"deviceList": [{"groupName": "HD-AI", "plugStatus": "1", "gainVolume": 0}]}})
        status = handler.get_status()
        self.assertEqual(status["camera_status"], "Off")
        self.assertEqual(status["mic_connection_status"], "Подключён")
        self.assertEqual(status["mic_volume"], 0)
        handler, _ = handler_with_responses(base, {"success": 1, "data": {"deviceList": [{"groupName": "HD-AI", "plugStatus": 0}]}})
        status = handler.get_status()
        self.assertEqual(status["mic_connection_status"], "Микрофон не подключён")
        self.assertNotIn("mic_volume", status)
        handler, _ = handler_with_responses(base, {"success": 1, "data": {"deviceList": [{"groupName": "HD-AI", "plugStatus": 1}]}})
        status = handler.get_status()
        self.assertNotIn("mic_connection_status", status)
        self.assertNotIn("mic_volume", status)

    def test_presentation_and_sleep_helpers_are_shared_with_readback(self):
        handler, _ = handler_with_responses(
            {"get_presentation": {"success": 1, "data": {"isSendAux": "auxOpen"}}, "get_sleep_mode": {"success": 1, "data": {"isSystemSleep": "sleep"}}}
        )
        self.assertEqual(handler.get_presentation_status(), "Start")
        self.assertEqual(handler.get_sleep_mode(), "On")
        handler, _ = handler_with_responses({"get_presentation": {"success": 1, "data": {"isSendAux": "other"}}})
        with self.assertRaises(ProtocolError):
            handler.get_presentation_status()

    def test_parser_requires_exact_core_and_omits_absent_optional_observations(self):
        invalid_payloads = [None, {}, {"model": "wrong", "version": "V1"}, {"model": "Huawei CloudLink Bar 310"}, {"model": "Huawei CloudLink Bar 310", "version": "   "}, {"model": "Huawei CloudLink Bar 310", "version": "Unknown"}, {"model": "Huawei CloudLink Bar 310", "version": "\x00"}]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ParseError):
                    HuaweiBar310DataParser.parse_raw_data(payload)
        parsed = HuaweiBar310DataParser.parse_raw_data({"model": "Huawei CloudLink Bar 310", "version": " V1 ", "speaker_volume": 0, "camera_status": "Off"})
        self.assertEqual(parsed["Модель"], "Huawei CloudLink Bar 310")
        self.assertEqual(parsed["Версия ПО"], "V1")
        self.assertEqual(parsed["Громкость динамиков"], "0")
        self.assertEqual(parsed["Статус камеры"], "Не подключена")
        self.assertNotIn("Режим презентации", parsed)
        self.assertNotIn("Статус звонка", parsed)

    def test_worker_rejects_unusable_raw_status_as_protocol_error(self):
        self._assert_worker_outcome({}, expect_result=False)
        self._assert_worker_outcome([], expect_result=False)
        self._assert_worker_outcome({"ip_address": "metadata"}, expect_result=False)
        self._assert_worker_outcome({"model": "wrong", "version": "V1"}, expect_result=False)

    def test_worker_classifies_parser_contract_failure_as_protocol_error(self):
        self._assert_worker_outcome(
            {"model": "Huawei CloudLink Bar 310", "version": "V1"},
            expect_result=False,
            parser_error=ParseError("synthetic parser contract failure"),
        )

    def test_worker_emits_usable_partial_status_then_cleans_up(self):
        events, results, errors = self._assert_worker_outcome(
            {"model": "Huawei CloudLink Bar 310", "version": "V1", "speaker_volume": 0},
            expect_result=True,
        )
        self.assertFalse(errors)
        self.assertEqual(results[0]["Громкость динамиков"], "0")
        self.assertIn("ip_address", results[0])
        self.assertLess(events.index("result"), events.index("disconnected"))
        self.assertLess(events.index("disconnected"), events.index("finished"))

    def _assert_worker_outcome(self, payload, expect_result, parser_error=None):
        class FakeHandler:
            port = 443
            use_ssl = True

            def __init__(self, **kwargs):
                self.kwargs = kwargs

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
            patch(
                "core.workers.codec_polling.HuaweiBar310DataParser.parse_raw_data",
                side_effect=parser_error,
            )
            if parser_error is not None
            else nullcontext()
        )
        with patch("core.workers.codec_polling.CloudLinkBar310Handler", FakeHandler), parser_context:
            worker.run()
        if expect_result:
            self.assertEqual(len(results), 1)
        else:
            self.assertFalse(results)
            self.assertEqual(errors[0][0], "protocol_error")
            self.assertLess(events.index("error"), events.index("disconnected"))
        self.assertEqual(events[-1], "finished")
        return events, results, errors


if __name__ == "__main__":
    unittest.main()
