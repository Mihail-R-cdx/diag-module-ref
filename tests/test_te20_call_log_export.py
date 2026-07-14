from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tools.te20_call_log_export import export_te20_call_log as export_tool


class Response:
    def __init__(self, body: str, status_code: int = 200):
        self.content = body.encode("utf-8")
        self.status_code = status_code

    def raise_for_status(self):
        return None


class Cookies:
    def __init__(self, session_id: str):
        self.session_id = session_id

    def get(self, name: str, default: str = "") -> str:
        return self.session_id if name == "SessionID" else default


class TE20CallLogExportTests(unittest.TestCase):
    def setUp(self):
        self.password = "synthetic-te20-password"
        self.session_id = "synthetic-te20-session"
        self.csrf_token = "synthetic-te20-csrf"
        self.auth_body = json.dumps(
            {
                "data": json.dumps({"acCSRFToken": self.csrf_token}),
                "password": self.password,
            }
        )
        self.xml = (
            '<?xml version="1.0"?><CallRecordsModule '
            f'password="{self.password}" session="{self.session_id}" '
            f'csrf="{self.csrf_token}" />'
        )

    def assert_public_output_is_safe(self, output: str):
        self.assertNotIn(self.password, output)
        self.assertNotIn(self.session_id, output)
        self.assertNotIn(self.csrf_token, output)
        self.assertNotIn(f"acCSRFToken={self.csrf_token}", output)
        self.assertNotIn(self.auth_body, output)

    def test_requests_transport_keeps_credentials_out_of_diagnostics(self):
        test_case = self

        class Session:
            def __init__(self):
                self.cookies = Cookies(test_case.session_id)
                self.verify = True

            def mount(self, *_args, **_kwargs):
                pass

            def post(self, url, data=None, json=None, headers=None, timeout=None):
                if "WEB_RequestSessionIDAPI" in url:
                    return Response(
                        json_module.dumps({"SessionID": test_case.session_id})
                    )
                if "WEB_RequestCertificateAPI" in url:
                    return Response(test_case.auth_body)
                return Response("not xml")

            def get(self, url, headers=None, timeout=None):
                if "acCSRFToken=" in url:
                    return Response(test_case.xml)
                return Response("not xml")

        json_module = json
        public_output = io.StringIO()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "te20.xml"
            argv = [
                "export_te20_call_log.py",
                "--http",
                "--probe",
                "--password",
                self.password,
                "--output",
                os.fspath(output_path),
            ]
            with patch.object(export_tool.requests, "Session", Session), patch.object(
                sys, "argv", argv
            ), contextlib.redirect_stdout(public_output), contextlib.redirect_stderr(
                public_output
            ):
                export_tool.main()

            self.assertEqual(self.xml, output_path.read_text(encoding="utf-8"))

        output = public_output.getvalue()
        self.assert_public_output_is_safe(output)
        self.assertIn("[session] status=200", output)
        self.assertIn("[auth] status=200", output)
        self.assertIn("[auth] authentication completed", output)
        self.assertIn("[export] status=200", output)

    def test_pycurl_transport_keeps_credentials_out_of_diagnostics(self):
        def fake_pycurl_request(
            url, _cookie_jar_path, *, method="POST", data="", headers=None
        ):
            if "Web_RequestSessionID" in url:
                return {
                    "status": 200,
                    "body": json.dumps({"SessionID": self.session_id}),
                    "headers": "",
                }
            if "Web_RequestCertificate" in url:
                return {"status": 200, "body": self.auth_body, "headers": ""}
            return {"status": 200, "body": self.xml, "headers": ""}

        public_output = io.StringIO()
        with patch.object(
            export_tool, "pycurl_request", fake_pycurl_request
        ), contextlib.redirect_stdout(public_output), contextlib.redirect_stderr(
            public_output
        ):
            result = export_tool.export_with_pycurl(
                "https://192.0.2.1:443", "synthetic-te20-user", self.password
            )

        self.assertEqual(self.xml, result)
        output = public_output.getvalue()
        self.assert_public_output_is_safe(output)
        self.assertIn("[session/pycurl] status=200", output)
        self.assertIn("[auth/pycurl] status=200", output)
        self.assertIn("[auth/pycurl] authentication completed", output)
        self.assertIn("[export/pycurl] status=200", output)

    def test_missing_password_does_not_create_network_session(self):
        session = Mock()
        stderr = io.StringIO()
        with patch.object(export_tool.requests, "Session", session), patch.dict(
            export_tool.os.environ, {"TE20_PASSWORD": ""}
        ), patch.object(sys, "argv", ["export_te20_call_log.py"]), contextlib.redirect_stderr(
            stderr
        ):
            with self.assertRaises(SystemExit):
                export_tool.main()

        session.assert_not_called()


if __name__ == "__main__":
    unittest.main()
