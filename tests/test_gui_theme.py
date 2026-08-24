from __future__ import annotations

import ast
import os
from pathlib import Path
import unittest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5.QtWidgets import QApplication
except ImportError:
    QApplication = None


THEME_PATH = Path("gui/theme.py")


def _literal_assignment(name: str):
    tree = ast.parse(THEME_PATH.read_text(encoding="utf-8"), filename=str(THEME_PATH))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} is not a literal module assignment")


class ThemeSourceContractTest(unittest.TestCase):
    def test_tokens_cover_required_semantics(self):
        colors = _literal_assignment("COLORS")
        self.assertTrue(
            {
                "background",
                "surface",
                "surface_raised",
                "border",
                "primary",
                "success",
                "danger",
                "warning",
                "text_primary",
                "text_secondary",
                "text_muted",
                "focus",
            }.issubset(colors)
        )
        self.assertTrue({"xs", "sm", "md", "lg", "xl"}.issubset(_literal_assignment("SPACING")))
        self.assertTrue({"sm", "md", "lg", "xl"}.issubset(_literal_assignment("RADII")))
        self.assertIn("control_height", _literal_assignment("SIZES"))
        self.assertIn("family", _literal_assignment("TYPOGRAPHY"))

        def luminance(hex_color):
            channels = [
                int(hex_color[index : index + 2], 16) / 255.0
                for index in (1, 3, 5)
            ]
            linear = [
                value / 12.92
                if value <= 0.04045
                else ((value + 0.055) / 1.055) ** 2.4
                for value in channels
            ]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        def contrast(first, second):
            lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
            return (lighter + 0.05) / (darker + 0.05)

        self.assertGreaterEqual(contrast(colors["text_secondary"], colors["background"]), 4.5)
        self.assertGreaterEqual(contrast(colors["text_secondary"], colors["surface"]), 4.5)

    def test_qss_declares_semantic_variants_and_widget_states(self):
        source = THEME_PATH.read_text(encoding="utf-8")
        required_fragments = (
            'QPushButton[uiRole="primary"]',
            'QPushButton[uiRole="success"]',
            'QPushButton[uiRole="danger"]',
            'QLabel[status="warning"]',
            "QPushButton:hover",
            "QPushButton:focus",
            "QPushButton:pressed",
            "QPushButton:disabled",
            "QLineEdit:focus",
            "QComboBox QAbstractItemView",
            "QTableView, QTableWidget",
            "QScrollBar::handle:vertical",
        )
        for fragment in required_fragments:
            self.assertIn(fragment, source)

    def test_application_and_main_window_use_the_shared_theme(self):
        main_source = Path("main.py").read_text(encoding="utf-8")
        window_source = Path("gui/main_window.py").read_text(encoding="utf-8")
        self.assertIn("apply_theme(app)", main_source)
        self.assertIn("self.colors = legacy_colors()", window_source)
        self.assertIn('self.refresh_btn.setProperty("uiRole", "primary")', window_source)
        self.assertIn("return EmptyState(", window_source)
        self.assertIn('self.connection_indicator = StatusIndicator("inactive"', window_source)


