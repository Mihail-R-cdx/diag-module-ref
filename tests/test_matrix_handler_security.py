import contextlib
import io
import unittest
from unittest.mock import patch

from core.exceptions import CommandOutcomeUnknownError, ConnectionError
from core.base_handler import BaseExtronMatrixHandler
from handlers.extron.in1804 import ExtronIN1804Handler


class ConcreteMatrixHandler(BaseExtronMatrixHandler):
    def get_device_info(self):
        return {}

    def get_status(self):
        return {}


class MatrixHandlerSecurityTests(unittest.TestCase):
    def test_telnet_authentication_does_not_print_or_log_actual_credentials(self):
        username = "matrix-secret-user"
        password = "matrix-secret-pass"
        handler = ConcreteMatrixHandler(
            "192.0.2.10",
            username=username,
            password=password,
        )
        handler.connection_protocol = "Telnet"
        reads = iter((
            f"Password: echoed {username}".encode(),
            f"> echoed {password}".encode(),
        ))
        sent = []
        logs = []
        stdout = io.StringIO()
        handler._read_until_patterns = lambda *_args, **_kwargs: next(reads)
        handler._send_bytes = sent.append
        handler.log_callback = logs.append

        with contextlib.redirect_stdout(stdout):
            self.assertTrue(handler._authenticate(f"login as: {username}".encode()))

        public_output = stdout.getvalue() + "\n".join(logs)
        self.assertIn("[send] <username>", public_output)
        self.assertIn("[send] <password>", public_output)
        self.assertNotIn(username, public_output)
        self.assertNotIn(password, public_output)
        self.assertEqual(
            [username.encode() + b"\r\n", password.encode() + b"\r\n"],
            sent,
        )

    def test_production_get_connections_transport_failure_is_structured(self):
        handler = ExtronIN1804Handler(
            "192.0.2.10",
            username="matrix-user",
            password="matrix-pass",
        )
        handler.socket = object()
        handler.authenticated = True
        handler._connected = True
        handler._send_bytes = lambda _payload: None
        handler._recv_bytes = lambda _size: (_ for _ in ()).throw(
            OSError("socket read failed")
        )

        with self.assertRaises(ConnectionError):
            handler.get_connections()

    def test_production_full_status_transport_failure_is_not_default_success(self):
        handler = ExtronIN1804Handler(
            "192.0.2.10",
            username="matrix-user",
            password="matrix-pass",
        )
        handler.socket = object()
        handler.authenticated = True
        handler._connected = True
        handler._send_bytes = lambda _payload: None
        handler._recv_bytes = lambda _size: (_ for _ in ()).throw(
            OSError("socket read failed")
        )

        with self.assertRaises(ConnectionError):
            handler.get_full_status()

    def test_post_send_auth_prompt_does_not_replay_route_command(self):
        handler = ExtronIN1804Handler(
            "192.0.2.10",
            username="matrix-user",
            password="matrix-pass",
        )
        handler.socket = object()
        handler.authenticated = True
        handler._connected = True
        handler.model = "IN1804"
        sent = []
        handler._send_bytes = sent.append
        handler._recv_bytes = lambda _size: b"Password:"

        with self.assertRaises(CommandOutcomeUnknownError):
            handler.set_connection(1, 3)

        self.assertEqual([b"3*1!\r"], sent)

    def test_route_empty_response_is_unknown_outcome_and_not_success(self):
        handler = ExtronIN1804Handler(
            "192.0.2.10",
            username="matrix-user",
            password="matrix-pass",
        )
        handler.socket = object()
        handler.authenticated = True
        handler._connected = True
        handler.model = "IN1804"
        sent = []
        handler._send_bytes = sent.append
        handler._recv_bytes = lambda _size: b""

        with patch("core.base_handler.time.sleep", lambda _seconds: None):
            with self.assertRaises(CommandOutcomeUnknownError):
                handler.set_connection(1, 3)

        self.assertEqual([b"3*1!\r"], sent)

    def test_read_only_empty_response_is_not_success(self):
        handler = ExtronIN1804Handler(
            "192.0.2.10",
            username="matrix-user",
            password="matrix-pass",
        )
        handler.socket = object()
        handler.authenticated = True
        handler._connected = True
        handler.inputs_num = 4
        sent = []
        handler._send_bytes = sent.append
        handler._recv_bytes = lambda _size: b""

        with patch("core.base_handler.time.sleep", lambda _seconds: None):
            with self.assertRaises(ConnectionError):
                handler.get_connections()

        self.assertEqual([b"!\r"], sent)

    def test_read_only_auth_recovery_is_bounded(self):
        handler = ExtronIN1804Handler(
            "192.0.2.10",
            username="matrix-user",
            password="matrix-pass",
        )
        handler.socket = object()
        handler.authenticated = True
        handler._connected = True
        handler.inputs_num = 4
        sent = []
        responses = iter((b"Password:", b"Password:"))
        handler._send_bytes = sent.append
        handler._read_response = lambda: next(responses)
        handler._authenticate = lambda *_args, **_kwargs: True

        with patch("core.base_handler.time.sleep", lambda _seconds: None):
            with self.assertRaises(ConnectionError):
                handler.get_connections()

        self.assertEqual([b"!\r", b"!\r"], sent)

    def test_read_only_auth_recovery_succeeds_within_budget(self):
        handler = ExtronIN1804Handler(
            "192.0.2.10",
            username="matrix-user",
            password="matrix-pass",
        )
        handler.socket = object()
        handler.authenticated = True
        handler._connected = True
        handler.inputs_num = 4
        sent = []
        responses = iter((b"Password:", b"In1 All\r\n"))
        handler._send_bytes = sent.append
        handler._read_response = lambda: next(responses)
        handler._authenticate = lambda *_args, **_kwargs: True

        with patch("core.base_handler.time.sleep", lambda _seconds: None):
            connections = handler.get_connections()

        self.assertEqual([1], connections)
        self.assertEqual([b"!\r", b"!\r"], sent)

    def test_route_echo_only_response_is_unknown_outcome(self):
        handler = ExtronIN1804Handler(
            "192.0.2.10",
            username="matrix-user",
            password="matrix-pass",
        )
        handler.socket = object()
        handler.authenticated = True
        handler._connected = True
        handler.model = "IN1804"
        sent = []
        handler._send_bytes = sent.append
        handler._read_response = lambda: b"3*1!\r\n"

        with patch("core.base_handler.time.sleep", lambda _seconds: None):
            with self.assertRaises(CommandOutcomeUnknownError):
                handler.set_connection(1, 3)

        self.assertEqual([b"3*1!\r"], sent)

    def test_read_only_echo_only_response_is_not_success(self):
        handler = ExtronIN1804Handler(
            "192.0.2.10",
            username="matrix-user",
            password="matrix-pass",
        )
        handler.socket = object()
        handler.authenticated = True
        handler._connected = True
        sent = []
        handler._send_bytes = sent.append
        handler._read_response = lambda: b"!\r\n"

        with patch("core.base_handler.time.sleep", lambda _seconds: None):
            with self.assertRaises(ConnectionError):
                handler.get_connections()

        self.assertEqual([b"!\r"], sent)

    def test_read_only_echo_plus_payload_is_success(self):
        handler = ExtronIN1804Handler(
            "192.0.2.10",
            username="matrix-user",
            password="matrix-pass",
        )
        handler.socket = object()
        handler.authenticated = True
        handler._connected = True
        handler.inputs_num = 4
        sent = []
        handler._send_bytes = sent.append
        handler._read_response = lambda: b"!\r\nIn1 All\r\n"

        with patch("core.base_handler.time.sleep", lambda _seconds: None):
            connections = handler.get_connections()

        self.assertEqual([1], connections)
        self.assertEqual([b"!\r"], sent)


if __name__ == "__main__":
    unittest.main()
