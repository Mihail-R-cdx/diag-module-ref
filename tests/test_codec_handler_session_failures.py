import io
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from core.exceptions import AuthenticationError, SessionInvalidError
from handlers.huawei.bar310 import CloudLinkBar310Handler
from handlers.huawei.te20 import HuaweiTE20Handler
from handlers.huawei.te40 import HuaweiTE40Handler
from handlers.polycom.rpg310 import PolycomRPG310Handler


class RequestsResponse:
    def __init__(self, status_code, text="{}"):
        self.status_code = status_code
        self.text = text
        self.content = text.encode("utf-8")


class RaisingOpener:
    def __init__(self, code):
        self.code = code

    def open(self, request, timeout=None):
        del timeout
        raise HTTPError(
            request.full_url,
            self.code,
            "rejected",
            hdrs=None,
            fp=io.BytesIO(b"{}"),
        )


class HandlerSessionFailureTests(unittest.TestCase):
    def assert_huawei_microphone_confirmation(
        self,
        handler_type,
        *,
        muted,
        observed,
        expected,
    ):
        handler = handler_type("192.0.2.10", username="u", password="p")
        with patch.object(
            handler,
            "send_command",
            return_value={"success": 0},
        ) as command, patch.object(
            handler,
            "get_microphone_volume",
            return_value=observed,
        ) as readback, patch(
            f"{handler_type.__module__}.time.sleep",
            return_value=None,
        ):
            self.assertEqual(expected, handler.set_microphone_mute(muted))

        expected_action = "WEB_CloseMicAPI" if muted else "WEB_OpenMicAPI"
        self.assertEqual(expected_action, command.call_args.args[0])
        readback.assert_called_once_with()

    def assert_huawei_microphone_confirmation_propagates_session_failure(
        self,
        handler_type,
    ):
        handler = handler_type("192.0.2.10", username="u", password="p")
        with patch.object(
            handler,
            "send_command",
            return_value={"success": 0},
        ), patch.object(
            handler,
            "get_microphone_volume",
            side_effect=SessionInvalidError("expired"),
        ), patch(
            f"{handler_type.__module__}.time.sleep",
            return_value=None,
        ):
            with self.assertRaises(SessionInvalidError):
                handler.set_microphone_mute(False)

    def assert_huawei_microphone_readback(self, handler_type, response, expected):
        handler = handler_type("192.0.2.10", username="u", password="p")
        with patch.object(handler, "send_command", return_value=response) as request:
            self.assertEqual(expected, handler.get_microphone_volume())
        request.assert_called_once_with("get_audio_status")

    def assert_huawei_microphone_session_failure(self, handler_type):
        handler = handler_type("192.0.2.10", username="u", password="p")
        with patch.object(
            handler,
            "send_command",
            side_effect=SessionInvalidError("expired"),
        ):
            with self.assertRaises(SessionInvalidError):
                handler.get_microphone_volume()

    def test_te20_authoritative_microphone_readback_returns_muted(self):
        self.assert_huawei_microphone_readback(
            HuaweiTE20Handler,
            {"success": 1, "data": {"MicSwitch": 0, "mic1Value": 19}},
            "Muted",
        )

    def test_te20_authoritative_microphone_readback_returns_unmuted(self):
        self.assert_huawei_microphone_readback(
            HuaweiTE20Handler,
            {"success": 1, "data": {"MicSwitch": 1, "mic1Value": 0}},
            "Unmuted",
        )

    def test_te20_authoritative_microphone_readback_missing_evidence_is_unavailable(self):
        self.assert_huawei_microphone_readback(
            HuaweiTE20Handler,
            {"success": 1, "data": {"mic1Value": 0}},
            None,
        )

    def test_te20_authoritative_microphone_readback_propagates_session_failure(self):
        self.assert_huawei_microphone_session_failure(HuaweiTE20Handler)

    def test_te20_unmute_confirmation_missing_evidence_is_not_success(self):
        self.assert_huawei_microphone_confirmation(
            HuaweiTE20Handler,
            muted=False,
            observed=None,
            expected=False,
        )

    def test_te20_unmute_confirmation_accepts_authoritative_unmuted(self):
        self.assert_huawei_microphone_confirmation(
            HuaweiTE20Handler,
            muted=False,
            observed="Unmuted",
            expected=True,
        )

    def test_te20_mute_confirmation_accepts_authoritative_muted(self):
        self.assert_huawei_microphone_confirmation(
            HuaweiTE20Handler,
            muted=True,
            observed="Muted",
            expected=True,
        )

    def test_te20_mute_confirmation_rejects_authoritative_unmuted(self):
        self.assert_huawei_microphone_confirmation(
            HuaweiTE20Handler,
            muted=True,
            observed="Unmuted",
            expected=False,
        )

    def test_te20_mute_confirmation_propagates_session_failure(self):
        self.assert_huawei_microphone_confirmation_propagates_session_failure(
            HuaweiTE20Handler
        )

    def test_te40_authoritative_microphone_readback_returns_muted(self):
        self.assert_huawei_microphone_readback(
            HuaweiTE40Handler,
            {"success": 1, "data": {"MicSwitch": 0, "micValue": 7}},
            "Muted",
        )

    def test_te40_authoritative_microphone_readback_returns_unmuted(self):
        self.assert_huawei_microphone_readback(
            HuaweiTE40Handler,
            {"success": 1, "data": {"MicSwitch": 1, "micValue": 0}},
            "Unmuted",
        )

    def test_te40_authoritative_microphone_readback_missing_evidence_is_unavailable(self):
        self.assert_huawei_microphone_readback(
            HuaweiTE40Handler,
            {"success": 1, "data": {"micValue": 0}},
            None,
        )

    def test_te40_authoritative_microphone_readback_propagates_session_failure(self):
        self.assert_huawei_microphone_session_failure(HuaweiTE40Handler)

    def test_te40_unmute_confirmation_missing_evidence_is_not_success(self):
        self.assert_huawei_microphone_confirmation(
            HuaweiTE40Handler,
            muted=False,
            observed=None,
            expected=False,
        )

    def test_te40_unmute_confirmation_accepts_authoritative_unmuted(self):
        self.assert_huawei_microphone_confirmation(
            HuaweiTE40Handler,
            muted=False,
            observed="Unmuted",
            expected=True,
        )

    def test_te40_mute_confirmation_accepts_authoritative_muted(self):
        self.assert_huawei_microphone_confirmation(
            HuaweiTE40Handler,
            muted=True,
            observed="Muted",
            expected=True,
        )

    def test_te40_mute_confirmation_rejects_authoritative_unmuted(self):
        self.assert_huawei_microphone_confirmation(
            HuaweiTE40Handler,
            muted=True,
            observed="Unmuted",
            expected=False,
        )

    def test_te40_mute_confirmation_propagates_session_failure(self):
        self.assert_huawei_microphone_confirmation_propagates_session_failure(
            HuaweiTE40Handler
        )

    def test_te20_established_401_is_session_invalid(self):
        handler = HuaweiTE20Handler(
            "192.0.2.10", username="synthetic", password="synthetic-secret"
        )
        handler._connected = True
        handler.session_id = "synthetic-session"
        handler.csrf_token = "synthetic-csrf"
        handler.session.post = Mock(return_value=RequestsResponse(401))
        try:
            with self.assertRaises(SessionInvalidError):
                handler.send_command("get_version")
        finally:
            handler.disconnect()

    def test_te40_established_403_is_session_invalid(self):
        handler = HuaweiTE40Handler(
            "192.0.2.10", username="synthetic", password="synthetic-secret"
        )
        handler._connected = True
        handler.session_id = "synthetic-session"
        handler.opener = RaisingOpener(403)
        with self.assertRaises(SessionInvalidError):
            handler.send_command("get_version")

    def test_bar310_401_is_phase_sensitive(self):
        handler = CloudLinkBar310Handler(
            "192.0.2.10", username="synthetic", password="synthetic-secret"
        )
        handler.session.request = Mock(return_value=RequestsResponse(401))
        try:
            with self.assertRaises(AuthenticationError):
                handler._make_request(
                    "action.cgi?ActionID=WEB_RequestCertificateAPI"
                )
            with self.assertRaises(SessionInvalidError):
                handler._make_request("action.cgi?ActionID=WEB_GetVersionInfoAPI")
        finally:
            handler.disconnect()

    def test_polycom_401_is_phase_sensitive(self):
        handler = PolycomRPG310Handler(
            "192.0.2.10", username="synthetic", password="synthetic-secret"
        )
        handler.opener = RaisingOpener(401)
        with self.assertRaises(AuthenticationError):
            handler._request_json("/rest/session", require_auth=False)
        handler.authenticated = True
        with self.assertRaises(SessionInvalidError):
            handler._request_json("/rest/config", require_auth=True)

    def test_bar310_presentation_sends_state_change_once_then_reads_back(self):
        handler = CloudLinkBar310Handler(
            "192.0.2.10", username="synthetic", password="synthetic-secret"
        )
        handler.send_command = Mock(return_value={"success": 0})
        handler.get_presentation_status = Mock(return_value="Start")
        try:
            self.assertTrue(handler.set_presentation("Start"))
            self.assertEqual(1, handler.send_command.call_count)
            handler.get_presentation_status.assert_called_once_with()
        finally:
            handler.disconnect()


if __name__ == "__main__":
    unittest.main()
