from __future__ import annotations

from dataclasses import dataclass
import ast
import os
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtWidgets import QApplication, QTableWidget
except ImportError:
    QApplication = None
    QTableWidget = None


ALIASES = '+OK "list":["Aec1" "AecInput1" "AudioMeter1" "Output2"]'
PEAKS_PUBLISH = '! "publishToken":"Diag1AecInput1peaks" "value":[false true]\n+OK'
LEVELS_PUBLISH = '! "publishToken":"Diag2AudioMeter1levels" "value":[-42.5 0]\n+OK'


@dataclass
class FakeBiampSession:
    transport: str = "ssh"
    port: int = 22
    responses: dict[str, str] | None = None

    def __post_init__(self):
        self.commands = []
        self.closed = False
        if self.responses is None:
            self.responses = {
                "SESSION get aliases": ALIASES,
                "AecInput1 subscribe peaks Diag1AecInput1peaks 500": PEAKS_PUBLISH,
                "AudioMeter1 subscribe levels Diag2AudioMeter1levels 500": LEVELS_PUBLISH,
            }

    def send_command(self, command: str) -> str:
        self.commands.append(command)
        return self.responses.get(command, "-ERR unsupported")

    def close(self) -> None:
        self.closed = True


class FakeBiampSessionManager:
    def __init__(self, sessions=None, fail_ssh=False):
        self.sessions = sessions or [FakeBiampSession()]
        self.fail_ssh = fail_ssh
        self.attempts = []

    def connect(self, *, ip_address, username, password, timeout_seconds):
        self.attempts.append(("ssh", 22))
        if self.fail_ssh:
            self.attempts.append(("telnet", 23))
            session = self.sessions.pop(0)
            session.transport = "telnet"
            session.port = 23
            return session
        return self.sessions.pop(0)


class BiampHandlerParserTest(unittest.TestCase):
    def test_handler_discovers_input_meter_excludes_output_and_subscribes(self):
        from handlers.biamp.tesira_forte_ci import BiampTesiraForteCIHandler

        session = FakeBiampSession()
        handler = BiampTesiraForteCIHandler(
            "link.ru",
            "default",
            "RAW_SECRET",
            transport=FakeBiampSessionManager([session]),
        )

        handler.connect()
        status = handler.get_status()
        handler.disconnect()

        self.assertEqual(
            [
                "SESSION get aliases",
                "AecInput1 subscribe peaks Diag1AecInput1peaks 500",
                "AudioMeter1 subscribe levels Diag2AudioMeter1levels 500",
            ],
            session.commands,
        )
        self.assertEqual(["AecInput1", "AudioMeter1"], [s["alias"] for s in status["signal_sources"]])
        self.assertNotIn("Output2", repr(status["signal_sources"]))
        self.assertEqual("absent", status["signal_sources"][0]["rows"][0]["state"])
        self.assertTrue(session.closed)

    def test_handler_records_telnet_fallback_profile(self):
        from handlers.biamp.tesira_forte_ci import BiampTesiraForteCIHandler

        manager = FakeBiampSessionManager(fail_ssh=True)
        handler = BiampTesiraForteCIHandler(
            "link.ru",
            "default",
            "RAW_SECRET",
            transport=manager,
        )

        handler.connect()
        status = handler.get_status()

        self.assertEqual([("ssh", 22), ("telnet", 23)], manager.attempts)
        self.assertEqual({"protocol": "telnet", "port": 23}, status["connection_profile"])

    def test_parser_returns_normalized_signal_sources(self):
        from core.parser import BiampTesiraForteCIDataParser

        parsed = BiampTesiraForteCIDataParser.parse_raw_data(
            {
                "device_info": {"ip_address": "link.ru"},
                "signal_sources": [
                    {
                        "alias": "AecInput1",
                        "subscription_attribute": "peaks",
                        "rows": [
                            {"channel_number": 1, "value": False},
                            {"channel_number": 2, "value": 12.5},
                        ],
                    },
                ],
            }
        )

        self.assertEqual("audio_dsp", parsed["type"])
        self.assertEqual("Biamp Tesira Forte CI", parsed["model"])
        self.assertEqual("absent", parsed["signal_sources"][0]["rows"][0]["state"])
        self.assertIsNone(parsed["signal_sources"][0]["rows"][1]["state"])


