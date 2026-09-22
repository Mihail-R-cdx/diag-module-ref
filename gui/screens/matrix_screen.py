from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QFrame, QHeaderView, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from ..components import ParameterRow, SectionCard
from ..equipment_pages import apply_switch_connection_row_values, attach_switch_connection_rows
from ..theme import COLORS, SPACING
from .base_screen import BaseScreen


class MatrixScreen(BaseScreen):
    """Profile-agnostic Matrix presentation; it owns no SIS or session state."""
    routeRequested = pyqtSignal(int, int)  # output ID, input ID
    refreshRequested = pyqtSignal()

    def __init__(self, parent=None):
        self.matrix_data = None; self.current_connection = None
        self.available_input_ids = []; self.available_output_ids = [1]
        self.inputs_num = 0; self.outputs_num = 1; self.input_names = {}; self.output_names = {}
        self.matrix_table = None; self.info_panel_layout = None
        super().__init__(parent)

    def init_ui(self, params=None):
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        self.scroll_area = QScrollArea(self); self.scroll_area.setObjectName("matrixScrollArea"); self.scroll_area.setFrameShape(QFrame.NoFrame); self.scroll_area.setWidgetResizable(True); self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content = QWidget(self.scroll_area); self.content.setObjectName("matrixContent")
        layout = QVBoxLayout(self.content); layout.setContentsMargins(SPACING["lg"], SPACING["md"], SPACING["lg"], SPACING["lg"]); layout.setSpacing(SPACING["md"])
        self.routing_card = self.create_matrix_table(); self.info_card = self.create_info_panel(); layout.addWidget(self.routing_card, 1); layout.addWidget(self.info_card)
        self.scroll_area.setWidget(self.content); root.addWidget(self.scroll_area)

    def create_matrix_table(self):
        card = SectionCard("Маршрутизация", "⇄", self)
        self.matrix_table = QTableWidget(0, 4, card); self.matrix_table.setObjectName("matrixRoutingTable"); self.matrix_table.setAlternatingRowColors(True); self.matrix_table.setSelectionMode(QTableWidget.NoSelection); self.matrix_table.setFocusPolicy(Qt.NoFocus); self.matrix_table.setEditTriggers(QTableWidget.NoEditTriggers); self.matrix_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.matrix_table.verticalHeader().setVisible(False); self.matrix_table.verticalHeader().setDefaultSectionSize(40); self.matrix_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed); self.matrix_table.cellClicked.connect(self.on_output_cell_clicked)
        header = self.matrix_table.horizontalHeader(); header.setSectionResizeMode(0, QHeaderView.Fixed); header.setSectionResizeMode(1, QHeaderView.Fixed); header.setSectionResizeMode(2, QHeaderView.Stretch); self.matrix_table.setColumnWidth(0, 82); self.matrix_table.setColumnWidth(1, 82)
        self.update_table_headers(); self.fill_matrix_table(); card.add_widget(self.matrix_table, 1); return card

    def create_info_panel(self):
        card = SectionCard("Информация о устройстве", "■", self); self.info_panel_layout = card.body_layout
        self.info_rows = {"temperature": ParameterRow("Температура", "—", card), "model": ParameterRow("Модель", "—", card), "protocol": ParameterRow("Протокол", "—", card)}
        self.temp_value = self.info_rows["temperature"].value_display; self.model_value = self.info_rows["model"].value_display; self.protocol_value = self.info_rows["protocol"].value_display
        for row in self.info_rows.values(): row.value_display.setProperty("data_field", True); card.add_widget(row)
        self.switch_ip_row, self.switch_port_row = attach_switch_connection_rows(card, self); return card

    def set_switch_connection(self, switch_ip_address=None, switch_port=None):
        apply_switch_connection_row_values(self.switch_ip_row, self.switch_port_row, switch_ip_address=switch_ip_address, switch_port=switch_port)
    def clear_data(self):
        self.matrix_data = None; self.temp_value.set_value("—"); self.model_value.set_value("—"); self.protocol_value.set_value("—"); self.fill_matrix_table()
    @staticmethod
    def _status_item(active, active_color, active_tooltip, inactive_tooltip):
        item = QTableWidgetItem("●" if active else "○"); item.setTextAlignment(Qt.AlignCenter); item.setForeground(QColor(active_color if active else COLORS["text_muted"])); item.setToolTip(active_tooltip if active else inactive_tooltip); font = QFont(); font.setPointSize(16); item.setFont(font); return item
    @classmethod
    def _hdcp_item(cls, state):
        """Keep confirmed HDCP absence distinct from unavailable evidence."""
        if state == "PRESENT_HDCP":
            semantic, tooltip, active = "HDCP есть", "HDCP есть", True
        elif state in {"PRESENT_NO_HDCP", "ABSENT"}:
            semantic, tooltip, active = "HDCP нет", "HDCP нет", False
        else:
            semantic, tooltip, active = "Нет данных", "HDCP: Нет данных", False
        item = cls._status_item(active, COLORS["success"], tooltip, tooltip)
        item.setData(Qt.UserRole, semantic)
        item.setData(Qt.UserRole + 1, state if state in {"PRESENT_HDCP", "PRESENT_NO_HDCP", "ABSENT"} else "UNKNOWN")
        return item
    def _name(self, names, item, fallback):
        if isinstance(names, dict): return names.get(item) or fallback
        return names[item - 1] if isinstance(names, (list, tuple)) and item - 1 < len(names) and names[item - 1] else fallback

    def _route_state(self, output_id, input_id):
        """Return the fail-closed route semantic for one visible cell.

        ``None`` is deliberately not an explicit untied value here.  The
        standalone snapshot format has no canonical marker that distinguishes
        it from absent or malformed route evidence.
        """
        data = self.matrix_data if isinstance(self.matrix_data, dict) else {}
        routes = data.get("routes")
        route = None
        has_route_evidence = False
        if isinstance(routes, dict) and output_id in routes:
            route = routes[output_id]
            has_route_evidence = True
        elif (
            output_id == 1
            and len(self.available_output_ids) == 1
            and "current_connection" in data
        ):
            route = data["current_connection"]
            has_route_evidence = True

        if not has_route_evidence or not isinstance(route, int) or route not in self.available_input_ids:
            return "UNKNOWN"
        return "ACTIVE" if route == input_id else "KNOWN_OTHER"

    @staticmethod
    def _route_item(semantic):
        if semantic == "ACTIVE":
            item = MatrixScreen._status_item(True, COLORS["primary"], "Активное подключение", "Активное подключение")
            tooltip = "Активное подключение"
        elif semantic == "KNOWN_OTHER":
            item = MatrixScreen._status_item(False, COLORS["primary"], "Нет подключения", "Нет подключения")
            tooltip = "Нет подключения"
        else:
            item = MatrixScreen._status_item(False, COLORS["primary"], "Нет данных", "Нет данных")
            tooltip = "Нет данных"
        item.setData(Qt.UserRole, semantic)
        item.setToolTip(tooltip)
        return item

    def fill_matrix_table(self):
        if self.matrix_table is None: return
        data = self.matrix_data or {}; self.matrix_table.setRowCount(len(self.available_input_ids)); self.matrix_table.setColumnCount(3 + len(self.available_output_ids))
        signal = data.get("signal_presence", {}); legacy_signal = data.get("signal_status", {}); hdcp = data.get("input_hdcp", {})
        for row, input_id in enumerate(self.available_input_ids):
            legacy = legacy_signal.get(input_id, {}) if isinstance(legacy_signal, dict) else {}; present = signal.get(input_id, legacy.get("has_signal") if isinstance(legacy, dict) else None) if isinstance(signal, dict) else None
            self.matrix_table.setItem(row, 0, self._status_item(present is True, COLORS["success"], "Сигнал присутствует", "Нет сигнала" if data else "Нет данных"))
            state = hdcp.get(input_id) if isinstance(hdcp, dict) else None
            self.matrix_table.setItem(row, 1, self._hdcp_item(state))
            name = QTableWidgetItem(self._name(self.input_names, input_id, "Input %s" % input_id)); name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter); self.matrix_table.setItem(row, 2, name)
            for column, output_id in enumerate(self.available_output_ids, 3): self.matrix_table.setItem(row, column, self._route_item(self._route_state(output_id, input_id)))
    def update_data(self, data=None):
        if not data: self.fill_matrix_table(); return
        self.matrix_data = data; self.available_input_ids = list(data.get("available_input_ids", range(1, int(data.get("inputs_num") or 0) + 1))); self.available_output_ids = list(data.get("available_output_ids", range(1, int(data.get("outputs_num") or 1) + 1))); self.inputs_num = len(self.available_input_ids); self.outputs_num = len(self.available_output_ids); self.input_names = data.get("input_names", {}); self.output_names = data.get("output_names", {}); self.current_connection = data.get("current_connection")
        self.update_table_headers(); self.fill_matrix_table(); self.model_value.set_value(data.get("model") or "Unknown"); temperature = data.get("temperature"); self.temp_value.set_value("%s°C" % temperature if temperature is not None else "—"); self.protocol_value.set_value(data.get("connection_protocol", "Unknown"))
    def update_table_headers(self):
        if self.matrix_table is None: return
        names = [self._name(self.output_names, item, "Output %s" % item) for item in self.available_output_ids]
        self.matrix_table.setColumnCount(3 + len(names)); self.matrix_table.setHorizontalHeaderLabels(["Сигнал", "HDCP", "Входы"] + names)
        header = self.matrix_table.horizontalHeader()
        for column in range(3, 3 + len(names)): header.setSectionResizeMode(column, QHeaderView.Stretch)
    def on_output_cell_clicked(self, row, column):
        if column < 3 or row < 0 or row >= len(self.available_input_ids) or column - 3 >= len(self.available_output_ids): return
        output_id = self.available_output_ids[column - 3]
        input_id = self.available_input_ids[row]
        if self._route_state(output_id, input_id) != "KNOWN_OTHER":
            return
        self.routeRequested.emit(output_id, input_id)
    def update_info_panel(self):
        if self.matrix_data: self.update_data(self.matrix_data)
    def update_connection_display(self): self.fill_matrix_table()
    def request_status_update(self): self.refreshRequested.emit()
    def refresh_statuses(self): self.update_data()
    def refresh(self): self.refreshRequested.emit()
