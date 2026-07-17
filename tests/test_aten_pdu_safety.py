import unittest
from unittest.mock import Mock

from core.exceptions import CommandOutcomeUnknownError, CommandRejectedError
from handlers.aten.pdu import AtenPDUHandler


class Response:
    def __init__(self, status_code=200):
        self.status_code = status_code


class AtenPDUPrimitiveTests(unittest.TestCase):
    def handler(self):
        handler = AtenPDUHandler(
            "192.0.2.45",
            username="synthetic-user",
            password="synthetic-password",
        )
        handler.connected = True
        return handler

    def test_on_uses_one_aten_wire_send(self):
        handler = self.handler()
        handler._api_request = Mock(return_value=Response())

        self.assertTrue(handler.turn_on(1))

        handler._api_request.assert_called_once_with(
            "POST",
            "/api/outlet/relay",
            data={"index": 1, "method": "on"},
        )

    def test_off_uses_one_aten_wire_send(self):
        handler = self.handler()
        handler._api_request = Mock(return_value=Response())

        self.assertTrue(handler.turn_off(1))

        handler._api_request.assert_called_once_with(
            "POST",
            "/api/outlet/relay",
            data={"index": 1, "method": "off"},
        )

    def test_reboot_success_is_one_send_without_readback_recovery(self):
        handler = self.handler()
        handler._api_request = Mock(return_value=Response())
        handler.get_outlets_status = Mock()

        self.assertTrue(handler.reboot(1))

        handler._api_request.assert_called_once()
        handler.get_outlets_status.assert_not_called()

    def test_ambiguous_reboot_is_not_replayed_by_handler(self):
        handler = self.handler()
        handler._api_request = Mock(return_value=None)
        handler.get_outlets_status = Mock()

        with self.assertRaises(CommandOutcomeUnknownError):
            handler.reboot(1)

        handler._api_request.assert_called_once()
        handler.get_outlets_status.assert_not_called()

    def test_authoritative_rejected_on_is_typed_rejection(self):
        handler = self.handler()
        handler._api_request = Mock(return_value=Response(500))

        with self.assertRaises(CommandRejectedError):
            handler.turn_on(1)

        handler._api_request.assert_called_once()

    def test_authoritative_rejected_off_is_typed_rejection(self):
        handler = self.handler()
        handler._api_request = Mock(return_value=Response(500))

        with self.assertRaises(CommandRejectedError):
            handler.turn_off(1)

        handler._api_request.assert_called_once()

    def test_authoritative_rejected_reboot_is_typed_rejection_one_send(self):
        handler = self.handler()
        handler._api_request = Mock(return_value=Response(500))
        handler.get_outlets_status = Mock()

        with self.assertRaises(CommandRejectedError):
            handler.reboot(1)

        handler._api_request.assert_called_once()
        handler.get_outlets_status.assert_not_called()


if __name__ == "__main__":
    unittest.main()
