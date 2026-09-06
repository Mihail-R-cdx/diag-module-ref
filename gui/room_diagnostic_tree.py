"""Presentation-only projection of a :mod:`core.room_diagnostic_tree` session."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from math import floor, isfinite
from numbers import Real

from PyQt5.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QSize, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QCursor, QIcon, QPainter, QPixmap, QPolygon
from PyQt5.QtWidgets import QAbstractItemView, QFormLayout, QFrame, QGridLayout, QHeaderView, QHBoxLayout, QLabel, QProgressBar, QPushButton, QSizePolicy, QStyle, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from .components import ParameterRow, SectionCard, SemanticButton, StatusIndicator

from core.room_diagnostic_tree import DeviceRowStatus, RoomCycleStatus, RoomDiagnosticSession
from core.room_interaction import RoomInteractionKind
from core.call_activity import CallActivity
from core.codec_call_history import CallDirection
from .diagnostic_dispatch import CodecMuteState, dispatch_entry_for_model, normalize_codec_audio_projection, normalize_codec_call_projection


def _room_pdu_lightning_icon() -> QIcon:
    """Return a font-independent lightning glyph for the outlet-control card."""
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#58a6ff"))
    painter.drawPolygon(QPolygon((
        QPoint(11, 1), QPoint(3, 11), QPoint(9, 11),
        QPoint(7, 19), QPoint(17, 7), QPoint(11, 7),
    )))
    painter.end()
    return QIcon(pixmap)


class SmoothRoomTreeWidget(QTreeWidget):
    """Room accordion with a restrained animated wheel scroll."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(10)
        self._scroll_animation = QPropertyAnimation(self.verticalScrollBar(), b"value", self)
        self._scroll_animation.setDuration(260)
        self._scroll_animation.setEasingCurve(QEasingCurve.InOutCubic)

    def stop_smooth_scroll(self) -> None:
        """Revoke transient motion before a destructive presentation rebuild."""
        self._scroll_animation.stop()

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        if not delta:
            super().wheelEvent(event)
            return
        scroll_bar = self.verticalScrollBar()
        steps = delta / 120
        start = scroll_bar.value()
        target = max(scroll_bar.minimum(), min(scroll_bar.maximum(), round(start - steps * 42)))
        self._scroll_animation.stop()
        self._scroll_animation.setStartValue(start)
        self._scroll_animation.setEndValue(target)
        self._scroll_animation.start()
        event.accept()


