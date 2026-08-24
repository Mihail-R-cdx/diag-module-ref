"""Regression coverage for retiring the PDU-hosted related-codec feature."""

import os
import unittest

class PDURoomCodecRemovalTests(unittest.TestCase):
    def test_pdu_screen_has_no_related_codec_or_meter_presentation(self):
        root = os.path.dirname(os.path.dirname(__file__))
        with open(os.path.join(root, "gui", "screens", "pdu_screen.py"), encoding="utf-8") as source:
            code = source.read()
        self.assertNotIn("set_related_room_codec", code)
        self.assertNotIn("microphone_meter_bar", code)
        self.assertNotIn("Комната и связанный кодек", code)

    def test_production_composition_does_not_import_or_create_enrichment_controller(self):
        root = os.path.dirname(os.path.dirname(__file__))
        with open(os.path.join(root, "gui", "main_window.py"), encoding="utf-8") as source:
            code = source.read()
        self.assertNotIn("PDURoomCodecEnrichmentController", code)
        self.assertNotIn("pdu_room_codec_enrichment_controller", code)

    def test_pdu_controller_has_no_enrichment_publication_hooks(self):
        root = os.path.dirname(os.path.dirname(__file__))
        with open(os.path.join(root, "gui", "pdu_controller.py"), encoding="utf-8") as source:
            code = source.read()
        self.assertNotIn("_publish_accepted_refresh", code)
        self.assertNotIn("_publish_superseded", code)
