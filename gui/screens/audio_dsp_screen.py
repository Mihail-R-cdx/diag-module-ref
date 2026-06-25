from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .base_screen import BaseScreen


class AudioDSPScreen(BaseScreen):
    """Read-only audio DSP status screen."""

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.container = QWidget()
        self.container.setStyleSheet(f"background-color: {self.colors['surface']};")
        self.content_layout = QVBoxLayout(self.container)
        self.content_layout.setContentsMargins(24, 20, 24, 20)
        self.content_layout.setSpacing(14)

        self.info_group = QGroupBox("Device")
        self.info_group.setStyleSheet(self._device_group_style())
        info_layout = QVBoxLayout(self.info_group)
        self.model_value = QLabel("<unavailable>")
        self.model_value.setStyleSheet(
            f"background-color: #3A3A3A; color: {self.colors['text_primary']}; font-weight: bold;"
        )
        self.ip_value = QLabel("<unavailable>")
        self.ip_value.setStyleSheet(f"background-color: #3A3A3A; color: {self.colors['text_primary']};")
        info_layout.addWidget(self.model_value)
        info_layout.addWidget(self.ip_value)
        self.content_layout.addWidget(self.info_group)

        self.sources_layout = QVBoxLayout()
        self.sources_layout.setSpacing(12)
        self.content_layout.addLayout(self.sources_layout)
        self.content_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.container)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        layout.addWidget(scroll)

    def clear_data(self):
        self.model_value.setText("<unavailable>")
        self.ip_value.setText("<unavailable>")
        self._clear_sources()

    def update_data(self, data):
        if not data:
            return

        device_info = data.get("device_info") or {}
        self.model_value.setText(str(device_info.get("model") or data.get("model") or "<unavailable>"))
        self.ip_value.setText(str(device_info.get("ip_address") or data.get("ip_address") or "<unavailable>"))
        self._clear_sources()

        signal_sources = data.get("signal_sources") or []
        if not signal_sources:
            empty = QLabel("No signal sources")
            empty.setStyleSheet(f"color: {self.colors['text_secondary']}; padding: 12px;")
            self.sources_layout.addWidget(empty)
            return

        grid = QGridLayout()
        grid.setSpacing(12)
        self.sources_layout.addLayout(grid)

        for source_index, source in enumerate(signal_sources):
            if not isinstance(source, dict):
                continue
            alias = source.get("alias", "<unknown>")
            attribute = source.get("subscription_attribute", "<unknown>")
            group = QGroupBox(f"{alias} ({attribute})")
            title_font = group.font()
            title_font.setPointSize(title_font.pointSize() + 2)
            group.setFont(title_font)
            group.setStyleSheet(self._group_style())
            group_layout = QVBoxLayout(group)
            group_layout.setContentsMargins(10, 16, 10, 10)

            table = QTableWidget()
            table.setFont(self.font())
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(["Channel number", "Value"])
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            table.verticalHeader().setVisible(False)
            table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
            table.verticalHeader().setDefaultSectionSize(16)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionMode(QTableWidget.NoSelection)
            table.setFocusPolicy(Qt.NoFocus)
            table.setStyleSheet(self._table_style())

            rows = source.get("rows") or []
            table.setRowCount(len(rows))
            for row_index, row in enumerate(rows):
                channel = row.get("channel_number", row_index + 1) if isinstance(row, dict) else row_index + 1
                value = row.get("value") if isinstance(row, dict) else row
                channel_item = QTableWidgetItem(str(channel))
                channel_item.setTextAlignment(Qt.AlignCenter)
                value_item = QTableWidgetItem(str(value))
                value_item.setTextAlignment(Qt.AlignCenter)
                self._apply_value_color(value_item, value)
                table.setItem(row_index, 0, channel_item)
                table.setItem(row_index, 1, value_item)
            self._fit_table_height(table, len(rows))
            group_layout.addWidget(table)
            grid.addWidget(group, source_index // 2, source_index % 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

    def refresh(self):
        if self.parent and hasattr(self.parent, "refresh_data"):
            self.parent.refresh_data()

    def _clear_sources(self):
        while self.sources_layout.count():
            child = self.sources_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

    def _clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                self._clear_layout(child.layout())

    def _apply_value_color(self, item, value):
        normalized = str(value).strip().lower()
        if normalized == "true":
            item.setForeground(QColor("#4CAF50"))
            return
        if normalized == "false":
            item.setForeground(QColor(self.colors["text_secondary"]))

    def _fit_table_height(self, table, row_count):
        row_height = table.verticalHeader().defaultSectionSize()
        header_height = table.horizontalHeader().sizeHint().height()
        frame_width = table.frameWidth() * 2
        table.setFixedHeight(header_height + (row_count * row_height) + frame_width)

    def _group_style(self, title_font_size=None):
        title_font = f"font-size: {title_font_size}pt;" if title_font_size else ""
        return f"""
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {self.colors['divider']};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 12px;
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                {title_font}
            }}
        """

    def _device_group_style(self):
        return f"""
            QGroupBox {{
                font-weight: bold;
                border: 1px solid #8A8A8A;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 12px;
                background-color: #3A3A3A;
                color: {self.colors['text_primary']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """

    def _table_style(self):
        return f"""
            QTableWidget {{
                background-color: {self.colors['background']};
                color: {self.colors['text_primary']};
                gridline-color: {self.colors['divider']};
                border: 1px solid {self.colors['divider']};
            }}
            QHeaderView::section {{
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
                padding: 8px;
                border: none;
                border-bottom: 2px solid {self.colors['primary']};
                font-weight: bold;
            }}
        """
