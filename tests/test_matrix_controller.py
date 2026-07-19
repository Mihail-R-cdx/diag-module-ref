import os
import unittest
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

    def make_controller(self, *, ip="192.0.2.10", revision=1, candidates=None):
        from gui.matrix_controller import MatrixController

        pool = CapturingThreadPool()
        state = {
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
            context_provider=lambda: ("Extron IN1804", state["ip"]),
            credential_candidates_provider=lambda _model, _ip: state["candidates"],
            credential_index_provider=lambda _model, _ip, _candidates: state["index"],
            credential_advance_provider=lambda _model, _ip, candidates, current, _op: (
                current + 1 if current + 1 < len(tuple(candidates or ())) else None
            ),
            credential_revision_provider=lambda: state["revision"],
            thread_pool=pool,
        )
        return controller, state, pool

    def test_route_intent_submits_background_operation_without_direct_send(self):
        controller, _state, pool = self.make_controller()
        controller.request_route(1, 4)

        self.assertEqual(1, len(pool.runnables))
        context = pool.runnables[0].context
        self.assertEqual("route", context.operation_kind)
        self.assertTrue(context.state_changing)
        self.assertEqual(1, context.output_num)
        self.assertEqual(4, context.input_num)

    def test_stale_result_is_suppressed(self):
        controller, _state, _pool = self.make_controller()
        accepted = []
        controller.resultAccepted.connect(lambda data, handle: accepted.append((data, handle)))

        stale = controller._make_context(
            operation_kind="full_refresh",
            ip_address="192.0.2.10",
            candidate_index=0,
            state_changing=False,
        )
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
            revised_handler = controller._acquire_session(revised, ())

            different_ip = controller._make_context(
                operation_kind="quick_refresh",
                ip_address="192.0.2.11",
                candidate_index=0,
                state_changing=False,
            )
            different_handler = controller._acquire_session(different_ip, ())

        for runnable in pool.runnables:
            if not hasattr(runnable, "context") or runnable.context.operation_kind == "cleanup":
                runnable.run()

        self.assertIsNot(first_handler, revised_handler)
        self.assertIsNot(revised_handler, different_handler)
        self.assertEqual(3, len([event for event in events if event[0] == "init"]))
        self.assertGreaterEqual(
            len([event for event in events if event[0] == "disconnect"]),
            2,
        )
        self.assertTrue(pool.runnables)

    def test_route_auth_before_send_uses_next_candidate(self):
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
                pass

        with patch("gui.matrix_controller.ExtronIN1804Handler", Handler):
            controller.request_route(1, 3)
            pool.runnables.pop(0).run()
            pool.runnables.pop(0).run()

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


if __name__ == "__main__":
    unittest.main()
