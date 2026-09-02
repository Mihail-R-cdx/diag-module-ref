import unittest
from datetime import datetime
from types import SimpleNamespace

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QLabel, QProgressBar, QPushButton, QWidget

from core.room_diagnostic_tree import (
    DeviceRowState, DeviceRowStatus, RoomDiagnosticSession,
    RoomDiagnosticSessionIdentity, RoomCycleStatus, RoomModelCapability,
)
from core.room_interaction import RoomInteractionBindings, RoomInteractionCoordinator
from core.codec_call_history import CallRecord, snapshot_from_records
from gui.diagnostic_dispatch import (
    CodecMuteState,
    dispatch_entry_for_model,
    normalize_codec_audio_projection,
    normalize_codec_call_projection,
)
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
            "_room_codec_call_active": False,
            "_room_codec_presentation_active": True,
            "_room_codec_registration_active": True,
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

    def test_shared_projections_reject_display_string_authority_for_every_model(self):
        raw = {
            "speaker_volume": 7,
            "mic_mute": "Muted",
            "speaker_mute": "Unmuted",
            "call_status": "active",
            "presentation_status": "активен",
            "sip_registration": "registered",
        }
        for model in MODELS:
            with self.subTest(model=model):
                audio = normalize_codec_audio_projection(raw, model)
                call = normalize_codec_call_projection(raw, model)
                self.assertEqual(7, audio.speaker_volume)
                self.assertIs(CodecMuteState.UNKNOWN, audio.microphone_mute_state)
                self.assertIs(CodecMuteState.UNKNOWN, audio.speaker_mute_state)
                self.assertIsNone(call.call_active)
                self.assertIsNone(call.presentation_active)
                self.assertIsNone(call.registration_active)

    def test_exact_parser_boundaries_publish_canonical_codec_authority(self):
        from core.parser import (
            HuaweiBar310DataParser,
            HuaweiTE20DataParser,
            HuaweiTE40DataParser,
            PolycomDataParser,
        )

        cases = (
            ("Huawei TE20", HuaweiTE20DataParser.parse_raw_data, {
                "call_status": "Calling", "presentation_local": "Start",
                "sip_status": "On", "mic_mute": "Muted", "speaker_volume": 7,
            }),
            ("Huawei TE40", HuaweiTE40DataParser.parse_raw_data, {
                "call_status": "Connected", "presentation": "auxOpen",
                "sip_status": "SIP_STATE_OK", "mic_mute": "Unmuted", "speaker_volume": 7,
            }),
            ("CloudLink Bar 310", HuaweiBar310DataParser.parse_raw_data, {
                "model": "Huawei CloudLink Bar 310", "version": "V1", "call_status": "Connected",
                "presentation": "Start", "sip_status": "On", "speaker_volume": 7,
            }),
            ("CloudLink Box 310", lambda raw: HuaweiBar310DataParser.parse_raw_data(raw, "Huawei CloudLink Box 310"), {
                "model": "Huawei CloudLink Box 310", "version": "V1", "call_status": "No Call",
                "presentation": "Stop", "sip_status": "Off", "speaker_volume": 0,
            }),
            ("Polycom RPG 310", PolycomDataParser.parse_raw_data, {
                "call_status": "Active", "presentation": "Started", "sip_status": "online",
                "mic_mute": "on", "speaker_volume": 7,
            }),
        )
        for model, parser, raw in cases:
            with self.subTest(model=model):
                snapshot = parser(raw)
                audio = normalize_codec_audio_projection(snapshot, model)
                call = normalize_codec_call_projection(snapshot, model)
                self.assertIsNotNone(call.call_active)
                self.assertIsNotNone(call.presentation_active)
                self.assertIsNotNone(call.registration_active)
                self.assertIsNot(CodecMuteState.UNKNOWN, audio.speaker_mute_state)
                if model in {"Huawei TE20", "Huawei TE40", "Polycom RPG 310"}:
                    self.assertIsNot(CodecMuteState.UNKNOWN, audio.microphone_mute_state)

    def test_exact_parser_boundaries_fail_closed_for_malformed_vendor_text(self):
        from core.parser import HuaweiTE40DataParser, PolycomDataParser

        huawei = HuaweiTE40DataParser.parse_raw_data({
            "call_status": "not active despite the word active",
            "presentation": "almost Start", "sip_status": "registered-ish",
            "mic_mute": "Muted later", "speaker_volume": "0",
        })
        polycom = PolycomDataParser.parse_raw_data({
            "call_status": "Active-ish", "presentation": "Stopped?",
            "sip_status": "online-now", "mic_mute": "onward", "speaker_volume": "0",
        })
        for model, snapshot in (("Huawei TE40", huawei), ("Polycom RPG 310", polycom)):
            with self.subTest(model=model):
                audio = normalize_codec_audio_projection(snapshot, model)
                call = normalize_codec_call_projection(snapshot, model)
                self.assertIs(CodecMuteState.UNKNOWN, audio.microphone_mute_state)
                self.assertIsNone(audio.speaker_volume)
                self.assertIs(CodecMuteState.UNKNOWN, audio.speaker_mute_state)
                self.assertIsNone(call.call_active)
                self.assertIsNone(call.presentation_active)
                self.assertIsNone(call.registration_active)

    def test_raw_display_mute_cannot_build_a_room_mutation_target(self):
        from gui.main_window import VCSDiagnosticApp

        session = SimpleNamespace(identity="generation-1")
        row = self._row(snapshot={"mic_mute": "Muted"})
        controls = dispatch_entry_for_model("Huawei TE40").codec_controls
        window = SimpleNamespace(_room_codec_restore_volumes={})
        command = VCSDiagnosticApp._codec_command_from_current_evidence(
            window, session, row, controls, "microphone_mute", "toggle",
        )
        self.assertIsNone(command)

        row.accepted_snapshot = {"microphone_muted": True}
        command = VCSDiagnosticApp._codec_command_from_current_evidence(
            window, session, row, controls, "microphone_mute", "toggle",
        )
        self.assertEqual({"operation": "microphone_mute", "target": False}, command)

    def test_microphone_meter_uses_only_finite_accepted_live_evidence(self):
        presentation = RoomReadOnlyPresentation(self._row(snapshot={
            "live_microphone": {"available": True, "normalized": 0.62},
        }))
        self.addCleanup(presentation.deleteLater)
        meter = presentation.findChild(QProgressBar, "roomCodecMicrophoneMeter")
        self.assertIsNotNone(meter)
        self.assertEqual(62, meter.value())
        self.assertEqual("available", meter.property("meterState"))
        self.assertEqual(
            "62%",
            presentation.findChildren(QLabel, "roomCodecAudioValue")[0].text(),
        )

    def test_call_card_icon_uses_compact_codec_specific_size(self):
        from gui.theme import apply_theme

        presentation = RoomReadOnlyPresentation(self._row())
        self.addCleanup(presentation.deleteLater)
        apply_theme(presentation, "dark")
        self.app.processEvents()
        call_card = presentation.findChild(QWidget, "roomCodecCallCard")
        icon = call_card.findChild(QLabel, "sectionCardIcon")
        self.assertEqual("☎", icon.text())
        self.assertEqual(20, icon.minimumWidth())
        self.assertEqual(20, icon.maximumWidth())
        self.assertEqual(20, icon.minimumHeight())

    def test_multiline_firmware_value_has_a_dedicated_expanded_row(self):
        presentation = RoomReadOnlyPresentation(self._row(snapshot={
            "firmware": "V600R019C00SPC700\nBuild 2026.09.02",
        }))
        self.addCleanup(presentation.deleteLater)
        firmware_row = presentation.findChild(QWidget, "roomCodecFirmwareRow")
        self.assertIsNotNone(firmware_row)
        self.assertGreaterEqual(firmware_row.minimumHeight(), 48)
        value = firmware_row.findChild(QLabel, "roomCodecFieldValue")
        self.assertEqual("V600R019C00SPC700\nBuild 2026.09.02", value.text())
        self.assertTrue(value.wordWrap())

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
