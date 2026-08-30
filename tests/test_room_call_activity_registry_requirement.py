"""Regression coverage for required CallActivity registry declarations."""

from __future__ import annotations

import unittest
from dataclasses import replace
from unittest.mock import patch

import gui.diagnostic_dispatch as dispatch


REGISTERED_SCREENS = {"codec", "matrix", "pdu", "audio_dsp"}
PAGE_MODELS_BY_SCREEN = {
    "codec": (
        "Huawei TE20",
        "Huawei TE40",
        "CloudLink Bar 310",
        "CloudLink Box 310",
        "Polycom RPG 310",
    ),
    "matrix": ("Extron IN1804",),
    "pdu": ("Aten PE8208AV", "Extron IPL T PCS4i"),
    "audio_dsp": ("Biamp Tesira Forte CI", "Extron DMP 64 Plus"),
}


class RequiredCallActivityRegistryTests(unittest.TestCase):
    REQUIRED_BASELINE_MODELS = (
        "Huawei TE20",
        "Huawei TE40",
        "CloudLink Bar 310",
        "CloudLink Box 310",
        "Polycom RPG 310",
    )

    def test_baseline_acceptance_oracle_declares_required_binding_on_each_exact_entry(self):
        entries = {entry.diagnostic_model: entry for entry in dispatch.dispatch_entries()}
        for model in self.REQUIRED_BASELINE_MODELS:
            with self.subTest(model=model):
                self.assertTrue(entries[model].call_activity_required)
                self.assertTrue(entries[model].call_activity_capability)
                self.assertIsNotNone(entries[model].call_activity_binding_key)

    def test_required_entry_cannot_silently_omit_capability_and_binding(self):
        original = dispatch.DISPATCH_REGISTRY
        required = next(entry for entry in original if entry.diagnostic_model == "Huawei TE20")
        invalid = replace(
            required,
            call_activity_capability=False,
            call_activity_binding_key=None,
        )
        mutated = tuple(
            invalid if entry.diagnostic_model == required.diagnostic_model else entry
            for entry in original
        )

        with patch.object(dispatch, "DISPATCH_REGISTRY", mutated):
            with self.assertRaisesRegex(ValueError, "required call-activity binding is missing"):
                dispatch.validate_dispatch_registry(
                    registered_screens=REGISTERED_SCREENS,
                    page_models_by_screen=PAGE_MODELS_BY_SCREEN,
                )


if __name__ == "__main__":
    unittest.main()
