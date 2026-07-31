import contextlib
import io
import ssl
import unittest
from unittest.mock import patch

from core.exceptions import AuthenticationError
from core.exceptions import ConnectionError
from core.exceptions import ProtocolError
from core.te20_worker import HuaweiTE20Worker
from core.worker import (
    AtenPDUWorker,
    BiampTesiraForteCIWorker,
    HuaweiBar310Worker,
)


CURRENT_USER = "synthetic-user-a"
CURRENT_PASSWORD = "synthetic-password-a"
OTHER_USER = "synthetic-user-b"
OTHER_PASSWORD = "synthetic-password-b"
OTHER_TOKEN = "synthetic-token"


def active_chain():
    return [
        {"username": OTHER_USER, "password": OTHER_PASSWORD},
        {"username": CURRENT_USER, "password": CURRENT_PASSWORD},
        {"token": OTHER_TOKEN},
    ]


def collect_outcomes(worker):
    results = []
    errors = []
    terminal = []
    finished = []
    worker.signals.result.connect(results.append)
    worker.signals.error.connect(errors.append)
    worker.signals.terminal_log.connect(terminal.append)
    worker.signals.finished.connect(lambda: finished.append(True))
    return results, errors, terminal, finished


class TE20CredentialRetryOwnershipTests(unittest.TestCase):
    def make_worker(self):
        worker = HuaweiTE20Worker(
            "192.0.2.20",
            username=CURRENT_USER,
            password=CURRENT_PASSWORD,
        )
        worker.creds_list = active_chain()
        worker.current_idx = 1
        return worker

    def test_authentication_failure_uses_only_assigned_credential_and_emits_once(self):
        captured = []

        class AuthFailingHandler:
            def __init__(self, **kwargs):
                captured.append(kwargs)
                self.port = kwargs["port"]
                self.use_ssl = kwargs["use_ssl"]

            def connect(self):
                raise AuthenticationError(
                    f"auth failed {CURRENT_PASSWORD} {OTHER_PASSWORD} {OTHER_TOKEN}"
                )

            def disconnect(self):
                pass

        worker = self.make_worker()
        worker._build_unique_profiles = lambda: [
            {"port": 80, "use_ssl": False, "label": "HTTP:80"},
            {"port": 443, "use_ssl": True, "label": "HTTPS:443"},
        ]
        results, errors, terminal, finished = collect_outcomes(worker)
        stdout = io.StringIO()

        with patch("core.te20_worker.HuaweiTE20Handler", AuthFailingHandler), \
                contextlib.redirect_stdout(stdout):
            worker.run()

        self.assertEqual(1, len(captured))
        self.assertEqual(CURRENT_USER, captured[0]["username"])
        self.assertEqual(CURRENT_PASSWORD, captured[0]["password"])
        self.assertEqual(1, worker.current_idx)
        self.assertEqual([], results)
        self.assertEqual(1, len(errors))
        self.assertEqual("authentication_error", errors[0][0])
        self.assertEqual([True], finished)
        self.assert_public_output_redacted(stdout, errors, terminal)

    def test_non_authentication_failures_never_select_another_credential(self):
        failures = [
            TimeoutError(f"timeout {OTHER_PASSWORD}"),
            ssl.SSLError(f"ssl {OTHER_PASSWORD}"),
            ConnectionRefusedError(f"refused {OTHER_PASSWORD}"),
            ValueError(f"protocol {OTHER_PASSWORD}"),
        ]
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                captured = []

                class FailingHandler:
                    def __init__(self, **kwargs):
                        captured.append(kwargs)
                        self.port = kwargs["port"]
                        self.use_ssl = kwargs["use_ssl"]

                    def connect(self):
                        raise failure

                    def disconnect(self):
                        pass

                worker = self.make_worker()
                worker._build_unique_profiles = lambda: [
                    {"port": 80, "use_ssl": False, "label": "HTTP:80"}
                ]
                results, errors, terminal, finished = collect_outcomes(worker)
                stdout = io.StringIO()

                with patch("core.te20_worker.HuaweiTE20Handler", FailingHandler), \
                        contextlib.redirect_stdout(stdout):
                    worker.run()

                self.assertEqual(1, len(captured))
                self.assertEqual(CURRENT_USER, captured[0]["username"])
                self.assertEqual(CURRENT_PASSWORD, captured[0]["password"])
                self.assertEqual(1, worker.current_idx)
                self.assertEqual([], results)
                self.assertEqual(1, len(errors))
                self.assertEqual("connection_error", errors[0][0])
                self.assertEqual([True], finished)
                self.assert_public_output_redacted(stdout, errors, terminal)

    def test_transport_fallback_preserves_credential_and_emits_one_result(self):
        captured = []

        class TransportHandler:
            def __init__(self, **kwargs):
                captured.append(kwargs)
                self.port = kwargs["port"]
                self.use_ssl = kwargs["use_ssl"]

            def connect(self):
                if self.port == 80:
                    raise TimeoutError("HTTP transport unavailable")
                return True

            def get_status(self):
                return {"status": "ok"}

            def disconnect(self):
                pass

        worker = self.make_worker()
        worker._build_unique_profiles = lambda: [
            {"port": 80, "use_ssl": False, "label": "HTTP:80"},
            {"port": 443, "use_ssl": True, "label": "HTTPS:443"},
        ]
        results, errors, terminal, finished = collect_outcomes(worker)

        with patch("core.te20_worker.HuaweiTE20Handler", TransportHandler), patch(
            "core.te20_worker.HuaweiTE20DataParser.parse_raw_data",
            side_effect=lambda data: dict(data),
        ), contextlib.redirect_stdout(io.StringIO()):
            worker.run()

        self.assertEqual([80, 443], [item["port"] for item in captured])
        self.assertEqual(
            [(CURRENT_USER, CURRENT_PASSWORD)] * 2,
            [(item["username"], item["password"]) for item in captured],
        )
        self.assertEqual(1, worker.current_idx)
        self.assertEqual(1, len(results))
        self.assertEqual([], errors)
        self.assertEqual([True], finished)

    def assert_public_output_redacted(self, stdout, errors, terminal):
        public_output = stdout.getvalue() + repr(errors) + "\n".join(terminal)
        for secret in (
            CURRENT_USER,
            CURRENT_PASSWORD,
            OTHER_USER,
            OTHER_PASSWORD,
            OTHER_TOKEN,
        ):
            self.assertNotIn(secret, public_output)


