from __future__ import annotations

import os
import socket
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtWidgets import QApplication, QMessageBox, QProgressBar, QTableWidget
except ImportError:
    QApplication = None


class FakeChannel:
    def __init__(self, chunks=(), on_recv=None):
        self.chunks = list(chunks)
        self.sent = []
        self.closed = False
        self.on_recv = on_recv

    def sendall(self, data):
        self.sent.append(data)

    def send(self, data):
        self.sendall(data)

    def recv(self, _size):
        if self.on_recv is not None:
            self.on_recv(self)
        if not self.chunks:
            raise socket.timeout()
        chunk = self.chunks.pop(0)
        if isinstance(chunk, BaseException):
            raise chunk
        return chunk

    def close(self):
        self.closed = True


class DMPProtocolTests(unittest.TestCase):
    def test_oid_map_and_sis_command_bytes_are_exact(self):
        from core.dmp64_plus import (
            INPUT_OIDS,
            OUTPUT_OIDS,
            build_identity_command,
            build_read_command,
            build_recovery_command,
        )

        self.assertEqual((40000, 40001, 40002, 40003, 40004, 40005), INPUT_OIDS)
        self.assertEqual((60000, 60001, 60002, 60003), OUTPUT_OIDS)
        self.assertNotIn(40100, INPUT_OIDS)
        self.assertEqual(b"1I\r", build_identity_command())
        self.assertEqual(b"\x1bV40004AU\r", build_read_command(40004))
        self.assertEqual(b"\x1bV40004*2AU\r", build_recovery_command(40004))

    def test_payload_conversion_and_visual_scale(self):
        from core.dmp64_plus import normalize_dbfs, parse_meter_payload

        sample = parse_meter_payload("1*457")
        self.assertEqual("valid", sample["kind"])
        self.assertAlmostEqual(-45.7, sample["dbfs"])
        self.assertAlmostEqual(((-45.7) + 60) / 72, sample["normalized"])
        self.assertEqual("valid", parse_meter_payload("2*1060")["kind"])
        self.assertEqual("unavailable", parse_meter_payload("0*0")["kind"])
        self.assertNotIn("dbfs", parse_meter_payload("0*0"))
        self.assertEqual("sis_protocol_error", parse_meter_payload("E13")["kind"])
        self.assertEqual("sis_protocol_error", parse_meter_payload("E14")["kind"])
        self.assertEqual("sis_protocol_error", parse_meter_payload("E99")["kind"])
        self.assertEqual("E99", parse_meter_payload("E99")["code"])
        self.assertEqual("malformed_payload", parse_meter_payload("bad")["kind"])
        self.assertEqual(0.0, normalize_dbfs(-80))
        self.assertAlmostEqual(0.5, normalize_dbfs(-24))
        self.assertAlmostEqual(5 / 6, normalize_dbfs(0))
        self.assertEqual(1.0, normalize_dbfs(30))

    def test_supported_variants_are_explicit_not_substring_based(self):
        from core.dmp64_plus import is_supported_dmp64_plus_variant

        for variant in (
            "DMP 64 Plus C",
            "DMP 64 Plus C AT",
            "DMP 64 Plus C V",
            "DMP 64 Plus C V AT",
        ):
            self.assertTrue(is_supported_dmp64_plus_variant(variant))
        self.assertFalse(is_supported_dmp64_plus_variant("DMP 64 Plus Future X"))
        self.assertFalse(is_supported_dmp64_plus_variant("Extron DMP 64 Plus"))

    def test_framer_filters_pty_echo_fragmentation_and_multiple_frames(self):
        from core.dmp64_plus import DMPStreamFramer

        framer = DMPStreamFramer()
        self.assertEqual([], framer.feed(b"\x1bV40004", command_echo=b"\x1bV40004AU\r"))
        frames = framer.feed(b"AU\r1*", command_echo=b"\x1bV40004AU\r")
        self.assertEqual([], frames)
        frames = framer.feed(b"1060\rE13\n", command_echo=b"\x1bV40004AU\r")
        self.assertEqual(["1*1060", "E13"], frames)

    def test_framer_filters_printable_pty_escape_echo_from_live_fixture(self):
        from core.dmp64_plus import DMPStreamFramer

        framer = DMPStreamFramer()
        frames = framer.feed(
            b"^[V40004AU\r\n2*457\r\r\n",
            command_echo=b"\x1bV40004AU\r",
        )

        self.assertEqual(["2*457"], frames)

    def test_framer_filters_fragmented_printable_pty_escape_echo(self):
        from core.dmp64_plus import DMPStreamFramer

        framer = DMPStreamFramer()
        self.assertEqual([], framer.feed(b"^[V400", command_echo=b"\x1bV40004AU\r"))
        frames = framer.feed(b"04AU\r\n2*457\r", command_echo=b"\x1bV40004AU\r")

        self.assertEqual(["2*457"], frames)

    def test_transaction_ignores_unrelated_frames_until_expected_payload(self):
        from core.dmp64_plus import DMPTransportSession

        channel = FakeChannel([b"Unrelated*Frame\r", b"DsV40005*2\r", b"1*1060\r"])
        session = DMPTransportSession(channel, transaction_timeout=0.05, sleep_interval=0.001)

        parsed = session.read_meter(40004)

        self.assertEqual("valid", parsed["kind"])
        self.assertEqual([b"\x1bV40004AU\r"], channel.sent)

    def test_transaction_ignores_unsafe_malformed_meter_like_frames(self):
        from core.dmp64_plus import DMPTransportSession

        for unsafe_frame in (b"9*bad\r", b"123*foo\r"):
            with self.subTest(frame=unsafe_frame):
                channel = FakeChannel([unsafe_frame, b"1*457\r"])
                session = DMPTransportSession(channel, transaction_timeout=0.05, sleep_interval=0.001)

                parsed = session.read_meter(40000)

                self.assertEqual("valid", parsed["kind"])
                self.assertEqual(457, parsed["raw_meter"])
                self.assertEqual([b"\x1bV40000AU\r"], channel.sent)

    def test_meter_terminal_contract_accepts_only_valid_meter_or_sis_error(self):
        from core.dmp64_plus import DMPTransportSession

        valid_cases = (
            (b"0*0\r", "unavailable"),
            (b"1*457\r", "valid"),
            (b"2*1060\r", "valid"),
            (b"E13\r", "sis_protocol_error"),
            (b"E14\r", "sis_protocol_error"),
        )
        for frame, expected_kind in valid_cases:
            with self.subTest(frame=frame):
                channel = FakeChannel([frame])
                session = DMPTransportSession(channel, transaction_timeout=0.05, sleep_interval=0.001)
                self.assertEqual(expected_kind, session.read_meter(40000)["kind"])

    def test_wrong_recovery_ack_waits_for_matching_oid(self):
        from core.dmp64_plus import DMPTransportSession

        channel = FakeChannel([b"DsV40005*2\r", b"DsV40004*2\r"])
        session = DMPTransportSession(channel, transaction_timeout=0.05, sleep_interval=0.001)

        parsed = session.recover_meter(40004)

        self.assertEqual("recovery_ack", parsed["kind"])
        self.assertIn(40004, session.recovered_oids)

    def test_recovery_budget_is_consumed_after_sis_error_not_only_ack(self):
        from core.dmp64_plus import DMPTransportSession, build_meter_snapshot

        cycle_one = [b"0*0\r", b"E13\r"]
        cycle_one.extend([b"1*100\r"] * 9)
        cycle_two = [b"0*0\r"]
        cycle_two.extend([b"1*100\r"] * 9)
        channel = FakeChannel(cycle_one + cycle_two)
        session = DMPTransportSession(channel, transaction_timeout=0.05, sleep_interval=0.001)

        first = build_meter_snapshot(session, ip_address="192.0.2.64")
        second = build_meter_snapshot(session, ip_address="192.0.2.64")

        self.assertTrue(first["complete"])
        self.assertTrue(second["complete"])
        self.assertEqual(1, channel.sent.count(b"\x1bV40000*2AU\r"))
        self.assertIn(40000, session.recovery_attempted_oids)

    def test_recovery_timeout_consumes_budget_and_poisons_session(self):
        from core.dmp64_plus import DMPSessionPoisoned, DMPTransactionTimeout, DMPTransportSession

        channel = FakeChannel([])
        session = DMPTransportSession(channel, transaction_timeout=0.005, sleep_interval=0.001)

        with self.assertRaises(DMPTransactionTimeout):
            session.recover_meter(40000)
        self.assertIn(40000, session.recovery_attempted_oids)
        with self.assertRaises(DMPSessionPoisoned):
            session.recover_meter(40000)

    def test_model_identity_query_filters_echo_and_returns_supported_variant(self):
        from core.dmp64_plus import DMPTransportSession

        channel = FakeChannel([b"1I\r", b"DMP 64 Plus C V AT\r"])
        session = DMPTransportSession(channel, transaction_timeout=0.05, sleep_interval=0.001)

        model = session.read_model_identity()

        self.assertEqual("DMP 64 Plus C V AT", model)
        self.assertEqual([b"1I\r"], channel.sent)

    def test_model_identity_ignores_banner_and_unrelated_frames(self):
        from core.dmp64_plus import DMPTransportSession

        channel = FakeChannel([b"Welcome\r", b"1*457\r", b"DMP 64 Plus C AT\r"])
        session = DMPTransportSession(channel, transaction_timeout=0.05, sleep_interval=0.001)

        self.assertEqual("DMP 64 Plus C AT", session.read_model_identity())
        self.assertEqual([b"1I\r"], channel.sent)

    def test_model_identity_discovers_unknown_dmp_model_like_response(self):
        from core.dmp64_plus import DMPTransportSession

        channel = FakeChannel([b"Welcome\r", b"DMP 64 Plus Future X\r"])
        session = DMPTransportSession(channel, transaction_timeout=0.05, sleep_interval=0.001)

        self.assertEqual("DMP 64 Plus Future X", session.read_model_identity())

    def test_model_identity_times_out_on_pure_unrelated_frames(self):
        from core.dmp64_plus import DMPTransactionTimeout, DMPTransportSession

        channel = FakeChannel([b"Welcome\r", b"Unrelated*Frame\r"])
        session = DMPTransportSession(channel, transaction_timeout=0.005, sleep_interval=0.001)

        with self.assertRaises(DMPTransactionTimeout):
            session.read_model_identity()

    def test_timeout_poisons_session_and_prevents_next_oid_or_delayed_shift(self):
        from core.dmp64_plus import DMPSessionPoisoned, DMPTransactionTimeout, DMPTransportSession

        channel = FakeChannel([])
        session = DMPTransportSession(channel, transaction_timeout=0.005, sleep_interval=0.001)

        with self.assertRaises(DMPTransactionTimeout):
            session.read_meter(40000)
        channel.chunks.append(b"1*457\r")
        with self.assertRaises(DMPSessionPoisoned):
            session.read_meter(40001)
        self.assertEqual([b"\x1bV40000AU\r"], channel.sent)

    def test_snapshot_uses_one_shot_recovery_and_fresh_session_budget(self):
        from core.dmp64_plus import DMPTransportSession, build_meter_snapshot

        cycle_one = [b"0*0\r", b"DsV40000*2\r", b"0*0\r"]
        cycle_one.extend([b"1*100\r"] * 9)
        cycle_two = [b"0*0\r"]
        cycle_two.extend([b"1*100\r"] * 9)
        channel = FakeChannel(cycle_one + cycle_two)
        session = DMPTransportSession(channel, transaction_timeout=0.05, sleep_interval=0.001)

        first = build_meter_snapshot(session, ip_address="192.0.2.64")
        second = build_meter_snapshot(session, ip_address="192.0.2.64")

        self.assertTrue(first["complete"])
        self.assertTrue(second["complete"])
        self.assertEqual(1, channel.sent.count(b"\x1bV40000*2AU\r"))
        self.assertFalse(first["meter_sections"][0]["channels"][0]["available"])
        self.assertFalse(second["meter_sections"][0]["channels"][0]["available"])

        fresh = DMPTransportSession(
            FakeChannel([b"0*0\r", b"DsV40000*2\r", b"1*100\r"] + [b"1*100\r"] * 9),
            transaction_timeout=0.05,
            sleep_interval=0.001,
        )
        build_meter_snapshot(fresh, ip_address="192.0.2.64")
        self.assertEqual(1, fresh.channel.sent.count(b"\x1bV40000*2AU\r"))

    def test_partial_protocol_outcomes_do_not_destroy_complete_snapshot(self):
        from core.dmp64_plus import DMPTransportSession, build_meter_snapshot

        channel = FakeChannel([b"E13\r", b"E14\r"] + [b"1*100\r"] * 8)
        session = DMPTransportSession(channel, transaction_timeout=0.05, sleep_interval=0.001)

        snapshot = build_meter_snapshot(session, ip_address="192.0.2.64")
        channels = [
            channel
            for section in snapshot["meter_sections"]
            for channel in section["channels"]
        ]

        self.assertTrue(snapshot["complete"])
        self.assertEqual("sis_protocol_error", channels[0]["outcome"])
        self.assertEqual("sis_protocol_error", channels[1]["outcome"])
        self.assertEqual("E14", channels[1]["error_code"])
        self.assertFalse(channels[0]["available"])
        self.assertFalse(channels[1]["available"])
        self.assertTrue(channels[2]["available"])

    def test_cancellation_between_oids_prevents_next_network_io(self):
        from core.dmp64_plus import DMPCancellationToken, DMPCancelled, DMPTransportSession, build_meter_snapshot

        token = DMPCancellationToken()

        def cancel_after_first_payload(channel):
            if len(channel.sent) == 1 and channel.chunks:
                token.cancel()

        channel = FakeChannel([b"1*100\r", b"1*100\r"], on_recv=cancel_after_first_payload)
        session = DMPTransportSession(channel, transaction_timeout=0.05, sleep_interval=0.001)

        with self.assertRaises(DMPCancelled):
            build_meter_snapshot(session, ip_address="192.0.2.64", cancellation=token)
        self.assertEqual([b"\x1bV40000AU\r"], channel.sent)

    def test_paramiko_transport_uses_open_session_pty_and_invoke_shell(self):
        from handlers.extron.dmp64_plus import _ParamikoDMPSession

        calls = []

        class FakeChannel:
            def get_pty(self, term):
                calls.append(("get_pty", term))

            def invoke_shell(self):
                calls.append(("invoke_shell",))

            def settimeout(self, timeout):
                calls.append(("settimeout", timeout))

            def recv(self, _size):
                raise socket.timeout()

            def sendall(self, _data):
                pass

            def close(self):
                calls.append(("channel_close",))

        class FakeTransport:
            def open_session(self):
                calls.append(("open_session",))
                return FakeChannel()

        class FakeSSHClient:
            def set_missing_host_key_policy(self, _policy):
                calls.append(("set_missing_host_key_policy",))

            def connect(self, *args, **kwargs):
                calls.append(("connect", args, kwargs))

            def get_transport(self):
                calls.append(("get_transport",))
                return FakeTransport()

            def close(self):
                calls.append(("client_close",))

        fake_paramiko = SimpleNamespace(
            SSHClient=FakeSSHClient,
            AutoAddPolicy=lambda: object(),
            AuthenticationException=type("AuthenticationException", (Exception,), {}),
            BadAuthenticationType=type("BadAuthenticationType", (Exception,), {}),
            PartialAuthentication=type("PartialAuthentication", (Exception,), {}),
        )

        with patch.dict(sys.modules, {"paramiko": fake_paramiko}):
            session = _ParamikoDMPSession.open(
                ip_address="192.0.2.64",
                port=22023,
                username="synthetic-user",
                password="synthetic-password",
                timeout=1.5,
            )

        self.assertIn(("open_session",), calls)
        self.assertIn(("get_pty", "vt100"), calls)
        self.assertIn(("invoke_shell",), calls)
        self.assertIn(("settimeout", 1.5), calls)
        connect_call = [call for call in calls if call[0] == "connect"][0]
        self.assertEqual("192.0.2.64", connect_call[1][0])
        self.assertEqual(22023, connect_call[2]["port"])
        self.assertFalse(connect_call[2]["look_for_keys"])
        self.assertFalse(connect_call[2]["allow_agent"])
        session.close()
        self.assertIn(("channel_close",), calls)
        self.assertIn(("client_close",), calls)

    def test_handler_validates_supported_model_before_meter_polling(self):
        from handlers.extron.dmp64_plus import ExtronDMP64PlusHandler

        class FakeSession:
            def __init__(self):
                self.closed = False
                self.close_count = 0

            def read_model_identity(self, _cancellation=None):
                return "DMP 64 Plus C"

            def close(self):
                self.close_count += 1
                self.closed = True

        sessions = []

        def factory(**_kwargs):
            session = FakeSession()
            sessions.append(session)
            return session

        handler = ExtronDMP64PlusHandler(
            "192.0.2.64",
            username="synthetic-user",
            password="synthetic-password",
            transport_factory=factory,
        )

        self.assertTrue(handler.connect())
        self.assertEqual("DMP 64 Plus C", handler.discovered_model)
        self.assertFalse(sessions[0].closed)
        handler.disconnect()
        self.assertTrue(sessions[0].closed)
        self.assertEqual(1, sessions[0].close_count)

    def test_handler_rejects_unknown_substring_model_without_polling(self):
        from core.dmp64_plus import DMPUnsupportedModel
        from handlers.extron.dmp64_plus import ExtronDMP64PlusHandler

        class FakeSession:
            def __init__(self):
                self.closed = False
                self.close_count = 0
                self.meter_polled = False

            def read_model_identity(self, _cancellation=None):
                return "DMP 64 Plus Future X"

            def close(self):
                self.close_count += 1
                self.closed = True

        sessions = []

        def factory(**_kwargs):
            session = FakeSession()
            sessions.append(session)
            return session

        handler = ExtronDMP64PlusHandler(
            "192.0.2.64",
            username="synthetic-user",
            password="synthetic-password",
            transport_factory=factory,
        )

        with self.assertRaises(DMPUnsupportedModel):
            handler.connect()
        self.assertTrue(sessions[0].closed)
        self.assertEqual(1, sessions[0].close_count)
        self.assertFalse(sessions[0].meter_polled)

    def test_handler_closes_session_on_identity_timeout_and_transport_failure(self):
        from core.dmp64_plus import DMPTransactionTimeout
        from core.exceptions import ConnectionError
        from handlers.extron.dmp64_plus import ExtronDMP64PlusHandler

        for error in (
            DMPTransactionTimeout("identity timeout"),
            ConnectionError("identity transport failure"),
        ):
            with self.subTest(error=type(error).__name__):
                class FakeSession:
                    def __init__(self):
                        self.close_count = 0

                    def read_model_identity(self, _cancellation=None):
                        raise error

                    def close(self):
                        self.close_count += 1

                sessions = []

                def factory(**_kwargs):
                    session = FakeSession()
                    sessions.append(session)
                    return session

                handler = ExtronDMP64PlusHandler(
                    "192.0.2.64",
                    username="synthetic-user",
                    password="synthetic-password",
                    transport_factory=factory,
                )

                with self.assertRaises(ConnectionError):
                    handler.connect()
                self.assertIsNone(handler.session)
                self.assertEqual(1, sessions[0].close_count)

    def test_handler_cancellation_after_session_creation_closes_without_identity_send(self):
        from core.dmp64_plus import DMPCancellationToken, DMPCancelled
        from handlers.extron.dmp64_plus import ExtronDMP64PlusHandler

        token = DMPCancellationToken()

        class FakeSession:
            def __init__(self):
                self.close_count = 0
                self.identity_sent = False

            def read_model_identity(self, _cancellation=None):
                self.identity_sent = True
                return "DMP 64 Plus C"

            def close(self):
                self.close_count += 1

        sessions = []

        def factory(**_kwargs):
            session = FakeSession()
            sessions.append(session)
            token.cancel()
            return session

        handler = ExtronDMP64PlusHandler(
            "192.0.2.64",
            username="synthetic-user",
            password="synthetic-password",
            transport_factory=factory,
        )

        with self.assertRaises(DMPCancelled):
            handler.connect(token)
        self.assertFalse(sessions[0].identity_sent)
        self.assertEqual(1, sessions[0].close_count)
        self.assertIsNone(handler.session)

    def test_handler_cancellation_during_identity_closes_session(self):
        from core.dmp64_plus import DMPCancellationToken, DMPCancelled
        from handlers.extron.dmp64_plus import ExtronDMP64PlusHandler

        token = DMPCancellationToken()

        class FakeSession:
            def __init__(self):
                self.close_count = 0
                self.identity_sent = False

            def read_model_identity(self, cancellation=None):
                self.identity_sent = True
                token.cancel()
                cancellation.raise_if_cancelled()

            def close(self):
                self.close_count += 1

        sessions = []

        def factory(**_kwargs):
            session = FakeSession()
            sessions.append(session)
            return session

        handler = ExtronDMP64PlusHandler(
            "192.0.2.64",
            username="synthetic-user",
            password="synthetic-password",
            transport_factory=factory,
        )

        with self.assertRaises(DMPCancelled):
            handler.connect(token)
        self.assertTrue(sessions[0].identity_sent)
        self.assertEqual(1, sessions[0].close_count)
        self.assertIsNone(handler.session)


