import unittest
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QLabel, QProgressBar, QPushButton, QWidget

from core.room_diagnostic_tree import (
    DeviceRowState, DeviceRowStatus, RoomDiagnosticSession,
    RoomDiagnosticSessionIdentity, RoomCycleStatus, RoomModelCapability,
)
from core.room_interaction import RoomInteractionBindings, RoomInteractionCoordinator
from core.codec_call_history import CallRecord, snapshot_from_records
from gui.diagnostic_dispatch import dispatch_entry_for_model, normalize_codec_audio_projection
from gui.room_diagnostic_tree import RoomReadOnlyPresentation


MODELS = (
    "Huawei TE20", "Huawei TE40", "CloudLink Bar 310",
    "CloudLink Box 310", "Polycom RPG 310",
)


class ModernCodecDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _row(self, model="Huawei TE40", snapshot=None):
        return DeviceRowState(
            "codec-1", model, "192.0.2.10", model, DeviceRowStatus.CONNECTED,
            capability=RoomModelCapability(model, "codec", "route", "adapter"),
            accepted_snapshot=snapshot or {},
        )

    def test_exact_registry_control_matrix_is_complete_and_fail_closed(self):
        expected = {
            "Huawei TE20": (True, True, False, True, False),
            "Huawei TE40": (True, True, False, True, False),
            "CloudLink Bar 310": (True, True, False, False, False),
            "CloudLink Box 310": (True, True, False, False, False),
            "Polycom RPG 310": (True, True, False, True, False),
        }
        for model, capabilities in expected.items():
            controls = dispatch_entry_for_model(model).codec_controls
            self.assertIsNotNone(controls)
            self.assertEqual(capabilities, tuple(
                controls.supported(operation) for operation in (
                    "speaker_adjust", "speaker_mute", "microphone_adjust",
                    "microphone_mute", "reboot",
                )
            ))
            controls.validate(model)

    def test_dashboard_has_fixed_cards_rows_without_status_dots(self):
        presentation = RoomReadOnlyPresentation(self._row())
        self.addCleanup(presentation.deleteLater)
        dashboard = presentation.findChild(QWidget, "roomCodecDashboard")
        self.assertIsNotNone(dashboard)
        self.assertEqual(
            ["roomCodecStateCard", "roomCodecCallCard", "roomCodecAudioCard", "roomCodecHistoryCard", "roomCodecActionsCard"],
            [child.objectName() for child in dashboard.findChildren(QWidget, options=Qt.FindDirectChildrenOnly)],
        )
        text = "\n".join(label.text() for label in presentation.findChildren(QLabel))
        for required in ("Модель", "MAC-адрес", "Серийный номер", "Платформа", "Версия ПО", "Микрофон", "Камера", "Статус звонка", "Презентация", "Регистрация SIP/H.323", "Нет данных"):
            self.assertIn(required, text)
        dots = presentation.findChildren(QLabel, "roomCodecStatusDot")
        self.assertEqual([], dots)

    def test_call_fields_use_yes_no_and_registration_uses_semantic_icon(self):
        presentation = RoomReadOnlyPresentation(self._row(snapshot={
            "call_status": "Нет активного звонка",
            "presentation_status": "Активна",
            "sip_registration": "Зарегистрирован",
        }))
        self.addCleanup(presentation.deleteLater)
        values = [label.text() for label in presentation.findChildren(QLabel, "roomCodecFieldValue")]
        self.assertIn("Нет", values)
        self.assertIn("Да", values)
        registration = presentation.findChild(QLabel, "roomCodecRegistrationValue")
        self.assertIsNotNone(registration)
        self.assertEqual("✓", registration.text())
        self.assertEqual("positive", registration.property("semantic"))
        self.assertEqual(Qt.AlignRight | Qt.AlignVCenter, registration.alignment())

    def test_light_theme_keeps_codec_card_order_and_geometry(self):
        from gui.theme import apply_theme

        presentation = RoomReadOnlyPresentation(self._row())
        self.addCleanup(presentation.deleteLater)
        presentation.resize(1440, 900)
        presentation.show()
        apply_theme(presentation, "dark")
        self.app.processEvents()
        dashboard = presentation.findChild(QWidget, "roomCodecDashboard")
        before = tuple(child.geometry() for child in dashboard.findChildren(
            QWidget, options=Qt.FindDirectChildrenOnly,
        ))
        try:
            apply_theme(presentation, "light")
            self.app.processEvents()
            self.assertEqual(before, tuple(child.geometry() for child in dashboard.findChildren(
                QWidget, options=Qt.FindDirectChildrenOnly,
            )))
        finally:
            apply_theme(self.app, "dark")

    def test_audio_projection_never_parses_display_mute_strings(self):
        projection = normalize_codec_audio_projection({
            "speaker_volume": 7,
            "mic_mute": "Muted",
            "speaker_mute": "Unmuted",
        })
        self.assertEqual(7, projection.speaker_volume)
        self.assertEqual("UNKNOWN", projection.microphone_mute_state.value)
        self.assertEqual("UNKNOWN", projection.speaker_mute_state.value)

    def test_microphone_meter_uses_only_finite_accepted_live_evidence(self):
        presentation = RoomReadOnlyPresentation(self._row(snapshot={
            "live_microphone": {"available": True, "normalized": 0.62},
        }))
        self.addCleanup(presentation.deleteLater)
        meter = presentation.findChild(QProgressBar, "roomCodecMicrophoneMeter")
        self.assertIsNotNone(meter)
        self.assertEqual(62, meter.value())
        self.assertEqual("available", meter.property("meterState"))

    def test_audio_has_two_meters_and_volume_controls_show_percentages(self):
        presentation = RoomReadOnlyPresentation(self._row(snapshot={
            "live_microphone": {"available": True, "normalized": 0.62},
            "speaker_volume": 12,
            "microphone_volume": 62,
        }))
        self.addCleanup(presentation.deleteLater)
        meters = presentation.findChildren(QProgressBar)
        self.assertEqual(2, len(meters))
        speaker = presentation.findChild(QProgressBar, "roomCodecSpeakerMeter")
        self.assertIsNotNone(speaker)
        self.assertEqual(57, speaker.value())
        values = [label.text() for label in presentation.findChildren(QLabel, "roomCodecAudioValue")]
        self.assertEqual(["62%", "57%"], values)

    def test_call_log_uses_direction_icons_from_typed_records(self):
        now = datetime(2026, 9, 2, 10, 0)
        row = self._row()
        row.call_log_snapshot = snapshot_from_records((
            CallRecord("out", now, 60, room_number="123456789", start_display="02.09.2026 10:00", direction="outgoing"),
            CallRecord("in", now, 60, room_number="987654321", start_display="02.09.2026 09:00", direction="incoming"),
        ), reference_now=now, source_ended=True)
        presentation = RoomReadOnlyPresentation(row)
        self.addCleanup(presentation.deleteLater)
        icons = presentation.findChildren(QLabel, "roomCodecCallDirectionIcon")
        self.assertEqual(["↗", "↙"], [icon.text() for icon in icons])
        self.assertEqual(["outgoing", "incoming"], [icon.property("direction") for icon in icons])
        timestamps = presentation.findChildren(QLabel, "roomCodecCallTimestamp")
        self.assertTrue(all(label.minimumWidth() == 112 for label in timestamps))
        expand = presentation.findChild(QPushButton, "roomCallLogButton")
        self.assertEqual(91, expand.minimumWidth())
        header_layout = expand.parentWidget().layout()
        self.assertIs(expand, header_layout.itemAt(header_layout.count() - 1).widget())

    def test_cloudlink_microphone_buttons_publish_only_local_unsupported_intent(self):
        intents = []
        presentation = RoomReadOnlyPresentation(
            self._row("CloudLink Bar 310", {"speaker_volume": 6}),
            request_codec_control=lambda operation, value: intents.append((operation, value)),
        )
        self.addCleanup(presentation.deleteLater)
        buttons = presentation.findChildren(QPushButton, "roomCodecAudioPlus")
        self.assertEqual(2, len(buttons))
        buttons[0].click()
        self.assertEqual([("microphone_adjust", 1)], intents)

    def test_preview_is_one_shot_per_real_expansion_epoch(self):
        row = self._row()
        session = RoomDiagnosticSession(
            RoomDiagnosticSessionIdentity("snapshot", 1, None, None, "R-1"),
            "R-1", None, None, [row], status=RoomCycleStatus.COMPLETE,
        )
        requests = []
        coordinator = RoomInteractionCoordinator(
            bindings_for_model=lambda _model: RoomInteractionBindings(
                auxiliary=lambda _context, action: requests.append(action),
            ),
        )
        coordinator.bind_session(session)
        coordinator.expand(row.record_id)
        coordinator.request_codec_preview()
        self.assertEqual(["call_log_preview"], requests)
        coordinator.complete(coordinator.active_context, success=False, warning="Нет данных")
        coordinator.expand(row.record_id)
        coordinator.request_codec_preview()
        self.assertEqual(["call_log_preview"], requests)
        coordinator.collapse(row.record_id)
        coordinator.expand(row.record_id)
        coordinator.request_codec_preview()
        self.assertEqual(["call_log_preview", "call_log_preview"], requests)


if __name__ == "__main__":
    unittest.main()
