import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtWidgets import QApplication, QLabel
except ImportError:  # pragma: no cover
    QApplication = None

from core.equipment_inventory import (
    EquipmentInventory,
    EquipmentInventoryMetadata,
    EquipmentRecord,
)
from gui.diagnostic_dispatch import (
    DiagnosticActionPurpose,
    ModelResolutionStatus,
    dispatch_entries,
    dispatch_entry_for_model,
    dispatch_model_names,
    resolve_exact_model_for_ip,
    validate_dispatch_registry,
)
from gui.equipment_pages import EQUIPMENT_PAGE_REGISTRY


def record(record_id, *, ip_address="192.0.2.10", diagnostic_model="Huawei TE40", device_kind="other"):
    return EquipmentRecord(
        record_id=record_id,
        source_model="Synthetic",
        diagnostic_model=diagnostic_model,
        ip_address=ip_address,
        mac_address=None,
        serial_number=None,
        room_id="ROOM-1",
        room_name="Room",
        device_kind=device_kind,
        room_vip=None,
    )


def inventory(records):
    return EquipmentInventory.from_records(
        tuple(records),
        EquipmentInventoryMetadata(schema_version=2, snapshot_id="sha256:" + "2" * 64),
    )


class DispatchRegistryTests(unittest.TestCase):
    def test_registry_has_all_models_once_and_no_unknown_default(self):
        expected = (
            "Huawei TE20",
            "Huawei TE40",
            "CloudLink Bar 310",
            "Polycom RPG 310",
            "Extron IN1804",
            "Aten PE8208AV",
            "Extron IPL T PCS4i",
            "Biamp Tesira Forte CI",
            "Extron DMP 64 Plus",
        )
        self.assertEqual(expected, dispatch_model_names())
        self.assertEqual(len(expected), len(set(dispatch_model_names())))
        self.assertIsNone(dispatch_entry_for_model("Unknown Model"))

    def test_registry_integrity_checks_registered_screens(self):
        validate_dispatch_registry(
            registered_screens={"codec", "matrix", "pdu", "audio_dsp"},
            page_models_by_screen={
                registration.screen_key: registration.device_models
                for registration in EQUIPMENT_PAGE_REGISTRY
            },
        )
        for entry in dispatch_entries():
            self.assertNotIn("password", entry.__dict__)
            self.assertNotIn("handler", entry.__dict__)


class ExactModelResolverTests(unittest.TestCase):
    def resolve(self, records, ip="192.0.2.10"):
        return resolve_exact_model_for_ip(
            purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
            normalized_ip=ip,
            inventory=inventory(records) if records is not None else None,
        )

    def test_resolution_outcomes_preserve_cardinality_before_model_inspection(self):
        self.assertEqual(ModelResolutionStatus.INVENTORY_UNAVAILABLE, self.resolve(None).status)
        self.assertEqual(ModelResolutionStatus.IP_NOT_FOUND, self.resolve([]).status)
        self.assertEqual(
            ModelResolutionStatus.AMBIGUOUS_IP,
            self.resolve(
                [
                    record("A", diagnostic_model="Huawei TE40", device_kind="video_codec"),
                    record("B", diagnostic_model="Aten PE8208AV", device_kind="other"),
                ]
            ).status,
        )

    def test_exact_model_routes_without_kind_authority(self):
        cases = {
            "Aten PE8208AV": "pdu",
            "Extron IPL T PCS4i": "pdu",
            "Huawei TE40": "codec",
            "Extron IN1804": "matrix",
            "Biamp Tesira Forte CI": "audio_dsp",
            "Extron DMP 64 Plus": "audio_dsp",
        }
        for model, screen in cases.items():
            with self.subTest(model=model):
                result = self.resolve([record("A", diagnostic_model=model, device_kind="other")])
                self.assertEqual(ModelResolutionStatus.RESOLVED, result.status)
                self.assertEqual(screen, result.entry.screen_key)

    def test_null_and_unsupported_model_do_not_default(self):
        self.assertEqual(
            ModelResolutionStatus.MODEL_UNMAPPED,
            self.resolve([record("A", diagnostic_model=None, device_kind="video_codec")]).status,
        )
        inv = inventory(
            [
                EquipmentRecord(
                    record_id="A",
                    source_model="Synthetic",
                    diagnostic_model="Future Model",
                    ip_address="192.0.2.10",
                    mac_address=None,
                    serial_number=None,
                    room_id="ROOM-1",
                    room_name="Room",
                    device_kind="video_codec",
                    room_vip=None,
                )
            ]
        )
        result = resolve_exact_model_for_ip(
            purpose=DiagnosticActionPurpose.DIAGNOSTIC_START,
            normalized_ip="192.0.2.10",
            inventory=inv,
        )
        self.assertEqual(ModelResolutionStatus.MODEL_UNSUPPORTED, result.status)
        self.assertIsNone(result.entry)


