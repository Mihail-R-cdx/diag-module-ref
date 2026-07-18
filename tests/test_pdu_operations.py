import unittest

from core.exceptions import (
    AuthenticationError,
    CommandError,
    CommandOutcomeUnknownError,
    CommandRejectedError,
)
from core.pdu import (
    BULK_COMMAND_OFF,
    BULK_COMMAND_ON,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_REBOOT,
    REFRESH,
    PDUOperationDescriptor,
    build_pdu_bulk_outlet_sequence,
    execute_pdu_bulk,
    execute_pdu_command,
    execute_pdu_refresh,
    pdu_result_capabilities,
)


class ScriptedPDUHandler:
    def __init__(self, reads=(), sends=(), connect_error=None):
        self.reads = list(reads)
        self.sends = list(sends)
        self.connect_error = connect_error
        self.read_count = 0
        self.sent_commands = []
        self.disconnected = False

    def connect(self):
        if self.connect_error is not None:
            raise self.connect_error

    def disconnect(self):
        self.disconnected = True

    def read_outlet_power_state(self, outlet_number):
        self.read_count += 1
        value = self.reads.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value

    def send_outlet_command_once(self, outlet_number, operation):
        self.sent_commands.append((outlet_number, operation))
        value = self.sends.pop(0) if self.sends else None
        if isinstance(value, BaseException):
            raise value