class Bar310CredentialRetryOwnershipTests(unittest.TestCase):
    def make_worker(self):
        worker = HuaweiBar310Worker(
            "192.0.2.31",
            username=CURRENT_USER,
            password=CURRENT_PASSWORD,
            creds_list=active_chain(),
        )
        worker.current_idx = 1
        return worker

    def run_failure(self, failure):
        captured = []

        class FailingHandler:
            def __init__(self, **kwargs):
                captured.append(kwargs)
                self.port = kwargs["port"]
                self.use_ssl = True

            def connect(self):
                raise failure

            def disconnect(self):
                pass

        worker = self.make_worker()
        results, errors, terminal, finished = collect_outcomes(worker)
        stdout = io.StringIO()
        with patch("core.workers.codec_polling.CloudLinkBar310Handler", FailingHandler), \
                contextlib.redirect_stdout(stdout):
            worker.run()
        return worker, captured, results, errors, terminal, finished, stdout

    def test_authentication_failure_uses_only_assigned_credential_and_emits_once(self):
        evidence = self.run_failure(
            AuthenticationError(
                f"auth failed {CURRENT_PASSWORD} {OTHER_PASSWORD} {OTHER_TOKEN}"
            )
        )
        worker, captured, results, errors, terminal, finished, stdout = evidence

        self.assert_single_failed_attempt(
            worker, captured, results, errors, finished, "authentication_error"
        )
        self.assert_public_output_redacted(stdout, errors, terminal)

    def test_non_authentication_failure_does_not_try_another_credential(self):
        evidence = self.run_failure(RuntimeError(f"transport {OTHER_PASSWORD}"))
        worker, captured, results, errors, terminal, finished, stdout = evidence

        self.assert_single_failed_attempt(
            worker, captured, results, errors, finished, "connection_error"
        )
        self.assert_public_output_redacted(stdout, errors, terminal)

    def test_success_emits_one_result_without_worker_success_index_cache(self):
        captured = []

        class SuccessfulHandler:
            def __init__(self, **kwargs):
                captured.append(kwargs)
                self.port = kwargs["port"]
                self.use_ssl = True

            def connect(self):
                return True

            def get_status(self):
                return {"status": "ok"}

            def disconnect(self):
                pass

        worker = self.make_worker()
        results, errors, _terminal, finished = collect_outcomes(worker)
        with patch("core.workers.codec_polling.CloudLinkBar310Handler", SuccessfulHandler), patch(
            "core.workers.codec_polling.HuaweiBar310DataParser.parse_raw_data",
            side_effect=lambda data: dict(data),
        ), contextlib.redirect_stdout(io.StringIO()):
            worker.run()

        self.assertEqual(1, len(captured))
        self.assertEqual(CURRENT_USER, captured[0]["username"])
        self.assertEqual(CURRENT_PASSWORD, captured[0]["password"])
        self.assertEqual(1, worker.current_idx)
        self.assertFalse(hasattr(worker, "current_credential_index"))
        self.assertEqual(1, len(results))
        self.assertEqual([], errors)
        self.assertEqual([True], finished)

    def assert_single_failed_attempt(
        self, worker, captured, results, errors, finished, expected_category
    ):
        self.assertEqual(1, len(captured))
        self.assertEqual(CURRENT_USER, captured[0]["username"])
        self.assertEqual(CURRENT_PASSWORD, captured[0]["password"])
        self.assertEqual(1, worker.current_idx)
        self.assertFalse(hasattr(worker, "current_credential_index"))
        self.assertEqual([], results)
        self.assertEqual(1, len(errors))
        self.assertEqual(expected_category, errors[0][0])
        self.assertEqual([True], finished)

    def assert_public_output_redacted(self, stdout, errors, terminal):
        public_output = stdout.getvalue() + repr(errors) + "\n".join(terminal)
        for secret in (
            CURRENT_USER,
            CURRENT_PASSWORD,
            OTHER_USER,
            OTHER_PASSWORD,
            OTHER_TOKEN,
        ):
            self.assertNotIn(secret, public_output)


