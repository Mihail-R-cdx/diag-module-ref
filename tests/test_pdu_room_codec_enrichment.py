import os
import threading
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
except ImportError:
    QApplication = None

from core.equipment_inventory import (
    EquipmentInventory,
    EquipmentInventoryMetadata,
    EquipmentRecord,
)
from core.exceptions import CodecFailureCategory, ProtocolError
from core.interactive_session import (
    InteractiveOperation,
    InteractiveSessionController,
    OperationSemantic,
)
from core.related_codec_status import RelatedCodecStatus, RelatedCodecStatusAdapter
from core.room_context import (
    ROOM_NAME_CONFLICT,
    RoomContextResolver,
    RoomResolutionStatus,
)
from gui.pdu_room_codec_enrichment import (
    PDUAcceptedRefreshContext,
    PDUContextSuperseded,
    PDURoomCodecEnrichmentController,
)


def record(
    record_id,
    *,
    ip_address=None,
    room_id="ROOM-1",
    room_name="Room One",
    device_kind="other",
    source_model=None,
    diagnostic_model=None,
):
    return EquipmentRecord(
        record_id=record_id,
        source_model=source_model,
        diagnostic_model=diagnostic_model,
        ip_address=ip_address,
        mac_address=None,
        serial_number=None,
        room_id=room_id,
        room_name=room_name,
        device_kind=device_kind,
    )


def inventory(records, snapshot_id="sha256:" + "1" * 64):
    return EquipmentInventory.from_records(
        tuple(records),
        EquipmentInventoryMetadata(schema_version=1, snapshot_id=snapshot_id),
    )


class RoomContextResolverTests(unittest.TestCase):
    def setUp(self):
        self.resolver = RoomContextResolver()

    def resolve(self, records, ip="192.0.2.10"):
        return self.resolver.resolve_related_codec(inventory(records), ip)

    def test_inventory_unavailable_and_pdu_ip_zero_one_many(self):
        self.assertEqual(
            RoomResolutionStatus.INVENTORY_UNAVAILABLE,
            self.resolver.resolve_related_codec(None, "192.0.2.10").status,
        )
        self.assertEqual(RoomResolutionStatus.PDU_NOT_FOUND, self.resolve([]).status)

        result = self.resolve(
            [
                record("PDU-1", ip_address="192.0.2.10", device_kind="pdu"),
                record("OTHER-1", ip_address="192.0.2.10", device_kind="other"),
            ]
        )
        self.assertEqual(RoomResolutionStatus.AMBIGUOUS_PDU_IP, result.status)

    def test_kind_mismatch_and_missing_room_id_do_not_fallback_to_room_name(self):
        result = self.resolve(
            [record("CODEC-IP", ip_address="192.0.2.10", device_kind="video_codec")]
        )
        self.assertEqual(RoomResolutionStatus.PDU_KIND_MISMATCH, result.status)

        result = self.resolve(
            [
                record(
                    "PDU-1",
                    ip_address="192.0.2.10",
                    room_id=None,
                    room_name="Display Only",
                    device_kind="pdu",
                )
            ]
        )
        self.assertEqual(RoomResolutionStatus.ROOM_UNRESOLVED, result.status)
        self.assertIsNone(result.room_id)
        self.assertEqual("Display Only", result.room_name)

    def test_codec_zero_one_many_missing_ip_and_unsupported(self):
        pdu = record("PDU-1", ip_address="192.0.2.10", device_kind="pdu")
        self.assertEqual(RoomResolutionStatus.CODEC_NOT_FOUND, self.resolve([pdu]).status)
        self.assertEqual(
            RoomResolutionStatus.AMBIGUOUS_CODEC,
            self.resolve(
                [
                    pdu,
                    record(
                        "C1",
                        ip_address="192.0.2.20",
                        device_kind="video_codec",
                        diagnostic_model="Huawei TE20",
                    ),
                    record(
                        "C2",
                        ip_address="192.0.2.21",
                        device_kind="video_codec",
                        diagnostic_model="Huawei TE40",
                    ),
                ]
            ).status,
        )
        self.assertEqual(
            RoomResolutionStatus.CODEC_IP_MISSING,
            self.resolve(
                [
                    pdu,
                    record(
                        "C1",
                        ip_address=None,
                        device_kind="video_codec",
                        diagnostic_model="Huawei TE20",
                    ),
                ]
            ).status,
        )
        self.assertEqual(
            RoomResolutionStatus.CODEC_UNSUPPORTED,
            self.resolve(
                [
                    pdu,
                    record(
                        "C1",
                        ip_address="192.0.2.20",
                        device_kind="video_codec",
                        diagnostic_model=None,
                    ),
                ]
            ).status,
        )
        resolved = self.resolve(
            [
                pdu,
                record(
                    "C1",
                    ip_address="192.0.2.20",
                    device_kind="video_codec",
                    diagnostic_model="Huawei TE20",
                ),
            ]
        )
        self.assertEqual(RoomResolutionStatus.RESOLVED, resolved.status)
        self.assertEqual("ROOM-1", resolved.context.room_id)
        self.assertEqual("192.0.2.20", resolved.context.codec_ip_address)

    def test_conflicting_room_names_continue_by_room_id_without_selecting_name(self):
        result = self.resolve(
            [
                record(
                    "PDU-1",
                    ip_address="192.0.2.10",
                    room_name="Room A",
                    device_kind="pdu",
                ),
                record(
                    "C1",
                    ip_address="192.0.2.20",
                    room_name="Room B",
                    device_kind="video_codec",
                    diagnostic_model="Huawei TE20",
                ),
            ]
        )
        self.assertEqual(RoomResolutionStatus.RESOLVED, result.status)
        self.assertIsNone(result.context.room_name)
        self.assertIn(ROOM_NAME_CONFLICT, result.warnings)


