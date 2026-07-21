from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..components import (
    EmptyState,
    ParameterRow,
    SectionCard,
    SemanticButton,
    StatusIndicator,
)
from ..theme import SPACING
from .base_screen import BaseScreen


class PDUScreen(BaseScreen):
    """Aten outlet status and control screen."""

    refreshRequested = pyqtSignal()
    outletMutationRequested = pyqtSignal(int, str)
    bulkMutationRequested = pyqtSignal(str)
    outlet_control_signal = pyqtSignal(int, str)
    bulk_control_signal = pyqtSignal(str)
    ACTION_BUTTON_WIDTH = 128

    def __init__(self, parent=None):
        self.outlet_names = [f"Розетка {number}" for number in range(1, 9)]
        self.outlets = []
        self.device_info = {}
        self.capabilities = {
            "on": True,
            "off": True,
            "reboot": True,
        }
        self.bulk_busy = False
        self.bulk_context = None
        self.bulk_records_current = False
        self.mutation_busy = False
        self.mutation_context = None
        self.mutation_kind = None
        super().__init__(parent)

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("pduScrollArea")
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content = QWidget(self.scroll_area)
        self.content.setObjectName("pduContent")
        main_layout = QVBoxLayout(self.content)
        main_layout.setContentsMargins(
            SPACING["lg"], SPACING["md"], SPACING["lg"], SPACING["lg"]
        )
        main_layout.setSpacing(SPACING["md"])
        self.create_info_panel(main_layout)
        self.create_outlets_table(main_layout)
        self.scroll_area.setWidget(self.content)
        root_layout.addWidget(self.scroll_area)
        self.outlet_control_signal.connect(self.on_outlet_control)
        self.bulk_control_signal.connect(self.on_bulk_control)

    def create_info_panel(self, parent_layout):
        self.info_group = SectionCard(
            "Информация об устройстве", "▣", self
        )
        self.info_labels = {}
        self.info_rows = {}
        fields = (
            ("model", "Модель"),
            ("ip_address", "IP-адрес"),
            ("firmware", "Прошивка"),
            ("status", "Состояние"),
        )
        for field, title in fields:
            row = ParameterRow(title, "—", self.info_group)
            row.value_display.setProperty("data_field", True)
            self.info_rows[field] = row
            self.info_labels[field] = row.value_display
            self.info_group.add_widget(row)
        parent_layout.addWidget(self.info_group)

    def create_outlets_table(self, parent_layout):
        self.outlets_group = SectionCard(
            "Управление розетками", "⏻", self
        )

        refresh_widget = QWidget(self.outlets_group)
        refresh_layout = QHBoxLayout(refresh_widget)
        refresh_layout.setContentsMargins(0, 0, 0, 0)
        refresh_layout.addStretch(1)
        self.btn_refresh = SemanticButton(
            "Обновить статус", "primary", refresh_widget
        )
        self.btn_refresh.clicked.connect(self.refresh)
        refresh_layout.addWidget(self.btn_refresh)
        self.outlets_group.add_widget(refresh_widget)

        self.outlets_table = QTableWidget(0, 6, self.outlets_group)
        self.outlets_table.setObjectName("pduOutletsTable")
        self.outlets_table.setHorizontalHeaderLabels(
            ["№", "Статус", "Название", "Вкл", "Выкл", "Перезапуск"]
        )
        self.outlets_table.setAlternatingRowColors(True)
        self.outlets_table.verticalHeader().setVisible(False)
        self.outlets_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.outlets_table.setSelectionMode(QTableWidget.NoSelection)
        self.outlets_table.setFocusPolicy(Qt.NoFocus)
        self.outlets_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.outlets_table.setMinimumHeight(300)

        header = self.outlets_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        for column in (3, 4, 5):
            self.outlets_table.setColumnWidth(column, self.ACTION_BUTTON_WIDTH)

        self.outlets_group.add_widget(self.outlets_table, 1)
        self.outlets_empty = EmptyState(
            "Нет данных о розетках",
            "Обновите статус устройства, чтобы увидеть доступные розетки.",
            "⏻",
            self.outlets_group,
        )
        self.outlets_group.add_widget(self.outlets_empty)
        self.outlets_table.setVisible(False)
        self.create_bulk_controls()
        parent_layout.addWidget(self.outlets_group, 1)

    def create_bulk_controls(self):
        self.bulk_widget = QWidget(self.outlets_group)
        self.bulk_layout = QGridLayout(self.bulk_widget)
        self.bulk_layout.setContentsMargins(0, 0, 0, 0)
        self.bulk_layout.setHorizontalSpacing(0)
        self.bulk_layout.setVerticalSpacing(0)
        self.bulk_layout.setColumnStretch(2, 1)

        self.btn_bulk_on = SemanticButton("Вкл всё", "success", self.bulk_widget)
        self.btn_bulk_on.setToolTip("Включить все доступные розетки по очереди")
        self.btn_bulk_on.clicked.connect(lambda: self.on_bulk_button_click("on"))
        self._configure_action_button(self.btn_bulk_on)
        self.bulk_layout.addWidget(self.btn_bulk_on, 0, 3, alignment=Qt.AlignCenter)

        self.btn_bulk_off = SemanticButton("Выкл всё", "danger", self.bulk_widget)
        self.btn_bulk_off.setToolTip("Выключить все доступные розетки по очереди")
        self.btn_bulk_off.clicked.connect(lambda: self.on_bulk_button_click("off"))
        self._configure_action_button(self.btn_bulk_off)
        self.bulk_layout.addWidget(self.btn_bulk_off, 0, 4, alignment=Qt.AlignCenter)

        self.outlets_group.add_widget(self.bulk_widget)
        self._sync_bulk_layout_columns()
        self._sync_bulk_controls()

    def clear_data(self):
        self.device_info = {}
        self.outlets = []
        for row in self.info_rows.values():
            row.set_value("—")
            row.set_state("inactive")
        self.outlets_table.clearContents()
        self.outlets_table.setRowCount(0)
        self.outlets_table.setVisible(False)
        self.outlets_empty.setVisible(True)
        self.bulk_busy = False
        self.bulk_context = None
        self.bulk_records_current = False
        self.mutation_busy = False
        self.mutation_context = None
        self.mutation_kind = None
        self._sync_bulk_controls()

    def update_data(self, data):
        if not data:
            return

        if "device_info" in data:
            self.device_info = data["device_info"] or {}
            self.update_info_panel()

        if "capabilities" in data and isinstance(data["capabilities"], dict):
            self.capabilities = {
                "on": bool(data["capabilities"].get("on", False)),
                "off": bool(data["capabilities"].get("off", False)),
                "reboot": bool(data["capabilities"].get("reboot", False)),
            }
            self._sync_capability_columns()
            self._sync_bulk_controls()

        if "outlets" in data:
            self.outlets = data["outlets"] or []
            self.bulk_records_current = True
            for outlet in self.outlets:
                number = outlet.get("number")
                name = outlet.get("name")
                if name and isinstance(number, int):
                    index = number - 1
                    if 0 <= index < len(self.outlet_names):
                        self.outlet_names[index] = name
            self.update_outlets_table()
            self._sync_bulk_controls()

    def update_info_panel(self):
        for field in ("model", "ip_address", "firmware"):
            if field in self.device_info:
                self.info_rows[field].set_value(self.device_info[field])
                self.info_rows[field].set_state("normal")

        if "connected" in self.device_info:
            connected = bool(self.device_info["connected"])
            self.info_rows["status"].set_value(
                "Подключено" if connected else "Отключено"
            )
            self.info_rows["status"].set_state(
                "success" if connected else "error"
            )
        elif "status" in self.device_info:
            self.info_rows["status"].set_value(self.device_info["status"])
            self.info_rows["status"].set_state("normal")

    @staticmethod
    def _is_outlet_on(value):
        return str(value).strip().lower() in {"on", "1", "true"}

    def update_outlets_table(self):
        self.outlets_table.clearContents()
        self.outlets_table.setRowCount(len(self.outlets))
        self.outlets_table.setVisible(bool(self.outlets))
        self.outlets_empty.setVisible(not self.outlets)
        self._sync_capability_columns()

        action_specs = (
            (3, "on", "Вкл", "Включить", "success"),
            (4, "off", "Выкл", "Выключить", "danger"),
            (5, "reboot", "Перезапуск", "Перезагрузить", "secondary"),
        )
        for row, outlet in enumerate(self.outlets):
            outlet_number = outlet.get("number", row + 1)
            number_item = QTableWidgetItem(str(outlet_number))
            number_item.setTextAlignment(Qt.AlignCenter)
            self.outlets_table.setItem(row, 0, number_item)

            status_on = self._is_outlet_on(outlet.get("status", "off"))
            indicator = StatusIndicator(
                "success" if status_on else "inactive",
                "Включена" if status_on else "Выключена",
                show_text=True,
                parent=self.outlets_table,
            )
            indicator.setAlignment(Qt.AlignCenter)
            self.outlets_table.setCellWidget(row, 1, indicator)

            default_name = (
                self.outlet_names[row]
                if row < len(self.outlet_names)
                else f"Розетка {row + 1}"
            )
            outlet_name = outlet.get("name") or default_name
            name_item = QTableWidgetItem(str(outlet_name).strip())
            name_item.setTextAlignment(Qt.AlignCenter)
            self.outlets_table.setItem(row, 2, name_item)

            for column, command, text, tooltip, role in action_specs:
                if not self.capabilities.get(command, False):
                    self.outlets_table.setItem(row, column, QTableWidgetItem(""))
                    continue
                button = SemanticButton(text, role, self.outlets_table)
                button.setToolTip(tooltip)
                self._configure_action_button(button)
                button.setEnabled(not self.mutation_busy)
                button.clicked.connect(
                    lambda checked=False, r=row, action=column:
                    self.on_outlet_button_click(r, action)
                )
                self.outlets_table.setCellWidget(row, column, button)

            self.outlets_table.setRowHeight(row, 44)
        self.outlets_table.viewport().update()
        self._sync_bulk_layout_columns()
        self._sync_bulk_controls()

    def _sync_capability_columns(self):
        self.outlets_table.setColumnHidden(5, not self.capabilities.get("reboot", False))
        for column in (3, 4, 5):
            self.outlets_table.setColumnWidth(column, self.ACTION_BUTTON_WIDTH)
        self._sync_bulk_layout_columns()

    def _configure_action_button(self, button):
        button.setFixedWidth(self.ACTION_BUTTON_WIDTH)
        button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

    def _sync_bulk_layout_columns(self):
        if not hasattr(self, "bulk_layout"):
            return
        for column in range(self.outlets_table.columnCount()):
            hidden = self.outlets_table.isColumnHidden(column)
            width = 0 if hidden else self.outlets_table.columnWidth(column)
            if column in (3, 4) or (column == 5 and not hidden):
                width = self.ACTION_BUTTON_WIDTH
            self.bulk_layout.setColumnMinimumWidth(column, width)
            self.bulk_layout.setColumnStretch(column, 1 if column == 2 else 0)

    def _sync_bulk_controls(self):
        if not hasattr(self, "btn_bulk_on"):
            return
        has_outlets = bool(self.outlets)
        controls_ready = has_outlets and self.bulk_records_current and not self.mutation_busy
        self.btn_bulk_on.setEnabled(
            controls_ready and self.capabilities.get("on", False)
        )
        self.btn_bulk_off.setEnabled(
            controls_ready and self.capabilities.get("off", False)
        )

    def _set_individual_controls_enabled(self, enabled):
        for row in range(self.outlets_table.rowCount()):
            for column in (3, 4, 5):
                button = self.outlets_table.cellWidget(row, column)
                if isinstance(button, SemanticButton):
                    button.setEnabled(enabled)

    def set_bulk_records_current(self, current):
        self.bulk_records_current = bool(current)
        self._sync_bulk_controls()

    def set_pdu_mutation_state(self, context, kind, busy):
        if busy:
            self.mutation_context = context
            self.mutation_kind = kind
            self.mutation_busy = True
            self.bulk_context = context if kind == "bulk" else None
            self.bulk_busy = kind == "bulk"
        elif self.mutation_context == context:
            self.mutation_context = None
            self.mutation_kind = None
            self.mutation_busy = False
            self.bulk_context = None
            self.bulk_busy = False
        else:
            return
        self._set_individual_controls_enabled(not self.mutation_busy)
        self._sync_bulk_controls()

    def clear_pdu_mutation_state(self):
        self.mutation_context = None
        self.mutation_kind = None
        self.mutation_busy = False
        self.bulk_context = None
        self.bulk_busy = False
        self._set_individual_controls_enabled(True)
        self._sync_bulk_controls()

    def set_bulk_operation_state(self, context, busy):
        self.set_pdu_mutation_state(context, "bulk", busy)

    def clear_bulk_operation_state(self):
        self.clear_pdu_mutation_state()

    def on_bulk_button_click(self, command):
        if self.mutation_busy:
            return
        prompts = {
            "off": "Выключить все розетки по очереди?",
            "on": "Включить все розетки по очереди?",
        }
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            prompts.get(command, "Выполнить групповую команду?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.bulk_control_signal.emit(command)

    def on_outlet_button_click(self, row, action):
        outlet_num = row + 1
        action_commands = {3: "on", 4: "off", 5: "reboot"}
        action_names = {
            3: "Включить",
            4: "Выключить",
            5: "Перезагрузить",
        }
        if action not in action_commands:
            return

        outlet_name = (
            self.outlet_names[row]
            if row < len(self.outlet_names)
            else f"Розетка {outlet_num}"
        )
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"{action_names[action]} {outlet_name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.outlet_control_signal.emit(
                outlet_num, action_commands[action]
            )

    @pyqtSlot(int, str)
    def on_outlet_control(self, outlet_num, command):
        if self.mutation_busy:
            return
        self.outletMutationRequested.emit(outlet_num, command)

    def set_outlet_command_state(self, outlet_num, command, busy):
        """Disable only the controls for the outlet being changed."""
        row = outlet_num - 1
        command_columns = {"on": 3, "off": 4, "reboot": 5}
        if not (0 <= row < self.outlets_table.rowCount()):
            return
        for column in command_columns.values():
            button = self.outlets_table.cellWidget(row, column)
            if not isinstance(button, SemanticButton):
                continue
            if busy and column == command_columns.get(command):
                button.set_loading(True, "Выполнение…")
            else:
                button.set_loading(False)
                button.setEnabled(not busy and not self.mutation_busy)

    @pyqtSlot(str)
    def on_bulk_control(self, command):
        self.bulkMutationRequested.emit(command)

    def refresh(self):
        self.refreshRequested.emit()
