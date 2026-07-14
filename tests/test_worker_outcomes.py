import ast
import contextlib
import inspect
import io
import ssl
import textwrap
import unittest
from unittest.mock import patch

from core.exceptions import AuthenticationError
from core.te20_worker import HuaweiTE20Worker
from core.worker import (
    AtenPDUWorker,
    BiampTesiraForteCIWorker,
    ExtronIN1804Worker,
    HuaweiBar310Worker,
    HuaweiTE40Worker,
    PolycomRPG310Worker,
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


def collect(worker):
    results = []
    errors = []
    terminal = []
    finished = []
    worker.signals.result.connect(results.append)
    worker.signals.error.connect(errors.append)
    worker.signals.terminal_log.connect(terminal.append)
    worker.signals.finished.connect(lambda: finished.append(True))
    return results, errors, terminal, finished


def public_output(stdout, errors, terminal):
    return stdout.getvalue() + repr(errors) + "\n".join(terminal)


class TE40WorkerOutcomeTests(unittest.TestCase):
    def make_worker(self):
        worker = HuaweiTE40Worker(
            "192.0.2.40",
            username=CURRENT_USER,
            password=CURRENT_PASSWORD,
        )
        worker.creds_list = active_chain()
        worker.current_idx = 1
        return worker

    def run_worker(self, https_behavior, http_behavior=True, parser_behavior=None):
        captured = []

        class Handler:
            def __init__(self, **kwargs):
                captured.append(kwargs)
                self.port = kwargs["port"]
                self.use_ssl = kwargs["use_ssl"]

            def connect(self):
                behavior = https_behavior if self.use_ssl else http_behavior
                if isinstance(behavior, BaseException):
                    raise behavior
                return behavior

            def get_status(self):
                return {"model": "TE40", "status": "ok"}

            def disconnect(self):
                pass

        worker = self.make_worker()
        results, errors, terminal, finished = collect(worker)
        stdout = io.StringIO()
        parser = parser_behavior or (lambda data: dict(data))
        with patch("core.worker.HuaweiTE40Handler", Handler), patch(
            "core.worker.HuaweiTE40DataParser.parse_raw_data", side_effect=parser
        ), contextlib.redirect_stdout(stdout):
            worker.run()
        return worker, captured, results, errors, terminal, finished, stdout

    def test_success_emits_one_final_result_and_no_error(self):
        evidence = self.run_worker(True)
        worker, captured, results, errors, _terminal, finished, _stdout = evidence

        self.assertEqual(1, len(captured))
        self.assertEqual(1, len(results))
        self.assertEqual([], errors)
        self.assertEqual([True], finished)
        self.assertEqual(1, worker.current_idx)

    def test_https_authentication_failure_does_not_start_http(self):
        evidence = self.run_worker(
            AuthenticationError(f"auth {CURRENT_PASSWORD} {OTHER_PASSWORD}")
        )
        worker, captured, results, errors, terminal, finished, stdout = evidence

        self.assertEqual(1, len(captured))
        self.assertEqual([], results)
        self.assertEqual(1, len(errors))
        self.assertEqual("authentication_error", errors[0][0])
        self.assertEqual([True], finished)
        self.assertEqual(1, worker.current_idx)
        self.assert_secrets_redacted(public_output(stdout, errors, terminal))

    def test_timeout_emits_non_auth_error_and_no_result(self):
        evidence = self.run_worker(
            TimeoutError(f"https timeout {OTHER_PASSWORD}"),
            TimeoutError(f"http timeout {OTHER_PASSWORD}"),
        )
        self.assert_non_auth_failure(evidence)

    def test_ssl_failure_emits_non_auth_error_and_no_result(self):
        evidence = self.run_worker(
            ssl.SSLError(f"https ssl {OTHER_PASSWORD}"),
            ssl.SSLError(f"http ssl {OTHER_PASSWORD}"),
        )
        self.assert_non_auth_failure(evidence)

    def test_parsing_failure_emits_non_auth_error_and_no_result(self):
        def fail_parse(_data):
            raise ValueError(f"parse {OTHER_PASSWORD}")

        evidence = self.run_worker(True, parser_behavior=fail_parse)
        self.assert_non_auth_failure(evidence, expected_handlers=1)

    def test_https_transport_fallback_uses_same_credential(self):
        evidence = self.run_worker(TimeoutError("https unavailable"), True)
        worker, captured, results, errors, _terminal, finished, _stdout = evidence

        self.assertEqual([443, 80], [item["port"] for item in captured])
        self.assertEqual(
            [(CURRENT_USER, CURRENT_PASSWORD)] * 2,
            [(item["username"], item["password"]) for item in captured],
        )
        self.assertEqual(1, len(results))
        self.assertEqual([], errors)
        self.assertEqual([True], finished)
        self.assertEqual(1, worker.current_idx)

    def test_https_transport_then_http_auth_returns_auth_error(self):
        evidence = self.run_worker(
            TimeoutError("https unavailable"),
            AuthenticationError(f"http auth {OTHER_PASSWORD}"),
        )
        worker, captured, results, errors, terminal, finished, stdout = evidence

        self.assertEqual(2, len(captured))
        self.assertEqual([], results)
        self.assertEqual(1, len(errors))
        self.assertEqual("authentication_error", errors[0][0])
        self.assertEqual([True], finished)
        self.assertEqual(1, worker.current_idx)
        self.assert_secrets_redacted(public_output(stdout, errors, terminal))

    def test_https_transport_then_http_protocol_returns_non_auth_error(self):
        evidence = self.run_worker(
            TimeoutError("https unavailable"),
            ValueError(f"http protocol {OTHER_PASSWORD}"),
        )
        self.assert_non_auth_failure(evidence)

    def assert_non_auth_failure(self, evidence, expected_handlers=2):
        worker, captured, results, errors, terminal, finished, stdout = evidence
        self.assertEqual(expected_handlers, len(captured))
        self.assertEqual([], results)
        self.assertEqual(1, len(errors))
        self.assertEqual("connection_error", errors[0][0])
        self.assertEqual([True], finished)
        self.assertEqual(1, worker.current_idx)
        self.assertTrue(
            all(item["username"] == CURRENT_USER for item in captured)
        )
        self.assert_secrets_redacted(public_output(stdout, errors, terminal))

    def assert_secrets_redacted(self, output):
        for secret in (
            CURRENT_USER,
            CURRENT_PASSWORD,
            OTHER_USER,
            OTHER_PASSWORD,
            OTHER_TOKEN,
        ):
            self.assertNotIn(secret, output)


class PolycomWorkerOutcomeTests(unittest.TestCase):
    def make_worker(self):
        worker = PolycomRPG310Worker(
            "192.0.2.31",
            username=CURRENT_USER,
            password=CURRENT_PASSWORD,
        )
        worker.creds_list = active_chain()
        worker.current_idx = 1
        return worker

    def run_worker(
        self,
        connect_behavior=True,
        https_behavior=None,
        ssh_behavior=None,
        parser_behaviors=None,
    ):
        captured = []

        class Handler:
            def __init__(self, **kwargs):
                captured.append(kwargs)
                self.port = kwargs["port"]

            def connect(self):
                if isinstance(connect_behavior, BaseException):
                    raise connect_behavior
                return connect_behavior

            def get_https_status(self):
                if isinstance(https_behavior, BaseException):
                    raise https_behavior
                return dict(https_behavior or {"model": "Group 310"})

            def _populate_cli_status(self, raw_data, **_kwargs):
                if isinstance(ssh_behavior, BaseException):
                    raise ssh_behavior
                raw_data["ssh"] = "ok"

            def disconnect(self):
                pass

        parser_values = list(parser_behaviors or [])

        def parse(data):
            behavior = parser_values.pop(0) if parser_values else dict(data)
            if isinstance(behavior, BaseException):
                raise behavior
            return dict(behavior)

        worker = self.make_worker()
        results, errors, terminal, finished = collect(worker)
        stdout = io.StringIO()
        with patch(
            "handlers.polycom.rpg310.PolycomRPG310Handler", Handler
        ), patch(
            "core.parser.PolycomDataParser.parse_raw_data", side_effect=parse
        ), contextlib.redirect_stdout(stdout):
            worker.run()
        return worker, captured, results, errors, terminal, finished, stdout

    def test_full_success_emits_partial_and_one_final_result(self):
        evidence = self.run_worker()
        worker, captured, results, errors, _terminal, finished, _stdout = evidence

        self.assertEqual(1, len(captured))
        self.assertEqual(2, len(results))
        self.assertTrue(results[0].get("_partial_update"))
        self.assertNotIn("_partial_update", results[1])
        self.assertEqual([], errors)
        self.assertEqual([True], finished)
        self.assertEqual(1, worker.current_idx)

    def test_authentication_failure_is_error_not_result(self):
        evidence = self.run_worker(
            connect_behavior=AuthenticationError(f"auth {OTHER_PASSWORD}")
        )
        self.assert_failure(evidence, "authentication_error", 0)

    def test_timeout_before_partial_is_error_not_result(self):
        evidence = self.run_worker(
            https_behavior=TimeoutError(f"timeout {OTHER_PASSWORD}")
        )
        self.assert_failure(evidence, "connection_error", 0)

    def test_protocol_failure_before_partial_is_error_not_result(self):
        evidence = self.run_worker(
            https_behavior=ValueError(f"protocol {OTHER_PASSWORD}")
        )
        self.assert_failure(evidence, "connection_error", 0)

    def test_ssh_failure_after_partial_emits_error_without_final_result(self):
        evidence = self.run_worker(
            ssh_behavior=RuntimeError(f"ssh {OTHER_PASSWORD}")
        )
        self.assert_failure(evidence, "connection_error", 1)

    def test_parsing_failure_after_partial_emits_error_without_final_result(self):
        evidence = self.run_worker(
            parser_behaviors=[
                {"Модель": "Group 310"},
                ValueError(f"parse {OTHER_PASSWORD}"),
            ]
        )
        self.assert_failure(evidence, "connection_error", 1)

    def assert_failure(self, evidence, category, expected_partial_count):
        worker, captured, results, errors, terminal, finished, stdout = evidence
        self.assertEqual(1, len(captured))
        self.assertEqual(expected_partial_count, len(results))
        if results:
            self.assertTrue(all(item.get("_partial_update") for item in results))
        self.assertEqual(1, len(errors))
        self.assertEqual(category, errors[0][0])
        self.assertEqual([True], finished)
        self.assertEqual(1, worker.current_idx)
        self.assertEqual(CURRENT_USER, captured[0]["username"])
        self.assertEqual(CURRENT_PASSWORD, captured[0]["password"])
        output = public_output(stdout, errors, terminal)
        for secret in (
            CURRENT_USER,
            CURRENT_PASSWORD,
            OTHER_USER,
            OTHER_PASSWORD,
            OTHER_TOKEN,
        ):
            self.assertNotIn(secret, output)


class ProductionWorkerOutcomeContractTests(unittest.TestCase):
    worker_classes = (
        HuaweiTE20Worker,
        HuaweiTE40Worker,
        HuaweiBar310Worker,
        PolycomRPG310Worker,
        ExtronIN1804Worker,
        AtenPDUWorker,
        BiampTesiraForteCIWorker,
    )

    def test_no_production_worker_emits_result_from_exception_handler(self):
        for worker_class in self.worker_classes:
            with self.subTest(worker=worker_class.__name__):
                tree = ast.parse(textwrap.dedent(inspect.getsource(worker_class.run)))
                handlers = [
                    node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)
                ]
                for handler in handlers:
                    self.assertFalse(
                        any(self.is_result_emit(node) for node in ast.walk(handler)),
                        worker_class.__name__,
                    )

    def test_no_production_worker_changes_credential_index_during_run(self):
        for worker_class in self.worker_classes:
            with self.subTest(worker=worker_class.__name__):
                tree = ast.parse(textwrap.dedent(inspect.getsource(worker_class.run)))
                assignments = [
                    target
                    for node in ast.walk(tree)
                    if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
                    for target in self.assignment_targets(node)
                ]
                self.assertFalse(
                    any(
                        isinstance(target, ast.Attribute)
                        and target.attr == "current_idx"
                        for target in assignments
                    ),
                    worker_class.__name__,
                )

    @staticmethod
    def is_result_emit(node):
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "emit"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "result"
        )

    @staticmethod
    def assignment_targets(node):
        if isinstance(node, ast.Assign):
            return node.targets
        return [node.target]


if __name__ == "__main__":
    unittest.main()