class RelatedCodecStatusAdapterTests(unittest.TestCase):
    def test_normalizes_supported_models_without_raw_payload(self):
        adapter = RelatedCodecStatusAdapter()
        shapes = {
            "Huawei TE20": {"call_status": "No Call", "presentation_local": "Stopped"},
            "Huawei TE40": {"call_status": "Calling", "presentation": "Start"},
            "CloudLink Bar 310": {
                "call_status": "In Call",
                "presentation_status": "Start",
            },
            "Polycom RPG 310": {"call": {"status": "Connected"}, "presentation": "content"},
        }
        for model, raw in shapes.items():
            with self.subTest(model=model):
                normalized = adapter.normalize(model, raw)
                self.assertNotEqual("unknown", normalized.call_status)
                self.assertNotEqual("unknown", normalized.presentation_status)
                self.assertEqual(
                    {"call_status", "presentation_status"},
                    set(normalized.as_dict()),
                )

    def test_allows_one_authoritative_field_but_rejects_uninterpretable_status(self):
        adapter = RelatedCodecStatusAdapter()
        normalized = adapter.normalize("Huawei TE20", {"call_status": "No Call"})
        self.assertEqual("No Call", normalized.call_status)
        self.assertEqual("unknown", normalized.presentation_status)

        with self.assertRaises(ProtocolError):
            adapter.normalize("Huawei TE20", {"error": "synthetic read failure"})
        with self.assertRaises(ProtocolError):
            adapter.normalize("Huawei TE20", {})
        with self.assertRaises(ProtocolError):
            adapter.read_status(object(), "Huawei TE20")
        with self.assertRaises(ProtocolError):
            adapter.read_status(type("Handler", (), {"get_status": lambda self: []})(), "Huawei TE20")

    def test_authoritative_huawei_status_reads_model_specific_command_fields(self):
        cases = {
            "Huawei TE20": (
                "get_presentation_local",
                "Calling",
                "Start",
                1,
                "auxOpen",
            ),
            "Huawei TE40": (
                "get_presentation",
                "Calling",
                "Stop",
                2,
                "auxClose",
            ),
            "CloudLink Bar 310": (
                "get_presentation",
                "Connected",
                "Start",
                3,
                "auxOpen",
            ),
        }
        for model, (presentation_command, call_text, presentation_text, callstate, aux_state) in cases.items():
            with self.subTest(model=model):
                handler = FakeHuaweiStatusHandler(
                    {
                        "get_call_status": success_response({"state": {"callstate": callstate}}),
                        presentation_command: success_response({"isSendAux": aux_state}),
                    }
                )
                status = RelatedCodecStatusAdapter().read_status(handler, model)
                self.assertEqual(call_text, status.call_status)
                self.assertEqual(presentation_text, status.presentation_status)

    def test_bar310_related_status_does_not_trust_get_status_defaults(self):
        handler = FakeHuaweiStatusHandler(
            {
                "get_call_status": {"success": 0, "error": {"code": 1}},
                "get_presentation": {"success": 0, "error": {"code": 2}},
            },
            get_status_payload={"call_status": "No Call", "presentation": "Stop"},
        )

        with self.assertRaises(ProtocolError):
            RelatedCodecStatusAdapter().read_status(handler, "CloudLink Bar 310")
        self.assertFalse(handler.get_status_called)
        self.assertEqual(["get_call_status", "get_presentation"], handler.commands)

    def test_bar310_related_status_allows_one_authoritative_field_only(self):
        handler = FakeHuaweiStatusHandler(
            {
                "get_call_status": {"success": 0, "error": {"code": 1}},
                "get_presentation": success_response({"isSendAux": "auxOpen"}),
            }
        )

        status = RelatedCodecStatusAdapter().read_status(handler, "CloudLink Bar 310")
        self.assertEqual("unknown", status.call_status)
        self.assertEqual("Start", status.presentation_status)

    def test_bar310_related_status_rejects_missing_or_malformed_authoritative_fields(self):
        adapter = RelatedCodecStatusAdapter()
        missing_fields = FakeHuaweiStatusHandler(
            {
                "get_call_status": success_response({"state": {}}),
                "get_presentation": success_response({}),
            }
        )
        malformed = FakeHuaweiStatusHandler(
            {
                "get_call_status": success_response("{not-json"),
                "get_presentation": success_response([]),
            }
        )

        with self.assertRaises(ProtocolError):
            adapter.read_status(missing_fields, "CloudLink Bar 310")
        with self.assertRaises(ProtocolError):
            adapter.read_status(malformed, "CloudLink Bar 310")

    def test_polycom_related_status_uses_narrow_methods_without_get_status_defaults(self):
        handler = FakePolycomStatusHandler(call_status="Active", presentation_status="Stop")
        status = RelatedCodecStatusAdapter().read_status(handler, "Polycom RPG 310")

        self.assertEqual("Active", status.call_status)
        self.assertEqual("Stop", status.presentation_status)
        self.assertFalse(handler.get_status_called)

    def test_polycom_related_status_rejects_both_fields_unavailable(self):
        with self.assertRaises(ProtocolError):
            RelatedCodecStatusAdapter().read_status(
                FakePolycomStatusHandler(call_status=None, presentation_status=None),
                "Polycom RPG 310",
            )


