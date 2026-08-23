import unittest

from core.room_diagnostic_tree import DeviceRowState, DeviceRowStatus, RoomCycleStatus, RoomDiagnosticSession, RoomDiagnosticSessionIdentity
from core.room_interaction import RoomInteractionBindings, RoomInteractionCoordinator, RoomInteractionKind


def session():
    row_a = DeviceRowState("a", "Huawei TE20", "192.0.2.10", None, DeviceRowStatus.CONNECTED)
    row_b = DeviceRowState("b", "Huawei TE20", "192.0.2.11", None, DeviceRowStatus.CONNECTED)
    return RoomDiagnosticSession(
        RoomDiagnosticSessionIdentity("s", 1, "192.0.2.1", "a", "r"),
        None, None, None, [row_a, row_b],
        expanded_record_id="a",
        status=RoomCycleStatus.COMPLETE,
    )


class RoomInteractionCoordinatorTests(unittest.TestCase):
    def test_live_switch_latest_row_and_stale_callback_are_isolated(self):
        calls = []
        bindings = RoomInteractionBindings(live=lambda c: calls.append(("live", c)), cancel=lambda c: calls.append(("cancel", c)), cleanup=lambda _c: True)
        coordinator = RoomInteractionCoordinator(bindings_for_model=lambda _m: bindings)
        current = session(); coordinator.bind_session(current); coordinator.cycle_finished(current)
        old = coordinator.active_context
        self.assertEqual(("live", old), calls[0])
        coordinator.expand("b")
        self.assertEqual("b", coordinator.active_context.record_id)
        coordinator.complete(old, success=False, connection_lost=True)
        self.assertEqual(DeviceRowStatus.CONNECTED, current.row_for("a").status)

    def test_mutation_ack_requires_reconciliation_before_cache_replacement(self):
        mutations, reconciliations = [], []
        bindings = RoomInteractionBindings(
            mutation=lambda c, value: mutations.append((c, value)),
            reconciliation=lambda c, value: reconciliations.append((c, value)),
            cancel=lambda _c: None, cleanup=lambda _c: True,
        )
        coordinator = RoomInteractionCoordinator(bindings_for_model=lambda _m: bindings)
        current = session(); coordinator.bind_session(current)
        context = coordinator.confirm_mutation("on")
        self.assertEqual("on", mutations[0][1])
        coordinator.complete(context, success=True, data={"ack": True})
        self.assertIsNone(current.row_for("a").accepted_snapshot)
        reconciliation = reconciliations[0][0]
        self.assertIs(RoomInteractionKind.RECONCILIATION, reconciliation.kind)
        coordinator.complete(reconciliation, success=True, data={"outlets": ["confirmed"]})
        self.assertEqual({"outlets": ["confirmed"]}, current.row_for("a").accepted_snapshot)

    def test_unconfirmed_mutation_blocks_only_the_exact_row(self):
        bindings = RoomInteractionBindings(
            mutation=lambda _c, _value: None,
            cancel=lambda _c: None, cleanup=lambda _c: True,
        )
        coordinator = RoomInteractionCoordinator(bindings_for_model=lambda _m: bindings)
        current = session(); coordinator.bind_session(current)
        context = coordinator.confirm_mutation("off")
        coordinator.complete(context, success=False, unconfirmed=True)
        first, second = current.rows
        self.assertTrue(first.interaction_blocked)
        self.assertTrue(first.unconfirmed_after_command)
        self.assertFalse(first.network_actions_enabled)
        self.assertEqual(DeviceRowStatus.CONNECTED, second.status)
        self.assertFalse(second.interaction_blocked)
        self.assertTrue(current.post_cycle_problem)

    def test_cleanup_timeout_degrades_exact_row_without_replacing_other_cache(self):
        bindings = RoomInteractionBindings(
            live=lambda _c: None, cancel=lambda _c: None, cleanup=lambda _c: False,
        )
        coordinator = RoomInteractionCoordinator(bindings_for_model=lambda _m: bindings)
        current = session(); current.row_for("a").accepted_snapshot = {"old": True}
        current.row_for("b").accepted_snapshot = {"other": True}
        coordinator.bind_session(current); coordinator.cycle_finished(current)
        context = coordinator.active_context
        coordinator.cleanup_finished(context, timed_out=True)
        self.assertEqual(DeviceRowStatus.DEGRADED, current.row_for("a").status)
        self.assertTrue(current.row_for("a").stale)
        self.assertEqual({"other": True}, current.row_for("b").accepted_snapshot)

    def test_local_refresh_owns_exclusive_lane_until_terminal_result(self):
        calls = []
        bindings = RoomInteractionBindings(
            local_refresh=lambda context: calls.append(context),
            cancel=lambda _context: None,
            cleanup=lambda _context: False,
        )
        coordinator = RoomInteractionCoordinator(bindings_for_model=lambda _model: bindings)
        current = session()
        coordinator.bind_session(current)
        context = coordinator.request_local_refresh()
        self.assertEqual([context], calls)
        self.assertTrue(coordinator.has_exclusive_operation)
        self.assertFalse(current.row_for("a").network_actions_enabled)
        coordinator.complete(context, success=True, data={"serial": "new"})
        self.assertFalse(coordinator.has_exclusive_operation)
        self.assertTrue(current.row_for("a").network_actions_enabled)
        self.assertEqual({"serial": "new"}, current.row_for("a").accepted_snapshot)

    def test_auxiliary_close_cancels_exact_context_and_releases_lane(self):
        calls = []
        bindings = RoomInteractionBindings(
            auxiliary=lambda context, action: calls.append((context, action)),
            local_refresh=lambda _context: self.fail("refresh must not overlap auxiliary"),
            cancel=lambda _context: None,
            cleanup=lambda _context: True,
        )
        coordinator = RoomInteractionCoordinator(bindings_for_model=lambda _model: bindings)
        current = session()
        coordinator.bind_session(current)
        context = coordinator.request_auxiliary("call_log")
        self.assertEqual([(context, "call_log")], calls)
        self.assertTrue(coordinator.has_exclusive_operation)
        self.assertIsNone(coordinator.request_local_refresh())
        coordinator.child_window_closed(context)
        self.assertIsNone(coordinator.active_context)
        self.assertFalse(coordinator.has_exclusive_operation)

    def test_live_tick_updates_exact_cache_without_releasing_live_owner(self):
        calls = []
        bindings = RoomInteractionBindings(
            live=lambda context: calls.append(context),
            cancel=lambda _context: None,
            cleanup=lambda _context: True,
        )
        coordinator = RoomInteractionCoordinator(bindings_for_model=lambda _model: bindings)
        current = session()
        coordinator.bind_session(current)
        coordinator.cycle_finished(current)
        context = coordinator.active_context
        coordinator.complete(context, success=True, data={"meter": -12.0})
        self.assertEqual([context], calls)
        self.assertIs(context, coordinator.active_context)
        self.assertEqual({"meter": -12.0}, current.row_for("a").accepted_snapshot)
