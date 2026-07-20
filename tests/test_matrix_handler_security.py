import contextlib
import io
import unittest

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


if __name__ == "__main__":
    unittest.main()
