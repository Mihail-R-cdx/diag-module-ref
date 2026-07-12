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