def success_response(data):
    return {"success": 1, "data": data}


class FakeHuaweiStatusHandler:
    def __init__(self, responses, *, get_status_payload=None):
        self.responses = dict(responses)
        self.get_status_payload = get_status_payload or {}
        self.get_status_called = False
        self.commands = []

    def send_command(self, command):
        self.commands.append(command)
        return self.responses.get(command)

    def get_status(self):
        self.get_status_called = True
        return dict(self.get_status_payload)


class FakePolycomStatusHandler:
    def __init__(self, *, call_status, presentation_status):
        self.call_status = call_status
        self.presentation_status = presentation_status
        self.get_status_called = False

    def _get_call_status(self):
        return self.call_status

    def get_presentation_status(self):
        return self.presentation_status

    def get_status(self):
        self.get_status_called = True
        return {"call_status": "No Call", "presentation": "Stop"}


class DummySession:
    def __init__(self):
        self.invalidate_calls = 0
        self.activate_calls = []
        self.submits = []
        self.shutdown_wait = None
        self.signals = _SessionSignals()

    def invalidate_context(self):
        self.invalidate_calls += 1
        return self.invalidate_calls

    def activate_context(self, *args, **kwargs):
        self.activate_calls.append((args, kwargs))
        return 100 + len(self.activate_calls)

    def submit(self, operation, *, generation=None):
        self.submits.append((operation, generation))
        return len(self.submits)

    def shutdown(self, wait=True):
        self.shutdown_wait = wait


class _SessionSignals:
    def __init__(self):
        self.result = _Signal()
        self.error = _Signal()
        self.dropped = _Signal()


class _Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, payload):
        for callback in tuple(self.callbacks):
            callback(payload)


