"""Focused fail-closed model fallback dialog."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QLabel, QListWidget, QVBoxLayout

from .diagnostic_dispatch import ActionBinding, DiagnosticActionPurpose


@dataclass(frozen=True)
class DeviceModelFallbackSelection:
    purpose: DiagnosticActionPurpose
    generation: int
    binding_id: ActionBinding
    diagnostic_model: str


class DeviceModelFallbackDialog(QDialog):
    """Render safe fallback choices and require explicit current selection."""

    def __init__(
        self,
        *,
        purpose: DiagnosticActionPurpose,
        generation: int,
        binding_id: ActionBinding,
        safe_reason: str,
        model_choices: tuple[str, ...],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._purpose = purpose
        self._generation = generation
        self._binding_id = binding_id
        self._selected_model: str | None = None
        self.setWindowTitle("Выбор модели устройства")
        self.setModal(True)

        layout = QVBoxLayout(self)
        reason = QLabel(safe_reason or "Модель не удалось определить автоматически.", self)
        reason.setWordWrap(True)
        layout.addWidget(reason)

        self.model_list = QListWidget(self)
        self.model_list.setObjectName("deviceModelFallbackChoices")
        for model in model_choices:
            self.model_list.addItem(model)
        self.model_list.clearSelection()
        self.model_list.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self.model_list)

        confirm_text = (
            "Подключиться"
            if purpose is DiagnosticActionPurpose.DIAGNOSTIC_START
            else "Продолжить"
        )
        self.buttons = QDialogButtonBox(QDialogButtonBox.Cancel, self)
        self.confirm_button = self.buttons.addButton(
            confirm_text,
            QDialogButtonBox.AcceptRole,
        )
        self.confirm_button.setEnabled(False)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.resize(420, 360)

    def selected_model(self) -> str | None:
        return self._selected_model

    def selection(self) -> DeviceModelFallbackSelection | None:
        if self._selected_model is None:
            return None
        return DeviceModelFallbackSelection(
            purpose=self._purpose,
            generation=self._generation,
            binding_id=self._binding_id,
            diagnostic_model=self._selected_model,
        )

    def accept(self) -> None:
        if self._selected_model is None:
            return
        super().accept()

    def _on_selection_changed(self, current, _previous) -> None:
        self._selected_model = current.text() if current is not None else None
        self.confirm_button.setEnabled(self._selected_model is not None)
