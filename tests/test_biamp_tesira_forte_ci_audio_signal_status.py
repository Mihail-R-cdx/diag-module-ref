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
    def assert_paramiko_non_retry_outcome(self, error):
        from core.exceptions import AuthenticationError, ProtocolError
        from handlers.biamp import tesira_forte_ci as biamp

        class RejectingSSHClient:
            closed = False

            def set_missing_host_key_policy(self, _policy):
                pass

            def connect(self, *_args, **_kwargs):
                raise error

            def close(self):
                self.closed = True

        client = RejectingSSHClient()
        import paramiko

        with patch.object(paramiko, "SSHClient", return_value=client):
            with self.assertRaises(ProtocolError) as caught:
                biamp._ParamikoBiampSession.open(
                    "192.0.2.10",
                    22,
                    "synthetic-user",
                    "synthetic-password",
                    1.0,
                )

        self.assertTrue(client.closed)
        self.assertIs(caught.exception.__cause__, error)
        self.assertNotIsInstance(caught.exception, AuthenticationError)
        self.assertNotIn("synthetic-password", str(caught.exception))

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

    def test_paramiko_non_retry_authentication_types_are_not_authentication_error(self):
        import paramiko

        cases = (
            paramiko.BadAuthenticationType("publickey", ["password"]),
            paramiko.ssh_exception.PartialAuthentication(["keyboard-interactive"]),
            paramiko.ssh_exception.UnableToAuthenticate(),
        )
        for error in cases:
            with self.subTest(error=type(error).__name__):
                self.assert_paramiko_non_retry_outcome(error)

    def test_paramiko_unknown_authentication_subclass_is_fail_closed_non_retry(self):
        import paramiko

        class UnknownAuthenticationOutcome(paramiko.AuthenticationException):
            pass

        self.assert_paramiko_non_retry_outcome(
            UnknownAuthenticationOutcome("future auth outcome")
        )

    def test_telnet_repeated_login_prompt_after_password_is_authentication_error(self):
        from core.exceptions import AuthenticationError
        from handlers.biamp import tesira_forte_ci as biamp

        for followup in (
            b"login:",
            b"Password:",
            b"Welcome to the Tesira Text Protocol Server\r\nPassword:",
        ):
            with self.subTest(followup=followup):
                class LoginRejectedTelnet:
                    def __init__(self):
                        self.reads = [b"login:", b"Password:", followup]
                        self.writes = []

                    def read_until(self, _marker, _timeout):
                        return self.reads.pop(0)

                    def write(self, data):
                        self.writes.append(data)

                tn = LoginRejectedTelnet()
                with self.assertRaises(AuthenticationError):
                    biamp._telnet_write_login(tn, "synthetic-user", "synthetic-password", 1.0)

                self.assertEqual([b"synthetic-user\n", b"synthetic-password\n"], tn.writes)

    def test_telnet_missing_initial_login_prompt_fails_closed_without_session(self):
        from core.exceptions import ConnectionError
        from handlers.biamp import tesira_forte_ci as biamp

        class MissingLoginPromptTelnet:
            def __init__(self, first_read):
                self.reads = [first_read]
                self.writes = []
                self.close_count = 0

            def read_until(self, _marker, _timeout):
                return self.reads.pop(0)

            def write(self, data):
                self.writes.append(data)

            def close(self):
                self.close_count += 1

        for first_read in (b"", b"Welcome operator\r\n"):
            with self.subTest(first_read=first_read):
                tn = MissingLoginPromptTelnet(first_read)
                with patch("telnetlib.Telnet", return_value=tn):
                    with self.assertRaises(ConnectionError) as caught:
                        biamp._TelnetBiampSession.open(
                            "192.0.2.10",
                            23,
                            "synthetic-user",
                            "synthetic-password",
                            1.0,
                        )

                self.assertEqual([], tn.writes)
                self.assertEqual(1, tn.close_count)
                self.assertIn("login prompt", str(caught.exception))
                self.assertNotIn("synthetic-user", str(caught.exception))
                self.assertNotIn("synthetic-password", str(caught.exception))

    def test_telnet_authentication_words_without_login_state_are_protocol_timeout(self):
        from core.exceptions import AuthenticationError, ConnectionError
        from handlers.biamp import tesira_forte_ci as biamp

        class MisleadingTelnet:
            def __init__(self, followup):
                self.reads = [b"login:", b"Password:", followup]

            def read_until(self, _marker, _timeout):
                return self.reads.pop(0)

            def write(self, _data):
                pass

        for followup in (
            b"AUTHENTICATION 401 FAILED\n",
            b"auth failed 403\n",
            b"Tesira authentication failed\n",
        ):
            with self.subTest(followup=followup):
                with self.assertRaises(ConnectionError) as caught:
                    biamp._telnet_write_login(
                        MisleadingTelnet(followup),
                        "synthetic-user",
                        "synthetic-password",
                        1.0,
                    )
                self.assertNotIsInstance(caught.exception, AuthenticationError)

    def test_telnet_failed_open_closes_socket_and_preserves_authentication_error(self):
        from core.exceptions import AuthenticationError
        from handlers.biamp import tesira_forte_ci as biamp

        class CountingTelnet:
            def __init__(self):
                self.close_count = 0

            def close(self):
                self.close_count += 1

        tn = CountingTelnet()
        original = AuthenticationError("Biamp Telnet rejected the assigned credential.")
        with patch("telnetlib.Telnet", return_value=tn), patch.object(
            biamp, "_telnet_write_login", side_effect=original
        ):
            with self.assertRaises(AuthenticationError) as caught:
                biamp._TelnetBiampSession.open(
                    "192.0.2.10",
                    23,
                    "synthetic-user",
                    "synthetic-password",
                    1.0,
                )

        self.assertIs(caught.exception, original)
        self.assertEqual(1, tn.close_count)

    def test_telnet_failed_open_closes_socket_and_preserves_non_auth_error(self):
        from core.exceptions import ConnectionError
        from handlers.biamp import tesira_forte_ci as biamp

        class CountingTelnet:
            def __init__(self):
                self.close_count = 0

            def close(self):
                self.close_count += 1

        tn = CountingTelnet()
        original = ConnectionError("Biamp Telnet login did not reach readiness.")
        with patch("telnetlib.Telnet", return_value=tn), patch.object(
            biamp, "_telnet_write_login", side_effect=original
        ):
            with self.assertRaises(ConnectionError) as caught:
                biamp._TelnetBiampSession.open(
                    "192.0.2.10",
                    23,
                    "synthetic-user",
                    "synthetic-password",
                    1.0,
                )

        self.assertIs(caught.exception, original)
        self.assertEqual(1, tn.close_count)

    def test_successful_telnet_open_stays_open_until_session_close(self):
        from handlers.biamp import tesira_forte_ci as biamp

        class CountingTelnet:
            def __init__(self):
                self.close_count = 0

            def close(self):
                self.close_count += 1

        tn = CountingTelnet()
        with patch("telnetlib.Telnet", return_value=tn), patch.object(
            biamp, "_telnet_write_login", return_value=None
        ):
            session = biamp._TelnetBiampSession.open(
                "192.0.2.10",
                23,
                "synthetic-user",
                "synthetic-password",
                1.0,
            )

        self.assertEqual(0, tn.close_count)
        session.close()
        self.assertEqual(1, tn.close_count)

    def test_telnet_delayed_repeated_prompt_inside_timeout_is_rejection(self):
        from core.exceptions import AuthenticationError
        from handlers.biamp import tesira_forte_ci as biamp

        class DelayedRejectedTelnet:
            def __init__(self):
                self.reads = [b"login:", b"Password:"]
                self.followups = [b"", b"login:"]

            def read_until(self, _marker, _timeout):
                return self.reads.pop(0)

            def write(self, _data):
                pass

            def read_very_eager(self):
                return self.followups.pop(0)

        with patch.object(biamp.time, "monotonic", side_effect=[0.0, 0.0, 0.6]), \
                patch.object(biamp.time, "sleep", return_value=None):
            with self.assertRaises(AuthenticationError):
                biamp._telnet_write_login(
                    DelayedRejectedTelnet(),
                    "synthetic-user",
                    "synthetic-password",
                    1.0,
                )

    def test_telnet_prompt_after_timeout_is_not_current_rejection(self):
        from core.exceptions import ConnectionError
        from handlers.biamp import tesira_forte_ci as biamp

        class PromptAfterTimeoutTelnet:
            def __init__(self):
                self.reads = [b"login:", b"Password:"]
                self.followups = [b"", b"login:"]
                self.followup_reads = 0

            def read_until(self, _marker, _timeout):
                return self.reads.pop(0)

            def write(self, _data):
                pass

            def read_very_eager(self):
                self.followup_reads += 1
                return self.followups.pop(0)

        tn = PromptAfterTimeoutTelnet()
        with patch.object(biamp.time, "monotonic", side_effect=[0.0, 0.0, 1.01]), \
                patch.object(biamp.time, "sleep", return_value=None):
            with self.assertRaises(ConnectionError):
                biamp._telnet_write_login(
                    tn,
                    "synthetic-user",
                    "synthetic-password",
                    1.0,
                )

        self.assertEqual(1, tn.followup_reads)

    def test_telnet_explicit_readiness_finishes_before_full_timeout(self):
        from handlers.biamp import tesira_forte_ci as biamp

        class ReadyTelnet:
            def __init__(self):
                self.reads = [b"login:", b"Password:"]
                self.followups = [b"\r\nWelcome to the Tesira Text Protocol Server\r\n"]

            def read_until(self, _marker, _timeout):
                return self.reads.pop(0)

            def write(self, _data):
                pass

            def read_very_eager(self):
                return self.followups.pop(0)

        with patch.object(biamp.time, "monotonic", side_effect=[0.0, 0.0]):
            biamp._telnet_write_login(
                ReadyTelnet(),
                "synthetic-user",
                "synthetic-password",
                5.0,
            )

    def test_telnet_readiness_marker_is_exact_and_case_insensitive(self):
        from core.exceptions import ConnectionError
        from handlers.biamp import tesira_forte_ci as biamp

        class ReadyTelnet:
            def __init__(self, followup):
                self.reads = [b"LoGiN:", b"Password:"]
                self.followups = [followup]

            def read_until(self, _marker, _timeout):
                return self.reads.pop(0)

            def write(self, _data):
                pass

            def read_very_eager(self):
                return self.followups.pop(0)

        for followup in (
            b"WELCOME TO THE TESIRA TEXT PROTOCOL\r\n",
            b" welcome to the tesira text protocol server \r\n",
        ):
            with self.subTest(followup=followup):
                with patch.object(biamp.time, "monotonic", side_effect=[0.0, 0.0]):
                    biamp._telnet_write_login(
                        ReadyTelnet(followup),
                        "synthetic-user",
                        "synthetic-password",
                        5.0,
                    )

        for followup in (
            b"Welcome operator\r\n",
            b"Welcome to the Tesira Text Protocol Server extra\r\n",
            b"Tesira\r\n",
            b"+OK\r\n",
        ):
            with self.subTest(followup=followup):
                with patch.object(biamp.time, "monotonic", side_effect=[0.0, 0.0, 5.1]), \
                        patch.object(biamp.time, "sleep", return_value=None):
                    with self.assertRaises(ConnectionError):
                        biamp._telnet_write_login(
                            ReadyTelnet(followup),
                            "synthetic-user",
                            "synthetic-password",
                            5.0,
                        )

    def test_telnet_split_readiness_banner_is_accepted_after_join(self):
        from handlers.biamp import tesira_forte_ci as biamp

        class SplitReadyTelnet:
            def __init__(self):
                self.reads = [b"login:", b"Password:"]
                self.followups = [
                    b"Welcome to the Tes",
                    b"ira Text Protocol Server\r\n",
                ]

            def read_until(self, _marker, _timeout):
                return self.reads.pop(0)

            def write(self, _data):
                pass

            def read_very_eager(self):
                return self.followups.pop(0)

        with patch.object(biamp.time, "monotonic", side_effect=[0.0, 0.0, 0.1]), \
                patch.object(biamp.time, "sleep", return_value=None):
            biamp._telnet_write_login(
                SplitReadyTelnet(),
                "synthetic-user",
                "synthetic-password",
                5.0,
            )


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