class PDUOperationContractTests(unittest.TestCase):
    def descriptor(self, model="Extron IPL T PCS4i", operation=REFRESH):
        return PDUOperationDescriptor(
            operation_id=1,
            generation=10,
            model=model,
            ip_address="192.0.2.44",
            operation=operation,
            outlet_number=1 if operation != REFRESH else None,
            credential_index=0,
        )

    def bulk_descriptor(self, model="Extron IPL T PCS4i", operation=BULK_COMMAND_ON, sequence=(1, 2)):
        return PDUOperationDescriptor(
            operation_id=2,
            generation=10,
            model=model,
            ip_address="192.0.2.44",
            operation=operation,
            credential_index=0,
            outlet_sequence=tuple(sequence),
        )

    def command_result(self, handler, model="Extron IPL T PCS4i", operation=COMMAND_ON):
        return execute_pdu_command(
            descriptor=self.descriptor(model=model, operation=operation),
            credentials={},
            is_current=lambda _descriptor: True,
            handler_factory=lambda *_args: handler,
        )

    def test_pcs4i_capabilities_hide_reboot_and_keep_on_off(self):
        self.assertEqual(
            {
                "refresh": True,
                "on": True,
                "off": True,
                "reboot": False,
                "bulk_on": True,
                "bulk_off": True,
            },
            pdu_result_capabilities("Extron IPL T PCS4i"),
        )
        self.assertTrue(pdu_result_capabilities("Aten PE8208AV")["reboot"])

    def test_unsupported_pcs4i_reboot_is_rejected_before_handler_acquisition(self):
        acquired = []

        def factory(*_args):
            acquired.append(True)
            raise AssertionError("must not acquire handler")

        with self.assertRaises(CommandError):
            execute_pdu_command(
                descriptor=self.descriptor(operation=COMMAND_REBOOT),
                credentials={},
                is_current=lambda _descriptor: True,
                handler_factory=factory,
            )

        self.assertEqual([], acquired)

    def test_invalid_pcs4i_outlet_is_rejected_before_handler_acquisition(self):
        acquired = []
        descriptor = self.descriptor(operation=COMMAND_ON)
        descriptor = PDUOperationDescriptor(
            **{**descriptor.__dict__, "outlet_number": 5}
        )

        with self.assertRaises(CommandError):
            execute_pdu_command(
                descriptor=descriptor,
                credentials={"password": "synthetic-password"},
                is_current=lambda _descriptor: True,
                handler_factory=lambda *_args: acquired.append(True),
            )

        self.assertEqual([], acquired)

    def test_pcs4i_credentials_are_normalized_before_handler_factory(self):
        captured = []

        class Handler:
            def connect(self):
                pass

            def disconnect(self):
                pass

            def get_outlets_status(self):
                return []

            def get_device_info(self):
                return {"model": "IPL T PCS4i", "manufacturer": "Extron"}

        def factory(model, ip_address, credentials):
            captured.append((model, ip_address, credentials))
            return Handler()

        execute_pdu_refresh(
            descriptor=self.descriptor(),
            credentials={
                "username": "unsupported-user",
                "password": "synthetic-password",
            },
            is_current=lambda _descriptor: True,
            handler_factory=factory,
        )

        self.assertEqual(
            [("Extron IPL T PCS4i", "192.0.2.44", {"password": "synthetic-password"})],
            captured,
        )

    def test_stale_refresh_is_dropped_before_handler_acquisition(self):
        acquired = []

        result = execute_pdu_refresh(
            descriptor=self.descriptor(),
            credentials={},
            is_current=lambda _descriptor: False,
            handler_factory=lambda *_args: acquired.append(True),
        )

        self.assertEqual({"_outcome": "stale", "operation": REFRESH}, result)
        self.assertEqual([], acquired)

    def test_stale_after_handler_acquisition_blocks_first_network_io(self):
        events = []

        class Handler:
            def connect(self):
                events.append("connect")

            def disconnect(self):
                events.append("disconnect")

        calls = []

        def is_current(_descriptor):
            calls.append(True)
            return len(calls) == 1

        result = execute_pdu_refresh(
            descriptor=self.descriptor(),
            credentials={},
            is_current=is_current,
            handler_factory=lambda *_args: Handler(),
        )

        self.assertEqual({"_outcome": "stale", "operation": REFRESH}, result)
        self.assertEqual(["disconnect"], events)

    def test_command_worker_emits_structured_indeterminate_outcome(self):
        from core.worker import PDUOperationWorker

        class Handler:
            def connect(self):
                pass

            def disconnect(self):
                pass

            def turn_on(self, _outlet):
                raise CommandOutcomeUnknownError("lost acknowledgement")

        worker = PDUOperationWorker(
            self.descriptor(operation=COMMAND_ON),
            credentials={},
            is_current=lambda _descriptor: True,
            handler_factory=lambda *_args: Handler(),
        )
        errors = []
        worker.signals.error.connect(errors.append)

        worker.run()

        self.assertEqual("indeterminate_outcome", errors[0][0])

    def test_command_worker_emits_structured_command_failure_outcome(self):
        from core.worker import PDUOperationWorker

        worker = PDUOperationWorker(
            self.descriptor(operation=COMMAND_ON),
            credentials={},
            is_current=lambda _descriptor: True,
            handler_factory=lambda *_args: ScriptedPDUHandler(
                reads=[False],
                sends=[CommandRejectedError("rejected")],
            ),
        )
        errors = []
        worker.signals.error.connect(errors.append)

        worker.run()

        self.assertEqual("command_failed", errors[0][0])

    def test_command_worker_keeps_unsupported_operation_distinct(self):
        from core.worker import PDUOperationWorker

        worker = PDUOperationWorker(
            self.descriptor(operation=COMMAND_REBOOT),
            credentials={},
            is_current=lambda _descriptor: True,
            handler_factory=lambda *_args: ScriptedPDUHandler(),
        )
        errors = []
        worker.signals.error.connect(errors.append)

        worker.run()

        self.assertEqual("unsupported_operation", errors[0][0])
        self.assertIn("does not support", errors[0][1])

    def test_command_worker_keeps_authentication_outcome_distinct(self):
        from core.worker import PDUOperationWorker

        worker = PDUOperationWorker(
            self.descriptor(operation=COMMAND_ON),
            credentials={},
            is_current=lambda _descriptor: True,
            handler_factory=lambda *_args: ScriptedPDUHandler(
                connect_error=AuthenticationError("bad credential")
            ),
        )
        errors = []
        worker.signals.error.connect(errors.append)

        worker.run()

        self.assertEqual("authentication_error", errors[0][0])

    def test_known_pre_state_acknowledged_success_uses_one_send(self):
        handler = ScriptedPDUHandler(reads=[False, True], sends=[None])

        result = self.command_result(handler, operation=COMMAND_ON)

        self.assertTrue(result["success"])
        self.assertEqual([(1, COMMAND_ON)], handler.sent_commands)
        self.assertEqual(2, handler.read_count)

    def test_known_pre_state_permits_one_controlled_resend(self):
        handler = ScriptedPDUHandler(reads=[True, True, False], sends=[None, None])

        result = self.command_result(handler, operation=COMMAND_OFF)

        self.assertTrue(result["success"])
        self.assertEqual([(1, COMMAND_OFF), (1, COMMAND_OFF)], handler.sent_commands)
        self.assertEqual(3, handler.read_count)

    def test_unknown_pre_state_valid_non_target_is_indeterminate_without_resend(self):
        handler = ScriptedPDUHandler(
            reads=[CommandOutcomeUnknownError("no pre-state"), True],
            sends=[None],
        )

        with self.assertRaises(CommandOutcomeUnknownError):
            self.command_result(handler, operation=COMMAND_OFF)

        self.assertEqual([(1, COMMAND_OFF)], handler.sent_commands)
        self.assertEqual(2, handler.read_count)

    def test_unavailable_post_readback_is_indeterminate_without_resend(self):
        handler = ScriptedPDUHandler(
            reads=[False, CommandOutcomeUnknownError("bad post-state")],
            sends=[None],
        )

        with self.assertRaises(CommandOutcomeUnknownError):
            self.command_result(handler, operation=COMMAND_ON)

        self.assertEqual([(1, COMMAND_ON)], handler.sent_commands)
        self.assertEqual(2, handler.read_count)

    def test_ambiguous_initial_delivery_reaches_target_without_resend(self):
        handler = ScriptedPDUHandler(
            reads=[False, True],
            sends=[CommandOutcomeUnknownError("lost ack")],
        )

        result = self.command_result(handler, operation=COMMAND_ON)

        self.assertTrue(result["success"])
        self.assertEqual([(1, COMMAND_ON)], handler.sent_commands)
        self.assertEqual(2, handler.read_count)

    def test_ambiguous_initial_delivery_remaining_pre_state_gets_one_resend(self):
        handler = ScriptedPDUHandler(
            reads=[True, True, False],
            sends=[CommandOutcomeUnknownError("lost ack"), None],
        )

        result = self.command_result(handler, operation=COMMAND_OFF)

        self.assertTrue(result["success"])
        self.assertEqual([(1, COMMAND_OFF), (1, COMMAND_OFF)], handler.sent_commands)
        self.assertEqual(3, handler.read_count)

    def test_ambiguous_controlled_resend_still_runs_terminal_confirmation(self):
        handler = ScriptedPDUHandler(
            reads=[True, True, False],
            sends=[None, CommandOutcomeUnknownError("lost ack")],
        )

        result = self.command_result(handler, operation=COMMAND_OFF)

        self.assertTrue(result["success"])
        self.assertEqual([(1, COMMAND_OFF), (1, COMMAND_OFF)], handler.sent_commands)
        self.assertEqual(3, handler.read_count)

    def test_device_rejection_is_failure_without_readback_driven_replay(self):
        handler = ScriptedPDUHandler(
            reads=[False],
            sends=[CommandRejectedError("rejected")],
        )

        with self.assertRaises(CommandRejectedError):
            self.command_result(handler, operation=COMMAND_ON)

        self.assertEqual([(1, COMMAND_ON)], handler.sent_commands)
        self.assertEqual(1, handler.read_count)

    def test_aten_reboot_success_is_one_send_without_readback(self):
        handler = ScriptedPDUHandler(sends=[None])

        result = self.command_result(
            handler,
            model="Aten PE8208AV",
            operation=COMMAND_REBOOT,
        )

        self.assertTrue(result["success"])
        self.assertEqual([(1, COMMAND_REBOOT)], handler.sent_commands)
        self.assertEqual(0, handler.read_count)

    def test_ambiguous_aten_reboot_is_not_replayed(self):
        handler = ScriptedPDUHandler(
            sends=[CommandOutcomeUnknownError("lost ack")]
        )

        with self.assertRaises(CommandOutcomeUnknownError):
            self.command_result(
                handler,
                model="Aten PE8208AV",
                operation=COMMAND_REBOOT,
            )

        self.assertEqual([(1, COMMAND_REBOOT)], handler.sent_commands)
        self.assertEqual(0, handler.read_count)

    def test_pcs4i_command_worker_boundary_is_password_only(self):
        from core.worker import PDUOperationWorker

        worker = PDUOperationWorker(
            self.descriptor(operation=COMMAND_ON),
            credentials={
                "username": "invented-user",
                "password": "synthetic-password",
            },
            is_current=lambda _descriptor: True,
        )

        self.assertEqual({"password": "synthetic-password"}, worker.credentials)
        self.assertIsNone(worker.username)
        self.assertEqual("synthetic-password", worker.password)

    def test_bulk_sequence_is_built_from_records_in_strict_order(self):
        records = [{"number": 3}, {"number": 1}, {"number": 2}]

        self.assertEqual(
            (1, 2, 3),
            build_pdu_bulk_outlet_sequence("Aten PE8208AV", records),
        )

    def test_bulk_duplicate_outlet_is_rejected_before_handler_acquisition(self):
        acquired = []
        descriptor = self.bulk_descriptor(sequence=(1, 1))

        with self.assertRaises(CommandError):
            execute_pdu_bulk(
                descriptor=descriptor,
                credentials={},
                is_current=lambda _descriptor: True,
                handler_factory=lambda *_args: acquired.append(True),
            )

        self.assertEqual([], acquired)

    def test_bulk_malformed_outlet_record_is_rejected_before_descriptor_capture(self):
        with self.assertRaises(CommandError):
            build_pdu_bulk_outlet_sequence("Aten PE8208AV", [{"number": "2"}])

    def test_bulk_sequence_capture_is_immutable_after_record_mutation(self):
        records = [{"number": 2}, {"number": 1}]
        sequence = build_pdu_bulk_outlet_sequence("Aten PE8208AV", records)

        records[0]["number"] = 8

        self.assertEqual((1, 2), sequence)

    def test_bulk_on_uses_existing_policy_for_each_outlet_with_inter_outlet_delay(self):
        handler = ScriptedPDUHandler(
            reads=[False, True, False, True, False, True],
            sends=[None, None, None],
        )
        delays = []

        result = execute_pdu_bulk(
            descriptor=self.bulk_descriptor(
                model="Aten PE8208AV",
                operation=BULK_COMMAND_ON,
                sequence=(3, 1, 2),
            ),
            credentials={},
            is_current=lambda _descriptor: True,
            handler_factory=lambda *_args: handler,
            delay=delays.append,
        )

        self.assertTrue(result["success"])
        self.assertEqual((1, 2, 3), result["outlet_sequence"])
        self.assertEqual((1, 2, 3), result["successful_outlets"])
        self.assertEqual([(1, COMMAND_ON), (2, COMMAND_ON), (3, COMMAND_ON)], handler.sent_commands)
        self.assertEqual([1.0, 1.0], delays)

    def test_bulk_off_fail_fast_reports_partial_without_replay_or_rollback(self):
        handler = ScriptedPDUHandler(
            reads=[True, False, True],
            sends=[None, CommandRejectedError("rejected")],
        )
        delays = []

        result = execute_pdu_bulk(
            descriptor=self.bulk_descriptor(operation=BULK_COMMAND_OFF, sequence=(1, 2, 3)),
            credentials={},
            is_current=lambda _descriptor: True,
            handler_factory=lambda *_args: handler,
            delay=delays.append,
        )

        self.assertFalse(result["success"])
        self.assertEqual("partial_failure", result["terminal_state"])
        self.assertEqual((1,), result["successful_outlets"])
        self.assertEqual(2, result["stopping_outlet"])
        self.assertEqual([(1, COMMAND_OFF), (2, COMMAND_OFF)], handler.sent_commands)
        self.assertEqual([1.0], delays)

    def test_bulk_stale_between_outlets_stops_before_delay_and_next_command(self):
        handler = ScriptedPDUHandler(reads=[False, True], sends=[None])
        delays = []
        calls = []

        def is_current(_descriptor):
            calls.append(True)
            return len(calls) < 3

        result = execute_pdu_bulk(
            descriptor=self.bulk_descriptor(sequence=(1, 2)),
            credentials={},
            is_current=is_current,
            handler_factory=lambda *_args: handler,
            delay=delays.append,
        )

        self.assertEqual("stale_after_partial_completion", result["terminal_state"])
        self.assertEqual((1,), result["successful_outlets"])
        self.assertEqual([(1, COMMAND_ON)], handler.sent_commands)
        self.assertEqual([], delays)

    def test_bulk_worker_auth_error_carries_zero_send_metadata(self):
        from core.worker import PDUOperationWorker

        worker = PDUOperationWorker(
            self.bulk_descriptor(sequence=(1, 2)),
            credentials={},
            is_current=lambda _descriptor: True,
            handler_factory=lambda *_args: ScriptedPDUHandler(
                connect_error=AuthenticationError("bad credential")
            ),
        )
        errors = []
        worker.signals.error.connect(errors.append)

        worker.run()

        self.assertEqual("authentication_error", errors[0][0])
        self.assertEqual({"state_changing_send_attempted": False}, errors[0][3])

    def test_command_worker_post_send_auth_is_indeterminate_not_retryable_auth(self):
        from core.worker import PDUOperationWorker

        handler = ScriptedPDUHandler(
            reads=[False, AuthenticationError("post-send credential failure")],
            sends=[None],
        )
        worker = PDUOperationWorker(
            self.descriptor(operation=COMMAND_ON),
            credentials={"password": "synthetic-password"},
            is_current=lambda _descriptor: True,
            handler_factory=lambda *_args: handler,
        )
        errors = []
        worker.signals.error.connect(errors.append)

        worker.run()

        self.assertEqual("indeterminate_outcome", errors[0][0])
        self.assertEqual([(1, COMMAND_ON)], handler.sent_commands)

    def test_bulk_worker_pre_send_auth_error_carries_zero_send_metadata(self):
        from core.worker import PDUOperationWorker

        worker = PDUOperationWorker(
            self.bulk_descriptor(sequence=(1, 2)),
            credentials={},
            is_current=lambda _descriptor: True,
            handler_factory=lambda *_args: ScriptedPDUHandler(
                reads=[AuthenticationError("bad credential")]
            ),
        )
        errors = []
        worker.signals.error.connect(errors.append)

        worker.run()

        self.assertEqual("authentication_error", errors[0][0])
        self.assertEqual({"state_changing_send_attempted": False}, errors[0][3])


if __name__ == "__main__":
    unittest.main()
