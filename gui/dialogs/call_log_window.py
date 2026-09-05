from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QHeaderView, QLabel, QTableWidget, QTableWidgetItem,
    QToolButton, QVBoxLayout,
)

from core.codec_call_history import (
    CallDirection, CallHistorySnapshot, CallRecord, calculate_usage, snapshot_from_display_records,
    usage_warnings,
)


class CallLogWindow(QDialog):
    """Read-only presentation of a normalized codec call-history snapshot."""

    MAX_ROWS = 20
    PREVIEW_ROWS = 2
    HEADERS = (
        "Номер комнаты", "Дата и время начала звонка", "Продолжительность звонка", "Скорость", "Направление",
    )

    def __init__(self, parent=None, colors=None):
        super().__init__(parent)
        self.colors = colors or getattr(parent, "colors", None)
        self.setWindowTitle("Журнал звонков")
        self.resize(760, 560)
        self.status_label = QLabel("Данные журнала звонков не загружены.", self)
        self.preview_table = self._table()
        self.usage_label = QLabel("", self)
        self.journal_toggle = QToolButton(self)
        self.journal_toggle.setText("Журнал звонков")
        self.journal_toggle.setCheckable(True)
        self.journal_toggle.setArrowType(Qt.RightArrow)
        self.table = self._table()  # Kept public for existing dialog consumers.
        self.table.setVisible(False)
        self.journal_toggle.toggled.connect(self._toggle_journal)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(self.status_label)
        layout.addWidget(self.preview_table)
        layout.addWidget(self.usage_label)
        layout.addWidget(self.journal_toggle)
        layout.addWidget(self.table, 1)
        self.apply_theme()

    def _table(self):
        table = QTableWidget(0, len(self.HEADERS), self)
        table.setHorizontalHeaderLabels(self.HEADERS)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        return table

    def apply_theme(self):
        if not self.colors:
            return
        self.setStyleSheet(f"""
            QDialog {{ background-color: {self.colors['background']}; color: {self.colors['text_primary']}; }}
            QLabel {{ color: {self.colors['text_secondary']}; }}
            QTableWidget {{ background-color: {self.colors['surface']}; color: {self.colors['text_primary']}; gridline-color: {self.colors['divider']}; border: 1px solid {self.colors['divider']}; border-radius: 6px; }}
            QHeaderView::section {{ background-color: {self.colors['surface']}; color: {self.colors['text_primary']}; border: 1px solid {self.colors['divider']}; padding: 6px; }}
        """)

    def _toggle_journal(self, expanded):
        self.table.setVisible(expanded)
        self.journal_toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)

    def set_snapshot(self, snapshot):
        if not isinstance(snapshot, CallHistorySnapshot):
            self.set_call_records(snapshot or [])
            return
        records = list(snapshot.records)
        self._fill(self.preview_table, records[:self.PREVIEW_ROWS])
        self._fill(self.table, records[:self.MAX_ROWS])
        rows = calculate_usage(snapshot)
        rendered_rows = []
        for row in rows:
            percentage = "н/д" if row.percentage is None else f"{row.percentage}%"
            suffix = " (неполные данные)" if not row.complete else ""
            rendered_rows.append(f"{row.days} дней: {row.hours:.1f} ч, {percentage}{suffix}")
        self.usage_label.setText("\n".join(rendered_rows))
        warnings = " ".join((*snapshot.warnings, *usage_warnings(rows)))
        if records:
            self.status_label.setText(warnings or f"Показаны последние {min(len(records), self.MAX_ROWS)} звонков.")
        else:
            self.status_label.setText(warnings or "Журнал звонков пуст.")

    def set_call_records(self, records):
        """Compatibility boundary for legacy handler tests and callers."""
        self.set_snapshot(snapshot_from_display_records(records or []))

    def clear_records(self):
        self.journal_toggle.setChecked(False)
        self._fill(self.preview_table, [])
        self._fill(self.table, [])
        self.usage_label.setText("")
        self.status_label.setText("Данные журнала звонков не загружены.")

    def _fill(self, table, records):
        table.setRowCount(len(records))
        for row, record in enumerate(records):
            room, start, duration, speed, direction = self.normalize_record(record, row)
            for column, value in enumerate((room, start, duration, speed, direction)):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, column, item)

    def normalize_record(self, record, row):
        if isinstance(record, CallRecord):
            return record.room_number, record.start_display, record.duration_display, record.speed, self._direction_text(record.direction)
        if isinstance(record, dict):
            return (record.get("room_number", record.get("call_number", "")), record.get("start_time", ""), record.get("duration", ""), record.get("speed", ""), self._direction_text(record.get("direction")))
        if isinstance(record, (list, tuple)):
            values = list(record) + [""] * 5
            return tuple(values[:5])
        return "", "", "", "", "Направление неизвестно"

    @staticmethod
    def _direction_text(direction) -> str:
        if direction is CallDirection.INCOMING:
            return "Входящий"
        if direction is CallDirection.OUTGOING:
            return "Исходящий"
        return "Направление неизвестно"
