import contextlib
import io
import unittest

from core.base_handler import BaseExtronMatrixHandler


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


if __name__ == "__main__":
    unittest.main()
