from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..components import EmptyState, ParameterRow, SectionCard
from ..equipment_pages import (
    apply_switch_connection_row_values,
    attach_switch_connection_rows,
)
from ..theme import COLORS, SPACING
from .base_screen import BaseScreen


class AudioDSPScreen(BaseScreen):
    """Read-only Biamp signal status screen."""

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("audioDSPScrollArea")
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.container = QWidget(self.scroll_area)
        self.container.setObjectName("audioDSPContent")
        self.content_layout = QVBoxLayout(self.container)
        self.content_layout.setContentsMargins(
            SPACING["lg"], SPACING["md"], SPACING["lg"], SPACING["lg"]
        )
        self.content_layout.setSpacing(SPACING["md"])

        self.info_group = SectionCard(
            "Информация об устройстве", "▣", self.container
        )
        self.model_row = ParameterRow("Модель", "—", self.info_group)
        self.ip_row = ParameterRow("IP-адрес", "—", self.info_group)
        self.model_value = self.model_row.value_display
        self.ip_value = self.ip_row.value_display
        self.model_value.setProperty("data_field", True)
        self.ip_value.setProperty("data_field", True)
        self.info_group.add_widget(self.model_row)
        self.info_group.add_widget(self.ip_row)
        self.switch_ip_row, self.switch_port_row = attach_switch_connection_rows(
            self.info_group, self
        )
        self.content_layout.addWidget(self.info_group)

        self.sources_container = QWidget(self.container)
        self.sources_container.setObjectName("audioDSPSources")
        self.sources_layout = QGridLayout(self.sources_container)
        self.sources_layout.setContentsMargins(0, 0, 0, 0)
        self.sources_layout.setHorizontalSpacing(SPACING["md"])
        self.sources_layout.setVerticalSpacing(SPACING["md"])
        self.content_layout.addWidget(self.sources_container)
        self.content_layout.addStretch(1)

        self.scroll_area.setWidget(self.container)
        layout.addWidget(self.scroll_area)
        self.source_cards = []

    def set_switch_connection(self, switch_ip_address=None, switch_port=None):
        """Render safe scalar switch presentation into the current switch rows."""
        if not hasattr(self, "switch_ip_row") or not hasattr(self, "switch_port_row"):
            return
        apply_switch_connection_row_values(
            self.switch_ip_row,
            self.switch_port_row,
            switch_ip_address=switch_ip_address,
            switch_port=switch_port,
        )

    def clear_data(self):
        self.model_row.set_value("—")
        self.ip_row.set_value("—")
        self.model_row.set_state("inactive")
        self.ip_row.set_state("inactive")
        self._clear_sources()

    def update_data(self, data):
        if not data:
            return

        device_info = data.get("device_info") or {}
        self.model_row.set_value(
            device_info.get("model") or data.get("model") or "—"
        )
        self.ip_row.set_value(
            device_info.get("ip_address") or data.get("ip_address") or "—"
        )
        self.model_row.set_state("normal")
        self.ip_row.set_state("normal")
        self._clear_sources()

        meter_sections = data.get("meter_sections") or []
        if meter_sections:
            self._render_meter_sections(meter_sections)
            return

        signal_sources = data.get("signal_sources") or []
        if not signal_sources:
            self.empty_state = EmptyState(
                "Нет источников сигнала",
                "Устройство не вернуло доступные измерения.",
                "∿",
                self.sources_container,
            )
            self.sources_layout.addWidget(self.empty_state, 0, 0, 1, 2)
            return

        source_index = 0
        for source in signal_sources:
            if not isinstance(source, dict):
                continue
            alias = source.get("alias", "<unknown>")
            attribute = source.get(
                "subscription_attribute", "<unknown>"
            )
            card = SectionCard(
                f"{alias} · {attribute}", "∿", self.sources_container
            )
            card.setObjectName("audioDSPSourceCard")
            table = self._create_source_table(card, source.get("rows") or [])
            card.add_widget(table)
            self.sources_layout.addWidget(
                card, source_index // 2, source_index % 2
            )
            self.source_cards.append(card)
            source_index += 1

        self.sources_layout.setColumnStretch(0, 1)
        self.sources_layout.setColumnStretch(1, 1)

    def _render_meter_sections(self, meter_sections):
        section_index = 0
        for section in meter_sections:
            if not isinstance(section, dict):
                continue
            title = section.get("title") or "Meters"
            channels = section.get("channels") or []
            card = SectionCard(str(title), "∿", self.sources_container)
            card.setObjectName("dmpMeterSectionCard")
            for channel in channels:
                if isinstance(channel, dict):
                    card.add_widget(self._create_meter_row(card, channel))
            self.sources_layout.addWidget(card, section_index, 0, 1, 2)
            self.source_cards.append(card)
            section_index += 1
        self.sources_layout.setColumnStretch(0, 1)
        self.sources_layout.setColumnStretch(1, 1)

    def _create_meter_row(self, parent, channel):
        row = QWidget(parent)
        row.setObjectName("dmpMeterRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, SPACING["xs"], 0, SPACING["xs"])
        layout.setSpacing(SPACING["sm"])

        label = QLabel(str(channel.get("name") or channel.get("oid") or "Meter"), row)
        label.setObjectName("dmpMeterLabel")
        label.setMinimumWidth(92)

        bar = QProgressBar(row)
        bar.setObjectName("dmpMeterBar")
        bar.setTextVisible(False)
        bar.setRange(0, 1000)
        bar.setProperty("available", bool(channel.get("available")))
        normalized = channel.get("normalized")
        if channel.get("available") and normalized is not None:
            bar.setValue(int(max(0.0, min(1.0, float(normalized))) * 1000))
        else:
            bar.setValue(0)
        bar.setStyleSheet(
            """
            QProgressBar#dmpMeterBar {
                min-height: 14px;
                border: 1px solid #2D2D2D;
                border-radius: 4px;
                background: #141414;
            }
            QProgressBar#dmpMeterBar::chunk {
                border-radius: 3px;
                background-color: #22C55E;
            }
            """
        )

        layout.addWidget(label)
        layout.addWidget(bar, 1)
        return row

    def _create_source_table(self, parent, rows):
        table = QTableWidget(len(rows), 2, parent)
        table.setObjectName("audioDSPValuesTable")
        table.setHorizontalHeaderLabels(["Номер канала", "Значение"])
        table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        table.verticalHeader().setDefaultSectionSize(28)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.setAlternatingRowColors(True)

        for row_index, row in enumerate(rows):
            channel = (
                row.get("channel_number", row_index + 1)
                if isinstance(row, dict)
                else row_index + 1
            )
            value = row.get("value") if isinstance(row, dict) else row
            channel_item = QTableWidgetItem(str(channel))
            channel_item.setTextAlignment(Qt.AlignCenter)
            value_item = QTableWidgetItem(str(value))
            value_item.setTextAlignment(Qt.AlignCenter)
            self._apply_value_color(value_item, value)
            table.setItem(row_index, 0, channel_item)
            table.setItem(row_index, 1, value_item)
        self._fit_table_height(table, len(rows))
        return table

    def refresh(self):
        if self.parent and hasattr(self.parent, "refresh_data"):
            self.parent.refresh_data()

    def _clear_sources(self):
        self.source_cards = []
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

    @staticmethod
    def _apply_value_color(item, value):
        normalized = str(value).strip().lower()
        if normalized == "true":
            item.setForeground(QColor(COLORS["success"]))
        elif normalized == "false":
            item.setForeground(QColor(COLORS["text_muted"]))

    @staticmethod
    def _fit_table_height(table, row_count):
        row_height = table.verticalHeader().defaultSectionSize()
        header_height = table.horizontalHeader().sizeHint().height()
        frame_width = table.frameWidth() * 2
        table.setFixedHeight(
            header_height + (row_count * row_height) + frame_width
        )
