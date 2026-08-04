"""Focused GUI regression tests for equipment-page switch presentation.

Covers the application-owned, display-only switch-connection presentation
contract: registry-wide row placement (including PDU), safe scalar resolution
outcomes, non-narrowing on ambiguity, request-independence, snapshot/model/IP
invalidation, stale-publication rejection, and the codec room-block ownership
rebuild contract after deferred-deletion processing.

Uses synthetic inventory only; no real workbook, generated production snapshot,
credential file, device, or network is required.
"""

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
from core.switch_connection_context import (
    SwitchConnectionResolver,
    SwitchConnectionStatus,
)
from gui.equipment_pages import (
    EQUIPMENT_PAGE_REGISTRY,
    PDU_DEVICE_NAMES,
    SWITCH_IP_LABEL,
    SWITCH_PORT_LABEL,
    RoomInformationBlock,
    registrations_by_screen,
)


def record(
    record_id,
    *,
    ip_address=None,
    room_id="ROOM-1",
    room_name="Room One",
    device_kind="other",
    diagnostic_model=None,
    room_vip=None,
    switch_ip_address=None,
    switch_port=None,
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
        switch_ip_address=switch_ip_address,
        switch_port=switch_port,
    )


def inventory(snapshot_id="sha256:" + "2" * 64, *, records=(), schema_version=3):
    return EquipmentInventory.from_records(
        tuple(records),
        EquipmentInventoryMetadata(schema_version=schema_version, snapshot_id=snapshot_id),
    )


def _codec(*args, **kwargs):
    kwargs.setdefault("ip_address", "192.0.2.10")
    kwargs.setdefault("device_kind", "video_codec")
    kwargs.setdefault("diagnostic_model", "Huawei TE20")
    kwargs.setdefault("room_vip", True)
    return record(*args, **kwargs)


