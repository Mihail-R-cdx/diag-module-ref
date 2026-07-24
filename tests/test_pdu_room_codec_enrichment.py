import os
import unittest
from unittest.mock import Mock

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
from core.related_codec_status import RelatedCodecStatusAdapter
from core.room_context import (
    ROOM_NAME_CONFLICT,
    RoomContextResolver,
    RoomResolutionStatus,
)
from gui.pdu_room_codec_enrichment import (
    CodecDiagnosticStatus,
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
                    record("C1", ip_address="192.0.2.20", device_kind="video_codec", diagnostic_model="Huawei TE20"),
                    record("C2", ip_address="192.0.2.21", device_kind="video_codec", diagnostic_model="Huawei TE40"),
                ]
            ).status,
        )
        self.assertEqual(
            RoomResolutionStatus.CODEC_IP_MISSING,
            self.resolve(
                [pdu, record("C1", ip_address=None, device_kind="video_codec", diagnostic_model="Huawei TE20")]
            ).status,
        )
        self.assertEqual(
            RoomResolutionStatus.CODEC_UNSUPPORTED,
            self.resolve(
                [pdu, record("C1", ip_address="192.0.2.20", device_kind="video_codec", diagnostic_model=None)]
            ).status,
        )
        resolved = self.resolve(
            [pdu, record("C1", ip_address="192.0.2.20", device_kind="video_codec", diagnostic_model="Huawei TE20")]
        )
        self.assertEqual(RoomResolutionStatus.RESOLVED, resolved.status)
        self.assertEqual("ROOM-1", resolved.context.room_id)
        self.assertEqual("192.0.2.20", resolved.context.codec_ip_address)

    def test_conflicting_room_names_continue_by_room_id_without_selecting_name(self):
        result = self.resolve(
            [
                record("PDU-1", ip_address="192.0.2.10", room_name="Room A", device_kind="pdu"),
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
            "CloudLink Bar 310": {"Статус звонка": "Вызов", "Режим презентации": "Старт"},
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


class DummySession:
    def __init__(self):
        self.invalidate_calls = 0
        self.activate_calls = []
        self.submits = []
        self.signals = type(
            "Signals",
            (),
            {
                "result": _Signal(),
                "error": _Signal(),
                "dropped": _Signal(),
            },
        )()

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
        inv = inventory(
            [
                record("PDU-1", ip_address="192.0.2.10", device_kind="pdu"),
                record("C1", ip_address="192.0.2.20", device_kind="video_codec", diagnostic_model="Huawei TE20"),
            ]
        )
        controller = self.build_controller(inv, session=session)
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
        self.assertEqual("NOT_STARTED", self.presentations[-1]["codec_diagnostic_status"])
        self.assertEqual("user_refresh_started", self.presentations[-1]["safe_message"])


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


if __name__ == "__main__":
    unittest.main()
