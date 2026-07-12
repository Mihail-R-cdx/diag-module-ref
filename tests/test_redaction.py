import unittest

from core.redaction import REDACTION_MARKER, redact_data, redact_diagnostic, redact_text


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
