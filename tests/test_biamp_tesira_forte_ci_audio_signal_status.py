from __future__ import annotations

from dataclasses import dataclass
import ast
import os
from pathlib import Path
import unittest

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
