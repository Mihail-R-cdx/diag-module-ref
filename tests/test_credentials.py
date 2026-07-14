import json
from pathlib import Path
import tempfile
import unittest

from core.credentials import (
    AUTH_NONE,
    AUTH_PASSWORD,
    AUTH_USERNAME_PASSWORD,
    Credential,
    CredentialProvider,
    JsonCredentialProvider,
    application_root,
    default_credentials_path,
    resolve_request_credential_candidates,
    resolve_request_credentials,
)
from core.exceptions import (
    CredentialFieldMissingError,
    CredentialFileMissingError,
    CredentialJsonError,
    CredentialProfileNotFoundError,
    CredentialSchemaError,
)
from gui.main_window import VCSDiagnosticApp


class JsonCredentialProviderTests(unittest.TestCase):
    def write_document(self, directory, document):
        path = Path(directory) / "credentials.local.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def valid_document(self):
        return {
            "version": 1,
            "profiles": {
                "user-pass": {
                    "auth_mode": AUTH_USERNAME_PASSWORD,
                    "username": "synthetic-user",
                    "password": "synthetic-password",
                },
                "password-only": {
                    "auth_mode": AUTH_PASSWORD,
                    "password": "synthetic-password",
                },
                "none": {"auth_mode": AUTH_NONE},
            },
            "device_profiles": {"Model A": "user-pass", "Model B": "password-only", "Model C": "none"},
        }

    def test_loads_mapped_username_password_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            provider = JsonCredentialProvider(self.write_document(directory, self.valid_document()))
            credential = provider.resolve(device_model="Model A")
        self.assertEqual(AUTH_USERNAME_PASSWORD, credential.auth_mode)
        self.assertEqual("synthetic-user", credential.username)

    def test_gui_model_labels_resolve_their_exact_profile_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            document = self.valid_document()
            document["device_profiles"] = {
                model: "user-pass"
                for model in (
                    "Huawei TE-20", "Huawei TE-40", "CloudLink Bar 310",
                    "Polycom RPG 310", "Biamp Tesira Forte CI", "Extron IN1804",
                    "Aten PE8208AV",
                )
            }
            provider = JsonCredentialProvider(self.write_document(directory, document))
            for model in document["device_profiles"]:
                self.assertEqual("synthetic-user", provider.resolve(device_model=model).username)

    def test_supports_password_only_and_unauthenticated_contracts(self):
        with tempfile.TemporaryDirectory() as directory:
            provider = JsonCredentialProvider(self.write_document(directory, self.valid_document()))
            password_only = provider.resolve(device_model="Model B")
            unauthenticated = provider.resolve(device_model="Model C")
        self.assertEqual({"password": "synthetic-password"}, password_only.as_handler_kwargs())
        self.assertEqual({}, unauthenticated.as_handler_kwargs())

    def test_distinguishes_missing_file_invalid_json_and_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = JsonCredentialProvider(Path(directory) / "missing.json")
            with self.assertRaises(CredentialFileMissingError):
                missing.resolve(device_model="Model A")
            invalid = Path(directory) / "invalid.json"
            invalid.write_text("{", encoding="utf-8")
            with self.assertRaises(CredentialJsonError) as error:
                JsonCredentialProvider(invalid).resolve(device_model="Model A")
            self.assertNotIn("synthetic-password", str(error.exception))
            schema = self.write_document(directory, {"version": 2, "profiles": {}})
            with self.assertRaises(CredentialSchemaError):
                JsonCredentialProvider(schema).resolve(device_model="Model A")

    def test_rejects_missing_profile_and_required_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            document = self.valid_document()
            document["profiles"]["user-pass"].pop("password")
            provider = JsonCredentialProvider(self.write_document(directory, document))
            with self.assertRaises(CredentialFieldMissingError):
                provider.resolve(device_model="Model A")
            with self.assertRaises(CredentialProfileNotFoundError):
                provider.resolve(device_model="Unknown")

    def test_direct_injection_wins_without_a_local_file(self):
        provider = JsonCredentialProvider(Path("does-not-exist.json"))
        direct = resolve_request_credentials(
            provider,
            device_model="Model A",
            explicit_credentials=Credential(AUTH_USERNAME_PASSWORD, "test-user", "test-password"),
        )
        self.assertEqual("test-user", direct.username)

    def test_credential_repr_and_str_never_disclose_values(self):
        credential = Credential(AUTH_USERNAME_PASSWORD, "synthetic-user", "synthetic-password")
        for rendered in (repr(credential), str(credential), f"assertion helper: {credential!r}"):
            self.assertNotIn("synthetic-user", rendered)
            self.assertNotIn("synthetic-password", rendered)

    def test_replaceable_provider_reaches_gui_composition_without_json_coupling(self):
        class TestProvider(CredentialProvider):
            def resolve(self, *, device_model=None, profile_name=None):
                self.request = (device_model, profile_name)
                return Credential(AUTH_USERNAME_PASSWORD, "synthetic-user", "synthetic-password")

        provider = TestProvider()
        window = VCSDiagnosticApp.__new__(VCSDiagnosticApp)
        window.credential_provider = provider
        resolved = window.resolve_device_credentials("Huawei TE-20")
        self.assertEqual(("Huawei TE-20", None), provider.request)
        self.assertEqual("synthetic-user", resolved["username"])
        self.assertNotIn("auth_mode", resolved)

    def test_default_path_is_anchored_to_the_application_module(self):
        self.assertEqual(application_root() / "credentials.local.json", default_credentials_path())
        self.assertTrue((application_root() / "main.py").is_file())

    def test_gui_composition_resolves_model_profile_without_rendering_values(self):
        with tempfile.TemporaryDirectory() as directory:
            window = VCSDiagnosticApp.__new__(VCSDiagnosticApp)
            window.credential_provider = JsonCredentialProvider(
                self.write_document(directory, self.valid_document())
            )
            resolved = window.resolve_device_credentials("Model A")
        self.assertEqual({"username", "password"}, set(resolved))

    def test_string_and_ordered_mappings_resolve_candidates_in_json_order(self):
        with tempfile.TemporaryDirectory() as directory:
            document = self.valid_document()
            document["profiles"].update({
                f"profile-{index}": {
                    "auth_mode": AUTH_USERNAME_PASSWORD,
                    "username": f"synthetic-user-{index}",
                    "password": f"synthetic-password-{index}",
                }
                for index in range(10)
            })
            document["device_profiles"] = {
                "String": "profile-0",
                "List": [f"profile-{index}" for index in range(10)],
            }
            provider = JsonCredentialProvider(self.write_document(directory, document))
            self.assertEqual(1, len(provider.resolve_candidates(device_model="String")))
            candidates = provider.resolve_candidates(device_model="List")
            self.assertEqual(10, len(candidates))
            self.assertEqual(
                [f"synthetic-user-{index}" for index in range(10)],
                [candidate.username for candidate in candidates],
            )
            self.assertEqual("synthetic-user-0", provider.resolve(device_model="List").username)

    def test_candidate_source_priority_and_legacy_provider_compatibility(self):
        class LegacyProvider(CredentialProvider):
            def resolve(self, *, device_model=None, profile_name=None):
                self.request = (device_model, profile_name)
                return Credential(AUTH_USERNAME_PASSWORD, "synthetic-user", "synthetic-password")

        provider = LegacyProvider()
        direct = resolve_request_credential_candidates(
            provider,
            device_model="ignored",
            profile_name="ignored",
            explicit_credentials=Credential(AUTH_PASSWORD, password="synthetic-direct-password"),
        )
        self.assertEqual(1, len(direct))
        self.assertEqual(AUTH_PASSWORD, direct[0].auth_mode)
        candidates = resolve_request_credential_candidates(
            provider, device_model="Model A", profile_name="explicit"
        )
        self.assertEqual(("Model A", "explicit"), provider.request)
        self.assertEqual(1, len(candidates))

    def test_invalid_chain_is_rejected_without_partial_candidates_or_secret_values(self):
        invalid_mappings = (
            [],
            ["user-pass", ""],
            ["user-pass", "   "],
            ["user-pass", 42],
            ["user-pass", {}],
            {"primary": "user-pass"},
            ["user-pass", "missing-profile"],
        )
        with tempfile.TemporaryDirectory() as directory:
            for mapping in invalid_mappings:
                with self.subTest(mapping_type=type(mapping).__name__):
                    document = self.valid_document()
                    document["device_profiles"] = {"Model A": mapping}
                    provider = JsonCredentialProvider(self.write_document(directory, document))
                    with self.assertRaises((CredentialSchemaError, CredentialProfileNotFoundError)) as error:
                        provider.resolve_candidates(device_model="Model A")
                    self.assertNotIn("synthetic-user", str(error.exception))
                    self.assertNotIn("synthetic-password", str(error.exception))

    def test_gui_candidate_composition_preserves_order_and_auth_mode_kwargs(self):
        class CandidateProvider(CredentialProvider):
            def resolve(self, *, device_model=None, profile_name=None):
                return Credential(AUTH_NONE)

            def resolve_candidates(self, *, device_model=None, profile_name=None):
                return (
                    Credential(AUTH_PASSWORD, password="synthetic-password-only"),
                    Credential(AUTH_NONE),
                    Credential(AUTH_USERNAME_PASSWORD, "synthetic-user", "synthetic-password"),
                )

        window = VCSDiagnosticApp.__new__(VCSDiagnosticApp)
        window.credential_provider = CandidateProvider()
        self.assertEqual(
            [
                {"password": "synthetic-password-only"},
                {},
                {"username": "synthetic-user", "password": "synthetic-password"},
            ],
            window.resolve_device_credential_candidates("Model A"),
        )