class RoomDiagnosticTreeWidget(QWidget):
    """A deterministic accordion-like room tree with no network-owning controls."""

    rowExpanded = pyqtSignal(str)
    rowCollapsed = pyqtSignal(str)
    localRefreshRequested = pyqtSignal(str)
    auxiliaryRequested = pyqtSignal(str, str)
    codecControlRequested = pyqtSignal(str, str, object)
    pduMutationRequested = pyqtSignal(str, int, str)
    pduBulkMutationRequested = pyqtSignal(str, str)
    matrixRouteRequested = pyqtSignal(str, int, int)
    debugRequested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("roomDiagnosticTree")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        upper = QWidget(self)
        upper.setObjectName("roomDiagnosticUpperCards")
        # Keep the room summary compact while leaving room for labelled facts
        # and the switch table above the accordion.
        upper.setFixedHeight(186)
        self.upper_cards = upper
        upper_layout = QHBoxLayout(upper)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.setSpacing(16)
        self.room_card = SectionCard("Информация о комнате", "ⓘ", upper)
        self.room_card.body_layout.setSpacing(6)
        self.room_name_row = QWidget(self.room_card)
        room_name_layout = QHBoxLayout(self.room_name_row)
        room_name_layout.setContentsMargins(0, 0, 0, 0)
        room_name_layout.setSpacing(8)
        self.room_name_label = QLabel(self.room_name_row)
        self.room_name_label.setObjectName("roomName")
        self.room_name_label.setWordWrap(True)
        self.vip_badge = QLabel(self.room_name_row)
        self.vip_badge.setObjectName("roomVipBadge")
        self.vip_badge.setText("VIP")
        self.vip_badge.setToolTip("VIP-переговорная")
        self.vip_badge.setVisible(False)
        room_name_layout.addWidget(self.room_name_label, 1)
        room_name_layout.addWidget(self.vip_badge, 0, Qt.AlignTop)
        self.room_header = QLabel(self.room_card)
        self.room_header.setObjectName("roomDiagnosticHeader")
        self.room_header.setWordWrap(True)
        self.room_warranty_label = QLabel(self.room_card)
        self.room_warranty_label.setObjectName("roomWarranty")
        self.occupancy_label = QLabel(self.room_card)
        self.occupancy_label.setObjectName("roomOccupancy")
        self.occupancy_label.setToolTip("Занятость определяется по текущему состоянию звонка кодека.")
        self.room_card.body_layout.addWidget(self.room_name_row)
        self.room_card.body_layout.addWidget(self.room_header)
        self.room_card.body_layout.addWidget(self.room_warranty_label)
        self.room_card.body_layout.addWidget(self.occupancy_label)
        self.network_card = SectionCard("Сетевые подключения", "⌘", upper)
        self.network_tree = QTreeWidget(self.network_card)
        self.network_tree.setObjectName("roomNetworkConnections")
        self.network_tree.setColumnCount(3)
        self.network_tree.setHeaderLabels(("Коммутатор (IP)", "Порты", "Подключено устройств"))
        self.network_tree.setHeaderHidden(False)
        self.network_tree.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.network_tree.verticalScrollBar().setSingleStep(10)
        self.network_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.network_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.network_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.network_tree.itemExpanded.connect(self._network_item_expanded)
        self.network_tree.itemCollapsed.connect(self._network_item_collapsed)
        self.network_card.body_layout.addWidget(self.network_tree)
        upper_layout.addWidget(self.room_card, 1)
        upper_layout.addWidget(self.network_card, 1)
        layout.addWidget(upper)
        self.global_status = QLabel(self)
        self.global_status.setObjectName("roomDiagnosticGlobalStatus")
        # Cycle health belongs to the persistent footer.  Keep this label as a
        # data-bearing accessibility surface without inserting a second status
        # line between the room facts and the accordion.
        self.global_status.setVisible(False)
        self.tree = SmoothRoomTreeWidget(self)
        self.tree.setObjectName("roomDiagnosticRows")
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(("", "Устройство", "Статус подключения", "IP-адрес", "Действия"))
        self.tree.setHeaderHidden(True)
        self.tree.setIconSize(QSize(28, 28))
        self.tree.header().setSectionResizeMode(0, QHeaderView.Fixed)
        self.tree.header().resizeSection(0, 44)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(2, QHeaderView.Fixed)
        self.tree.header().resizeSection(2, 250)
        self.tree.header().setSectionResizeMode(3, QHeaderView.Fixed)
        self.tree.header().resizeSection(3, 160)
        self.tree.header().setSectionResizeMode(4, QHeaderView.Fixed)
        self.tree.header().resizeSection(4, 0)
        self.tree.itemExpanded.connect(self._accordion_expanded)
        self.tree.itemCollapsed.connect(self._accordion_collapsed)
        self.tree.itemClicked.connect(self._accordion_clicked)
        layout.addWidget(self.global_status)
        layout.addWidget(self.tree, 1)
        self._by_record: dict[str, QTreeWidgetItem] = {}
        self._changing = False
        self._interaction_locked = False
        self._active_interaction = None
        self._active_interaction_retiring = False
        self._session: RoomDiagnosticSession | None = None
        # This is deliberately local presentation state.  It is kept above the
        # disposable exact-row child widgets because render() rebuilds them.
        self._audio_selection_context = None
        self._audio_selection: tuple[str, str, str] | None = None
        self._presentation_identity = None
        self._network_expanded_switches: set[str] = set()
        self._network_restoring = False
        self._audio_popup = AudioPopupCoordinator(self)

    def render(self, session: RoomDiagnosticSession) -> None:
        # `expanded_record_id` belongs to the application session.  Rendering a
        # progress callback must not replace a user's secondary selection with the
        # source row again.
        same_context = self._presentation_identity == session.identity
        # An old animation is a write-capable transient, never restorable state.
        self.tree.stop_smooth_scroll()
        viewport = self._capture_viewport() if same_context else None
        if not same_context:
            self._network_expanded_switches.clear()
        self._audio_popup.begin_render(session, same_context)
        self._session = session
        self._presentation_identity = session.identity
        if self._audio_selection_context != session.identity:
            self._audio_selection_context = session.identity
            self._audio_selection = None
        self._prune_audio_selection(session)
        expanded_record_id = session.expanded_record_id
        self.tree.header().resizeSection(4, 0)
        self._changing = True
        try:
            self.room_name_label.setText(f"Название комнаты:  {session.room_name or '—'}")
            self.vip_badge.setVisible(session.room_vip is True)
            self.room_header.setText(f"Адрес комнаты:  {session.room_address or '—'}")
            self.room_warranty_label.setText("Гарантия:  нет данных")
            self.global_status.setText(
                "Есть проблемы с соединением" if session.post_cycle_problem else session.status.value
            )
            occupied = any(row.call_activity is CallActivity.ACTIVE and not row.stale for row in session.rows)
            self.occupancy_label.setText(f"Занятость:  {'Занято' if occupied else 'Нет данных'}")
            self._render_network(session)
            self.tree.clear()
            self._by_record.clear()
            for row in session.rows:
                active_here = (
                    self._active_interaction is not None
                    and self._active_interaction.record_id == row.record_id
                )
                live_here = (
                    active_here
                    and self._active_interaction.kind is RoomInteractionKind.LIVE
                    and not self._active_interaction_retiring
                )
                actions_allowed = (
                    session.status in {
                        RoomCycleStatus.COMPLETE,
                        RoomCycleStatus.COMPLETE_WITH_PROBLEMS,
                    }
                    and not self._interaction_locked
                    and (self._active_interaction is None or live_here)
                )
                debug_allowed = (
                    self._active_interaction is None
                    or (
                        active_here
                        and self._active_interaction.kind in {
                            RoomInteractionKind.LIVE,
                            RoomInteractionKind.LOCAL_REFRESH,
                            RoomInteractionKind.AUXILIARY_READ,
                        }
                    )
                )
                item = QTreeWidgetItem(("", row.model_label, row.status.value, row.ip_address or "—", ""))
                item.setSizeHint(0, QSize(0, 42))
                item.setIcon(0, self._device_icon(row))
                item.setText(2, f"{self._status_cue(row)}  {row.status.value}")
                item.setForeground(2, QBrush(self._status_color(row)))
                if not self._is_expandable(row):
                    item.setDisabled(True)
                item.setData(0, Qt.UserRole, row.record_id)
                item.setData(0, Qt.UserRole + 1, self._is_expandable(row))
                if self._is_expandable(row):
                    projection = QTreeWidgetItem(("", "", "", "", ""))
                    projection.setFlags(projection.flags() & ~Qt.ItemIsSelectable)
                    item.addChild(projection)
                self.tree.addTopLevelItem(item)
                if self._is_expandable(row):
                    # Qt applies first-column spanning only after the item has
                    # joined its view; otherwise an item widget may remain
                    # constrained to the icon column on some platform styles.
                    projection.setFirstColumnSpanned(True)
                    presentation = RoomReadOnlyPresentation(
                        row,
                        request_local_refresh=lambda record_id=row.record_id: self.localRefreshRequested.emit(record_id),
                        request_auxiliary=(
                            lambda action, record_id=row.record_id: self.auxiliaryRequested.emit(record_id, action)
                        ),
                        request_codec_control=(
                            lambda operation, value=None, record_id=row.record_id: self.codecControlRequested.emit(
                                record_id, operation, value
                            )
                        ),
                        request_mutation=(
                            lambda outlet, command, record_id=row.record_id: self.pduMutationRequested.emit(record_id, outlet, command)
                        ),
                        request_bulk_mutation=(
                            lambda command, record_id=row.record_id: self.pduBulkMutationRequested.emit(record_id, command)
                        ),
                        request_matrix_route=(
                            lambda output, input_number, record_id=row.record_id: self.matrixRouteRequested.emit(record_id, output, input_number)
                        ),
                        request_debug=lambda record_id=row.record_id: self.debugRequested.emit(record_id),
                        local_refresh_allowed=actions_allowed,
                        auxiliary_allowed=actions_allowed,
                        mutation_allowed=actions_allowed,
                        debug_allowed=debug_allowed,
                        live_here=live_here,
                        audio_selection=(
                            self._audio_selection[1:]
                            if self._audio_selection is not None
                            and self._audio_selection[0] == row.record_id
                            else None
                        ),
                        audio_channel_selected=(
                            lambda section, oid, record_id=row.record_id: self._select_audio_channel(
                                record_id, section, oid
                            )
                        ),
                        audio_popup=self._audio_popup,
                        parent=self.tree,
                    )
                    presentation.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                    self.tree.setItemWidget(
                        projection,
                        0,
                        presentation,
                    )
                self._by_record[row.record_id] = item
            self.tree.doItemsLayout()
            if expanded_record_id and expanded_record_id in self._by_record:
                item = self._by_record[expanded_record_id]
                if item.data(0, Qt.UserRole + 1):
                    item.setExpanded(True)
            self.tree.doItemsLayout()
            if viewport is not None:
                self._restore_viewport(viewport)
        finally:
            self._changing = False
        self._audio_popup.finish_render(session)
        self.tree.setEnabled(not self._interaction_locked)

    def _render_network(self, session: RoomDiagnosticSession) -> None:
        self._network_restoring = True
        self.network_tree.clear()
        known: dict[str, list] = {}
        unknown: list = []
        for record in sorted(session.records, key=lambda item: item.record_id):
            if record.switch_ip_address is None and record.switch_port is None:
                continue
            if record.switch_ip_address is None:
                unknown.append(record)
            else:
                known.setdefault(record.switch_ip_address, []).append(record)
        self.network_card.set_title(f"Сетевые подключения ({len(known) + len(unknown)} коммутаторов)")
        self._network_expanded_switches.intersection_update(known)
        for switch_ip, records in sorted(known.items()):
            ports = list(dict.fromkeys(record.switch_port for record in records if record.switch_port is not None))
            parent = QTreeWidgetItem((f"SW ({switch_ip})", ", ".join(ports) or "Нет данных", str(len(records))))
            parent.setData(0, Qt.UserRole, switch_ip)
            for record in records:
                label = record.diagnostic_model or record.record_id
                child = QTreeWidgetItem((str(label), record.switch_port or "Нет данных", ""))
                child.setFlags(child.flags() & ~Qt.ItemIsSelectable)
                parent.addChild(child)
            self.network_tree.addTopLevelItem(parent)
            parent.setExpanded(switch_ip in self._network_expanded_switches)
        for record in unknown:
            self.network_tree.addTopLevelItem(
                QTreeWidgetItem(("Коммутатор не определён", record.switch_port or "Нет данных", "1"))
            )
        if self.network_tree.topLevelItemCount() == 0:
            self.network_tree.addTopLevelItem(QTreeWidgetItem(("Нет данных о сетевых подключениях", "", "")))
        self._network_restoring = False

    def _network_item_expanded(self, item: QTreeWidgetItem) -> None:
        if not self._network_restoring:
            key = item.data(0, Qt.UserRole)
            if key:
                self._network_expanded_switches.add(str(key))

    def _network_item_collapsed(self, item: QTreeWidgetItem) -> None:
        if not self._network_restoring:
            key = item.data(0, Qt.UserRole)
            if key:
                self._network_expanded_switches.discard(str(key))

    def _capture_viewport(self):
        scroll_bar = self.tree.verticalScrollBar()
        item = self.tree.itemAt(QPoint(0, 0))
        while item is not None and item.parent() is not None:
            item = item.parent()
        record_id = item.data(0, Qt.UserRole) if item is not None else None
        offset = self.tree.visualItemRect(item).top() if item is not None else 0
        return (record_id, offset, scroll_bar.value())

    def _restore_viewport(self, viewport) -> None:
        record_id, offset, fallback = viewport
        scroll_bar = self.tree.verticalScrollBar()
        value = fallback
        item = self._by_record.get(record_id)
        if item is not None:
            value = scroll_bar.value() + self.tree.visualItemRect(item).top() - offset
        scroll_bar.setValue(max(scroll_bar.minimum(), min(scroll_bar.maximum(), value)))

    def set_interaction_locked(self, locked: bool) -> None:
        """Block accordion changes while an exclusive row operation owns I/O."""
        self._interaction_locked = locked

    def clear_presentation(self) -> None:
        """Forget displayed room data when application authority is revoked.

        This is intentionally presentation-only: it neither resolves inventory nor
        starts, stops, or otherwise owns device I/O.
        """
        self.tree.stop_smooth_scroll()
        self._audio_popup.revoke()
        self._presentation_identity = None
        self._network_expanded_switches.clear()
        self._changing = True
        try:
            self.tree.clear()
            self.network_tree.clear()
            self.room_name_label.clear()
            self.vip_badge.setVisible(False)
            self.room_header.clear()
            self.room_warranty_label.clear()
            self.occupancy_label.clear()
            self.global_status.clear()
            self._by_record.clear()
            self._session = None
            self._audio_selection_context = None
            self._audio_selection = None
            self._active_interaction = None
            self._active_interaction_retiring = False
            self._interaction_locked = False
        finally:
            self._changing = False
        self.tree.setEnabled(True)

    def _select_audio_channel(self, record_id: str, section: str, oid: str) -> None:
        """Remember only a safe local visual identity and rebuild its row."""
        if self._session is None or self._audio_selection_context != self._session.identity:
            return
        self._audio_selection = (record_id, section, oid)
        self.render(self._session)

    def _prune_audio_selection(self, session: RoomDiagnosticSession) -> None:
        if self._audio_selection is None:
            return
        record_id, section, oid = self._audio_selection
        row = next((candidate for candidate in session.rows if candidate.record_id == record_id), None)
        if row is None or not _audio_channel_exists(row.accepted_snapshot, section, oid):
            self._audio_selection = None

    def set_active_interaction(self, context, *, retiring: bool = False) -> None:
        """Render controls from coordinator authority, never widget identity."""
        self._active_interaction = context
        self._active_interaction_retiring = retiring

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

    def _device_icon(self, row):
        screen = row.capability.screen_key if row.capability is not None else ""
        pixmap = {
            "codec": QStyle.SP_MediaPlay,
            "matrix": QStyle.SP_ComputerIcon,
            "pdu": QStyle.SP_DriveFDIcon,
            "audio_dsp": QStyle.SP_MediaVolume,
        }.get(screen, QStyle.SP_FileIcon)
        return self.style().standardIcon(pixmap)

    @staticmethod
    def _status_cue(row) -> str:
        if row.status is DeviceRowStatus.CONNECTED:
            return "✓"
        if row.status in {DeviceRowStatus.FAILED, DeviceRowStatus.DEGRADED}:
            return "!"
        if row.status in {DeviceRowStatus.UNSUPPORTED, DeviceRowStatus.MISSING_IP, DeviceRowStatus.AMBIGUOUS_IP}:
            return "—"
        return "…"

    @staticmethod
    def _status_color(row):
        if row.status is DeviceRowStatus.CONNECTED:
            return QColor("#24A85A")
        if row.status in {DeviceRowStatus.FAILED, DeviceRowStatus.DEGRADED}:
            return QColor("#E05260")
        if row.status in {DeviceRowStatus.UNSUPPORTED, DeviceRowStatus.MISSING_IP, DeviceRowStatus.AMBIGUOUS_IP}:
            return QColor("#6F7B8A")
        return QColor("#F59E0B")

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
        if self._changing or self._interaction_locked or item.parent() is not None:
            return
        if not item.data(0, Qt.UserRole + 1):
            return
        item.setExpanded(not item.isExpanded())

    def _accordion_expanded(self, item: QTreeWidgetItem) -> None:
        if self._changing or item.parent() is not None:
            return
        if self._interaction_locked:
            self._changing = True
            try:
                item.setExpanded(False)
            finally:
                self._changing = False
            return
        self._changing = True
        try:
            for index in range(self.tree.topLevelItemCount()):
                other = self.tree.topLevelItem(index)
                if other is not item:
                    other.setExpanded(False)
            if self._session is not None:
                self._audio_popup.revoke_unless_record(item.data(0, Qt.UserRole))
                self._session.expanded_record_id = item.data(0, Qt.UserRole)
                self.rowExpanded.emit(self._session.expanded_record_id)
        finally:
            self._changing = False

    def _accordion_collapsed(self, item: QTreeWidgetItem) -> None:
        if self._changing or item.parent() is not None:
            return
        if self._session is not None and self._session.expanded_record_id == item.data(0, Qt.UserRole):
            record_id = self._session.expanded_record_id
            self._audio_popup.revoke_for_record(record_id)
            self._session.expanded_record_id = None
            self.rowCollapsed.emit(record_id)


