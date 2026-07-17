import unittest
from unittest.mock import patch

from core.exceptions import AuthenticationError, CommandOutcomeUnknownError, CredentialRequired
from handlers.extron.pcs4i import ESC, ExtronIPLTPCS4iHandler


class FakeTelnetTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.sent = []
        self.closed = False

    def recv(self, _size=4096):
        if not self.responses:
            return b""
        value = self.responses.pop(0)
        if isinstance(value, list):
            if value:
                chunk = value.pop(0)
                if value:
                    self.responses.insert(0, value)
                return chunk
            return b""
        return value

    def sendall(self, data):
        self.sent.append(data)

    def close(self):
        self.closed = True


def make_handler(responses, password=None, **handler_kwargs):
    transport = FakeTelnetTransport(responses)
    handler = ExtronIPLTPCS4iHandler(
        "192.0.2.44",
        password=password,
        timeout=0.01,
        transport_factory=lambda *_args: transport,
        **handler_kwargs,
    )
    return handler, transport


class ExtronPCS4iAuthenticationTests(unittest.TestCase):
    def test_passwordless_session_uses_read_only_probe_and_sends_no_password(self):
        handler, transport = make_handler([b"", b"12\r\n"], password="unused")

        self.assertTrue(handler.connect())

        self.assertEqual([ESC + b"CK\r"], transport.sent)
        self.assertFalse(handler.credential_used)

    def test_fragmented_decorated_password_prompt_sends_assigned_password_once(self):
        handler, transport = make_handler(
            [[b"Pass", b"word:**********************"], b"Login Administrator\r\n"],
            password="secret-pass",
        )

        self.assertTrue(handler.connect())

        self.assertEqual([b"secret-pass\r"], transport.sent)
        self.assertTrue(handler.credential_used)

    def test_password_prompt_without_assigned_credential_is_not_auth_failure(self):
        handler, transport = make_handler([b"Password:"])

        with self.assertRaises(CredentialRequired):
            handler.connect()

        self.assertEqual([], transport.sent)

    def test_third_prompt_after_two_password_sends_is_authentication_error(self):
        handler, transport = make_handler(
            [b"Password:", b"Password:*", b"Password:**********************"],
            password="secret-pass",
        )

        with self.assertRaises(AuthenticationError):
            handler.connect()

        self.assertEqual([b"secret-pass\r", b"secret-pass\r"], transport.sent)

    def test_initial_prompt_is_not_reused_as_second_prompt(self):
        handler, transport = make_handler(
            [b"Password:", b"12\r\n"],
            password="secret-pass",
        )

        self.assertTrue(handler.connect())

        self.assertEqual([b"secret-pass\r"], transport.sent)

    def test_readiness_probe_prompt_after_first_send_uses_second_password_send(self):
        handler, transport = make_handler(
            [b"Password:", b"", b"Password:", b"12\r\n"],
            password="secret-pass",
        )

        self.assertTrue(handler.connect())

        self.assertEqual(2, transport.sent.count(b"secret-pass\r"))
        self.assertEqual([b"secret-pass\r", ESC + b"CK\r", b"secret-pass\r"], transport.sent)

    def test_readiness_probe_third_prompt_is_authentication_error(self):
        handler, transport = make_handler(
            [b"Password:", b"Password:", b"", b"Password:"],
            password="secret-pass",
        )

        with self.assertRaises(AuthenticationError):
            handler.connect()

        self.assertEqual(2, transport.sent.count(b"secret-pass\r"))
        self.assertEqual([b"secret-pass\r", b"secret-pass\r", ESC + b"CK\r"], transport.sent)

    def test_credentialless_readiness_probe_prompt_requires_credential(self):
        handler, transport = make_handler([b"", b"Password:"])

        with self.assertRaises(CredentialRequired):
            handler.connect()

        self.assertEqual([ESC + b"CK\r"], transport.sent)


