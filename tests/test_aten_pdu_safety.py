import unittest
from unittest.mock import Mock

from core.exceptions import CommandError, CommandOutcomeUnknownError
from handlers.aten.pdu import AtenPDUHandler


class Response:
    def __init__(self, status_code=200):
        self.status_code = status_code


class AtenPDUSafetyTests(unittest.TestCase):
    def handler(self):
        handler = AtenPDUHandler(
            "192.0.2.45",
            username="synthetic-user",
            password="synthetic-password",
        )
        handler.connected = True
        return handler

    def test_on_success_requires_authoritative_confirmation(self):
        handler = self.handler()
        handler._try_read_outlet_power_state = Mock(side_effect=[False, True])
        handler._send_outlet_command_once = Mock()

        self.assertTrue(handler.turn_on(1))

        handler._send_outlet_command_once.assert_called_once_with(1, "on")
        self.assertEqual(2, handler._try_read_outlet_power_state.call_count)

    def test_known_pre_state_recovery_uses_one_controlled_resend(self):
        handler = self.handler()
        handler._try_read_outlet_power_state = Mock(side_effect=[True, True, False])
        handler._send_outlet_command_once = Mock()

        self.assertTrue(handler.turn_off(1))

        self.assertEqual(2, handler._send_outlet_command_once.call_count)
        self.assertEqual(3, handler._try_read_outlet_power_state.call_count)

    def test_known_pre_state_with_unavailable_post_readback_is_indeterminate(self):
        handler = self.handler()
        handler._try_read_outlet_power_state = Mock(side_effect=[False, None])
        handler._send_outlet_command_once = Mock()

        with self.assertRaises(CommandOutcomeUnknownError):
            handler.turn_on(1)

        handler._send_outlet_command_once.assert_called_once_with(1, "on")
        self.assertEqual(2, handler._try_read_outlet_power_state.call_count)

    def test_unknown_pre_state_does_not_resend(self):
        handler = self.handler()
        handler._try_read_outlet_power_state = Mock(side_effect=[None, None])
        handler._send_outlet_command_once = Mock()

        with self.assertRaises(CommandOutcomeUnknownError):
            handler.turn_on(1)

        handler._send_outlet_command_once.assert_called_once_with(1, "on")

    def test_ambiguous_initial_delivery_is_indeterminate_without_blind_resend(self):
        handler = self.handler()
        handler._try_read_outlet_power_state = Mock(side_effect=[None, False])
        handler._send_outlet_command_once = Mock(
            side_effect=CommandOutcomeUnknownError("lost ack")
        )

        with self.assertRaises(CommandOutcomeUnknownError):
            handler.turn_on(1)

        handler._send_outlet_command_once.assert_called_once_with(1, "on")

    def test_ambiguous_initial_send_with_unavailable_post_readback_is_indeterminate(self):
        handler = self.handler()
        handler._try_read_outlet_power_state = Mock(side_effect=[False, None])
        handler._send_outlet_command_once = Mock(
            side_effect=CommandOutcomeUnknownError("lost ack")
        )

        with self.assertRaises(CommandOutcomeUnknownError):
            handler.turn_on(1)

        handler._send_outlet_command_once.assert_called_once_with(1, "on")
        self.assertEqual(2, handler._try_read_outlet_power_state.call_count)

    def test_reboot_success_is_one_send_without_readback_recovery(self):
        handler = self.handler()
        handler._api_request = Mock(return_value=Response())
        handler.get_outlets_status = Mock()

        self.assertTrue(handler.reboot(1))

        handler._api_request.assert_called_once()
        handler.get_outlets_status.assert_not_called()

    def test_ambiguous_reboot_is_not_replayed(self):
        handler = self.handler()
        handler._api_request = Mock(return_value=None)
        handler.get_outlets_status = Mock()

        with self.assertRaises(CommandOutcomeUnknownError):
            handler.reboot(1)

        handler._api_request.assert_called_once()
        handler.get_outlets_status.assert_not_called()

    def test_authoritative_rejected_on_is_failure_without_resend(self):
        handler = self.handler()
        handler._try_read_outlet_power_state = Mock(side_effect=[False])
        handler._api_request = Mock(return_value=Response(500))

        with self.assertRaises(CommandError):
            handler.turn_on(1)

        handler._api_request.assert_called_once()
        self.assertEqual(1, handler._try_read_outlet_power_state.call_count)

    def test_authoritative_rejected_off_is_failure_without_resend(self):
        handler = self.handler()
        handler._try_read_outlet_power_state = Mock(side_effect=[True])
        handler._api_request = Mock(return_value=Response(500))

        with self.assertRaises(CommandError):
            handler.turn_off(1)

        handler._api_request.assert_called_once()
        self.assertEqual(1, handler._try_read_outlet_power_state.call_count)

    def test_authoritative_rejected_reboot_is_failure_one_send(self):
        handler = self.handler()
        handler._api_request = Mock(return_value=Response(500))
        handler.get_outlets_status = Mock()

        with self.assertRaises(CommandError):
            handler.reboot(1)

        handler._api_request.assert_called_once()
        handler.get_outlets_status.assert_not_called()


if __name__ == "__main__":
    unittest.main()
