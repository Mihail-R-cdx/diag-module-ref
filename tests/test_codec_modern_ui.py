import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QLabel, QProgressBar, QPushButton, QWidget

from core.room_diagnostic_tree import (
    DeviceRowState, DeviceRowStatus, RoomDiagnosticSession,
    RoomDiagnosticSessionIdentity, RoomCycleStatus, RoomModelCapability,
)
from core.room_interaction import RoomInteractionBindings, RoomInteractionCoordinator
from core.codec_call_history import CallDirection, CallRecord, snapshot_from_records
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

    def test_exact_registry_is_the_speaker_range_authority(self):
        expected = {
            "Huawei TE20": (0, 21), "Huawei TE40": (0, 21),
            "CloudLink Bar 310": (0, 15), "CloudLink Box 310": (0, 15),
            "Polycom RPG 310": (0, 100),
        }
        for model, bounds in expected.items():
            with self.subTest(model=model):
                controls = dispatch_entry_for_model(model).codec_controls
                self.assertEqual(bounds, (controls.speaker_minimum, controls.speaker_maximum))
        self.assertEqual(2, dispatch_entry_for_model("Polycom RPG 310").codec_controls.speaker_step)

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
        for required in ("Модель", "MAC-адрес", "Серийный номер", "Версия ПО", "Микрофон", "Камера", "Статус звонка", "Презентация", "Регистрация SIP/H.323", "Нет данных"):
            self.assertIn(required, text)
        self.assertNotIn("Платформа", text)
        dots = presentation.findChildren(QLabel, "roomCodecStatusDot")
        self.assertEqual([], dots)
        self.assertIsNone(presentation.findChild(QPushButton, "roomLocalDebugButton"))

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
                "presentation": "Start", "sip_status": "On", "speaker_volume": 7, "mic_volume": 41,
            }),
            ("CloudLink Box 310", lambda raw: HuaweiBar310DataParser.parse_raw_data(raw, "Huawei CloudLink Box 310"), {
                "model": "Huawei CloudLink Box 310", "version": "V1", "call_status": "No Call",
                "presentation": "Stop", "sip_status": "Off", "speaker_volume": 0, "mic_volume": 9,
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
                if model in {"CloudLink Bar 310", "CloudLink Box 310"}:
                    self.assertIsNotNone(audio.microphone_volume)

    def test_cloudlink_transport_parser_to_accepted_snapshot_to_dashboard_normalizes_mic_volume(self):
        """Regression starts with the transport-shaped compatibility field, not a snapshot stub."""
        from core.parser import HuaweiBar310DataParser

        transport_payload = {
            "model": "Huawei CloudLink Box 310", "version": "V1",
            "call_status": "No Call", "presentation": "Stop", "sip_status": "Off",
            "mic_volume": 9, "speaker_volume": 7,
        }
        parsed = HuaweiBar310DataParser.parse_raw_data(
            transport_payload, "Huawei CloudLink Box 310",
        )
        row = self._row("CloudLink Box 310", parsed)
        session = RoomDiagnosticSession(
            RoomDiagnosticSessionIdentity("snapshot", 1, None, None, "R-1"),
            "R-1", None, None, [row], status=RoomCycleStatus.COMPLETE,
        )
        self.assertIs(row.accepted_snapshot, parsed)
        presentation = RoomReadOnlyPresentation(session.row_for(row.record_id))
        self.addCleanup(presentation.deleteLater)
        self.assertEqual("9%", presentation.findChildren(QLabel, "roomCodecAudioValue")[0].text())

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

    def test_speaker_targets_use_current_accepted_authority_and_scoped_restore(self):
        from gui.main_window import VCSDiagnosticApp

        session = SimpleNamespace(identity="generation-1")
        controls = dispatch_entry_for_model("Huawei TE40").codec_controls
        window = SimpleNamespace(_room_codec_restore_volumes={})
        row = self._row(snapshot={"speaker_volume": 20})
        self.assertEqual(
            {"operation": "speaker_volume", "target": 21},
            VCSDiagnosticApp._codec_command_from_current_evidence(
                window, session, row, controls, "speaker_adjust", 1,
            ),
        )
        self.assertEqual(
            {"operation": "speaker_volume", "target": 0},
            VCSDiagnosticApp._codec_command_from_current_evidence(
                window, session, row, controls, "speaker_mute", "toggle",
            ),
        )
        row.accepted_snapshot = {"speaker_volume": 0}
        self.assertEqual(
            {"operation": "speaker_volume", "target": 20},
            VCSDiagnosticApp._codec_command_from_current_evidence(
                window, session, row, controls, "speaker_mute", "toggle",
            ),
        )
        fresh_window = SimpleNamespace(_room_codec_restore_volumes={})
        self.assertIsNone(VCSDiagnosticApp._codec_command_from_current_evidence(
            fresh_window, session, row, controls, "speaker_mute", "toggle",
        ))
        self.assertIsNone(VCSDiagnosticApp._codec_command_from_current_evidence(
            fresh_window, session, self._row(snapshot={}), controls, "speaker_adjust", 1,
        ))
        polycom_controls = dispatch_entry_for_model("Polycom RPG 310").codec_controls
        self.assertEqual(
            {"operation": "speaker_volume", "target": 22},
            VCSDiagnosticApp._codec_command_from_current_evidence(
                fresh_window, session, self._row("Polycom RPG 310", {"speaker_volume": 20}),
                polycom_controls, "speaker_adjust", 1,
            ),
        )

    def test_room_context_invalidation_clears_speaker_restore_authority(self):
        from gui.main_window import VCSDiagnosticApp

        window = SimpleNamespace(
            _room_codec_restore_volumes={("old-generation", "codec-1"): 20},
            _close_room_child_presentations=lambda: None,
        )
        VCSDiagnosticApp._clear_room_diagnostic_session(window)
        self.assertEqual({}, window._room_codec_restore_volumes)

    def test_microphone_meter_uses_only_finite_accepted_live_evidence(self):
        presentation = RoomReadOnlyPresentation(self._row("CloudLink Bar 310", {
            "live_microphone": {"available": True, "normalized": 0.62},
        }))
        self.addCleanup(presentation.deleteLater)
        meter = presentation.findChild(QProgressBar, "roomCodecMicrophoneMeter")
        self.assertIsNotNone(meter)
        self.assertEqual(62, meter.value())
        self.assertEqual("available", meter.property("meterState"))
        self.assertEqual(
            "Нет данных",
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
        self.assertLessEqual(firmware_row.maximumHeight(), 56)
        value = firmware_row.findChild(QLabel, "roomCodecFieldValue")
        self.assertEqual("V600R019C00SPC700\nBuild 2026.09.02", value.text())
        self.assertEqual(Qt.PlainText, value.textFormat())
        self.assertTrue(value.wordWrap())
        missing = RoomReadOnlyPresentation(self._row())
        self.addCleanup(missing.deleteLater)
        missing_row = missing.findChild(QWidget, "roomCodecFirmwareRow")
        self.assertEqual("Нет данных", missing_row.findChild(QLabel, "roomCodecFieldValue").text())

    def test_audio_has_no_speaker_meter_and_volume_controls_show_accepted_percentages(self):
        presentation = RoomReadOnlyPresentation(self._row("CloudLink Bar 310", {
            "live_microphone": {"available": True, "normalized": 0.62},
            "speaker_volume": 7,
            "microphone_volume": 41,
        }))
        self.addCleanup(presentation.deleteLater)
        meters = presentation.findChildren(QProgressBar)
        self.assertEqual(1, len(meters))
        self.assertIsNone(presentation.findChild(QProgressBar, "roomCodecSpeakerMeter"))
        values = [label.text() for label in presentation.findChildren(QLabel, "roomCodecAudioValue")]
        self.assertEqual(["41%", "47%"], values)

    def test_call_log_uses_direction_icons_from_typed_records(self):
        now = datetime(2026, 9, 2, 10, 0)
        row = self._row()
        row.call_log_preview_snapshot = snapshot_from_records((
            CallRecord("out", now, 60, room_number="123456789", start_display="02.09.2026 10:00", direction=CallDirection.OUTGOING),
            CallRecord("in", now, 60, room_number="987654321", start_display="02.09.2026 09:00", direction=CallDirection.INCOMING),
        ), reference_now=now, source_ended=True)
        presentation = RoomReadOnlyPresentation(row)
        self.addCleanup(presentation.deleteLater)
        icons = presentation.findChildren(QLabel, "roomCodecCallDirectionIcon")
        self.assertEqual(["↗", "↙"], [icon.text() for icon in icons])
        self.assertEqual(["outgoing", "incoming"], [icon.property("direction") for icon in icons])
        timestamps = presentation.findChildren(QLabel, "roomCodecCallTimestamp")
        self.assertTrue(all(label.minimumWidth() == 112 for label in timestamps))
        expand = presentation.findChild(QPushButton, "roomCallLogButton")
        self.assertGreaterEqual(expand.minimumHeight(), 34)

    def test_speaker_percentage_uses_registry_ranges_without_clamping(self):
        cases = (
            ("Huawei TE20", 0, 0), ("Huawei TE20", 10, 48), ("Huawei TE40", 21, 100),
            ("CloudLink Bar 310", 0, 0), ("CloudLink Box 310", 7, 47), ("CloudLink Box 310", 15, 100),
            ("Polycom RPG 310", 0, 0), ("Polycom RPG 310", 42, 42), ("Polycom RPG 310", 100, 100),
        )
        for model, volume, expected in cases:
            with self.subTest(model=model, volume=volume):
                self.assertEqual(expected, normalize_codec_audio_projection({"speaker_volume": volume}, model).speaker_volume_percent)
        self.assertIsNone(normalize_codec_audio_projection({"speaker_volume": 22}, "Huawei TE20").speaker_volume_percent)
        self.assertIsNone(normalize_codec_audio_projection({"speaker_volume": "7"}, "CloudLink Bar 310").speaker_volume_percent)

    def test_microphone_meter_capability_distinguishes_unsupported_and_missing_samples(self):
        for model in ("Huawei TE20", "Huawei TE40", "Polycom RPG 310"):
            with self.subTest(model=model):
                presentation = RoomReadOnlyPresentation(self._row(model, {"live_microphone": {"available": True, "normalized": 0}}))
                self.addCleanup(presentation.deleteLater)
                self.assertIsNone(presentation.findChild(QProgressBar, "roomCodecMicrophoneMeter"))
                self.assertEqual("Не поддерживается", presentation.findChild(QLabel, "roomCodecMicrophoneMeterState").text())
        for model in ("CloudLink Bar 310", "CloudLink Box 310"):
            with self.subTest(model=model):
                presentation = RoomReadOnlyPresentation(self._row(model, {"live_microphone": {"available": True, "normalized": 0}}))
                self.addCleanup(presentation.deleteLater)
                self.assertEqual(0, presentation.findChild(QProgressBar, "roomCodecMicrophoneMeter").value())

    def test_cloudlink_microphone_buttons_are_disabled_before_any_intent(self):
        intents = []
        presentation = RoomReadOnlyPresentation(
            self._row("CloudLink Bar 310", {"speaker_volume": 6}),
            request_codec_control=lambda operation, value: intents.append((operation, value)),
        )
        self.addCleanup(presentation.deleteLater)
        buttons = presentation.findChildren(QPushButton, "roomCodecAudioPlus")
        self.assertEqual(2, len(buttons))
        self.assertFalse(buttons[0].isEnabled())
        buttons[0].click()
        self.assertEqual([], intents)

    def test_unsupported_codec_affordances_stop_before_coordinator_admission(self):
        from gui.main_window import VCSDiagnosticApp

        coordinator = Mock()
        for model, operation in (
            *((model, "reboot") for model in MODELS),
            ("CloudLink Bar 310", "microphone_adjust"),
            ("CloudLink Box 310", "microphone_adjust"),
        ):
            with self.subTest(model=model, operation=operation):
                row = self._row(model)
                session = SimpleNamespace(
                    expanded_record_id=row.record_id,
                    row_for=lambda _record_id, current=row: current,
                )
                window = SimpleNamespace(
                    room_diagnostic_session=session,
                    room_interaction_coordinator=coordinator,
                )
                with patch("gui.main_window.QMessageBox.information") as information:
                    VCSDiagnosticApp._on_room_codec_control_requested(
                        window, row.record_id, operation, 1,
                    )
                information.assert_called_once()
        coordinator.confirm_mutation.assert_not_called()

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

    def test_current_preview_evidence_completes_epoch_without_network_owner(self):
        row = self._row()
        row.call_log_preview_snapshot = snapshot_from_records((), source_ended=True)
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
        self.assertEqual([], requests)
        self.assertIsNone(coordinator.active_context)

    def test_te_live_projection_keeps_microphone_and_speaker_evidence(self):
        presentation = RoomReadOnlyPresentation(self._row("Huawei TE20", {
            "live_audio": {"microphone": 11, "speaker": 22},
        }))
        self.addCleanup(presentation.deleteLater)
        self.assertEqual(
            ["11", "22"],
            [label.text() for label in presentation.findChildren(QLabel, "roomCodecLiveAudioValue")],
        )

    def test_confirmed_codec_readback_merges_only_the_targeted_field(self):
        row = self._row(snapshot={"speaker_volume": 5, "serial_number": "unchanged"})
        session = RoomDiagnosticSession(
            RoomDiagnosticSessionIdentity("snapshot", 1, None, None, "R-1"),
            "R-1", None, None, [row], expanded_record_id=row.record_id,
            status=RoomCycleStatus.COMPLETE,
        )
        reconciliations = []
        coordinator = RoomInteractionCoordinator(
            bindings_for_model=lambda _model: RoomInteractionBindings(
                mutation=lambda _context, _command: None,
                reconciliation=lambda _context, _data: reconciliations.append(True),
            ),
        )
        coordinator.bind_session(session)
        context = coordinator.confirm_mutation({"operation": "speaker_volume", "target": 7})
        coordinator.complete(context, success=True, data={
            "_room_codec_confirmed": {"speaker_volume": 7, "speaker_muted": False},
        })
        self.assertEqual([], reconciliations)
        self.assertEqual(7, row.accepted_snapshot["speaker_volume"])
        self.assertEqual("unchanged", row.accepted_snapshot["serial_number"])

    def test_reboot_is_disabled_for_every_codec_model(self):
        for model in MODELS:
            with self.subTest(model=model):
                presentation = RoomReadOnlyPresentation(self._row(model, {"speaker_volume": 5}))
                self.addCleanup(presentation.deleteLater)
                self.assertFalse(presentation.findChild(QPushButton, "roomCodecRebootButton").isEnabled())

    def test_preterminal_codec_expansion_defers_its_single_preview_attempt(self):
        row = self._row()
        session = RoomDiagnosticSession(
            RoomDiagnosticSessionIdentity("snapshot", 1, None, None, "R-1"),
            "R-1", None, None, [row], status=RoomCycleStatus.ACTIVE,
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
        self.assertEqual([], requests)
        session.status = RoomCycleStatus.COMPLETE
        coordinator.cycle_finished(session)
        coordinator.request_codec_preview()
        self.assertEqual(["call_log_preview"], requests)

    def test_preview_remains_pending_while_auxiliary_lane_is_busy(self):
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
        explicit = coordinator.request_auxiliary("call_log")
        self.assertEqual(["call_log"], requests)
        coordinator.request_codec_preview()
        self.assertEqual(["call_log"], requests)
        coordinator.complete(explicit, success=True, data={})
        self.assertEqual(["call_log", "call_log_preview"], requests)

    def test_pending_preview_identity_is_not_transferred_between_codec_rows(self):
        first = self._row("Huawei TE20")
        second = self._row("CloudLink Box 310")
        second.record_id, second.ip_address = "codec-2", "192.0.2.11"
        session = RoomDiagnosticSession(
            RoomDiagnosticSessionIdentity("snapshot", 1, None, None, "R-1"),
            "R-1", None, None, [first, second], status=RoomCycleStatus.COMPLETE,
        )
        requests = []
        coordinator = RoomInteractionCoordinator(
            bindings_for_model=lambda _model: RoomInteractionBindings(
                auxiliary=lambda context, action: requests.append((action, context.record_id)),
                cancel=lambda _context: None, cleanup=lambda _context: False,
            ),
        )
        coordinator.bind_session(session)
        coordinator.expand(first.record_id)
        busy = coordinator.request_auxiliary("call_log")
        coordinator.request_codec_preview()
        coordinator.expand(second.record_id)
        coordinator.request_codec_preview()
        coordinator.cleanup_finished(busy)

        self.assertEqual([("call_log", "codec-1"), ("call_log_preview", "codec-2")], requests)
        coordinator.complete(coordinator.active_context, success=True, data={})
        coordinator.request_codec_preview()
        self.assertEqual(1, [action for action, _record in requests].count("call_log_preview"))

    def test_pending_preview_rechecks_live_priority_after_non_live_cleanup(self):
        first = DeviceRowState(
            "aux-1", "Extron IN1804", "192.0.2.10", "Extron IN1804",
            DeviceRowStatus.CONNECTED,
            capability=RoomModelCapability("Extron IN1804", "matrix", "route", "adapter"),
            accepted_snapshot={},
        )
        second = self._row("CloudLink Box 310")
        second.record_id, second.ip_address = "codec-2", "192.0.2.11"
        session = RoomDiagnosticSession(
            RoomDiagnosticSessionIdentity("snapshot", 1, None, None, "R-1"),
            "R-1", None, None, [first, second], status=RoomCycleStatus.COMPLETE,
        )
        calls = []
        auxiliary = RoomInteractionBindings(
            auxiliary=lambda context, action: calls.append((action, context.record_id)),
            cancel=lambda _context: None, cleanup=lambda _context: False,
        )
        codec = RoomInteractionBindings(
            live=lambda context: calls.append(("live", context.record_id)),
            auxiliary=lambda context, action: calls.append((action, context.record_id)),
            cancel=lambda _context: None, cleanup=lambda _context: False,
        )
        coordinator = RoomInteractionCoordinator(
            bindings_for_model=lambda model: codec if model == "CloudLink Box 310" else auxiliary,
        )
        coordinator.bind_session(session)
        coordinator.expand(first.record_id)
        busy = coordinator.request_auxiliary("call_log")
        coordinator.expand(second.record_id)
        coordinator.request_codec_preview()
        coordinator.cleanup_finished(busy)

        self.assertEqual([("call_log", "aux-1"), ("live", "codec-2")], calls)
        self.assertEqual("LIVE", coordinator.active_context.kind.value)
        self.assertIsNone(coordinator._pending_codec_preview)
        coordinator.complete(coordinator.active_context, success=True, data={})
        coordinator.request_codec_preview()
        self.assertEqual(0, sum(action == "call_log_preview" for action, _row in calls))

    def test_pending_preview_is_discarded_for_non_codec_switch_and_collapse(self):
        first = self._row("Huawei TE20")
        non_codec = DeviceRowState(
            "matrix-1", "Extron IN1804", "192.0.2.11", "Extron IN1804",
            DeviceRowStatus.CONNECTED,
            capability=RoomModelCapability("Extron IN1804", "matrix", "route", "adapter"),
            accepted_snapshot={},
        )
        session = RoomDiagnosticSession(
            RoomDiagnosticSessionIdentity("snapshot", 1, None, None, "R-1"),
            "R-1", None, None, [first, non_codec], status=RoomCycleStatus.COMPLETE,
        )
        requests = []
        codec_bindings = RoomInteractionBindings(
            auxiliary=lambda context, action: requests.append((action, context.record_id)),
            cancel=lambda _context: None, cleanup=lambda _context: False,
        )
        matrix_bindings = RoomInteractionBindings(
            live=lambda context: requests.append(("live", context.record_id)),
            cancel=lambda _context: None, cleanup=lambda _context: False,
        )
        coordinator = RoomInteractionCoordinator(
            bindings_for_model=lambda model: matrix_bindings if model == "Extron IN1804" else codec_bindings,
        )
        coordinator.bind_session(session)
        coordinator.expand(first.record_id)
        busy = coordinator.request_auxiliary("call_log")
        coordinator.request_codec_preview()
        coordinator.expand(non_codec.record_id)
        coordinator.cleanup_finished(busy)
        self.assertEqual([("call_log", "codec-1"), ("live", "matrix-1")], requests)

        coordinator.bind_session(session)
        coordinator.expand(first.record_id)
        busy = coordinator.request_auxiliary("call_log")
        coordinator.request_codec_preview()
        coordinator.collapse(first.record_id)
        coordinator.cleanup_finished(busy)
        self.assertEqual([], [item for item in requests if item[0] == "call_log_preview"])

    def test_live_preview_handoff_discards_stale_codec_preview_and_starts_non_codec_live(self):
        codec = self._row("CloudLink Bar 310")
        matrix = DeviceRowState(
            "matrix-1", "Extron IN1804", "192.0.2.11", "Extron IN1804",
            DeviceRowStatus.CONNECTED,
            capability=RoomModelCapability("Extron IN1804", "matrix", "route", "adapter"),
            accepted_snapshot={},
        )
        session = RoomDiagnosticSession(
            RoomDiagnosticSessionIdentity("snapshot", 1, None, None, "R-1"),
            "R-1", None, None, [codec, matrix], status=RoomCycleStatus.COMPLETE,
        )
        calls = []
        codec_bindings = RoomInteractionBindings(
            live=lambda context: calls.append(("live", context.record_id)),
            auxiliary=lambda context, action: calls.append((action, context.record_id)),
            cancel=lambda _context: None, cleanup=lambda _context: False,
        )
        matrix_bindings = RoomInteractionBindings(
            live=lambda context: calls.append(("live", context.record_id)),
            cancel=lambda _context: None, cleanup=lambda _context: False,
        )
        coordinator = RoomInteractionCoordinator(
            bindings_for_model=lambda model: matrix_bindings if model == "Extron IN1804" else codec_bindings,
        )
        coordinator.bind_session(session)
        coordinator.expand(codec.record_id)
        retiring_live = coordinator.active_context
        coordinator.request_codec_preview()
        coordinator.expand(matrix.record_id)
        coordinator.cleanup_finished(retiring_live)

        self.assertEqual([("live", "codec-1"), ("live", "matrix-1")], calls)
        self.assertEqual("matrix-1", coordinator.active_context.record_id)
        self.assertIsNone(coordinator._pending_operation)

    def test_live_preview_handoff_starts_only_current_live_owner(self):
        first = self._row("CloudLink Box 310")
        second = self._row("Huawei TE20")
        second.record_id, second.ip_address = "codec-2", "192.0.2.11"
        session = RoomDiagnosticSession(
            RoomDiagnosticSessionIdentity("snapshot", 1, None, None, "R-1"),
            "R-1", None, None, [first, second], status=RoomCycleStatus.COMPLETE,
        )
        calls = []
        bindings = RoomInteractionBindings(
            live=lambda context: calls.append(("live", context.record_id)),
            auxiliary=lambda context, action: calls.append((action, context.record_id)),
            cancel=lambda _context: None, cleanup=lambda _context: False,
        )
        coordinator = RoomInteractionCoordinator(bindings_for_model=lambda _model: bindings)
        coordinator.bind_session(session)
        coordinator.expand(first.record_id)
        retiring_live = coordinator.active_context
        coordinator.request_codec_preview()
        coordinator.expand(second.record_id)
        coordinator.request_codec_preview()
        coordinator.cleanup_finished(retiring_live)

        self.assertEqual([("live", "codec-1"), ("live", "codec-2")], calls)
        self.assertEqual("codec-2", coordinator.active_context.record_id)
        self.assertEqual(0, [call for call in calls if call[0] == "call_log_preview"].count(("call_log_preview", "codec-2")))
        self.assertNotIn(("call_log_preview", "codec-1"), calls)

    def test_live_priority_preview_is_terminal_and_never_starts_after_cleanup(self):
        row = self._row("CloudLink Bar 310")
        session = RoomDiagnosticSession(
            RoomDiagnosticSessionIdentity("snapshot", 1, None, None, "R-1"),
            "R-1", None, None, [row], status=RoomCycleStatus.COMPLETE,
        )
        calls = []
        bindings = RoomInteractionBindings(
            live=lambda context: calls.append(("live", context.record_id)),
            auxiliary=lambda context, action: calls.append((action, context.record_id)),
            cancel=lambda _context: None, cleanup=lambda _context: False,
        )
        coordinator = RoomInteractionCoordinator(bindings_for_model=lambda _model: bindings)
        coordinator.bind_session(session)
        coordinator.expand(row.record_id)
        retiring_live = coordinator.active_context
        coordinator.request_codec_preview()
        coordinator.cleanup_finished(retiring_live)

        self.assertEqual([("live", "codec-1"), ("live", "codec-1")], calls)
        self.assertEqual(0, calls.count(("call_log_preview", "codec-1")))

    def test_live_preview_handoff_collapse_does_not_resurrect_work(self):
        row = self._row("CloudLink Box 310")
        session = RoomDiagnosticSession(
            RoomDiagnosticSessionIdentity("snapshot", 1, None, None, "R-1"),
            "R-1", None, None, [row], status=RoomCycleStatus.COMPLETE,
        )
        calls = []
        bindings = RoomInteractionBindings(
            live=lambda context: calls.append(("live", context.record_id)),
            auxiliary=lambda context, action: calls.append((action, context.record_id)),
            cancel=lambda _context: None, cleanup=lambda _context: False,
        )
        coordinator = RoomInteractionCoordinator(bindings_for_model=lambda _model: bindings)
        coordinator.bind_session(session)
        coordinator.expand(row.record_id)
        retiring_live = coordinator.active_context
        coordinator.request_codec_preview()
        coordinator.collapse(row.record_id)
        coordinator.cleanup_finished(retiring_live)

        self.assertEqual([("live", "codec-1")], calls)
        self.assertIsNone(coordinator.active_context)
        self.assertIsNone(coordinator._pending_operation)

    def test_preview_is_not_dropped_when_explicit_detail_arrives_during_live_retirement(self):
        row = self._row()
        session = RoomDiagnosticSession(
            RoomDiagnosticSessionIdentity("snapshot", 1, None, None, "R-1"),
            "R-1", None, None, [row], status=RoomCycleStatus.COMPLETE,
        )
        requests = []
        coordinator = RoomInteractionCoordinator(
            bindings_for_model=lambda _model: RoomInteractionBindings(
                live=lambda context: requests.append(("live", context)),
                auxiliary=lambda _context, action: requests.append((action, None)),
                cancel=lambda _context: None,
                cleanup=lambda _context: False,
            ),
        )
        coordinator.bind_session(session)
        coordinator.expand(row.record_id)
        live = coordinator.active_context
        coordinator.request_codec_preview()
        coordinator.request_auxiliary("call_log")
        coordinator.cleanup_finished(live)
        explicit = coordinator.active_context
        coordinator.complete(explicit, success=True, data={})
        self.assertEqual(["live", "call_log", "live"], [request[0] for request in requests])

    def test_explicit_detail_never_reuses_preview_snapshot(self):
        from gui.main_window import VCSDiagnosticApp

        row = self._row()
        row.call_log_preview_snapshot = snapshot_from_records((), source_ended=True)
        coordinator = Mock()
        window = SimpleNamespace(
            room_diagnostic_session=SimpleNamespace(row_for=lambda _record_id: row),
            room_interaction_coordinator=coordinator,
        )
        VCSDiagnosticApp._on_room_auxiliary_requested(window, row.record_id, "call_log")
        coordinator.request_auxiliary.assert_called_once_with("call_log")

    def test_stale_call_log_result_has_no_publication_or_success_persistence(self):
        from gui.main_window import VCSDiagnosticApp

        row = self._row()
        session = RoomDiagnosticSession(
            RoomDiagnosticSessionIdentity("snapshot", 1, None, None, "R-1"),
            "R-1", None, None, [row], expanded_record_id=row.record_id,
            status=RoomCycleStatus.COMPLETE,
        )
        coordinator = RoomInteractionCoordinator(
            bindings_for_model=lambda _model: RoomInteractionBindings(auxiliary=lambda *_args: None),
        )
        coordinator.bind_session(session)
        context = coordinator.request_auxiliary("call_log_preview")
        row.operation_token += 1  # retirement leaves active_context but invalidates authority
        detail_window = SimpleNamespace(set_snapshot=Mock(), status_label=SimpleNamespace(setText=Mock()))
        credential_index, profile = Mock(), Mock()
        window = SimpleNamespace(
            room_interaction_coordinator=coordinator,
            room_diagnostic_session=session,
            _room_call_log_actions={context: "call_log_preview"},
            _room_call_log_windows={context: detail_window},
            _room_credential_attempts={context: (({"username": "u"},), 0, None)},
            room_call_log_controller=SimpleNamespace(take_success_evidence=Mock(return_value={"connection_profile": {"mode": "x"}})),
            set_current_credential_index=credential_index,
            set_device_connection_profile=profile,
        )
        VCSDiagnosticApp._on_room_call_log_finished(window, context, True, {"fresh": True}, False, None)

        self.assertIsNone(row.call_log_preview_snapshot)
        detail_window.set_snapshot.assert_not_called()
        detail_window.status_label.setText.assert_not_called()
        credential_index.assert_not_called()
        profile.assert_not_called()

    def test_stale_local_refresh_success_does_not_persist_credential(self):
        from gui.main_window import VCSDiagnosticApp

        row = self._row()
        session = RoomDiagnosticSession(
            RoomDiagnosticSessionIdentity("snapshot", 1, None, None, "R-1"),
            "R-1", None, None, [row], expanded_record_id=row.record_id,
            status=RoomCycleStatus.COMPLETE,
        )
        coordinator = RoomInteractionCoordinator(
            bindings_for_model=lambda _model: RoomInteractionBindings(local_refresh=lambda *_args: None),
        )
        coordinator.bind_session(session)
        context = coordinator.request_local_refresh()
        row.operation_token += 1
        credential_index = Mock()
        controller = SimpleNamespace(forget_local_refresh=Mock())
        window = SimpleNamespace(
            room_interaction_coordinator=coordinator,
            _room_matrix_reconciliation_requests={},
            _room_credential_attempts={context: (({"username": "u"},), 0, None)},
            _room_live_inflight=set(),
            room_diagnostic_controller=controller,
            set_current_credential_index=credential_index,
        )
        VCSDiagnosticApp._on_room_local_refresh_finished(window, context, True, {"fresh": True}, False, None)

        credential_index.assert_not_called()
        controller.forget_local_refresh.assert_called_once_with(context)

    def test_cloudlink_box_310_preview_and_fresh_detail_regression_oracle(self):
        from gui.dialogs.call_log_window import CallLogWindow

        entry = dispatch_entry_for_model("CloudLink Box 310")
        self.assertEqual("CloudLink Box 310", entry.diagnostic_model)
        self.assertEqual("cloudlink_bar_310", entry.lifecycle_route)
        self.assertEqual("codec_one_shot", entry.room_adapter_key)
        now = datetime(2026, 9, 2, 10, 0)
        preview = snapshot_from_records((
            CallRecord("preview", now, 60, room_number="preview", direction=CallDirection.INCOMING),
        ), reference_now=now, source_ended=True)
        fresh = snapshot_from_records((
            CallRecord("detail", now, 120, room_number="fresh", direction=CallDirection.OUTGOING),
        ), reference_now=now, source_ended=True)
        row = self._row("CloudLink Box 310")
        row.call_log_preview_snapshot = preview
        presentation = RoomReadOnlyPresentation(row)
        self.addCleanup(presentation.deleteLater)
        self.assertEqual("preview", presentation.findChild(QLabel, "roomCodecCallNumber").text())
        dialog = CallLogWindow()
        self.addCleanup(dialog.deleteLater)
        dialog.set_snapshot(fresh)
        self.assertEqual("fresh", dialog.preview_table.item(0, 0).text())
        self.assertEqual("Исходящий", dialog.preview_table.item(0, 4).text())
        self.assertTrue(dialog.usage_label.text())


if __name__ == "__main__":
    unittest.main()