def _flush_deferred(app):
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class EquipmentSwitchPresentationGUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")

    def build_window(self, inv=None, error=None):
        import gui.main_window as main_window

        if error is not None:
            patcher = patch.object(main_window, "load_equipment_inventory", side_effect=error)
        else:
            patcher = patch.object(main_window, "load_equipment_inventory", return_value=inv)
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

    def _register(self, window, device_name, ip):
        window.ip_entry.setText(ip)
        window._accept_test_diagnostic_model(device_name)
        QApplication.processEvents()

    # --- Registry placement (7.1, 7.2) ---

    def test_both_switch_rows_exist_exactly_once_in_every_registered_screen(self):
        from PyQt5.QtWidgets import QFrame

        inv = inventory(
            records=(
                _codec("CODEC-1", switch_ip_address="10.0.0.1", switch_port="Gi1/1"),
                record(
                    "MATRIX-1",
                    ip_address="192.0.2.11",
                    device_kind="other",
                    diagnostic_model="Extron IN1804",
                ),
                record(
                    "PDU-A",
                    ip_address="192.0.2.12",
                    device_kind="pdu",
                    diagnostic_model="Aten PE8208AV",
                    switch_ip_address="10.0.0.9",
                    switch_port="Port 4",
                ),
                record(
                    "DSP-1",
                    ip_address="192.0.2.13",
                    device_kind="audio_dsp",
                    diagnostic_model="Biamp Tesira Forte CI",
                ),
            )
        )
        window = self.build_window(inv)

        for registration in EQUIPMENT_PAGE_REGISTRY:
            with self.subTest(screen=registration.screen_key):
                screen = window.screens[registration.screen_key]
                ip_count = 0
                port_count = 0
                for child in screen.findChildren(QFrame):
                    name_label = getattr(child, "name_label", None)
                    if name_label is not None:
                        if name_label.text() == SWITCH_IP_LABEL:
                            ip_count += 1
                        if name_label.text() == SWITCH_PORT_LABEL:
                            port_count += 1
                self.assertEqual(1, ip_count, registration.screen_key)
                self.assertEqual(1, port_count, registration.screen_key)
                self.assertTrue(screen.switch_ip_row.property("inventoryContextBoundary"))
                self.assertIs(screen.switch_ip_row.value_display.property("data_field"), False)
                self.assertTrue(screen.switch_port_row.property("inventoryContextBoundary"))
                if registration.screen_key == "pdu":
                    self.assertFalse(registration.shared_room_block)
                    self.assertTrue(registration.dedicated_pdu_room_placement)
                    self.assertTrue(set(registration.device_models).issubset(PDU_DEVICE_NAMES))
                    self.assertIsNone(getattr(screen, "shared_room_information_block", None))
                else:
                    self.assertTrue(registration.shared_room_block)
                    self.assertIsNotNone(screen.shared_room_information_block)

    def test_pdu_registration_keeps_dedicated_room_placement(self):
        registration = registrations_by_screen()["pdu"]
        self.assertFalse(registration.shared_room_block)
        self.assertTrue(registration.dedicated_pdu_room_placement)
        self.assertTrue(set(registration.device_models).issubset(PDU_DEVICE_NAMES))

    # --- Resolver outcomes (7.3) ---

    def test_resolver_full_partial_null_and_v1_v2(self):
        resolver = SwitchConnectionResolver()

        full = inventory(records=(_codec("C1", switch_ip_address="10.0.0.1", switch_port="Gi1/1"),))
        result = resolver.resolve_switch_connection(full, "192.0.2.10")
        self.assertIs(result.status, SwitchConnectionStatus.RESOLVED)
        self.assertEqual("10.0.0.1", result.switch_ip_address)
        self.assertEqual("Gi1/1", result.switch_port)

        ip_only = inventory(records=(_codec("C2", switch_ip_address="10.0.0.2"),))
        result = resolver.resolve_switch_connection(ip_only, "192.0.2.10")
        self.assertEqual("10.0.0.2", result.switch_ip_address)
        self.assertIsNone(result.switch_port)

        port_only = inventory(records=(_codec("C3", switch_port="Gi1/3"),))
        result = resolver.resolve_switch_connection(port_only, "192.0.2.10")
        self.assertIsNone(result.switch_ip_address)
        self.assertEqual("Gi1/3", result.switch_port)

        both_null = inventory(records=(_codec("C4"),))
        result = resolver.resolve_switch_connection(both_null, "192.0.2.10")
        self.assertIsNone(result.switch_ip_address)
        self.assertIsNone(result.switch_port)

        legacy = inventory(records=(_codec("C5"),), schema_version=2)
        result = resolver.resolve_switch_connection(legacy, "192.0.2.10")
        self.assertIsNone(result.switch_ip_address)
        self.assertIsNone(result.switch_port)

    def test_resolver_unavailable_invalid_not_found_ambiguous(self):
        resolver = SwitchConnectionResolver()
        self.assertIs(
            resolver.resolve_switch_connection(None, "192.0.2.10").status,
            SwitchConnectionStatus.INVENTORY_UNAVAILABLE,
        )
        inv = inventory(records=(_codec("C1"),))
        self.assertIs(
            resolver.resolve_switch_connection(inv, "not-an-ip").status,
            SwitchConnectionStatus.INVALID_IP,
        )
        self.assertIs(
            resolver.resolve_switch_connection(inv, "192.0.2.99").status,
            SwitchConnectionStatus.IP_NOT_FOUND,
        )
        ambiguous = inventory(
            records=(_codec("C2", switch_ip_address="10.0.0.2"), _codec("C3", switch_ip_address="10.0.0.3"))
        )
        result = resolver.resolve_switch_connection(ambiguous, "192.0.2.10")
        self.assertIs(result.status, SwitchConnectionStatus.AMBIGUOUS_IP)
        self.assertIsNone(result.switch_ip_address)
        self.assertIsNone(result.switch_port)

    def test_ambiguity_is_never_narrowed_by_model(self):
        resolver = SwitchConnectionResolver()
        ambiguous = inventory(
            records=(
                record(
                    "M-1",
                    ip_address="192.0.2.10",
                    device_kind="other",
                    diagnostic_model="Extron IN1804",
                    switch_ip_address="10.0.0.2",
                ),
                _codec("C-1", switch_ip_address="10.0.0.3"),
            )
        )
        result = resolver.resolve_switch_connection(ambiguous, "192.0.2.10")
        self.assertIs(result.status, SwitchConnectionStatus.AMBIGUOUS_IP)
        self.assertIsNone(result.switch_ip_address)
        self.assertIsNone(result.switch_port)

    # --- Request independence and device-payload protection (7.5) ---

    def test_publish_is_independent_of_request_and_survives_errors(self):
        inv = inventory(
            records=(_codec("C1", switch_ip_address="10.0.0.1", switch_port="Gi1/1"),)
        )
        window = self.build_window(inv)
        screen = window.screens["codec"]
        self._register(window, "Huawei TE20", "192.0.2.10")
        self.assertEqual("10.0.0.1", screen.switch_ip_row.value_display.text())

        window._publish_current_equipment_switch_context("request_started", force=True)
        self.assertEqual("10.0.0.1", screen.switch_ip_row.value_display.text())

        class Worker:
            device_name = "Huawei TE20"
            ip_address = "192.0.2.10"
            current_idx = 0
            creds_list = []

        with patch.object(QMessageBox, "critical"), patch.object(QMessageBox, "warning"):
            window.on_device_error(("connection_error", "synthetic failure", ""), Worker(), None)

        self.assertEqual("10.0.0.1", screen.switch_ip_row.value_display.text())
        self.assertEqual("Gi1/1", screen.switch_port_row.value_display.text())

    def test_device_payload_cannot_overwrite_switch_values(self):
        inv = inventory(
            records=(_codec("C1", switch_ip_address="10.0.0.1", switch_port="Gi1/1"),)
        )
        window = self.build_window(inv)
        screen = window.screens["codec"]
        self._register(window, "Huawei TE20", "192.0.2.10")
        self.assertEqual("10.0.0.1", screen.switch_ip_row.value_display.text())

        # A generic device result payload has no switch fields and screens have
        # no method to ingest them; switch rows are application-owned only.
        screen.update_data({"model": "Huawei TE20", "ip_address": "192.0.2.10"})
        screen.update_parameters_display()
        window._publish_current_equipment_switch_context("request_started", force=True)
        self.assertEqual("10.0.0.1", screen.switch_ip_row.value_display.text())
        self.assertEqual("Gi1/1", screen.switch_port_row.value_display.text())

    # --- Invalidation and stale-publication rejection (7.6) ---

    def _stale_publication_rejected_after_binding_change(self, change_binding):
        inv = inventory(
            records=(_codec("C1", switch_ip_address="10.0.0.1", switch_port="Gi1/1"),)
        )
        window = self.build_window(inv)
        screen = window.screens["codec"]
        self._register(window, "Huawei TE20", "192.0.2.10")
        self.assertEqual("10.0.0.1", screen.switch_ip_row.value_display.text())

        window._publish_current_equipment_switch_context("capture", force=True)
        stale_generation = window._equipment_switch_context_generation
        stale_binding = window._equipment_switch_context_binding

        change_binding(window)

        result = window.switch_connection_resolver.resolve_switch_connection(
            window.equipment_inventory, "192.0.2.10"
        )
        accepted = window._accept_equipment_switch_publication(
            stale_generation, stale_binding, result, reason="stale", device_name="Huawei TE20"
        )
        self.assertFalse(accepted)

    def test_stale_publication_rejected_after_model_change(self):
        inv = inventory(
            records=(
                _codec("C1", switch_ip_address="10.0.0.1", switch_port="Gi1/1"),
                record(
                    "MATRIX-1",
                    ip_address="192.0.2.11",
                    device_kind="other",
                    diagnostic_model="Extron IN1804",
                ),
            )
        )

        def change(window):
            window._accept_test_diagnostic_model("Extron IN1804")

        self._stale_publication_rejected_after_binding_change(change)

    def test_stale_publication_rejected_after_ip_change(self):
        inv = inventory(records=(_codec("C1", switch_ip_address="10.0.0.1", switch_port="Gi1/1"),))

        def change(window):
            window.ip_entry.setText("192.0.2.99")

        self._stale_publication_rejected_after_binding_change(change)

    def test_stale_publication_rejected_after_snapshot_change(self):
        inv = inventory(records=(_codec("C1", switch_ip_address="10.0.0.1", switch_port="Gi1/1"),))

        def change(window):
            err = EquipmentInventoryLoadError(InventoryLoadFailure.NOT_FOUND, "snapshot changed")
            window.replace_equipment_inventory_state(
                inventory=None, load_error=err, reason="snapshot_changed"
            )

        self._stale_publication_rejected_after_binding_change(change)

    def test_new_ip_republishes_new_value(self):
        inv = inventory(
            records=(
                record(
                    "C1",
                    ip_address="192.0.2.10",
                    device_kind="video_codec",
                    diagnostic_model="Huawei TE20",
                    switch_ip_address="10.0.0.1",
                ),
                record(
                    "C2",
                    ip_address="192.0.2.20",
                    device_kind="video_codec",
                    diagnostic_model="Huawei TE20",
                    switch_ip_address="10.0.0.2",
                    switch_port="Gi1/2",
                ),
            )
        )
        window = self.build_window(inv)
        screen = window.screens["codec"]
        self._register(window, "Huawei TE20", "192.0.2.20")
        self.assertEqual("10.0.0.2", screen.switch_ip_row.value_display.text())
        self.assertEqual("Gi1/2", screen.switch_port_row.value_display.text())

    # --- Codec rebuild and room-block ownership (7.7 - 7.14) ---

    def _build_codec_window(self, *, switch_ip="10.0.0.1", switch_port="Gi1/1", snapshot="sha256:" + "3" * 64):
        inv = inventory(
            snapshot_id=snapshot,
            records=(_codec("CODEC-1", switch_ip_address=switch_ip, switch_port=switch_port),),
        )
        return self.build_window(inv)

    def test_codec_rebuild_preserves_single_live_room_block_and_switch_pairs(self):
        window = self._build_codec_window()
        screen = window.screens["codec"]
        self._register(window, "Huawei TE20", "192.0.2.10")
        self.assertEqual("10.0.0.1", screen.switch_ip_row.value_display.text())

        pre_rebuild_block = screen.shared_room_information_block
        self.assertIsNotNone(pre_rebuild_block)
        self.assertEqual("Room One", pre_rebuild_block.room_name_value.text())

        for iteration in range(3):
            screen.update_parameters_display()
            window._publish_current_equipment_room_context("request_started", force=True)
            window._publish_current_equipment_switch_context("request_started", force=True)
            _flush_deferred(self.app)

            room_blocks = screen.findChildren(RoomInformationBlock)
            self.assertEqual(1, len(room_blocks), iteration)
            self.assertIs(room_blocks[0], screen.shared_room_information_block)
            self.assertIs(pre_rebuild_block, screen.shared_room_information_block)
            self.assertFalse(pre_rebuild_block.isHidden())
            self.assertEqual("Room One", pre_rebuild_block.room_name_value.text())

            layout = screen.param_layout
            block_index = None
            for i in range(layout.count()):
                if layout.itemAt(i).widget() is pre_rebuild_block:
                    block_index = i
                    break
            self.assertIsNotNone(block_index, iteration)
            if layout.count() > 1 and layout.itemAt(layout.count() - 1).spacerItem() is not None:
                self.assertEqual(layout.count() - 2, block_index, iteration)

            ip_count = 0
            port_count = 0
            for child in screen.findChildren(type(screen.switch_ip_row)):
                name_label = getattr(child, "name_label", None)
                if name_label is not None:
                    if name_label.text() == SWITCH_IP_LABEL:
                        ip_count += 1
                    if name_label.text() == SWITCH_PORT_LABEL:
                        port_count += 1
            self.assertEqual(1, ip_count, iteration)
            self.assertEqual(1, port_count, iteration)
            self.assertEqual("10.0.0.1", screen.switch_ip_row.value_display.text())

    def test_deleted_stale_codec_block_is_recovered_and_cannot_receive_publication(self):
        window = self._build_codec_window()
        screen = window.screens["codec"]
        self._register(window, "Huawei TE20", "192.0.2.10")

        stale_block = screen.shared_room_information_block
        self.assertIsNotNone(stale_block)
        stale_block.deleteLater()
        _flush_deferred(self.app)

        window._publish_current_equipment_room_context("request_started", force=True)
        window._publish_current_equipment_switch_context("request_started", force=True)

        self.assertIsNotNone(screen.shared_room_information_block)
        self.assertIsNot(screen.shared_room_information_block, stale_block)
        room_blocks = screen.findChildren(RoomInformationBlock)
        self.assertEqual(1, len(room_blocks))

    def test_codec_request_failure_does_not_clear_room_or_switch_presentation(self):
        window = self._build_codec_window()
        screen = window.screens["codec"]
        self._register(window, "Huawei TE20", "192.0.2.10")
        self.assertEqual("10.0.0.1", screen.switch_ip_row.value_display.text())

        class Worker:
            device_name = "Huawei TE20"
            ip_address = "192.0.2.10"
            current_idx = 0
            creds_list = []

        with patch.object(QMessageBox, "critical"), patch.object(QMessageBox, "warning"):
            window.on_device_error(("connection_error", "synthetic failure", ""), Worker(), None)

        _flush_deferred(self.app)
        self.assertEqual("10.0.0.1", screen.switch_ip_row.value_display.text())
        self.assertEqual("Gi1/1", screen.switch_port_row.value_display.text())
        self.assertEqual("Room One", screen.shared_room_information_block.room_name_value.text())


if __name__ == "__main__":
    unittest.main()
