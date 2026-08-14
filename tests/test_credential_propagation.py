import sys
import unittest
import contextlib
import io
from unittest.mock import Mock, patch

from core.credentials import AUTH_USERNAME_PASSWORD, Credential
from core.factory import ProtocolFactory
from core.exceptions import AuthenticationError, CommandOutcomeUnknownError
from handlers.aten.pdu import AtenPDUHandler
from handlers.biamp.tesira_forte_ci import BiampTesiraForteCIHandler
from handlers.extron.in1804 import ExtronIN1804Handler
from handlers.huawei.bar310 import CloudLinkBar310Handler
from core.te20_worker import HuaweiTE20Worker
from core.worker import CodecSipFixWorker, HuaweiBar310Worker, HuaweiTE40Worker
from gui.main_window import VCSDiagnosticApp


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

    def test_gui_resolved_credentials_reach_every_production_handler_constructor(self):
        captured = []

        class Provider:
            def resolve(self, *, device_model=None, profile_name=None):
                self.request = (device_model, profile_name)
                return Credential(AUTH_USERNAME_PASSWORD, "synthetic-user", "synthetic-password")

        class CapturingHandler:
            def __init__(self, **kwargs):
                captured.append(kwargs)

        model_protocols = {
            "Huawei TE-20": "huawei_te20",
            "Huawei TE-40": "huawei_te40",
            "CloudLink Bar 310": "huawei_bar310",
            "Polycom RPG 310": "polycom_rpg310",
            "Extron IN1804": "extron_in1804",
            "Aten PE8208AV": "aten_pdu",
            "Biamp Tesira Forte CI": "biamp_tesira_forte_ci",
        }
        window = VCSDiagnosticApp.__new__(VCSDiagnosticApp)
        window.credential_provider = Provider()
        setattr(sys.modules[__name__], "CapturingHandler", CapturingHandler)
        original_handlers = ProtocolFactory._handlers.copy()
        try:
            for label, protocol in model_protocols.items():
                ProtocolFactory.register_handler(protocol, __name__, "CapturingHandler")
                resolved = window.resolve_device_credentials(label)
                ProtocolFactory.create_handler(protocol, "192.0.2.1", resolved)
        finally:
            ProtocolFactory._handlers = original_handlers
            delattr(sys.modules[__name__], "CapturingHandler")

        self.assertEqual(7, len(captured))
        self.assertTrue(all(item["username"] == "synthetic-user" for item in captured))
        self.assertTrue(all(item["password"] == "synthetic-password" for item in captured))

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

    def test_bar310_and_extron_reject_missing_auth_before_network_io(self):
        bar310 = CloudLinkBar310Handler("192.0.2.1")
        with patch.object(bar310, "_make_request") as request:
            with self.assertRaises(AuthenticationError):
                bar310.connect()
        self.assertFalse(request.called)

        extron = ExtronIN1804Handler("192.0.2.1")
        with patch.object(extron, "_connect_via_ssh") as ssh, patch.object(
            extron, "_connect_plain_socket"
        ) as plain_socket:
            with self.assertRaises(AuthenticationError):
                extron.connect()
        self.assertFalse(ssh.called)
        self.assertFalse(plain_socket.called)

    def test_bar310_redacts_a_session_token_prefix_in_debug_output(self):
        token = "synthetic-session-token-with-a-long-prefix"
        handler = CloudLinkBar310Handler(
            "192.0.2.1", username="synthetic-user", password="synthetic-password"
        )
        with patch.object(
            handler,
            "_make_request",
            side_effect=[
                {"success": 1},
                {"success": 1, "data": {"acCSRFToken": token}},
            ],
        ), patch.object(
            handler,
            "_modern_request",
            side_effect=[
                {"success": 1},
                {"success": 1, "data": {"acCSRFToken": "modern-session-token"}},
            ],
        ):
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertTrue(handler.connect())
        output = stdout.getvalue()
        self.assertNotIn(token, output)
        self.assertNotIn(token[:20], output)
        self.assertNotIn("synthetic-user", output)
        self.assertNotIn("synthetic-password", output)

    def test_te20_worker_redacts_synthetic_secrets_from_exception_tracebacks(self):
        class RaisingHandler:
            def __init__(self, **_kwargs):
                self.port = 80
                self.use_ssl = False

            def connect(self):
                raise RuntimeError("synthetic-password")

            def disconnect(self):
                pass

        worker = HuaweiTE20Worker(
            "192.0.2.1", username="synthetic-user", password="synthetic-password"
        )
        worker._build_unique_profiles = lambda: [
            {"port": 80, "use_ssl": False, "label": "HTTP:80"}
        ]
        stdout = io.StringIO()
        with patch("core.te20_worker.HuaweiTE20Handler", RaisingHandler), contextlib.redirect_stdout(stdout):
            worker.run()
        output = stdout.getvalue()
        self.assertNotIn("synthetic-user", output)
        self.assertNotIn("synthetic-password", output)

    def test_bar310_worker_propagates_credentials_without_public_output(self):
        captured = []

        class CapturingHandler:
            def __init__(self, **kwargs):
                captured.append(kwargs)
                self.port = kwargs["port"]
                self.use_ssl = True

            def connect(self):
                return True

            def get_status(self):
                return {"username": "synthetic-user", "password": "synthetic-password"}

            def disconnect(self):
                pass

        worker = HuaweiBar310Worker(
            "192.0.2.1",
            username="synthetic-user",
            password="synthetic-password",
            creds_list=[{"username": "synthetic-user", "password": "synthetic-password"}],
        )
        stdout = io.StringIO()
        with patch("core.workers.codec_polling.CloudLinkBar310Handler", CapturingHandler), patch(
            "core.workers.codec_polling.HuaweiBar310DataParser.parse_raw_data", side_effect=lambda data, *_: data
        ), contextlib.redirect_stdout(stdout):
            worker.run()
        self.assertEqual("synthetic-user", captured[0]["username"])
        self.assertEqual("synthetic-password", captured[0]["password"])
        self.assertNotIn("synthetic-user", stdout.getvalue())
        self.assertNotIn("synthetic-password", stdout.getvalue())

    def test_box_worker_keeps_application_identity_separate_from_handler_identity(self):
        captured = []

        class CapturingHandler:
            def __init__(self, **kwargs):
                captured.append(kwargs)
                self.port = kwargs["port"]
                self.use_ssl = True

            def connect(self): return True
            def get_status(self): return {"model": "Huawei CloudLink Box 310", "version": "V1"}
            def disconnect(self): pass

        worker = HuaweiBar310Worker("192.0.2.10", username="user", password="pass", assigned_model="CloudLink Box 310")
        self.assertEqual("CloudLink Box 310", worker.device_name)
        self.assertEqual("CloudLink Box 310", worker.assigned_model)
        self.assertEqual("Huawei CloudLink Box 310", worker.expected_identity)
        with patch("core.workers.codec_polling.CloudLinkBar310Handler", CapturingHandler):
            worker.run()
        self.assertEqual("Huawei CloudLink Box 310", captured[0]["expected_identity"])

    def test_refresh_composition_preserves_application_and_display_identities(self):
        for model, expected in (
            ("CloudLink Bar 310", "Huawei CloudLink Bar 310"),
            ("CloudLink Box 310", "Huawei CloudLink Box 310"),
        ):
            with self.subTest(model=model):
                app = VCSDiagnosticApp.__new__(VCSDiagnosticApp)
                app.huawei_settings = {"port": 443}
                app.current_device_name = lambda: model
                app.device_credentials = {model: [{"username": "user", "password": "pass"}]}
                app.validate_ip_address = lambda _ip: True
                app._snapshot_credential_candidates = lambda *_args: ()
                app._snapshot_credential_index = lambda *_args: 0
                app.show_progress_dialog = Mock()
                app.show_codec_poll_terminal = Mock()
                app._bind_worker = Mock()
                app.on_codec_poll_terminal_log = Mock()
                app.refresh_btn = Mock()
                with patch("gui.main_window.QThreadPool.globalInstance") as pool:
                    VCSDiagnosticApp.refresh_huawei_bar310(app, "192.0.2.10")
                worker = app.current_worker
                self.assertEqual(model, worker.device_name)
                self.assertEqual(model, worker.assigned_model)
                self.assertEqual(expected, worker.expected_identity)
                pool.return_value.start.assert_called_once_with(worker)

    def test_box_sip_worker_uses_shared_handler_with_box_identity(self):
        captured = []

        class CapturingHandler:
            def __init__(self, **kwargs):
                captured.append(kwargs)

        worker = CodecSipFixWorker("CloudLink Box 310", "192.0.2.10", 443, "user", "pass", "sip.example.test")
        with patch("core.workers.codec_actions.CloudLinkBar310Handler", CapturingHandler):
            worker._create_handler()
        self.assertEqual("CloudLink Box 310", worker.device_name)
        self.assertEqual("Huawei CloudLink Box 310", captured[0]["expected_identity"])

    def test_box_sip_worker_run_preserves_identity_and_never_blindly_replays(self):
        calls, results, errors = [], [], []

        class FakeSipHandler:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def connect(self):
                calls.append("connect")
                return True

            def set_sip_server(self, server):
                calls.append(("set_sip_server", server))
                return True

            def verify_sip_server(self):
                calls.append("verify_sip_server")
                return "sip.example.test"

            def disconnect(self):
                calls.append("disconnect")

        worker = CodecSipFixWorker("CloudLink Box 310", "192.0.2.10", 443, "user", "pass", "sip.example.test")
        worker.signals.result.connect(results.append)
        with patch("core.workers.codec_actions.CloudLinkBar310Handler", FakeSipHandler):
            worker.run()
        self.assertEqual(1, len([call for call in calls if isinstance(call, tuple) and call[0] == "set_sip_server"]))
        self.assertEqual("CloudLink Box 310", results[0]["device_name"])
        self.assertTrue(results[0]["success"])

        class UnknownSipHandler(FakeSipHandler):
            def set_sip_server(self, server):
                calls.append(("unknown_set_sip_server", server))
                raise CommandOutcomeUnknownError("synthetic unknown outcome")

        failed_worker = CodecSipFixWorker("CloudLink Box 310", "192.0.2.10", 443, "user", "pass", "sip.example.test")
        failed_worker.signals.error.connect(errors.append)
        with patch("core.workers.codec_actions.CloudLinkBar310Handler", UnknownSipHandler):
            failed_worker.run()
        self.assertEqual(1, len([call for call in calls if isinstance(call, tuple) and call[0] == "unknown_set_sip_server"]))
        self.assertEqual("set_sip_server_error", errors[0][0])

    def test_te40_worker_error_and_sip_precondition_do_not_publish_credentials(self):
        secret = "synthetic-te40-password"

        class FailingHandler:
            def __init__(self, **_kwargs):
                self.port = 443
                self.use_ssl = True

            def connect(self):
                raise RuntimeError(f"failure carries {secret}")

            def disconnect(self):
                pass

        worker = HuaweiTE40Worker("192.0.2.1", username="synthetic-te40-user", password=secret)
        emitted = []
        terminal_log = []
        worker.signals.result.connect(emitted.append)
        worker.signals.error.connect(emitted.append)
        worker.signals.terminal_log.connect(terminal_log.append)
        stdout = io.StringIO()
        with patch("core.workers.codec_polling.HuaweiTE40Handler", FailingHandler), contextlib.redirect_stdout(stdout):
            worker.run()
        public_output = stdout.getvalue() + repr(emitted) + "\n".join(terminal_log)
        self.assertNotIn(secret, public_output)

        sip_worker = CodecSipFixWorker(
            "Huawei TE40", "192.0.2.1", 443, "", "", "sip.example.test"
        )
        sip_errors = []
        sip_worker.signals.error.connect(sip_errors.append)
        sip_worker.run()
        self.assertEqual("authentication_error", sip_errors[0][0])


if __name__ == "__main__":
    unittest.main()