class EnrichmentControllerTests(unittest.TestCase):
    def accepted_context(self):
        return PDUAcceptedRefreshContext(
            pdu_generation=7,
            refresh_operation_id=11,
            model="Aten PE8208AV",
            ip_address="192.0.2.10",
            credential_context_revision=3,
        )

    def build_controller(self, inv, session=None, credentials=({"username": "u", "password": "p"},)):
        self.presentations = []
        self.persisted = []
        return PDURoomCodecEnrichmentController(
            inventory_provider=lambda: inv,
            inventory_failure_provider=lambda: None,
            credential_candidates_provider=lambda model, ip: credentials,
            credential_index_provider=lambda model, ip, candidates: 0,
            credential_revision_provider=lambda: 1,
            connection_profile_provider=lambda model, ip: {"port": 80, "use_ssl": False},
            success_persistence=lambda *args: self.persisted.append(args),
            presentation_callback=self.presentations.append,
            session_controller=session or DummySession(),
        )

    def resolved_inventory(self):
        return inventory(
            [
                record("PDU-1", ip_address="192.0.2.10", device_kind="pdu"),
                record(
                    "C1",
                    ip_address="192.0.2.20",
                    device_kind="video_codec",
                    diagnostic_model="Huawei TE20",
                ),
            ]
        )

    def test_inventory_unavailable_does_not_start_codec_work(self):
        session = DummySession()
        controller = self.build_controller(None, session=session)
        controller.accept_pdu_refresh(self.accepted_context())
        self.assertEqual(1, session.invalidate_calls)
        self.assertEqual([], session.activate_calls)
        self.assertEqual("INVENTORY_UNAVAILABLE", self.presentations[-1]["resolution_status"])
        self.assertEqual("NOT_STARTED", self.presentations[-1]["codec_diagnostic_status"])

    def test_resolved_context_force_rollover_and_queued_status_submission(self):
        session = DummySession()
        controller = self.build_controller(self.resolved_inventory(), session=session)
        controller.accept_pdu_refresh(self.accepted_context())
        controller.accept_pdu_refresh(self.accepted_context())
        self.assertEqual(2, session.invalidate_calls)
        self.assertEqual(2, len(session.activate_calls))
        self.assertEqual(2, len(session.submits))
        self.assertNotEqual(self.presentations[1]["generation"], self.presentations[-2]["generation"])

    def test_supersession_clears_presentation_before_replacement_success(self):
        session = DummySession()
        controller = self.build_controller(None, session=session)
        controller.supersede_pdu_context(PDUContextSuperseded(8, "user_refresh_started"))
        self.assertEqual(1, session.invalidate_calls)
        self.assertTrue(self.presentations[-1]["reset"])
        self.assertEqual("NOT_STARTED", self.presentations[-1]["codec_diagnostic_status"])
        self.assertIsNone(self.presentations[-1]["safe_message"])

    def test_terminal_success_persists_and_cleans_up_session(self):
        session = DummySession()
        controller = self.build_controller(self.resolved_inventory(), session=session)
        controller.accept_pdu_refresh(self.accepted_context())
        token = session.submits[-1][0].client_token
        session.signals.result.emit(
            {
                "client_token": token,
                "value": RelatedCodecStatus("Connected", "Start"),
                "credential_index": 0,
                "connection_profile": {"port": 80, "use_ssl": False},
            }
        )

        self.assertEqual("SUCCESS", self.presentations[-1]["codec_diagnostic_status"])
        self.assertEqual(1, len(self.persisted))
        self.assertEqual(2, session.invalidate_calls)

    def test_uninterpretable_status_result_is_protocol_failure_without_persistence(self):
        session = DummySession()
        controller = self.build_controller(self.resolved_inventory(), session=session)
        controller.accept_pdu_refresh(self.accepted_context())
        token = session.submits[-1][0].client_token
        session.signals.result.emit(
            {
                "client_token": token,
                "value": object(),
                "credential_index": 0,
                "connection_profile": {"port": 80, "use_ssl": False},
            }
        )

        self.assertEqual("PROTOCOL_FAILED", self.presentations[-1]["codec_diagnostic_status"])
        self.assertEqual([], self.persisted)
        self.assertEqual(2, session.invalidate_calls)

    def test_terminal_error_cleans_up_without_persistence(self):
        session = DummySession()
        controller = self.build_controller(self.resolved_inventory(), session=session)
        controller.accept_pdu_refresh(self.accepted_context())
        token = session.submits[-1][0].client_token
        session.signals.error.emit(
            {
                "client_token": token,
                "category": CodecFailureCategory.PROTOCOL.value,
            }
        )

        self.assertEqual("PROTOCOL_FAILED", self.presentations[-1]["codec_diagnostic_status"])
        self.assertEqual([], self.persisted)
        self.assertEqual(2, session.invalidate_calls)

    def test_stale_in_flight_success_cannot_restore_presentation_or_persist(self):
        session = DummySession()
        controller = self.build_controller(self.resolved_inventory(), session=session)
        controller.accept_pdu_refresh(self.accepted_context())
        token = session.submits[-1][0].client_token
        controller.supersede_pdu_context(PDUContextSuperseded(8, "user_refresh_started"))
        session.signals.result.emit(
            {
                "client_token": token,
                "value": RelatedCodecStatus("Connected", "Start"),
                "credential_index": 0,
                "connection_profile": {"port": 80, "use_ssl": False},
            }
        )

        self.assertTrue(self.presentations[-1]["reset"])
        self.assertEqual([], self.persisted)