class BiampTransportAuthenticationBoundaryTest(unittest.TestCase):
    def test_ssh_authentication_rejection_stops_before_telnet_fallback(self):
        from core.exceptions import AuthenticationError
        from handlers.biamp import tesira_forte_ci as biamp

        telnet_attempts = []

        def reject_ssh(*_args):
            raise AuthenticationError("Biamp SSH rejected the assigned credential.")

        def open_telnet(*_args):
            telnet_attempts.append(True)
            return FakeBiampSession(transport="telnet", port=23)

        manager = biamp._DefaultBiampSessionManager()
        with patch.object(biamp._ParamikoBiampSession, "open", side_effect=reject_ssh), \
                patch.object(biamp._TelnetBiampSession, "open", side_effect=open_telnet):
            with self.assertRaises(AuthenticationError):
                manager.connect(
                    ip_address="192.0.2.10",
                    username="synthetic-user",
                    password="synthetic-password",
                    timeout_seconds=1.0,
                )

        self.assertEqual([], telnet_attempts)

    def test_ssh_transport_failure_then_telnet_authentication_is_authentication_error(self):
        from core.exceptions import AuthenticationError
        from handlers.biamp import tesira_forte_ci as biamp

        manager = biamp._DefaultBiampSessionManager()
        with patch.object(biamp._ParamikoBiampSession, "open", side_effect=OSError("ssh down")), \
                patch.object(
                    biamp._TelnetBiampSession,
                    "open",
                    side_effect=AuthenticationError("Biamp Telnet rejected the assigned credential."),
                ):
            with self.assertRaises(AuthenticationError):
                manager.connect(
                    ip_address="192.0.2.10",
                    username="synthetic-user",
                    password="synthetic-password",
                    timeout_seconds=1.0,
                )

    def test_non_authentication_transport_failures_remain_connection_error(self):
        from core.exceptions import ConnectionError
        from handlers.biamp import tesira_forte_ci as biamp

        manager = biamp._DefaultBiampSessionManager()
        with patch.object(
            biamp._ParamikoBiampSession,
            "open",
            side_effect=OSError("ssh synthetic-password down"),
        ), patch.object(
            biamp._TelnetBiampSession,
            "open",
            side_effect=TimeoutError("telnet synthetic-password timeout"),
        ):
            with self.assertRaises(ConnectionError) as error:
                manager.connect(
                    ip_address="192.0.2.10",
                    username="synthetic-user",
                    password="synthetic-password",
                    timeout_seconds=1.0,
                )

        message = str(error.exception)
        self.assertIn("ssh:22", message)
        self.assertIn("telnet:23", message)
        self.assertIn("***", message)
        self.assertNotIn("synthetic-password", message)

    def test_paramiko_authentication_exception_is_mapped_to_safe_authentication_error(self):
        import paramiko

        from core.exceptions import AuthenticationError
        from handlers.biamp import tesira_forte_ci as biamp

        class RejectingSSHClient:
            closed = False

            def set_missing_host_key_policy(self, _policy):
                pass

            def connect(self, *_args, **_kwargs):
                raise paramiko.AuthenticationException("Authentication failed.")

            def close(self):
                self.closed = True

        client = RejectingSSHClient()
        with patch.object(paramiko, "SSHClient", return_value=client):
            with self.assertRaises(AuthenticationError) as error:
                biamp._ParamikoBiampSession.open(
                    "192.0.2.10",
                    22,
                    "synthetic-user",
                    "synthetic-password",
                    1.0,
                )

        self.assertTrue(client.closed)
        self.assertIn("Biamp SSH rejected", str(error.exception))
        self.assertNotIn("synthetic-password", str(error.exception))

    def test_telnet_repeated_login_prompt_after_password_is_authentication_error(self):
        from core.exceptions import AuthenticationError
        from handlers.biamp import tesira_forte_ci as biamp

        class LoginRejectedTelnet:
            def __init__(self):
                self.reads = [b"login:", b"Password:", b"login:"]
                self.writes = []

            def read_until(self, _marker, _timeout):
                return self.reads.pop(0)

            def write(self, data):
                self.writes.append(data)

        tn = LoginRejectedTelnet()
        with self.assertRaises(AuthenticationError):
            biamp._telnet_write_login(tn, "synthetic-user", "synthetic-password", 1.0)

        self.assertEqual([b"synthetic-user\n", b"synthetic-password\n"], tn.writes)

    def test_telnet_authentication_words_without_login_state_are_not_auth_boundary(self):
        from handlers.biamp import tesira_forte_ci as biamp

        class MisleadingTelnet:
            def __init__(self):
                self.reads = [b"login:", b"Password:", b"AUTHENTICATION 401 FAILED\n"]

            def read_until(self, _marker, _timeout):
                return self.reads.pop(0)

            def write(self, _data):
                pass

        biamp._telnet_write_login(MisleadingTelnet(), "synthetic-user", "synthetic-password", 1.0)