def _indexed_value(values: Any, input_number: int) -> Any:
    if isinstance(values, Mapping):
        return values.get(input_number, values.get(str(input_number), "—"))
    if isinstance(values, (list, tuple)) and input_number - 1 < len(values):
        return values[input_number - 1]
    return "—"


def normalize_matrix_presentation(snapshot: Any) -> list[tuple[Any, Any, Any, Any, Any]]:
    """Return truthful Matrix rows in the approved semantic column order."""
    source = snapshot if isinstance(snapshot, Mapping) else {}
    inputs = source.get("inputs_num")
    if not isinstance(inputs, int) or inputs < 1:
        return []
    names = source.get("input_names") or ()
    signals = source.get("signal_status") or {}
    hdcp_present = source.get("hdcp_present") or ()
    current = source.get("current_connection")
    rows = []
    for number in range(1, inputs + 1):
        signal = _indexed_value(signals, number)
        if isinstance(signal, Mapping):
            present = signal.get("has_signal")
            signal = "есть" if present is True else "нет сигнала" if present is False else "Нет данных"
        else:
            signal = "Нет данных"
        hdcp = _indexed_value(hdcp_present, number)
        hdcp = "есть" if hdcp is True else "нет" if hdcp is False else "Нет данных"
        name = _indexed_value(names, number)
        name = name if name not in (None, "", "—") else "Нет данных"
        route = "активен" if current == number else "не выбран" if isinstance(current, int) else "Нет данных"
        rows.append((number, signal, hdcp, name, route))
    return rows


class MatrixRoutingTable(QTableWidget):
    """Room-only Matrix table with stable approved semantic proportions."""

    column_ratios = (8, 19, 17, 27, 29)

    def __init__(self, parent=None):
        super().__init__(0, len(self.column_ratios), parent)
        header = self.horizontalHeader()
        for column in range(self.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.Fixed)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.apply_column_widths()

    def apply_column_widths(self) -> None:
        width = max(1, self.viewport().width())
        remaining = width
        for column, ratio in enumerate(self.column_ratios):
            column_width = width * ratio // 100 if column < self.columnCount() - 1 else remaining
            self.setColumnWidth(column, column_width)
            remaining -= column_width


class RoomPduOutletTable(QTableWidget):
    """Five-column PDU table with fixed presentation proportions."""

    column_ratios = (9, 31, 12, 20, 28)

    def __init__(self, parent=None):
        super().__init__(0, len(self.column_ratios), parent)
        header = self.horizontalHeader()
        for column in range(self.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.Fixed)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.apply_column_widths()

    def apply_column_widths(self) -> None:
        width = max(1, self.viewport().width())
        remaining = width
        for column, ratio in enumerate(self.column_ratios):
            column_width = width * ratio // 100 if column < self.columnCount() - 1 else remaining
            self.setColumnWidth(column, column_width)
            remaining -= column_width


def _room_pdu_display_value(value: Any) -> str:
    if value is None:
        return "—"
    text = str(value).strip()
    return text or "—"


def _room_pdu_outlet_sort_key(value: Any) -> tuple[int, int | str]:
    if isinstance(value, int) and not isinstance(value, bool):
        return (0, value)
    try:
        return (0, int(str(value)))
    except (TypeError, ValueError):
        return (1, _room_pdu_display_value(value))


def _room_pdu_status_indicator(value: Any, parent: QWidget) -> StatusIndicator:
    normalized = str(value).strip().lower()
    if normalized in {"on", "1", "true"}:
        state, text = "success", "ON"
    elif normalized in {"off", "0", "false"}:
        state, text = "danger", "OFF"
    else:
        state, text = "inactive", "—"
    indicator = StatusIndicator(state, text, show_text=True, parent=parent)
    indicator.setAlignment(Qt.AlignCenter)
    return indicator


def _matrix_indicator_item(value: Any, *, positive: str, inactive: str) -> QTableWidgetItem:
    """Render a matrix state as an icon while retaining its accessible meaning."""
    item = QTableWidgetItem()
    item.setData(Qt.UserRole, value)
    item.setTextAlignment(Qt.AlignCenter)
    item.setToolTip(str(value))
    if value == positive:
        item.setText("●")
        item.setForeground(QBrush(QColor("#24A85A")))
    elif value == inactive:
        item.setText("○")
        item.setForeground(QBrush(QColor("#6F7B8A")))
    else:
        item.setText("●")
        item.setForeground(QBrush(QColor("#6F7B8A")))
    return item


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
            if _has_current_numeric_meter(channel):
                value = f"{channel.get('dbfs', '—')} dBFS"
                if channel.get("state") not in (None, ""):
                    value += f" ({channel['state']})"
            else:
                detail = " · ".join(
                    str(channel[key])
                    for key in ("outcome", "error_code")
                    if channel.get(key) not in (None, "")
                )
                value = "— dBFS" + (f" ({detail})" if detail else "")
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


METER_SEGMENT_COUNT = 20


def quantize_meter_segments(normalized: Any) -> int:
    """Return the approved 20-segment, round-half-up visual fill."""
    try:
        value = float(normalized)
    except (TypeError, ValueError):
        value = 0.0
    value = max(0.0, min(1.0, value))
    return floor(value * METER_SEGMENT_COUNT + 0.5)


def _is_finite_real(value: Any) -> bool:
    """Accept only canonical numeric evidence, never bool/NaN/infinity."""
    return isinstance(value, Real) and not isinstance(value, bool) and isfinite(float(value))


def _has_current_numeric_meter(channel: Mapping[str, Any]) -> bool:
    return (
        channel.get("available") is True
        and _is_finite_real(channel.get("dbfs"))
        and _is_finite_real(channel.get("normalized"))
    )


def _is_numeric_meter_evidence(channel: Mapping[str, Any]) -> bool:
    """Unavailable evidence is valid; current levels require both numeric fields."""
    return channel.get("available") is False or _has_current_numeric_meter(channel)


def _has_numeric_meter_presentation(snapshot: Mapping[str, Any]) -> bool:
    for meter_section in snapshot.get("meter_sections") or ():
        if not isinstance(meter_section, Mapping):
            continue
        for channel in meter_section.get("channels") or ():
            if isinstance(channel, Mapping) and _is_numeric_meter_evidence(channel):
                return True
    return False


def meter_segment_zone(index: int) -> str:
    """Classify a physical scale segment, independent of channel dBFS."""
    midpoint_dbfs = -60 + (index + 0.5) * 3.6
    if midpoint_dbfs < -18:
        return "success"
    if midpoint_dbfs < -6:
        return "warning"
    return "elevated"


def _audio_channel_exists(snapshot: Any, section: str, oid: str) -> bool:
    if not isinstance(snapshot, Mapping):
        return False
    for meter_section in snapshot.get("meter_sections") or ():
        if not isinstance(meter_section, Mapping) or str(meter_section.get("title") or "") != section:
            continue
        for channel in meter_section.get("channels") or ():
            if isinstance(channel, Mapping) and str(channel.get("oid")) == oid:
                return True
    return False


