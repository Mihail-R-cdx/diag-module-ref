import unittest

from core.codec_connection_profiles import order_codec_profiles
from core.credentials import CredentialAttemptPlan
from core.exceptions import (
    AuthenticationError,
    CodecFailureCategory,
    CommandError,
    CommandOutcomeUnknownError,
    ParseError,
    SessionInvalidError,
    classify_codec_failure,
)


class CredentialAttemptPlanTests(unittest.TestCase):
    def test_plan_starts_at_saved_index_advances_monotonically_and_never_wraps(self):
        plan = CredentialAttemptPlan(("first", "second", "third"), 1)

        self.assertEqual("second", plan.current_candidate)
        self.assertTrue(plan.advance_after_authentication_failure())
        self.assertEqual(2, plan.current_index)
        self.assertFalse(plan.advance_after_authentication_failure())
        self.assertEqual((1, 2), plan.attempted_indexes)

    def test_invalid_saved_index_safely_starts_at_zero(self):
        self.assertEqual(0, CredentialAttemptPlan(("only",), 99).current_index)


class CodecProfileOrderingTests(unittest.TestCase):
    def test_box_uses_https_443_without_aliasing_application_model(self):
        profiles = order_codec_profiles("CloudLink Box 310")
        self.assertEqual([(443, True)], [(item["port"], item["use_ssl"]) for item in profiles])
    def test_supported_saved_te20_https_profile_is_first_and_deduplicated(self):
        profiles = order_codec_profiles(
            "Huawei TE20",
            {"port": 443, "use_ssl": True, "label": "saved HTTPS"},
            te20_https_ready=True,
        )

        self.assertEqual([(443, True), (80, False)], [
            (profile["port"], profile["use_ssl"]) for profile in profiles
        ])

    def test_unsupported_saved_profile_is_ignored(self):
        profiles = order_codec_profiles(
            "Huawei TE40",
            {"port": 8443, "use_ssl": True},
        )
        self.assertEqual([(443, True), (80, False)], [
            (profile["port"], profile["use_ssl"]) for profile in profiles
        ])


class CodecFailureClassificationTests(unittest.TestCase):
    def test_classification_uses_types_not_message_text(self):
        self.assertEqual(
            CodecFailureCategory.AUTHENTICATION,
            classify_codec_failure(AuthenticationError("confirmed")),
        )
        self.assertEqual(
            CodecFailureCategory.SESSION_INVALID,
            classify_codec_failure(SessionInvalidError("401")),
        )
        self.assertEqual(
            CodecFailureCategory.PROTOCOL,
            classify_codec_failure(ParseError("auth 403")),
        )
        self.assertEqual(
            CodecFailureCategory.COMMAND,
            classify_codec_failure(CommandError("success: 0")),
        )
        self.assertEqual(
            CodecFailureCategory.UNKNOWN_COMMAND_OUTCOME,
            classify_codec_failure(CommandOutcomeUnknownError("response lost")),
        )


if __name__ == "__main__":
    unittest.main()
