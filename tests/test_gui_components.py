from __future__ import annotations

import os
import unittest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtWidgets import QApplication
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class ComponentsOffscreenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")

    def tearDown(self):
        if hasattr(self, "widget"):
            self.widget.close()
            self.widget.deleteLater()
        QApplication.processEvents()

    def test_section_card_and_parameter_row_update_without_recreation(self):
        from gui.components import ParameterRow, SectionCard, SemanticButton

        self.widget = SectionCard("Параметры", "⚙")
        row = ParameterRow("Громкость", "65%")
        action = SemanticButton("Вкл", "active")
        row.add_action(action)
        self.widget.add_widget(row)

        value_widget = row.value_display
        row.set_value("70%")
        row.set_state("success")
        self.widget.set_title("Аудио")

        self.assertIs(value_widget, row.value_display)
        self.assertEqual("70%", row.value_display.value())
        self.assertEqual("success", row.value_display.property("uiState"))
        self.assertEqual("Аудио", self.widget.title_label.text())
        self.assertEqual("active", action.property("uiRole"))

    def test_semantic_button_click_loading_and_error_states(self):
        from gui.components import SemanticButton

        self.widget = SemanticButton("Обновить", "primary")
        clicks = []
        self.widget.clicked.connect(lambda: clicks.append(True))
        self.widget.click()
        self.widget.set_loading(True, "Подключение…")

        self.assertEqual([True], clicks)
        self.assertFalse(self.widget.isEnabled())
        self.assertEqual("Подключение…", self.widget.text())
        self.assertEqual("loading", self.widget.property("uiState"))

        self.widget.set_state("error")
        self.assertTrue(self.widget.isEnabled())
        self.assertEqual("Обновить", self.widget.text())
        self.assertEqual("error", self.widget.property("uiState"))

    def test_status_value_and_empty_state_can_change_in_place(self):
        from gui.components import EmptyState, StatusIndicator, ValueDisplay

        self.widget = EmptyState("Нет данных", "Запустите обновление")
        self.widget.set_content("Ошибка", "Повторите попытку", "error")
        indicator = StatusIndicator("warning", "Нестабильно")
        value = ValueDisplay()
        value.set_value("Зарегистрирован")
        value.set_state("success")

        self.assertEqual("Ошибка", self.widget.title_label.text())
        self.assertEqual("error", self.widget.property("uiState"))
        self.assertEqual("warning", indicator.status())
        self.assertIn("Нестабильно", indicator.text())
        self.assertEqual("Зарегистрирован", value.value())
        self.assertEqual("success", value.property("uiState"))

        indicator.deleteLater()
        value.deleteLater()

    def test_exclusive_action_group_emits_selected_key(self):
        from gui.components import ExclusiveActionGroup

        self.widget = ExclusiveActionGroup(
            (("on", "Вкл"), ("off", "Выкл"), ("mute", "Мьют")),
            selected="off",
        )
        selected = []
        self.widget.selectionChanged.connect(selected.append)
        self.widget.buttons["on"].click()

        self.assertEqual("on", self.widget.selected_key())
        self.assertEqual(["on"], selected)
        self.assertEqual("active", self.widget.buttons["on"].property("uiRole"))
        self.assertEqual("secondary", self.widget.buttons["off"].property("uiRole"))

    def test_existing_button_can_receive_semantic_role(self):
        from PyQt5.QtWidgets import QPushButton

        from gui.components import configure_button

        self.widget = QPushButton("Удалить")
        configure_button(self.widget, "danger")
        self.assertEqual("danger", self.widget.property("uiRole"))


if __name__ == "__main__":
    unittest.main()
