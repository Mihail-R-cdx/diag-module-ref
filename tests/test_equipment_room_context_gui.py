from __future__ import annotations

import os
import unittest
from unittest.mock import patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtCore import QEvent
    from PyQt5.QtWidgets import QApplication, QMessageBox
except ImportError:
    QApplication = None

from core.equipment_inventory import (
    EquipmentInventory,
    EquipmentInventoryLoadError,
    EquipmentInventoryMetadata,
    EquipmentRecord,
    InventoryLoadFailure,
)
from core.room_context import EquipmentRoomResolutionResult, RoomResolutionStatus, RoomVipStatus
from gui.equipment_pages import EQUIPMENT_PAGE_REGISTRY, PDU_DEVICE_NAMES


def record(
    record_id,
    *,
    ip_address=None,
    room_id="ROOM-1",
    room_name="Room One",
    device_kind="other",
    diagnostic_model=None,
    room_vip=None,
):
    return EquipmentRecord(
        record_id=record_id,
        source_model=diagnostic_model,
        diagnostic_model=diagnostic_model,
        ip_address=ip_address,
        mac_address=None,
        serial_number=None,
        room_id=room_id,
        room_name=room_name,
        device_kind=device_kind,
        room_vip=room_vip,
    )


def inventory(snapshot_id="sha256:" + "2" * 64):
    return EquipmentInventory.from_records(
        (
            record(
                "CODEC-1",
                ip_address="192.0.2.10",
                device_kind="video_codec",
                diagnostic_model="Huawei TE20",
                room_vip=True,
            ),
            record(
                "MATRIX-1",
                ip_address="192.0.2.11",
                device_kind="other",
                diagnostic_model="Extron IN1804",
                room_vip=True,
            ),
        ),
        EquipmentInventoryMetadata(schema_version=2, snapshot_id=snapshot_id),
    )


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class EquipmentRoomContextGUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")

    def build_window(self, inv=None, error=None):
        import gui.main_window as main_window

        if error is not None:
            patcher = patch.object(main_window, "load_equipment_inventory", side_effect=error)
        else:
            patcher = patch.object(main_window, "load_equipment_inventory", return_value=inv or inventory())
        self.addCleanup(patcher.stop)
        patcher.start()
        window = main_window.VCSDiagnosticApp()
        window.show()
        self.addCleanup(self._close_window, window)
        QApplication.processEvents()
        return window

    def _close_window(self, window):
        window.close()
        window.deleteLater()
        QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        QApplication.processEvents()

    def test_registry_attaches_shared_blocks_to_non_pdu_pages_only(self):
        window = self.build_window()
        for registration in EQUIPMENT_PAGE_REGISTRY:
            with self.subTest(screen=registration.screen_key):
                screen = window.screens[registration.screen_key]
                block = getattr(screen, "shared_room_information_block", None)
                if registration.shared_room_block:
                    self.assertIsNotNone(block)
                    self.assertTrue(block.property("roomContextBoundary"))
                else:
                    self.assertIsNone(block)
                    self.assertTrue(registration.dedicated_pdu_room_placement)
                    self.assertTrue(set(registration.device_models).issubset(PDU_DEVICE_NAMES))

    def test_selecting_new_ip_publishes_room_context_without_refresh(self):
        window = self.build_window()
        window.device_combo.setCurrentText("Huawei TE20")
        window.ip_entry.setText("192.0.2.10")
        QApplication.processEvents()

        block = window.screens["codec"].shared_room_information_block
        self.assertEqual("Room One", block.room_name_value.text())
        self.assertEqual("ДА", block.room_vip_value.text())
        self.assertEqual("success", block.room_vip_row.property("uiState"))

    def test_device_error_does_not_clear_available_room_context(self):
        window = self.build_window()
        window.device_combo.setCurrentText("Huawei TE20")
        window.ip_entry.setText("192.0.2.10")
        screen = window.screens["codec"]
        window._begin_request("Huawei TE20", "192.0.2.10", screen)
        window._publish_current_equipment_room_context("request_started", force=True)

        class Worker:
            device_name = "Huawei TE20"
            ip_address = "192.0.2.10"
            current_idx = 0
            creds_list = []

        with patch.object(QMessageBox, "critical"), patch.object(QMessageBox, "warning"):
            window.on_device_error(("connection_error", "synthetic failure", ""), Worker(), window._active_request["id"])

        block = screen.shared_room_information_block
        self.assertEqual("Room One", block.room_name_value.text())
        self.assertEqual("ДА", block.room_vip_value.text())

    def test_stale_room_publication_is_rejected_after_context_changes(self):
        window = self.build_window()
        window.device_combo.setCurrentText("Huawei TE20")
        window.ip_entry.setText("192.0.2.10")
        binding = window._equipment_room_context_binding
        generation = window._equipment_room_context_generation
        stale_result = EquipmentRoomResolutionResult(
            RoomResolutionStatus.RESOLVED,
            room_name="Stale Room",
            room_vip_status=RoomVipStatus.VIP_FALSE,
        )

        window.ip_entry.setText("192.0.2.11")
        accepted = window._accept_equipment_room_context_publication(
            generation,
            binding,
            stale_result,
            reason="stale_test",
            device_name="Huawei TE20",
        )

        self.assertFalse(accepted)
        block = window.screens["codec"].shared_room_information_block
        self.assertNotEqual("Stale Room", block.room_name_value.text())

    def test_inventory_failure_renders_safe_room_state_without_modal(self):
        error = EquipmentInventoryLoadError(
            InventoryLoadFailure.INVALID_SNAPSHOT,
            "synthetic",
        )
        window = self.build_window(error=error)
        with patch.object(QMessageBox, "critical") as critical, patch.object(QMessageBox, "warning") as warning:
            window.device_combo.setCurrentText("Huawei TE20")
            window.ip_entry.setText("192.0.2.10")
            QApplication.processEvents()

        critical.assert_not_called()
        warning.assert_not_called()
        block = window.screens["codec"].shared_room_information_block
        self.assertEqual("—", block.room_vip_value.text())
        self.assertIn("Equipment inventory unavailable", block.message_value.text())


if __name__ == "__main__":
    unittest.main()
