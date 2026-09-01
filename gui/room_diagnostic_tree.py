"""Presentation-only projection of a :mod:`core.room_diagnostic_tree` session."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from math import floor, isfinite
from numbers import Real

from PyQt5.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QSize, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import QAbstractItemView, QFormLayout, QFrame, QGridLayout, QHeaderView, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QStyle, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from .components import ParameterRow, SectionCard

from core.room_diagnostic_tree import DeviceRowStatus, RoomCycleStatus, RoomDiagnosticSession
from core.room_interaction import RoomInteractionKind
from core.call_activity import CallActivity


class SmoothRoomTreeWidget(QTreeWidget):
    """Room accordion with a restrained animated wheel scroll."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(10)
        self._scroll_animation = QPropertyAnimation(self.verticalScrollBar(), b"value", self)
        self._scroll_animation.setDuration(260)
        self._scroll_animation.setEasingCurve(QEasingCurve.InOutCubic)

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
    pduMutationRequested = pyqtSignal(str, int, str)
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
        upper.setFixedHeight(156)
        self.upper_cards = upper
        upper_layout = QHBoxLayout(upper)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.setSpacing(16)
        self.room_card = SectionCard("Комната", "⌂", upper)
        self.room_card.header_widget.setVisible(False)
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
        self.network_card = SectionCard("Сетевые подключения", "⌁", upper)
        self.network_card.header_widget.setVisible(False)
        self.network_tree = QTreeWidget(self.network_card)
        self.network_tree.setObjectName("roomNetworkConnections")
        self.network_tree.setColumnCount(2)
        self.network_tree.setHeaderLabels(("Коммутатор (IP) / Устройства", "Порт"))
        self.network_tree.setHeaderHidden(True)
        self.network_tree.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.network_tree.verticalScrollBar().setSingleStep(10)
        self.network_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.network_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.network_card.body_layout.addWidget(self.network_tree)
        upper_layout.addWidget(self.room_card, 1)
        upper_layout.addWidget(self.network_card, 1)
        layout.addWidget(upper)
        self.global_status = QLabel(self)
        self.global_status.setObjectName("roomDiagnosticGlobalStatus")
        self.tree = SmoothRoomTreeWidget(self)
        self.tree.setObjectName("roomDiagnosticRows")
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(("", "Устройство", "Статус подключения", "IP-адрес", "Действия"))
        self.tree.setIconSize(QSize(48, 48))
        self.tree.header().setSectionResizeMode(0, QHeaderView.Fixed)
        self.tree.header().resizeSection(0, 76)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(2, QHeaderView.Fixed)
        self.tree.header().resizeSection(2, 290)
        self.tree.header().setSectionResizeMode(3, QHeaderView.Fixed)
        self.tree.header().resizeSection(3, 180)
        self.tree.header().setSectionResizeMode(4, QHeaderView.ResizeToContents)
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

    def render(self, session: RoomDiagnosticSession) -> None:
        # `expanded_record_id` belongs to the application session.  Rendering a
        # progress callback must not replace a user's secondary selection with the
        # source row again.
        self._session = session
        if self._audio_selection_context != session.identity:
            self._audio_selection_context = session.identity
            self._audio_selection = None
        self._prune_audio_selection(session)
        expanded_record_id = session.expanded_record_id
        self._changing = True
        try:
            self.room_name_label.setText(session.room_name or "—")
            self.vip_badge.setVisible(session.room_vip is True)
            self.room_header.setText(f"Адрес: {session.room_address or '—'}")
            self.room_warranty_label.setText("Гарантия: Нет данных")
            self.global_status.setText(
                "Есть проблемы с соединением" if session.post_cycle_problem else session.status.value
            )
            occupied = any(row.call_activity is CallActivity.ACTIVE and not row.stale for row in session.rows)
            self.occupancy_label.setText(f"Занятость: {'Занято' if occupied else 'Нет данных'}")
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
                item = QTreeWidgetItem(("", row.model_label, row.status.value, row.ip_address or "—", "⋯"))
                item.setSizeHint(0, QSize(0, 64))
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
                        request_mutation=(
                            lambda outlet, command, record_id=row.record_id: self.pduMutationRequested.emit(record_id, outlet, command)
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
        finally:
            self._changing = False
        self.tree.setEnabled(not self._interaction_locked)

    def _render_network(self, session: RoomDiagnosticSession) -> None:
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
        for switch_ip, records in sorted(known.items()):
            ports = list(dict.fromkeys(record.switch_port for record in records if record.switch_port is not None))
            parent = QTreeWidgetItem((f"Коммутатор ({switch_ip})", ", ".join(ports) or "Нет данных"))
            self.network_tree.addTopLevelItem(parent)
            for record in records:
                parent.addChild(QTreeWidgetItem((record.diagnostic_model or record.source_model or record.record_id, record.switch_port or "Нет данных")))
        for record in unknown:
            parent = QTreeWidgetItem(("Коммутатор не определён", record.switch_port or "Нет данных"))
            parent.addChild(QTreeWidgetItem((record.diagnostic_model or record.source_model or record.record_id, record.switch_port or "Нет данных")))
            self.network_tree.addTopLevelItem(parent)
        if self.network_tree.topLevelItemCount() == 0:
            self.network_tree.addTopLevelItem(QTreeWidgetItem(("Нет данных о сетевых подключениях", "")))
        self.network_tree.expandAll()

    def set_interaction_locked(self, locked: bool) -> None:
        """Block accordion changes while an exclusive row operation owns I/O."""
        self._interaction_locked = locked

    def clear_presentation(self) -> None:
        """Forget displayed room data when application authority is revoked.

        This is intentionally presentation-only: it neither resolves inventory nor
        starts, stops, or otherwise owns device I/O.
        """
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


class AudioDspChannelColumn(QFrame):
    """A click-only local DMP channel projection with no device authority."""

    selected = pyqtSignal(str, str)

    def __init__(self, section: str, channel: Mapping[str, Any], is_selected: bool, parent=None):
        super().__init__(parent)
        self._section = section
        self._oid = str(channel.get("oid"))
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
        self._local_controls = AudioDspLocalControls(str(channel.get("name") or "Канал"), self)
        self._hide_controls_timer = QTimer(self)
        self._hide_controls_timer.setSingleShot(True)
        self._hide_controls_timer.setInterval(180)
        self._hide_controls_timer.timeout.connect(self._hide_local_controls)
        self._local_controls.pointerEntered.connect(self._keep_local_controls)
        self._local_controls.pointerLeft.connect(self._schedule_local_controls_hide)
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
            QTimer.singleShot(0, self._show_local_controls)

    def enterEvent(self, event) -> None:
        self._show_local_controls()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._schedule_local_controls_hide()
        super().leaveEvent(event)

    def _show_local_controls(self) -> None:
        self._hide_controls_timer.stop()
        if not self.isVisible():
            return
        popup_size = self._local_controls.sizeHint()
        origin = self.mapToGlobal(QPoint(self.width() + 8, max(0, (self.height() - popup_size.height()) // 2)))
        self._local_controls.move(origin)
        self._local_controls.show()
        self._local_controls.raise_()

    def _keep_local_controls(self) -> None:
        self._hide_controls_timer.stop()

    def _schedule_local_controls_hide(self) -> None:
        if not self.property("audioSelected"):
            self._hide_controls_timer.start()

    def _hide_local_controls(self) -> None:
        if not self.property("audioSelected"):
            self._local_controls.hide()

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
        title = QLabel(channel_name, self)
        title.setObjectName("roomAudioDspLocalControlsTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
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

    def enterEvent(self, event) -> None:
        self.pointerEntered.emit()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.pointerLeft.emit()
        super().leaveEvent(event)


class AudioDspMeterPresentation(QWidget):
    """Focused room-only projection for accepted numeric ``meter_sections``."""

    def __init__(self, snapshot: Mapping[str, Any], selection, on_select, parent=None):
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

    def __init__(self, snapshot: Mapping[str, Any], source: Any, selection, on_select, actions=(), parent=None):
        super().__init__(parent)
        self.setObjectName("roomAudioDspDashboard")
        self.setProperty("presentationOnly", True)
        self._dashboard_layout = QGridLayout(self)
        self._dashboard_layout.setContentsMargins(0, 0, 0, 0)
        self._dashboard_layout.setSpacing(8)
        self._information = _audio_device_info_card(source, self)
        self._meters = AudioDspMeterPresentation(snapshot, selection, on_select, self)
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

    def __init__(self, row, *, request_local_refresh=None, request_auxiliary=None, request_mutation=None, request_matrix_route=None, request_debug=None, local_refresh_allowed=True, auxiliary_allowed=True, mutation_allowed=True, debug_allowed=True, live_here=False, audio_selection=None, audio_channel_selected=None, parent=None):
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
        if use_audio_dashboard:
            audio_actions.append(refresh_button)
        elif not use_matrix_dashboard:
            layout.addWidget(refresh_button)
        if row.capability is not None and row.capability.screen_key == "codec":
            call_log_button = QPushButton("Журнал звонков", self)
            call_log_button.setObjectName("roomCallLogButton")
            call_log_button.setEnabled(
                bool(request_auxiliary)
                and auxiliary_allowed
                and row.status is DeviceRowStatus.CONNECTED
                and (row.network_actions_enabled or live_here)
                and not row.interaction_blocked
            )
            if request_auxiliary is not None:
                call_log_button.clicked.connect(lambda: request_auxiliary("call_log"))
            layout.addWidget(call_log_button)
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
                "mutation_allowed": mutation_allowed,
            }
            if screen_key == "matrix":
                builder_kwargs.update(
                    request_local_refresh=request_local_refresh,
                    local_refresh_allowed=local_refresh_allowed,
                    request_matrix_route=request_matrix_route,
                    live_here=live_here,
                )
            if screen_key == "audio_dsp":
                builder_kwargs.update(
                    audio_selection=audio_selection,
                    audio_channel_selected=audio_channel_selected,
                    audio_actions=audio_actions,
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

    def _build_codec(self, layout, data, row, **_unused) -> None:
        self._add_fields(layout, "Кодек", data, (
            "model", "Модель", "Модель кодеков", "firmware", "Версия ПО", "Серийный номер", "serial",
            "MAC адрес", "mac", "SIP регистрация", "SIP адрес", "Время работы", "temperature",
            "network_speed", "Статус звонка", "Статус презентации",
        ))

    def _build_pdu(
        self,
        layout,
        data,
        row,
        *,
        request_mutation=None,
        mutation_allowed=True,
        live_here=False,
    ) -> None:
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
                and (row.network_actions_enabled or live_here)
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

    def _build_matrix(self, layout, data, row, *, request_local_refresh=None, local_refresh_allowed=True, request_matrix_route=None, live_here=False, **_unused) -> None:
        source = data if isinstance(data, Mapping) else {}
        dashboard = QWidget(self)
        dashboard.setObjectName("roomMatrixDashboard")
        dashboard_layout = QHBoxLayout(dashboard)
        dashboard_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_layout.setSpacing(12)
        info = SectionCard("Общая информация", "▣", dashboard)
        form = QFormLayout()
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
            form.addRow(label, QLabel(str(value) if value not in (None, "") else no_data, info))
        info.body_layout.addLayout(form)
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
                table.setItem(index, column, QTableWidgetItem(str(value)))
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
        dashboard_layout.addWidget(info, 25)
        dashboard_layout.addWidget(card, 53)
        dashboard_layout.addWidget(actions, 22)
        layout.addWidget(dashboard)

    def _build_audio(self, layout, data, row, *, audio_selection=None, audio_channel_selected=None, audio_actions=(), **_unused) -> None:
        source = data.get("device_info", data) if isinstance(data, Mapping) else data
        if isinstance(data, Mapping) and _has_numeric_meter_presentation(data):
            layout.addWidget(
                AudioDspDashboardPresentation(
                    data,
                    source,
                    audio_selection,
                    audio_channel_selected or (lambda *_args: None),
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
