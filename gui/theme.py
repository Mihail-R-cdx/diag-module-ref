"""Central design tokens and the application-wide PyQt5 theme.

Widgets should select a semantic variant with ``uiRole`` instead of matching
their visible text.  Status labels use the ``status`` dynamic property.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QWidget


COLORS = {
    "background": "#0D1117",
    "surface": "#151B23",
    "surface_raised": "#1B232D",
    "surface_hover": "#222C38",
    "border": "#2B3644",
    "border_strong": "#3B495A",
    "primary": "#2F6FED",
    "primary_hover": "#3D7CF5",
    "primary_pressed": "#245AC5",
    "success": "#24A85A",
    "success_hover": "#2DBE68",
    "success_pressed": "#1D8748",
    "danger": "#E05260",
    "danger_hover": "#ED6370",
    "danger_pressed": "#B83E4A",
    "warning": "#F59E0B",
    "text_primary": "#F2F5F8",
    "text_secondary": "#A6B0BE",
    "text_muted": "#6F7B8A",
    "text_on_accent": "#FFFFFF",
    "focus": "#78A7FF",
}

DARK_COLORS = dict(COLORS)
LIGHT_COLORS = {
    "background": "#F4F6F8", "surface": "#FFFFFF", "surface_raised": "#F0F3F6",
    "surface_hover": "#E7EDF5", "border": "#CBD5E1", "border_strong": "#94A3B8",
    "primary": "#2563EB", "primary_hover": "#1D4ED8", "primary_pressed": "#1E40AF",
    "success": "#16803B", "success_hover": "#117A34", "success_pressed": "#0E642B",
    "danger": "#C82D3D", "danger_hover": "#B91C2C", "danger_pressed": "#991B2A", "warning": "#B45309",
    "text_primary": "#172033", "text_secondary": "#475569", "text_muted": "#64748B",
    "text_on_accent": "#FFFFFF", "focus": "#2563EB",
}

SPACING = {
    "xxs": 2,
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
    "xxl": 32,
}

RADII = {
    "sm": 4,
    "md": 6,
    "lg": 8,
    "xl": 12,
    "pill": 999,
}

SIZES = {
    "control_height": 40,
    "control_height_compact": 32,
    "toolbar_control_min_height": 44,
    "toolbar_control_max_height": 56,
    "scrollbar": 10,
    "border": 1,
    "focus_border": 1,
}

TYPOGRAPHY = {
    "family": '"Segoe UI", "Inter", Arial, sans-serif',
    "body": 10,
    "body_large": 11,
    "caption": 9,
    "title": 16,
    "weight_regular": 400,
    "weight_medium": 500,
    "weight_semibold": 600,
}


def legacy_colors() -> dict:
    """Return the legacy color contract backed by the central palette."""
    return {
        "background": COLORS["background"],
        "surface": COLORS["surface"],
        "primary": COLORS["primary"],
        "primary_variant": COLORS["primary_pressed"],
        "secondary": COLORS["success"],
        "success": COLORS["success"],
        "error": COLORS["danger"],
        "warning": COLORS["warning"],
        "text_primary": COLORS["text_primary"],
        "text_secondary": COLORS["text_secondary"],
        "divider": COLORS["border"],
    }


def create_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(COLORS["background"]))
    palette.setColor(QPalette.WindowText, QColor(COLORS["text_primary"]))
    palette.setColor(QPalette.Base, QColor(COLORS["surface"]))
    palette.setColor(QPalette.AlternateBase, QColor(COLORS["surface_raised"]))
    palette.setColor(QPalette.ToolTipBase, QColor(COLORS["surface_raised"]))
    palette.setColor(QPalette.ToolTipText, QColor(COLORS["text_primary"]))
    palette.setColor(QPalette.Text, QColor(COLORS["text_primary"]))
    palette.setColor(QPalette.Button, QColor(COLORS["surface_raised"]))
    palette.setColor(QPalette.ButtonText, QColor(COLORS["text_primary"]))
    palette.setColor(QPalette.BrightText, QColor(COLORS["text_on_accent"]))
    palette.setColor(QPalette.Highlight, QColor(COLORS["primary"]))
    palette.setColor(QPalette.HighlightedText, QColor(COLORS["text_on_accent"]))
    palette.setColor(QPalette.Link, QColor(COLORS["focus"]))

    disabled = QPalette.Disabled
    palette.setColor(disabled, QPalette.WindowText, QColor(COLORS["text_muted"]))
    palette.setColor(disabled, QPalette.Text, QColor(COLORS["text_muted"]))
    palette.setColor(disabled, QPalette.ButtonText, QColor(COLORS["text_muted"]))
    palette.setColor(disabled, QPalette.Highlight, QColor(COLORS["border_strong"]))
    return palette


def build_stylesheet() -> str:
    c, r, s, t = COLORS, RADII, SIZES, TYPOGRAPHY
    return f"""
        QMainWindow, QDialog {{
            background-color: {c["background"]};
            color: {c["text_primary"]};
        }}
        QWidget {{
            color: {c["text_primary"]};
            font-family: {t["family"]};
            font-size: {t["body"]}pt;
        }}
        QWidget#centralWidget {{
            background-color: {c["background"]};
        }}
        QWidget#codecContent, QWidget#matrixContent,
        QWidget#pduContent, QWidget#audioDSPContent {{
            background-color: {c["background"]};
        }}
        QWidget[uiRole="card"], QFrame[uiRole="card"] {{
            background-color: {c["surface"]};
            border: 1px solid {c["border"]};
            border-radius: {r["lg"]}px;
        }}
        QWidget[uiRole="toolbar"], QGroupBox[uiRole="toolbar"] {{
            background-color: {c["surface"]};
            border: 1px solid {c["border"]};
            border-radius: {r["lg"]}px;
            margin: 0;
            padding: 0;
        }}
        QWidget[uiRole="statusBar"] {{
            background-color: {c["background"]};
            border-top: 1px solid {c["border"]};
        }}
        QWidget[uiState="authentication_error"],
        QWidget[uiState="request_error"],
        QWidget[uiState="disconnected"] {{
            border-color: {c["danger"]};
        }}
        QWidget[uiState="sleeping"],
        QWidget[uiState="unavailable"] {{
            border-color: {c["warning"]};
        }}
        QStackedWidget#screenContainer {{
            background-color: transparent;
            border: none;
        }}
        QGroupBox {{
            background-color: {c["surface"]};
            border: 1px solid {c["border"]};
            border-radius: {r["lg"]}px;
            font-weight: {t["weight_semibold"]};
            margin-top: 12px;
            padding-top: 12px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 5px;
            color: {c["text_primary"]};
        }}
        QGroupBox[uiRole="toolbar"]::title {{
            height: 0;
            margin: 0;
            padding: 0;
        }}
        QLabel[uiRole="secondary"], QLabel[uiRole="fieldLabel"] {{
            color: {c["text_secondary"]};
        }}
        QLabel[uiRole="fieldLabel"] {{
            font-size: {t["caption"]}pt;
            font-weight: {t["weight_medium"]};
        }}
        QLabel[uiRole="emptyTitle"] {{
            color: {c["text_primary"]};
            font-size: {t["title"]}pt;
            font-weight: {t["weight_semibold"]};
        }}
        QLabel[uiRole="cardTitle"] {{
            color: {c["text_primary"]};
            font-size: {t["body_large"]}pt;
            font-weight: {t["weight_semibold"]};
        }}
        QLabel[status="success"] {{ color: {c["success"]}; }}
        QLabel[status="danger"], QLabel[status="error"] {{ color: {c["danger"]}; }}
        QLabel[status="warning"] {{ color: {c["warning"]}; }}
        QLabel[status="loading"] {{ color: {c["primary"]}; }}
        QLabel[status="muted"], QLabel[status="inactive"] {{ color: {c["text_muted"]}; }}
        QLabel#connectionIndicator {{
            font-size: {t["body_large"]}pt;
        }}
        QLabel#sipRegistrationIndicator {{
            min-width: 32px;
            max-width: 32px;
            min-height: 32px;
            max-height: 32px;
            border-radius: 16px;
            color: {c["text_on_accent"]};
            font-size: {t["body_large"]}pt;
            font-weight: {t["weight_semibold"]};
        }}
        QLabel#sipRegistrationIndicator[status="success"] {{
            color: {c["text_on_accent"]};
            background-color: {c["success"]};
        }}
        QLabel#sipRegistrationIndicator[status="danger"] {{
            color: {c["text_on_accent"]};
            background-color: {c["danger"]};
        }}
        QLabel#sipRegistrationIndicator[status="inactive"] {{
            color: {c["text_muted"]};
            background-color: {c["surface_raised"]};
        }}
        QPushButton {{
            min-height: {s["control_height_compact"]}px;
            padding: 4px 14px;
            color: {c["text_primary"]};
            background-color: {c["surface_raised"]};
            border: 1px solid {c["border"]};
            border-radius: {r["md"]}px;
            font-weight: {t["weight_medium"]};
        }}
        QPushButton#sipFixButton {{
            min-height: {s["control_height_compact"] - 2}px;
            max-height: {s["control_height_compact"] - 2}px;
            padding: 0 14px;
        }}
        QPushButton:hover {{
            background-color: {c["surface_hover"]};
            border-color: {c["border_strong"]};
        }}
        QPushButton:focus {{
            border-color: {c["focus"]};
        }}
        QPushButton:pressed {{
            background-color: {c["border"]};
        }}
        QPushButton:disabled {{
            color: {c["text_muted"]};
            background-color: {c["surface"]};
            border-color: {c["border"]};
        }}
        QPushButton[uiRole="primary"] {{
            color: {c["text_on_accent"]};
            background-color: {c["primary"]};
            border-color: {c["primary"]};
            font-weight: {t["weight_semibold"]};
        }}
        QPushButton[uiRole="primary"]:hover {{
            background-color: {c["primary_hover"]};
            border-color: {c["primary_hover"]};
        }}
        QPushButton[uiRole="primary"]:pressed {{
            background-color: {c["primary_pressed"]};
            border-color: {c["primary_pressed"]};
        }}
        QPushButton[uiRole="success"], QPushButton[uiRole="active"] {{
            color: {c["text_on_accent"]};
            background-color: {c["success"]};
            border-color: {c["success"]};
        }}
        QPushButton[uiRole="success"]:hover, QPushButton[uiRole="active"]:hover {{
            background-color: {c["success_hover"]};
            border-color: {c["success_hover"]};
        }}
        QPushButton[uiRole="success"]:pressed, QPushButton[uiRole="active"]:pressed {{
            background-color: {c["success_pressed"]};
            border-color: {c["success_pressed"]};
        }}
        QPushButton[uiRole="danger"] {{
            color: {c["text_on_accent"]};
            background-color: {c["danger"]};
            border-color: {c["danger"]};
        }}
        QPushButton[uiRole="danger"]:hover {{
            background-color: {c["danger_hover"]};
            border-color: {c["danger_hover"]};
        }}
        QPushButton[uiRole="danger"]:pressed {{
            background-color: {c["danger_pressed"]};
            border-color: {c["danger_pressed"]};
        }}
        QPushButton[uiState="warning"] {{
            color: {c["warning"]};
            border-color: {c["warning"]};
        }}
        QPushButton[uiState="error"] {{
            color: {c["danger"]};
            border-color: {c["danger"]};
        }}
        QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            min-height: {s["control_height"]}px;
            padding: 0 12px;
            color: {c["text_primary"]};
            selection-color: {c["text_on_accent"]};
            selection-background-color: {c["primary"]};
            background-color: {c["surface"]};
            border: 1px solid {c["border"]};
            border-radius: {r["md"]}px;
        }}
        QPlainTextEdit, QTextEdit {{
            padding: 8px;
        }}
        QLineEdit:hover, QPlainTextEdit:hover, QTextEdit:hover,
        QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{
            border-color: {c["border"]};
        }}
        QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
        QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
            border-color: {c["border"]};
        }}
        QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled,
        QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
            color: {c["text_muted"]};
            background-color: {c["surface"]};
            border-color: {c["border"]};
        }}
        QLineEdit[uiRole="valueDisplay"] {{
            background-color: {c["surface_raised"]};
        }}
        QLineEdit[toolbarControl="true"],
        QPushButton[toolbarControl="true"] {{
            min-height: {s["toolbar_control_min_height"]}px;
            max-height: {s["toolbar_control_max_height"]}px;
        }}
        QLineEdit[uiRole="valueDisplay"][density="compact"] {{
            min-height: {s["control_height_compact"] - 2}px;
            max-height: {s["control_height_compact"] - 2}px;
        }}
        QLabel[parameterDensity="compact"],
        QLineEdit[parameterDensity="compact"] {{
            font-size: {t["caption"]}pt;
        }}
        QLineEdit[uiRole="valueDisplay"][uiState="success"] {{
            color: {c["success"]};
            border-color: {c["success"]};
        }}
        QLineEdit[uiRole="valueDisplay"][uiState="warning"] {{
            color: {c["warning"]};
            border-color: {c["warning"]};
        }}
        QLineEdit[uiRole="valueDisplay"][uiState="error"] {{
            color: {c["danger"]};
            border-color: {c["danger"]};
        }}
        QFrame[uiRole="parameterRow"] {{
            background-color: {c["surface"]};
            border: none;
            border-bottom: 1px solid {c["border"]};
        }}
        QComboBox::drop-down {{
            width: 30px;
            border: none;
        }}
        QComboBox QAbstractItemView {{
            color: {c["text_primary"]};
            background-color: {c["surface_raised"]};
            selection-color: {c["text_on_accent"]};
            selection-background-color: {c["primary"]};
            border: 1px solid {c["border_strong"]};
            outline: 0;
        }}
        QComboBox QAbstractItemView::item {{
            min-height: 30px;
            padding: 3px 10px;
        }}
        QComboBox QAbstractItemView::item:!enabled {{
            color: {c["success"]};
            font-weight: {t["weight_semibold"]};
        }}
        QTableView, QTableWidget {{
            color: {c["text_primary"]};
            alternate-background-color: {c["surface_raised"]};
            background-color: {c["surface"]};
            gridline-color: {c["border"]};
            border: 1px solid {c["border"]};
            border-radius: {r["md"]}px;
            selection-color: {c["text_on_accent"]};
            selection-background-color: {c["primary_pressed"]};
            outline: 0;
        }}
        QHeaderView::section {{
            color: {c["text_secondary"]};
            background-color: {c["surface_raised"]};
            border: none;
            border-right: 1px solid {c["border"]};
            border-bottom: 1px solid {c["border"]};
            padding: 8px;
            font-weight: {t["weight_semibold"]};
        }}
        QLabel#roomName {{
            color: {c["text_primary"]};
            font-size: {t["body"]}pt;
            font-weight: {t["weight_semibold"]};
        }}
        QLabel#roomVipBadge {{
            color: {c["text_on_accent"]};
            background-color: #8b5cf6;
            border-radius: {r["pill"]}px;
            padding: 2px 9px;
            font-size: {t["caption"]}pt;
            font-weight: {t["weight_semibold"]};
        }}
        QScrollArea {{
            background: transparent;
            border: none;
        }}
        QScrollBar:vertical {{
            width: {s["scrollbar"]}px;
            margin: 0;
            background: {c["surface"]};
            border: none;
        }}
        QScrollBar:horizontal {{
            height: {s["scrollbar"]}px;
            margin: 0;
            background: {c["surface"]};
            border: none;
        }}
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
            min-height: 24px;
            min-width: 24px;
            background: {c["border_strong"]};
            border-radius: {r["sm"]}px;
        }}
        QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
            background: {c["text_muted"]};
        }}
        QScrollBar::add-line, QScrollBar::sub-line,
        QScrollBar::add-page, QScrollBar::sub-page {{
            width: 0;
            height: 0;
            background: transparent;
            border: none;
        }}
        QProgressBar {{
            min-height: 8px;
            color: transparent;
            background-color: {c["surface_raised"]};
            border: 1px solid {c["border"]};
            border-radius: {r["sm"]}px;
        }}
        QProgressBar::chunk {{
            background-color: {c["primary"]};
            border-radius: {r["sm"]}px;
        }}
        QProgressBar[meterState="available"] {{
            background-color: {c["surface_raised"]};
            border: 1px solid {c["border"]};
        }}
        QProgressBar[meterState="available"]::chunk {{
            background-color: {c["primary"]};
        }}
        QProgressBar[meterState="unavailable"] {{
            background-color: {c["surface"]};
            border: 1px dashed {c["text_muted"]};
        }}
        QProgressBar[meterState="unavailable"]::chunk {{
            background-color: transparent;
        }}
        QCheckBox, QRadioButton {{
            spacing: 8px;
            color: {c["text_primary"]};
        }}
        QCheckBox:disabled, QRadioButton:disabled {{
            color: {c["text_muted"]};
        }}
        QToolTip {{
            color: {c["text_primary"]};
            background-color: {c["surface_raised"]};
            border: 1px solid {c["border_strong"]};
            padding: 5px;
        }}
        QMenuBar, QMenu, QStatusBar {{
            color: {c["text_primary"]};
            background-color: {c["surface"]};
        }}
        QMenu {{
            border: 1px solid {c["border"]};
        }}
        QMenu::item:selected, QMenuBar::item:selected {{
            color: {c["text_on_accent"]};
            background-color: {c["primary"]};
        }}
        QPlainTextEdit[uiRole="terminal"] {{
            color: #D7FBE8;
            background-color: #090C10;
            border-color: {c["border"]};
            font-family: Consolas, "Courier New", monospace;
        }}
    """


def apply_theme(target, theme: str = "dark") -> None:
    """Apply the shared palette and QSS to a QApplication or QWidget."""
    if theme not in {"dark", "light"}:
        raise ValueError(f"Unsupported theme: {theme}")
    COLORS.clear()
    COLORS.update(DARK_COLORS if theme == "dark" else LIGHT_COLORS)
    target.setPalette(create_palette())
    target.setStyleSheet(build_stylesheet())
    if isinstance(target, QWidget):
        target.setAttribute(Qt.WA_StyledBackground, True)