@unittest.skipIf(QApplication is None, "PyQt5 is unavailable")
class MainPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_main_panel_has_no_persistent_model_selector(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        self.assertFalse(hasattr(window, "device_combo"))
        self.assertEqual([], window.findChildren(type(window.ip_entry), "deviceCombo"))
        labels = [label.text() for label in window.connection_panel.findChildren(QLabel)]
        self.assertNotIn("Устройство", labels)
        self.assertIn("IP-адрес", labels)


@unittest.skipIf(QApplication is None, "PyQt5 is unavailable")
class FailClosedProductionRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_bind_worker_with_unknown_model_does_not_create_codec_request(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        worker = Mock()
        worker.device_name = "Future Model"
        worker.ip_address = "192.0.2.10"
        worker.signals.result.connect = Mock()
        worker.signals.error.connect = Mock()
        worker.signals.progress.connect = Mock()
        worker.signals.status.connect = Mock()
        worker.signals.finished.connect = Mock()
        window._fail_request_start = Mock()

        window._bind_worker(worker)

        self.assertIsNone(window._active_request)
        window._fail_request_start.assert_called_once()
        worker.signals.result.connect.assert_not_called()

    def test_on_device_change_unknown_model_does_not_switch_to_codec(self):
        from gui.main_window import VCSDiagnosticApp

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.current_screen_type = "matrix"
        before_widget = window.screen_container.currentWidget()
        window.matrix_controller.invalidate_context = Mock()

        changed = window.on_device_change("Future Model")

        self.assertFalse(changed)
        self.assertEqual("matrix", window.current_screen_type)
        self.assertIs(before_widget, window.screen_container.currentWidget())
        window.matrix_controller.invalidate_context.assert_not_called()

    def test_unknown_screen_key_does_not_select_codec(self):
        from gui.main_window import VCSDiagnosticApp
        from gui.diagnostic_dispatch import DiagnosticDispatchEntry

        window = VCSDiagnosticApp()
        self.addCleanup(window.close)
        window.ip_entry.setText("192.0.2.10")
        bad_entry = DiagnosticDispatchEntry(
            "Huawei TE40",
            "unknown_screen",
            "huawei_te40",
        )
        window._resolve_model_for_action = Mock(
            return_value=type(
                "Resolution",
                (),
                {
                    "resolved": True,
                    "entry": bad_entry,
                    "status": ModelResolutionStatus.RESOLVED,
                },
            )()
        )
        window.ensure_ping_success = Mock(return_value=True)
        window.device_credentials["Huawei TE40"] = [
            {"username": "operator", "password": "secret-password"}
        ]
        before_widget = window.screen_container.currentWidget()

        with patch("gui.main_window.QMessageBox.warning"):
            window.refresh_data()

        self.assertIsNone(window._active_request)
        self.assertIs(before_widget, window.screen_container.currentWidget())


if __name__ == "__main__":
    unittest.main()
