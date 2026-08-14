import threading
import unittest
from unittest.mock import Mock, patch

import paramiko
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
from core.interactive_session import _default_handler_factory
from handlers.huawei.te20 import HuaweiTE20Handler
from handlers.huawei.bar310 import CloudLinkBar310Handler
from handlers.huawei.te40 import HuaweiTE40Handler
from handlers.polycom.rpg310 import PolycomRPG310Handler


class CloudLinkBoxInteractiveFactoryTests(unittest.TestCase):
    def test_box_context_uses_shared_handler_with_box_identity(self):
        handler = _default_handler_factory(
            "CloudLink Box 310",
            {"ip_address": "192.0.2.10", "username": "user", "password": "pass"},
        )
        self.assertEqual("Huawei CloudLink Box 310", handler.device_model)


class OfflineHuaweiMuteMixin:
    def __init__(self, *, events, set_attempts, audio_outcomes=None, **kwargs):
        super().__init__(**kwargs)
        self.events = events
        self.set_attempts = set_attempts
        self.audio_outcomes = (
            audio_outcomes
            if audio_outcomes is not None
            else [{"success": 1, "data": {"MicSwitch": 1, "micValue": 0}}]
        )

    def connect(self):
        self.events.append(("https", self.credentials["password"]))
        self._connected = True
        return True

    def disconnect(self):
        self._connected = False

    def send_command(self, command, data=None):
        del data
        self.events.append(("read", self.credentials["password"], command))
        outcomes = self.audio_outcomes
        outcome = outcomes.pop(0) if len(outcomes) > 1 else outcomes[0]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def set_microphone_volume(self, value):
        self.events.append(("mute-set", self.credentials["password"], value))
        self.set_attempts.append(value)
        if len(self.set_attempts) == 1:
            raise CommandOutcomeUnknownError("synthetic ambiguous result")
        return True


class OfflineTE20Handler(OfflineHuaweiMuteMixin, HuaweiTE20Handler):
    pass


class OfflineTE40Handler(OfflineHuaweiMuteMixin, HuaweiTE40Handler):
    pass


class FakeSSHChannel:
    def __init__(self, password, events):
        self.password = password
        self.events = events
        self.closed = False
        self.muted = False
        self.pending = b""

    def close(self):
        self.closed = True

    def recv_ready(self):
        return bool(self.pending)

    def recv(self, _buffer_size):
        pending, self.pending = self.pending, b""
        return pending

    def send(self, command):
        command = command.strip()
        self.events.append(("command", self.password, command))
        if command == "mute near on":
            self.muted = True
            self.pending = b"mute near on\n"
        elif command == "mute near off":
            self.muted = False
            self.pending = b"mute near off\n"
        elif command == "mute near get":
            state = b"on" if self.muted else b"off"
            self.pending = b"mute near " + state + b"\n"
        return len(command)


class FakeSSHClient:
    def __init__(self, events, auth_rejects=(), transport_failures=()):
        self.events = events
        self.auth_rejects = set(auth_rejects)
        self.transport_failures = set(transport_failures)
        self.password = None

    def set_missing_host_key_policy(self, _policy):
        pass

    def connect(self, **kwargs):
        self.password = kwargs["password"]
        self.events.append(("ssh", self.password))
        if self.password in self.auth_rejects:
            raise paramiko.AuthenticationException("synthetic rejection")
        if self.password in self.transport_failures:
            raise paramiko.SSHException("synthetic transport failure")

    def invoke_shell(self):
        return FakeSSHChannel(self.password, self.events)

    def close(self):
        pass