def _selected_audio_channel_context(snapshot: Mapping[str, Any], selection) -> str | None:
    if selection is None:
        return None
    selected_section, selected_oid = selection
    for meter_section in snapshot.get("meter_sections") or ():
        if not isinstance(meter_section, Mapping):
            continue
        title = str(meter_section.get("title") or "Измерения")
        if title != selected_section:
            continue
        for channel in meter_section.get("channels") or ():
            if isinstance(channel, Mapping) and str(channel.get("oid")) == selected_oid:
                return f"{title} · {channel.get('name') or '—'}"
    return None


def _audio_meter_label(section: str, channel_name: Any) -> str:
    """Use the compact ordinal above a DMP meter without changing its identity."""
    name = str(channel_name or "—")
    prefix = "Input " if section == "Inputs" else "Output " if section == "Outputs" else ""
    return name[len(prefix):] if prefix and name.startswith(prefix) else name


@dataclass(frozen=True)
class AudioPopupTarget:
    """Safe, presentation-only identity for one current Audio channel."""

    room_identity: object
    record_id: str
    section: str
    oid: str


class AudioPopupCoordinator(QWidget):
    """One room-owned hover popup, independent from disposable meter widgets."""

    def __init__(self, parent: RoomDiagnosticTreeWidget):
        super().__init__(parent)
        self._room = parent
        self._session: RoomDiagnosticSession | None = None
        self._target: AudioPopupTarget | None = None
        self._sources: dict[AudioPopupTarget, AudioDspChannelColumn] = {}
        self._source_hover = False
        self._epoch = 0
        self._pending_hide_epoch: int | None = None
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(180)
        self._hide_timer.timeout.connect(self._hide_if_current)
        self.popup = AudioDspLocalControls("Канал", parent)
        self.popup.pointerEntered.connect(self.popup_entered)
        self.popup.pointerLeft.connect(self.popup_left)

    def begin_render(self, session: RoomDiagnosticSession, same_context: bool) -> None:
        # Incoming authoritative evidence is checked before the room tree clears
        # disposable sources.  A same-identity refresh cannot keep a popup whose
        # expanded row, Audio family, or exact channel is already obsolete.
        if not same_context or (
            self._target is not None and not self._target_is_current(session)
        ):
            self.revoke()
        self._session = session
        self._sources.clear()

    def register(self, record_id: str, section: str, oid: str, channel_name: str, source) -> None:
        if self._session is None:
            return
        target = AudioPopupTarget(self._session.identity, record_id, section, oid)
        self._sources[target] = source
        if target == self._target:
            self.popup.set_channel_name(channel_name)

    def finish_render(self, session: RoomDiagnosticSession) -> None:
        if self._target is None:
            return
        if not self._target_is_current(session) or self._target not in self._sources:
            self.revoke()
            return
        source = self._sources[self._target]
        # A retained hover fact is rechecked using the replacement source; old
        # QWidget references are never evidence across a render boundary.
        self._source_hover = self._cursor_over(source)
        if self._source_hover or self._cursor_over(self.popup):
            self._show_for_current_target()
        else:
            self.revoke()

    def enter_source(self, record_id: str, section: str, oid: str, channel_name: str, source) -> None:
        if self._session is None:
            return
        target = AudioPopupTarget(self._session.identity, record_id, section, oid)
        self._sources[target] = source
        if not self._target_is_current(self._session, target):
            return
        self._epoch += 1
        self._hide_timer.stop()
        self._pending_hide_epoch = None
        self._target = target
        self._source_hover = True
        self.popup.set_channel_name(channel_name)
        self._show_for_current_target()

    def leave_source(self, source) -> None:
        if self._target is None or self._sources.get(self._target) is not source:
            return
        self._source_hover = False
        if not self._cursor_over(self.popup):
            self._schedule_hide()

    def popup_entered(self) -> None:
        self._hide_timer.stop()
        self._pending_hide_epoch = None

    def popup_left(self) -> None:
        if not self._source_hover and not self._cursor_over(self._sources.get(self._target)):
            self._schedule_hide()

    def revoke_for_record(self, record_id: str | None) -> None:
        if self._target is not None and self._target.record_id == record_id:
            self.revoke()

    def revoke_unless_record(self, record_id: str) -> None:
        if self._target is not None and self._target.record_id != record_id:
            self.revoke()

    def revoke(self) -> None:
        self._epoch += 1
        self._hide_timer.stop()
        self.popup.hide()
        self._target = None
        self._source_hover = False

    def _schedule_hide(self) -> None:
        if self._target is not None:
            self._pending_hide_epoch = self._epoch
            self._hide_timer.start()

    def _hide_if_current(self) -> None:
        # The timer belongs to this coordinator; entering another scale increments
        # the epoch and stops it before the old target can affect the new one.
        if (
            self._pending_hide_epoch != self._epoch
            or self._target is None
            or self._source_hover
            or self._cursor_over(self.popup)
        ):
            return
        self.revoke()

    def _target_is_current(self, session: RoomDiagnosticSession, target=None) -> bool:
        target = target or self._target
        if target is None or target.room_identity != session.identity:
            return False
        if session.expanded_record_id != target.record_id:
            return False
        row = next((row for row in session.rows if row.record_id == target.record_id), None)
        return bool(
            row is not None
            and row.capability is not None
            and row.capability.screen_key == "audio_dsp"
            and _audio_channel_exists(row.accepted_snapshot, target.section, target.oid)
        )

    @staticmethod
    def _cursor_over(widget) -> bool:
        return bool(widget is not None and widget.isVisible() and widget.rect().contains(widget.mapFromGlobal(QCursor.pos())))

    def _show_for_current_target(self) -> None:
        if self._target is None:
            return
        source = self._sources.get(self._target)
        if source is None or not source.isVisible():
            return
        popup_size = self.popup.sizeHint()
        origin = source.mapToGlobal(QPoint(source.width() + 8, max(0, (source.height() - popup_size.height()) // 2)))
        self.popup.move(origin)
        self.popup.show()
        self.popup.raise_()


class AudioDspChannelColumn(QFrame):
    """A click-only local DMP channel projection with no device authority."""

    selected = pyqtSignal(str, str)

    def __init__(self, section: str, channel: Mapping[str, Any], is_selected: bool, coordinator=None, record_id=None, parent=None):
        super().__init__(parent)
        self._section = section
        self._oid = str(channel.get("oid"))
        self._channel_name = str(channel.get("name") or "Канал")
        self._coordinator = coordinator
        self._record_id = record_id
        self.setObjectName("roomAudioDspChannel")
        self.setProperty("audioSelected", is_selected)
        self.setProperty("presentationOnly", True)
        self.setCursor(Qt.PointingHandCursor)
        is_output = section == "Outputs"
        self.setMinimumWidth(62 if is_output else 44)
        self.setMaximumWidth(66 if is_output else 52)
        self.setAccessibleName(
            f"{channel.get('name') or 'Канал'}" + (", Выбрано" if is_selected else "")
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 4, 3, 4)
        layout.setSpacing(2)
        label = QLabel(_audio_meter_label(section, channel.get("name")), self)
        label.setObjectName("roomAudioDspChannelLabel")
        label.setAlignment(Qt.AlignHCenter)
        label.setWordWrap(not is_output)
        layout.addWidget(label)
        track = QWidget(self)
        track.setObjectName("roomAudioDspMeterTrack")
        is_current_numeric = _has_current_numeric_meter(channel)
        track.setProperty("meterAvailable", channel.get("available") is True)
        track.setProperty("numericMeterValid", is_current_numeric)
        track_layout = QVBoxLayout(track)
        track_layout.setContentsMargins(0, 0, 0, 0)
        track_layout.setSpacing(2)
        filled = quantize_meter_segments(channel.get("normalized")) if is_current_numeric else 0
        for index in range(METER_SEGMENT_COUNT - 1, -1, -1):
            segment = QFrame(track)
            segment.setObjectName("roomAudioDspMeterSegment")
            segment.setFixedHeight(6)
            segment.setProperty("meterFilled", index < filled)
            segment.setProperty("meterZone", meter_segment_zone(index))
            segment.setProperty("segmentIndex", index)
            track_layout.addWidget(segment)
        layout.addWidget(track, 1, Qt.AlignHCenter)
        if self._coordinator is not None and self._record_id is not None:
            self._coordinator.register(self._record_id, self._section, self._oid, self._channel_name, self)
        value = QLabel(self)
        value.setObjectName("roomAudioDspDbfs")
        value.setAlignment(Qt.AlignHCenter)
        value.setWordWrap(True)
        if is_current_numeric:
            value.setText(f"{channel['dbfs']} dBFS")
        else:
            value.setText("— dBFS")
            detail_parts = [str(channel[key]) for key in ("outcome", "error_code") if channel.get(key) not in (None, "")]
            if detail_parts:
                detail_text = " · ".join(detail_parts)
                detail = QLabel(detail_text.replace("_", "_\u200b"), self)
                detail.setObjectName("roomAudioDspUnavailableDetail")
                detail.setAlignment(Qt.AlignHCenter)
                detail.setWordWrap(True)
                detail.setToolTip(detail_text)
                layout.addWidget(detail)
        layout.addWidget(value)
        if is_selected:
            cue = QLabel("Выбрано", self)
            cue.setObjectName("roomAudioDspSelectionCue")
            cue.setAlignment(Qt.AlignHCenter)
            layout.addWidget(cue)

    def enterEvent(self, event) -> None:
        if self._coordinator is not None and self._record_id is not None:
            self._coordinator.enter_source(self._record_id, self._section, self._oid, self._channel_name, self)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self._coordinator is not None:
            self._coordinator.leave_source(self)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.selected.emit(self._section, self._oid)
            event.accept()
            return
        super().mousePressEvent(event)


class AudioDspLocalControls(QFrame):
    """A deliberately disabled, local-only visual affordance for one meter."""

    pointerEntered = pyqtSignal()
    pointerLeft = pyqtSignal()

    def __init__(self, channel_name: str, parent=None):
        super().__init__(parent)
        self.setObjectName("roomAudioDspLocalControls")
        self.setProperty("presentationOnly", True)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedWidth(176)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        self._title = QLabel(channel_name, self)
        self._title.setObjectName("roomAudioDspLocalControlsTitle")
        self._title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._title)
        for text, name in (
            ("−", "roomAudioDspGainDown"),
            ("— / Нет данных", "roomAudioDspGainValue"),
            ("+", "roomAudioDspGainUp"),
            ("Mute", "roomAudioDspMute"),
        ):
            button = QPushButton(text, self)
            button.setObjectName(name)
            button.setEnabled(False)
            button.setMinimumHeight(38)
            layout.addWidget(button)

    def set_channel_name(self, channel_name: str) -> None:
        self._title.setText(channel_name)

    def enterEvent(self, event) -> None:
        self.pointerEntered.emit()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.pointerLeft.emit()
        super().leaveEvent(event)


class AudioDspMeterPresentation(QWidget):
    """Focused room-only projection for accepted numeric ``meter_sections``."""

    def __init__(self, snapshot: Mapping[str, Any], selection, on_select, coordinator=None, record_id=None, parent=None):
        super().__init__(parent)
        self.setObjectName("roomAudioDspMeters")
        self.setProperty("presentationOnly", True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        selected_label = _selected_audio_channel_context(snapshot, selection) or "Выберите канал"
        # Retain a stable presentation-only identity target without reserving a
        # permanent control strip below the meters.
        context = QLabel(selected_label, self)
        context.setObjectName("roomAudioDspSelectedChannelContext")
        context.setVisible(False)
        layout.addWidget(context)
        sections_layout = QHBoxLayout()
        sections_layout.setSpacing(8)
        for ordinal, meter_section in enumerate(snapshot.get("meter_sections") or ()):
            if not isinstance(meter_section, Mapping):
                continue
            title = str(meter_section.get("title") or "Измерения")
            card = SectionCard(title, "∿", self)
            card.setObjectName("roomAudioDspMeterSection")
            card.setProperty("meterSection", title)
            channel_layout = QHBoxLayout()
            channel_layout.setContentsMargins(0, 0, 0, 0)
            channel_layout.setSpacing(4)
            for channel in meter_section.get("channels") or ():
                if not isinstance(channel, Mapping):
                    continue
                column = AudioDspChannelColumn(
                    title,
                    channel,
                    selection == (title, str(channel.get("oid"))),
                    coordinator,
                    record_id,
                    card,
                )
                column.selected.connect(on_select)
                channel_layout.addWidget(column)
            card.body_layout.addLayout(channel_layout)
            sections_layout.addWidget(card, 3 if ordinal == 0 else 2)
        layout.addLayout(sections_layout)


def _audio_device_info_card(source: Any, parent=None) -> SectionCard:
    """Render only scalar, accepted device information in the dashboard column."""
    card = SectionCard("Общая информация", "ⓘ", parent)
    card.setObjectName("roomAudioDspInfo")
    card.body_layout.setAlignment(Qt.AlignTop)
    form = QGridLayout()
    form.setContentsMargins(0, 2, 0, 0)
    form.setHorizontalSpacing(14)
    form.setVerticalSpacing(10)
    form.setColumnMinimumWidth(0, 116)
    form.setColumnStretch(0, 0)
    form.setColumnStretch(1, 1)
    source = source if isinstance(source, Mapping) else {}
    labels = {
        "model": "Модель",
        "ip_address": "IP-адрес",
        "firmware": "Версия прошивки",
        "mac": "MAC адрес",
    }
    preferred = tuple(labels)
    seen = set()
    for key in preferred + tuple(key for key in source if key not in preferred):
        if key in seen or key not in source or str(key).startswith("_"):
            continue
        value = source[key]
        if isinstance(value, (Mapping, list, tuple)):
            continue
        seen.add(key)
        row = form.rowCount()
        name = QLabel(labels.get(str(key), str(key)), card)
        name.setObjectName("roomAudioDspInfoLabel")
        value_label = QLabel(str(value), card)
        value_label.setObjectName("roomAudioDspInfoValue")
        value_label.setWordWrap(True)
        form.addWidget(name, row, 0)
        form.addWidget(value_label, row, 1)
    if not seen:
        form.addWidget(QLabel("Статус", card), 0, 0)
        form.addWidget(QLabel("—", card), 0, 1)
    card.body_layout.addLayout(form)
    card.body_layout.addStretch(1)
    return card


class AudioDspDashboardPresentation(QWidget):
    """Compact horizontal DMP dashboard with no new action authority."""

    def __init__(self, snapshot: Mapping[str, Any], source: Any, selection, on_select, coordinator=None, record_id=None, actions=(), parent=None):
        super().__init__(parent)
        self.setObjectName("roomAudioDspDashboard")
        self.setProperty("presentationOnly", True)
        self._dashboard_layout = QGridLayout(self)
        self._dashboard_layout.setContentsMargins(0, 0, 0, 0)
        self._dashboard_layout.setSpacing(8)
        self._information = _audio_device_info_card(source, self)
        self._meters = AudioDspMeterPresentation(snapshot, selection, on_select, coordinator, record_id, self)
        quick_actions = SectionCard("Быстрые действия", "ϟ", self)
        quick_actions.setObjectName("roomAudioDspQuickActions")
        for action in actions:
            quick_actions.body_layout.addWidget(action)
        if not actions:
            unavailable = QLabel("Нет доступных действий", quick_actions)
            unavailable.setObjectName("roomAudioDspNoQuickActions")
            unavailable.setWordWrap(True)
            quick_actions.body_layout.addWidget(unavailable)
        quick_actions.body_layout.addStretch(1)
        self._quick_actions = quick_actions
        self._compact_layout = None
        self._apply_responsive_layout()

    @staticmethod
    def _repolish(widget) -> None:
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)

    def _apply_responsive_layout(self) -> None:
        compact = self.width() < 1200
        if compact == self._compact_layout:
            return
        self._compact_layout = compact
        for card in (self._information, self._quick_actions):
            card.setProperty("audioCompact", compact)
            self._repolish(card)
        if compact:
            self._dashboard_layout.addWidget(self._information, 0, 0)
            self._dashboard_layout.addWidget(self._quick_actions, 0, 1)
            self._dashboard_layout.addWidget(self._meters, 1, 0, 1, 2)
            self._dashboard_layout.setColumnStretch(0, 1)
            self._dashboard_layout.setColumnStretch(1, 1)
            self._dashboard_layout.setColumnStretch(2, 0)
        else:
            self._dashboard_layout.addWidget(self._information, 0, 0)
            self._dashboard_layout.addWidget(self._meters, 0, 1)
            self._dashboard_layout.addWidget(self._quick_actions, 0, 2)
            self._dashboard_layout.setColumnStretch(0, 2)
            self._dashboard_layout.setColumnStretch(1, 6)
            self._dashboard_layout.setColumnStretch(2, 2)

    def resizeEvent(self, event) -> None:
        self._apply_responsive_layout()
        super().resizeEvent(event)

    def wheelEvent(self, event) -> None:
        """Keep the room tree scrollable while the pointer is above a meter."""
        owner = self.parentWidget()
        while owner is not None and not isinstance(owner, SmoothRoomTreeWidget):
            owner = owner.parentWidget()
        if owner is None:
            event.ignore()
            return
        scroll_bar = owner.verticalScrollBar()
        delta = event.angleDelta().y()
        if delta:
            steps = delta / 120
            target = max(scroll_bar.minimum(), min(scroll_bar.maximum(), round(scroll_bar.value() - steps * 42)))
            scroll_bar.setValue(target)
            event.accept()
            return
        event.ignore()


class RoomReadOnlyPresentation(QWidget):
    """Exact-row data projection with a deliberately narrow action request."""

    def __init__(self, row, *, request_local_refresh=None, request_auxiliary=None, request_codec_control=None, request_mutation=None, request_bulk_mutation=None, request_matrix_route=None, request_debug=None, local_refresh_allowed=True, auxiliary_allowed=True, mutation_allowed=True, debug_allowed=True, live_here=False, audio_selection=None, audio_channel_selected=None, audio_popup=None, parent=None):
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
        data = row.accepted_snapshot if row.accepted_snapshot is not None else row.partial_data
        screen_key = row.capability.screen_key if row.capability is not None else ""
        use_audio_dashboard = (
            screen_key == "audio_dsp"
            and isinstance(data, Mapping)
            and _has_numeric_meter_presentation(data)
        )
        use_matrix_dashboard = screen_key == "matrix"
        audio_actions = []
        refresh_button = None
        if screen_key not in {"pdu", "codec"}:
            refresh_button = QPushButton("Локальный опрос", self)
            refresh_button.setObjectName("roomLocalRefreshButton")
            refresh_button.setEnabled(
                bool(request_local_refresh)
                and local_refresh_allowed
                and row.status is DeviceRowStatus.CONNECTED
                and (row.network_actions_enabled or live_here)
                and not row.interaction_blocked
            )
            if request_local_refresh is not None:
                refresh_button.clicked.connect(request_local_refresh)
        is_codec_dashboard = screen_key == "codec"
        if use_audio_dashboard and refresh_button is not None:
            audio_actions.append(refresh_button)
        elif refresh_button is not None and not use_matrix_dashboard and not is_codec_dashboard:
            layout.addWidget(refresh_button)
        if screen_key not in {"pdu", "codec"}:
            debug_button = QPushButton("Отладка", self)
            debug_button.setObjectName("roomLocalDebugButton")
            debug_button.setEnabled(
                bool(request_debug) and debug_allowed and row.accepted_snapshot is not None
            )
            if request_debug is not None:
                debug_button.clicked.connect(request_debug)
            if use_audio_dashboard:
                audio_actions.append(debug_button)
            elif not use_matrix_dashboard:
                layout.addWidget(debug_button)
        if row.warnings:
            warnings = QLabel("Предупреждения: " + "; ".join(row.warnings), self)
            warnings.setObjectName("roomPresentationWarnings")
            warnings.setWordWrap(True)
            layout.addWidget(warnings)
        builder = {
            "codec": self._build_codec,
            "pdu": self._build_pdu,
            "matrix": self._build_matrix,
            "audio_dsp": self._build_audio,
        }.get(screen_key)
        if builder is not None:
            builder_kwargs = {
                "request_mutation": request_mutation,
                "request_bulk_mutation": request_bulk_mutation,
                "mutation_allowed": mutation_allowed,
            }
            if screen_key == "matrix":
                builder_kwargs.update(
                    request_local_refresh=request_local_refresh,
                    local_refresh_allowed=local_refresh_allowed,
                    request_matrix_route=request_matrix_route,
                    live_here=live_here,
                )
            if screen_key == "pdu":
                builder_kwargs.update(
                    request_local_refresh=request_local_refresh,
                    request_bulk_mutation=request_bulk_mutation,
                    local_refresh_allowed=local_refresh_allowed,
                    live_here=live_here,
                )
            if screen_key == "audio_dsp":
                builder_kwargs.update(
                    audio_selection=audio_selection,
                    audio_channel_selected=audio_channel_selected,
                    audio_popup=audio_popup,
                    record_id=row.record_id,
                    audio_actions=audio_actions,
                )
            if screen_key == "codec":
                builder_kwargs.update(
                    request_local_refresh=request_local_refresh,
                    request_auxiliary=request_auxiliary,
                    request_codec_control=request_codec_control,
                    local_refresh_allowed=local_refresh_allowed,
                    auxiliary_allowed=auxiliary_allowed,
                    live_here=live_here,
                )
            builder(layout, data, row, **builder_kwargs)
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

    def _build_codec(
        self, layout, data, row, *, request_local_refresh=None,
        request_auxiliary=None, request_codec_control=None,
        local_refresh_allowed=True, auxiliary_allowed=True, live_here=False, **_unused,
    ) -> None:
        """Build the fixed shared dashboard; widgets only publish safe intents."""
        source = data if isinstance(data, Mapping) else {}
        dashboard = QWidget(self)
        dashboard.setObjectName("roomCodecDashboard")
        dashboard.setMinimumHeight(286)
        dashboard.setMaximumHeight(326)
        dashboard.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cards = QHBoxLayout(dashboard)
        cards.setContentsMargins(0, 0, 0, 0)
        cards.setSpacing(10)

        state = SectionCard("Состояние", "ⓘ", dashboard)
        state.setObjectName("roomCodecStateCard")
        call = SectionCard("Вызов и презентация", "☎", dashboard)
        call.setObjectName("roomCodecCallCard")
        audio = SectionCard("Аудио", "♪", dashboard)
        audio.setObjectName("roomCodecAudioCard")
        history = SectionCard("Журнал вызовов", "=", dashboard)
        history.setObjectName("roomCodecHistoryCard")
        actions = SectionCard("Действия", "⚡", dashboard)
        actions.setObjectName("roomCodecActionsCard")
        for card in (state, call, audio, history, actions):
            card.setMinimumHeight(286)
            card.setMaximumHeight(326)
            card.layout().setContentsMargins(14, 10, 14, 12)
            card.layout().setSpacing(8)
            card.body_layout.setAlignment(Qt.AlignTop)

        missing = "Нет данных"
        self._codec_data_rows(state, source, (
            ("Модель", ("model", "Модель", "Модель кодеков"), False),
            ("MAC-адрес", ("mac_address", "mac", "MAC адрес", "MAC-адрес"), False),
            ("Серийный номер", ("serial_number", "serial", "Серийный номер"), False),
            ("Версия ПО", ("firmware", "Версия ПО", "software_version"), False, "multiline"),
            ("Микрофон", ("microphone_status", "mic_mute", "microphone_mute_state"), False),
            ("Камера", ("camera_status", "camera_mute", "camera_mute_state"), False),
        ), missing)
        state.body_layout.addStretch(1)
        call_projection = normalize_codec_call_projection(source, row.diagnostic_model)
        self._codec_data_rows(call, source, (
            ("Статус звонка", ("call_status", "Статус звонка"), False, "yes_no", call_projection.call_active),
            ("Презентация", ("presentation_status", "Статус презентации"), False, "yes_no", call_projection.presentation_active),
            ("Регистрация SIP/H.323", ("sip_registration", "SIP регистрация", "sip_status"), False, "registration", call_projection.registration_active),
        ), missing)
        call.body_layout.addStretch(1)

        projection = normalize_codec_audio_projection(source, row.diagnostic_model)
        meter_label = QLabel("Микрофон (уровень)", audio)
        meter_label.setObjectName("roomCodecMicrophoneLevelLabel")
        audio.body_layout.addWidget(meter_label)
        meter_supported = self._codec_microphone_meter_supported(row.diagnostic_model)
        meter_state = QLabel("", audio)
        meter_state.setObjectName("roomCodecMicrophoneMeterState")
        if meter_supported:
            meter = QProgressBar(audio)
            meter.setObjectName("roomCodecMicrophoneMeter")
            meter.setRange(0, 100)
            meter.setTextVisible(False)
            meter.setFixedHeight(10)
            level = self._codec_microphone_level(source)
            meter.setProperty("meterState", "available" if level is not None else "unavailable")
            meter.setValue(level or 0)
            meter_state.setText("" if level is not None else missing)
            audio.body_layout.addWidget(meter)
        else:
            meter_state.setText("Не поддерживается")
        audio.body_layout.addWidget(meter_state)
        audio.body_layout.addSpacing(8)
        controls_enabled = (
            row.status is DeviceRowStatus.CONNECTED
            and (row.network_actions_enabled or live_here)
            and not row.interaction_blocked
        )
        self._codec_audio_row(audio, "Громкость микрофона", projection.microphone_volume,
            projection.microphone_mute_state, "microphone_adjust", "microphone_mute",
            request_codec_control, controls_enabled,
            display_value=self._codec_volume_text(projection.microphone_volume))
        self._codec_audio_row(audio, "Громкость динамиков", projection.speaker_volume,
            projection.speaker_mute_state, "speaker_adjust", "speaker_mute",
            request_codec_control, controls_enabled,
            display_value=self._codec_volume_text(projection.speaker_volume_percent))
        audio.body_layout.addStretch(1)

        snapshot = getattr(row, "call_log_preview_snapshot", None)
        records = tuple(getattr(snapshot, "records", ()) or ())[:3]
        if not records:
            empty = QLabel(missing, history)
            empty.setObjectName("roomCodecCallLogEmpty")
            history.body_layout.addWidget(empty)
        for record in records:
            direction = self._codec_call_direction(record)
            entry = QWidget(history)
            entry.setObjectName("roomCodecCallLogPreview")
            entry.setMinimumHeight(52)
            entry_layout = QHBoxLayout(entry)
            entry_layout.setContentsMargins(0, 4, 0, 4)
            entry_layout.setSpacing(8)
            icon = QLabel(self._codec_call_direction_icon(direction), entry)
            icon.setObjectName("roomCodecCallDirectionIcon")
            icon.setProperty("direction", direction)
            icon.setAlignment(Qt.AlignCenter)
            icon.setFixedWidth(24)
            details = QWidget(entry)
            details_layout = QVBoxLayout(details)
            details_layout.setContentsMargins(0, 0, 0, 0)
            details_layout.setSpacing(1)
            title = QLabel(self._codec_call_direction_title(direction), details)
            title.setObjectName("roomCodecCallDirectionTitle")
            number = QLabel(getattr(record, "room_number", "") or missing, details)
            number.setObjectName("roomCodecCallNumber")
            details_layout.addWidget(title)
            details_layout.addWidget(number)
            timestamp = QLabel(getattr(record, "start_display", "") or missing, entry)
            timestamp.setObjectName("roomCodecCallTimestamp")
            timestamp.setFixedWidth(112)
            timestamp.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            entry_layout.addWidget(icon)
            entry_layout.addWidget(details, 1)
            entry_layout.addWidget(timestamp)
            history.body_layout.addWidget(entry)
        expand = QPushButton("Развернуть", history)
        expand.setObjectName("roomCallLogButton")
        expand.setMinimumHeight(34)
        expand.setEnabled(bool(request_auxiliary) and auxiliary_allowed and controls_enabled)
        if request_auxiliary is not None:
            expand.clicked.connect(lambda: request_auxiliary("call_log"))
        history.body_layout.addWidget(expand)
        history.body_layout.addStretch(1)

        refresh = QPushButton("Обновить статус", actions)
        refresh.setObjectName("roomLocalRefreshButton")
        refresh.setMinimumHeight(36)
        refresh.setEnabled(bool(request_local_refresh) and local_refresh_allowed and controls_enabled)
        if request_local_refresh is not None:
            refresh.clicked.connect(request_local_refresh)
        reboot = QPushButton("Перезагрузить устройство", actions)
        reboot.setObjectName("roomCodecRebootButton")
        reboot.setMinimumHeight(36)
        reboot.setEnabled(controls_enabled)
        if request_codec_control is not None:
            reboot.clicked.connect(lambda: request_codec_control("reboot", None))
        actions.body_layout.addWidget(refresh)
        actions.body_layout.addSpacing(10)
        actions.body_layout.addWidget(reboot)
        actions.body_layout.addStretch(1)

        # Pixel proportions measured from the supplied codec reference:
        # 370 / 267 / 268 / 383 / 276, excluding the uniform inter-card gaps.
        for card, weight in ((state, 370), (call, 267), (audio, 268), (history, 383), (actions, 276)):
            cards.addWidget(card, weight)
        layout.addWidget(dashboard)

    @staticmethod
    def _codec_microphone_level(source: Mapping[str, Any]) -> int | None:
        """Return only a finite accepted live meter level, scaled to percentage."""
        sample = source.get("live_microphone")
        if not isinstance(sample, Mapping) or sample.get("available") is False:
            return None
        raw = sample.get("normalized")
        if not isinstance(raw, Real) or isinstance(raw, bool) or not isfinite(raw):
            return None
        return max(0, min(100, round(raw * 100)))

    @staticmethod
    def _codec_microphone_meter_supported(model: str | None) -> bool:
        entry = dispatch_entry_for_model(model)
        return bool(entry is not None and entry.live_binding_key == "cloudlink_room_live")

    @classmethod
    def _codec_volume_text(cls, percentage: int | None) -> str:
        return f"{percentage}%" if percentage is not None else "Нет данных"

    @staticmethod
    def _codec_value(source: Mapping[str, Any], keys: tuple[str, ...]):
        for key in keys:
            value = source.get(key)
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def _codec_yes_no(value: Any, missing: str) -> str:
        if value is None:
            return missing
        if value is True:
            return "Да"
        if value is False:
            return "Нет"
        return missing

    @staticmethod
    def _codec_registration_presentation(value: Any) -> tuple[str, str]:
        if value is True:
            return "✓", "positive"
        if value is False or value is None:
            return ("✕", "negative") if value is False else ("—", "unavailable")
        return "—", "unavailable"

    @staticmethod
    def _codec_call_direction(record: Any) -> str:
        direction = getattr(record, "direction", CallDirection.UNKNOWN)
        if direction is CallDirection.INCOMING:
            return "incoming"
        if direction is CallDirection.OUTGOING:
            return "outgoing"
        return "unknown"

    @staticmethod
    def _codec_call_direction_icon(direction: str) -> str:
        return {"outgoing": "↗", "incoming": "↙"}.get(direction, "↔")

    @staticmethod
    def _codec_call_direction_title(direction: str) -> str:
        return {
            "outgoing": "Исходящий",
            "incoming": "Входящий",
        }.get(direction, "Направление неизвестно")

    def _codec_data_rows(self, card, source, rows, missing) -> None:
        for row_spec in rows:
            label, keys, status = row_spec[:3]
            presentation = row_spec[3] if len(row_spec) > 3 else "text"
            multiline = presentation == "multiline"
            has_normalized_value = len(row_spec) > 4
            row = QWidget(card)
            row.setObjectName(
                "roomCodecFirmwareRow" if multiline
                else "roomCodecStatusRow" if status else "roomCodecDataRow"
            )
            row.setMinimumHeight(48 if multiline else 28)
            row.setMaximumHeight(56 if multiline else 34)
            line = QHBoxLayout(row)
            line.setContentsMargins(0, 0, 0, 0)
            line.setSpacing(6)
            name = QLabel(label, row)
            name.setObjectName("roomCodecFieldLabel")
            value = row_spec[4] if has_normalized_value else self._codec_value(source, keys)
            if status:
                dot = QLabel("•", row)
                dot.setObjectName("roomCodecStatusDot")
                dot.setFixedSize(10, 10)
                # All current raw compatibility fields are informational;
                # model adapters may later provide an explicit typed class.
                dot.setProperty("semantic", "neutral" if value is not None else "unavailable")
                line.addWidget(dot)
            if presentation == "yes_no":
                value_text = self._codec_yes_no(value, missing)
            elif presentation == "registration":
                value_text, semantic = self._codec_registration_presentation(value)
            else:
                value_text = str(value) if value is not None else missing
            value_label = QLabel(value_text, row)
            value_label.setObjectName("roomCodecRegistrationValue" if presentation == "registration" else "roomCodecFieldValue")
            if presentation == "registration":
                value_label.setProperty("semantic", semantic)
            if multiline:
                value_label.setTextFormat(Qt.PlainText)
                value_label.setWordWrap(True)
            value_label.setToolTip(value_label.text())
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            line.addWidget(name, 42)
            line.addWidget(value_label, 58)
            card.body_layout.addWidget(row)

    def _codec_audio_row(
        self, card, title, volume, mute_state, adjust_operation, mute_operation, callback, enabled,
        *, display_value: str,
    ) -> None:
        row = QWidget(card)
        row.setObjectName(f"roomCodec{adjust_operation.title().replace('_', '')}Row")
        block = QVBoxLayout(row)
        block.setContentsMargins(0, 0, 0, 0)
        block.setSpacing(4)
        label = QLabel(title, row)
        label.setObjectName("roomCodecAudioLabel")
        line = QHBoxLayout()
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(5)
        minus = QPushButton("−", row)
        plus = QPushButton("+", row)
        for button, delta in ((minus, -1), (plus, 1)):
            button.setFixedSize(30, 30)
            button.setObjectName("roomCodecAudioMinus" if delta < 0 else "roomCodecAudioPlus")
            button.setEnabled(enabled)
            if callback is not None:
                button.clicked.connect(lambda _checked=False, change=delta: callback(adjust_operation, change))
        value = QLabel(display_value, row)
        value.setObjectName("roomCodecAudioValue")
        value.setMinimumWidth(38)
        value.setAlignment(Qt.AlignCenter)
        mute = QPushButton("🔇" if mute_state is CodecMuteState.MUTED else "🔊", row)
        mute.setObjectName("roomCodecAudioMute")
        mute.setFixedHeight(30)
        mute.setMinimumWidth(40)
        mute.setToolTip("Включить или выключить звук")
        mute.setEnabled(enabled)
        if callback is not None:
            mute.clicked.connect(lambda: callback(mute_operation, "toggle"))
        line.addWidget(minus)
        line.addWidget(value)
        line.addWidget(plus)
        line.addWidget(mute)
        line.addStretch(1)
        block.addWidget(label)
        block.addLayout(line)
        card.body_layout.addWidget(row)

    def _build_pdu(
        self,
        layout,
        data,
        row,
        *,
        request_local_refresh=None,
        request_mutation=None,
        request_bulk_mutation=None,
        local_refresh_allowed=True,
        mutation_allowed=True,
        live_here=False,
    ) -> None:
        dashboard = QWidget(self)
        dashboard.setObjectName("roomPduDashboard")
        dashboard.setMinimumHeight(360)
        dashboard.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        cards = QHBoxLayout(dashboard)
        cards.setContentsMargins(0, 0, 0, 0)
        cards.setSpacing(12)

        info = SectionCard("Основная информация", "ⓘ", dashboard)
        info.setObjectName("roomPduInfoCard")
        controls = SectionCard("Управление розетками", "⏻", dashboard)
        controls.setObjectName("roomPduOutletCard")
        controls.set_icon(_room_pdu_lightning_icon())
        for card in (info, controls):
            card.body_layout.setAlignment(Qt.AlignTop)
        cards.addWidget(info, 30)
        cards.addWidget(controls, 70)

        for label, value in (
            ("Модель", row.diagnostic_model),
            ("Серийный номер", getattr(row, "serial_number", None)),
            ("MAC-адрес", getattr(row, "mac_address", None)),
        ):
            parameter = ParameterRow(label, _room_pdu_display_value(value), info, compact=True)
            parameter.setObjectName("roomPduInfoRow")
            # The PDU information card is a compact label/value summary, not a
            # form: values should read as a right-aligned text column without
            # individual input-field chrome.
            parameter.value_display.setFrame(False)
            parameter.value_display.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            parameter.value_display.setProperty("pduInfoValue", True)
            parameter.value_display.setMinimumWidth(143)
            parameter.value_display.setMaximumWidth(468)
            info.add_widget(parameter)
        info.body_layout.addStretch(1)

        raw_outlets = data.get("outlets", ()) if isinstance(data, Mapping) else ()
        outlets = sorted(
            (outlet for outlet in raw_outlets if isinstance(outlet, Mapping)),
            key=lambda outlet: _room_pdu_outlet_sort_key(outlet.get("number")),
        )
        controls_enabled = (
            mutation_allowed
            and row.status is DeviceRowStatus.CONNECTED
            and (row.network_actions_enabled or live_here)
            and not row.interaction_blocked
        )
        refresh_enabled = (
            bool(request_local_refresh)
            and local_refresh_allowed
            and row.status is DeviceRowStatus.CONNECTED
            and (row.network_actions_enabled or live_here)
            and not row.interaction_blocked
        )
        actions = QWidget(controls)
        actions.setObjectName("roomPduTopActions")
        actions.setFixedHeight(26)
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)
        actions_layout.addStretch(1)
        refresh = SemanticButton("Обновить статус", "secondary", actions)
        refresh.setObjectName("roomPduRefreshButton")
        refresh.setEnabled(refresh_enabled)
        if request_local_refresh is not None:
            refresh.clicked.connect(lambda _checked=False: request_local_refresh())
        actions_layout.addWidget(refresh)
        bulk_on = SemanticButton("Включить всё", "success", actions)
        bulk_on.setObjectName("roomPduBulkOnButton")
        bulk_on.setEnabled(bool(request_bulk_mutation) and controls_enabled and bool(outlets))
        if request_bulk_mutation is not None:
            bulk_on.clicked.connect(lambda _checked=False: request_bulk_mutation("on"))
        actions_layout.addWidget(bulk_on)
        bulk_off = SemanticButton("Выключить всё", "danger", actions)
        bulk_off.setObjectName("roomPduBulkOffButton")
        bulk_off.setEnabled(bool(request_bulk_mutation) and controls_enabled and bool(outlets))
        if request_bulk_mutation is not None:
            bulk_off.clicked.connect(lambda _checked=False: request_bulk_mutation("off"))
        actions_layout.addWidget(bulk_off)
        controls.header_widget.layout().addWidget(actions)

        table = RoomPduOutletTable(controls)
        table.setObjectName("roomPduOutlets")
        table.setHorizontalHeaderLabels(("Розетка", "Имя розетки", "Состояние", "Текущая мощность", "Действия"))
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setMinimumHeight(286)
        table.setMaximumHeight(310)
        for outlet in outlets:
            index = table.rowCount()
            table.insertRow(index)
            outlet_number = outlet.get("number")
            number = _room_pdu_display_value(outlet_number)
            number_item = QTableWidgetItem(number)
            number_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(index, 0, number_item)
            table.setItem(index, 1, QTableWidgetItem(_room_pdu_display_value(outlet.get("name"))))
            table.setCellWidget(index, 2, _room_pdu_status_indicator(outlet.get("status"), table))
            power = QTableWidgetItem("—")
            power.setTextAlignment(Qt.AlignCenter)
            table.setItem(index, 3, power)
            action_cell = QWidget(table)
            action_cell.setObjectName("roomPduOutletActions")
            action_layout = QHBoxLayout(action_cell)
            action_layout.setContentsMargins(3, 1, 3, 1)
            action_layout.setSpacing(4)
            for command, label, role in (
                ("on", "Вкл", "success"),
                ("off", "Выкл", "danger"),
                ("reboot", "Перезапуск", "secondary"),
            ):
                button = SemanticButton(label, role, action_cell)
                button.setObjectName(f"roomPdu{command.title()}Button")
                button.setMinimumWidth(52 if command != "reboot" else 96)
                button.setFixedHeight(24)
                button.setEnabled(bool(request_mutation) and controls_enabled and isinstance(outlet_number, int))
                if request_mutation is not None and isinstance(outlet_number, int):
                    button.clicked.connect(
                        lambda _checked=False, number=outlet_number, action=command: request_mutation(number, action)
                    )
                action_layout.addWidget(button)
            action_layout.addStretch(1)
            table.setCellWidget(index, 4, action_cell)
            table.setRowHeight(index, 30)
        table.apply_column_widths()
        controls.add_widget(table)
        layout.addWidget(dashboard)

    def _build_matrix(self, layout, data, row, *, request_local_refresh=None, local_refresh_allowed=True, request_matrix_route=None, live_here=False, **_unused) -> None:
        source = data if isinstance(data, Mapping) else {}
        dashboard = QWidget(self)
        dashboard.setObjectName("roomMatrixDashboard")
        # A room matrix is the primary diagnostic surface.  Reserve a stable
        # inspection height instead of collapsing it to the content of a short
        # input list; the accordion rows naturally follow below it.
        dashboard.setMinimumHeight(360)
        dashboard.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        dashboard_layout = QHBoxLayout(dashboard)
        dashboard_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_layout.setSpacing(12)
        info = SectionCard("Общая информация", "▣", dashboard)
        info.body_layout.setAlignment(Qt.AlignTop)
        form = QFormLayout()
        form.setFormAlignment(Qt.AlignTop)
        form.setVerticalSpacing(8)
        no_data = "Нет данных"
        fields = (
            ("Модель", source.get("model")),
            ("MAC-адрес", source.get("mac_address")),
            ("Серийный номер", source.get("serial_number")),
            ("Версия прошивки", source.get("firmware")),
            ("Температура", source.get("temperature")),
            ("Время работы", source.get("uptime")),
        )
        for label, value in fields:
            value_label = QLabel(str(value) if value not in (None, "") else no_data, info)
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            form.addRow(label, value_label)
        info.body_layout.addLayout(form)
        # Keep the compact facts directly below the heading.  The additional
        # room-dashboard height belongs beneath the data, not between rows.
        info.body_layout.addStretch(1)
        card = SectionCard("Матрица (входы и коммутация)", "⇄", dashboard)
        table = MatrixRoutingTable(card)
        table.setObjectName("roomMatrixRouting")
        output_names = source.get("output_names")
        output_name = output_names[0] if isinstance(output_names, (tuple, list)) and output_names and output_names[0] else "Main Output"
        table.setHorizontalHeaderLabels(("№", "Сигнал", "HDCP", "Входы", str(output_name)))
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.verticalHeader().setVisible(False)
        route_allowed = (
            bool(request_matrix_route)
            and row.status is DeviceRowStatus.CONNECTED
            and (row.network_actions_enabled or live_here)
            and not row.interaction_blocked
            and not row.unconfirmed_after_command
            and not row.stale
            and isinstance(source.get("inputs_num"), int)
        )
        for values in normalize_matrix_presentation(source):
            index = table.rowCount()
            table.insertRow(index)
            for column, value in enumerate(values):
                if column == 1:
                    table.setItem(index, column, _matrix_indicator_item(
                        value, positive="есть", inactive="нет сигнала"
                    ))
                elif column == 4:
                    table.setItem(index, column, _matrix_indicator_item(
                        value, positive="активен", inactive="не выбран"
                    ))
                else:
                    item = QTableWidgetItem(str(value))
                    if column in {2, 3}:
                        item.setTextAlignment(Qt.AlignCenter)
                    table.setItem(index, column, item)
            if route_allowed and values[4] == "не выбран":
                route_item = table.item(index, 4)
                route_item.setToolTip("Выбрать вход для Main Output")
        def request_route(index, column):
            if column != 4 or not route_allowed:
                return
            values = normalize_matrix_presentation(source)
            if not (0 <= index < len(values)) or values[index][4] != "не выбран":
                return
            request_matrix_route(1, values[index][0])
        table.cellClicked.connect(request_route)
        table.apply_column_widths()
        card.add_widget(table)
        actions = SectionCard("Быстрые действия", "⚡", dashboard)
        refresh = QPushButton("Обновить статус", actions)
        refresh.setObjectName("roomMatrixRefreshButton")
        refresh.setEnabled(bool(request_local_refresh) and local_refresh_allowed and row.status is DeviceRowStatus.CONNECTED and (row.network_actions_enabled or live_here) and not row.interaction_blocked)
        if request_local_refresh is not None:
            refresh.clicked.connect(request_local_refresh)
        reboot = QPushButton("Перезагрузить устройство", actions)
        reboot.setObjectName("roomMatrixRebootButton")
        reboot.setEnabled(False)
        actions.add_widget(refresh)
        actions.add_widget(reboot)
        # Likewise, the action buttons stay adjacent to the heading.
        actions.body_layout.addStretch(1)
        dashboard_layout.addWidget(info, 25)
        dashboard_layout.addWidget(card, 53)
        dashboard_layout.addWidget(actions, 22)
        layout.addWidget(dashboard)

    def _build_audio(self, layout, data, row, *, audio_selection=None, audio_channel_selected=None, audio_popup=None, record_id=None, audio_actions=(), **_unused) -> None:
        source = data.get("device_info", data) if isinstance(data, Mapping) else data
        if isinstance(data, Mapping) and _has_numeric_meter_presentation(data):
            layout.addWidget(
                AudioDspDashboardPresentation(
                    data,
                    source,
                    audio_selection,
                    audio_channel_selected or (lambda *_args: None),
                    audio_popup,
                    record_id,
                    audio_actions,
                    self,
                )
            )
            return
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