@unittest.skipIf(QApplication is None, "PyQt5 is not installed")
class ThemeOffscreenSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")
        cls.app.setQuitOnLastWindowClosed(False)

    def tearDown(self):
        if hasattr(self, "window"):
            from PyQt5.QtCore import QEvent

            self.window.close()
            self.window.deleteLater()
            QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            QApplication.processEvents()

    def test_theme_applies_to_application(self):
        from gui.theme import COLORS, apply_theme

        apply_theme(self.app)

        self.assertIn(COLORS["primary"], self.app.styleSheet())
        self.assertEqual(COLORS["background"].lower(), self.app.palette().window().color().name())

    def test_full_window_keeps_contracts_without_hardware(self):
        from gui.main_window import VCSDiagnosticApp

        self.window = VCSDiagnosticApp()
        QApplication.processEvents()

        self.assertEqual((950, 1000), (self.window.width(), self.window.height()))
        self.assertEqual(6, self.window.screen_container.count())
        self.assertIs(self.window.placeholder_widget, self.window.screen_container.currentWidget())
        self.assertEqual("Никогда", self.window.time_display.text())
        self.assertFalse(hasattr(self.window, "device_combo"))
        self.assertEqual("primary", self.window.refresh_btn.property("uiRole"))
        self.assertEqual("secondary", self.window.password_btn.property("uiRole"))
        self.assertEqual("secondary", self.window.debug_btn.property("uiRole"))
        self.assertEqual("card", self.window.placeholder_widget.property("uiRole"))
        self.assertEqual("screenContainer", self.window.screen_container.objectName())
        self.assertEqual("inactive", self.window.connection_indicator.property("status"))
        self.assertEqual(
            "Соединение: не установлено",
            self.window.connection_status.text(),
        )
        self.assertTrue(self.window.update_timer.isActive())

    def test_window_frame_starts_at_available_screen_top(self):
        from gui.main_window import VCSDiagnosticApp

        self.window = VCSDiagnosticApp()
        self.window.show()
        QApplication.processEvents()
        QApplication.processEvents()

        self.assertEqual(
            self.window.screen().availableGeometry().top(),
            self.window.frameGeometry().top(),
        )

    def test_clicking_ip_field_selects_the_complete_address(self):
        from PyQt5.QtCore import Qt
        from PyQt5.QtTest import QTest

        from gui.main_window import VCSDiagnosticApp

        self.window = VCSDiagnosticApp()
        self.window.show()
        self.window.ip_entry.setText("link.ru")
        QApplication.processEvents()

        QTest.mouseClick(self.window.ip_entry, Qt.LeftButton)
        QApplication.processEvents()

        self.assertEqual("link.ru", self.window.ip_entry.selectedText())

    def test_main_window_shell_status_can_show_success_and_error(self):
        from gui.main_window import VCSDiagnosticApp

        self.window = VCSDiagnosticApp()
        self.window.set_connection_status("success", "Соединение: установлено")
        QApplication.processEvents()

        self.assertEqual("success", self.window.connection_indicator.property("status"))
        self.assertEqual("Соединение: установлено", self.window.connection_status.text())

        self.window.set_connection_status("danger", "Соединение: ошибка подключения")
        QApplication.processEvents()

        self.assertEqual("danger", self.window.connection_indicator.property("status"))
        self.assertEqual("Соединение: ошибка подключения", self.window.connection_status.text())

    def test_connection_panel_controls_do_not_overlap_at_smaller_size(self):
        from PyQt5.QtCore import Qt

        from gui.components import ValueDisplay
        from gui.main_window import VCSDiagnosticApp

        self.window = VCSDiagnosticApp()
        self.window.show()
        pdu = self.window.screens["pdu"]
        pdu.update_data(
            {
                "device_info": {
                    "model": "PE8208AV",
                    "ip_address": "link.ru",
                    "firmware": "2.4.1",
                    "connected": True,
                },
                "outlets": [
                    {"number": number, "name": f"Outlet {number}", "status": "on"}
                    for number in range(1, 9)
                ],
            }
        )

        sizes = ((800, 700), (800, 800), (950, 950), (1200, 900), (1536, 1024))
        for width, height in sizes:
            with self.subTest(size=(width, height)):
                self.window.resize(width, height)
                QApplication.processEvents()
                self.assertEqual((width, height), (self.window.width(), self.window.height()))

                controls = (
                    self.window.ip_entry,
                    self.window.password_btn,
                    self.window.refresh_btn,
                    self.window.debug_btn,
                )
                for index, left_control in enumerate(controls):
                    self.assertGreater(left_control.width(), 0)
                    self.assertLess(
                        left_control.geometry().right(),
                        self.window.connection_panel.width(),
                    )
                    for right_control in controls[index + 1:]:
                        self.assertFalse(
                            left_control.geometry().intersects(right_control.geometry())
                        )

                for screen in self.window.screens.values():
                    self.window.screen_container.setCurrentWidget(screen)
                    QApplication.processEvents()
                    scroll_area = getattr(screen, "scroll_area", None)
                    if scroll_area is not None:
                        self.assertEqual(
                            Qt.ScrollBarAlwaysOff,
                            scroll_area.horizontalScrollBarPolicy(),
                        )
                        self.assertEqual(0, scroll_area.horizontalScrollBar().maximum())

        self.window.resize(800, 700)
        self.window.screen_container.setCurrentWidget(pdu)
        QApplication.processEvents()
        self.assertGreater(pdu.scroll_area.verticalScrollBar().maximum(), 0)
        column_width = sum(
            pdu.outlets_table.columnWidth(column)
            for column in range(pdu.outlets_table.columnCount())
        )
        self.assertLessEqual(column_width, pdu.outlets_table.viewport().width())

        self.window.resize(1536, 1024)
        QApplication.processEvents()
        for screen in self.window.screens.values():
            for value in screen.findChildren(ValueDisplay):
                if value.parent().property("alignedControls"):
                    self.assertLess(value.width(), screen.width())
                elif value.accessibleName() == "Версия прошивки":
                    self.assertLess(value.width(), screen.width())
                else:
                    self.assertLessEqual(value.width(), 360)

        self.assertIs(self.window.password_btn, self.window.ip_entry.nextInFocusChain())
        self.assertIs(self.window.refresh_btn, self.window.password_btn.nextInFocusChain())
        self.assertIs(self.window.debug_btn, self.window.refresh_btn.nextInFocusChain())


if __name__ == "__main__":
    unittest.main()
