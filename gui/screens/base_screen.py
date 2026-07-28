from PyQt5.QtWidgets import QPushButton, QWidget

from ..components import ValueDisplay
from ..ui_states import UIState, coerce_ui_state, state_spec


class BaseScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.colors = parent.colors if parent else None
        self.ui_state = UIState.IDLE
        self.init_ui()
        self.setProperty("uiState", self.ui_state.value)
    
    def init_ui(self):
        raise NotImplementedError
    
    def update_data(self, data):
        raise NotImplementedError
    
    def refresh(self):
        """Обновление данных экрана"""
        pass

    def set_ui_state(self, state, message=None):
        """Apply a shared state without replacing device-specific layouts."""
        self.ui_state = coerce_ui_state(state)
        spec = state_spec(self.ui_state)
        self.setProperty("uiState", self.ui_state.value)

        if self.ui_state in {UIState.LOADING, UIState.COMMAND}:
            for value in self.findChildren(ValueDisplay):
                if _inside_room_context_boundary(value):
                    continue
                value.set_state("loading", message or spec.default_text)
        elif self.ui_state == UIState.UNAVAILABLE:
            for value in self.findChildren(ValueDisplay):
                if _inside_room_context_boundary(value):
                    continue
                value.set_value("—")
                value.set_state("inactive")

        disabled = self.ui_state == UIState.DISABLED
        for button in self.findChildren(QPushButton):
            button.setEnabled(not disabled)

        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


def _inside_room_context_boundary(widget):
    parent = widget.parent()
    while parent is not None:
        if parent.property("roomContextBoundary") is True:
            return True
        next_parent = getattr(parent, "parent", None)
        if not callable(next_parent):
            return False
        parent = next_parent()
    return False
