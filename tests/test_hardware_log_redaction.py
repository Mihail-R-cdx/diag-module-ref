import contextlib
import io
import unittest
from unittest.mock import patch

from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import QApplication

from gui.main_window import VCSDiagnosticApp
from core.worker import PolycomCallLogWorker, PolycomRPG310Worker
from handlers.huawei.bar310 import CloudLinkBar310Handler
from handlers.huawei.te20 import HuaweiTE20Handler
from handlers.huawei.te40 import HuaweiTE40Handler
from handlers.polycom.rpg310 import PolycomRPG310Handler


class HardwareLogRedactionTests(unittest.TestCase):
    def _assert_handler_redacts(self, handler):
        messages = []
        handler.command_logger = messages.append

        handler._log_command(
            '[payload] {"user":"admin","password":"admin"}'
        )
        handler._log_command(
            '[response] 200 {"acCSRFToken":"admin","data":"private"}'
        )
        handler._log_command(
            "connection admin admin admin"
        )

        text = "\n".join(messages)
        self.assertNotIn("admin", text)
        self.assertNotIn("admin", text)
        self.assertNotIn("admin", text)
        self.assertIn("<redacted>", text)

    def test_bar310_terminal_log_redacts_credentials_and_response(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            handler = CloudLinkBar310Handler(
                "link.ru",
                username="admin",
                password="admin",
            )
        handler.acCSRFToken = "admin"

        self.assertNotIn("admin", stdout.getvalue())
        self.assertNotIn("admin", stdout.getvalue())
        self._assert_handler_redacts(handler)

    def test_bar310_presentation_no_signal_error_is_actionable(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            handler = CloudLinkBar310Handler("link.ru")
        handler.send_command = lambda *_args, **_kwargs: {
            "success": 0,
            "error": {
                "id": 100666941,
                "code": 100687877,
            },
        }
        handler.get_presentation_status = lambda: "Stop"

        with patch("handlers.huawei.bar310.time.sleep"):
            success = handler.set_presentation("Start")

        self.assertFalse(success)
        self.assertIn(
            "Нет видеосигнала",
            handler.last_presentation_error_message,
        )
        self.assertIn(
            "100666941",
            handler.last_presentation_error_message,
        )

    def test_te20_terminal_log_redacts_credentials_and_response(self):
        handler = HuaweiTE20Handler(
            "link.ru",
            username="admin",
            password="admin",
        )
        handler.csrf_token = "admin"
        self._assert_handler_redacts(handler)

    def test_te40_terminal_log_redacts_credentials_and_response(self):
        handler = HuaweiTE40Handler(
            "link.ru",
            username="admin",
            password="admin",
        )
        handler.csrf_token = "admin"
        self._assert_handler_redacts(handler)

    def test_te40_microphone_connection_uses_audio_evidence(self):
        self.assertEqual(
            "Микрофон подключён",
            HuaweiTE40Handler._resolve_microphone_connection_status(
                [],
                {"MicSwitch": 1},
            ),
        )
        self.assertEqual(
            "Микрофон подключён. Модель VPM220",
            HuaweiTE40Handler._resolve_microphone_connection_status(
                ["VPM220"],
                {},
            ),
        )
        self.assertEqual(
            "Микрофон подключён. Модель M220",
            HuaweiTE40Handler._resolve_microphone_connection_status(
                [
                    {
                        "ip": "",
                        "micVersion": (
                            "M220 V100R001 Release 1.1.2.0"
                        ),
                    }
                ],
                {"MicSwitch": 1},
            ),
        )
        self.assertEqual(
            "Не определено",
            HuaweiTE40Handler._resolve_microphone_connection_status(
                [],
                {},
            ),
        )

    def test_te40_camera_type_uses_local_model_mapping(self):
        self.assertEqual(
            "Камера подключена. Модель VPC600/VPC620",
            HuaweiTE40Handler._format_camera_connection_status(24),
        )
        self.assertEqual(
            "Камера подключена. Модель VPC800",
            HuaweiTE40Handler._format_camera_connection_status("29"),
        )
        self.assertEqual(
            "Камера подключена. Модель неизвестна (код 999)",
            HuaweiTE40Handler._format_camera_connection_status(999),
        )

        from core.parser import HuaweiTE40DataParser

        parsed = HuaweiTE40DataParser.parse_raw_data(
            {
                "camera_status": "OnOff",
                "camera_connection_status": (
                    "Камера подключена. Модель VPC600/VPC620"
                ),
            }
        )
        self.assertEqual(
            "Камера подключена. Модель VPC600/VPC620",
            parsed["Статус камеры"],
        )

    def test_te40_parser_formats_monitor_audio_levels(self):
        from core.parser import HuaweiTE40DataParser

        parsed = HuaweiTE40DataParser.parse_raw_data(
            {
                "monitor_mic_value": 20,
                "monitor_speaker_value": 220,
            }
        )

        self.assertEqual(
            "9%",
            parsed["Звук в помещении (микрофон)"],
        )
        self.assertEqual(
            "100%",
            parsed["Звук из динамиков (выход кодека)"],
        )

    def test_polycom_terminal_log_redacts_credentials_and_response(self):
        handler = PolycomRPG310Handler(
            "link.ru",
            username="admin",
            password="admin",
        )
        messages = []
        handler.command_logger = messages.append

        handler._log_command(
            '[payload] {"user":"admin","password":"admin"}'
        )
        handler._log_command(
            '[response] 200 {"session":"admin","data":"private"}'
        )

        text = "\n".join(messages)
        self.assertNotIn("admin", text)
        self.assertNotIn("admin", text)
        self.assertNotIn("admin", text)
        self.assertNotIn("private", text)
        self.assertIn("<redacted>", text)

    def test_polycom_parser_exposes_sip_address(self):
        from core.parser import PolycomDataParser

        parsed = PolycomDataParser.parse_raw_data(
            {
                "model": "Polycom RealPresence Group 310",
                "sip_address": "sip:qa@link.ru",
            }
        )

        self.assertEqual(parsed["SIP адрес"], "sip:qa@link.ru")
        self.assertEqual(parsed["Статус микрофона"], "Не доступно")
        self.assertEqual(parsed["Mute микрофона"], "Не доступно")

        parsed_with_mute = PolycomDataParser.parse_raw_data(
            {"mic_mute": "off"}
        )
        self.assertEqual(
            parsed_with_mute["Статус микрофона"],
            "Не определено",
        )
        self.assertEqual(parsed_with_mute["Mute микрофона"], "Unmuted")

    def test_polycom_disconnect_logs_out_server_session(self):
        handler = PolycomRPG310Handler("link.ru")
        handler.opener = object()
        handler.authenticated = True
        calls = []
        handler._request_json = lambda *args, **kwargs: calls.append(
            (args, kwargs)
        )

        handler.disconnect()

        self.assertEqual("/rest/session", calls[0][0][0])
        self.assertEqual("POST", calls[0][1]["method"])
        self.assertEqual({"action": "Logout"}, calls[0][1]["payload"])
        self.assertFalse(handler.authenticated)
        self.assertIsNone(handler.opener)

    def test_polycom_worker_disconnects_after_post_connect_error(self):
        instances = []

        class FailingHandler:
            def __init__(self, **_kwargs):
                self.command_logger = None
                self.port = 443
                self.disconnected = False
                instances.append(self)

            def connect(self):
                return True

            def get_https_status(self):
                raise RuntimeError("synthetic read failure")

            def disconnect(self):
                self.disconnected = True

        worker = PolycomRPG310Worker(
            "link.ru", username="synthetic-user", password="synthetic-password"
        )
        with patch(
            "handlers.polycom.rpg310.PolycomRPG310Handler",
            FailingHandler,
        ):
            worker.run()

        self.assertEqual(1, len(instances))
        self.assertTrue(instances[0].disconnected)

    def test_polycom_call_log_worker_redacts_failed_request_error(self):
        synthetic_username = "synthetic-polycom-user"
        synthetic_password = "synthetic-polycom-password"
        synthetic_token = "synthetic-polycom-authorization-token"

        class FailingHandler:
            def __init__(self, **_kwargs):
                self.disconnected = False

            def connect(self):
                pass

            def get_call_records(self):
                raise RuntimeError(
                    '{{"username":"{}","password":"{}",'
                    '"Authorization":"Bearer {}"}}'.format(
                        synthetic_username,
                        synthetic_password,
                        synthetic_token,
                    )
                )

            def disconnect(self):
                self.disconnected = True

        worker = PolycomCallLogWorker(
            FailingHandler,
            {
                "username": synthetic_username,
                "password": synthetic_password,
            },
        )
        errors = []
        worker.signals.error.connect(errors.append)

        worker.run()

        self.assertEqual(1, len(errors))
        category, message, details = errors[0]
        self.assertEqual("PolycomCallLogError", category)
        self.assertEqual("", details)
        self.assertIn("Polycom call log request failed", message)
        self.assertIn("<redacted>", message)
        self.assertNotIn(synthetic_username, message)
        self.assertNotIn(synthetic_password, message)
        self.assertNotIn(synthetic_token, message)
        self.assertNotIn("NameError", message)

    def test_te40_presentation_no_signal_error_is_actionable(self):
        handler = HuaweiTE40Handler("link.ru")
        handler.send_command = lambda *_args, **_kwargs: {
            "success": 0,
            "error": {
                "id": 100666963,
                "code": 100687877,
            },
        }
        handler.get_presentation_status = lambda: "Stop"

        with patch("handlers.huawei.te40.time.sleep"):
            success = handler.set_presentation("Start")

        self.assertFalse(success)
        self.assertIn(
            "Нет видеосигнала",
            handler.last_presentation_error_message,
        )
        self.assertIn(
            "100687877",
            handler.last_presentation_error_message,
        )


class RequestLifecycleRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_switching_device_restores_refresh_control(self):
        window = VCSDiagnosticApp()
        reset_calls = []
        try:
            window._active_request = {
                "id": 1,
                "device": "CloudLink Bar 310",
                "ip": "link.ru",
                "screen": window.screens["codec"],
            }
            window.refresh_btn.setEnabled(False)
            window.refresh_btn.setText("Подключение...")

            window.on_device_change("Huawei TE40")

            self.assertIsNone(window._active_request)
            self.assertTrue(window.refresh_btn.isEnabled())
            self.assertEqual(window.refresh_btn.text(), "Обновить данные")
            window.screens["codec"].shutdown_interactive_controller = (
                lambda: reset_calls.append(True)
            )
        finally:
            window.close()
            window.deleteLater()
            QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            QApplication.processEvents()
        self.assertEqual([True], reset_calls)

if __name__ == "__main__":
    unittest.main()
