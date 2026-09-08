import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication


class _Signals(QObject):
    result = pyqtSignal(dict)
    error = pyqtSignal(dict)
    dropped = pyqtSignal(dict)


class _Session:
    def __init__(self, *_args, **_kwargs):
        self.signals = _Signals()
        self.generation = 0
        self.activations = []
        self.submits = []
        self.invalidations = 0

    def activate_context(self, *args, **kwargs):
        self.generation += 1
        self.activations.append((args, kwargs))
        return self.generation

    def invalidate_context(self):
        self.invalidations += 1
        self.generation += 1
        return self.generation

    def submit(self, operation, *, generation):
        self.submits.append((operation, generation))
        return len(self.submits)

    def shutdown(self, **_kwargs):
        pass


class CloudLinkMeterCompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from gui.main_window import VCSDiagnosticApp
        self.window = VCSDiagnosticApp()
        self.window.screens["codec"] = object()
        self.window.device_credentials["CloudLink Bar 310"] = [{"username": "u", "password": "p"}]

    def tearDown(self):
        self.window.close(); self.window.deleteLater(); self.app.processEvents()

    def _accept(self, model="CloudLink Bar 310", ip="192.0.2.10", request_id=1):
        self.window._active_request = {"id": request_id, "device": model, "ip": ip,
                                       "screen": self.window.screens["codec"]}
        return SimpleNamespace(device_name=model, ip_address=ip)

    def test_lazy_supported_start_and_unsupported_never_create_session(self):
        self.assertIsNone(self.window.cloudlink_meter_session)
        with patch("gui.main_window.InteractiveSessionController", _Session):
            self.window._start_cloudlink_microphone_meter_for_accepted_codec(
                self._accept("Huawei TE40"))
            self.assertIsNone(self.window.cloudlink_meter_session)
            self.window._start_cloudlink_microphone_meter_for_accepted_codec(self._accept())
        self.assertEqual(1, len(self.window.cloudlink_meter_session.activations))
        self.assertEqual(1, len(self.window.cloudlink_meter_session.submits))

    def test_repeat_refresh_replaces_generation_and_credential_change_invalidates(self):
        with patch("gui.main_window.InteractiveSessionController", _Session):
            self.window._start_cloudlink_microphone_meter_for_accepted_codec(self._accept(request_id=1))
            first = self.window.cloudlink_microphone_meter._generation
            self.window._start_cloudlink_microphone_meter_for_accepted_codec(self._accept(request_id=2))
            second = self.window.cloudlink_microphone_meter._generation
            self.assertNotEqual(first, second)
            self.assertEqual(2, len(self.window.cloudlink_meter_session.submits))
            candidates = self.window.device_credentials["CloudLink Bar 310"]
            candidates[0]["password"] = "changed"
            self.window._on_credential_configuration_changed("CloudLink Bar 310", "192.0.2.10")
        self.assertFalse(self.window.cloudlink_microphone_meter._active)
        self.assertGreaterEqual(self.window.cloudlink_meter_session.invalidations, 2)

    def test_model_and_ip_supersession_stop_meter_before_late_callback(self):
        class Screen:
            def __init__(self): self.samples = []
            def apply_microphone_meter_presentation(self, sample): self.samples.append(sample)

        screen = Screen()
        self.window.screens["codec"] = screen
        with patch("gui.main_window.InteractiveSessionController", _Session):
            self.window._start_cloudlink_microphone_meter_for_accepted_codec(self._accept())
        session = self.window.cloudlink_meter_session
        generation = self.window.cloudlink_microphone_meter._generation

        # This is the production composition boundary invoked by both the IP
        # text-change signal and model selection path.
        self.window._supersede_model_actions("ip_changed")
        self.assertFalse(self.window.cloudlink_microphone_meter._active)
        self.assertGreater(session.generation, generation)
        session.signals.result.emit({"kind": "cloudlink_microphone_meter", "generation": generation,
                                     "client_token": 1, "value": {"available": True, "raw_level": 9, "fraction": .45}})
        self.assertEqual([], screen.samples)

        self.window._start_cloudlink_microphone_meter_for_accepted_codec(self._accept(request_id=2))
        self.window._supersede_model_actions("model_changed")
        self.assertFalse(self.window.cloudlink_microphone_meter._active)

    def test_terminal_meter_failure_invalidates_codec_session_without_erasing_status(self):
        class Screen:
            def __init__(self): self.samples = []
            def apply_microphone_meter_presentation(self, sample): self.samples.append(sample)

        screen = Screen()
        self.window.screens["codec"] = screen
        with patch("gui.main_window.InteractiveSessionController", _Session):
            self.window._start_cloudlink_microphone_meter_for_accepted_codec(self._accept())
        session = self.window.cloudlink_meter_session
        generation = self.window.cloudlink_microphone_meter._generation
        session.signals.error.emit({"kind": "cloudlink_microphone_meter", "generation": generation,
                                    "client_token": 1, "category": "session_invalid"})
        self.assertFalse(self.window.cloudlink_microphone_meter._active)
        self.assertGreaterEqual(session.invalidations, 2)
        self.assertEqual([False], [sample["available"] for sample in screen.samples])

    def test_composition_rejects_stale_meter_presentation_and_accepts_current_one(self):
        class Screen:
            def __init__(self): self.samples = []
            def apply_microphone_meter_presentation(self, sample): self.samples.append(sample)

        screen = Screen()
        session = _Session(); session.generation = 8
        self.window.screens["codec"] = screen
        self.window.cloudlink_meter_session = session
        self.window._active_request = {"id": 4, "device": "CloudLink Bar 310",
                                       "ip": "192.0.2.10", "screen": screen}
        self.window._render_cloudlink_microphone_meter({"available": True, "fraction": .2,
                                                        "_meter_token": 3, "_meter_generation": 7})
        self.assertEqual([], screen.samples)
        self.window._render_cloudlink_microphone_meter({"available": True, "fraction": .5,
                                                        "_meter_token": 4, "_meter_generation": 8})
        self.assertEqual([.5], [sample["fraction"] for sample in screen.samples])


class CodecScreenMeterRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from gui.main_window import VCSDiagnosticApp
        self.window = VCSDiagnosticApp()
        self.screen = self.window.screens["codec"]

    def tearDown(self):
        self.window.close(); self.window.deleteLater(); self.app.processEvents()

    def _rebuild(self, model):
        self.window._accept_test_diagnostic_model(model)
        self.screen.update_parameters_display()

    def test_supported_rows_are_ordered_render_zero_and_rebuild_without_duplicates(self):
        for model in ("CloudLink Bar 310", "CloudLink Box 310"):
            with self.subTest(model=model):
                self._rebuild(model)
                names = list(self.screen.parameter_rows)
                expected = (
                    ["Статус микрофона", "Уровень микрофонов", "Журнал звонков"]
                    if model == "CloudLink Bar 310"
                    else ["Статус микрофона", "Журнал звонков"]
                )
                self.assertEqual(expected, names[names.index("Статус микрофона"):names.index("Журнал звонков") + 1])
                if model == "CloudLink Box 310":
                    self.assertIsNone(self.screen.microphone_meter_bar)
                    continue
                first = self.screen.microphone_meter_bar
                self.assertFalse(first.isTextVisible())
                self.screen.apply_microphone_meter_presentation({"available": True, "raw_level": 0, "fraction": 0.0})
                self.assertEqual("available", first.property("meterState"))
                self.assertEqual(0, first.value())
                self.screen.apply_microphone_meter_presentation({"available": False, "raw_level": None, "fraction": None})
                self.assertEqual("unavailable", first.property("meterState"))
                self.assertEqual(0, first.value())
                self._rebuild(model)
                self.assertIsNot(first, self.screen.microphone_meter_bar)
                self.assertEqual(1, list(self.screen.parameter_rows).count("Уровень микрофонов"))

    def test_cloudlink_runtime_rows_are_visible_without_gain_controls(self):
        self._rebuild("CloudLink Bar 310")
        for name in ("Режим сна", "Версия камеры", "Версия микрофона"):
            self.assertIn(name, self.screen.parameter_rows)
        self.assertNotIn("Громкость микрофона", self.screen.parameter_rows)

    def test_unsupported_rebuild_clears_meter_reference_and_cannot_be_resurrected(self):
        self._rebuild("CloudLink Bar 310")
        old = self.screen.microphone_meter_bar
        self._rebuild("Huawei TE40")
        self.assertIsNone(self.screen.microphone_meter_bar)
        self.assertNotIn("Уровень микрофонов", self.screen.parameter_rows)
        self.screen.apply_microphone_meter_presentation({"available": True, "fraction": 1.0})
        self.assertIsNone(self.screen.microphone_meter_bar)
        self.assertIsNotNone(old)

    def test_theme_defines_distinct_available_and_unavailable_meter_selectors(self):
        from gui.theme import build_stylesheet
        stylesheet = build_stylesheet()
        self.assertIn('QProgressBar[meterState="available"]', stylesheet)
        self.assertIn('QProgressBar[meterState="available"]::chunk', stylesheet)
        self.assertIn('QProgressBar[meterState="unavailable"]', stylesheet)
        self.assertIn('QProgressBar[meterState="unavailable"]::chunk', stylesheet)
