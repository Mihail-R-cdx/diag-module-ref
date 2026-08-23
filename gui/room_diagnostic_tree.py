"""Presentation-only projection of a :mod:`core.room_diagnostic_tree` session."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QFormLayout, QHeaderView, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from .components import ParameterRow, SectionCard

from core.room_diagnostic_tree import DeviceRowStatus, RoomCycleStatus, RoomDiagnosticSession


class RoomDiagnosticTreeWidget(QWidget):
    """A deterministic accordion-like room tree with no network-owning controls."""

    rowExpanded = pyqtSignal(str)
    rowCollapsed = pyqtSignal(str)
    localRefreshRequested = pyqtSignal(str)
    auxiliaryRequested = pyqtSignal(str, str)
    pduMutationRequested = pyqtSignal(str, int, str)
    debugRequested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("roomDiagnosticTree")
        layout = QVBoxLayout(self)
        self.room_header = QLabel(self)
        self.room_header.setObjectName("roomDiagnosticHeader")
        self.global_status = QLabel(self)
        self.global_status.setObjectName("roomDiagnosticGlobalStatus")
        self.tree = QTreeWidget(self)
        self.tree.setObjectName("roomDiagnosticRows")
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(("Оборудование", "IP", "Статус"))
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tree.header().setStretchLastSection(True)
        self.tree.itemExpanded.connect(self._accordion_expanded)
        self.tree.itemCollapsed.connect(self._accordion_collapsed)
        self.tree.itemClicked.connect(self._accordion_clicked)
        layout.addWidget(self.room_header)
        layout.addWidget(self.global_status)
        layout.addWidget(self.tree, 1)
        self._by_record: dict[str, QTreeWidgetItem] = {}
        self._changing = False
        self._interaction_locked = False
        self._session: RoomDiagnosticSession | None = None

    def render(self, session: RoomDiagnosticSession) -> None:
        # `expanded_record_id` belongs to the application session.  Rendering a
        # progress callback must not replace a user's secondary selection with the
        # source row again.
        self._session = session
        expanded_record_id = session.expanded_record_id
        self._changing = True
        try:
            vip = "ДА" if session.room_vip is True else "НЕТ" if session.room_vip is False else "НЕТ ДАННЫХ"
            self.room_header.setText(
                f"Название комнаты: {session.room_name or '—'}\n"
                f"Адрес: {session.room_address or '—'}\nVIP: {vip}"
            )
            self.global_status.setText(
                "Есть проблемы с соединением" if session.post_cycle_problem else session.status.value
            )
            self.tree.clear()
            self._by_record.clear()
            for row in session.rows:
                item = QTreeWidgetItem((row.model_label, row.ip_address or "—", row.status.value))
                item.setData(0, Qt.UserRole, row.record_id)
                item.setData(0, Qt.UserRole + 1, self._is_expandable(row))
                if self._is_expandable(row):
                    projection = QTreeWidgetItem(("", "", ""))
                    projection.setFirstColumnSpanned(True)
                    projection.setFlags(projection.flags() & ~Qt.ItemIsSelectable)
                    item.addChild(projection)
                else:
                    item.setText(2, row.status.value)
                self.tree.addTopLevelItem(item)
                if self._is_expandable(row):
                    self.tree.setItemWidget(
                        projection,
                        0,
                        RoomReadOnlyPresentation(
                            row,
                            request_local_refresh=lambda record_id=row.record_id: self.localRefreshRequested.emit(record_id),
                            request_auxiliary=(
                                lambda action, record_id=row.record_id: self.auxiliaryRequested.emit(record_id, action)
                            ),
                            request_mutation=(
                                lambda outlet, command, record_id=row.record_id: self.pduMutationRequested.emit(record_id, outlet, command)
                            ),
                            request_debug=lambda record_id=row.record_id: self.debugRequested.emit(record_id),
                            local_refresh_allowed=(
                                session.status in {
                                    RoomCycleStatus.COMPLETE,
                                    RoomCycleStatus.COMPLETE_WITH_PROBLEMS,
                                }
                                and not self._interaction_locked
                            ),
                            auxiliary_allowed=(
                                session.status in {
                                    RoomCycleStatus.COMPLETE,
                                    RoomCycleStatus.COMPLETE_WITH_PROBLEMS,
                                }
                                and not self._interaction_locked
                            ),
                            mutation_allowed=(
                                session.status in {
                                    RoomCycleStatus.COMPLETE,
                                    RoomCycleStatus.COMPLETE_WITH_PROBLEMS,
                                }
                                and not self._interaction_locked
                            ),
                            parent=self.tree,
                        ),
                    )
                self._by_record[row.record_id] = item
            if expanded_record_id and expanded_record_id in self._by_record:
                item = self._by_record[expanded_record_id]
                if item.data(0, Qt.UserRole + 1):
                    item.setExpanded(True)
        finally:
            self._changing = False
        self.tree.setEnabled(not self._interaction_locked)

    def set_interaction_locked(self, locked: bool) -> None:
        """Block accordion changes while an exclusive row operation owns I/O."""
        self._interaction_locked = locked
        self.tree.setEnabled(not locked)

    @staticmethod
    def _is_expandable(row) -> bool:
        return (
            row.capability is not None
            and row.status not in {
                DeviceRowStatus.UNSUPPORTED,
                DeviceRowStatus.MISSING_IP,
                DeviceRowStatus.AMBIGUOUS_IP,
            }
        )

    @staticmethod
    def _projection_text(row) -> str:
        lines: list[str] = []
        if row.status is DeviceRowStatus.WAITING:
            lines.append("Ожидание опроса")
        elif row.status is DeviceRowStatus.CONNECTING:
            lines.append("Подключение и получение данных...")
        if row.partial_data is not None:
            lines.append("Неподтверждённые данные:")
            lines.extend(_present_row_data(row, row.partial_data))
        if row.accepted_snapshot is not None:
            lines.append("Подтверждённые данные (устарели):" if row.stale else "Подтверждённые данные:")
            lines.extend(_present_row_data(row, row.accepted_snapshot))
        if row.warnings:
            lines.append("Предупреждения: " + "; ".join(row.warnings))
        if row.failure_reason:
            lines.append("Причина: " + row.failure_reason)
        if not lines:
            lines.append("Данные недоступны")
        return "\n".join(lines)

    def _accordion_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        if self._changing or item.parent() is not None:
            return
        if not item.data(0, Qt.UserRole + 1):
            return
        item.setExpanded(not item.isExpanded())

    def _accordion_expanded(self, item: QTreeWidgetItem) -> None:
        if self._changing or item.parent() is not None:
            return
        self._changing = True
        try:
            for index in range(self.tree.topLevelItemCount()):
                other = self.tree.topLevelItem(index)
                if other is not item:
                    other.setExpanded(False)
            if self._session is not None:
                self._session.expanded_record_id = item.data(0, Qt.UserRole)
                self.rowExpanded.emit(self._session.expanded_record_id)
        finally:
            self._changing = False

    def _accordion_collapsed(self, item: QTreeWidgetItem) -> None:
        if self._changing or item.parent() is not None:
            return
        if self._session is not None and self._session.expanded_record_id == item.data(0, Qt.UserRole):
            record_id = self._session.expanded_record_id
            self._session.expanded_record_id = None
            self.rowCollapsed.emit(record_id)


def _indexed_value(values: Any, input_number: int) -> Any:
    if isinstance(values, Mapping):
        return values.get(input_number, values.get(str(input_number), "—"))
    if isinstance(values, (list, tuple)) and input_number - 1 < len(values):
        return values[input_number - 1]
    return "—"


def normalize_matrix_presentation(snapshot: Any) -> list[tuple[Any, Any, Any, Any, Any]]:
    """Adapt the public Extron parser result to read-only table rows."""
    source = snapshot if isinstance(snapshot, Mapping) else {}
    inputs = int(source.get("inputs_num", 0) or 0)
    names = source.get("input_names") or ()
    signals = source.get("signal_status") or {}
    auth = source.get("input_hdcp_auth") or ()
    status = source.get("input_hdcp_status") or ()
    output_hdcp = source.get("output_hdcp")
    current = source.get("current_connection")
    if isinstance(signals, Mapping):
        numeric_signal_inputs = [int(key) for key in signals if str(key).isdigit()]
        if numeric_signal_inputs:
            inputs = max(inputs, max(numeric_signal_inputs))
    rows = []
    for number in range(1, inputs + 1):
        signal = _indexed_value(signals, number)
        if isinstance(signal, Mapping):
            present = "Есть сигнал" if signal.get("has_signal") else "Нет сигнала"
            signal_text = signal.get("status_text")
            signal = f"{present}: {signal_text}" if signal_text else present
        hdcp = f"Auth: {_indexed_value(auth, number)}; статус: {_indexed_value(status, number)}"
        if output_hdcp not in (None, ""):
            hdcp += f"; выход: {output_hdcp}"
        rows.append((number, _indexed_value(names, number), signal, hdcp, "Активен" if current == number else "—"))
    return rows


def normalize_audio_dsp_presentation(snapshot: Any) -> list[tuple[str, str, str]]:
    """Adapt DMP meters and Biamp signal sources without altering snapshots."""
    source = snapshot if isinstance(snapshot, Mapping) else {}
    rows: list[tuple[str, str, str]] = []
    for section in source.get("meter_sections") or ():
        if not isinstance(section, Mapping):
            continue
        title = str(section.get("title") or "Измерения")
        for channel in section.get("channels") or ():
            if not isinstance(channel, Mapping):
                continue
            if channel.get("available"):
                value = f"{channel.get('dbfs', '—')} dBFS"
                if channel.get("state") not in (None, ""):
                    value += f" ({channel['state']})"
            else:
                value = f"Недоступен ({channel.get('outcome') or 'unknown'})"
            rows.append((title, str(channel.get("name") or "—"), value))
    for source_row in source.get("signal_sources") or ():
        if not isinstance(source_row, Mapping):
            continue
        title = str(source_row.get("alias") or "Источник")
        for channel in source_row.get("rows") or ():
            if not isinstance(channel, Mapping):
                continue
            value = str(channel.get("value", "—"))
            if channel.get("state") not in (None, ""):
                value += f" ({channel['state']})"
            rows.append((title, f"Канал {channel.get('channel_number', '—')}", value))
    return rows


class RoomReadOnlyPresentation(QWidget):
    """Exact-row data projection with a deliberately narrow action request."""

    def __init__(self, row, *, request_local_refresh=None, request_auxiliary=None, request_mutation=None, request_debug=None, local_refresh_allowed=True, auxiliary_allowed=True, mutation_allowed=True, parent=None):
        super().__init__(parent)
        self.setObjectName("roomReadOnlyPresentation")
        self.setProperty("recordId", row.record_id)
        self.setProperty("presentationOnly", True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        state = self._state_text(row)
        if state:
            notice = QLabel(state, self)
            notice.setObjectName("roomPresentationState")
            notice.setWordWrap(True)
            layout.addWidget(notice)
        refresh_button = QPushButton("Локальный опрос", self)
        refresh_button.setObjectName("roomLocalRefreshButton")
        refresh_button.setEnabled(
            bool(request_local_refresh)
            and local_refresh_allowed
            and row.status is DeviceRowStatus.CONNECTED
            and row.network_actions_enabled
            and not row.interaction_blocked
        )
        if request_local_refresh is not None:
            refresh_button.clicked.connect(request_local_refresh)
        layout.addWidget(refresh_button)
        if row.capability is not None and row.capability.screen_key == "codec":
            call_log_button = QPushButton("Журнал звонков", self)
            call_log_button.setObjectName("roomCallLogButton")
            call_log_button.setEnabled(
                bool(request_auxiliary)
                and auxiliary_allowed
                and row.status is DeviceRowStatus.CONNECTED
                and row.network_actions_enabled
                and not row.interaction_blocked
            )
            if request_auxiliary is not None:
                call_log_button.clicked.connect(lambda: request_auxiliary("call_log"))
            layout.addWidget(call_log_button)
        debug_button = QPushButton("Отладка", self)
        debug_button.setObjectName("roomLocalDebugButton")
        debug_button.setEnabled(bool(request_debug) and row.accepted_snapshot is not None)
        if request_debug is not None:
            debug_button.clicked.connect(request_debug)
        layout.addWidget(debug_button)
        if row.warnings:
            warnings = QLabel("Предупреждения: " + "; ".join(row.warnings), self)
            warnings.setObjectName("roomPresentationWarnings")
            warnings.setWordWrap(True)
            layout.addWidget(warnings)
        data = row.accepted_snapshot if row.accepted_snapshot is not None else row.partial_data
        screen_key = row.capability.screen_key if row.capability is not None else ""
        builder = {
            "codec": self._build_codec,
            "pdu": self._build_pdu,
            "matrix": self._build_matrix,
            "audio_dsp": self._build_audio,
        }.get(screen_key)
        if builder is not None:
            builder(layout, data, row, request_mutation=request_mutation, mutation_allowed=mutation_allowed)
        else:
            self._add_fields(layout, "Диагностика", data)

    @staticmethod
    def _state_text(row) -> str:
        if row.partial_data is not None and row.accepted_snapshot is None:
            return "Неподтверждённые данные: подключение продолжается"
        if row.stale:
            if row.unconfirmed_after_command:
                return "Подтверждённые данные устарели: состояние после команды не подтверждено"
            return "Подтверждённые данные устарели: соединение завершено по таймауту"
        if row.last_safe_operation_error:
            return "Последняя операция: " + row.last_safe_operation_error
        if row.failure_reason:
            return "Причина: " + row.failure_reason
        if row.status is DeviceRowStatus.WAITING:
            return "Ожидание опроса"
        if row.status is DeviceRowStatus.CONNECTING:
            return "Подключение и получение данных..."
        return ""

    def _build_codec(self, layout, data, row, **_unused) -> None:
        self._add_fields(layout, "Кодек", data, (
            "model", "Модель", "Модель кодеков", "firmware", "Версия ПО", "Серийный номер", "serial",
            "MAC адрес", "mac", "SIP регистрация", "SIP адрес", "Время работы", "temperature",
            "network_speed", "Статус звонка", "Статус презентации",
        ))

    def _build_pdu(self, layout, data, row, *, request_mutation=None, mutation_allowed=True) -> None:
        source = dict(data.get("device_info") or {}) if isinstance(data, Mapping) else {}
        if isinstance(data, Mapping):
            source.update({
                key: value
                for key, value in data.items()
                if key in {"switch_ip_address", "switch_port", "ip_address", "model", "firmware"}
            })
        if not source:
            source = data
        self._add_fields(layout, "PDU", source)
        outlets = data.get("outlets", ()) if isinstance(data, Mapping) else ()
        card = SectionCard("Розетки", "⏻", self)
        table = QTableWidget(0, 6, card)
        table.setObjectName("roomPduOutlets")
        table.setHorizontalHeaderLabels(("№", "Статус", "Название", "Вкл", "Выкл", "Перезагрузка"))
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        for outlet in outlets if isinstance(outlets, list) else ():
            if not isinstance(outlet, Mapping):
                continue
            index = table.rowCount()
            table.insertRow(index)
            for column, value in enumerate((outlet.get("number", "—"), outlet.get("status", "—"), outlet.get("name", "—"))):
                table.setItem(index, column, QTableWidgetItem(str(value)))
            outlet_number = outlet.get("number")
            enabled = (
                bool(request_mutation)
                and mutation_allowed
                and row.status is DeviceRowStatus.CONNECTED
                and row.network_actions_enabled
                and not row.interaction_blocked
                and isinstance(outlet_number, int)
            )
            for column, command, label in ((3, "on", "Вкл"), (4, "off", "Выкл"), (5, "reboot", "Перезагрузка")):
                button = QPushButton(label, table)
                button.setObjectName(f"roomPdu{command.title()}Button")
                button.setEnabled(enabled and (command != "reboot" or row.diagnostic_model == "Aten PE8208AV"))
                if request_mutation is not None and isinstance(outlet_number, int):
                    button.clicked.connect(
                        lambda _checked=False, number=outlet_number, action=command: request_mutation(number, action)
                    )
                table.setCellWidget(index, column, button)
        card.add_widget(table)
        layout.addWidget(card)

    def _build_matrix(self, layout, data, row, **_unused) -> None:
        source = data if isinstance(data, Mapping) else {}
        self._add_fields(layout, "Матрица", source, ("model", "ip_address", "temperature", "connection_protocol"))
        card = SectionCard("Маршрутизация (только чтение)", "⇄", self)
        table = QTableWidget(0, 5, card)
        table.setObjectName("roomMatrixRouting")
        table.setHorizontalHeaderLabels(("Вход", "Название", "Сигнал", "HDCP", "Маршрут"))
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.verticalHeader().setVisible(False)
        for values in normalize_matrix_presentation(source):
            index = table.rowCount()
            table.insertRow(index)
            for column, value in enumerate(values):
                table.setItem(index, column, QTableWidgetItem(str(value)))
        card.add_widget(table)
        layout.addWidget(card)

    def _build_audio(self, layout, data, row, **_unused) -> None:
        source = data.get("device_info", data) if isinstance(data, Mapping) else data
        self._add_fields(layout, "Аудио DSP", source)
        card = SectionCard("Каналы и измерения", "∿", self)
        table = QTableWidget(0, 3, card)
        table.setObjectName("roomAudioMeasurements")
        table.setHorizontalHeaderLabels(("Раздел", "Параметр", "Значение"))
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        for values in normalize_audio_dsp_presentation(data):
            index = table.rowCount()
            table.insertRow(index)
            for column, item in enumerate(values):
                table.setItem(index, column, QTableWidgetItem(str(item)))
        card.add_widget(table)
        layout.addWidget(card)

    def _add_fields(self, layout, title: str, data: Any, preferred=()) -> None:
        card = SectionCard(title, "▣", self)
        form = QFormLayout()
        source = data if isinstance(data, Mapping) else {}
        keys = list(preferred) if preferred else list(source)
        seen = set()
        for key in keys + [key for key in source if key not in keys]:
            if key in seen or key not in source or str(key).startswith("_"):
                continue
            value = source[key]
            if isinstance(value, (Mapping, list, tuple)):
                continue
            seen.add(key)
            label = {
                "serial": "Серийный номер",
                "firmware": "Версия прошивки",
                "mac": "MAC адрес",
                "ip_address": "IP-адрес",
                "network_speed": "Скорость сети",
            }.get(str(key), str(key))
            form.addRow(QLabel(label, card), QLabel(str(value), card))
        if not seen:
            form.addRow(QLabel("Статус", card), QLabel("—", card))
        card.body_layout.addLayout(form)
        layout.addWidget(card)