class DMPWorkerLifecycleTests(unittest.TestCase):
    def test_worker_caches_credential_only_on_first_accepted_complete_snapshot(self):
        from core.worker import ExtronDMP64PlusMeterWorker

        class FakeHandler:
            instances = []

            def __init__(self, **_kwargs):
                self.closed = False
                FakeHandler.instances.append(self)

            def connect(self):
                return True

            def get_meter_snapshot(self, _cancellation):
                return {
                    "device_info": {"model": "Extron DMP 64 Plus", "ip_address": "192.0.2.64"},
                    "meter_sections": [
                        {"title": "Inputs", "channels": [{"name": "Input 1", "available": True, "normalized": 0.5}]},
                        {"title": "Outputs", "channels": [{"name": "Output 1", "available": False, "normalized": None}]},
                    ],
                    "attempted_oids": list(range(10)),
                    "complete": True,
                    "ip_address": "192.0.2.64",
                    "model": "Extron DMP 64 Plus",
                    "type": "audio_dsp",
                }

            def disconnect(self):
                self.closed = True

        worker = ExtronDMP64PlusMeterWorker(
            "192.0.2.64",
            username="synthetic-user",
            password="synthetic-password",
            handler_factory=FakeHandler,
            max_cycles=2,
            poll_interval=0,
        )
        results = []
        errors = []
        finished = []
        worker.signals.result.connect(results.append)
        worker.signals.error.connect(errors.append)
        worker.signals.finished.connect(lambda: finished.append(True))

        worker.run()

        self.assertEqual([], errors)
        self.assertEqual([True, False], [result["_credential_used"] for result in results])
        self.assertTrue(all(result["_continuous_update"] for result in results))
        self.assertEqual([True], finished)
        self.assertTrue(FakeHandler.instances[0].closed)

    def test_worker_structures_timeout_as_transport_not_authentication(self):
        from core.dmp64_plus import DMPTransactionTimeout
        from core.worker import ExtronDMP64PlusMeterWorker

        class TimeoutHandler:
            def __init__(self, **_kwargs):
                self.closed = False

            def connect(self):
                return True

            def get_meter_snapshot(self, _cancellation):
                raise DMPTransactionTimeout("synthetic-password auth 401 delayed timeout text")

            def disconnect(self):
                self.closed = True

        worker = ExtronDMP64PlusMeterWorker(
            "192.0.2.64",
            username="synthetic-user",
            password="synthetic-password",
            handler_factory=TimeoutHandler,
        )
        errors = []
        worker.signals.error.connect(errors.append)

        worker.run()

        self.assertEqual("transport_session_failure", errors[0][0])
        self.assertIn("<redacted>", errors[0][1])
        self.assertNotIn("synthetic-password", errors[0][1])

    def test_worker_cadence_does_not_add_wait_after_slow_cycle(self):
        from core.worker import ExtronDMP64PlusMeterWorker

        class FakeHandler:
            def __init__(self, **_kwargs):
                self.count = 0

            def connect(self):
                return True

            def get_meter_snapshot(self, _cancellation):
                self.count += 1
                return {
                    "device_info": {"model": "Extron DMP 64 Plus", "ip_address": "192.0.2.64"},
                    "meter_sections": [{"title": "Inputs", "channels": [{"available": True}]}],
                    "attempted_oids": list(range(10)),
                    "complete": True,
                    "ip_address": "192.0.2.64",
                    "model": "Extron DMP 64 Plus",
                    "type": "audio_dsp",
                }

            def disconnect(self):
                pass

        worker = ExtronDMP64PlusMeterWorker(
            "192.0.2.64",
            username="synthetic-user",
            password="synthetic-password",
            handler_factory=FakeHandler,
            max_cycles=2,
            poll_interval=1.0,
        )

        waits = []
        with patch("core.worker.time.monotonic", side_effect=[0.0, 1.07, 2.0]):
            with patch("core.worker.wait_cancelable", side_effect=lambda _token, seconds: waits.append(seconds)):
                worker.run()

        self.assertEqual([0.0], waits)

    def test_worker_cadence_waits_only_remaining_fast_cycle_duration(self):
        from core.worker import ExtronDMP64PlusMeterWorker

        class FakeHandler:
            def __init__(self, **_kwargs):
                pass

            def connect(self):
                return True

            def get_meter_snapshot(self, _cancellation):
                return {
                    "device_info": {"model": "Extron DMP 64 Plus", "ip_address": "192.0.2.64"},
                    "meter_sections": [{"title": "Inputs", "channels": [{"available": True}]}],
                    "attempted_oids": list(range(10)),
                    "complete": True,
                    "ip_address": "192.0.2.64",
                    "model": "Extron DMP 64 Plus",
                    "type": "audio_dsp",
                }

            def disconnect(self):
                pass

        worker = ExtronDMP64PlusMeterWorker(
            "192.0.2.64",
            username="synthetic-user",
            password="synthetic-password",
            handler_factory=FakeHandler,
            max_cycles=2,
            poll_interval=1.0,
        )

        waits = []
        with patch("core.worker.time.monotonic", side_effect=[0.0, 0.25, 1.0]):
            with patch("core.worker.wait_cancelable", side_effect=lambda _token, seconds: waits.append(seconds)):
                worker.run()

        self.assertEqual([0.75], waits)

    def test_worker_reports_unsupported_model_without_auth_fallback_category(self):
        from core.dmp64_plus import DMPUnsupportedModel
        from core.worker import ExtronDMP64PlusMeterWorker

        class UnsupportedHandler:
            def __init__(self, **_kwargs):
                self.closed = False

            def connect(self):
                raise DMPUnsupportedModel("Unsupported Extron DMP 64 Plus variant: DMP 64 Plus Future X")

            def disconnect(self):
                self.closed = True

        worker = ExtronDMP64PlusMeterWorker(
            "192.0.2.64",
            username="synthetic-user",
            password="synthetic-password",
            handler_factory=UnsupportedHandler,
        )
        errors = []
        worker.signals.error.connect(errors.append)

        worker.run()

        self.assertEqual("unsupported_device", errors[0][0])

    def test_worker_cancellation_before_handler_acquisition_creates_no_handler(self):
        from core.dmp64_plus import DMPCancellationToken
        from core.worker import ExtronDMP64PlusMeterWorker

        token = DMPCancellationToken()
        token.cancel()

        class FakeHandler:
            instances = []

            def __init__(self, **_kwargs):
                FakeHandler.instances.append(self)

        worker = ExtronDMP64PlusMeterWorker(
            "192.0.2.64",
            username="synthetic-user",
            password="synthetic-password",
            cancellation=token,
            handler_factory=FakeHandler,
        )

        worker.run()

        self.assertEqual([], FakeHandler.instances)

    def test_worker_cancellation_after_identity_before_first_meter_sends_no_meter_oid(self):
        from core.dmp64_plus import DMPCancellationToken
        from core.worker import ExtronDMP64PlusMeterWorker

        token = DMPCancellationToken()

        class FakeHandler:
            instances = []

            def __init__(self, **_kwargs):
                self.meter_polled = False
                self.closed = False
                FakeHandler.instances.append(self)

            def connect(self, cancellation=None):
                cancellation.cancel()
                return True

            def get_meter_snapshot(self, _cancellation):
                self.meter_polled = True
                raise AssertionError("meter polling must not start after cancellation")

            def disconnect(self):
                self.closed = True

        worker = ExtronDMP64PlusMeterWorker(
            "192.0.2.64",
            username="synthetic-user",
            password="synthetic-password",
            cancellation=token,
            handler_factory=FakeHandler,
        )

        worker.run()

        self.assertFalse(FakeHandler.instances[0].meter_polled)
        self.assertTrue(FakeHandler.instances[0].closed)

    def test_worker_terminal_cleanup_after_connect_failure_is_idempotent(self):
        from core.dmp64_plus import DMPUnsupportedModel
        from core.worker import ExtronDMP64PlusMeterWorker

        class FakeHandler:
            instances = []

            def __init__(self, **_kwargs):
                self.disconnect_count = 0
                FakeHandler.instances.append(self)

            def connect(self, _cancellation=None):
                self.disconnect()
                raise DMPUnsupportedModel("Unsupported Extron DMP 64 Plus variant: DMP 64 Plus Future X")

            def disconnect(self):
                self.disconnect_count += 1

        worker = ExtronDMP64PlusMeterWorker(
            "192.0.2.64",
            username="synthetic-user",
            password="synthetic-password",
            handler_factory=FakeHandler,
        )
        errors = []
        worker.signals.error.connect(errors.append)

        worker.run()

        self.assertEqual("unsupported_device", errors[0][0])
        self.assertEqual(2, FakeHandler.instances[0].disconnect_count)


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class DMPGuiIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")

    def setUp(self):
        from gui.main_window import VCSDiagnosticApp

        self.window = VCSDiagnosticApp()
        self.window.show()
        QApplication.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        QApplication.processEvents()

    def test_selector_registration_and_audio_dsp_routing(self):
        items = [
            self.window.device_combo.itemText(index)
            for index in range(self.window.device_combo.count())
        ]

        self.assertIn("Extron DMP 64 Plus", items)
        self.assertGreater(items.index("Extron DMP 64 Plus"), items.index("Audio DSP"))
        self.assertLess(items.index("Extron DMP 64 Plus"), items.index("Управление питанием"))
        self.assertEqual("audio_dsp", self.window.device_to_screen["Extron DMP 64 Plus"])
        self.assertEqual("audio_dsp", self.window.device_to_screen["Biamp Tesira Forte CI"])

    def test_audio_dsp_screen_renders_dmp_inputs_outputs_green_bars(self):
        from gui.components import SectionCard
        from gui.screens.audio_dsp_screen import AudioDSPScreen

        screen = AudioDSPScreen(self.window)
        screen.update_data(
            {
                "device_info": {"model": "Extron DMP 64 Plus", "ip_address": "192.0.2.64"},
                "meter_sections": [
                    {
                        "title": "Inputs",
                        "channels": [
                            {"name": f"Input {number}", "available": True, "normalized": 0.5}
                            for number in range(1, 7)
                        ],
                    },
                    {
                        "title": "Outputs",
                        "channels": [
                            {"name": "Output 1", "available": False, "normalized": None},
                            *[
                                {"name": f"Output {number}", "available": True, "normalized": 1.0}
                                for number in range(2, 5)
                            ],
                        ],
                    },
                ],
            }
        )

        cards = [card.title_label.text() for card in screen.findChildren(SectionCard)]
        bars = screen.findChildren(QProgressBar)
        self.assertIn("Inputs", cards)
        self.assertIn("Outputs", cards)
        self.assertEqual(10, len(bars))
        self.assertEqual(500, bars[0].value())
        self.assertFalse(bars[6].property("available"))
        self.assertEqual(0, bars[6].value())
        self.assertIn("#22C55E", bars[0].styleSheet())
        self.assertEqual([], screen.findChildren(QTableWidget))

    def test_refresh_starts_one_dmp_worker_and_repeat_refresh_cancels_previous(self):
        started = []
        self.window.device_credentials["Extron DMP 64 Plus"] = [
            {"username": "synthetic-user", "password": "synthetic-password"}
        ]
        self.window.device_combo.setCurrentText("Extron DMP 64 Plus")
        self.window.ip_entry.setText("192.0.2.64")
        self.window.ensure_ping_success = lambda _ip: True
        self.window.show_progress_dialog = lambda _message: None

        with patch.object(QThreadPool_global(), "start", side_effect=started.append):
            self.window.refresh_data()
            first_worker = started[0]
            self.window.refresh_data()
            second_worker = started[1]

        self.assertEqual(2, len(started))
        self.assertIsInstance(first_worker.cancellation.is_cancelled(), bool)
        self.assertTrue(first_worker.cancellation.is_cancelled())
        self.assertFalse(second_worker.cancellation.is_cancelled())
        self.assertEqual("Extron DMP 64 Plus", first_worker.device_name)

    def test_dmp_timeout_text_does_not_advance_credential_chain(self):
        from core.dmp64_plus import DMPCancellationToken
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp.__new__(VCSDiagnosticApp)
        token = DMPCancellationToken()
        window._active_request = {
            "id": 1,
            "screen": None,
            "device": "Extron DMP 64 Plus",
            "ip": "192.0.2.64",
        }
        window._dmp_context_revision = 1
        window._dmp_cancel_token = token
        window.current_credential_index = {}
        window.current_worker = None
        window.device_combo = SimpleNamespace(currentText=lambda: "Extron DMP 64 Plus")
        window.hide_progress_dialog = Mock()
        window.finish_codec_terminal = Mock()
        window.set_ui_state = Mock()
        window.set_current_credential_index = Mock()
        window.refresh_extron_dmp64_plus = Mock()
        window.refresh_btn = Mock()
        window.screens = {}
        window.current_screen_type = None
        window.progress_dialog = None
        window.is_vcs_codec_device = lambda _device: False
        worker = SimpleNamespace(
            device_name="Extron DMP 64 Plus",
            ip_address="192.0.2.64",
            current_idx=0,
            creds_list=[
                {"username": "synthetic-user-a", "password": "synthetic-password-a"},
                {"username": "synthetic-user-b", "password": "synthetic-password-b"},
            ],
        )
        worker.dmp_context = {
            "generation": 1,
            "model": "Extron DMP 64 Plus",
            "ip": "192.0.2.64",
            "token": token,
            "worker": worker,
        }
        window.current_worker = worker

        with patch.object(QMessageBox, "critical"):
            window.on_device_error(
                ("transport_session_failure", "auth 401 403 timeout", ""),
                worker,
                1,
            )

        window.refresh_extron_dmp64_plus.assert_not_called()
        window.set_current_credential_index.assert_not_called()

    def test_dmp_structured_authentication_failure_advances_request_plan(self):
        from core.dmp64_plus import DMPCancellationToken
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp.__new__(VCSDiagnosticApp)
        token = DMPCancellationToken()
        window._active_request = {
            "id": 1,
            "screen": None,
            "device": "Extron DMP 64 Plus",
            "ip": "192.0.2.64",
        }
        window._dmp_context_revision = 1
        window._dmp_cancel_token = token
        window.current_credential_index = {}
        window.current_worker = None
        window.device_combo = SimpleNamespace(currentText=lambda: "Extron DMP 64 Plus")
        window.hide_progress_dialog = Mock()
        window.finish_codec_terminal = Mock()
        window.set_ui_state = Mock()
        window.set_current_credential_index = Mock()
        window.refresh_extron_dmp64_plus = Mock()
        window.refresh_btn = Mock()
        window.screens = {}
        window.current_screen_type = None
        window.progress_dialog = None
        window.is_vcs_codec_device = lambda _device: False
        worker = SimpleNamespace(
            device_name="Extron DMP 64 Plus",
            ip_address="192.0.2.64",
            current_idx=0,
            creds_list=[
                {"username": "synthetic-user-a", "password": "synthetic-password-a"},
                {"username": "synthetic-user-b", "password": "synthetic-password-b"},
            ],
        )
        worker.dmp_context = {
            "generation": 1,
            "model": "Extron DMP 64 Plus",
            "ip": "192.0.2.64",
            "token": token,
            "worker": worker,
        }
        window.current_worker = worker

        window.on_device_error(("authentication_error", "rejected", ""), worker, 1)

        window.set_current_credential_index.assert_not_called()
        window.refresh_extron_dmp64_plus.assert_called_once_with("192.0.2.64")
        self.assertEqual(
            1,
            window._credential_attempt_plans[
                "Extron DMP 64 Plus|192.0.2.64"
            ].current_index,
        )

    def test_stale_dmp_snapshot_does_not_cache_or_render(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp.__new__(VCSDiagnosticApp)
        window._active_request = {"id": 2, "screen": Mock()}
        window.current_worker = object()
        window.current_credential_index = {}
        window.device_combo = SimpleNamespace(currentText=lambda: "Extron DMP 64 Plus")
        window.hide_progress_dialog = Mock()
        window.set_ui_state = Mock()
        window.set_current_credential_index = Mock()
        stale_worker = SimpleNamespace(
            device_name="Extron DMP 64 Plus",
            ip_address="192.0.2.64",
            current_idx=1,
            creds_list=[{"username": "synthetic-user", "password": "synthetic-password"}],
        )

        window.on_device_data_received(
            {
                "_continuous_update": True,
                "_credential_used": True,
                "ip_address": "192.0.2.64",
                "meter_sections": [{"title": "Inputs", "channels": []}],
            },
            stale_worker,
            1,
        )

        window.set_current_credential_index.assert_not_called()
        window._active_request["screen"].update_data.assert_not_called()

    def test_stale_dmp_generation_same_request_worker_does_not_cache_or_render(self):
        from core.dmp64_plus import DMPCancellationToken
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp.__new__(VCSDiagnosticApp)
        screen = Mock()
        current_token = DMPCancellationToken()
        old_token = DMPCancellationToken()
        window._active_request = {
            "id": 1,
            "screen": screen,
            "device": "Extron DMP 64 Plus",
            "ip": "192.0.2.64",
        }
        window._dmp_context_revision = 2
        window._dmp_cancel_token = current_token
        window.current_credential_index = {}
        window.device_combo = SimpleNamespace(currentText=lambda: "Extron DMP 64 Plus")
        window.hide_progress_dialog = Mock()
        window.set_ui_state = Mock()
        window.set_current_credential_index = Mock()
        worker = SimpleNamespace(
            device_name="Extron DMP 64 Plus",
            ip_address="192.0.2.64",
            current_idx=0,
            creds_list=[{"username": "synthetic-user", "password": "synthetic-password"}],
        )
        worker.dmp_context = {
            "generation": 1,
            "model": "Extron DMP 64 Plus",
            "ip": "192.0.2.64",
            "token": old_token,
            "worker": worker,
        }
        window.current_worker = worker

        window.on_device_data_received(
            {
                "_continuous_update": True,
                "_credential_used": True,
                "ip_address": "192.0.2.64",
                "meter_sections": [{"title": "Inputs", "channels": [{"available": True}]}],
            },
            worker,
            1,
        )

        window.hide_progress_dialog.assert_not_called()
        window.set_current_credential_index.assert_not_called()
        screen.update_data.assert_not_called()

    def test_stale_dmp_error_and_finished_same_request_worker_are_ignored(self):
        from core.dmp64_plus import DMPCancellationToken
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp.__new__(VCSDiagnosticApp)
        current_token = DMPCancellationToken()
        old_token = DMPCancellationToken()
        window._active_request = {
            "id": 1,
            "screen": None,
            "device": "Extron DMP 64 Plus",
            "ip": "192.0.2.64",
        }
        window._dmp_context_revision = 2
        window._dmp_cancel_token = current_token
        window.current_credential_index = {}
        window.device_combo = SimpleNamespace(currentText=lambda: "Extron DMP 64 Plus")
        window.hide_progress_dialog = Mock()
        window.finish_codec_terminal = Mock()
        window.set_ui_state = Mock()
        window.set_current_credential_index = Mock()
        window.refresh_extron_dmp64_plus = Mock()
        window.refresh_btn = Mock()
        worker = SimpleNamespace(
            device_name="Extron DMP 64 Plus",
            ip_address="192.0.2.64",
            current_idx=0,
            creds_list=[
                {"username": "synthetic-user-a", "password": "synthetic-password-a"},
                {"username": "synthetic-user-b", "password": "synthetic-password-b"},
            ],
        )
        worker.dmp_context = {
            "generation": 1,
            "model": "Extron DMP 64 Plus",
            "ip": "192.0.2.64",
            "token": old_token,
            "worker": worker,
        }
        window.current_worker = worker

        window.on_device_error(("authentication_error", "rejected", ""), worker, 1)
        window.on_worker_finished(worker, 1)

        window.refresh_extron_dmp64_plus.assert_not_called()
        window.set_current_credential_index.assert_not_called()
        window.hide_progress_dialog.assert_not_called()
        window.refresh_btn.setEnabled.assert_not_called()

    def test_close_event_cancels_active_dmp_context(self):
        from PyQt5.QtGui import QCloseEvent

        token = SimpleNamespace(cancel=Mock())
        self.window._dmp_cancel_token = token

        self.window.closeEvent(QCloseEvent())

        token.cancel.assert_called()


def QThreadPool_global():
    from PyQt5.QtCore import QThreadPool

    return QThreadPool.globalInstance()


if __name__ == "__main__":
    unittest.main()
