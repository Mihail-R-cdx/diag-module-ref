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
    def test_te20_microphone_readback_returns_mute_state_not_numeric_gain(self):
        handler = HuaweiTE20Handler("192.0.2.10", username="u", password="p")

        with patch.object(
            handler,
            "get_audio_status",
            return_value={"mute": "On", "microphone_volume": 0},
        ):
            self.assertEqual("Muted", handler.get_microphone_volume())

        with patch.object(
            handler,
            "get_audio_status",
            return_value={"mute": "Off", "microphone_volume": 0},
        ):
            self.assertEqual("Unmuted", handler.get_microphone_volume())

    def test_te40_unmuted_zero_gain_uses_authoritative_mute_state(self):
        handler = HuaweiTE40Handler("192.0.2.10", username="u", password="p")

        with patch.object(
            handler,
            "get_audio_status",
            return_value={"mute": "Off", "microphone_volume": 0},
        ):
            self.assertEqual("Unmuted", handler.get_microphone_volume())

    def test_te40_muted_nonzero_gain_uses_authoritative_mute_state(self):
        handler = HuaweiTE40Handler("192.0.2.10", username="u", password="p")

        with patch.object(
            handler,
            "get_audio_status",
            return_value={"mute": "On", "microphone_volume": 7},
        ):
            self.assertEqual("Muted", handler.get_microphone_volume())

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