class ExtronPCS4iSISTests(unittest.TestCase):
    def connected_handler(self, responses, **handler_kwargs):
        handler, transport = make_handler([b"", b"12\r\n"] + responses, **handler_kwargs)
        handler.connect()
        transport.sent.clear()
        return handler, transport

    def test_get_outlets_status_uses_pc_for_four_authoritative_states(self):
        handler, transport = self.connected_handler(
            [b"1\r\n", b"0\r\n", b"1\r\n", b"0\r\n"]
        )

        outlets = handler.get_outlets_status()

        self.assertEqual(["on", "off", "on", "off"], [item["status"] for item in outlets])
        self.assertEqual(
            ["Розетка 1", "Розетка 2", "Розетка 3", "Розетка 4"],
            [item["name"] for item in outlets],
        )
        self.assertEqual(
            [ESC + b"1PC\r", ESC + b"2PC\r", ESC + b"3PC\r", ESC + b"4PC\r"],
            transport.sent,
        )

    def test_ps_is_threshold_state_and_not_power_state(self):
        handler, transport = self.connected_handler([b"2\r\n"])

        self.assertEqual("full", handler.get_threshold_state(1))

        self.assertEqual([ESC + b"1PS\r"], transport.sent)

    def test_on_uses_exact_command_and_final_pc_readback(self):
        handler, transport = self.connected_handler(
            [b"Cpn1 Ppc1\r\n", b"1\r\n"]
        )

        self.assertTrue(handler.turn_on(1))

        self.assertEqual(
            [ESC + b"1*1PC\r", ESC + b"1PC\r"],
            transport.sent,
        )

    def test_invalid_outlet_is_rejected_before_network_send(self):
        handler, transport = self.connected_handler([])

        with self.assertRaises(ValueError):
            handler.turn_off(5)

        self.assertEqual([], transport.sent)

    def test_unconfirmed_acknowledgement_is_ambiguous_without_resend(self):
        handler, transport = self.connected_handler(
            [b"bad\r\n"]
        )

        with self.assertRaises(CommandOutcomeUnknownError):
            handler.send_outlet_command_once(1, "off")

        self.assertEqual(1, transport.sent.count(ESC + b"1*0PC\r"))
        self.assertEqual(0, transport.sent.count(ESC + b"1PC\r"))

    def test_off_uses_exact_command_acknowledgement(self):
        handler, transport = self.connected_handler(
            [b"Cpn1 Ppc0\r\n"]
        )

        handler.send_outlet_command_once(1, "off")

        self.assertEqual([ESC + b"1*0PC\r"], transport.sent)

    def test_read_outlet_power_state_reports_malformed_pc(self):
        handler, transport = self.connected_handler(
            [b"garbled\r\n"]
        )

        with self.assertRaises(CommandOutcomeUnknownError):
            handler.send_outlet_command_once(1, "off")

        self.assertEqual(1, transport.sent.count(ESC + b"1*0PC\r"))
        self.assertEqual(0, transport.sent.count(ESC + b"1PC\r"))

    def test_turn_off_reads_final_pc_after_acknowledged_send(self):
        handler, transport = self.connected_handler(
            [b"Cpn1 Ppc0\r\n", b"0\r\n"]
        )

        self.assertTrue(handler.turn_off(1))

        self.assertEqual(1, transport.sent.count(ESC + b"1*0PC\r"))
        self.assertEqual(1, transport.sent.count(ESC + b"1PC\r"))

    def test_handler_does_not_own_controlled_resend_policy(self):
        handler, transport = self.connected_handler(
            [b"Cpn1 Ppc0\r\n"]
        )

        handler.send_outlet_command_once(1, "off")

        self.assertEqual(1, transport.sent.count(ESC + b"1*0PC\r"))
        self.assertEqual(0, transport.sent.count(ESC + b"1PC\r"))

    def test_http_name_parser_maps_confirmed_xname_representation(self):
        body = """
        <script>
        var xName1 = "Codec";
        var xName2 = 'Display';
        var xName3 = "";
        var xName4 = "Matrix";
        </script>
        """

        self.assertEqual(
            {1: "Codec", 2: "Display", 4: "Matrix"},
            ExtronIPLTPCS4iHandler.parse_http_outlet_names(body),
        )

    def test_http_name_parser_maps_real_evidence_xname_representation(self):
        body = """
        <script>
        xName1='123';
        xName2='VCS';
        xName3='Transmitter';
        xName4='Receptacle 4';
        </script>
        """

        self.assertEqual(
            {1: "123", 2: "VCS", 3: "Transmitter", 4: "Receptacle 4"},
            ExtronIPLTPCS4iHandler.parse_http_outlet_names(body),
        )

    def test_production_http_name_path_is_confirmed_status_page(self):
        self.assertEqual("/nortxe_status.html", ExtronIPLTPCS4iHandler.HTTP_NAME_PATH)

    def test_get_outlets_status_requests_confirmed_production_http_name_path(self):
        requested = []
        body = """
        <script>
        xName1='123';
        xName2='VCS';
        xName3='Transmitter';
        xName4='Receptacle 4';
        </script>
        """
        handler, transport = self.connected_handler(
            [b"1\r\n", b"0\r\n", b"1\r\n", b"0\r\n"],
            http_get=lambda path, _timeout: requested.append(path) or body,
        )

        outlets = handler.get_outlets_status()

        self.assertEqual(["/nortxe_status.html"], requested)
        self.assertEqual(["on", "off", "on", "off"], [item["status"] for item in outlets])
        self.assertEqual(
            ["123", "VCS", "Transmitter", "Receptacle 4"],
            [item["name"] for item in outlets],
        )
        self.assertEqual(
            [ESC + b"1PC\r", ESC + b"2PC\r", ESC + b"3PC\r", ESC + b"4PC\r"],
            transport.sent,
        )

    def test_partial_http_names_keep_per_outlet_russian_fallback(self):
        body = """
        <script>
        xName1='Display';
        xName2='';
        xName3='Codec';
        </script>
        """
        handler, _transport = self.connected_handler(
            [b"1\r\n", b"0\r\n", b"1\r\n", b"0\r\n"],
            http_get=lambda _path, _timeout: body,
        )

        outlets = handler.get_outlets_status()

        self.assertEqual(
            ["Display", "Розетка 2", "Codec", "Розетка 4"],
            [item["name"] for item in outlets],
        )

    def test_http_name_failure_keeps_telnet_status_successful_with_fallback_names(self):
        def failing_http(_path, _timeout):
            raise RuntimeError("HTTP unavailable")

        handler, _transport = self.connected_handler(
            [b"1\r\n", b"0\r\n", b"1\r\n", b"0\r\n"],
            http_get=failing_http,
        )

        outlets = handler.get_outlets_status()

        self.assertEqual(["on", "off", "on", "off"], [item["status"] for item in outlets])
        self.assertEqual(
            ["Розетка 1", "Розетка 2", "Розетка 3", "Розетка 4"],
            [item["name"] for item in outlets],
        )

    def test_http_401_and_403_keep_telnet_status_without_credential_fallback(self):
        class Response:
            def __init__(self, status_code):
                self.status_code = status_code
                self.text = "xName1='Should not be used';"

            def raise_for_status(self):
                raise AssertionError("401/403 should not raise into credential fallback")

        for status_code in (401, 403):
            with self.subTest(status_code=status_code):
                handler, transport = self.connected_handler(
                    [b"1\r\n", b"0\r\n", b"1\r\n", b"0\r\n"],
                )

                with patch("handlers.extron.pcs4i.requests.get", return_value=Response(status_code)) as get:
                    outlets = handler.get_outlets_status()

                get.assert_called_once_with(
                    "http://192.0.2.44/nortxe_status.html",
                    timeout=handler.timeout,
                )
                self.assertEqual(["on", "off", "on", "off"], [item["status"] for item in outlets])
                self.assertEqual(
                    ["Розетка 1", "Розетка 2", "Розетка 3", "Розетка 4"],
                    [item["name"] for item in outlets],
                )
                self.assertFalse(handler.credential_used)
                self.assertEqual(
                    [ESC + b"1PC\r", ESC + b"2PC\r", ESC + b"3PC\r", ESC + b"4PC\r"],
                    transport.sent,
                )


if __name__ == "__main__":
    unittest.main()
