import threading
import unittest

from PyQt5.QtCore import QCoreApplication

from core.exceptions import (
    AuthenticationError,
    CommandOutcomeUnknownError,
    SessionInvalidError,
)
from core.interactive_session import (
    InteractiveOperation,
    InteractiveSessionController,
    OperationSemantic,
)


class FakeHandler:
    def __init__(self, kwargs, behavior, calls):
        self.kwargs = dict(kwargs)
        self.behavior = behavior
        self.calls = calls
        self.connected = False

    def connect(self):
        self.calls.append(("connect", self.kwargs["port"], self.kwargs.get("password")))
        outcome = self.behavior.get(("connect", self.kwargs["port"], self.kwargs.get("password")))
        if isinstance(outcome, list):
            outcome = outcome.pop(0) if outcome else None
        if isinstance(outcome, BaseException):
            raise outcome
        self.connected = True
        return True if outcome is None else outcome

    def disconnect(self):
        self.calls.append(("disconnect", self.kwargs["port"]))
        self.connected = False

    def is_connected(self):
        return self.connected

    def read(self):
        self.calls.append(("read", self.kwargs.get("password")))
        outcomes = self.behavior.setdefault("read", ["ok"])
        outcome = outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        if callable(outcome):
            return outcome()
        return outcome

    def set_value(self, value):
        self.calls.append(("set", value))
        outcomes = self.behavior.setdefault("set", [True])
        outcome = outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def get_value(self):
        self.calls.append(("get",))
        return self.behavior.get("current", 0)


class InteractiveSessionControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def make_controller(self, behavior=None):
        calls = []
        behavior = {} if behavior is None else behavior

        def factory(_model, kwargs):
            return FakeHandler(kwargs, behavior, calls)

        controller = InteractiveSessionController(handler_factory=factory)
        return controller, calls

    def collect(self, controller):
        results, errors, dropped = [], [], []
        controller.signals.result.connect(results.append)
        controller.signals.error.connect(errors.append)
        controller.signals.dropped.connect(dropped.append)
        return results, errors, dropped

    def drain(self):
        self.app.processEvents()

    def test_saved_profile_first_and_transport_exception_keeps_credential(self):
        behavior = {
            ("connect", 80, "one"): OSError("first transport failed"),
        }
        controller, calls = self.make_controller(behavior)
        results, errors, _ = self.collect(controller)
        controller.activate_context(
            "Huawei TE40",
            "192.0.2.10",
            ({"username": "u", "password": "one"},),
            saved_profile={"port": 80, "use_ssl": False},
        )
        controller.submit(InteractiveOperation(kind="read", method="read"))
        controller.wait_until_idle(2)
        self.drain()
        controller.shutdown()

        self.assertEqual([], errors)
        self.assertEqual("ok", results[0]["value"])
        self.assertEqual(
            [("connect", 80, "one"), ("connect", 443, "one")],
            [call for call in calls if call[0] == "connect"],
        )

    def test_confirmed_login_authentication_advances_monotonically(self):
        behavior = {
            ("connect", 443, "one"): AuthenticationError("confirmed"),
        }
        controller, calls = self.make_controller(behavior)
        results, errors, _ = self.collect(controller)
        controller.activate_context(
            "Huawei TE40",
            "192.0.2.10",
            (
                {"username": "u", "password": "one"},
                {"username": "u", "password": "two"},
            ),
        )
        controller.submit(InteractiveOperation(kind="read", method="read"))
        controller.wait_until_idle(2)
        self.drain()
        controller.shutdown()

        self.assertEqual([], errors)
        self.assertEqual(1, results[0]["credential_index"])
        self.assertNotIn(("connect", 80, "one"), calls)

    def test_session_invalid_reconnects_once_and_replays_read_once(self):
        controller, calls = self.make_controller(
            {"read": [SessionInvalidError("expired"), "recovered"]}
        )
        results, errors, _ = self.collect(controller)
        controller.activate_context(
            "CloudLink Bar 310",
            "192.0.2.10",
            ({"username": "u", "password": "one"},),
        )
        controller.submit(InteractiveOperation(kind="read", method="read"))
        controller.wait_until_idle(2)
        self.drain()
        controller.shutdown()

        self.assertEqual([], errors)
        self.assertEqual("recovered", results[0]["value"])
        self.assertEqual(2, len([call for call in calls if call[0] == "connect"]))
        self.assertEqual(2, len([call for call in calls if call[0] == "read"]))

    def test_locally_disconnected_cache_consumes_only_reconnect_cycle(self):
        controller, calls = self.make_controller(
            {"read": ["warm", SessionInvalidError("expired after reconnect")]}
        )
        results, errors, _ = self.collect(controller)
        controller.activate_context(
            "CloudLink Bar 310",
            "192.0.2.10",
            ({"username": "u", "password": "one"},),
        )
        controller.submit(InteractiveOperation(kind="warm", method="read"))
        controller.wait_until_idle(2)
        self.drain()

        controller._handler_record.handler.connected = False
        controller.submit(InteractiveOperation(kind="read", method="read"))
        controller.wait_until_idle(2)
        self.drain()
        controller.shutdown()

        self.assertEqual(["warm"], [result["value"] for result in results])
        self.assertEqual("session_invalid", errors[0]["category"])
        self.assertEqual(2, len([call for call in calls if call[0] == "connect"]))
        self.assertEqual(2, len([call for call in calls if call[0] == "read"]))

    def test_recovery_tries_same_credential_then_advances_on_confirmed_login_auth(self):
        behavior = {
            ("connect", 443, "one"): [None, AuthenticationError("rejected")],
            "read": [SessionInvalidError("expired"), "recovered"],
        }
        controller, calls = self.make_controller(behavior)
        results, errors, _ = self.collect(controller)
        controller.activate_context(
            "Huawei TE40",
            "192.0.2.10",
            (
                {"username": "u", "password": "one"},
                {"username": "u", "password": "two"},
            ),
        )
        controller.submit(InteractiveOperation(kind="read", method="read"))
        controller.wait_until_idle(2)
        self.drain()
        controller.shutdown()

        self.assertEqual([], errors)
        self.assertEqual(1, results[0]["credential_index"])
        self.assertEqual(
            ["one", "one", "two"],
            [call[2] for call in calls if call[0] == "connect"],
        )

    def test_second_session_failure_is_terminal_without_retry_loop(self):
        controller, calls = self.make_controller(
            {"read": [SessionInvalidError("first"), SessionInvalidError("second")]}
        )
        results, errors, _ = self.collect(controller)
        controller.activate_context(
            "CloudLink Bar 310",
            "192.0.2.10",
            ({"username": "u", "password": "one"},),
        )
        controller.submit(InteractiveOperation(kind="read", method="read"))
        controller.wait_until_idle(2)
        self.drain()
        controller.shutdown()

        self.assertEqual([], results)
        self.assertEqual("session_invalid", errors[0]["category"])
        self.assertEqual(2, len([call for call in calls if call[0] == "connect"]))
        self.assertEqual(2, len([call for call in calls if call[0] == "read"]))

    def test_relative_intent_is_not_blindly_replayed_after_unknown_outcome(self):
        behavior = {
            "set": [CommandOutcomeUnknownError("lost"), True],
            "current": 7,
        }
        controller, calls = self.make_controller(behavior)
        results, errors, _ = self.collect(controller)
        controller.activate_context(
            "Huawei TE40",
            "192.0.2.10",
            ({"username": "u", "password": "one"},),
        )
        controller.submit(
            InteractiveOperation(
                kind="volume_relative",
                method="set_value",
                args=(7,),
                semantic=OperationSemantic.RELATIVE_AS_ABSOLUTE,
                readback_method="get_value",
                original=6,
                target=7,
            )
        )
        controller.wait_until_idle(2)
        self.drain()
        controller.shutdown()

        self.assertEqual([], errors)
        self.assertEqual(7, results[0]["value"])
        self.assertEqual(1, len([call for call in calls if call[0] == "set"]))

    def test_desired_state_replays_only_when_readback_is_original_state(self):
        behavior = {
            "set": [CommandOutcomeUnknownError("lost"), True],
            "current": "Stop",
        }
        controller, calls = self.make_controller(behavior)
        results, errors, _ = self.collect(controller)
        controller.activate_context(
            "Huawei TE20",
            "192.0.2.10",
            ({"username": "u", "password": "one"},),
        )
        controller.submit(
            InteractiveOperation(
                kind="presentation",
                method="set_value",
                args=("Start",),
                semantic=OperationSemantic.DESIRED_STATE,
                readback_method="get_value",
                original="Stop",
                target="Start",
            )
        )
        controller.wait_until_idle(2)
        self.drain()
        controller.shutdown()

        self.assertEqual([], errors)
        self.assertTrue(results[0]["value"])
        self.assertEqual(2, len([call for call in calls if call[0] == "set"]))

    def test_ambiguous_mute_reconciles_once_from_authoritative_opposite(self):
        behavior = {
            "set": [CommandOutcomeUnknownError("lost"), True],
            "current": "Unmuted",
        }
        controller, calls = self.make_controller(behavior)
        results, errors, _ = self.collect(controller)
        controller.activate_context(
            "Huawei TE20",
            "192.0.2.10",
            ({"username": "u", "password": "one"},),
        )
        controller.submit(
            InteractiveOperation(
                kind="microphone_set",
                method="set_value",
                args=(0,),
                semantic=OperationSemantic.DESIRED_STATE,
                readback_method="get_value",
                original="Unmuted",
                target="Muted",
            )
        )
        controller.wait_until_idle(2)
        self.drain()
        controller.shutdown()

        self.assertEqual([], errors)
        self.assertTrue(results[0]["value"])
        self.assertTrue(results[0]["reconciled"])
        self.assertEqual(2, len([call for call in calls if call[0] == "set"]))

    def test_ambiguous_mute_target_already_applied_is_not_sent_twice(self):
        behavior = {
            "set": [CommandOutcomeUnknownError("lost"), True],
            "current": "Muted",
        }
        controller, calls = self.make_controller(behavior)
        results, errors, _ = self.collect(controller)
        controller.activate_context(
            "Huawei TE20",
            "192.0.2.10",
            ({"username": "u", "password": "one"},),
        )
        controller.submit(
            InteractiveOperation(
                kind="microphone_set",
                method="set_value",
                args=(0,),
                semantic=OperationSemantic.DESIRED_STATE,
                readback_method="get_value",
                original="Unmuted",
                target="Muted",
            )
        )
        controller.wait_until_idle(2)
        self.drain()
        controller.shutdown()

        self.assertEqual([], errors)
        self.assertEqual("Muted", results[0]["value"])
        self.assertEqual(1, len([call for call in calls if call[0] == "set"]))

    def test_ambiguous_mute_unknown_readback_refuses_second_send(self):
        behavior = {
            "set": [CommandOutcomeUnknownError("lost"), True],
            "current": None,
        }
        controller, calls = self.make_controller(behavior)
        results, errors, _ = self.collect(controller)
        controller.activate_context(
            "Huawei TE20",
            "192.0.2.10",
            ({"username": "u", "password": "one"},),
        )
        controller.submit(
            InteractiveOperation(
                kind="microphone_set",
                method="set_value",
                args=(0,),
                semantic=OperationSemantic.DESIRED_STATE,
                readback_method="get_value",
                original="Unmuted",
                target="Muted",
            )
        )
        controller.wait_until_idle(2)
        self.drain()
        controller.shutdown()

        self.assertEqual([], results)
        self.assertEqual("unknown_command_outcome", errors[0]["category"])
        self.assertEqual(1, len([call for call in calls if call[0] == "set"]))

    def test_unknown_readback_refuses_state_change_replay(self):
        behavior = {
            "set": [CommandOutcomeUnknownError("lost"), True],
            "current": None,
        }
        controller, calls = self.make_controller(behavior)
        results, errors, _ = self.collect(controller)
        controller.activate_context(
            "Huawei TE20",
            "192.0.2.10",
            ({"username": "u", "password": "one"},),
        )
        controller.submit(
            InteractiveOperation(
                kind="wake",
                method="set_value",
                args=("Off",),
                semantic=OperationSemantic.DESIRED_STATE,
                readback_method="get_value",
                original="On",
                target="Off",
            )
        )
        controller.wait_until_idle(2)
        self.drain()
        controller.shutdown()

        self.assertEqual([], results)
        self.assertEqual("unknown_command_outcome", errors[0]["category"])
        self.assertEqual(1, len([call for call in calls if call[0] == "set"]))

    def test_stale_queued_command_is_dropped_before_handler_acquisition(self):
        gate = threading.Event()
        release = threading.Event()
        controller, calls = self.make_controller()
        _, _, dropped = self.collect(controller)
        first_generation = controller.activate_context(
            "Huawei TE40",
            "192.0.2.10",
            ({"username": "u", "password": "one"},),
        )
        controller._executor.submit(lambda: (gate.set(), release.wait(2)))
        gate.wait(1)
        controller.submit(
            InteractiveOperation(
                kind="stale_set",
                method="set_value",
                args=(4,),
                semantic=OperationSemantic.ABSOLUTE,
            ),
            generation=first_generation,
        )
        controller.activate_context(
            "Huawei TE40",
            "192.0.2.11",
            ({"username": "u", "password": "one"},),
        )
        release.set()
        controller.wait_until_idle(2)
        self.drain()
        controller.shutdown()

        self.assertEqual([], [call for call in calls if call[0] in {"connect", "set"}])
        self.assertEqual(1, len(dropped))

    def test_duplicate_poll_is_suppressed_until_first_finishes(self):
        controller, _ = self.make_controller()
        controller.activate_context(
            "Huawei TE40",
            "192.0.2.10",
            ({"username": "u", "password": "one"},),
        )
        blocker = threading.Event()
        controller._executor.submit(lambda: blocker.wait(2))
        operation = InteractiveOperation(
            kind="live_audio",
            method="read",
            duplicate_key="live_audio",
        )
        first = controller.submit(operation)
        second = controller.submit(operation)
        blocker.set()
        controller.wait_until_idle(2)
        controller.shutdown()

        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_old_generation_cannot_release_new_duplicate_marker(self):
        first_lane_gate = threading.Event()
        first_lane_release = threading.Event()
        new_poll_started = threading.Event()
        new_poll_release = threading.Event()

        def blocking_read():
            new_poll_started.set()
            new_poll_release.wait(2)
            return "new"

        controller, _ = self.make_controller({"read": [blocking_read, "next"]})
        controller.activate_context(
            "Huawei TE40",
            "192.0.2.10",
            ({"username": "u", "password": "one"},),
        )
        controller._executor.submit(
            lambda: (first_lane_gate.set(), first_lane_release.wait(2))
        )
        first_lane_gate.wait(1)
        operation = InteractiveOperation(
            kind="live_audio",
            method="read",
            duplicate_key="live_audio",
        )
        old_poll = controller.submit(operation)

        controller.activate_context(
            "Huawei TE40",
            "192.0.2.11",
            ({"username": "u", "password": "one"},),
        )
        new_poll = controller.submit(operation)
        first_lane_release.set()
        self.assertTrue(new_poll_started.wait(1))

        overlapping_poll = controller.submit(operation)
        new_poll_release.set()
        controller.wait_until_idle(2)
        next_poll = controller.submit(operation)
        controller.wait_until_idle(2)
        controller.shutdown()

        self.assertIsNotNone(old_poll)
        self.assertIsNotNone(new_poll)
        self.assertIsNone(overlapping_poll)
        self.assertIsNotNone(next_poll)

    def test_shutdown_closes_cached_handler_on_serial_lane(self):
        controller, calls = self.make_controller()
        controller.activate_context(
            "Huawei TE40",
            "192.0.2.10",
            ({"username": "u", "password": "one"},),
        )
        controller.submit(InteractiveOperation(kind="read", method="read"))
        controller.wait_until_idle(2)
        controller.shutdown()

        self.assertIn(("disconnect", 443), calls)


if __name__ == "__main__":
    unittest.main()
