from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ..components import ParameterRow, SectionCard
from ..theme import COLORS, SPACING
from .base_screen import BaseScreen


class MatrixScreen(BaseScreen):
    """Extron routing screen with the original switching contract."""

    def __init__(self, parent=None):
        self.matrix_data = None
        self.current_connection = 1
        self.inputs_num = 8
        self.outputs_num = 1
        self.input_names = []
        self.output_names = ["Main Output"]
        self.matrix_table = None
        self.info_panel_layout = None
        self.output_column_width = 150
        self.main_window = parent
        super().__init__(parent)

    def init_ui(self, params=None):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            SPACING["lg"], SPACING["md"], SPACING["lg"], SPACING["lg"]
        )
        layout.setSpacing(SPACING["md"])

        params = params or {}
        self.inputs_num = params.get("num_inputs", 8)
        self.outputs_num = params.get("num_outputs", 1)
        self.input_names = params.get(
            "input_names",
            [
                "Ноутбук 1",
                "Ноутбук 2",
                "Apple TV",
                "ВКС система",
                "Документ-камера",
                "Системный ПК",
                "Резерв 1",
                "Резерв 2",
            ],
        )
        self.output_names = params.get("output_names", ["Main Output"])

        self.routing_card = self.create_matrix_table()
        self.info_card = self.create_info_panel()
        layout.addWidget(self.routing_card, 1)
        layout.addWidget(self.info_card)

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
        return card

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

        self.matrix_table.setRowCount(self.inputs_num)
        signal_status = (self.matrix_data or {}).get("signal_status", {})
        hdcp_statuses = (self.matrix_data or {}).get("input_hdcp_status", [])
        hdcp_auth = (self.matrix_data or {}).get("input_hdcp_auth", [])
        selected_input = (self.matrix_data or {}).get(
            "current_connection", self.current_connection
        )

        for row in range(self.inputs_num):
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
        self.inputs_num = data.get("inputs_num", self.inputs_num)
        self.input_names = data.get("input_names", self.input_names)
        self.output_names = data.get("output_names", self.output_names)
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
        """Keep the existing persistent-session switching flow."""
        if column != 3 or not self.main_window:
            return

        input_num = row + 1
        ip_address = self.main_window.ip_entry.text().strip()
        device_name = self.main_window.device_combo.currentText()
        creds_list = self.main_window.device_credentials.get(device_name, [])
        if not creds_list:
            return

        current_idx = self.main_window.get_current_credential_index(
            device_name, ip_address
        )
        if current_idx >= len(creds_list):
            current_idx = 0
        creds = creds_list[current_idx]

        try:
            handler = self.main_window.ensure_matrix_persistent_handler(
                ip_address=ip_address,
                username=creds.get("username", ""),
                password=creds.get("password", ""),
            )
            handler.set_connection(1, input_num)
            QTimer.singleShot(300, self.request_status_update)
        except Exception as error:
            from PyQt5.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось переключить матрицу: {error}",
            )

    def update_info_panel(self):
        if self.matrix_data:
            self.update_data(self.matrix_data)

    def update_connection_display(self):
        if self.matrix_table is None:
            return
        for row in range(self.inputs_num):
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
        if not self.main_window:
            return

        ip_address = self.main_window.ip_entry.text().strip()
        device_name = self.main_window.device_combo.currentText()
        creds_list = self.main_window.device_credentials.get(device_name, [])
        if not creds_list:
            return
        current_idx = self.main_window.get_current_credential_index(
            device_name, ip_address
        )
        if current_idx >= len(creds_list):
            current_idx = 0
        creds = creds_list[current_idx]

        try:
            handler = self.main_window.ensure_matrix_persistent_handler(
                ip_address=ip_address,
                username=creds.get("username", ""),
                password=creds.get("password", ""),
            )
            connections = handler.get_connections()
            if connections:
                self.current_connection = connections[0]
                self.update_connection_display()
        except Exception:
            # The historical quick refresh is intentionally best-effort.
            pass

    def refresh_statuses(self):
        self.update_data()

    def refresh(self):
        if self.parent and hasattr(self.parent, "refresh_data"):
            self.parent.refresh_data()
