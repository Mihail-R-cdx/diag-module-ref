"""Standalone PyQt5 operator GUI for equipment inventory conversion."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from PyQt5.QtCore import QObject, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from tools.import_equipment_inventory import (
    ConverterOperation,
    ConverterStage,
    ImportIssue,
    ImportResult,
    SourceFileRole,
    capture_output_precondition,
    import_equipment_inventory,
    preflight_combined_sources,
    preflight_network_source,
    preflight_primary_source,
)


SOURCE_STATES = {
    "NOT_TESTED",
    "RUNNING",
    "PASSED",
    "PASSED_WITH_WARNINGS",
    "FAILED",
    "STALE",
}
STATUS_TO_SOURCE_STATE = {
    "SUCCEEDED": "PASSED",
    "SUCCEEDED_WITH_WARNINGS": "PASSED_WITH_WARNINGS",
    "FAILED": "FAILED",
}
ISSUE_COLUMNS = (
    "class",
    "stage",
    "code",
    "source_file_role",
    "sheet",
    "row",
    "source_column",
    "record_id",
    "description",
)


@dataclass(frozen=True)
class SourceFingerprint:
    path: str
    size: int
    mtime_ns: int


class InventoryOperationWorker(QObject):
    finished = pyqtSignal(object)

    def __init__(self, callback: Callable[[], ImportResult]):
        super().__init__()
        self._callback = callback

    @pyqtSlot()
    def run(self) -> None:
        try:
            result = self._callback()
        except Exception as exc:  # pragma: no cover - defensive GUI boundary
            result = ImportResult(
                published=False,
                output_path=None,
                worksheet=None,
                header_row=None,
                source_row_count=0,
                record_count=0,
                snapshot_id=None,
                issues=(
                    ImportIssue(
                        "fatal",
                        "INTERNAL_ERROR",
                        description=f"Unexpected converter error: {type(exc).__name__}",
                        stage=ConverterStage.INTERNAL.value,
                    ),
                ),
                operation=ConverterOperation.CONVERSION.value,
                stage_reached=ConverterStage.INTERNAL.value,
            )
        self.finished.emit(result)


class InventoryConverterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inventory Converter")
        self._primary_state = "NOT_TESTED"
        self._network_state = "NOT_TESTED"
        self._primary_fingerprint: SourceFingerprint | None = None
        self._network_fingerprint: SourceFingerprint | None = None
        self._current_report: ImportResult | None = None
        self._active_thread: QThread | None = None
        self._active_worker: InventoryOperationWorker | None = None
        self._build_ui()
        self._set_running(False)
        self._update_source_labels()

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        paths = QGroupBox("Paths", self)
        grid = QGridLayout(paths)
        self.primary_edit = QLineEdit(paths)
        self.network_edit = QLineEdit(paths)
        self.output_edit = QLineEdit(paths)
        self.primary_browse_button = QPushButton("Browse", paths)
        self.network_browse_button = QPushButton("Browse", paths)
        self.output_browse_button = QPushButton("Browse", paths)
        self.primary_test_button = QPushButton("Test", paths)
        self.network_test_button = QPushButton("Test", paths)
        self.primary_state_label = QLabel(paths)
        self.network_state_label = QLabel(paths)

        grid.addWidget(QLabel("Primary workbook", paths), 0, 0)
        grid.addWidget(self.primary_edit, 0, 1)
        grid.addWidget(self.primary_browse_button, 0, 2)
        grid.addWidget(self.primary_test_button, 0, 3)
        grid.addWidget(self.primary_state_label, 0, 4)
        grid.addWidget(QLabel("Network workbook", paths), 1, 0)
        grid.addWidget(self.network_edit, 1, 1)
        grid.addWidget(self.network_browse_button, 1, 2)
        grid.addWidget(self.network_test_button, 1, 3)
        grid.addWidget(self.network_state_label, 1, 4)
        grid.addWidget(QLabel("Output JSON", paths), 2, 0)
        grid.addWidget(self.output_edit, 2, 1)
        grid.addWidget(self.output_browse_button, 2, 2)

        actions = QHBoxLayout()
        self.check_all_button = QPushButton("Check all", self)
        self.convert_button = QPushButton("Convert", self)
        self.save_report_button = QPushButton("Save report", self)
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 0)
        self.status_label = QLabel("", self)
        actions.addWidget(self.check_all_button)
        actions.addWidget(self.convert_button)
        actions.addWidget(self.save_report_button)
        actions.addWidget(self.progress)
        actions.addWidget(self.status_label, 1)

        summary_box = QGroupBox("Summary", self)
        summary = QFormLayout(summary_box)
        self.summary_labels: dict[str, QLabel] = {}
        for key in (
            "operation",
            "status",
            "published",
            "output_path",
            "stage_reached",
            "schema_version",
            "source_row_count",
            "network_source_row_count",
            "record_count",
            "snapshot_id",
            "enriched_record_count",
            "fatal_issue_count",
            "data_quality_issue_count",
            "consistency_issue_count",
        ):
            label = QLabel("", summary_box)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.summary_labels[key] = label
            summary.addRow(key, label)

        issue_controls = QHBoxLayout()
        self.issue_filter = QComboBox(self)
        self.issue_filter.addItems(["all", "fatal", "data_quality", "consistency"])
        issue_controls.addWidget(QLabel("Issue class", self))
        issue_controls.addWidget(self.issue_filter)
        issue_controls.addStretch(1)

        self.issue_table = QTableWidget(0, len(ISSUE_COLUMNS), self)
        self.issue_table.setHorizontalHeaderLabels(ISSUE_COLUMNS)
        self.issue_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.issue_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.issue_table.setSelectionMode(QTableWidget.SingleSelection)
        self.details_view = QPlainTextEdit(self)
        self.details_view.setReadOnly(True)
        self.details_view.setMaximumBlockCount(1000)

        root.addWidget(paths)
        root.addLayout(actions)
        root.addWidget(summary_box)
        root.addLayout(issue_controls)
        root.addWidget(self.issue_table, 1)
        root.addWidget(self.details_view)

        self.primary_edit.textEdited.connect(lambda _text: self._reset_source_state("primary"))
        self.network_edit.textEdited.connect(lambda _text: self._reset_source_state("network"))
        self.primary_browse_button.clicked.connect(lambda: self._browse_input(self.primary_edit, "Primary workbook"))
        self.network_browse_button.clicked.connect(lambda: self._browse_input(self.network_edit, "Network workbook"))
        self.output_browse_button.clicked.connect(self._browse_output)
        self.primary_test_button.clicked.connect(self.run_primary_test)
        self.network_test_button.clicked.connect(self.run_network_test)
        self.check_all_button.clicked.connect(self.run_combined_preflight)
        self.convert_button.clicked.connect(self.run_conversion)
        self.save_report_button.clicked.connect(self.save_report)
        self.issue_filter.currentTextChanged.connect(lambda _text: self._render_issues())
        self.issue_table.itemSelectionChanged.connect(self._render_selected_issue_details)

    def _browse_input(self, edit: QLineEdit, title: str) -> None:
        path, _filter = QFileDialog.getOpenFileName(self, title, "", "Excel workbooks (*.xlsx)")
        if path:
            edit.setText(path)
            if edit is self.primary_edit:
                self._reset_source_state("primary")
            else:
                self._reset_source_state("network")

    def _browse_output(self) -> None:
        path, _filter = QFileDialog.getSaveFileName(self, "Output JSON", "", "JSON files (*.json)")
        if path:
            self.output_edit.setText(path)

    def _reset_source_state(self, role: str) -> None:
        if role == "primary":
            self._primary_state = "NOT_TESTED"
            self._primary_fingerprint = None
        else:
            self._network_state = "NOT_TESTED"
            self._network_fingerprint = None
        self._update_source_labels()

    def _update_source_labels(self) -> None:
        self.primary_state_label.setText(self._primary_state)
        self.network_state_label.setText(self._network_state)

    def _current_fingerprint(self, path_text: str) -> SourceFingerprint | None:
        if not path_text.strip():
            return None
        path = Path(path_text).expanduser().resolve(strict=False)
        try:
            stat = path.stat()
        except OSError:
            return None
        return SourceFingerprint(str(path), stat.st_size, stat.st_mtime_ns)

    def _mark_stale_if_needed(self) -> None:
        if self._primary_fingerprint is not None:
            current = self._current_fingerprint(self.primary_edit.text())
            if current != self._primary_fingerprint:
                self._primary_state = "STALE"
        if self._network_fingerprint is not None:
            current = self._current_fingerprint(self.network_edit.text())
            if current != self._network_fingerprint:
                self._network_state = "STALE"
        self._update_source_labels()

    def run_primary_test(self) -> None:
        path = self.primary_edit.text().strip()
        if not path:
            self._show_configuration_failure(ConverterOperation.PRIMARY_SOURCE_PREFLIGHT.value, "Primary workbook path is required.")
            return
        self._primary_state = "RUNNING"
        self._update_source_labels()
        self._start_operation(lambda: preflight_primary_source(path))

    def run_network_test(self) -> None:
        path = self.network_edit.text().strip()
        if not path:
            self._show_configuration_failure(ConverterOperation.NETWORK_SOURCE_PREFLIGHT.value, "Network workbook path is required.")
            return
        self._network_state = "RUNNING"
        self._update_source_labels()
        self._start_operation(lambda: preflight_network_source(path))

    def run_combined_preflight(self) -> None:
        self._mark_stale_if_needed()
        primary = self.primary_edit.text().strip()
        network = self.network_edit.text().strip()
        if not primary or not network:
            self._show_configuration_failure(ConverterOperation.COMBINED_PREFLIGHT.value, "Primary and network workbook paths are required.")
            return
        self._start_operation(lambda: preflight_combined_sources(primary, network))

    def run_conversion(self) -> None:
        self._mark_stale_if_needed()
        primary = self.primary_edit.text().strip()
        network = self.network_edit.text().strip()
        output = self.output_edit.text().strip()
        if not primary or not network or not output:
            self._show_configuration_failure(ConverterOperation.CONVERSION.value, "Primary, network, and output paths are required.")
            return
        precondition = capture_output_precondition(output)
        if precondition.confirmed_state.exists:
            answer = QMessageBox.question(
                self,
                "Replace output",
                f"Replace existing output?\n\n{precondition.output_path}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        self._start_operation(
            lambda: import_equipment_inventory(
                primary,
                network_source_path=network,
                output_path=output,
                publication_precondition=precondition,
            )
        )

    def _show_configuration_failure(self, operation: str, description: str) -> None:
        result = ImportResult(
            published=False,
            output_path=Path(self.output_edit.text()).expanduser().resolve(strict=False) if self.output_edit.text().strip() else None,
            worksheet=None,
            header_row=None,
            source_row_count=0,
            record_count=0,
            snapshot_id=None,
            issues=(
                ImportIssue(
                    "fatal",
                    "GUI_CONFIGURATION_MISSING",
                    description=description,
                    stage=ConverterStage.CONFIGURATION.value,
                ),
            ),
            operation=operation,
            stage_reached=ConverterStage.CONFIGURATION.value,
            primary_source_path=Path(self.primary_edit.text()).expanduser().resolve(strict=False) if self.primary_edit.text().strip() else None,
            network_source_path=Path(self.network_edit.text()).expanduser().resolve(strict=False) if self.network_edit.text().strip() else None,
        )
        self._operation_finished(result)

    def _start_operation(self, callback: Callable[[], ImportResult]) -> None:
        if self._active_thread is not None:
            return
        self._set_running(True)
        self.status_label.setText("RUNNING")
        thread = QThread(self)
        worker = InventoryOperationWorker(callback)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._operation_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self._operation_thread_finished)
        thread.start()
        self._active_thread = thread
        self._active_worker = worker

    @pyqtSlot()
    def _operation_thread_finished(self) -> None:
        thread = self.sender()
        if thread is not None:
            thread.deleteLater()
        self._active_thread = None
        self._active_worker = None

    @pyqtSlot(object)
    def _operation_finished(self, result: ImportResult) -> None:
        self._current_report = result
        self.status_label.setText(result.status)
        self._set_running(False)
        if result.operation == ConverterOperation.PRIMARY_SOURCE_PREFLIGHT.value:
            self._primary_state = STATUS_TO_SOURCE_STATE[result.status]
            self._primary_fingerprint = self._current_fingerprint(self.primary_edit.text())
        elif result.operation == ConverterOperation.NETWORK_SOURCE_PREFLIGHT.value:
            self._network_state = STATUS_TO_SOURCE_STATE[result.status]
            self._network_fingerprint = self._current_fingerprint(self.network_edit.text())
        self._update_source_labels()
        self._render_report(result)

    def _set_running(self, running: bool) -> None:
        for widget in (
            self.primary_edit,
            self.network_edit,
            self.output_edit,
            self.primary_browse_button,
            self.network_browse_button,
            self.output_browse_button,
            self.primary_test_button,
            self.network_test_button,
            self.check_all_button,
            self.convert_button,
            self.save_report_button,
        ):
            widget.setEnabled(not running)
        self.progress.setVisible(running)
        self.save_report_button.setEnabled(not running and self._current_report is not None)

    def _render_report(self, result: ImportResult) -> None:
        report = result.to_report()
        for key, label in self.summary_labels.items():
            value = report.get(key)
            label.setText("" if value is None else str(value))
        self._render_issues()

    def _render_issues(self) -> None:
        self.issue_table.setRowCount(0)
        self.details_view.clear()
        if self._current_report is None:
            return
        selected_class = self.issue_filter.currentText()
        issues = list(self._current_report.to_report()["issues"])
        if selected_class != "all":
            issues = [issue for issue in issues if issue["class"] == selected_class]
        issues.sort(key=lambda issue: 0 if issue["class"] == "fatal" else 1)
        for row, issue in enumerate(issues):
            self.issue_table.insertRow(row)
            for column, key in enumerate(ISSUE_COLUMNS):
                value = issue.get(key)
                item = QTableWidgetItem("" if value is None else str(value))
                item.setData(Qt.UserRole, issue)
                self.issue_table.setItem(row, column, item)
        self.issue_table.resizeColumnsToContents()

    def _render_selected_issue_details(self) -> None:
        selected = self.issue_table.selectedItems()
        if not selected:
            self.details_view.clear()
            return
        issue = selected[0].data(Qt.UserRole)
        self.details_view.setPlainText(json.dumps(issue.get("details", {}), ensure_ascii=False, indent=2, sort_keys=True))

    def save_report(self) -> None:
        if self._current_report is None:
            return
        path, _filter = QFileDialog.getSaveFileName(self, "Save report", "", "JSON files (*.json)")
        if not path:
            return
        payload = json.dumps(self._current_report.to_report(), ensure_ascii=False, indent=2, sort_keys=True)
        Path(path).write_text(payload + "\n", encoding="utf-8", newline="\n")

    def closeEvent(self, event) -> None:
        if self._active_thread is not None:
            QMessageBox.warning(self, "Operation running", "Wait for the current operation to finish.")
            event.ignore()
            return
        super().closeEvent(event)


def main(argv: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv if argv is None else argv)
    app.setStyle("Fusion")
    window = InventoryConverterWindow()
    window.resize(1100, 760)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
