"""Presentation-only projection of a :mod:`core.room_diagnostic_tree` session."""

from __future__ import annotations

from PyQt5.QtWidgets import QHeaderView, QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from core.room_diagnostic_tree import RoomDiagnosticSession


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
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(("Оборудование", "IP", "Статус", "Детали"))
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tree.header().setStretchLastSection(True)
        self.tree.itemSelectionChanged.connect(self._accordion_selection)
        layout.addWidget(self.room_header)
        layout.addWidget(self.global_status)
        layout.addWidget(self.tree, 1)
        self._by_record: dict[str, QTreeWidgetItem] = {}
        self._changing = False

    def render(self, session: RoomDiagnosticSession) -> None:
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
                detail = row.failure_reason or "; ".join(row.warnings) or ("Ожидание опроса" if row.eligible else "")
                item = QTreeWidgetItem((row.model_label, row.ip_address or "—", row.status.value, detail))
                item.setData(0, 32, row.record_id)
                item.setFlags(item.flags() & ~0x2)  # presentation-only; no editable cells
                self.tree.addTopLevelItem(item)
                self._by_record[row.record_id] = item
            if session.expanded_record_id and session.expanded_record_id in self._by_record:
                self.tree.setCurrentItem(self._by_record[session.expanded_record_id])
        finally:
            self._changing = False

    def _accordion_selection(self) -> None:
        if self._changing:
            return
        # Selection is intentionally presentation-only.  It cannot call an adapter,
        # start a waiting row, or affect the source-first queue.
