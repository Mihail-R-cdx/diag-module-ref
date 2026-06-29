"""Small reusable widgets styled by :mod:`gui.theme`.

The components intentionally know nothing about devices or network commands.
Callers update their values and connect regular Qt signals to existing
application handlers.
"""

from __future__ import annotations

from typing import Dict, Iterable, Optional, Tuple

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..theme import SIZES, SPACING


BUTTON_ROLES = {"primary", "secondary", "active", "success", "danger"}
SEMANTIC_STATES = {
    "normal",
    "inactive",
    "disabled",
    "loading",
    "success",
    "warning",
    "error",
}


def _repolish(widget: QWidget) -> None:
    """Refresh QSS after changing a dynamic property."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def _set_state(widget: QWidget, state: str) -> None:
    if state not in SEMANTIC_STATES:
        raise ValueError(f"Unsupported semantic state: {state}")
    widget.setProperty("uiState", state)
    _repolish(widget)


def configure_button(button: QPushButton, role: str = "secondary") -> QPushButton:
    """Apply a semantic theme role to any existing push button."""
    if role not in BUTTON_ROLES:
        raise ValueError(f"Unsupported button role: {role}")
    button.setProperty("uiRole", role)
    _repolish(button)
    return button


class SemanticButton(QPushButton):
    """Push button with semantic role and reversible loading state."""

    def __init__(
        self,
        text: str = "",
        role: str = "secondary",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(text, parent)
        self._normal_text = text
        self._loading = False
        configure_button(self, role)
        _set_state(self, "normal")

    def role(self) -> str:
        return str(self.property("uiRole"))

    def set_role(self, role: str) -> None:
        configure_button(self, role)

    def set_state(self, state: str) -> None:
        if state == "disabled":
            self.set_loading(False)
            self.setEnabled(False)
        elif state == "loading":
            self.set_loading(True)
            return
        else:
            self.set_loading(False)
            self.setEnabled(True)
        _set_state(self, state)

    def set_loading(self, loading: bool, text: Optional[str] = None) -> None:
        loading = bool(loading)
        if loading and not self._loading:
            self._normal_text = self.text()
        self._loading = loading
        self.setEnabled(not loading)
        self.setText((text or "Загрузка…") if loading else self._normal_text)
        _set_state(self, "loading" if loading else "normal")

    def is_loading(self) -> bool:
        return self._loading


class StatusIndicator(QLabel):
    """Colored status dot with optional adjacent text."""

    def __init__(
        self,
        status: str = "inactive",
        text: str = "",
        show_text: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._status_text = text
        self._show_text = show_text
        self.setObjectName("statusIndicator")
        self.setAccessibleName("Индикатор состояния")
        self.set_status(status, text)

    def set_status(self, status: str, text: Optional[str] = None) -> None:
        normalized = "danger" if status == "error" else status
        allowed = {"success", "danger", "warning", "inactive", "muted", "loading"}
        if normalized not in allowed:
            raise ValueError(f"Unsupported indicator status: {status}")
        if text is not None:
            self._status_text = text
        self.setProperty("status", normalized)
        self.setText(
            f"●  {self._status_text}" if self._show_text and self._status_text else "●"
        )
        _repolish(self)

    def status(self) -> str:
        return str(self.property("status"))


class ValueDisplay(QLineEdit):
    """Read-only, selectable value field with semantic states."""

    def __init__(
        self,
        value: object = "—",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("valueDisplay")
        self.setProperty("uiRole", "valueDisplay")
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.ClickFocus)
        self.set_value(value)
        _set_state(self, "normal")

    def set_value(self, value: object) -> None:
        self.setText("—" if value is None or value == "" else str(value))

    def value(self) -> str:
        return self.text()

    def set_state(self, state: str, message: Optional[str] = None) -> None:
        if state == "loading":
            self.setText(message or "Загрузка…")
        elif state in {"inactive", "disabled"} and message is not None:
            self.setText(message)
        self.setEnabled(state != "disabled")
        _set_state(self, state)


class SectionCard(QFrame):
    """Card with a title, optional icon, and public body layout."""

    def __init__(
        self,
        title: str,
        icon: Optional[object] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("uiRole", "card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(
            SPACING["lg"], SPACING["md"], SPACING["lg"], SPACING["lg"]
        )
        root_layout.setSpacing(SPACING["md"])

        self.header_widget = QWidget(self)
        self.header_widget.setProperty("uiRole", "cardHeader")
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(SPACING["sm"])

        self.icon_label = QLabel(self.header_widget)
        self.icon_label.setObjectName("sectionCardIcon")
        self.icon_label.setProperty("status", "muted")
        self.icon_label.setVisible(icon is not None)
        self.set_icon(icon)

        self.title_label = QLabel(title, self.header_widget)
        self.title_label.setObjectName("sectionCardTitle")
        self.title_label.setProperty("uiRole", "cardTitle")

        header_layout.addWidget(self.icon_label)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)
        root_layout.addWidget(self.header_widget)

        self.body = QWidget(self)
        self.body.setProperty("uiRole", "cardBody")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)
        root_layout.addWidget(self.body)

    def set_title(self, title: str) -> None:
        self.title_label.setText(title)

    def set_icon(self, icon: Optional[object]) -> None:
        if icon is None:
            self.icon_label.clear()
            self.icon_label.setVisible(False)
        elif isinstance(icon, QIcon):
            self.icon_label.setPixmap(icon.pixmap(QSize(20, 20)))
            self.icon_label.setVisible(True)
        else:
            self.icon_label.setText(str(icon))
            self.icon_label.setVisible(True)

    def add_widget(self, widget: QWidget, stretch: int = 0) -> None:
        self.body_layout.addWidget(widget, stretch)


class ParameterRow(QFrame):
    """Label/value/action row whose content can be updated in place."""

    def __init__(
        self,
        name: str,
        value: object = "—",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("uiRole", "parameterRow")

        layout = QGridLayout(self)
        layout.setContentsMargins(SPACING["md"], SPACING["sm"], SPACING["md"], SPACING["sm"])
        layout.setHorizontalSpacing(SPACING["md"])
        layout.setVerticalSpacing(SPACING["xs"])

        self.name_label = QLabel(name, self)
        self.name_label.setObjectName("parameterName")
        self.value_display = ValueDisplay(value, self)
        self.value_display.setMinimumWidth(110)

        self.actions_widget = QWidget(self)
        self.actions_widget.setObjectName("parameterActions")
        self.action_layout = QHBoxLayout(self.actions_widget)
        self.action_layout.setContentsMargins(0, 0, 0, 0)
        self.action_layout.setSpacing(SPACING["sm"])

        layout.addWidget(self.name_label, 0, 0)
        layout.addWidget(self.value_display, 0, 1)
        layout.addWidget(self.actions_widget, 0, 2)
        layout.setColumnStretch(0, 3)
        layout.setColumnStretch(1, 2)
        layout.setColumnStretch(2, 0)

    def set_name(self, name: str) -> None:
        self.name_label.setText(name)

    def set_value(self, value: object) -> None:
        self.value_display.set_value(value)

    def set_state(self, state: str, message: Optional[str] = None) -> None:
        self.value_display.set_state(state, message)
        _set_state(self, state)

    def add_action(self, widget: QWidget) -> None:
        self.action_layout.addWidget(widget)


class EmptyState(QWidget):
    """Consistent placeholder for screens with no data yet."""

    def __init__(
        self,
        title: str,
        description: str = "",
        icon: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("uiRole", "card")
        self.setProperty("uiState", "inactive")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(SPACING["sm"])
        layout.setContentsMargins(SPACING["xl"], SPACING["xl"], SPACING["xl"], SPACING["xl"])

        self.icon_label = QLabel(icon, self)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setProperty("status", "muted")
        self.icon_label.setVisible(bool(icon))

        self.title_label = QLabel(title, self)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setProperty("uiRole", "emptyTitle")

        self.description_label = QLabel(description, self)
        self.description_label.setAlignment(Qt.AlignCenter)
        self.description_label.setWordWrap(True)
        self.description_label.setProperty("uiRole", "secondary")
        self.description_label.setVisible(bool(description))

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.description_label)

    def set_content(
        self,
        title: str,
        description: Optional[str] = None,
        state: str = "inactive",
    ) -> None:
        self.title_label.setText(title)
        if description is not None:
            self.description_label.setText(description)
            self.description_label.setVisible(bool(description))
        _set_state(self, state)


class ExclusiveActionGroup(QWidget):
    """Compact mutually-exclusive semantic action buttons."""

    selectionChanged = pyqtSignal(str)

    def __init__(
        self,
        actions: Iterable[Tuple[str, str]],
        selected: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("uiRole", "actionGroup")
        self.buttons: Dict[str, SemanticButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING["xs"])

        for key, label in actions:
            button = SemanticButton(label, "secondary", self)
            button.setCheckable(True)
            button.setMinimumHeight(SIZES["control_height_compact"])
            button.clicked.connect(lambda checked, action=key: self._on_clicked(action, checked))
            self._group.addButton(button)
            self.buttons[key] = button
            layout.addWidget(button)

        if selected is not None:
            self.select(selected, emit=False)

    def _on_clicked(self, key: str, checked: bool) -> None:
        if checked:
            self._sync_roles()
            self.selectionChanged.emit(key)

    def _sync_roles(self) -> None:
        for button in self.buttons.values():
            button.set_role("active" if button.isChecked() else "secondary")

    def select(self, key: str, emit: bool = False) -> None:
        if key not in self.buttons:
            raise KeyError(key)
        self.buttons[key].setChecked(True)
        self._sync_roles()
        if emit:
            self.selectionChanged.emit(key)

    def selected_key(self) -> Optional[str]:
        for key, button in self.buttons.items():
            if button.isChecked():
                return key
        return None

    def set_actions_enabled(self, enabled: bool) -> None:
        for button in self.buttons.values():
            button.setEnabled(enabled)
