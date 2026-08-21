"""Presentation-only projection of a :mod:`core.room_diagnostic_tree` session."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHeaderView, QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from core.room_diagnostic_tree import DeviceRowStatus, RoomDiagnosticSession


class RoomDiagnosticTreeWidget(QWidget):
    """A deterministic accordion-like room tree with no network-owning controls."""

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
            self.global_status.setText(session.status.value)
            self.tree.clear()
            self._by_record.clear()
            for row in session.rows:
                item = QTreeWidgetItem((row.model_label, row.ip_address or "—", row.status.value))
                item.setData(0, Qt.UserRole, row.record_id)
                item.setData(0, Qt.UserRole + 1, self._is_expandable(row))
                if self._is_expandable(row):
                    projection = QTreeWidgetItem(("", "", ""))
                    projection.setFirstColumnSpanned(True)
                    projection.setText(0, self._projection_text(row))
                    projection.setFlags(projection.flags() & ~Qt.ItemIsSelectable)
                    item.addChild(projection)
                else:
                    item.setText(2, row.status.value)
                self.tree.addTopLevelItem(item)
                self._by_record[row.record_id] = item
            if expanded_record_id and expanded_record_id in self._by_record:
                item = self._by_record[expanded_record_id]
                if item.data(0, Qt.UserRole + 1):
                    item.setExpanded(True)
        finally:
            self._changing = False

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
        finally:
            self._changing = False

    def _accordion_collapsed(self, item: QTreeWidgetItem) -> None:
        if self._changing or item.parent() is not None:
            return
        if self._session is not None and self._session.expanded_record_id == item.data(0, Qt.UserRole):
            self._session.expanded_record_id = None


def _present_row_data(row, data: Any) -> list[str]:
    """Project exact-row state through the registered screen family only.

    These presenters share existing screen labels and field semantics, but are
    deliberately pure/read-only: they neither instantiate an interactive screen
    nor receive a controller, worker, timer, or connection authority.
    """
    screen_key = row.capability.screen_key if row.capability is not None else ""
    presenter = _ROOM_PRESENTERS.get(screen_key)
    if presenter is None:
        return ["Данные модели получены"]
    return presenter(data)


def _codec_presentation(data: Any) -> list[str]:
    return _labelled_fields(
        "Кодек",
        data,
        (
            ("model", "Модель"),
            ("Модель", "Модель"),
            ("Модель кодеков", "Модель"),
            ("serial", "Серийный номер"),
            ("Серийный номер", "Серийный номер"),
            ("firmware", "Версия прошивки"),
            ("Версия ПО", "Версия прошивки"),
            ("ip_address", "IP-адрес"),
            ("SIP регистрация", "SIP регистрация"),
            ("Статус презентации", "Статус презентации"),
        ),
    )


def _pdu_presentation(data: Any) -> list[str]:
    source = data.get("device_info", data) if isinstance(data, Mapping) else data
    lines = _labelled_fields(
        "PDU",
        source,
        (("model", "Модель"), ("ip_address", "IP-адрес"), ("firmware", "Версия ПО"), ("serial", "Серийный номер")),
    )
    if isinstance(data, Mapping) and isinstance(data.get("outlets"), list):
        outlets = [item for item in data["outlets"] if isinstance(item, Mapping)]
        if outlets:
            labels = ", ".join(
                f"{item.get('number', '—')}: {item.get('name') or item.get('status') or '—'}"
                for item in outlets
            )
            lines.append("Розетки: " + labels)
    return lines


def _matrix_presentation(data: Any) -> list[str]:
    return _labelled_fields(
        "Матрица",
        data,
        (("model", "Модель"), ("ip_address", "IP-адрес"), ("temperature", "Температура"), ("connection_protocol", "Протокол"), ("current_connection", "Активный вход")),
    )


def _audio_presentation(data: Any) -> list[str]:
    source = data.get("device_info", data) if isinstance(data, Mapping) else data
    lines = _labelled_fields(
        "Аудио DSP",
        source,
        (("model", "Модель"), ("ip_address", "IP-адрес"), ("name", "Устройство")),
    )
    if isinstance(data, Mapping):
        sections = data.get("meter_sections") or data.get("signal_sources")
        if isinstance(sections, list):
            lines.append(f"Источники/метры: {len(sections)}")
    return lines


def _labelled_fields(title: str, data: Any, fields: tuple[tuple[str, str], ...]) -> list[str]:
    if not isinstance(data, Mapping):
        return [f"{title}: данные получены"]
    lines = [title]
    shown: set[str] = set()
    for key, label in fields:
        if key in data and label not in shown:
            lines.append(f"{label}: {data[key]}")
            shown.add(label)
    return lines if len(lines) > 1 else [f"{title}: модельные данные получены"]


_ROOM_PRESENTERS = {
    "codec": _codec_presentation,
    "pdu": _pdu_presentation,
    "matrix": _matrix_presentation,
    "audio_dsp": _audio_presentation,
}