class InteractiveSessionStaleWorkTests(unittest.TestCase):
    def test_queued_stale_work_drops_before_handler_factory(self):
        blocked = threading.Event()
        entered = threading.Event()
        handler_factory_calls = []

        def handler_factory(*args, **kwargs):
            handler_factory_calls.append((args, kwargs))
            raise AssertionError("stale work must not acquire a handler")

        session = InteractiveSessionController(handler_factory=handler_factory)
        blocker = session._executor.submit(lambda: (entered.set(), blocked.wait(5)))
        try:
            self.assertTrue(entered.wait(1))
            generation = session.activate_context(
                "Huawei TE20",
                "192.0.2.20",
                [{"username": "u", "password": "p"}],
            )
            submitted = session.submit(
                InteractiveOperation(
                    kind="pdu_room_codec_status",
                    method="read_status",
                    semantic=OperationSemantic.READ_ONLY,
                ),
                generation=generation,
            )
            self.assertIsNotNone(submitted)
            session.invalidate_context()
            blocked.set()
            blocker.result(timeout=2)
            session.wait_until_idle(timeout=2)
            self.assertEqual([], handler_factory_calls)
        finally:
            blocked.set()
            session.shutdown(wait=True)


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class PDUIntegrationScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_pdu_screen_renders_inline_failure_without_modal(self):
        from gui.screens.pdu_screen import PDUScreen

        screen = PDUScreen()
        with unittest.mock.patch.object(QMessageBox, "critical") as critical:
            screen.update_data(
                {
                    "device_info": {"model": "Aten", "connected": True},
                    "outlets": [{"number": 1, "status": "on"}],
                }
            )
            screen.set_related_room_codec(
                {
                    "resolution_status": "RESOLVED",
                    "codec_diagnostic_status": "TRANSPORT_FAILED",
                    "room_id": "ROOM-1",
                    "codec_diagnostic_model": "Huawei TE20",
                    "codec_ip_address": "192.0.2.20",
                    "safe_message": "Codec connection failed.",
                }
            )
        critical.assert_not_called()
        self.assertEqual("ROOM-1", screen.related_rows["room_id"].value_display.text())
        self.assertTrue(screen.outlets)

    def test_pdu_screen_reset_payload_clears_related_room_without_warning(self):
        from gui.screens.pdu_screen import PDUScreen

        screen = PDUScreen()
        screen.set_related_room_codec(
            {
                "resolution_status": "RESOLVED",
                "codec_diagnostic_status": "SUCCESS",
                "room_id": "ROOM-1",
                "codec_diagnostic_model": "Huawei TE20",
                "codec_ip_address": "192.0.2.20",
                "call_status": "Connected",
                "presentation_status": "Start",
            }
        )
        screen.set_related_room_codec({"reset": True})

        self.assertEqual("", screen.related_message.text())
        for row in screen.related_rows.values():
            self.assertNotIn(
                row.value_display.text(),
                {"ROOM-1", "Huawei TE20", "192.0.2.20", "Connected", "Start"},
            )


if __name__ == "__main__":
    unittest.main()