class RemainingProductionWorkerRetryOwnershipTests(unittest.TestCase):
    worker_cases = (
        (
            "Biamp",
            BiampTesiraForteCIWorker,
            "handlers.biamp.tesira_forte_ci.BiampTesiraForteCIHandler",
        ),
        (
            "Aten",
            AtenPDUWorker,
            "handlers.aten.pdu.AtenPDUHandler",
        ),
    )

    def test_authentication_failure_uses_only_gui_assigned_credential(self):
        for label, worker_class, handler_target in self.worker_cases:
            with self.subTest(worker=label):
                self.assert_single_attempt(
                    worker_class,
                    handler_target,
                    AuthenticationError(f"auth {OTHER_PASSWORD}"),
                    "authentication_error",
                )

    def test_non_authentication_failure_never_selects_another_credential(self):
        for label, worker_class, handler_target in self.worker_cases:
            with self.subTest(worker=label):
                self.assert_single_attempt(
                    worker_class,
                    handler_target,
                    RuntimeError(f"transport {OTHER_PASSWORD}"),
                    "connection_error",
                )

    def test_biamp_non_retry_authentication_protocol_outcome_is_not_authentication_error(self):
        self.assert_single_attempt(
            BiampTesiraForteCIWorker,
            "handlers.biamp.tesira_forte_ci.BiampTesiraForteCIHandler",
            ProtocolError("Paramiko BadAuthenticationType did not confirm rejection"),
            "connection_error",
        )

    def test_biamp_missing_telnet_login_prompt_is_connection_error(self):
        self.assert_single_attempt(
            BiampTesiraForteCIWorker,
            "handlers.biamp.tesira_forte_ci.BiampTesiraForteCIHandler",
            ConnectionError("Biamp Telnet login prompt was not received before timeout."),
            "connection_error",
        )

    def assert_single_attempt(
        self, worker_class, handler_target, failure, expected_category
    ):
        captured = []

        class FailingHandler:
            def __init__(self, **kwargs):
                captured.append(kwargs)

            def connect(self):
                raise failure

            def disconnect(self):
                pass

        worker = worker_class(
            "192.0.2.40",
            username=CURRENT_USER,
            password=CURRENT_PASSWORD,
        )
        worker.creds_list = active_chain()
        worker.current_idx = 1
        results, errors, terminal, finished = collect_outcomes(worker)
        stdout = io.StringIO()

        with patch(handler_target, FailingHandler), contextlib.redirect_stdout(stdout):
            worker.run()

        self.assertEqual(1, len(captured))
        self.assertEqual(CURRENT_USER, captured[0]["username"])
        self.assertEqual(CURRENT_PASSWORD, captured[0]["password"])
        self.assertEqual(1, worker.current_idx)
        self.assertEqual([], results)
        self.assertEqual(1, len(errors))
        self.assertEqual(expected_category, errors[0][0])
        self.assertEqual([True], finished)
        public_output = stdout.getvalue() + repr(errors) + "\n".join(terminal)
        for secret in (
            CURRENT_USER,
            CURRENT_PASSWORD,
            OTHER_USER,
            OTHER_PASSWORD,
            OTHER_TOKEN,
        ):
            self.assertNotIn(secret, public_output)


if __name__ == "__main__":
    unittest.main()
