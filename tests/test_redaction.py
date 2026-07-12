import contextlib
import io
import json
import unittest
from unittest.mock import patch

from core.redaction import REDACTION_MARKER, redact_data, redact_diagnostic, redact_text
from handlers.huawei.te40 import HuaweiTE40Handler


class RedactionTests(unittest.TestCase):
    def test_redacts_values_and_sensitive_fields_from_public_payloads(self):
        secret = "synthetic-secret"
        payload = {
            "password": secret,
            "status": f"failed with {secret}",
            "nested": {"authorization": "Bearer token", "ok": True},
        }
        result = redact_data(payload, [secret])
        self.assertEqual(REDACTION_MARKER, result["password"])
        self.assertEqual(f"failed with {REDACTION_MARKER}", result["status"])
        self.assertEqual(REDACTION_MARKER, result["nested"]["authorization"])
        self.assertNotIn(secret, redact_text(payload, [secret]))

    def test_redacts_json_diagnostic_bodies_and_authentication_headers(self):
        secret = "synthetic-secret"
        token = "synthetic-token"
        body = '{"password": "synthetic-secret", "acCSRFToken": "synthetic-token"}'
        redacted = redact_diagnostic(body, (secret, token))
        self.assertNotIn(secret, redacted)
        self.assertNotIn(token, redacted)
        self.assertIn(REDACTION_MARKER, redacted)

    def test_redacts_te40_sensitive_key_variants_and_nested_data_json(self):
        values = {
            "password": "synthetic-password",
            "username": "synthetic-username",
            "credential": "synthetic-credential",
            "token": "synthetic-token",
            "csrf": "synthetic-csrf",
            "session": "synthetic-session",
            "sessionId": "synthetic-session-id",
            "authorization": "Bearer synthetic-authorization",
            "cookie": "synthetic-cookie",
            "secret": "synthetic-secret",
            "access_key": "synthetic-access-key",
            "api_key": "synthetic-api-key",
        }
        payload = {"data": json.dumps(values), **values}

        redacted = redact_data(payload)
        self.assertEqual(REDACTION_MARKER, redacted["password"])
        nested = json.loads(redacted["data"])
        for key, value in values.items():
            self.assertEqual(REDACTION_MARKER, nested[key])
            self.assertNotIn(value, json.dumps(redacted))

    def test_te40_set_sip_server_redacts_request_and_response_secrets(self):
        username = "synthetic-te40-user"
        password = "synthetic-te40-password"
        session_id = "synthetic-te40-session"
        csrf_token = "synthetic-te40-csrf"
        authorization = "Bearer synthetic-te40-authorization"

        class Response:
            def read(self):
                return json.dumps({
                    "success": 1,
                    "data": {
                        "sessionId": session_id,
                        "acCSRFToken": csrf_token,
                        "Authorization": authorization,
                        "password": password,
                    },
                }).encode("utf-8")

        handler = HuaweiTE40Handler("192.0.2.1", username=username, password=password)
        handler._connected = True
        handler.session_id = session_id
        handler.csrf_token = csrf_token
        handler.opener = type("Opener", (), {"open": lambda *_args, **_kwargs: Response()})()
        command_log = []
        handler.command_logger = command_log.append
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertTrue(handler.set_sip_server("sip.example.test"))

        public_output = stdout.getvalue() + "\n".join(command_log)
        for secret in (username, password, session_id, csrf_token, authorization):
            self.assertNotIn(secret, public_output)
        self.assertIn(REDACTION_MARKER, public_output)

    def test_te40_connect_redacts_new_session_and_csrf_values_before_state_assignment(self):
        username = "synthetic-connect-user"
        password = "synthetic-connect-password"
        session_id = "synthetic-new-session-id"
        csrf_token = "synthetic-new-csrf-token"
        authorization = "Bearer synthetic-connect-authorization"
        cookie = "synthetic-connect-cookie"

        class Response:
            def __init__(self, payload):
                self.payload = payload

            def read(self):
                return json.dumps(self.payload).encode("utf-8")

        class Opener:
            def __init__(self):
                self.responses = iter((
                    Response({
                        "success": 1,
                        "data": json.dumps({
                            "acSessionId": session_id,
                            "Authorization": authorization,
                            "cookie": cookie,
                        }),
                    }),
                    Response({
                        "success": 1,
                        "data": json.dumps({"acCSRFToken": csrf_token}),
                    }),
                ))

            def open(self, *_args, **_kwargs):
                return next(self.responses)

        handler = HuaweiTE40Handler("192.0.2.1", username=username, password=password)
        handler.opener = Opener()
        command_log = []
        handler.command_logger = command_log.append

        self.assertIsNone(handler.session_id)
        self.assertIsNone(handler.csrf_token)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertTrue(handler.connect())

        public_output = stdout.getvalue() + "\n".join(command_log)
        for secret in (username, password, session_id, csrf_token, authorization, cookie):
            self.assertNotIn(secret, public_output)
        self.assertIn(REDACTION_MARKER, public_output)
        self.assertEqual(session_id, handler.session_id)
        self.assertEqual(csrf_token, handler.csrf_token)

    def test_te40_sip_gui_exception_boundary_redacts_credentials(self):
        from gui.main_window import VCSDiagnosticApp

        username = "synthetic-gui-user"
        password = "synthetic-gui-password"

        class App:
            def _get_sip_fix_connection_params(self, *_args):
                return 443, 0, {"username": username, "password": password}

            def _start_sip_fix(self, *_args):
                raise RuntimeError(f"SIP request failed for {username}/{password}")

            def hide_progress_dialog(self):
                pass

            def _set_sip_fix_busy(self, _busy):
                pass

        app = App()
        stdout = io.StringIO()
        with patch("gui.main_window.QMessageBox.critical") as critical, \
                contextlib.redirect_stdout(stdout):
            VCSDiagnosticApp.fix_sip_huawei_te40(app, "192.0.2.1")

        public_output = stdout.getvalue() + "\n".join(map(str, critical.call_args[0]))
        self.assertNotIn(username, public_output)
        self.assertNotIn(password, public_output)
        self.assertIn(REDACTION_MARKER, public_output)

    def test_te40_operation_exception_and_traceback_are_redacted(self):
        username = "synthetic-boundary-user"
        password = "synthetic-boundary-password"
        session_id = "synthetic-boundary-session"
        csrf_token = "synthetic-boundary-csrf"
        cookie = "synthetic-boundary-cookie"
        authorization = "Bearer synthetic-boundary-authorization"
        secrets = (username, password, session_id, csrf_token, cookie, authorization)
        error_text = " | ".join(secrets)

        class Opener:
            def open(self, *_args, **_kwargs):
                raise RuntimeError(error_text)

        handler = HuaweiTE40Handler("192.0.2.1", username=username, password=password)
        handler.session_id = session_id
        handler.csrf_token = csrf_token
        handler.cookie_jar = [type("Cookie", (), {"value": cookie})()]
        command_log = []
        handler.command_logger = command_log.append
        handler.opener = Opener()

        def send_command(command, *_args, **_kwargs):
            if command in {
                "get_call_status",
                "get_audio_status",
                "get_monitor_audio_params",
                "get_presentation",
                "get_camera_status",
            }:
                raise RuntimeError(error_text)
            return {}

        handler.send_command = send_command
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            handler.get_status()
            handler._connected = True
            self.assertFalse(handler.set_sip_server("sip.example.test"))
            self.assertIsNone(handler.verify_sip_server())

        public_output = stdout.getvalue() + "\n".join(command_log)
        for secret in secrets:
            self.assertNotIn(secret, public_output)
        self.assertIn(REDACTION_MARKER, public_output)
        self.assertIn("Call-status request failed", public_output)
        self.assertIn("SIP-server update failed", public_output)
        self.assertIn("SIP-server verification failed", public_output)
