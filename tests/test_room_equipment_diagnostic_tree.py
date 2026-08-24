"""Offline regression tests for the room diagnostic application boundary."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch
import threading
import time

try:
    from PyQt5.QtWidgets import QApplication, QLabel, QTableWidget
except ImportError:  # pragma: no cover
    QApplication = None

from core.equipment_inventory import EquipmentInventory, EquipmentInventoryMetadata, EquipmentRecord
from core.exceptions import AuthenticationError
from core.parser import BiampTesiraForteCIDataParser, ExtronIN1804DataParser
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
            [
                OneShotEvent(OneShotEventKind.TERMINAL_FAILURE, AuthenticationError("rejected")),
                OneShotEvent(OneShotEventKind.CLEANUP_COMPLETE),
            ],
            [OneShotEvent(OneShotEventKind.USABLE_SUCCESS, {"ok": True}, credential_success=True)],
        ])
        persisted = []
        RoomDiagnosticOrchestrator(
            adapters={"codec": adapter}, credential_candidates=lambda *_: ({"id": 0}, {"id": 1}),
            ping=lambda _ip: True, persist_success=lambda evidence: persisted.append((evidence.diagnostic_model, evidence.ip_address, evidence.candidate_index)),
        ).run(session)
        self.assertEqual(2, len(adapter.calls))
        self.assertEqual([("Huawei TE40", "192.0.2.10", 1)], persisted)
        self.assertEqual(DeviceRowStatus.CONNECTED, session.row_for("a").status)

    def test_authentication_cleanup_timeout_does_not_start_next_candidate_but_continues_next_row(self):
        session = self._session([record("a"), record("b", ip="192.0.2.11")])
        adapter = _Adapter([
            [
                OneShotEvent(OneShotEventKind.TERMINAL_FAILURE, AuthenticationError("rejected")),
                OneShotEvent(OneShotEventKind.CLEANUP_TIMEOUT),
            ],
            [OneShotEvent(OneShotEventKind.USABLE_SUCCESS, {"serial": "B"}, credential_success=True)],
        ])
        persisted = []
        RoomDiagnosticOrchestrator(
            adapters={"codec": adapter}, credential_candidates=lambda *_: ({"id": 0}, {"id": 1}),
            ping=lambda _ip: True, persist_success=lambda evidence: persisted.append(evidence),
        ).run(session)
        self.assertEqual([("a", 0), ("b", 0)], [(call.record_id, call.credential["id"]) for call in adapter.calls])
        self.assertEqual(DeviceRowStatus.FAILED, session.row_for("a").status)
        self.assertEqual(DeviceRowStatus.CONNECTED, session.row_for("b").status)
        self.assertEqual([0], [item.candidate_index for item in persisted])

    def test_authentication_false_fallback_cleanup_does_not_start_next_candidate(self):
        class AbandoningAdapter(_Adapter):
            def cleanup(self, _context):
                return False

        session = self._session([record("a")])
        adapter = AbandoningAdapter([[OneShotEvent(OneShotEventKind.TERMINAL_FAILURE, AuthenticationError("rejected"))]])
        RoomDiagnosticOrchestrator(
            adapters={"codec": adapter}, credential_candidates=lambda *_: ({"id": 0}, {"id": 1}), ping=lambda _ip: True,
        ).run(session)
        self.assertEqual([0], [call.credential["id"] for call in adapter.calls])
        self.assertEqual(DeviceRowStatus.FAILED, session.row_for("a").status)

    def test_authentication_lookalike_text_never_advances_candidate(self):
        for text in ("auth", "401", "403"):
            with self.subTest(text=text):
                session = self._session([record("a")])
                adapter = _Adapter([[OneShotEvent(OneShotEventKind.TERMINAL_FAILURE, RuntimeError(text))]])
                RoomDiagnosticOrchestrator(
                    adapters={"codec": adapter}, credential_candidates=lambda *_: ({"id": 0}, {"id": 1}), ping=lambda _ip: True,
                ).run(session)
                self.assertEqual(1, len(adapter.calls))

    def test_saved_starting_index_uses_only_remaining_candidate_suffix(self):
        session = self._session([record("a")])
        adapter = _Adapter([[OneShotEvent(OneShotEventKind.TERMINAL_FAILURE, AuthenticationError("rejected"))]])
        RoomDiagnosticOrchestrator(
            adapters={"codec": adapter}, credential_candidates=lambda *_: ({"id": 0}, {"id": 1}),
            starting_index=lambda *_: 1, ping=lambda _ip: True,
        ).run(session)
        self.assertEqual([1], [call.credential["id"] for call in adapter.calls])
        self.assertEqual(DeviceRowStatus.FAILED, session.row_for("a").status)

    def test_non_auth_failure_does_not_advance_candidate_chain(self):
        session = self._session([record("a")])
        adapter = _Adapter([[OneShotEvent(OneShotEventKind.TERMINAL_FAILURE, failure_reason="Безопасная ошибка")]])
        RoomDiagnosticOrchestrator(
            adapters={"codec": adapter}, credential_candidates=lambda *_: ({"id": 0}, {"id": 1}), ping=lambda _ip: True,
        ).run(session)
        self.assertEqual(1, len(adapter.calls))
        self.assertEqual("Безопасная ошибка", session.row_for("a").failure_reason)

    def test_ping_failure_prevents_adapter_acquisition_and_queue_continues(self):
        session = self._session([record("a"), record("b", ip="192.0.2.11")])
        adapter = _Adapter([[OneShotEvent(OneShotEventKind.USABLE_SUCCESS, {"serial": "B"})]])
        RoomDiagnosticOrchestrator(
            adapters={"codec": adapter}, credential_candidates=lambda *_: ({"id": 0},),
            ping=lambda ip: ip.endswith("11"),
        ).run(session)
        self.assertEqual(DeviceRowStatus.FAILED, session.row_for("a").status)
        self.assertEqual(["b"], [call.record_id for call in adapter.calls])

    def test_pcs4i_forms_credentialless_plan_before_ping(self):
        inv = inventory(record("pdu", model="Extron IPL T PCS4i"))
        source = resolve_room_source(inv, "192.0.2.10", CAPS)
        session = build_room_session(inventory=inv, source=source, generation=3, capabilities=CAPS)
        adapter = _Adapter([[OneShotEvent(OneShotEventKind.USABLE_SUCCESS, {"device_info": {"model": "PCS4i"}})]])
        pings = []
        RoomDiagnosticOrchestrator(
            adapters={"pcs": adapter}, credential_candidates=lambda *_: (), ping=lambda ip: pings.append(ip) or True,
        ).run(session)
        self.assertEqual(["192.0.2.10"], pings)
        self.assertIsNone(adapter.calls[0].credential)

    def test_partial_evidence_stays_connecting_and_never_becomes_cache_on_failure(self):
        session = self._session([record("a")])
        observed = []
        adapter = _Adapter([[
            OneShotEvent(OneShotEventKind.PARTIAL, {"serial": "partial"}),
            OneShotEvent(OneShotEventKind.TERMINAL_FAILURE, failure_reason="Безопасная ошибка"),
        ]])
        RoomDiagnosticOrchestrator(
            adapters={"codec": adapter}, credential_candidates=lambda *_: ({"id": 0},), ping=lambda _ip: True,
            on_update=lambda state: observed.append((state.row_for("a").status, state.row_for("a").partial_data)),
        ).run(session)
        row = session.row_for("a")
        self.assertIn((DeviceRowStatus.CONNECTING, {"serial": "partial"}), observed)
        self.assertIsNone(row.accepted_snapshot)
        self.assertEqual(DeviceRowStatus.FAILED, row.status)

    def test_ineligible_rows_are_visible_and_perform_zero_adapter_io(self):
        source = record("source", ip="192.0.2.9")
        missing_ip = record("missing", ip=None)
        duplicate = record("duplicate")
        duplicate_peer = record("duplicate-peer")
        inv = inventory(source, missing_ip, duplicate, duplicate_peer)
        session = build_room_session(
            inventory=inv, source=resolve_room_source(inv, source.ip_address, CAPS), generation=3, capabilities=CAPS,
        )
        adapter = _Adapter([])
        RoomDiagnosticOrchestrator(adapters={"codec": adapter}, credential_candidates=lambda *_: ({"id": 0},), ping=lambda _ip: True).run(session)
        self.assertEqual(["source"], [call.record_id for call in adapter.calls])
        self.assertEqual(DeviceRowStatus.MISSING_IP, session.row_for("missing").status)
        self.assertEqual(DeviceRowStatus.AMBIGUOUS_IP, session.row_for("duplicate").status)

    def test_clock_and_problem_summary_are_finalized_after_room_queue(self):
        session = self._session([record("a")])
        RoomDiagnosticOrchestrator(
            adapters={"codec": _Adapter([[OneShotEvent(OneShotEventKind.USABLE_SUCCESS, {"serial": "A"})]])},
            credential_candidates=lambda *_: ({"id": 0},), ping=lambda _ip: True, clock=lambda: "finished",
        ).run(session)
        self.assertEqual(RoomCycleStatus.COMPLETE, session.status)
        self.assertEqual("finished", session.completion_timestamp)

    def test_warning_is_usable_but_does_not_persist_new_credential(self):
        session = self._session([record("a")])
        adapter = _Adapter([[
            OneShotEvent(OneShotEventKind.USABLE_SUCCESS_WITH_WARNING, {"https": "ok"}, "SSH unavailable", credential_success=False),
        ]])
        persisted = []
        RoomDiagnosticOrchestrator(
            adapters={"codec": adapter}, credential_candidates=lambda *_: ({"id": 0},), ping=lambda _ip: True,
            persist_success=lambda evidence: persisted.append(evidence),
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

    def test_cleanup_timeout_never_persists_new_successful_credential(self):
        session = self._session([record("a")])
        adapter = _Adapter([[
            OneShotEvent(OneShotEventKind.USABLE_SUCCESS, {"serial": "A"}, credential_success=True),
            OneShotEvent(OneShotEventKind.CLEANUP_TIMEOUT),
            OneShotEvent(OneShotEventKind.CLEANUP_COMPLETE),
        ]])
        persisted = []
        RoomDiagnosticOrchestrator(
            adapters={"codec": adapter}, credential_candidates=lambda *_: ({"id": 0},), ping=lambda _ip: True,
            persist_success=lambda evidence: persisted.append((evidence.diagnostic_model, evidence.ip_address, evidence.candidate_index)),
        ).run(session)
        self.assertEqual(DeviceRowStatus.DEGRADED, session.row_for("a").status)
        self.assertEqual([], persisted)

    def test_cleanup_complete_persists_successful_credential_once(self):
        session = self._session([record("a")])
        adapter = _Adapter([[
            OneShotEvent(OneShotEventKind.USABLE_SUCCESS, {"serial": "A"}, credential_success=True),
            OneShotEvent(OneShotEventKind.CLEANUP_COMPLETE),
        ]])
        persisted = []
        RoomDiagnosticOrchestrator(
            adapters={"codec": adapter}, credential_candidates=lambda *_: ({"id": 0},), ping=lambda _ip: True,
            persist_success=lambda evidence: persisted.append((evidence.diagnostic_model, evidence.ip_address, evidence.candidate_index)),
        ).run(session)
        self.assertEqual([("Huawei TE40", "192.0.2.10", 0)], persisted)

    def test_invalidation_at_cleanup_persistence_boundary_never_persists(self):
        session = self._session([record("a")])
        persisted = []

        class BoundaryAdapter(_Adapter):
            def cleanup(self, _context):
                session.invalidate()
                return True

        adapter = BoundaryAdapter([[
            OneShotEvent(OneShotEventKind.USABLE_SUCCESS, {"serial": "A"}, credential_success=True),
        ]])
        RoomDiagnosticOrchestrator(
            adapters={"codec": adapter}, credential_candidates=lambda *_: ({"id": 0},), ping=lambda _ip: True,
            persist_success=lambda evidence: persisted.append(evidence),
        ).run(session)
        self.assertEqual([], persisted)

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

    def test_post_thread_start_invalidation_prevents_matrix_and_codec_handler_acquisition(self):
        from core.room_diagnostic_tree import OneShotAttemptContext
        from gui.room_one_shot_adapters import WorkerOneShotAdapter, _codec_worker, _matrix_worker

        def assert_post_start_abort(factory, model, handler_patch):
            current = True
            checks = 0
            check_lock = threading.Lock()
            worker_guard = threading.Event()
            resume_worker = threading.Event()

            def is_current():
                nonlocal checks
                with check_lock:
                    checks += 1
                    pause_here = checks == 3  # two adapter checks precede Thread.start().
                if pause_here:
                    worker_guard.set()
                    self.assertTrue(resume_worker.wait(1.0))
                with check_lock:
                    return current

            context = OneShotAttemptContext(
                self._session([record("a")]).identity,
                "a", model, "192.0.2.10", 1, {"username": "u", "password": "p"}, is_current=is_current,
            )
            events = []
            with patch(handler_patch) as handler:
                thread = threading.Thread(
                    target=lambda: events.extend(WorkerOneShotAdapter(factory).run(context)), daemon=True,
                )
                thread.start()
                self.assertTrue(worker_guard.wait(1.0))
                with check_lock:
                    current = False
                resume_worker.set()
                thread.join(1.0)
                self.assertFalse(thread.is_alive())
                handler.assert_not_called()
            self.assertEqual([], events)

        assert_post_start_abort(_matrix_worker, "Extron IN1804", "core.workers.matrix.ExtronIN1804Handler")
        assert_post_start_abort(_codec_worker, "Huawei TE40", "core.workers.codec_polling.HuaweiTE40Handler")

    def test_matrix_invalidation_after_handler_construction_skips_connect(self):
        from core.workers.matrix import ExtronIN1804Worker

        constructed = threading.Event()
        release_constructor = threading.Event()
        current = True

        class Handler:
            def __init__(self, **_kwargs):
                constructed.set()
                self.connect_calls = 0
                self.disconnected = False
                self.log_callback = None
                self._release = release_constructor
                if not self._release.wait(1.0):
                    raise AssertionError("test did not release matrix handler construction")

            def connect(self):
                self.connect_calls += 1

            def disconnect(self):
                self.disconnected = True

        with patch("core.workers.matrix.ExtronIN1804Handler", Handler):
            worker = ExtronIN1804Worker(
                "192.0.2.10", username="u", password="p", is_current=lambda: current,
            )
            thread = threading.Thread(target=worker.run, daemon=True)
            thread.start()
            self.assertTrue(constructed.wait(1.0))
            current = False
            release_constructor.set()
            thread.join(1.0)
        self.assertFalse(thread.is_alive())
        self.assertEqual(0, worker.handler.connect_calls)

    def test_post_thread_start_invalidation_prevents_biamp_and_dmp_handler_acquisition(self):
        from core.worker import BiampTesiraForteCIWorker, ExtronDMP64PlusMeterWorker

        def stale_after_worker_starts(worker, handler_patch):
            current = True
            entered_guard = threading.Event()
            release_guard = threading.Event()

            def is_current():
                entered_guard.set()
                self.assertTrue(release_guard.wait(1.0))
                return current

            worker.is_current = is_current
            with patch(handler_patch) as handler:
                thread = threading.Thread(target=worker.run, daemon=True)
                thread.start()
                self.assertTrue(entered_guard.wait(1.0))
                current = False
                release_guard.set()
                thread.join(1.0)
                self.assertFalse(thread.is_alive())
                handler.assert_not_called()

        stale_after_worker_starts(
            BiampTesiraForteCIWorker("192.0.2.20", username="u", password="p"),
            "handlers.biamp.tesira_forte_ci.BiampTesiraForteCIHandler",
        )
        dmp_factory = Mock()
        dmp_guard_entered = threading.Event()
        dmp_resume = threading.Event()
        dmp_current = True

        def dmp_is_current():
            dmp_guard_entered.set()
            self.assertTrue(dmp_resume.wait(1.0))
            return dmp_current

        dmp_worker = ExtronDMP64PlusMeterWorker(
            "192.0.2.64", username="u", password="p", handler_factory=dmp_factory,
            max_cycles=1, is_current=dmp_is_current,
        )
        dmp_thread = threading.Thread(target=dmp_worker.run, daemon=True)
        dmp_thread.start()
        self.assertTrue(dmp_guard_entered.wait(1.0))
        dmp_current = False
        dmp_resume.set()
        dmp_thread.join(1.0)
        self.assertFalse(dmp_thread.is_alive())
        dmp_factory.assert_not_called()

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

    def test_slow_acquisition_is_not_a_cleanup_timeout(self):
        from core.room_diagnostic_tree import OneShotAttemptContext, RoomCleanupPolicy
        from core.workers.common import WorkerSignals
        from gui.room_one_shot_adapters import WorkerOneShotAdapter

        class SlowAcquisitionWorker:
            def __init__(self):
                self.signals = WorkerSignals()

            def run(self):
                time.sleep(0.02)
                self.signals.result.emit({"serial": "A"})

        context = OneShotAttemptContext(
            RoomDiagnosticSessionIdentity("snapshot", 1, "192.0.2.10", "a", "room"),
            "a", "Huawei TE40", "192.0.2.10", 1, {"id": 0}, is_current=lambda: True,
        )
        events = list(WorkerOneShotAdapter(
            lambda _context: SlowAcquisitionWorker(), cleanup_policy=RoomCleanupPolicy(0.001)
        ).run(context))
        self.assertEqual(
            [OneShotEventKind.USABLE_SUCCESS, OneShotEventKind.CLEANUP_COMPLETE],
            [event.kind for event in events],
        )

    def test_worker_adapter_streams_partial_before_terminal_retirement(self):
        from core.room_diagnostic_tree import OneShotAttemptContext
        from core.workers.common import WorkerSignals
        from gui.room_one_shot_adapters import WorkerOneShotAdapter

        allow_terminal = threading.Event()

        class StreamingWorker:
            def __init__(self):
                self.signals = WorkerSignals()

            def run(self):
                self.signals.result.emit({"serial": "partial", "_partial_update": True})
                allow_terminal.wait(0.5)
                self.signals.result.emit({"serial": "final"})

        context = OneShotAttemptContext(
            RoomDiagnosticSessionIdentity("snapshot", 1, "192.0.2.10", "a", "room"),
            "a", "Huawei TE40", "192.0.2.10", 1, {"id": 0}, is_current=lambda: True,
        )
        stream = iter(WorkerOneShotAdapter(lambda _context: StreamingWorker()).run(context))
        self.assertEqual(OneShotEventKind.PARTIAL, next(stream).kind)
        allow_terminal.set()
        self.assertEqual(
            [OneShotEventKind.USABLE_SUCCESS, OneShotEventKind.CLEANUP_COMPLETE],
            [event.kind for event in stream],
        )

    def test_terminal_result_then_hanging_retirement_times_out(self):
        from core.room_diagnostic_tree import OneShotAttemptContext, RoomCleanupPolicy
        from core.workers.common import WorkerSignals
        from gui.room_one_shot_adapters import WorkerOneShotAdapter

        class HangingRetirementWorker:
            def __init__(self):
                self.signals = WorkerSignals()

            def run(self):
                self.signals.result.emit({"serial": "A"})
                time.sleep(0.05)

        context = OneShotAttemptContext(
            RoomDiagnosticSessionIdentity("snapshot", 1, "192.0.2.10", "a", "room"),
            "a", "Huawei TE40", "192.0.2.10", 1, {"id": 0}, is_current=lambda: True,
        )
        events = list(WorkerOneShotAdapter(
            lambda _context: HangingRetirementWorker(), cleanup_policy=RoomCleanupPolicy(0.001)
        ).run(context))
        self.assertEqual(
            [OneShotEventKind.USABLE_SUCCESS, OneShotEventKind.CLEANUP_TIMEOUT],
            [event.kind for event in events],
        )

    def test_polycom_worker_signal_boundary_keeps_https_success_with_warning(self):
        from core.room_diagnostic_tree import OneShotAttemptContext
        from core.workers.common import WorkerSignals
        from gui.room_one_shot_adapters import WorkerOneShotAdapter

        class PolycomWorker:
            def __init__(self):
                self.signals = WorkerSignals()

            def run(self):
                self.signals.result.emit({"https": "ok", "_partial_update": True})
                self.signals.error.emit(("connection_error", "optional ssh unavailable", ""))

        session = self._session([record("a")])
        context = OneShotAttemptContext(session.identity, "a", "Polycom RPG 310", "192.0.2.10", 1, {"id": 0}, is_current=lambda: True)
        events = list(WorkerOneShotAdapter(lambda _context: PolycomWorker(), polycom=True).run(context))
        self.assertEqual(OneShotEventKind.USABLE_SUCCESS_WITH_WARNING, events[-2].kind)
        self.assertEqual({"https": "ok", "_partial_update": True}, events[-2].data)
        self.assertFalse(events[-2].credential_success)


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

    def test_automatic_room_pdu_path_does_not_call_legacy_enrichment_callback(self):
        from gui.main_window import VCSDiagnosticApp
        from unittest.mock import patch

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window._on_pdu_refresh_accepted_for_enrichment = Mock()
        pdu = record("pdu", model="Extron IPL T PCS4i")
        inv = inventory(pdu)
        pdu_caps = {
            "Extron IPL T PCS4i": RoomModelCapability(
                "Extron IPL T PCS4i", "pdu", "pdu_pcs4i", "pdu_one_shot", credentialless_allowed=True,
            ),
        }
        session = build_room_session(
            inventory=inv,
            source=resolve_room_source(inv, pdu.ip_address, pdu_caps),
            generation=3,
            capabilities=pdu_caps,
        )
        window.room_diagnostic_session = session
        adapter = _Adapter([[OneShotEvent(OneShotEventKind.USABLE_SUCCESS, {"device_info": {"model": "PCS4i"}})]])
        with patch("gui.room_diagnostic_controller.build_room_one_shot_adapters", return_value={"pdu_one_shot": adapter}):
            window.room_diagnostic_controller._run_session(session)
        QApplication.processEvents()
        self.assertEqual(DeviceRowStatus.CONNECTED, session.row_for("pdu").status)
        window._on_pdu_refresh_accepted_for_enrichment.assert_not_called()

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
        secondary_view = widget.tree.itemWidget(widget.tree.topLevelItem(1).child(0), 0)
        primary_view = widget.tree.itemWidget(widget.tree.topLevelItem(0).child(0), 0)
        secondary_text = "\n".join(label.text() for label in secondary_view.findChildren(QLabel))
        primary_text = "\n".join(label.text() for label in primary_view.findChildren(QLabel))
        self.assertIn("Серийный номер", secondary_text)
        self.assertIn("B", secondary_text)
        self.assertIn("устарели", secondary_text)
        self.assertNotIn("B", primary_text)

    def test_read_only_presenters_use_production_matrix_dmp_and_biamp_contracts(self):
        from gui.room_diagnostic_tree import RoomReadOnlyPresentation

        row = OrchestratorTests()._session([record("a")]).row_for("a")
        matrix_snapshot = ExtronIN1804DataParser.parse({
            "device_info": {"model": "IN1804", "temperature": 41},
            "inputs_num": 2,
            "outputs_num": 1,
            "input_names": ["Laptop", "Wireless"],
            "output_names": ["Display"],
            "connection_protocol": "TCP",
            "signal_status": [
                {"input": 1, "has_signal": True, "status": "Present"},
                {"input": 2, "has_signal": False, "status": "No signal"},
            ],
            "input_hdcp_auth": ["Authenticated", "Not authenticated"],
            "input_hdcp_status": ["Enabled", "Disabled"],
            "output_hdcp": "Enabled",
            "connections": [1],
        })
        dmp_snapshot = {
            "device_info": {"model": "DMP 64 Plus", "ip_address": "192.0.2.30"},
            "meter_sections": [
                {"title": "Inputs", "channels": [{"name": "Input 1", "section": "Inputs", "oid": 1001, "available": True, "dbfs": -12.5, "raw_meter": 42, "state": "present", "normalized": 0.7, "outcome": "valid"}]},
                {"title": "Outputs", "channels": [{"name": "Output 1", "section": "Outputs", "oid": 2001, "available": False, "normalized": None, "outcome": "unavailable"}]},
            ],
        }
        biamp_snapshot = BiampTesiraForteCIDataParser.parse_raw_data({
            "device_info": {"ip_address": "192.0.2.40"},
            "signal_sources": [{"alias": "Mic Inputs", "subscription_attribute": "levels", "rows": [{"channel_number": 3, "value": -18.0, "state": "present"}]}],
        })
        cases = (
            ("pdu", {"device_info": {"model": "PDU"}, "outlets": [{"number": 1, "status": "ON", "name": "Rack"}]}, "roomPduOutlets", 1),
            ("matrix", matrix_snapshot, "roomMatrixRouting", 2),
            ("audio_dsp", dmp_snapshot, "roomAudioMeasurements", 2),
            ("audio_dsp", biamp_snapshot, "roomAudioMeasurements", 1),
        )
        for screen_key, snapshot, object_name, rows in cases:
            row.capability = RoomModelCapability("Synthetic", screen_key, "route", "adapter")
            row.accepted_snapshot = snapshot
            presentation = RoomReadOnlyPresentation(row)
            self.addCleanup(presentation.deleteLater)
            table = presentation.findChild(QTableWidget, object_name)
            self.assertIsNotNone(table)
            self.assertEqual(rows, table.rowCount())
            if screen_key == "matrix":
                self.assertEqual("Laptop", table.item(0, 1).text())
                self.assertIn("Present", table.item(0, 2).text())
                self.assertIn("Authenticated", table.item(0, 3).text())
                self.assertEqual("Активен", table.item(0, 4).text())
            elif snapshot is dmp_snapshot:
                self.assertEqual("Inputs", table.item(0, 0).text())
                self.assertEqual("Input 1", table.item(0, 1).text())
                self.assertIn("-12.5 dBFS", table.item(0, 2).text())
                self.assertIn("Недоступен", table.item(1, 2).text())
            elif snapshot is biamp_snapshot:
                self.assertEqual("Mic Inputs", table.item(0, 0).text())
                self.assertEqual("Канал 3", table.item(0, 1).text())
                self.assertIn("-18.0", table.item(0, 2).text())
                self.assertIn("present", table.item(0, 2).text())

    def test_matrix_presentation_handles_empty_real_parser_signal_status(self):
        from gui.room_diagnostic_tree import RoomReadOnlyPresentation

        snapshot = ExtronIN1804DataParser.parse({
            "device_info": {"model": "IN1804", "temperature": 40},
            "inputs_num": 8,
            "input_names": ["Input 1"],
            "signal_status": [],
            "input_hdcp_auth": [],
            "input_hdcp_status": [],
            "connections": [],
        })
        row = OrchestratorTests()._session([record("a")]).row_for("a")
        row.capability = RoomModelCapability("Extron IN1804", "matrix", "matrix", "adapter")
        row.accepted_snapshot = snapshot
        presentation = RoomReadOnlyPresentation(row)
        self.addCleanup(presentation.deleteLater)
        table = presentation.findChild(QTableWidget, "roomMatrixRouting")
        self.assertIsNotNone(table)
        self.assertEqual(8, table.rowCount())
        self.assertEqual("—", table.item(1, 1).text())
        self.assertEqual("—", table.item(0, 2).text())
        self.assertIn("—", table.item(0, 3).text())


if __name__ == "__main__":
    unittest.main()
