import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtTest import QTest
    from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox
except Exception:  # pragma: no cover - environment without Qt
    QApplication = None
    QFileDialog = None
    QMessageBox = None
    QTest = None

from tests.test_equipment_inventory import network_row, source_row, write_network_xlsx, write_xlsx
from tools import import_equipment_inventory as importer
from tools.import_equipment_inventory import ConverterOperation, ConverterStage, ImportIssue, ImportResult

if QApplication is not None:
    from tools import inventory_converter_gui as converter_gui


def wait_for_idle(window, timeout_ms=5000):
    deadline = time.monotonic() + timeout_ms / 1000
    while window._active_thread is not None and time.monotonic() < deadline:
        QApplication.processEvents()
        QTest.qWait(10)
    QApplication.processEvents()
    if window._active_thread is not None:
        raise AssertionError("operation did not finish")


class CloseEventStub:
    def __init__(self):
        self.ignored = False

    def ignore(self):
        self.ignored = True


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class InventoryConverterGUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = converter_gui.InventoryConverterWindow()

    def tearDown(self):
        if self.window._active_thread is not None:
            wait_for_idle(self.window)
        self.window.close()
        QApplication.processEvents()

    def _write_sources(self, directory):
        source = Path(directory) / "inventory.xlsx"
        network = Path(directory) / "network.xlsx"
        write_xlsx(
            source,
            [
                source_row(
                    "RID-1",
                    source_model="Huawei TE20",
                    ip="192.0.2.10",
                    mac="00:11:22:33:44:01",
                    serial="SER-1",
                    manufacturer="Huawei",
                    model="TE20",
                    controller=None,
                )
            ],
        )
        write_network_xlsx(network, [network_row("00-11-22-33-44-01")])
        return source, network

    def _assert_report_exportable(self, operation):
        self.assertEqual(operation, self.window._current_report.operation)
        self.assertEqual(operation, self.window.summary_labels["operation"].text())
        self.assertTrue(self.window.save_report_button.isEnabled())
        with tempfile.TemporaryDirectory() as directory:
            export_path = Path(directory) / "report.json"
            with patch.object(QFileDialog, "getSaveFileName", return_value=(str(export_path), "JSON files (*.json)")):
                self.window.save_report()
            self.assertEqual(operation, json.loads(export_path.read_text(encoding="utf-8"))["operation"])
            self.assertTrue(export_path.read_text(encoding="utf-8").endswith("\n"))

    def test_initial_states_path_reset_and_stale_transition(self):
        self.assertEqual("NOT_TESTED", self.window.primary_state_label.text())
        self.assertEqual("NOT_TESTED", self.window.network_state_label.text())
        self.assertFalse(self.window.save_report_button.isEnabled())

        with tempfile.TemporaryDirectory() as directory:
            source, _network = self._write_sources(directory)
            self.window.primary_edit.setText(str(source))
            self.window.run_primary_test()
            wait_for_idle(self.window)
            self.assertEqual("PASSED", self.window.primary_state_label.text())

            self.window.primary_edit.setText(str(Path(directory) / "other.xlsx"))
            self.window.primary_edit.textEdited.emit(self.window.primary_edit.text())
            self.assertEqual("NOT_TESTED", self.window.primary_state_label.text())

            self.window.primary_edit.setText(str(source))
            self.window.run_primary_test()
            wait_for_idle(self.window)
            write_xlsx(source, [source_row("RID-2", controller=None)])
            self.window._mark_stale_if_needed()
            self.assertEqual("STALE", self.window.primary_state_label.text())

    def test_independent_tests_check_all_without_output_and_conversion(self):
        with tempfile.TemporaryDirectory() as directory:
            source, network = self._write_sources(directory)
            output = Path(directory) / "snapshot.json"
            self.window.primary_edit.setText(str(source))
            self.window.network_edit.setText(str(network))

            self.window.run_primary_test()
            wait_for_idle(self.window)
            self.window.run_network_test()
            wait_for_idle(self.window)
            self.assertEqual("PASSED", self.window.primary_state_label.text())
            self.assertEqual("PASSED", self.window.network_state_label.text())

            self.window.run_combined_preflight()
            wait_for_idle(self.window)
            self.assertEqual(ConverterOperation.COMBINED_PREFLIGHT.value, self.window._current_report.operation)
            self.assertFalse(output.exists())
            self.assertIsNone(self.window._current_report.output_path)

            self.window.output_edit.setText(str(output))
            self.window.run_conversion()
            wait_for_idle(self.window)
            self.assertTrue(self.window._current_report.published)
            self.assertTrue(output.exists())
            self.assertEqual(ConverterOperation.CONVERSION.value, self.window.summary_labels["operation"].text())

    def test_serialized_operation_disables_controls_and_close_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            source, _network = self._write_sources(directory)

            def slow_primary():
                time.sleep(0.2)
                return importer.preflight_primary_source(source)

            self.window._start_operation(ConverterOperation.PRIMARY_SOURCE_PREFLIGHT.value, slow_primary)
            QApplication.processEvents()
            self.assertFalse(self.window.primary_edit.isEnabled())
            self.assertFalse(self.window.convert_button.isEnabled())

            event = CloseEventStub()
            with patch.object(QMessageBox, "warning") as warning:
                self.window.closeEvent(event)
            self.assertTrue(event.ignored)
            warning.assert_called_once()
            wait_for_idle(self.window)
            self.assertTrue(self.window.primary_edit.isEnabled())

    def test_overwrite_decline_and_guarded_output_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            source, network = self._write_sources(directory)
            output = Path(directory) / "snapshot.json"
            output.write_text("previous-output", encoding="utf-8")
            self.window.primary_edit.setText(str(source))
            self.window.network_edit.setText(str(network))
            self.window.output_edit.setText(str(output))

            with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
                self.window.run_conversion()
            self.assertIsNone(self.window._active_thread)
            self.assertEqual("previous-output", output.read_text(encoding="utf-8"))

            output.unlink()
            real_import = importer.import_equipment_inventory

            def racing_import(source_path, **kwargs):
                Path(kwargs["output_path"]).write_text("raced-output", encoding="utf-8")
                return real_import(source_path, **kwargs)

            with patch.object(converter_gui, "import_equipment_inventory", side_effect=racing_import):
                self.window.run_conversion()
                wait_for_idle(self.window)

            self.assertFalse(self.window._current_report.published)
            self.assertEqual(("OUTPUT_CHANGED_SINCE_CONFIRMATION",), tuple(issue.code for issue in self.window._current_report.fatal_issues))
            self.assertEqual("raced-output", output.read_text(encoding="utf-8"))

    def test_source_failure_and_overwrite_acceptance_render_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            bad_source = Path(directory) / "bad-source.xlsx"
            bad_source.write_text("not a workbook", encoding="utf-8")
            self.window.primary_edit.setText(str(bad_source))

            self.window.run_primary_test()
            wait_for_idle(self.window)
            self.assertEqual("FAILED", self.window._current_report.status)
            self.assertEqual("FAILED", self.window.primary_state_label.text())
            self.assertTrue(self.window.save_report_button.isEnabled())

            source, network = self._write_sources(directory)
            output = Path(directory) / "snapshot.json"
            output.write_text("previous-output", encoding="utf-8")
            self.window.primary_edit.setText(str(source))
            self.window.network_edit.setText(str(network))
            self.window.output_edit.setText(str(output))

            with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
                self.window.run_conversion()
                wait_for_idle(self.window)

            self.assertTrue(self.window._current_report.published)
            self.assertNotEqual("previous-output", output.read_text(encoding="utf-8"))
            self.assertEqual(ConverterOperation.CONVERSION.value, self.window.summary_labels["operation"].text())

    def test_worker_exception_preserves_operation_context_and_unlocks(self):
        with tempfile.TemporaryDirectory() as directory:
            source, network = self._write_sources(directory)
            output = Path(directory) / "snapshot.json"
            self.window.primary_edit.setText(str(source))
            self.window.network_edit.setText(str(network))
            self.window.output_edit.setText(str(output))

            scenarios = (
                (
                    ConverterOperation.PRIMARY_SOURCE_PREFLIGHT.value,
                    "preflight_primary_source",
                    self.window.run_primary_test,
                    self.window.primary_state_label,
                ),
                (
                    ConverterOperation.NETWORK_SOURCE_PREFLIGHT.value,
                    "preflight_network_source",
                    self.window.run_network_test,
                    self.window.network_state_label,
                ),
                (
                    ConverterOperation.COMBINED_PREFLIGHT.value,
                    "preflight_combined_sources",
                    self.window.run_combined_preflight,
                    None,
                ),
                (
                    ConverterOperation.CONVERSION.value,
                    "import_equipment_inventory",
                    self.window.run_conversion,
                    None,
                ),
            )
            for operation, function_name, runner, source_state_label in scenarios:
                with self.subTest(operation=operation):
                    self.window._current_report = None
                    self.window._set_running(False)
                    with patch.object(converter_gui, function_name, side_effect=RuntimeError("boom")):
                        runner()
                        wait_for_idle(self.window)
                    self.assertEqual("FAILED", self.window._current_report.status)
                    self.assertEqual(("INTERNAL_ERROR",), tuple(issue.code for issue in self.window._current_report.fatal_issues))
                    self.assertEqual(ConverterStage.INTERNAL.value, self.window._current_report.fatal_issues[0].stage)
                    if source_state_label is not None:
                        self.assertEqual("FAILED", source_state_label.text())
                    self.assertTrue(self.window.primary_edit.isEnabled())
                    self.assertTrue(self.window.convert_button.isEnabled())
                    self.assertIsNone(self.window._active_thread)
                    self.assertIsNone(self.window._active_worker)
                    self._assert_report_exportable(operation)

    def test_source_preflight_changes_during_operation_mark_state_stale(self):
        with tempfile.TemporaryDirectory() as directory:
            source, network = self._write_sources(directory)
            self.window.primary_edit.setText(str(source))
            self.window.network_edit.setText(str(network))

            real_primary_preflight = importer.preflight_primary_source

            def changing_primary(path):
                result = real_primary_preflight(path)
                write_xlsx(Path(path), [source_row("RID-2", mac="00:11:22:33:44:02", controller=None)])
                return result

            with patch.object(converter_gui, "preflight_primary_source", side_effect=changing_primary):
                self.window.run_primary_test()
                wait_for_idle(self.window)
            self.assertEqual("SUCCEEDED", self.window._current_report.status)
            self.assertEqual("STALE", self.window.primary_state_label.text())
            self.assertTrue(self.window.save_report_button.isEnabled())

            real_network_preflight = importer.preflight_network_source

            def changing_network(path):
                result = real_network_preflight(path)
                write_network_xlsx(Path(path), [network_row("00-11-22-33-44-02")])
                return result

            with patch.object(converter_gui, "preflight_network_source", side_effect=changing_network):
                self.window.run_network_test()
                wait_for_idle(self.window)
            self.assertEqual("SUCCEEDED", self.window._current_report.status)
            self.assertEqual("STALE", self.window.network_state_label.text())
            self.assertTrue(self.window.save_report_button.isEnabled())

    def test_unchanged_source_preflight_maps_success_and_warning_states(self):
        with tempfile.TemporaryDirectory() as directory:
            source, network = self._write_sources(directory)
            self.window.primary_edit.setText(str(source))
            self.window.network_edit.setText(str(network))

            self.window.run_primary_test()
            wait_for_idle(self.window)
            self.assertEqual("PASSED", self.window.primary_state_label.text())

            warning_source = Path(directory) / "warning-inventory.xlsx"
            write_xlsx(
                warning_source,
                [
                    source_row(
                        "RID-WARN",
                        ip="not-an-ip",
                        mac="00:11:22:33:44:09",
                        controller=None,
                    )
                ],
            )
            self.window.primary_edit.setText(str(warning_source))
            self.window.primary_edit.textEdited.emit(self.window.primary_edit.text())
            self.window.run_primary_test()
            wait_for_idle(self.window)
            self.assertEqual("SUCCEEDED_WITH_WARNINGS", self.window._current_report.status)
            self.assertEqual("PASSED_WITH_WARNINGS", self.window.primary_state_label.text())

            self.window.run_network_test()
            wait_for_idle(self.window)
            self.assertEqual("PASSED", self.window.network_state_label.text())

    def test_network_reconciliation_counters_are_rendered_from_report(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "inventory.xlsx"
            network = Path(directory) / "network.xlsx"
            write_xlsx(
                source,
                [
                    source_row("RID-1", mac="00:11:22:33:44:01", controller=None),
                    source_row("RID-2", mac="00:11:22:33:44:02", controller=None),
                    source_row("RID-3", mac="00:11:22:33:44:03", controller=None),
                ],
            )
            write_network_xlsx(
                network,
                [
                    network_row("00-11-22-33-44-01", switch_ip="198.51.100.1", port="Gi1/0/1"),
                    network_row("00-11-22-33-44-01", switch_ip="198.51.100.1", port="Gi1/0/1"),
                    network_row("00-11-22-33-44-02", switch_ip=None, port=None),
                    network_row("00-11-22-33-44-03", switch_ip="198.51.100.3", port="Gi1/0/3"),
                    network_row("00-11-22-33-44-03", switch_ip="198.51.100.33", port="Gi1/0/33"),
                    network_row("00-11-22-33-44-99", switch_ip="198.51.100.99", port="Gi1/0/99"),
                ],
            )
            self.window.primary_edit.setText(str(source))
            self.window.network_edit.setText(str(network))

            self.window.run_combined_preflight()
            wait_for_idle(self.window)

        self.assertEqual("4", self.window.summary_labels["distinct_network_mac_count"].text())
        self.assertEqual("1", self.window.summary_labels["enriched_record_count"].text())
        self.assertEqual("1", self.window.summary_labels["empty_connection_row_count"].text())
        self.assertEqual("1", self.window.summary_labels["duplicate_connection_count"].text())
        self.assertEqual("1", self.window.summary_labels["ambiguity_count"].text())
        self.assertEqual("1", self.window.summary_labels["unmatched_network_mac_count"].text())

    def test_report_fatal_first_filter_details_and_complete_export(self):
        report = ImportResult(
            published=False,
            output_path=Path("out.json"),
            worksheet="Synthetic",
            header_row=1,
            source_row_count=2,
            record_count=0,
            snapshot_id=None,
            issues=(
                ImportIssue("consistency", "WARN_CODE", description="warning", details={"safe": "value"}),
                ImportIssue("fatal", "FATAL_CODE", description="fatal", stage=ConverterStage.PUBLICATION.value, details={"why": "blocked"}),
            ),
            operation=ConverterOperation.CONVERSION.value,
            stage_reached=ConverterStage.PUBLICATION.value,
        )
        self.window._operation_finished(report)

        self.assertEqual("FATAL_CODE", self.window.issue_table.item(0, 2).text())
        self.window.issue_table.selectRow(0)
        self.window._render_selected_issue_details()
        self.assertIn("blocked", self.window.details_view.toPlainText())

        self.window.issue_filter.setCurrentText("consistency")
        self.assertEqual(1, self.window.issue_table.rowCount())
        self.assertEqual("WARN_CODE", self.window.issue_table.item(0, 2).text())

        with tempfile.TemporaryDirectory() as directory:
            export_path = Path(directory) / "report.json"
            with patch.object(QFileDialog, "getSaveFileName", return_value=(str(export_path), "JSON files (*.json)")):
                self.window.save_report()
            exported = json.loads(export_path.read_text(encoding="utf-8"))
            self.assertEqual(2, len(exported["issues"]))
            self.assertTrue(export_path.read_text(encoding="utf-8").endswith("\n"))

    def test_importer_and_main_application_do_not_import_converter_gui(self):
        script = (
            "import sys\n"
            "import tools.import_equipment_inventory\n"
            "import core.equipment_inventory\n"
            "print('tools.inventory_converter_gui' in sys.modules)\n"
            "print('PyQt5' in sys.modules)\n"
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(["False", "False"], completed.stdout.splitlines())


if __name__ == "__main__":
    unittest.main()
