from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QFrame,
    QHeaderView,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..components import ParameterRow, SectionCard
from ..equipment_pages import (
    apply_switch_connection_row_values,
    attach_switch_connection_rows,
)
from ..theme import COLORS, SPACING
from .base_screen import BaseScreen


class MatrixScreen(BaseScreen):
    """Extron routing screen with the original switching contract."""

    routeRequested = pyqtSignal(int, int)
    refreshRequested = pyqtSignal()

    def __init__(self, parent=None):
        self.matrix_data = None
        self.current_connection = None
        self.inputs_num = 0
        self.outputs_num = 1
        self.input_names = []
        self.output_names = ["Main Output"]
        self.matrix_table = None
        self.info_panel_layout = None
        self.output_column_width = 150
        super().__init__(parent)

    def init_ui(self, params=None):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("matrixScrollArea")
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content = QWidget(self.scroll_area)
        self.content.setObjectName("matrixContent")
        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(
            SPACING["lg"], SPACING["md"], SPACING["lg"], SPACING["lg"]
        )
        layout.setSpacing(SPACING["md"])

        # Constructor parameters are presentation convenience only; standalone
        # routing authority begins solely with an accepted data snapshot.
        self.inputs_num = 0
        self.outputs_num = 1
        self.input_names = []
        self.output_names = ["Main Output"]

        self.routing_card = self.create_matrix_table()
        self.info_card = self.create_info_panel()
        layout.addWidget(self.routing_card, 1)
        layout.addWidget(self.info_card)
        self.scroll_area.setWidget(self.content)
        root_layout.addWidget(self.scroll_area)

    def create_matrix_table(self):
        card = SectionCard("Маршрутизация", "⇄", self)
        self.matrix_table = QTableWidget(self.inputs_num, 3 + self.outputs_num, card)
        self.matrix_table.setObjectName("matrixRoutingTable")
        self.matrix_table.setAlternatingRowColors(True)
        self.matrix_table.setSelectionMode(QTableWidget.NoSelection)
        self.matrix_table.setFocusPolicy(Qt.NoFocus)
        self.matrix_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.matrix_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.matrix_table.verticalHeader().setVisible(False)
        self.matrix_table.verticalHeader().setDefaultSectionSize(40)
        self.matrix_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.matrix_table.cellClicked.connect(self.on_output_cell_clicked)

        header = self.matrix_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        for column in range(3, 3 + self.outputs_num):
            header.setSectionResizeMode(column, QHeaderView.Stretch)
        self.matrix_table.setColumnWidth(0, 82)
        self.matrix_table.setColumnWidth(1, 82)

        self.update_table_headers()
        self.fill_matrix_table()
        card.add_widget(self.matrix_table, 1)
        return card

    def create_info_panel(self):
        card = SectionCard("Информация об устройстве", "▣", self)
        self.info_panel_layout = card.body_layout
        self.info_rows = {
            "temperature": ParameterRow("Температура", "—", card),
            "model": ParameterRow("Модель", "—", card),
            "protocol": ParameterRow("Протокол", "—", card),
        }
        self.temp_value = self.info_rows["temperature"].value_display
        self.model_value = self.info_rows["model"].value_display
        self.protocol_value = self.info_rows["protocol"].value_display
        for row in self.info_rows.values():
            row.value_display.setProperty("data_field", True)
            card.add_widget(row)
        self.switch_ip_row, self.switch_port_row = attach_switch_connection_rows(card, self)
        return card

    def set_switch_connection(self, switch_ip_address=None, switch_port=None):
        """Render safe scalar switch presentation into the current switch rows."""
        apply_switch_connection_row_values(
            self.switch_ip_row,
            self.switch_port_row,
            switch_ip_address=switch_ip_address,
            switch_port=switch_port,
        )

    def clear_data(self):
        """Reset displayed values without losing the selected route."""
        self.matrix_data = None
        self.temp_value.set_value("—")
        self.model_value.set_value("—")
        self.protocol_value.set_value("—")
        self.fill_matrix_table()

    @staticmethod
    def _status_item(active, active_color, active_tooltip, inactive_tooltip):
        item = QTableWidgetItem("●" if active else "○")
        item.setTextAlignment(Qt.AlignCenter)
        item.setForeground(
            QColor(active_color if active else COLORS["text_muted"])
        )
        item.setToolTip(active_tooltip if active else inactive_tooltip)
        font = QFont()
        font.setPointSize(16)
        item.setFont(font)
        return item

    def fill_matrix_table(self):
        if self.matrix_table is None:
            return

        input_count = self.inputs_num if isinstance(self.inputs_num, int) and self.inputs_num > 0 else 0
        self.matrix_table.setRowCount(input_count)
        signal_status = (self.matrix_data or {}).get("signal_status", {})
        hdcp_statuses = (self.matrix_data or {}).get("input_hdcp_status", [])
        hdcp_auth = (self.matrix_data or {}).get("input_hdcp_auth", [])
        selected_input = (self.matrix_data or {}).get(
            "current_connection", self.current_connection
        )

        for row in range(input_count):
            signal = signal_status.get(row + 1, {})
            has_signal = bool(signal.get("has_signal", False))
            self.matrix_table.setItem(
                row,
                0,
                self._status_item(
                    has_signal,
                    COLORS["success"],
                    "Сигнал присутствует",
                    "Нет сигнала" if self.matrix_data else "Нет данных",
                ),
            )

            status = hdcp_statuses[row] if row < len(hdcp_statuses) else None
            auth = hdcp_auth[row] if row < len(hdcp_auth) else 0
            hdcp_active = status not in (None, "0", "1") and auth == 1
            self.matrix_table.setItem(
                row,
                1,
                self._status_item(
                    hdcp_active,
                    COLORS["success"],
                    "HDCP включен",
                    "HDCP не активен" if self.matrix_data else "Нет данных",
                ),
            )

            input_name = (
                self.input_names[row]
                if row < len(self.input_names)
                else f"Вход {row + 1}"
            )
            input_item = QTableWidgetItem(input_name)
            input_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.matrix_table.setItem(row, 2, input_item)

            if self.outputs_num:
                self.matrix_table.setItem(
                    row,
                    3,
                    self._status_item(
                        row + 1 == selected_input,
                        COLORS["primary"],
                        "Активное подключение",
                        "Нет подключения",
                    ),
                )

    def update_data(self, data=None):
        if not data:
            self.fill_matrix_table()
            return

        self.matrix_data = data
        reported_count = data.get("inputs_num")
        self.inputs_num = reported_count if isinstance(reported_count, int) and reported_count > 0 else 0
        self.input_names = data.get("input_names") if isinstance(data.get("input_names"), (list, tuple)) else []
        self.output_names = data.get("output_names") if isinstance(data.get("output_names"), (list, tuple)) else []
        self.current_connection = data.get(
            "current_connection", self.current_connection
        )
        self.update_table_headers()
        self.fill_matrix_table()
        self.model_value.set_value(data.get("model", "Unknown"))
        temperature = data.get("temperature")
        self.temp_value.set_value(
            f"{temperature}°C" if temperature is not None else "—"
        )
        self.protocol_value.set_value(
            data.get("connection_protocol", "Unknown")
        )

    def update_table_headers(self):
        if self.matrix_table is None:
            return
        output_name = self.output_names[0] if self.output_names else "Выход"
        self.matrix_table.setHorizontalHeaderLabels(
            ["Сигнал", "HDCP", "Входы", output_name]
        )

    def on_output_cell_clicked(self, row, column):
        """Publish a non-secret route intent."""
        if column != 3:
            return

        input_num = row + 1
        if not isinstance(self.inputs_num, int) or not 1 <= input_num <= self.inputs_num:
            return
        self.routeRequested.emit(1, input_num)

    def update_info_panel(self):
        if self.matrix_data:
            self.update_data(self.matrix_data)

    def update_connection_display(self):
        if self.matrix_table is None:
            return
        for row in range(self.inputs_num if isinstance(self.inputs_num, int) and self.inputs_num > 0 else 0):
            self.matrix_table.setItem(
                row,
                3,
                self._status_item(
                    row + 1 == self.current_connection,
                    COLORS["primary"],
                    "Активное подключение",
                    "Нет подключения",
                ),
            )
        self.matrix_table.viewport().update()

    def request_status_update(self):
        self.refreshRequested.emit()

    def refresh_statuses(self):
        self.update_data()

    def refresh(self):
        self.refreshRequested.emit()
