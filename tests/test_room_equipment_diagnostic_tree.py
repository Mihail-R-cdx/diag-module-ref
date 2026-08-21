"""Offline regression tests for the room diagnostic application boundary."""

from __future__ import annotations

import unittest
from unittest.mock import Mock
import time

try:
    from PyQt5.QtWidgets import QApplication
except ImportError:  # pragma: no cover
    QApplication = None

from core.equipment_inventory import EquipmentInventory, EquipmentInventoryMetadata, EquipmentRecord
from core.exceptions import AuthenticationError
from core.room_diagnostic_tree import (
    DeviceRowStatus,
    OneShotEvent,
    OneShotEventKind,
    RoomCycleStatus,
    RoomDiagnosticOrchestrator,
    RoomDiagnosticSessionIdentity,
    RoomModelCapability,
    RoomSourceStatus,
    build_room_session,
    resolve_room_source,
)


def record(record_id, *, ip="192.0.2.10", model="Huawei TE40", room="R-1", source="Synthetic", name=None, address=None, vip=None):
    return EquipmentRecord(record_id, source, model, ip, None, None, room, name, "other", vip, address)


def inventory(*records):
    return EquipmentInventory.from_records(
        records,
        EquipmentInventoryMetadata(4, "sha256:" + "a" * 64),
    )


CAPS = {
    "Huawei TE40": RoomModelCapability("Huawei TE40", "codec", "huawei_te40", "codec"),
    "Extron IPL T PCS4i": RoomModelCapability("Extron IPL T PCS4i", "pdu", "pdu_pcs4i", "pcs", credentialless_allowed=True),
}


class SourceAndTreeTests(unittest.TestCase):
    def test_valid_inventory_source_cardinality_and_legacy_boundary(self):
        self.assertEqual(RoomSourceStatus.IP_NOT_FOUND, resolve_room_source(inventory(), "192.0.2.10", CAPS).status)
        self.assertEqual(
            RoomSourceStatus.AMBIGUOUS_SOURCE_IP,
            resolve_room_source(inventory(record("a"), record("b")), "192.0.2.10", CAPS).status,
        )
        self.assertEqual(RoomSourceStatus.INVENTORY_UNAVAILABLE, resolve_room_source(None, "192.0.2.10", CAPS).status)
        self.assertEqual(
            RoomSourceStatus.LEGACY_SINGLE_DEVICE,
            resolve_room_source(inventory(record("a", room=None)), "192.0.2.10", CAPS).status,
        )

    def test_unsupported_source_still_enters_room_and_tree_is_source_first(self):
        source = record("z-source", model="Future", name=None, address=None, vip=None)
        second = record("a-second", ip="192.0.2.11", name="Room", address="Address", vip=True)
        inv = inventory(source, second)
        resolution = resolve_room_source(inv, source.ip_address, CAPS)
        self.assertEqual(RoomSourceStatus.ROOM, resolution.status)
        session = build_room_session(inventory=inv, source=resolution, generation=1, capabilities=CAPS)
        self.assertEqual(["z-source", "a-second"], [row.record_id for row in session.rows])
        self.assertEqual(DeviceRowStatus.UNSUPPORTED, session.rows[0].status)
        self.assertEqual(("Room", "Address", True), (session.room_name, session.room_address, session.room_vip))
        self.assertIsNone(session.expanded_record_id)

    def test_duplicate_in_same_room_including_unsupported_blocks_supported_row_only_in_that_room(self):
        source = record("source", ip="192.0.2.9")
        duplicate_supported = record("duplicate-supported")
        unsupported = record("unsupported", model="Future")
        elsewhere = record("elsewhere", ip="192.0.2.12", room="R-2")
        inv = inventory(source, duplicate_supported, unsupported, elsewhere)
        session = build_room_session(inventory=inv, source=resolve_room_source(inv, source.ip_address, CAPS), generation=1, capabilities=CAPS)
        self.assertEqual(DeviceRowStatus.AMBIGUOUS_IP, session.row_for("duplicate-supported").status)
        self.assertEqual(DeviceRowStatus.UNSUPPORTED, session.row_for("unsupported").status)
        self.assertEqual("source", session.expanded_record_id)


class _Adapter:
    def __init__(self, events):
        self.events = events
        self.calls = []

    def run(self, context):
        self.calls.append(context)
        return tuple(self.events.pop(0))

    def cleanup(self, _context):
        return True