class OfflinePolycomHandler(PolycomRPG310Handler):
    def __init__(self, *, events, **kwargs):
        super().__init__(**kwargs)
        self.events = events

    def connect(self):
        self.events.append(("https", self.password))
        self.opener = object()
        self.authenticated = True
        return True

    def disconnect(self):
        self.opener = None
        self.authenticated = False
        self._disconnect_ssh()


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

    @staticmethod
    def count_recoveries(controller):
        recoveries = []
        recover_once = controller._recover_once

        def counted_recovery(*args, **kwargs):
            recoveries.append(args[2])
            return recover_once(*args, **kwargs)

        controller._recover_once = counted_recovery
        return recoveries

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

    def test_stale_after_factory_never_connects(self):
        calls = []
        controller = None

        class Handler:
            def connect(self):
                calls.append("connect")
                return True

            def disconnect(self):
                calls.append("disconnect")

            def is_connected(self):
                return False

            def read(self):
                calls.append("read")
                return "unexpected"

        def factory(_model, _kwargs):
            calls.append("factory")
            controller.invalidate_context()
            return Handler()

        controller = InteractiveSessionController(handler_factory=factory)
        _results, _errors, dropped = self.collect(controller)
        controller.activate_context("Huawei TE40", "192.0.2.10", ({"username": "u", "password": "p"},))
        controller.submit(InteractiveOperation(kind="read", method="read"))
        controller.wait_until_idle(2)
        self.drain()
        self.assertEqual("factory", calls[0])
        self.assertNotIn("connect", calls)
        self.assertNotIn("read", calls)
        self.assertEqual(1, len(dropped))
        controller.shutdown()

    def test_box_context_acquires_shared_handler_for_read_only_operation_without_aliasing(self):
        captured = []

        class FakeBoxHandler:
            def __init__(self, **kwargs):
                captured.append(kwargs)
                self.connected = False

            def connect(self):
                self.connected = True
                return True

            def disconnect(self):
                self.connected = False

            def is_connected(self):
                return self.connected

            def read(self):
                return "box-status"

        controller = InteractiveSessionController()
        results, errors, _ = self.collect(controller)
        with patch("handlers.huawei.bar310.CloudLinkBar310Handler", FakeBoxHandler):
            controller.activate_context(
                "CloudLink Box 310", "192.0.2.20", ({"username": "u", "password": "p"},)
            )
            controller.submit(InteractiveOperation(kind="read", method="read", semantic=OperationSemantic.READ_ONLY))
            controller.wait_until_idle(2)
            self.drain()
        controller.shutdown()

        self.assertEqual([], errors)
        self.assertEqual("CloudLink Box 310", results[0]["model"])
        self.assertEqual("box-status", results[0]["value"])
        self.assertEqual("Huawei CloudLink Box 310", captured[0]["expected_identity"])
        self.assertEqual(443, captured[0]["port"])

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

    def test_cloudlink_new_login_authentication_advances_application_credential_chain(self):
        attempts = []

        class Response:
            def __init__(self, status_code, text="{}"):
                self.status_code = status_code
                self.text = text

        def factory(_model, kwargs):
            attempts.append(kwargs["password"])
            handler = CloudLinkBar310Handler(**kwargs)
            handler._make_request = Mock(side_effect=[
                {"success": 1},
                {"success": 1, "data": {"acCSRFToken": "legacy-token"}},
            ])
            modern_session = Mock()
            handler._new_modern_session = Mock(return_value=modern_session)
            if kwargs["password"] == "rejected":
                modern_session.request = Mock(return_value=Response(401))
            else:
                modern_session.request = Mock(side_effect=[
                    Response(200, '{"success": 1}'),
                    Response(200, '{"success": 1, "data": {"acCSRFToken": "modern-token"}}'),
                ])
            handler.read = lambda: "connected"
            return handler

        controller = InteractiveSessionController(handler_factory=factory)
        results, errors, _ = self.collect(controller)
        controller.activate_context(
            "CloudLink Bar 310",
            "192.0.2.10",
            (
                {"username": "synthetic", "password": "rejected"},
                {"username": "synthetic", "password": "accepted"},
            ),
        )
        controller.submit(InteractiveOperation(kind="read", method="read"))
        controller.wait_until_idle(2)
        self.drain()
        controller.shutdown()

        self.assertEqual([], errors)
        self.assertEqual("connected", results[0]["value"])
        self.assertEqual(1, results[0]["credential_index"])
        self.assertEqual(["rejected", "accepted"], attempts)

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

    def test_session_invalid_recovery_keeps_the_same_cloudlink_credential(self):
        controller, calls = self.make_controller(
            {"read": [SessionInvalidError("expired"), "recovered"]}
        )
        results, errors, _ = self.collect(controller)
        controller.activate_context(
            "CloudLink Bar 310",
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
        self.assertEqual("recovered", results[0]["value"])
        self.assertEqual(0, results[0]["credential_index"])
        self.assertEqual(
            ["one", "one"],
            [call[2] for call in calls if call[0] == "connect"],
        )

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

    def test_real_huawei_readback_reconciles_ambiguous_mute_from_unmuted(self):
        for model, handler_type in (
            ("Huawei TE20", OfflineTE20Handler),
            ("Huawei TE40", OfflineTE40Handler),
        ):
            with self.subTest(model=model):
                events = []
                set_attempts = []

                def factory(selected_model, kwargs):
                    self.assertEqual(model, selected_model)
                    return handler_type(
                        events=events,
                        set_attempts=set_attempts,
                        **kwargs,
                    )

                controller = InteractiveSessionController(handler_factory=factory)
                results, errors, _ = self.collect(controller)
                controller.activate_context(
                    model,
                    "192.0.2.10",
                    ({"username": "synthetic", "password": "credential-a"},),
                )
                controller.submit(
                    InteractiveOperation(
                        kind="microphone_set",
                        method="set_microphone_volume",
                        args=(0,),
                        semantic=OperationSemantic.DESIRED_STATE,
                        readback_method="get_microphone_volume",
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
                self.assertEqual([0, 0], set_attempts)
                self.assertEqual(
                    [("https", "credential-a"), ("https", "credential-a")],
                    [event for event in events if event[0] == "https"],
                )

    def test_real_huawei_missing_mute_evidence_refuses_reconciled_resend(self):
        for model, handler_type in (
            ("Huawei TE20", OfflineTE20Handler),
            ("Huawei TE40", OfflineTE40Handler),
        ):
            with self.subTest(model=model):
                events = []
                set_attempts = []
                audio_outcomes = [{"success": 1, "data": {"micValue": 0}}]

                def factory(_model, kwargs):
                    return handler_type(
                        events=events,
                        set_attempts=set_attempts,
                        audio_outcomes=audio_outcomes,
                        **kwargs,
                    )

                controller = InteractiveSessionController(handler_factory=factory)
                results, errors, _ = self.collect(controller)
                controller.activate_context(
                    model,
                    "192.0.2.10",
                    ({"username": "synthetic", "password": "credential-a"},),
                )
                controller.submit(
                    InteractiveOperation(
                        kind="microphone_set",
                        method="set_microphone_volume",
                        args=(0,),
                        semantic=OperationSemantic.DESIRED_STATE,
                        readback_method="get_microphone_volume",
                        original="Unmuted",
                        target="Muted",
                    )
                )
                controller.wait_until_idle(2)
                self.drain()
                controller.shutdown()

                self.assertEqual([], results)
                self.assertEqual("unknown_command_outcome", errors[0]["category"])
                self.assertEqual([0], set_attempts)
                self.assertEqual(1, len([event for event in events if event[0] == "read"]))

    def test_te20_setter_missing_mute_evidence_reaches_controller_as_failure(self):
        commands = []
        diagnostic_reads = []

        def factory(model, kwargs):
            self.assertEqual("Huawei TE20", model)
            handler = HuaweiTE20Handler(**kwargs)
            outcomes = [
                {"success": 0},
                {"success": 1, "data": {"mic1Value": 0}},
            ]

            def connect():
                handler._connected = True
                return True

            def disconnect():
                handler._connected = False

            def send_command(command, data=None):
                del data
                commands.append(command)
                return outcomes.pop(0)

            def get_audio_status():
                diagnostic_reads.append("get_audio_status")
                return {"mute": "Off"}

            handler.connect = connect
            handler.disconnect = disconnect
            handler.send_command = send_command
            handler.get_audio_status = get_audio_status
            return handler

        controller = InteractiveSessionController(handler_factory=factory)
        results, errors, _ = self.collect(controller)
        controller.activate_context(
            "Huawei TE20",
            "192.0.2.10",
            ({"username": "synthetic", "password": "credential-a"},),
        )
        with patch("handlers.huawei.te20.time.sleep", return_value=None):
            controller.submit(
                InteractiveOperation(
                    kind="microphone_set",
                    method="set_microphone_volume",
                    args=(1,),
                    semantic=OperationSemantic.DESIRED_STATE,
                    readback_method="get_microphone_volume",
                    original="Muted",
                    target="Unmuted",
                )
            )
            controller.wait_until_idle(2)
            self.drain()
            controller.shutdown()

        self.assertEqual([], results)
        self.assertEqual("command_error", errors[0]["category"])
        self.assertEqual(["WEB_OpenMicAPI", "get_audio_status"], commands)
        self.assertEqual([], diagnostic_reads)

    def test_real_huawei_muted_readback_does_not_send_twice(self):
        for model, handler_type in (
            ("Huawei TE20", OfflineTE20Handler),
            ("Huawei TE40", OfflineTE40Handler),
        ):
            with self.subTest(model=model):
                events = []
                set_attempts = []
                audio_outcomes = [{"success": 1, "data": {"MicSwitch": 0}}]

                def factory(_model, kwargs):
                    return handler_type(
                        events=events,
                        set_attempts=set_attempts,
                        audio_outcomes=audio_outcomes,
                        **kwargs,
                    )

                controller = InteractiveSessionController(handler_factory=factory)
                results, errors, _ = self.collect(controller)
                controller.activate_context(
                    model,
                    "192.0.2.10",
                    ({"username": "synthetic", "password": "credential-a"},),
                )
                controller.submit(
                    InteractiveOperation(
                        kind="microphone_set",
                        method="set_microphone_volume",
                        args=(0,),
                        semantic=OperationSemantic.DESIRED_STATE,
                        readback_method="get_microphone_volume",
                        original="Unmuted",
                        target="Muted",
                    )
                )
                controller.wait_until_idle(2)
                self.drain()
                controller.shutdown()

                self.assertEqual([], errors)
                self.assertEqual("Muted", results[0]["value"])
                self.assertEqual([0], set_attempts)

    def test_real_huawei_expired_readback_reaches_controller_session_path(self):
        for model, handler_type in (
            ("Huawei TE20", OfflineTE20Handler),
            ("Huawei TE40", OfflineTE40Handler),
        ):
            with self.subTest(model=model):
                events = []
                audio_outcomes = [
                    SessionInvalidError("expired"),
                    SessionInvalidError("still expired"),
                ]

                def factory(_model, kwargs):
                    return handler_type(
                        events=events,
                        set_attempts=[],
                        audio_outcomes=audio_outcomes,
                        **kwargs,
                    )

                controller = InteractiveSessionController(handler_factory=factory)
                results, errors, _ = self.collect(controller)
                controller.activate_context(
                    model,
                    "192.0.2.10",
                    ({"username": "synthetic", "password": "credential-a"},),
                )
                controller.submit(
                    InteractiveOperation(
                        kind="microphone_read",
                        method="get_microphone_volume",
                    )
                )
                controller.wait_until_idle(2)
                self.drain()
                controller.shutdown()

                self.assertEqual([], results)
                self.assertEqual("session_invalid", errors[0]["category"])
                self.assertEqual(2, len([event for event in events if event[0] == "https"]))
                self.assertEqual(2, len([event for event in events if event[0] == "read"]))

    def test_polycom_lazy_ssh_auth_advances_inside_single_recovery_cycle(self):
        events = []

        def factory(model, kwargs):
            self.assertEqual("Polycom RPG 310", model)
            return OfflinePolycomHandler(events=events, **kwargs)

        controller = InteractiveSessionController(handler_factory=factory)
        recoveries = self.count_recoveries(controller)
        results, errors, _ = self.collect(controller)
        controller.activate_context(
            "Polycom RPG 310",
            "192.0.2.10",
            (
                {"username": "synthetic", "password": "credential-a"},
                {"username": "synthetic", "password": "credential-b"},
            ),
        )
        ssh_factory = lambda: FakeSSHClient(
            events,
            auth_rejects={"credential-a"},
        )
        with patch(
            "handlers.polycom.rpg310.paramiko.SSHClient",
            side_effect=ssh_factory,
        ), patch("handlers.polycom.rpg310.time.sleep", return_value=None):
            controller.submit(
                InteractiveOperation(
                    kind="microphone_set",
                    method="set_microphone_volume",
                    args=(0,),
                    semantic=OperationSemantic.DESIRED_STATE,
                    readback_method="get_microphone_volume",
                    original="Unmuted",
                    target="Muted",
                )
            )
            controller.wait_until_idle(2)
            self.drain()
            controller.shutdown()

        self.assertEqual([], errors)
        self.assertTrue(results[0]["value"])
        self.assertEqual(1, results[0]["credential_index"])
        self.assertEqual(1, len(recoveries))
        self.assertEqual(
            [
                ("https", "credential-a"),
                ("https", "credential-a"),
                ("https", "credential-b"),
            ],
            [event for event in events if event[0] == "https"],
        )
        self.assertEqual(
            [
                ("ssh", "credential-a"),
                ("ssh", "credential-a"),
                ("ssh", "credential-b"),
            ],
            [event for event in events if event[0] == "ssh"],
        )
        state_changes = [
            event
            for event in events
            if event[0] == "command" and event[2] == "mute near on"
        ]
        self.assertEqual([("command", "credential-b", "mute near on")], state_changes)

    def test_polycom_lazy_ssh_transport_failure_does_not_advance_credential(self):
        events = []

        def factory(_model, kwargs):
            return OfflinePolycomHandler(events=events, **kwargs)

        controller = InteractiveSessionController(handler_factory=factory)
        recoveries = self.count_recoveries(controller)
        results, errors, _ = self.collect(controller)
        controller.activate_context(
            "Polycom RPG 310",
            "192.0.2.10",
            (
                {"username": "synthetic", "password": "credential-a"},
                {"username": "synthetic", "password": "credential-b"},
            ),
        )
        ssh_factory = lambda: FakeSSHClient(
            events,
            transport_failures={"credential-a"},
        )
        with patch(
            "handlers.polycom.rpg310.paramiko.SSHClient",
            side_effect=ssh_factory,
        ), patch("handlers.polycom.rpg310.time.sleep", return_value=None):
            controller.submit(
                InteractiveOperation(
                    kind="microphone_set",
                    method="set_microphone_volume",
                    args=(0,),
                    semantic=OperationSemantic.DESIRED_STATE,
                    readback_method="get_microphone_volume",
                    original="Unmuted",
                    target="Muted",
                )
            )
            controller.wait_until_idle(2)
            self.drain()
            controller.shutdown()

        self.assertEqual([], results)
        self.assertEqual("connection_error", errors[0]["category"])
        self.assertEqual(1, len(recoveries))
        self.assertEqual(
            ["credential-a", "credential-a"],
            [event[1] for event in events if event[0] == "https"],
        )
        self.assertNotIn("credential-b", [event[1] for event in events])

    def test_polycom_rejected_lazy_ssh_credentials_advance_without_wraparound(self):
        events = []

        def factory(_model, kwargs):
            return OfflinePolycomHandler(events=events, **kwargs)

        controller = InteractiveSessionController(handler_factory=factory)
        recoveries = self.count_recoveries(controller)
        results, errors, _ = self.collect(controller)
        controller.activate_context(
            "Polycom RPG 310",
            "192.0.2.10",
            tuple(
                {"username": "synthetic", "password": password}
                for password in ("credential-a", "credential-b", "credential-c")
            ),
        )
        ssh_factory = lambda: FakeSSHClient(
            events,
            auth_rejects={"credential-a", "credential-b"},
        )
        with patch(
            "handlers.polycom.rpg310.paramiko.SSHClient",
            side_effect=ssh_factory,
        ), patch("handlers.polycom.rpg310.time.sleep", return_value=None):
            controller.submit(InteractiveOperation(kind="read", method="get_microphone_volume"))
            controller.wait_until_idle(2)
            self.drain()
            controller.shutdown()

        self.assertEqual([], errors)
        self.assertEqual("Unmuted", results[0]["value"])
        self.assertEqual(2, results[0]["credential_index"])
        self.assertEqual(1, len(recoveries))
        self.assertEqual(
            ["credential-a", "credential-a", "credential-b", "credential-c"],
            [event[1] for event in events if event[0] == "ssh"],
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