class BiampMainWindowRoutingTest(unittest.TestCase):
    def test_main_window_declares_biamp_device_and_audio_dsp_screen(self):
        from gui.diagnostic_dispatch import dispatch_entry_for_model

        entry = dispatch_entry_for_model("Biamp Tesira Forte CI")
        self.assertIsNotNone(entry)
        self.assertEqual("audio_dsp", entry.screen_key)

        source = Path("gui/main_window.py").read_text(encoding="utf-8")
        self.assertIn("self.device_to_screen = {", source)
        self.assertIn("entry.diagnostic_model: entry.screen_key", source)
        self.assertIn('"audio_dsp": AudioDSPScreen(self)', source)
        self.assertIn("refresh_biamp_tesira_forte_ci", source)


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class BiampAudioDSPScreenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        if hasattr(self, "screen"):
            self.screen.close()
            self.screen.deleteLater()
            QApplication.processEvents()

    def test_audio_dsp_screen_renders_signal_source_tables(self):
        from PyQt5.QtWidgets import QWidget
        from gui.screens.audio_dsp_screen import AudioDSPScreen

        self.parent_widget = QWidget()
        self.parent_widget.colors = {
            "background": "#121212",
            "surface": "#1E1E1E",
            "primary": "#BB86FC",
            "text_primary": "#FFFFFF",
            "text_secondary": "#B3B3B3",
            "divider": "#2D2D2D",
        }

        self.screen = AudioDSPScreen(self.parent_widget)
        self.screen.update_data(
            {
                "device_info": {"model": "Biamp Tesira Forte CI", "ip_address": "link.ru"},
                "signal_sources": [
                    {
                        "alias": "AecInput1",
                        "subscription_attribute": "peaks",
                        "rows": [
                            {"channel_number": 1, "value": False},
                            {"channel_number": 2, "value": True},
                        ],
                    }
                ],
            }
        )

        from gui.components import SectionCard

        cards = [
            card.title_label.text()
            for card in self.screen.findChildren(SectionCard)
        ]
        self.assertIn("AecInput1 · peaks", cards)
        table = self.screen.findChild(QTableWidget)
        self.assertEqual(["Номер канала", "Значение"], [table.horizontalHeaderItem(i).text() for i in range(2)])
        self.assertEqual("1", table.item(0, 0).text())
        self.assertEqual("False", table.item(0, 1).text())
        self.assertEqual("True", table.item(1, 1).text())


class BiampGUIBoundaryTest(unittest.TestCase):
    def test_gui_modules_do_not_import_biamp_handler_or_ttp_commands(self):
        forbidden_literals = (
            "SESSION get aliases",
            "subscribe peaks",
            "subscribe levels",
        )
        for path in Path("gui").rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for literal in forbidden_literals:
                self.assertNotIn(literal, source, str(path))
            tree = ast.parse(source, filename=str(path))
            for node in ast.walk(tree):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    modules = [node.module or ""]
                for module in modules:
                    self.assertFalse(module.startswith("handlers.biamp"), str(path))


if __name__ == "__main__":
    unittest.main()
