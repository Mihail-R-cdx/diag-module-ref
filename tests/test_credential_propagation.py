import sys
import unittest
import contextlib
import io
from unittest.mock import patch

from core.credentials import AUTH_USERNAME_PASSWORD, Credential
from core.factory import ProtocolFactory
from core.exceptions import AuthenticationError
from handlers.aten.pdu import AtenPDUHandler
from handlers.biamp.tesira_forte_ci import BiampTesiraForteCIHandler


class CredentialPropagationTests(unittest.TestCase):
    def test_factory_passes_explicit_credentials_for_all_supported_device_paths(self):
        captured = []

        class CapturingHandler:
            def __init__(self, **kwargs):
                captured.append(kwargs)

        setattr(sys.modules[__name__], "CapturingHandler", CapturingHandler)
        protocols = (
            "huawei_te20", "huawei_te40", "huawei_bar310", "polycom_rpg310",
            "extron_in1804", "aten_pdu", "biamp_tesira_forte_ci",
        )
        original_handlers = ProtocolFactory._handlers.copy()
        try:
            for protocol in protocols:
                ProtocolFactory.register_handler(protocol, __name__, "CapturingHandler")
                handler = ProtocolFactory.create_handler(
                    protocol,
                    "192.0.2.1",
                    Credential(AUTH_USERNAME_PASSWORD, "synthetic-user", "synthetic-password"),
                )
                self.assertIsInstance(handler, CapturingHandler)
        finally:
            ProtocolFactory._handlers = original_handlers
            delattr(sys.modules[__name__], "CapturingHandler")

        self.assertEqual(len(protocols), len(captured))
        for kwargs in captured:
            self.assertEqual("192.0.2.1", kwargs["ip_address"])
            self.assertEqual("synthetic-user", kwargs["username"])
            self.assertEqual("synthetic-password", kwargs["password"])

    def test_required_auth_handlers_reject_absent_credentials_before_network_io(self):
        aten = AtenPDUHandler("192.0.2.1")
        with patch.object(aten, "_api_request") as request:
            with self.assertRaises(AuthenticationError) as error:
                aten.connect()
        self.assertFalse(request.called)
        self.assertNotIn("password", str(error.exception).lower())

        biamp = BiampTesiraForteCIHandler("192.0.2.1", username="", password="")
        with self.assertRaises(AuthenticationError) as error:
            biamp.connect()
        self.assertNotIn("password", str(error.exception).lower())

    def test_workers_and_handlers_do_not_import_the_json_provider(self):
        for module_path in (
            "core/worker.py", "core/te20_worker.py", "core/factory.py",
            "handlers/aten/pdu.py", "handlers/biamp/tesira_forte_ci.py",
            "handlers/extron/in1804.py", "handlers/huawei/te20.py",
            "handlers/huawei/te40.py", "handlers/huawei/bar310.py",
            "handlers/polycom/rpg310.py",
        ):
            with open(module_path, encoding="utf-8") as source:
                self.assertNotIn("JsonCredentialProvider", source.read(), module_path)

    def test_aten_debug_output_redacts_request_credentials(self):
        class Response:
            status_code = 200

        class Session:
            def get(self, *_args, **_kwargs):
                return Response()

        handler = AtenPDUHandler("192.0.2.1", username="synthetic-user", password="synthetic-password")
        handler.session = Session()
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            handler._api_request("GET", "/api/device/relay")
        output = stdout.getvalue()
        self.assertNotIn("synthetic-user", output)
        self.assertNotIn("synthetic-password", output)


if __name__ == "__main__":
    unittest.main()
