from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class CallLogWindow(QDialog):
    """Window for displaying the last codec call records."""

    MAX_ROWS = 10
    HEADERS = (
        "Номер комнаты",
        "Дата и время начала звонка",
        "Продолжительность звонка",
        "Скорость",
    )

    def __init__(self, parent=None, colors=None):
        super().__init__(parent)
        self.colors = colors or getattr(parent, "colors", None)
        self.setWindowTitle("Журнал звонков")
        self.resize(720, 420)

        self.status_label = QLabel("Данные журнала звонков не загружены.", self)
        self.table = QTableWidget(0, len(self.HEADERS), self)
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, 1)

        self.apply_theme()

    def apply_theme(self):
        if not self.colors:
            return

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colors['background']};
                color: {self.colors['text_primary']};
            }}
            QLabel {{
                color: {self.colors['text_secondary']};
            }}
            QTableWidget {{
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
                gridline-color: {self.colors['divider']};
                border: 1px solid {self.colors['divider']};
                border-radius: 6px;
                selection-background-color: {self.colors['primary_variant']};
            }}
            QHeaderView::section {{
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['divider']};
                padding: 6px;
            }}
        """)

    def set_call_records(self, records):
        """Fill the table with up to ten latest call records."""
        visible_records = list(records or [])[:self.MAX_ROWS]
        self.table.setRowCount(len(visible_records))

        for row, record in enumerate(visible_records):
            room_number, start_time, duration, speed = self.normalize_record(record, row)
            self._set_cell(row, 0, room_number, Qt.AlignCenter)
            self._set_cell(row, 1, start_time, Qt.AlignCenter)
            self._set_cell(row, 2, duration, Qt.AlignCenter)
            self._set_cell(row, 3, speed, Qt.AlignCenter)

        if visible_records:
            self.status_label.setText(f"Показаны последние {len(visible_records)} звонков.")
        else:
            self.status_label.setText("Журнал звонков пуст или еще не загружен.")

    def load_from_device(self, device_handler):
        """Placeholder for device-specific call history commands."""
        raise NotImplementedError(
            "Команды чтения журнала звонков для устройств будут добавлены позже."
        )

    def clear_records(self):
        self.table.setRowCount(0)
        self.status_label.setText("Данные журнала звонков не загружены.")

    def normalize_record(self, record, row):
        if isinstance(record, dict):
            room_number = record.get("room_number", record.get("call_number", ""))
            start_time = record.get("start_time", "")
            duration = record.get("duration", "")
            speed = record.get("speed", "")
            return room_number, start_time, duration, speed

        if isinstance(record, (list, tuple)):
            values = list(record)
            room_number = values[0] if len(values) > 0 else ""
            start_time = values[1] if len(values) > 1 else ""
            duration = values[2] if len(values) > 2 else ""
            speed = values[3] if len(values) > 3 else ""
            return room_number, start_time, duration, speed

        return "", "", "", ""

    def _set_cell(self, row, column, value, alignment):
        item = QTableWidgetItem(str(value))
        item.setTextAlignment(alignment)
        self.table.setItem(row, column, item)
