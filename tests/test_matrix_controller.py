import os
import threading
import unittest
from types import MappingProxyType
from unittest.mock import patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtWidgets import QApplication
except ImportError:
    QApplication = None


class CapturingThreadPool:
    def __init__(self):
        self.runnables = []

    def start(self, runnable):
        self.runnables.append(runnable)


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class MatrixControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_controller(self, *, ip="192.0.2.10", revision=1, candidates=None, retirement_timeout_seconds=5.0):
        from gui.matrix_controller import MatrixController

        pool = CapturingThreadPool()
        state = {
            "model": "Extron IN1804",
            "ip": ip,
            "revision": revision,
            "candidates": tuple(
                candidates
                or (
                    {"username": "synthetic-user", "password": "synthetic-pass"},
                    {"username": "synthetic-user-2", "password": "synthetic-pass-2"},
                )
            ),
            "index": 0,
        }
        controller = MatrixController(
            context_provider=lambda: (state["model"], state["ip"]),
            credential_candidates_provider=lambda _model, _ip: state["candidates"],
            credential_index_provider=lambda _model, _ip, _candidates: state["index"],
            credential_advance_provider=lambda _model, _ip, candidates, current, _op: (
                current + 1 if current + 1 < len(tuple(candidates or ())) else None
            ),
            credential_revision_provider=lambda: state["revision"],
            thread_pool=pool,
            retirement_timeout_seconds=retirement_timeout_seconds,
        )
        return controller, state, pool

    def test_route_intent_submits_background_operation_without_direct_send(self):
        controller, state, pool = self.make_controller()
        controller.request_route(1, 4)

        self.assertEqual(1, len(pool.runnables))
        context = pool.runnables[0].context
        self.assertEqual("route", context.operation_kind)
        self.assertTrue(context.state_changing)
        self.assertEqual(1, context.output_num)
        self.assertEqual(4, context.input_num)

    def test_stale_result_is_suppressed(self):
        controller, state, _pool = self.make_controller()
        accepted = []
        controller.resultAccepted.connect(lambda data, handle: accepted.append((data, handle)))

        stale = controller._make_context(
            operation_kind="full_refresh",
            ip_address="192.0.2.10",
            candidate_index=0,
            state_changing=False,
        )
        state["ip"] = "192.0.2.11"
        controller._make_context(
            operation_kind="full_refresh",
            ip_address="192.0.2.11",
            candidate_index=0,
            state_changing=False,
        )

        controller._on_result(stale, {"model": "old"})
        self.assertEqual([], accepted)

    def test_public_handle_does_not_carry_credential_candidates(self):
        controller, _state, _pool = self.make_controller()
        accepted = []
        controller.resultAccepted.connect(lambda data, handle: accepted.append(handle))

        current = controller._make_context(
            operation_kind="full_refresh",
            ip_address="192.0.2.10",
            candidate_index=0,
            state_changing=False,
        )
        controller._on_result(current, {"model": "IN1804"})

        self.assertEqual(1, len(accepted))
        self.assertEqual((), accepted[0].creds_list)
        self.assertFalse(hasattr(accepted[0], "username"))
        self.assertFalse(hasattr(accepted[0], "password"))

    def test_protocol_failure_publishes_terminal_state_before_retirement_and_gates_next_acquisition(self):
        """Logical completion is immediate, but conflicting I/O waits for retirement."""
        from core.exceptions import ProtocolError

        controller, state, pool = self.make_controller()
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        errors, finished, instances = [], [], []
        disconnect_entered, release_disconnect = threading.Event(), threading.Event()
        controller.errorAccepted.connect(lambda error, _handle: errors.append(error))
        controller.finishedAccepted.connect(lambda _handle: finished.append(True))

        class BlockingProtocolHandler:
            def __init__(self, **kwargs):
                self.log_callback = None
                self.connected = False
                self.username = kwargs["username"]
                instances.append(self)

            def connect(self):
                self.connected = True

            def is_connected(self):
                return self.connected

            def get_full_status(self):
                raise ProtocolError("malformed exact identity")

            def disconnect(self):
                disconnect_entered.set()
                release_disconnect.wait(1)
                self.connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", BlockingProtocolHandler):
            failed = controller._make_context(
                operation_kind="full_refresh", ip_address="192.0.2.10",
                candidate_index=0, state_changing=False,
            )
            controller._run_background_operation(failed)

            self.assertEqual(["protocol_error"], [error[0] for error in errors])
            self.assertEqual([True], finished)
            self.assertIsNone(controller._session_handler)
            self.assertEqual(1, len(instances))
            self.assertEqual(1, len(pool.runnables))

            cleanup_thread = threading.Thread(target=pool.runnables.pop().run)
            cleanup_thread.start()
            self.assertTrue(disconnect_entered.wait(0.2))

            next_context = controller._make_context(
                operation_kind="quick_refresh", ip_address="192.0.2.10",
                candidate_index=0, state_changing=False,
            )
            acquired = []
            acquire_thread = threading.Thread(
                target=lambda: acquired.append(controller._acquire_session(next_context, ()))
            )
            acquire_thread.start()
            acquire_thread.join(0.05)
            self.assertTrue(acquire_thread.is_alive())
            self.assertEqual(1, len(instances))
            self.assertEqual(0, state["index"])

            release_disconnect.set()
            cleanup_thread.join(1)
            acquire_thread.join(1)
            self.assertFalse(cleanup_thread.is_alive())
            self.assertFalse(acquire_thread.is_alive())
            next_handler = acquired[0]
            self.assertIsNot(instances[0], next_handler)
            self.assertIs(next_handler, controller._session_handler)
            self.assertEqual(2, len(instances))

    def test_retirement_waiter_superseded_before_release_never_constructs_handler(self):
        """A waiter that becomes stale at the barrier has no acquisition authority."""
        controller, _state, _pool = self.make_controller()
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        wait_entered = threading.Event()
        constructed, results, errors = [], [], []
        controller.resultAccepted.connect(lambda data, _handle: results.append(data))
        controller.errorAccepted.connect(lambda error, _handle: errors.append(error))

        class ObservedBarrier(threading.Event):
            def wait(self, timeout=None):
                wait_entered.set()
                return super().wait(timeout)

        class Handler:
            def __init__(self, **_kwargs):
                constructed.append(self)

        with patch("gui.matrix_controller.ExtronIN1804Handler", Handler):
            waiter = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            barrier = ObservedBarrier()
            key = controller._retirement_key(waiter)
            with controller._retirement_lock:
                controller._retirement_events[key] = barrier

            waiter_thread = threading.Thread(
                target=controller._run_background_operation,
                args=(waiter,),
            )
            waiter_thread.start()
            self.assertTrue(wait_entered.wait(1))

            replacement = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._complete_retirement(key, barrier)
            waiter_thread.join(1)
            self.app.processEvents()

        self.assertFalse(waiter_thread.is_alive())
        self.assertEqual([], constructed)
        self.assertEqual([], results)
        self.assertEqual([], errors)
        self.assertIsNone(controller._session_handler)
        self.assertIs(controller._active_context, replacement)

    def test_read_only_acquisition_fails_closed_after_retirement_timeout(self):
        from core.exceptions import ProtocolError

        controller, state, pool = self.make_controller(retirement_timeout_seconds=0.001)
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        errors, instances = [], []
        controller.errorAccepted.connect(lambda error, _handle: errors.append(error))

        class HangingCleanupHandler:
            def __init__(self, **_kwargs):
                self.log_callback = None
                self.connected = False
                instances.append(self)

            def connect(self):
                self.connected = True

            def is_connected(self):
                return self.connected

            def get_full_status(self):
                raise ProtocolError("bad identity")

            def disconnect(self):
                pass

        with patch("gui.matrix_controller.ExtronIN1804Handler", HangingCleanupHandler):
            failed = controller._make_context(
                operation_kind="full_refresh", ip_address="192.0.2.10",
                candidate_index=0, state_changing=False,
            )
            controller._run_background_operation(failed)
            self.assertEqual(1, len(pool.runnables))

            next_context = controller._make_context(
                operation_kind="full_refresh", ip_address="192.0.2.10",
                candidate_index=0, state_changing=False,
            )
            controller._run_background_operation(next_context)

        self.assertEqual(1, len(instances))
        self.assertEqual(["protocol_error", "connection_error"], [error[0] for error in errors])
        self.assertIsNone(controller._session_handler)

    def test_stale_callbacks_are_suppressed_for_all_public_channels(self):
        controller, state, pool = self.make_controller()
        accepted = {
            "result": [],
            "error": [],
            "progress": [],
            "status": [],
            "terminal": [],
            "finished": [],
            "route": [],
            "route_error": [],
        }
        controller.resultAccepted.connect(lambda *args: accepted["result"].append(args))
        controller.errorAccepted.connect(lambda *args: accepted["error"].append(args))
        controller.progressAccepted.connect(lambda *args: accepted["progress"].append(args))
        controller.statusAccepted.connect(lambda *args: accepted["status"].append(args))
        controller.terminalAccepted.connect(lambda *args: accepted["terminal"].append(args))
        controller.finishedAccepted.connect(lambda *args: accepted["finished"].append(args))
        controller.routeAccepted.connect(accepted["route"].append)
        controller.routeError.connect(accepted["route_error"].append)

        stale = controller._make_context(
            operation_kind="route",
            ip_address="192.0.2.10",
            candidate_index=0,
            output_num=1,
            input_num=2,
            state_changing=True,
        )
        state["ip"] = "192.0.2.11"
        current = controller._make_context(
            operation_kind="full_refresh",
            ip_address="192.0.2.11",
            candidate_index=0,
            state_changing=False,
        )
        cleanup = controller._make_cleanup_context()

        controller._on_result(stale, {"route_input": 2})
        controller._on_error(stale, ("authentication_error", "rejected", ""))
        controller._on_progress(stale, 50)
        controller._on_status(stale, "old")
        controller._on_terminal(stale, "old terminal")
        controller._on_finished(stale)
        controller._on_finished(cleanup)

        self.assertEqual({key: [] for key in accepted}, accepted)
        self.assertIs(current, controller._active_context)
        self.assertEqual([], pool.runnables)

    def test_session_identity_includes_ip_candidate_and_credential_revision(self):
        controller, state, pool = self.make_controller()
        events = []

        class Handler:
            def __init__(self, **kwargs):
                events.append(("init", kwargs["ip_address"], kwargs["username"]))
                self.log_callback = None
                self.connected = False

            def connect(self):
                events.append(("connect", None, None))
                self.connected = True

            def is_connected(self):
                return self.connected

            def disconnect(self):
                events.append(("disconnect", None, None))
                self.connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", Handler):
            first = controller._make_context(
                operation_kind="full_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            first_handler = controller._acquire_session(first, ())
            same = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            self.assertIs(first_handler, controller._acquire_session(same, ()))

            state["revision"] = 2
            revised = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            pool.runnables.pop().run()
            revised_handler = controller._acquire_session(revised, ())

            state["ip"] = "192.0.2.11"
            different_ip = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.11",
                candidate_index=0,
                state_changing=False,
            )
            pool.runnables.pop().run()
            different_handler = controller._acquire_session(different_ip, ())

        self.assertIsNot(first_handler, revised_handler)
        self.assertIsNot(revised_handler, different_handler)
        self.assertEqual(3, len([event for event in events if event[0] == "init"]))
        self.assertGreaterEqual(
            len([event for event in events if event[0] == "disconnect"]),
            2,
        )
        self.assertEqual([], pool.runnables)

    def test_same_ip_model_replacement_retires_old_session_and_constructs_exact_new_model(self):
        controller, state, pool = self.make_controller()
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        expected_models, instances = [], []

        class Handler:
            def __init__(self, **kwargs):
                expected_models.append(kwargs["expected_model"])
                self.connected = False
                self.log_callback = None
                instances.append(self)

            def connect(self):
                self.connected = True

            def is_connected(self):
                return self.connected

            def disconnect(self):
                self.connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", Handler):
            first = controller._make_context(
                operation_kind="full_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            first_handler = controller._acquire_session(first, ())
            self.assertEqual("Extron IN1804", controller._session_identity.model)

            state["model"] = "Extron DTP CrossPoint 108 4K"
            replacement = controller._make_context(
                operation_kind="full_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            self.assertEqual("Extron DTP CrossPoint 108 4K", replacement.model)
            self.assertIs(first_handler, controller._session_handler)
            retirement = next(
                runnable for runnable in pool.runnables
                if runnable.context.operation_kind == "retirement"
            )
            self.assertEqual("Extron IN1804", retirement.context.model)
            retirement.run()

            replacement_handler = controller._acquire_session(replacement, ())

        self.assertIsNot(first_handler, replacement_handler)
        self.assertEqual(
            ["Extron IN1804", "Extron DTP CrossPoint 108 4K"], expected_models
        )
        self.assertEqual("Extron DTP CrossPoint 108 4K", controller._session_identity.model)

    def test_persistent_handler_access_is_serialized_for_overlapping_operations(self):
        controller, state, pool = self.make_controller()
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        entered_first = threading.Event()
        release_first = threading.Event()
        entered_route = threading.Event()
        calls = []

        class Handler:
            def __init__(self, **_kwargs):
                self.log_callback = None
                self.connected = True

            def connect(self):
                self.connected = True

            def is_connected(self):
                return self.connected

            def get_connections(self):
                calls.append("quick")
                entered_first.set()
                release_first.wait(2)
                return [1]

            def set_connection(self, output_num, input_num):
                calls.append(("route", output_num, input_num))
                entered_route.set()

            def disconnect(self):
                self.connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", Handler):
            first = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._submit(first, state["candidates"])
            first_thread = threading.Thread(
                target=controller._run_background_operation,
                args=(first,),
            )
            first_thread.start()
            self.assertTrue(entered_first.wait(1))

            second = controller._make_context(
                operation_kind="route",
                ip_address="192.0.2.10",
                candidate_index=0,
                output_num=1,
                input_num=4,
                state_changing=True,
            )
            controller._submit(second, state["candidates"])
            second_thread = threading.Thread(
                target=controller._run_background_operation,
                args=(second,),
            )
            second_thread.start()
            self.assertFalse(entered_route.wait(0.2))

            release_first.set()
            first_thread.join(2)
            second_thread.join(2)

        self.assertFalse(first_thread.is_alive())
        self.assertFalse(second_thread.is_alive())
        self.assertEqual(["quick", ("route", 1, 4)], calls)

    def test_stale_queued_route_is_discarded_before_handler_acquisition(self):
        controller, _state, pool = self.make_controller()
        controller.request_route(1, 4)
        route = pool.runnables[0]
        controller.invalidate_context()

        with patch("gui.matrix_controller.ExtronIN1804Handler") as handler_factory:
            route.run()

        handler_factory.assert_not_called()

    def test_route_that_becomes_stale_while_waiting_for_lane_does_not_send(self):
        controller, _state, pool = self.make_controller()
        waiting_for_lane = threading.Event()
        release_lane = threading.Event()

        class BlockingLane:
            def __enter__(self):
                waiting_for_lane.set()
                release_lane.wait(2)
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

        controller._operation_lock = BlockingLane()
        controller.request_route(1, 4)
        route = pool.runnables[0]
        with patch("gui.matrix_controller.ExtronIN1804Handler") as handler_factory:
            thread = threading.Thread(target=route.run)
            thread.start()
            self.assertTrue(waiting_for_lane.wait(1))
            controller.invalidate_context()
            release_lane.set()
            thread.join(2)

            self.assertFalse(thread.is_alive())
            handler_factory.assert_not_called()

    def test_gui_invalidation_returns_while_serialized_transport_io_is_blocked(self):
        """Invalidation only publishes retirement metadata on the GUI path."""
        controller, state, pool = self.make_controller()
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        io_entered = threading.Event()
        release_io = threading.Event()
        disconnect_called = threading.Event()

        class BlockingHandler:
            def __init__(self, **_kwargs):
                self.log_callback = None
                self.connected = False

            def connect(self):
                self.connected = True

            def is_connected(self):
                return self.connected

            def get_connections(self):
                io_entered.set()
                release_io.wait(2)
                return [2]

            def disconnect(self):
                disconnect_called.set()
                self.connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", BlockingHandler):
            context = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            operation_thread = threading.Thread(
                target=controller._run_background_operation, args=(context,)
            )
            operation_thread.start()
            self.assertTrue(io_entered.wait(1))

            invalidation_thread = threading.Thread(target=controller.invalidate_context)
            invalidation_thread.start()
            invalidation_thread.join(0.2)
            self.assertFalse(invalidation_thread.is_alive())
            self.assertIsNone(controller._active_context)
            self.assertFalse(disconnect_called.is_set())
            self.assertEqual(1, len(pool.runnables))

            release_io.set()
            operation_thread.join(1)
            self.assertFalse(operation_thread.is_alive())
            retirement_thread = threading.Thread(target=pool.runnables.pop().run)
            retirement_thread.start()
            self.assertTrue(disconnect_called.wait(1))
            retirement_thread.join(1)
            self.assertFalse(retirement_thread.is_alive())

    def test_invalidation_during_connect_retires_stale_handler_without_publication(self):
        """A connected-but-stale handler cannot become persistent authority."""
        controller, state, pool = self.make_controller()
        controller._request_keepalive_stop = lambda: None
        keepalive_starts = []
        controller._request_keepalive_start = lambda: keepalive_starts.append(True)
        connect_entered = threading.Event()
        release_connect = threading.Event()
        disconnect_entered = threading.Event()
        release_disconnect = threading.Event()
        instances = []
        errors = []
        controller.errorAccepted.connect(lambda *args: errors.append(args))

        class BlockingConnectHandler:
            def __init__(self, **_kwargs):
                self.log_callback = None
                self.connected = False
                self.index = len(instances)
                instances.append(self)

            def connect(self):
                connect_entered.set()
                release_connect.wait(2)
                self.connected = True

            def is_connected(self):
                return self.connected

            def get_connections(self):
                return [2]

            def disconnect(self):
                disconnect_entered.set()
                if self.index == 0:
                    release_disconnect.wait(2)
                self.connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", BlockingConnectHandler):
            stale = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            stale_thread = threading.Thread(
                target=controller._run_background_operation, args=(stale,)
            )
            stale_thread.start()
            self.assertTrue(connect_entered.wait(1))

            invalidation_thread = threading.Thread(target=controller.invalidate_context)
            invalidation_thread.start()
            invalidation_thread.join(0.2)
            self.assertFalse(invalidation_thread.is_alive())
            self.assertIsNone(controller._active_context)
            self.assertFalse(disconnect_entered.is_set())

            release_connect.set()
            stale_thread.join(1)
            self.assertFalse(stale_thread.is_alive())
            self.assertIsNone(controller._session_handler)
            self.assertIsNone(controller._session_identity)
            self.assertIsNone(controller._published_session_ip)
            self.assertEqual([], keepalive_starts)
            key = controller._retirement_key(stale)
            with controller._retirement_lock:
                self.assertIn(key, controller._retirement_events)

            replacement = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            replacement_thread = threading.Thread(
                target=controller._run_background_operation, args=(replacement,)
            )
            replacement_thread.start()
            self.assertEqual(1, len(instances))

            cleanup = next(
                runnable for runnable in pool.runnables
                if getattr(runnable.context, "operation_kind", None) == "cleanup"
            )
            cleanup_thread = threading.Thread(target=cleanup.run)
            cleanup_thread.start()
            self.assertTrue(disconnect_entered.wait(1))
            self.assertEqual(1, len(instances))
            release_disconnect.set()
            cleanup_thread.join(1)
            replacement_thread.join(1)

        self.app.processEvents()
        self.assertFalse(cleanup_thread.is_alive())
        self.assertFalse(replacement_thread.is_alive())
        self.assertEqual([], errors)

    def test_post_connect_authority_commit_is_atomic_against_gui_replacement(self):
        """A stale post-connect handler cannot publish between check and commit."""
        controller, state, pool = self.make_controller()
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        checked_current = threading.Event()
        release_commit = threading.Event()
        disconnect_entered = threading.Event()
        release_disconnect = threading.Event()
        instances, results = [], []
        controller.resultAccepted.connect(lambda data, _handle: results.append(data))

        class Handler:
            def __init__(self, **kwargs):
                self.log_callback = None
                self.ip_address = kwargs["ip_address"]
                self.connected = False
                instances.append(self)

            def connect(self):
                self.connected = True

            def is_connected(self):
                return self.connected

            def get_connections(self):
                return [2]

            def disconnect(self):
                if self.ip_address == "192.0.2.10":
                    disconnect_entered.set()
                    release_disconnect.wait(2)
                self.connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", Handler):
            first = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._submit(first, state["candidates"])
            real_commit = controller._commit_session_authority_locked

            def pause_before_commit(context, identity, handler):
                if context == first:
                    self.assertTrue(controller._is_current(context))
                    checked_current.set()
                    release_commit.wait(2)
                return real_commit(context, identity, handler)

            controller._commit_session_authority_locked = pause_before_commit
            first_thread = threading.Thread(
                target=controller._run_background_operation, args=(first,)
            )
            first_thread.start()
            self.assertTrue(checked_current.wait(1))

            state["ip"] = "192.0.2.11"
            replacement = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.11",
                candidate_index=0,
                state_changing=False,
            )
            controller._submit(replacement, state["candidates"])
            release_commit.set()
            first_thread.join(1)

            self.assertFalse(first_thread.is_alive())
            self.assertIs(replacement, controller._active_context)
            self.assertIsNone(controller._session_handler)
            self.assertIsNone(controller._session_identity)
            self.assertIsNone(controller._published_session_ip)
            self.assertEqual([], results)

            cleanup = next(
                runnable for runnable in pool.runnables
                if getattr(runnable.context, "operation_kind", None) == "cleanup"
            )
            replacement_thread = threading.Thread(
                target=controller._run_background_operation, args=(replacement,)
            )
            replacement_thread.start()
            cleanup_thread = threading.Thread(target=cleanup.run)
            cleanup_thread.start()
            self.assertTrue(disconnect_entered.wait(1))
            self.assertEqual(["192.0.2.10"], [handler.ip_address for handler in instances])

            release_disconnect.set()
            cleanup_thread.join(1)
            replacement_thread.join(1)

        self.assertFalse(cleanup_thread.is_alive())
        self.assertFalse(replacement_thread.is_alive())
        self.assertEqual(
            ["192.0.2.10", "192.0.2.11"],
            [handler.ip_address for handler in instances],
        )
        self.assertIs(replacement, controller._active_context)
        self.assertEqual("192.0.2.11", controller._published_session_ip)
        self.assertEqual([], results)

    def test_stale_queued_keepalive_start_cannot_restart_timer(self):
        """Queued start signals carry the committed context, not signal order."""
        controller, state, pool = self.make_controller()
        starts = []

        class Timer:
            active = False

            def isActive(self):
                return self.active

            def start(self):
                starts.append(True)
                self.active = True

            def stop(self):
                self.active = False

        class Handler:
            def __init__(self, **kwargs):
                self.log_callback = None
                self.connected = False
                self.ip_address = kwargs["ip_address"]

            def connect(self):
                self.connected = True

            def is_connected(self):
                return self.connected

            def disconnect(self):
                self.connected = False

        controller._keepalive_timer = Timer()
        with patch("gui.matrix_controller.ExtronIN1804Handler", Handler):
            first = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._submit(first, state["candidates"])
            first_thread = threading.Thread(target=controller._acquire_session, args=(first, ()))
            first_thread.start()
            first_thread.join(1)
            self.assertFalse(first_thread.is_alive())

            controller.invalidate_context()
            state["ip"] = "192.0.2.11"
            replacement = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.11",
                candidate_index=0,
                state_changing=False,
            )
            self.app.processEvents()
            self.assertEqual([], starts)

            retirement = next(
                runnable for runnable in pool.runnables
                if getattr(runnable.context, "operation_kind", None) == "retirement"
            )
            retirement.run()
            controller._submit(replacement, state["candidates"])
            controller._acquire_session(replacement, ())

        self.assertEqual([True], starts)
        self.assertEqual("192.0.2.11", controller._published_session_ip)

    def test_public_full_refresh_target_replacement_retires_old_owner_before_b_starts(self):
        """Public A-to-B replacement keeps A's transport identity observable."""
        controller, state, pool = self.make_controller()
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        instances = []

        class Handler:
            def __init__(self, **kwargs):
                self.log_callback = None
                self.ip_address = kwargs["ip_address"]
                self.connected = False
                instances.append(self)

            def connect(self):
                self.connected = True

            def is_connected(self):
                return self.connected

            def disconnect(self):
                self.connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", Handler):
            first = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._acquire_session(first, ())
            self.assertEqual("192.0.2.10", controller._session_identity.ip_address)
            self.assertEqual("192.0.2.10", controller._published_session_ip)

            state["ip"] = "192.0.2.11"
            controller.request_full_refresh("192.0.2.11", state["candidates"], 0)
            current = controller._active_context
            self.assertEqual("192.0.2.11", current.ip_address)
            old_key = controller._retirement_key(first)
            with controller._retirement_lock:
                self.assertIn(old_key, controller._retirement_events)

            controller.invalidate_context()
            self.assertIsNone(controller._active_context)
            with controller._retirement_lock:
                self.assertIn(old_key, controller._retirement_events)

            stale_b = next(
                runnable for runnable in pool.runnables
                if getattr(runnable.context, "ip_address", None) == "192.0.2.11"
                and getattr(runnable.context, "operation_kind", None) == "full_refresh"
            )
            stale_b.run()
            self.assertEqual(1, len(instances))

            retirement = next(
                runnable for runnable in pool.runnables
                if getattr(runnable.context, "operation_kind", None) == "retirement"
            )
            retirement.run()

        self.assertIsNone(controller._session_handler)
        self.assertIsNone(controller._session_identity)
        self.assertIsNone(controller._published_session_ip)

    def test_public_same_ip_revision_replacement_publishes_retirement_for_old_session(self):
        controller, state, pool = self.make_controller()
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None

        class Handler:
            def __init__(self, **_kwargs):
                self.log_callback = None
                self.connected = False

            def connect(self):
                self.connected = True

            def is_connected(self):
                return self.connected

            def disconnect(self):
                self.connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", Handler):
            first = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._acquire_session(first, ())
            state["revision"] = 2

            controller.request_full_refresh("192.0.2.10", state["candidates"], 0)

        self.assertEqual(2, controller._active_context.credential_context_revision)
        with controller._retirement_lock:
            self.assertIn(controller._retirement_key(first), controller._retirement_events)
        self.assertTrue(any(
            getattr(runnable.context, "operation_kind", None) == "retirement"
            for runnable in pool.runnables
        ))

    def test_replacement_target_waits_for_published_retirement_without_owner_lock_cycle(self):
        """A new endpoint cannot bypass retirement even when scheduled first."""
        controller, state, pool = self.make_controller()
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        first_io_entered = threading.Event()
        release_first_io = threading.Event()
        disconnect_entered = threading.Event()
        release_disconnect = threading.Event()
        instances = []

        class BlockingHandler:
            def __init__(self, **kwargs):
                self.log_callback = None
                self.ip_address = kwargs["ip_address"]
                self.connected = False
                self.index = len(instances)
                instances.append(self)

            def connect(self):
                self.connected = True

            def is_connected(self):
                return self.connected

            def get_connections(self):
                if self.index == 0:
                    first_io_entered.set()
                    release_first_io.wait(2)
                return [2]

            def disconnect(self):
                if self.index == 0:
                    disconnect_entered.set()
                    release_disconnect.wait(2)
                self.connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", BlockingHandler):
            first = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            first_thread = threading.Thread(
                target=controller._run_background_operation, args=(first,)
            )
            first_thread.start()
            self.assertTrue(first_io_entered.wait(1))

            controller.invalidate_context()
            state["ip"] = "192.0.2.11"
            state["revision"] = 2
            replacement = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.11",
                candidate_index=0,
                state_changing=False,
            )
            replacement_thread = threading.Thread(
                target=controller._run_background_operation, args=(replacement,)
            )
            replacement_thread.start()
            self.assertEqual(1, len(instances))

            release_first_io.set()
            first_thread.join(1)
            self.assertFalse(first_thread.is_alive())
            retirement = next(
                runnable for runnable in pool.runnables
                if getattr(runnable.context, "operation_kind", None) == "retirement"
            )
            retirement_thread = threading.Thread(target=retirement.run)
            retirement_thread.start()
            self.assertTrue(disconnect_entered.wait(1))
            self.assertEqual(1, len(instances))

            release_disconnect.set()
            retirement_thread.join(1)
            replacement_thread.join(1)

        self.assertFalse(retirement_thread.is_alive())
        self.assertFalse(replacement_thread.is_alive())
        self.assertEqual(["192.0.2.10", "192.0.2.11"], [item.ip_address for item in instances])

    def test_background_operation_does_not_start_keepalive_timer_directly(self):
        controller, state, pool = self.make_controller()
        start_called = threading.Event()

        class Timer:
            def isActive(self):
                return False

            def start(self):
                start_called.set()

            def stop(self):
                pass

        class Handler:
            def __init__(self, **_kwargs):
                self.log_callback = None

            def connect(self):
                pass

            def is_connected(self):
                return True

            def get_connections(self):
                return [2]

            def disconnect(self):
                pass

        controller._keepalive_timer = Timer()
        context = controller._make_context(
            operation_kind="quick_refresh",
            ip_address="192.0.2.10",
            candidate_index=0,
            state_changing=False,
        )
        controller._submit(context, state["candidates"])
        with patch("gui.matrix_controller.ExtronIN1804Handler", Handler):
            thread = threading.Thread(
                target=controller._run_background_operation,
                args=(context,),
            )
            thread.start()
            thread.join(2)

        self.assertFalse(thread.is_alive())
        self.assertFalse(start_called.is_set())

    def test_session_failure_invalidates_matching_session_and_reconnects(self):
        from core.exceptions import ConnectionError

        controller, state, pool = self.make_controller()
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        instances = []

        class Handler:
            def __init__(self, **_kwargs):
                self.log_callback = None
                self.connected = False
                instances.append(self)

            def connect(self):
                self.connected = True

            def is_connected(self):
                return self.connected

            def get_connections(self):
                if self is instances[0]:
                    raise ConnectionError("socket failed")
                return [3]

            def disconnect(self):
                self.connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", Handler):
            first = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._submit(first, state["candidates"])
            controller._run_background_operation(first)
            next(runnable for runnable in pool.runnables if getattr(getattr(runnable, "context", None), "operation_kind", None) == "cleanup").run()

            second = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._submit(second, state["candidates"])
            controller._run_background_operation(second)

        self.assertEqual(2, len(instances))
        self.assertFalse(instances[0].connected)
        self.assertTrue(instances[1].connected)

    def test_failed_session_invalidation_is_serialized_for_same_identity_race(self):
        from core.exceptions import ConnectionError

        controller, state, pool = self.make_controller()
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        entered_first = threading.Event()
        release_first = threading.Event()
        disconnect_started = threading.Event()
        release_disconnect = threading.Event()
        schedule_entered = threading.Event()
        release_schedule = threading.Event()
        second_used_new_handler = threading.Event()
        instances = []
        calls = []

        class Handler:
            def __init__(self, **_kwargs):
                self.log_callback = None
                self.connected = False
                self.id = len(instances)
                instances.append(self)

            def connect(self):
                self.connected = True

            def is_connected(self):
                return self.connected

            def get_connections(self):
                calls.append(("get", self.id))
                if self.id == 0:
                    entered_first.set()
                    release_first.wait(2)
                    raise ConnectionError("socket failed")
                second_used_new_handler.set()
                return [2]

            def disconnect(self):
                calls.append(("disconnect", self.id))
                self.connected = False
                if self.id == 0:
                    disconnect_started.set()
                    release_disconnect.wait(2)

        with patch("gui.matrix_controller.ExtronIN1804Handler", Handler):
            original_schedule = controller._schedule_retirement

            def blocked_schedule(retirement):
                schedule_entered.set()
                release_schedule.wait(2)
                original_schedule(retirement)

            controller._schedule_retirement = blocked_schedule
            first = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._submit(first, state["candidates"])
            first_thread = threading.Thread(
                target=controller._run_background_operation,
                args=(first,),
            )
            first_thread.start()
            self.assertTrue(entered_first.wait(1))

            second = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._submit(second, state["candidates"])
            second_thread = threading.Thread(
                target=controller._run_background_operation,
                args=(second,),
            )
            second_thread.start()

            release_first.set()
            self.assertTrue(schedule_entered.wait(1))
            key = controller._retirement_key(first)
            with controller._retirement_lock:
                self.assertIn(key, controller._retirement_events)
                self.assertFalse(controller._retirement_events[key].is_set())
            self.assertFalse(second_used_new_handler.wait(0.05))
            self.assertEqual(1, len(instances))

            release_schedule.set()
            first_thread.join(1)
            cleanup = next(
                runnable for runnable in pool.runnables
                if getattr(getattr(runnable, "context", None), "operation_kind", None) == "cleanup"
            )
            cleanup_thread = threading.Thread(target=cleanup.run)
            cleanup_thread.start()
            self.assertTrue(disconnect_started.wait(1))
            self.assertFalse(second_used_new_handler.wait(0.05))
            release_disconnect.set()
            cleanup_thread.join(2)
            self.assertTrue(second_used_new_handler.wait(1))
            second_thread.join(2)
            first_thread.join(2)

        self.assertFalse(first_thread.is_alive())
        self.assertEqual(2, len(instances))
        self.assertEqual(("get", 0), calls[0])
        self.assertIn(("disconnect", 0), calls)
        self.assertIn(("get", 1), calls)
        self.assertFalse(instances[0].connected)
        self.assertTrue(instances[1].connected)
        self.assertIs(controller._session_handler, instances[1])

    def test_production_quick_refresh_transport_failure_does_not_emit_route_one(self):
        from core.exceptions import ConnectionError

        controller, state, pool = self.make_controller()
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        routes = []
        errors = []
        controller.routeAccepted.connect(routes.append)
        controller.routeError.connect(errors.append)

        class Handler:
            def __init__(self, **_kwargs):
                self.log_callback = None
                self.connected = False

            def connect(self):
                self.connected = True

            def is_connected(self):
                return self.connected

            def get_connections(self):
                raise ConnectionError("transport failed")

            def disconnect(self):
                self.connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", Handler):
            context = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._submit(context, state["candidates"])
            controller._run_background_operation(context)

        self.assertEqual([], routes)
        self.assertEqual(1, len(errors))

    def test_production_full_refresh_transport_failure_is_not_accepted_or_cached(self):
        from handlers.extron.in1804 import ExtronIN1804Handler

        controller, state, pool = self.make_controller()
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        accepted = []
        errors = []
        route_errors = []
        instances = []
        controller.resultAccepted.connect(lambda *args: accepted.append(args))
        controller.errorAccepted.connect(lambda *args: errors.append(args))
        controller.routeError.connect(route_errors.append)

        class BrokenTransportHandler(ExtronIN1804Handler):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                instances.append(self)

            def connect(self):
                self.socket = object()
                self.authenticated = True
                self._connected = True

            def _send_bytes(self, _payload):
                pass

            def _recv_bytes(self, _size):
                raise OSError("socket read failed")

            def disconnect(self):
                super().disconnect()
                self.socket = None
                self._connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", BrokenTransportHandler):
            first = controller._make_context(
                operation_kind="full_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._submit(first, state["candidates"])
            controller._run_background_operation(first)
            next(runnable for runnable in pool.runnables if getattr(getattr(runnable, "context", None), "operation_kind", None) == "cleanup").run()

            second = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._submit(second, state["candidates"])
            controller._run_background_operation(second)

        self.assertEqual([], accepted)
        self.assertEqual(1, len(errors))
        self.assertEqual(1, len(route_errors))
        self.assertEqual("connection_error", errors[0][0][0])
        self.assertGreaterEqual(len(instances), 2)
        self.assertIsNot(instances[0], instances[1])

    def test_route_empty_response_does_not_accept_or_fallback(self):
        from handlers.extron.in1804 import ExtronIN1804Handler

        controller, _state, pool = self.make_controller()
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        routes = []
        route_errors = []
        fallback_calls = []
        sends = []
        controller.routeAccepted.connect(routes.append)
        controller.routeError.connect(route_errors.append)
        controller._credential_advance_provider = (
            lambda *_args: fallback_calls.append(_args) or 1
        )

        class EmptyRouteResponseHandler(ExtronIN1804Handler):
            def connect(self):
                self.socket = object()
                self.authenticated = True
                self._connected = True
                self.model = "IN1804"

            def _send_bytes(self, payload):
                sends.append(payload)

            def _recv_bytes(self, _size):
                return b""

            def disconnect(self):
                super().disconnect()
                self.socket = None
                self._connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", EmptyRouteResponseHandler):
            with patch("core.base_handler.time.sleep", lambda _seconds: None):
                controller.request_route(1, 3)
                pool.runnables.pop(0).run()

        self.assertEqual([], routes)
        self.assertEqual(1, len(route_errors))
        self.assertEqual([], fallback_calls)
        self.assertEqual([b"3*1!\r"], sends)
        self.assertIsNone(controller._session_handler)

    def test_full_refresh_empty_response_is_not_accepted_and_reconnects_next(self):
        from handlers.extron.in1804 import ExtronIN1804Handler

        controller, state, pool = self.make_controller()
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        accepted = []
        errors = []
        route_errors = []
        instances = []
        controller.resultAccepted.connect(lambda *args: accepted.append(args))
        controller.errorAccepted.connect(lambda *args: errors.append(args))
        controller.routeError.connect(route_errors.append)

        class EmptyReadResponseHandler(ExtronIN1804Handler):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                instances.append(self)

            def connect(self):
                self.socket = object()
                self.authenticated = True
                self._connected = True

            def _send_bytes(self, _payload):
                pass

            def _recv_bytes(self, _size):
                return b""

            def disconnect(self):
                super().disconnect()
                self.socket = None
                self._connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", EmptyReadResponseHandler):
            with patch("core.base_handler.time.sleep", lambda _seconds: None):
                first = controller._make_context(
                    operation_kind="full_refresh",
                    ip_address="192.0.2.10",
                    candidate_index=0,
                    state_changing=False,
                )
                controller._submit(first, state["candidates"])
                controller._run_background_operation(first)
                next(runnable for runnable in pool.runnables if getattr(getattr(runnable, "context", None), "operation_kind", None) == "cleanup").run()

                second = controller._make_context(
                    operation_kind="quick_refresh",
                    ip_address="192.0.2.10",
                    candidate_index=0,
                    state_changing=False,
                )
                controller._submit(second, state["candidates"])
                controller._run_background_operation(second)

        self.assertEqual([], accepted)
        self.assertEqual(1, len(errors))
        self.assertEqual(1, len(route_errors))
        self.assertEqual("connection_error", errors[0][0][0])
        self.assertGreaterEqual(len(instances), 2)
        self.assertIsNot(instances[0], instances[1])

    def test_route_echo_only_response_does_not_accept_or_fallback(self):
        from handlers.extron.in1804 import ExtronIN1804Handler

        controller, _state, pool = self.make_controller()
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        routes = []
        route_errors = []
        fallback_calls = []
        sends = []
        controller.routeAccepted.connect(routes.append)
        controller.routeError.connect(route_errors.append)
        controller._credential_advance_provider = (
            lambda *_args: fallback_calls.append(_args) or 1
        )

        class EchoOnlyRouteHandler(ExtronIN1804Handler):
            def connect(self):
                self.socket = object()
                self.authenticated = True
                self._connected = True
                self.model = "IN1804"

            def _send_bytes(self, payload):
                sends.append(payload)

            def _read_response(self):
                return b"3*1!\r\n"

            def disconnect(self):
                super().disconnect()
                self.socket = None
                self._connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", EchoOnlyRouteHandler):
            with patch("core.base_handler.time.sleep", lambda _seconds: None):
                controller.request_route(1, 3)
                pool.runnables.pop(0).run()

        self.assertEqual([], routes)
        self.assertEqual(1, len(route_errors))
        self.assertEqual([], fallback_calls)
        self.assertEqual([b"3*1!\r"], sends)
        self.assertIsNone(controller._session_handler)

    def test_full_refresh_echo_only_response_is_not_accepted(self):
        from handlers.extron.in1804 import ExtronIN1804Handler

        controller, state, pool = self.make_controller()
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        accepted = []
        errors = []
        instances = []
        controller.resultAccepted.connect(lambda *args: accepted.append(args))
        controller.errorAccepted.connect(lambda *args: errors.append(args))

        class EchoOnlyReadHandler(ExtronIN1804Handler):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                instances.append(self)

            def connect(self):
                self.socket = object()
                self.authenticated = True
                self._connected = True

            def _send_bytes(self, _payload):
                pass

            def _read_response(self):
                return b"1I\r\n"

            def disconnect(self):
                super().disconnect()
                self.socket = None
                self._connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", EchoOnlyReadHandler):
            with patch("core.base_handler.time.sleep", lambda _seconds: None):
                first = controller._make_context(
                    operation_kind="full_refresh",
                    ip_address="192.0.2.10",
                    candidate_index=0,
                    state_changing=False,
                )
                controller._submit(first, state["candidates"])
                controller._run_background_operation(first)
                next(runnable for runnable in pool.runnables if getattr(getattr(runnable, "context", None), "operation_kind", None) == "cleanup").run()

                second = controller._make_context(
                    operation_kind="quick_refresh",
                    ip_address="192.0.2.10",
                    candidate_index=0,
                    state_changing=False,
                )
                controller._submit(second, state["candidates"])
                controller._run_background_operation(second)

        self.assertEqual([], accepted)
        self.assertEqual(1, len(errors))
        self.assertEqual("connection_error", errors[0][0][0])
        self.assertGreaterEqual(len(instances), 2)
        self.assertIsNot(instances[0], instances[1])

    def test_old_failure_does_not_invalidate_new_matching_context_session(self):
        controller, state, pool = self.make_controller()
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None

        class Handler:
            def __init__(self, **_kwargs):
                self.log_callback = None
                self.connected = True

            def connect(self):
                self.connected = True

            def is_connected(self):
                return self.connected

            def disconnect(self):
                self.connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", Handler):
            old = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._submit(old, state["candidates"])
            controller._acquire_session(old, ())

            state["revision"] = 2
            new = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._submit(new, state["candidates"])
            next(runnable for runnable in pool.runnables if getattr(getattr(runnable, "context", None), "operation_kind", None) == "retirement").run()
            new_handler = controller._acquire_session(new, ())
            controller._invalidate_failed_session(old)

        self.assertIs(new_handler, controller._session_handler)
        self.assertTrue(new_handler.connected)

    def test_route_auth_before_send_uses_next_candidate(self):
        from core.exceptions import MatrixAuthenticationError

        controller, _state, pool = self.make_controller()
        route_errors = []
        controller.routeError.connect(route_errors.append)
        disconnect_entered, release_disconnect = threading.Event(), threading.Event()

        class Handler:
            attempts = []

            def __init__(self, **kwargs):
                self.log_callback = None
                self.username = kwargs["username"]
                Handler.attempts.append(self.username)

            def connect(self):
                if self.username == "synthetic-user":
                    raise MatrixAuthenticationError(
                        "rejected before send",
                        confirmed_device_rejection=True,
                        safe_for_credential_fallback=True,
                    )

            def is_connected(self):
                return True

            def set_connection(self, output_num, input_num):
                Handler.attempts.append(("set", output_num, input_num, self.username))

            def get_connections(self):
                return [3]

            def disconnect(self):
                if self.username == "synthetic-user":
                    disconnect_entered.set()
                    release_disconnect.wait(1)

        with patch("gui.matrix_controller.ExtronIN1804Handler", Handler):
            controller.request_route(1, 3)
            pool.runnables.pop(0).run()
            cleanup, retry = pool.runnables
            retry_thread = threading.Thread(target=retry.run)
            retry_thread.start()
            retry_thread.join(0.05)
            self.assertTrue(retry_thread.is_alive())
            self.assertEqual(["synthetic-user"], Handler.attempts)
            cleanup_thread = threading.Thread(target=cleanup.run)
            cleanup_thread.start()
            self.assertTrue(disconnect_entered.wait(0.2))
            self.assertEqual(["synthetic-user"], Handler.attempts)
            release_disconnect.set()
            cleanup_thread.join(1)
            retry_thread.join(1)
            self.assertFalse(cleanup_thread.is_alive())
            self.assertFalse(retry_thread.is_alive())

        self.assertEqual(
            ["synthetic-user", "synthetic-user-2", ("set", 1, 3, "synthetic-user-2")],
            Handler.attempts,
        )
        self.assertEqual([], route_errors)

    def test_route_auth_after_possible_send_is_not_retried(self):
        from core.exceptions import MatrixAuthenticationError

        controller, _state, pool = self.make_controller()
        route_errors = []
        controller.routeError.connect(route_errors.append)

        class Handler:
            attempts = []

            def __init__(self, **kwargs):
                self.log_callback = None
                self.username = kwargs["username"]
                Handler.attempts.append(self.username)

            def connect(self):
                pass

            def is_connected(self):
                return True

            def set_connection(self, output_num, input_num):
                Handler.attempts.append(("set", output_num, input_num, self.username))
                raise MatrixAuthenticationError(
                    "post-send auth-like failure",
                    confirmed_device_rejection=True,
                    safe_for_credential_fallback=True,
                )

            def disconnect(self):
                pass

        with patch("gui.matrix_controller.ExtronIN1804Handler", Handler):
            controller.request_route(1, 3)
            pool.runnables.pop(0).run()

        self.assertEqual(["synthetic-user", ("set", 1, 3, "synthetic-user")], Handler.attempts)
        self.assertEqual(1, len(route_errors))

    def test_ambiguous_route_failure_never_replays_across_blocked_retirement(self):
        from core.exceptions import CommandOutcomeUnknownError

        controller, _state, pool = self.make_controller(retirement_timeout_seconds=0.001)
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        route_errors = []
        controller.routeError.connect(route_errors.append)
        disconnect_entered, release_disconnect = threading.Event(), threading.Event()

        class Handler:
            attempts = []

            def __init__(self, **kwargs):
                self.log_callback = None
                self.username = kwargs["username"]
                Handler.attempts.append(self.username)

            def connect(self):
                pass

            def is_connected(self):
                return True

            def set_connection(self, output_num, input_num):
                Handler.attempts.append(("set", output_num, input_num, self.username))
                raise CommandOutcomeUnknownError("route may have been delivered")

            def disconnect(self):
                disconnect_entered.set()
                release_disconnect.wait(1)

        with patch("gui.matrix_controller.ExtronIN1804Handler", Handler):
            controller.request_route(1, 3)
            pool.runnables.pop(0).run()
            cleanup = pool.runnables.pop(0)
            cleanup_thread = threading.Thread(target=cleanup.run)
            cleanup_thread.start()
            self.assertTrue(disconnect_entered.wait(0.2))

            controller.request_route(1, 2)
            pool.runnables.pop(0).run()
            self.assertEqual(["synthetic-user", ("set", 1, 3, "synthetic-user")], Handler.attempts)
            self.assertEqual(2, len(route_errors))

            release_disconnect.set()
            cleanup_thread.join(1)
            self.assertFalse(cleanup_thread.is_alive())
        self.assertIsNone(controller._session_handler)

    def test_immutable_candidate_for_context_returns_assigned_mapping_unchanged(self):
        controller, state, pool = self.make_controller(
            candidates=[
                MappingProxyType(
                    {"username": "synth-immutable-user", "password": "synth-immutable-pass"}
                ),
                MappingProxyType(
                    {"username": "synth-immutable-user-2", "password": "synth-immutable-pass-2"}
                ),
            ]
        )
        context = controller._make_context(
            operation_kind="full_refresh",
            ip_address="192.0.2.10",
            candidate_index=1,
            state_changing=False,
        )
        controller._submit(context, state["candidates"])

        candidate = controller._candidate_for_context(context)

        self.assertIsInstance(candidate, MappingProxyType)
        self.assertEqual("synth-immutable-user-2", candidate.get("username", ""))
        self.assertEqual("synth-immutable-pass-2", candidate.get("password", ""))
        # Candidate must not be mutated or converted into shared mutable state.
        self.assertIsInstance(candidate, MappingProxyType)
        self.assertEqual(
            {"username": "synth-immutable-user-2", "password": "synth-immutable-pass-2"},
            dict(candidate),
        )

    def test_immutable_candidate_secrets_include_username_and_password(self):
        controller, state, pool = self.make_controller(
            candidates=[
                MappingProxyType(
                    {"username": "synth-immutable-user", "password": "synth-immutable-pass"}
                )
            ]
        )
        context = controller._make_context(
            operation_kind="full_refresh",
            ip_address="192.0.2.10",
            candidate_index=0,
            state_changing=False,
        )
        controller._submit(context, state["candidates"])

        secrets = controller._candidate_secrets(context)

        self.assertIn("synth-immutable-user", secrets)
        self.assertIn("synth-immutable-pass", secrets)

    def test_immutable_candidate_acquires_session_and_connects(self):
        controller, state, pool = self.make_controller(
            candidates=[
                MappingProxyType(
                    {"username": "synth-immutable-user", "password": "synth-immutable-pass"}
                )
            ]
        )
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        constructed = []
        connected = []

        class Handler:
            def __init__(self, **kwargs):
                constructed.append((kwargs["username"], kwargs["password"]))
                self.log_callback = None
                self.connected = False

            def connect(self):
                connected.append(True)
                self.connected = True

            def is_connected(self):
                return self.connected

            def disconnect(self):
                self.connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", Handler):
            context = controller._make_context(
                operation_kind="full_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._submit(context, state["candidates"])
            handler = controller._acquire_session(context, ())

        self.assertEqual([("synth-immutable-user", "synth-immutable-pass")], constructed)
        self.assertEqual([True], connected)
        self.assertIsNotNone(handler)

    def test_mutable_dict_candidate_remains_supported(self):
        controller, state, pool = self.make_controller(
            candidates=[
                {"username": "synth-dict-user", "password": "synth-dict-pass"}
            ]
        )
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        constructed = []

        class Handler:
            def __init__(self, **kwargs):
                constructed.append((kwargs["username"], kwargs["password"]))
                self.log_callback = None
                self.connected = False

            def connect(self):
                self.connected = True

            def is_connected(self):
                return self.connected

            def disconnect(self):
                self.connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", Handler):
            dict_context = controller._make_context(
                operation_kind="full_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._submit(dict_context, state["candidates"])
            candidate = controller._candidate_for_context(dict_context)

            self.assertEqual("synth-dict-user", candidate.get("username", ""))
            secrets = controller._candidate_secrets(dict_context)
            self.assertIn("synth-dict-user", secrets)
            self.assertIn("synth-dict-pass", secrets)
            controller._acquire_session(dict_context, ())

        self.assertEqual([("synth-dict-user", "synth-dict-pass")], constructed)

    def test_non_mapping_candidate_is_rejected_before_handler_construction(self):
        controller, state, pool = self.make_controller(
            candidates=[object()]
        )
        advance_calls = []
        controller._credential_advance_provider = (
            lambda *_args: advance_calls.append(_args) or None
        )

        with patch("gui.matrix_controller.ExtronIN1804Handler") as handler_factory:
            context = controller._make_context(
                operation_kind="full_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._submit(context, state["candidates"])
            with self.assertRaises(RuntimeError) as captured:
                controller._acquire_session(context, ())

        handler_factory.assert_not_called()
        self.assertIn("No credentials for current Matrix context", str(captured.exception))
        self.assertEqual([], advance_calls)

    def test_absent_candidate_index_is_rejected_before_handler_and_io(self):
        controller, state, pool = self.make_controller()
        advance_calls = []
        controller._credential_advance_provider = (
            lambda *_args: advance_calls.append(_args) or None
        )
        # Empty request-scoped snapshot: no assigned candidate exists.
        state["candidates"] = ()

        with patch("gui.matrix_controller.ExtronIN1804Handler") as handler_factory:
            context = controller._make_context(
                operation_kind="full_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._submit(context, state["candidates"])
            with self.assertRaises(RuntimeError) as captured:
                controller._acquire_session(context, ())

        handler_factory.assert_not_called()
        self.assertIn("No credentials for current Matrix context", str(captured.exception))
        self.assertEqual([], advance_calls)

    def test_none_candidate_index_is_rejected_before_handler_and_io(self):
        controller, _state, _pool = self.make_controller()
        advance_calls = []
        controller._credential_advance_provider = (
            lambda *_args: advance_calls.append(_args) or None
        )

        with patch("gui.matrix_controller.ExtronIN1804Handler") as handler_factory:
            context = controller._make_context(
                operation_kind="full_refresh",
                ip_address="192.0.2.10",
                candidate_index=None,
                state_changing=False,
            )
            with self.assertRaises(RuntimeError) as captured:
                controller._acquire_session(context, ())

        handler_factory.assert_not_called()
        self.assertIn("No credentials for current Matrix context", str(captured.exception))
        self.assertEqual([], advance_calls)

    def test_out_of_range_candidate_index_is_rejected_before_handler_and_io(self):
        controller, state, pool = self.make_controller(
            candidates=[
                {"username": "synth-dict-user", "password": "synth-dict-pass"}
            ]
        )
        advance_calls = []
        controller._credential_advance_provider = (
            lambda *_args: advance_calls.append(_args) or None
        )

        with patch("gui.matrix_controller.ExtronIN1804Handler") as handler_factory:
            context = controller._make_context(
                operation_kind="full_refresh",
                ip_address="192.0.2.10",
                candidate_index=5,
                state_changing=False,
            )
            controller._submit(context, state["candidates"])
            with self.assertRaises(RuntimeError) as captured:
                controller._acquire_session(context, ())

        handler_factory.assert_not_called()
        self.assertIn("No credentials for current Matrix context", str(captured.exception))
        self.assertEqual([], advance_calls)

    def test_immutable_and_mutable_candidates_produce_equivalent_redaction_secrets(self):
        controller, state, pool = self.make_controller(
            candidates=[
                MappingProxyType({"username": "synth-k", "password": "synth-v"}),
                {"username": "synth-k", "password": "synth-v"},
            ]
        )
        immutable_context = controller._make_context(
            operation_kind="full_refresh",
            ip_address="192.0.2.10",
            candidate_index=0,
            state_changing=False,
        )
        mutable_context = controller._make_context(
            operation_kind="full_refresh",
            ip_address="192.0.2.10",
            candidate_index=1,
            state_changing=False,
        )
        controller._submit(immutable_context, state["candidates"])

        immutable_secrets = set(controller._candidate_secrets(immutable_context))
        mutable_secrets = set(controller._candidate_secrets(mutable_context))

        self.assertEqual({"synth-k", "synth-v"}, immutable_secrets)
        self.assertEqual(immutable_secrets, mutable_secrets)

    def test_immutable_candidate_values_are_redacted_from_public_error(self):
        controller, state, pool = self.make_controller(
            candidates=[
                MappingProxyType(
                    {"username": "synth-secret-user", "password": "synth-secret-pass"}
                )
            ]
        )
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        errors = []
        controller.errorAccepted.connect(lambda *args: errors.append(args))

        class FailingHandler:
            def __init__(self, **kwargs):
                self.log_callback = None
                self.connected = False

            def connect(self):
                self.connected = True

            def is_connected(self):
                return self.connected

            def get_full_status(self):
                raise RuntimeError("handler rejected synth-secret-user with synth-secret-pass")

            def disconnect(self):
                self.connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", FailingHandler):
            context = controller._make_context(
                operation_kind="full_refresh",
                ip_address="192.0.2.10",
                candidate_index=0,
                state_changing=False,
            )
            controller._submit(context, state["candidates"])
            controller._run_background_operation(context)

        self.assertEqual(1, len(errors))
        error_payload = str(errors[0])
        self.assertNotIn("synth-secret-pass", error_payload)
        self.assertNotIn("synth-secret-user", error_payload)

    def test_immutable_candidate_terminal_output_is_redacted(self):
        controller, state, pool = self.make_controller(
            candidates=[
                MappingProxyType(
                    {"username": "synth-term-user", "password": "synth-term-pass"}
                )
            ]
        )
        controller._request_keepalive_start = lambda: None
        controller._request_keepalive_stop = lambda: None
        terminal = []
        controller.terminalAccepted.connect(lambda *args: terminal.append(args))

        class EmittingHandler:
            def __init__(self, **kwargs):
                self.log_callback = None
                self.connected = False

            def connect(self):
                self.connected = True

            def is_connected(self):
                return self.connected

            def get_full_status(self):
                self.log_callback("auth user synth-term-user password synth-term-pass")
                return "In0 All\r\n"

            def disconnect(self):
                self.connected = False

        with patch("gui.matrix_controller.ExtronIN1804Handler", EmittingHandler):
            with patch("gui.matrix_controller.ExtronIN1804DataParser") as parser:
                parser.return_value.parse.return_value = {"model": "IN1804"}
                context = controller._make_context(
                    operation_kind="full_refresh",
                    ip_address="192.0.2.10",
                    candidate_index=0,
                    state_changing=False,
                )
                controller._submit(context, state["candidates"])
                controller._run_background_operation(context)

        self.assertEqual(1, len(terminal))
        term_payload = str(terminal[0])
        self.assertNotIn("synth-term-pass", term_payload)
        self.assertNotIn("synth-term-user", term_payload)

if __name__ == "__main__":
    unittest.main()
