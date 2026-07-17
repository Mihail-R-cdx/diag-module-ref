import unittest

from core.exceptions import CommandError, CommandOutcomeUnknownError
from core.pdu import (
    COMMAND_ON,
    COMMAND_REBOOT,
    REFRESH,
    PDUOperationDescriptor,
    execute_pdu_command,
    execute_pdu_refresh,
    pdu_result_capabilities,
)


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

    def test_pcs4i_capabilities_hide_reboot_and_keep_on_off(self):
        self.assertEqual(
            {"refresh": True, "on": True, "off": True, "reboot": False},
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


if __name__ == "__main__":
    unittest.main()