class OrchestratorTests(unittest.TestCase):
    def _session(self, rows):
        inv = inventory(*rows)
        source = resolve_room_source(inv, rows[0].ip_address, CAPS)
        return build_room_session(inventory=inv, source=source, generation=3, capabilities=CAPS)

    def test_credentials_precede_ping_and_missing_credentials_has_zero_io(self):
        session = self._session([record("a"), record("b", ip="192.0.2.11")])
        adapter = _Adapter([[OneShotEvent(OneShotEventKind.USABLE_SUCCESS, {"ok": True})]])
        pings = []
        queue = RoomDiagnosticOrchestrator(
            adapters={"codec": adapter},
            credential_candidates=lambda _m, ip: ({"username": "u"},) if ip.endswith("11") else (),
            ping=lambda ip: pings.append(ip) or True,
        )
        queue.run(session)
        self.assertEqual("Credentials не настроены", session.row_for("a").failure_reason)
        self.assertEqual(["192.0.2.11"], pings)
        self.assertEqual(1, len(adapter.calls))
        self.assertEqual(RoomCycleStatus.COMPLETE_WITH_PROBLEMS, session.status)

    def test_only_structured_authentication_error_advances_candidate_suffix(self):
        session = self._session([record("a")])
        adapter = _Adapter([
            [OneShotEvent(OneShotEventKind.TERMINAL_FAILURE, AuthenticationError("rejected"))],
            [OneShotEvent(OneShotEventKind.USABLE_SUCCESS, {"ok": True}, credential_success=True)],
        ])
        persisted = []
        RoomDiagnosticOrchestrator(
            adapters={"codec": adapter}, credential_candidates=lambda *_: ({"id": 0}, {"id": 1}),
            ping=lambda _ip: True, persist_success=lambda model, ip, index: persisted.append((model, ip, index)),
        ).run(session)
        self.assertEqual(2, len(adapter.calls))
        self.assertEqual([("Huawei TE40", "192.0.2.10", 1)], persisted)
        self.assertEqual(DeviceRowStatus.CONNECTED, session.row_for("a").status)

    def test_warning_is_usable_but_does_not_persist_new_credential(self):
        session = self._session([record("a")])
        adapter = _Adapter([[
            OneShotEvent(OneShotEventKind.USABLE_SUCCESS_WITH_WARNING, {"https": "ok"}, "SSH unavailable", credential_success=False),
        ]])
        persisted = []
        RoomDiagnosticOrchestrator(
            adapters={"codec": adapter}, credential_candidates=lambda *_: ({"id": 0},), ping=lambda _ip: True,
            persist_success=lambda *args: persisted.append(args),
        ).run(session)
        row = session.row_for("a")
        self.assertEqual(DeviceRowStatus.CONNECTED, row.status)
        self.assertEqual(["SSH unavailable"], row.warnings)
        self.assertEqual([], persisted)

    def test_cleanup_timeout_degrades_usable_snapshot_and_continues_queue(self):
        session = self._session([record("a"), record("b", ip="192.0.2.11")])
        adapter = _Adapter([
            [
                OneShotEvent(OneShotEventKind.USABLE_SUCCESS, {"a": "snapshot"}),
                OneShotEvent(OneShotEventKind.CLEANUP_TIMEOUT),
            ],
            [OneShotEvent(OneShotEventKind.USABLE_SUCCESS, {"b": "snapshot"})],
        ])
        RoomDiagnosticOrchestrator(
            adapters={"codec": adapter}, credential_candidates=lambda *_: ({"id": 0},), ping=lambda _ip: True,
        ).run(session)
        self.assertEqual(DeviceRowStatus.DEGRADED, session.row_for("a").status)
        self.assertEqual({"a": "snapshot"}, session.row_for("a").accepted_snapshot)
        self.assertEqual(DeviceRowStatus.CONNECTED, session.row_for("b").status)
        self.assertEqual(2, len(adapter.calls))
        self.assertEqual(RoomCycleStatus.COMPLETE_WITH_PROBLEMS, session.status)

    def test_invalidated_session_does_not_acquire_adapter_or_ping(self):
        session = self._session([record("a")])
        adapter = _Adapter([])
        session.invalidate()
        pings = []
        RoomDiagnosticOrchestrator(
            adapters={"codec": adapter}, credential_candidates=lambda *_: ({"id": 0},), ping=lambda ip: pings.append(ip) or True,
        ).run(session)
        self.assertEqual([], adapter.calls)
        self.assertEqual([], pings)

    def test_stale_worker_adapter_does_not_create_worker(self):
        from gui.room_one_shot_adapters import WorkerOneShotAdapter
        from core.room_diagnostic_tree import OneShotAttemptContext

        factory = Mock()
        context = OneShotAttemptContext(
            RoomDiagnosticSessionIdentity("snapshot", 1, "192.0.2.10", "a", "room"),
            "a", "Huawei TE40", "192.0.2.10", 1, {"id": 0}, is_current=lambda: False,
        )
        self.assertEqual([], list(WorkerOneShotAdapter(factory).run(context)))
        factory.assert_not_called()

    def test_worker_adapter_rechecks_before_worker_io(self):
        from core.room_diagnostic_tree import OneShotAttemptContext
        from core.workers.common import WorkerSignals
        from gui.room_one_shot_adapters import WorkerOneShotAdapter

        current = True
        worker_runs = 0

        class Worker:
            def __init__(self):
                self.signals = WorkerSignals()

            def run(self):
                nonlocal worker_runs
                worker_runs += 1

        def factory(_context):
            nonlocal current
            current = False
            return Worker()

        context = OneShotAttemptContext(
            self._session([record("a")]).identity,
            "a",
            "Huawei TE40",
            "192.0.2.10",
            1,
            {"id": 0},
            is_current=lambda: current,
        )
        self.assertEqual([], list(WorkerOneShotAdapter(factory).run(context)))
        self.assertEqual(0, worker_runs)

    def test_stale_pdu_descriptor_does_not_build_handler(self):
        from core.pdu import PDUOperationDescriptor, REFRESH, execute_pdu_refresh

        handler_factory = Mock()
        result = execute_pdu_refresh(
            descriptor=PDUOperationDescriptor(1, 1, "Aten PE8208AV", "192.0.2.10", REFRESH),
            credentials={"username": "u", "password": "p"},
            is_current=lambda _descriptor: False,
            handler_factory=handler_factory,
        )
        self.assertEqual("stale", result["_outcome"])
        handler_factory.assert_not_called()

    def test_worker_adapter_reports_bounded_abandonment_not_fake_cleanup(self):
        from core.room_diagnostic_tree import OneShotAttemptContext, RoomCleanupPolicy
        from core.workers.common import WorkerSignals
        from gui.room_one_shot_adapters import WorkerOneShotAdapter

        class HangingWorker:
            def __init__(self):
                self.signals = WorkerSignals()

            def run(self):
                time.sleep(0.05)

        context = OneShotAttemptContext(
            RoomDiagnosticSessionIdentity("snapshot", 1, "192.0.2.10", "a", "room"),
            "a", "Huawei TE40", "192.0.2.10", 1, {"id": 0}, is_current=lambda: True,
        )
        events = list(WorkerOneShotAdapter(
            lambda _context: HangingWorker(), cleanup_policy=RoomCleanupPolicy(0.001)
        ).run(context))
        self.assertEqual(OneShotEventKind.CLEANUP_TIMEOUT, events[-1].kind)


@unittest.skipIf(QApplication is None, "PyQt5 is unavailable")
class RoomGuiCompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_room_mode_builds_tree_before_background_cycle_and_locks_top_actions(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        source = record("source", ip="192.0.2.20")
        secondary = record("secondary", ip="192.0.2.21", model="Future")
        window.equipment_inventory = inventory(source, secondary)
        window.ip_entry.setText("192.0.2.20")
        window.room_diagnostic_controller.start = Mock()

        window.refresh_data()

        self.assertIs(window.room_diagnostic_tree, window.screen_container.currentWidget())
        self.assertEqual(["source", "secondary"], [
            window.room_diagnostic_tree.tree.topLevelItem(index).data(0, 256)
            for index in range(window.room_diagnostic_tree.tree.topLevelItemCount())
        ])
        self.assertFalse(window.ip_entry.isEnabled())
        self.assertFalse(window.password_btn.isEnabled())
        self.assertFalse(window.refresh_btn.isEnabled())
        self.assertFalse(window.debug_btn.isEnabled())
        window.room_diagnostic_controller.start.assert_called_once()

    def test_accordion_keeps_secondary_selection_and_exact_row_snapshots(self):
        from gui.room_diagnostic_tree import RoomDiagnosticTreeWidget

        session = OrchestratorTests()._session([
            record("a"), record("b", ip="192.0.2.11"),
        ])
        session.row_for("a").accepted_snapshot = {"serial": "A"}
        session.row_for("b").accepted_snapshot = {"serial": "B"}
        session.row_for("b").stale = True
        widget = RoomDiagnosticTreeWidget()
        self.addCleanup(widget.deleteLater)
        widget.render(session)
        secondary = widget.tree.topLevelItem(1)
        secondary.setExpanded(True)
        QApplication.processEvents()
        self.assertEqual("b", session.expanded_record_id)
        widget.render(session)
        self.assertTrue(widget.tree.topLevelItem(1).isExpanded())
        self.assertIn("serial: B", widget.tree.topLevelItem(1).child(0).text(0))
        self.assertIn("устарели", widget.tree.topLevelItem(1).child(0).text(0))
        self.assertNotIn("serial: B", widget.tree.topLevelItem(0).child(0).text(0))


if __name__ == "__main__":
    unittest.main()
