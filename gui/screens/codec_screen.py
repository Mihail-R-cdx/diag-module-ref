import json
from dataclasses import replace

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QScrollArea,
    QGridLayout,
    QFrame,
    QLabel,
    QWidget,
    QMessageBox,
    QProgressDialog,
    QSizePolicy,
    QApplication,
)
from PyQt5.QtCore import Qt, QTimer, QEventLoop, QThreadPool, QPoint
try:
    from PyQt5 import sip
except ImportError:
    sip = None
from ..dialogs import CallLogWindow
from ..components import (
    ParameterRow,
    SectionCard,
    SemanticButton,
    StatusIndicator,
    configure_button,
)
from ..theme import SIZES, SPACING
from ..ui_states import UIState
from utils.te20_audio import format_te20_monitor_audio_level
from core.interactive_session import (
    InteractiveOperation,
    InteractiveSessionController,
    OperationSemantic,
)
from .base_screen import BaseScreen


class SIPRegistrationIndicator(QLabel):
    """Compact round SIP registration state without an external icon pack."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sipRegistrationIndicator")
        self.setAccessibleName("Статус SIP-регистрации")
        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(32, 32)
        self.set_status("inactive")

    def set_status(self, status):
        normalized = "danger" if status == "error" else status
        glyphs = {
            "success": "✓",
            "danger": "×",
            "inactive": "–",
        }
        if normalized not in glyphs:
            normalized = "inactive"
        self.setProperty("status", normalized)
        self.setText(glyphs[normalized])
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        self.update()

    def status(self):
        return str(self.property("status"))


class CodecScreen(BaseScreen):
    TE20_MONITOR_AUDIO_INTERVAL_MS = 2000
    INFO_VALUE_WIDTH_SCALE = 1.5
    INFO_VALUE_PREFERRED_WIDTH = 216
    INFO_WIDE_VALUE_WIDTH = round(INFO_VALUE_PREFERRED_WIDTH * 1.1)
    CONTROL_LABEL_WIDTH = 360
    CONTROL_LABEL_WIDTH_NARROW = 240

    CALL_LOG_PARAM = "Журнал звонков"

    TE20_SLEEP_UNAVAILABLE_FIELDS = (
        "Звук в помещении (микрофон)",
        "Звук из динамиков (выход кодека)",
        "Громкость микрофона",
        "Mute микрофона",
    )

    def __init__(self, parent=None):
        self.param_count = 15
        self.param_widgets = []
        self.presentation_buttons = {}
        self.sip_fix_buttons = []  # Храним кнопки для каждого блока
        self.volume_buttons = {}  # Храним кнопки для изменения громкости
        self.mute_buttons = {}
        self.volume_values = {}  # Храним текущие значения громкости для каждого параметра
        self.last_unmuted_volume = {}
        self.microphone_mute_state = None
        self._show_te20_monitor_audio_fields = False
        self.wake_buttons = {}
        self.wake_countdown_labels = {}
        self.parameter_rows = {}
        self.sip_status_indicators = {}
        self._te20_is_sleeping = False
        self._te20_wake_countdown_remaining = 0
        self._polycom_command_progress = None
        self._presentation_enable_timers = {}
        self._interactive_callback_serial = 0
        self._interactive_callbacks = {}
        super().__init__(parent)
        self.interactive_controller = InteractiveSessionController(self)
        self.interactive_controller.signals.result.connect(self._on_interactive_result)
        self.interactive_controller.signals.error.connect(self._on_interactive_error)
        self.interactive_controller.signals.dropped.connect(self._on_interactive_dropped)
        self.interactive_controller.signals.finished.connect(self._on_interactive_finished)
        if self.parent and hasattr(self.parent, "ip_entry"):
            self.parent.ip_entry.textChanged.connect(self._on_interactive_identity_changed)
        controller = self.interactive_controller
        self.destroyed.connect(lambda: controller.shutdown(wait=False))
        self.volume_refresh_timer = QTimer(self)
        self.volume_refresh_timer.setSingleShot(True)
        self._pending_volume_refresh_param = "Громкость динамиков"
        self.volume_refresh_timer.timeout.connect(self.refresh_pending_volume_status)
        self.presentation_refresh_timer = QTimer(self)
        self.presentation_refresh_timer.setSingleShot(True)
        self.presentation_refresh_timer.timeout.connect(self.refresh_presentation_status)
        self.monitor_audio_timer = QTimer(self)
        # The TE20 web interface samples these live meters every two seconds.
        # Using the same cadence avoids displaying an unnecessarily stale sample.
        self.monitor_audio_timer.setInterval(
            self.TE20_MONITOR_AUDIO_INTERVAL_MS
        )
        self.monitor_audio_timer.timeout.connect(self.poll_te20_monitor_audio)
        self.wake_countdown_timer = QTimer(self)
        self.wake_countdown_timer.setInterval(1000)
        self.wake_countdown_timer.timeout.connect(self._tick_te20_wake_countdown)

    def _get_current_device_credentials(self, device_name, ip_address):
        """Возвращает актуальные credentials с учётом IP-специфичного индекса."""
        if not self.parent:
            return None, 0, []

        creds_list = self.parent.device_credentials.get(device_name, [])
        if not creds_list:
            return None, 0, []

        if hasattr(self.parent, 'get_current_credential_index'):
            current_idx = self.parent.get_current_credential_index(device_name, ip_address)
        else:
            current_idx = self.parent.current_credential_index.get(device_name, 0)

        if current_idx >= len(creds_list):
            current_idx = 0

        return creds_list[current_idx], current_idx, creds_list

    def _activate_interactive_context(self):
        if not self.parent:
            return None
        device_name = self.parent.device_combo.currentText()
        ip_address = self.parent.ip_entry.text().strip()
        if not device_name or not ip_address:
            return None
        creds_list = self.parent.device_credentials.get(device_name, [])
        if not creds_list:
            return None
        if hasattr(self.parent, "get_valid_current_credential_index"):
            current_idx = self.parent.get_valid_current_credential_index(
                device_name, creds_list, ip_address
            )
        else:
            _creds, current_idx, _all = self._get_current_device_credentials(
                device_name, ip_address
            )
        saved_profile = None
        if hasattr(self.parent, "get_device_connection_profile"):
            saved_profile = self.parent.get_device_connection_profile(
                device_name, ip_address
            )
        generation = self.interactive_controller.activate_context(
            device_name,
            ip_address,
            creds_list,
            current_idx,
            saved_profile,
        )
        return device_name, ip_address, generation

    def _submit_interactive(self, operation, on_result=None, on_error=None):
        context = self._activate_interactive_context()
        if context is None:
            return None
        self._interactive_callback_serial += 1
        token = self._interactive_callback_serial
        operation = replace(operation, client_token=token)
        self._interactive_callbacks[token] = (on_result, on_error)
        operation_id = self.interactive_controller.submit(
            operation, generation=context[2]
        )
        if operation_id is None:
            self._interactive_callbacks.pop(token, None)
        return operation_id

    def _interactive_payload_is_current(self, payload):
        if not self.parent:
            return False
        return (
            payload.get("generation") == self.interactive_controller.generation
            and payload.get("model") == self.parent.device_combo.currentText()
            and payload.get("ip_address") == self.parent.ip_entry.text().strip()
        )

    def _on_interactive_result(self, payload):
        if not self._interactive_payload_is_current(payload):
            return
        if self.parent:
            index = payload.get("credential_index")
            profile = payload.get("connection_profile")
            if index is not None and hasattr(self.parent, "set_current_credential_index"):
                self.parent.set_current_credential_index(
                    payload["model"], index, payload["ip_address"]
                )
            if profile and hasattr(self.parent, "set_device_connection_profile"):
                self.parent.set_device_connection_profile(
                    payload["model"], profile, payload["ip_address"]
                )
        callback = self._interactive_callbacks.get(
            payload.get("client_token"), (None, None)
        )[0]
        if callable(callback):
            callback(payload.get("value"), payload)

    def _on_interactive_error(self, payload):
        if not self._interactive_payload_is_current(payload):
            return
        callback = self._interactive_callbacks.get(
            payload.get("client_token"), (None, None)
        )[1]
        if callable(callback):
            callback(payload)
        elif not payload.get("quiet"):
            QMessageBox.warning(
                self,
                "Ошибка управления кодеком",
                payload.get("message", "Не удалось выполнить операцию."),
            )

    def _on_interactive_dropped(self, payload):
        self._interactive_callbacks.pop(payload.get("client_token"), None)

    def _on_interactive_finished(self, payload):
        self._interactive_callbacks.pop(payload.get("client_token"), None)

    def _on_interactive_identity_changed(self, *_args):
        self.stop_te20_monitor_audio_polling()
        self.interactive_controller.invalidate_context()

    def shutdown_interactive_controller(self):
        self.stop_te20_monitor_audio_polling()
        for timer_name in (
            "volume_refresh_timer",
            "presentation_refresh_timer",
            "wake_countdown_timer",
        ):
            timer = getattr(self, timer_name, None)
            if timer is not None:
                timer.stop()
        self.interactive_controller.shutdown(wait=False)

    def _is_deleted_widget(self, widget):
        if widget is None:
            return True
        if sip is not None and sip.isdeleted(widget):
            return True
        try:
            widget.parent()
        except RuntimeError:
            return True
        return False

    def _is_te20_device(self):
        return bool(
            self.parent
            and hasattr(self.parent, 'device_combo')
            and self.parent.device_combo.currentText() == "Huawei TE20"
        )

    def _uses_microphone_mute_control(self):
        return bool(
            self.parent
            and hasattr(self.parent, 'device_combo')
            and self.parent.device_combo.currentText() in {"Huawei TE20", "Huawei TE40", "Polycom RPG 310"}
        )

    def _microphone_param_name(self):
        return "Mute микрофона" if self._uses_microphone_mute_control() else "Громкость микрофона"

    def _microphone_param_names(self):
        return ("Громкость микрофона", "Mute микрофона")

    def _format_microphone_mute_state(self, mute_state):
        text = str(mute_state).strip().lower()
        if text.startswith("off") or "включ" in text or "unmuted" in text:
            return "Unmuted"
        if text.startswith("on") or "выключ" in text or "muted" in text:
            return "Muted"
        return str(mute_state)

    def _reset_param_widget_refs(self):
        self.param_widgets = []
        self.presentation_buttons = {}
        self.sip_fix_buttons = []
        self.volume_buttons = {}
        self.mute_buttons = {}
        self.wake_buttons = {}
        self.wake_countdown_labels = {}
        self.parameter_rows = {}
        self.sip_status_indicators = {}

    def clear_data(self):
        """Очистка данных перед новой загрузкой"""
        # Если есть таблицы - очищаем их
        if hasattr(self, 'table'):
            self.table.clearContents()

        self.volume_values.clear()
        self.last_unmuted_volume.clear()
        self.microphone_mute_state = None
        self.stop_te20_monitor_audio_polling()
        self._stop_te20_wake_countdown()
        self._te20_is_sleeping = False

        for button in self.mute_buttons.values():
            if self._is_deleted_widget(button):
                continue
            button.setText("—")
            button.setVisible(True)
        for buttons in self.volume_buttons.values():
            for button in buttons.values():
                if self._is_deleted_widget(button):
                    continue
                button.setVisible(True)

        for _, value_widget in self.param_widgets:
            if not self._is_deleted_widget(value_widget):
                value_widget.setText("—")
                self._set_widget_state(value_widget, "inactive")
        self._set_sip_indicator("inactive")
        
        # Если есть метки с данными - очищаем их
        for widget in self.findChildren(QLabel):
            # Очищаем только те метки, которые отображают данные
            if widget.property("data_field") is True:
                widget.setText("—")
        
        # Показываем статус загрузки
        if hasattr(self, 'status_label'):
            self.status_label.setText("Загрузка данных...")

    def _build_control_button(self, text, min_width=48, max_width=48):
        button = SemanticButton(text, "secondary")
        button.setMinimumWidth(min_width)
        button.setMaximumWidth(max_width)
        return button


    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("codecScrollArea")
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.param_widget = QWidget()
        self.param_widget.setObjectName("codecContent")
        self.param_layout = QVBoxLayout(self.param_widget)
        self.param_layout.setSpacing(SPACING["md"])
        self.param_layout.setContentsMargins(
            SPACING["lg"], SPACING["md"], SPACING["lg"], SPACING["lg"]
        )

        self.scroll_area.setWidget(self.param_widget)
        layout.addWidget(self.scroll_area)
        self.update_parameters_display()


    def update_parameters_display(self):
        """Перестраивает карточки, сохраняя публичные ссылки на controls."""
        while self.param_layout.count():
            child = self.param_layout.takeAt(0)
            if child.widget():
                child.widget().hide()
                child.widget().deleteLater()

        self._reset_param_widget_refs()

        firmware_params = [
            "Версия прошивки",
        ]
        primary_params = [
            "Модель кодеков",
            "Серийный номер",
            "MAC адрес",
        ]
        secondary_params = [
            "SIP регистрация",
            "SIP адрес",
            "Время работы",
        ]

        control_params = [
            "Статус звонка",
            "Статус презентации",
            self._microphone_param_name(),
            "Громкость динамиков",
            "Статус камеры",
            "Статус микрофона",
        ]

        show_te20_monitor_audio_fields = self._should_show_te20_monitor_audio_fields()
        if show_te20_monitor_audio_fields:
            control_params.extend([
                "Звук в помещении (микрофон)",
                "Звук из динамиков (выход кодека)",
            ])
        self._show_te20_monitor_audio_fields = show_te20_monitor_audio_fields
        control_params.append(self.CALL_LOG_PARAM)

        self.info_card = SectionCard("Основная информация", "▣", self.param_widget)
        self.info_columns_widget = QWidget(self.info_card)
        self.info_grid = QGridLayout(self.info_columns_widget)
        self.info_grid.setContentsMargins(0, 0, 0, 0)
        self.info_grid.setHorizontalSpacing(SPACING["md"])
        self.info_grid.setVerticalSpacing(0)
        self.info_firmware_column = self._create_param_column(firmware_params)
        self.info_left_column = self._create_param_column(primary_params)
        self.info_right_column = self._create_param_column(secondary_params)
        self.info_card.add_widget(self.info_columns_widget)

        self.controls_card = SectionCard("Параметры и управление", "⚙", self.param_widget)
        self.create_param_block(
            control_params,
            self.controls_card.body_layout,
            aligned_controls=True,
        )

        self.param_layout.addWidget(self.info_card)
        self.param_layout.addWidget(self.controls_card)
        self.param_layout.addStretch(1)
        self._apply_responsive_layout()


    def _create_param_column(self, params):
        column = QWidget(self.info_columns_widget)
        column_layout = QVBoxLayout(column)
        column_layout.setContentsMargins(0, 0, 0, 0)
        column_layout.setSpacing(0)
        self.create_param_block(params, column_layout, compact_info=True)
        return column

    def create_param_block(
        self,
        params,
        target_layout=None,
        compact_info=False,
        aligned_controls=False,
    ):
        """Создаёт строки через общие компоненты этапа 4."""
        if target_layout is None:
            target_layout = self.param_layout

        for param_name in params:
            row = ParameterRow(param_name, "—", self.param_widget)
            row.setObjectName("codecParameterRow")
            row.setProperty("alignedControls", aligned_controls)
            row.value_display.setProperty("data_field", True)
            row.value_display.setAccessibleName(param_name)
            self.parameter_rows[param_name] = row
            value_label = row.value_display
            if aligned_controls:
                value_label.setMaximumWidth(16777215)
            if compact_info:
                value_label.setProperty("density", "compact")
                if param_name == "Версия прошивки":
                    value_label.setMaximumWidth(16777215)
                row.name_label.setSizePolicy(
                    QSizePolicy.Ignored,
                    QSizePolicy.Preferred,
                )
                row_layout = row.layout()
                margins = row_layout.contentsMargins()
                row_layout.setContentsMargins(
                    margins.left(),
                    (
                        SPACING["sm"]
                        if param_name == "Версия прошивки"
                        else SPACING["xs"]
                    ),
                    margins.right(),
                    SPACING["xs"],
                )
                value_label.setMinimumWidth(
                    round(value_label.minimumWidth() * self.INFO_VALUE_WIDTH_SCALE)
                    if param_name == "SIP регистрация"
                    else (
                        self.INFO_WIDE_VALUE_WIDTH
                        if param_name in {"SIP адрес", "Время работы"}
                        else self.INFO_VALUE_PREFERRED_WIDTH
                    )
                )
                if param_name != "Версия прошивки":
                    value_label.setMaximumWidth(
                        round(value_label.maximumWidth() * self.INFO_VALUE_WIDTH_SCALE)
                    )
                value_label.setMinimumHeight(SIZES["control_height_compact"])
                value_label.setMaximumHeight(SIZES["control_height_compact"])

            if param_name == self.CALL_LOG_PARAM:
                value_label.setVisible(False)
                call_log_btn = SemanticButton("Открыть журнал", "primary", row)
                call_log_btn.clicked.connect(self.open_call_log_window)
                row.add_action(call_log_btn)
            elif param_name == "SIP регистрация":
                value_label.setVisible(False)
                indicator = SIPRegistrationIndicator(row)
                indicator.setToolTip("Статус SIP-регистрации")
                fix_btn = SemanticButton("Исправить", "danger", row)
                fix_btn.setObjectName("sipFixButton")
                fix_btn.setVisible(False)
                fix_btn.clicked.connect(self.on_fix_sip_clicked)
                row.add_action(indicator)
                row.add_action(fix_btn)
                self.sip_status_indicators[param_name] = indicator
                self.sip_fix_buttons.append((value_label, fix_btn))
            elif param_name == "Статус презентации":
                presentation_off_btn = SemanticButton("Выкл", "secondary", row)
                presentation_off_btn.setCheckable(True)
                presentation_off_btn.clicked.connect(
                    lambda checked=False, name=param_name: self.on_presentation_button_clicked(name, "off")
                )
                presentation_on_btn = SemanticButton("Вкл", "secondary", row)
                presentation_on_btn.setCheckable(True)
                presentation_on_btn.clicked.connect(
                    lambda checked=False, name=param_name: self.on_presentation_button_clicked(name, "on")
                )
                row.add_action(presentation_on_btn)
                row.add_action(presentation_off_btn)
                self.presentation_buttons[param_name] = {"on": presentation_on_btn, "off": presentation_off_btn}
            elif param_name == "Громкость динамиков":
                mute_btn = self._build_control_button("Мьют", min_width=72, max_width=86)
                mute_btn.setCheckable(True)
                mute_btn.clicked.connect(lambda checked, name=param_name: self.on_mute_button_clicked(name))
                volume_down_btn = self._build_control_button("-")
                volume_down_btn.clicked.connect(lambda checked, name=param_name: self.on_volume_button_clicked(name, "down"))
                volume_up_btn = self._build_control_button("+")
                volume_up_btn.clicked.connect(lambda checked, name=param_name: self.on_volume_button_clicked(name, "up"))
                row.add_action(mute_btn)
                row.add_action(volume_down_btn)
                row.add_action(volume_up_btn)
                self.mute_buttons[param_name] = mute_btn
                self.volume_buttons[param_name] = {"up": volume_up_btn, "down": volume_down_btn}
            elif param_name in self._microphone_param_names():
                mute_btn = self._build_control_button("Мьют", min_width=72, max_width=86)
                mute_btn.setCheckable(True)
                mute_btn.clicked.connect(lambda checked, name=param_name: self.on_mute_button_clicked(name))
                row.add_action(mute_btn)
                self.mute_buttons[param_name] = mute_btn
                if param_name == "Громкость микрофона":
                    volume_down_btn = self._build_control_button("-")
                    volume_down_btn.clicked.connect(lambda checked, name=param_name: self.on_volume_button_clicked(name, "down"))
                    volume_up_btn = self._build_control_button("+")
                    volume_up_btn.clicked.connect(lambda checked, name=param_name: self.on_volume_button_clicked(name, "up"))
                    row.add_action(volume_down_btn)
                    row.add_action(volume_up_btn)
                    self.volume_buttons[param_name] = {"up": volume_up_btn, "down": volume_down_btn}
                else:
                    self.volume_buttons[param_name] = {}
            elif param_name == "Звук в помещении (микрофон)":
                if self._is_te20_device():
                    wake_btn = SemanticButton("Разбудить", "primary", row)
                    wake_btn.clicked.connect(self.on_wake_te20_clicked)
                    wake_btn.setVisible(False)
                    row.add_action(wake_btn)
                    self.wake_buttons[param_name] = wake_btn
                    countdown_label = StatusIndicator(
                        "warning",
                        "",
                        True,
                        row,
                    )
                    countdown_label.setAlignment(Qt.AlignCenter)
                    countdown_label.setVisible(False)
                    row.add_action(countdown_label)
                    self.wake_countdown_labels[param_name] = countdown_label

            if param_name != self.CALL_LOG_PARAM:
                self.param_widgets.append((param_name, value_label))
            if aligned_controls and row.action_layout.count() == 0:
                row.actions_widget.setVisible(False)
            target_layout.addWidget(row)

        if aligned_controls:
            self._align_control_rows(self.CONTROL_LABEL_WIDTH)

    def _align_control_rows(self, label_width):
        for row in self.parameter_rows.values():
            if not row.property("alignedControls"):
                continue
            row.name_label.setMinimumWidth(label_width)
            row.name_label.setMaximumWidth(label_width)
            row_layout = row.layout()
            row_layout.setColumnStretch(0, 0)
            row_layout.setColumnStretch(1, 1)
            row_layout.setColumnStretch(2, 0)

    def _align_firmware_value_to_info_columns(self):
        """Match firmware value edges to the two detail value columns."""
        firmware_row = self.parameter_rows.get("Версия прошивки")
        model_row = self.parameter_rows.get("Модель кодеков")
        sip_row = self.parameter_rows.get("SIP адрес")
        if not firmware_row or not model_row or not sip_row:
            return

        common_parent = self.info_columns_widget
        firmware_origin = firmware_row.mapTo(
            common_parent,
            QPoint(0, 0),
        ).x()
        desired_left = model_row.value_display.mapTo(
            common_parent,
            QPoint(0, 0),
        ).x()
        desired_right = sip_row.value_display.mapTo(
            common_parent,
            QPoint(sip_row.value_display.width(), 0),
        ).x()
        desired_width = desired_right - desired_left

        row_layout = firmware_row.layout()
        margins = row_layout.contentsMargins()
        name_width = (
            desired_left
            - firmware_origin
            - margins.left()
            - row_layout.horizontalSpacing()
        )
        if name_width <= 0 or desired_width <= 0:
            return

        firmware_row.name_label.setFixedWidth(name_width)
        firmware_row.value_display.setFixedWidth(desired_width)
        firmware_row.actions_widget.setFixedWidth(0)
        row_layout.setColumnStretch(0, 0)
        row_layout.setColumnStretch(1, 0)
        row_layout.setColumnStretch(2, 0)
        row_layout.activate()

    def _apply_responsive_layout(self):
        if not hasattr(self, "info_grid"):
            return
        available_width = self.scroll_area.viewport().width()
        narrow = available_width < 840
        self._align_control_rows(
            self.CONTROL_LABEL_WIDTH_NARROW
            if narrow
            else self.CONTROL_LABEL_WIDTH
        )
        positions = (
            (
                (self.info_firmware_column, 0, 0, 1, 1),
                (self.info_left_column, 1, 0, 1, 1),
                (self.info_right_column, 2, 0, 1, 1),
            )
            if narrow
            else (
                (self.info_firmware_column, 0, 0, 1, 2),
                (self.info_left_column, 1, 0, 1, 1),
                (self.info_right_column, 1, 1, 1, 1),
            )
        )
        for widget, row, column, row_span, column_span in positions:
            self.info_grid.removeWidget(widget)
            self.info_grid.addWidget(
                widget,
                row,
                column,
                row_span,
                column_span,
            )
        self.info_grid.setColumnStretch(0, 1)
        self.info_grid.setColumnStretch(1, 0 if narrow else 1)
        self.info_grid.invalidate()
        self.info_grid.activate()
        self._align_firmware_value_to_info_columns()
        QTimer.singleShot(
            0,
            self._align_firmware_value_to_info_columns,
        )
        self.info_columns_widget.updateGeometry()
        self.info_card.updateGeometry()
        self.param_layout.invalidate()
        self.param_layout.activate()
        self.param_widget.updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_layout()


    def open_call_log_window(self):
        if not hasattr(self, 'call_log_window') or self._is_deleted_widget(self.call_log_window):
            self.call_log_window = CallLogWindow(self, self.colors)

        self.call_log_window.clear_records()
        self.call_log_window.show()
        self.call_log_window.raise_()
        self.call_log_window.activateWindow()

        device_name = self.parent.device_combo.currentText() if self.parent else ""
        ip_address = self.parent.ip_entry.text().strip() if self.parent else ""

        if device_name not in {"Huawei TE20", "Huawei TE40", "CloudLink Bar 310", "Polycom RPG 310"}:
            self.call_log_window.status_label.setText("Получение журнала звонков для этого устройства будет добавлено позже.")
            return

        creds, current_idx, creds_list = self._get_current_device_credentials(device_name, ip_address)
        if creds is None:
            QMessageBox.warning(self, "Ошибка", f"Не найдены credentials для {device_name}")
            return

        if device_name == "Polycom RPG 310":
            self._start_polycom_call_log_load(
                ip_address,
                creds["username"],
                creds["password"],
            )
            return

        self.call_log_window.status_label.setText("Загрузка журнала звонков...")

        def on_records(records, _payload):
            if not self._is_deleted_widget(self.call_log_window):
                self.call_log_window.set_call_records(records or [])

        def on_error(payload):
            if not self._is_deleted_widget(self.call_log_window):
                self.call_log_window.status_label.setText(
                    "Не удалось загрузить журнал звонков."
                )
            QMessageBox.critical(
                self,
                "Ошибка",
                payload.get("message", "Не удалось получить журнал звонков."),
            )

        self._submit_interactive(
            InteractiveOperation(
                kind="huawei_call_log",
                method="get_call_records",
                semantic=OperationSemantic.READ_ONLY,
            ),
            on_records,
            on_error,
        )

    def _start_polycom_call_log_load(self, ip_address, username, password):
        if getattr(self, "_polycom_call_log_loading", False):
            return

        from core.worker import PolycomCallLogWorker
        from handlers.polycom.rpg310 import PolycomRPG310Handler

        self._polycom_call_log_loading = True
        self.call_log_window.status_label.setText("Загрузка журнала звонков...")
        progress_dialog = self._show_polycom_command_progress(
            "Загрузка журнала звонков Polycom..."
        )
        request_key = ("Polycom RPG 310", ip_address)
        worker = PolycomCallLogWorker(
            PolycomRPG310Handler,
            {
                "ip_address": ip_address,
                "port": 443,
                "username": username,
                "password": password,
            },
        )
        self._polycom_call_log_worker = worker
        import weakref

        screen_ref = weakref.ref(self)

        def widget_deleted(widget):
            return widget is None or bool(sip and sip.isdeleted(widget))

        def request_is_current():
            screen = screen_ref()
            if (
                screen is None
                or widget_deleted(screen)
                or not screen.parent
            ):
                return False
            return (
                screen.parent.device_combo.currentText(),
                screen.parent.ip_entry.text().strip(),
            ) == request_key

        def on_result(payload):
            screen = screen_ref()
            if (
                screen is not None
                and request_is_current()
                and not widget_deleted(screen.call_log_window)
                and screen.call_log_window.isVisible()
            ):
                screen.call_log_window.set_call_records(
                    payload.get("records", [])
                )

        def on_error(error_info):
            screen = screen_ref()
            if (
                screen is None
                or not request_is_current()
                or widget_deleted(screen.call_log_window)
                or not screen.call_log_window.isVisible()
            ):
                return
            _error_type, message, _traceback_text = error_info
            screen.call_log_window.status_label.setText(
                "Не удалось загрузить журнал звонков."
            )
            QMessageBox.critical(
                screen,
                "Ошибка",
                f"Не удалось получить журнал звонков:\n{message}",
            )

        def on_finished():
            screen = screen_ref()
            if screen is not None and not widget_deleted(screen):
                screen._polycom_call_log_loading = False
                screen._polycom_call_log_worker = None
                screen._hide_polycom_command_progress(progress_dialog)

        worker.signals.result.connect(on_result)
        worker.signals.error.connect(on_error)
        worker.signals.finished.connect(on_finished)
        QThreadPool.globalInstance().start(worker)


    def add_divider(self):
        """Совместимый helper: разделение теперь задаёт общая тема строк."""
        return None


    def update_data(self, data):
        """Обновление данных на экране"""
        
        # Преобразуем данные из парсера в формат GUI
        show_te20_monitor_audio_fields = self._should_show_te20_monitor_audio_fields()
        if show_te20_monitor_audio_fields != self._show_te20_monitor_audio_fields:
            self.update_parameters_display()

        display_data = self._convert_parser_data_to_gui(data)
        self._sync_te20_monitor_audio_polling()
        
        # Для отладки
        print("Данные из парсера:", data)
        print("Данные для GUI:", display_data)
        self._set_te20_monitor_audio_sleep_state(
            self._should_show_te20_monitor_audio_fields() and data.get('power_status') == 'Sleep'
        )
        self.microphone_mute_state = data.get('mic_mute')
        
        for param_name, value_label in self.param_widgets:
            if param_name in display_data:
                if self._te20_is_sleeping and param_name in self.TE20_SLEEP_UNAVAILABLE_FIELDS:
                    continue
                value = display_data[param_name]
                value_label.setText(str(value))
                self._set_widget_state(value_label, "normal")
                if param_name == "Громкость динамиков" or param_name in self._microphone_param_names():
                    numeric_value = self._extract_numeric_value(value)
                    if numeric_value is not None:
                        self.volume_values[param_name] = numeric_value
                        self._remember_unmuted_volume(param_name, numeric_value)
                    if param_name in self._microphone_param_names():
                        self._set_microphone_volume_controls_visible(
                            not self._is_microphone_disconnected_value(value)
                        )
                
                if param_name == "SIP регистрация" and value == "Не зарегистрирован":
                    self._set_widget_state(value_label, "error")
                    self._set_sip_indicator("danger")
                    for val_label, btn in self.sip_fix_buttons:
                        if val_label is value_label:
                            btn.setVisible(True)
                            break
                elif param_name == "SIP регистрация":
                    self._set_widget_state(value_label, "success")
                    self._set_sip_indicator("success")
                    for val_label, btn in self.sip_fix_buttons:
                        if val_label is value_label:
                            btn.setVisible(False)
                            break
                elif param_name == "Статус звонка" and value == "В звонке":
                    self._set_widget_state(value_label, "success")
                elif param_name == "Статус микрофона" and value == "Выключен":
                    self._set_widget_state(value_label, "warning")
                if param_name == "Статус презентации":
                    self._sync_presentation_button_state(value)
            else:
                if self._te20_is_sleeping and param_name in self.TE20_SLEEP_UNAVAILABLE_FIELDS:
                    continue
                value_label.setText("—")
                self._set_widget_state(value_label, "inactive")
                for val_label, btn in self.sip_fix_buttons:
                    if val_label is value_label:
                        btn.setVisible(False)
                        self._set_sip_indicator("inactive")
                        break

        if (
            self.parent
            and self.parent.device_combo.currentText() == "Polycom RPG 310"
        ):
            self._apply_polycom_microphone_connection_state()

        self.refresh_all_mute_buttons()

    def _set_widget_state(self, widget, state):
        if hasattr(widget, "set_state"):
            widget.set_state(state)
            return
        widget.setProperty("uiState", state)
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()

    def _set_sip_indicator(self, status):
        indicator = self.sip_status_indicators.get("SIP регистрация")
        if not self._is_deleted_widget(indicator):
            indicator.set_status(status)

    def _sync_presentation_button_state(self, value):
        normalized = str(value).strip().lower()
        selected = None
        if normalized in {"демонстрируется", "start", "started", "auxopen"}:
            selected = "on"
        elif normalized in {"не демонстрируется", "stop", "stopped", "auxclose"}:
            selected = "off"
        for direction, button in self.presentation_buttons.get("Статус презентации", {}).items():
            checked = direction == selected
            button.setChecked(checked)
            button.set_role("active" if checked else "secondary")


    def _extract_numeric_value(self, value):
        """Преобразует строку вида '12' или '12%' в число."""
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            cleaned = value.strip().rstrip('%')
            try:
                return int(cleaned)
            except ValueError:
                return None
        return None

    def _set_microphone_volume_controls_visible(self, visible):
        for param_name in self._microphone_param_names():
            mute_button = self.mute_buttons.get(param_name)
            if mute_button is not None:
                mute_button.setVisible(visible)

            for button in self.volume_buttons.get(param_name, {}).values():
                button.setVisible(visible)

    def _is_microphone_disconnected_value(self, value):
        return str(value).strip().lower() in {
            "микрофон не подключён",
            "не подключён",
            "не подключен",
            "не подключено",
            "не доступно",
            "недоступно",
            "disconnected",
            "n/a",
        }

    def _apply_polycom_microphone_connection_state(self):
        status = self._get_microphone_status_text().strip().lower()
        connected = status in {"подключён", "подключен", "connected"}
        disconnected = status in {
            "микрофон не подключён",
            "не подключён",
            "не подключен",
            "не подключено",
            "disconnected",
        }

        self._set_microphone_volume_controls_visible(connected)
        if connected:
            return

        mute_row = self.parameter_rows.get(self._microphone_param_name())
        if mute_row is None:
            return
        mute_row.value_display.setText(
            "Не подключено" if disconnected else "Не определено"
        )
        self._set_widget_state(mute_row.value_display, "inactive")

    def on_fix_sip_clicked(self):
        """Обработчик нажатия кнопки "Исправить" для SIP регистрации"""
        # Получаем IP адрес из главного окна
        ip_address = self.parent.ip_entry.text().strip() if self.parent else None
        device_name = self.parent.device_combo.currentText() if self.parent else None
        
        if not ip_address or not device_name:
            print("Не удалось получить IP адрес или имя устройства")
            return
        
        # Вызываем обработчик в главном окне
        if hasattr(self.parent, 'on_fix_sip_registration'):
            self.parent.on_fix_sip_registration(ip_address, device_name)
        else:
            print("Метод on_fix_sip_registration не найден в главном окне")


    def on_volume_button_clicked(self, param_name, direction):
        """Обработчик нажатия кнопки изменения громкости"""
        print(f"Нажата кнопка {direction} для {param_name}")

        if param_name in self.volume_buttons:
            self.adjust_volume(param_name, direction)

    def _get_param_label_widget(self, param_name):
        for name_label, value_label in self.param_widgets:
            if name_label == param_name:
                return value_label
        return None

    def _get_microphone_status_text(self):
        label = self._get_param_label_widget("Статус микрофона")
        return label.text().strip() if label else ""

    def _is_param_muted(self, param_name):
        if param_name == "Громкость динамиков":
            value = self._get_current_volume_value(param_name)
            return value == 0 if value is not None else None

        if param_name in self._microphone_param_names():
            mute_state = str(self.microphone_mute_state or "").strip().lower()
            if mute_state:
                if (
                    mute_state.startswith("off")
                    or "включ" in mute_state
                    or "unmuted" in mute_state
                ):
                    return False
                if (
                    mute_state.startswith("on")
                    or "выключ" in mute_state
                    or "muted" in mute_state
                ):
                    return True
            status_text = self._get_microphone_status_text().lower()
            if status_text in {"выключен", "закрыто", "muted", "off"}:
                return True
            if status_text in {"включен", "открыто", "unmuted", "on"}:
                return False
            value = self._get_current_volume_value(param_name)
            return value == 0 if value is not None else None

        return None

    def _remember_unmuted_volume(self, param_name, value):
        if value is None:
            return
        if value > 0:
            self.last_unmuted_volume[param_name] = int(value)

    def _get_restore_volume(self, param_name):
        remembered = self.last_unmuted_volume.get(param_name)
        if isinstance(remembered, int) and remembered > 0:
            return remembered

        min_volume, max_volume = self._get_volume_range(param_name)
        preferred = 1 if min_volume <= 1 <= max_volume else max(min_volume, 0)
        if preferred == 0 and max_volume > 0:
            preferred = min(max_volume, 1)
        return preferred

    def update_mute_button_state(self, param_name, muted=None):
        button = self.mute_buttons.get(param_name)
        if not button:
            return

        if muted is None:
            muted = self._is_param_muted(param_name)

        if muted is True:
            button.setText("Мьют")
            button.setChecked(True)
            configure_button(button, "active")
        elif muted is False:
            button.setText("Мьют")
            button.setChecked(False)
            configure_button(button, "secondary")
        else:
            button.setText("—")
            button.setChecked(False)
            configure_button(button, "secondary")

    def refresh_all_mute_buttons(self):
        self.update_mute_button_state("Громкость динамиков")
        self.update_mute_button_state(self._microphone_param_name())

    def on_mute_button_clicked(self, param_name):
        print(f"Нажата кнопка mute для {param_name}")

        muted = self._is_param_muted(param_name)
        if muted is None:
            return

        current_value = self._get_current_volume_value(param_name)
        if muted:
            restore_value = self._get_restore_volume(param_name)
            self.set_volume_value(
                param_name,
                restore_value,
                original=current_value,
                relative=True,
            )
        else:
            self._remember_unmuted_volume(param_name, current_value)
            self.set_volume_value(
                param_name,
                0,
                original=current_value,
                relative=True,
            )

    def _schedule_presentation_buttons_enable(self, param_name):
        previous_timer = self._presentation_enable_timers.pop(param_name, None)
        if previous_timer is not None:
            previous_timer.stop()
            previous_timer.deleteLater()

        timer = QTimer(self)
        timer.setSingleShot(True)

        def enable_buttons():
            self._presentation_enable_timers.pop(param_name, None)
            self.set_presentation_buttons_enabled(param_name, True)
            timer.deleteLater()

        timer.timeout.connect(enable_buttons)
        self._presentation_enable_timers[param_name] = timer
        timer.start(1500)

    def on_presentation_button_clicked(self, param_name, direction):
        """Обработчик нажатия кнопок управления презентацией"""
        print(f"Нажата кнопка presentation {direction} для {param_name}")

        if param_name in self.presentation_buttons:
            self.set_presentation_buttons_enabled(param_name, False)
            self._schedule_presentation_buttons_enable(param_name)
            self.set_presentation_state(direction)

    def _is_polycom_selected(self):
        return bool(
            self.parent
            and hasattr(self.parent, "device_combo")
            and self.parent.device_combo.currentText() == "Polycom RPG 310"
        )

    def _show_polycom_command_progress(self, message):
        if not self._is_polycom_selected():
            return None
        if self._polycom_command_progress is not None:
            return self._polycom_command_progress

        dialog = QProgressDialog(message, "", 0, 0, self)
        dialog.setWindowTitle("Выполнение команды Polycom")
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)
        dialog.setCancelButton(None)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self._polycom_command_progress = dialog
        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)
        return dialog

    def _hide_polycom_command_progress(self, dialog):
        if dialog is None:
            return
        if not self._is_deleted_widget(dialog):
            dialog.close()
            dialog.deleteLater()
        if self._polycom_command_progress is dialog:
            self._polycom_command_progress = None

    def set_presentation_state(self, direction):
        """Submit desired presentation state without blocking the GUI thread."""
        ip_address = self.parent.ip_entry.text().strip() if self.parent else None
        device_name = self.parent.device_combo.currentText() if self.parent else None

        if not ip_address or not device_name:
            print("Не удалось получить IP адрес или имя устройства для управления презентацией")
            return

        command_map = {
            "on": "Start",
            "off": "Stop",
        }
        command = command_map.get(direction)
        if command is None:
            print(f"Неизвестное направление управления презентацией: {direction}")
            return

        self._show_presentation_terminal(device_name, ip_address, command)
        if command == "Start" and device_name in {
            "Huawei TE20",
            "Huawei TE40",
            "CloudLink Bar 310",
        }:
            self._submit_interactive(
                InteractiveOperation(
                    kind="presentation_sleep_read",
                    method="get_sleep_mode",
                    semantic=OperationSemantic.READ_ONLY,
                    quiet=True,
                ),
                lambda sleep_mode, _payload: self._continue_presentation_after_sleep_read(
                    command, sleep_mode
                ),
                lambda _payload: self._submit_presentation_command(command),
            )
            return
        self._submit_presentation_command(command)

    def _continue_presentation_after_sleep_read(self, command, sleep_mode):
        if sleep_mode != "On":
            self._submit_presentation_command(command)
            return
        reply = QMessageBox.question(
            self,
            "Режим сна",
            "Устройство в состоянии сна, разбудить его ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            self._finish_presentation_terminal("cancelled while device was sleeping")
            return
        self._submit_interactive(
            InteractiveOperation(
                kind="presentation_wake",
                method="wake_up",
                semantic=OperationSemantic.DESIRED_STATE,
                readback_method="get_sleep_mode",
                target="Off",
                original="On",
            ),
            lambda _value, _payload: self._submit_presentation_command(command),
            lambda payload: self._finish_presentation_terminal(
                f"wake failed: {payload.get('category')}"
            ),
        )

    def _submit_presentation_command(self, command):
        opposite = "Stop" if command == "Start" else "Start"

        def on_result(_value, _payload):
            self._finish_presentation_terminal(f"completed successfully: {command}")
            self.update_presentation_display(command)
            self.schedule_presentation_refresh()

        def on_error(payload):
            self._finish_presentation_terminal(
                f"failed: {payload.get('category', 'command_error')}"
            )
            for name in self.presentation_buttons:
                self.set_presentation_buttons_enabled(name, True)
            QMessageBox.warning(
                self,
                "Ошибка",
                payload.get("message", "Не удалось изменить презентацию."),
            )

        self._submit_interactive(
            InteractiveOperation(
                kind="presentation_set",
                method="set_presentation",
                args=(command,),
                semantic=OperationSemantic.DESIRED_STATE,
                readback_method="get_presentation_status",
                target=command,
                original=opposite,
            ),
            on_result,
            on_error,
        )

    def _show_presentation_terminal(self, device_name, ip_address, command):
        if self.parent and hasattr(self.parent, 'show_codec_terminal'):
            self.parent.show_codec_terminal(device_name, ip_address, command, reset=True)

    def _append_presentation_terminal_log(self, message):
        if self.parent and hasattr(self.parent, 'append_codec_terminal_line'):
            self.parent.append_codec_terminal_line(message)

    def _finish_presentation_terminal(self, message):
        if self.parent and hasattr(self.parent, 'finish_codec_terminal'):
            self.parent.finish_codec_terminal(message)

    def _prepare_sleeping_device_for_presentation(self, handler):
        get_sleep_mode = getattr(handler, 'get_sleep_mode', None)
        if not callable(get_sleep_mode):
            return True

        try:
            sleep_mode = get_sleep_mode()
        except Exception as e:
            self._append_presentation_terminal_log(
                f"[sleep] failed to read sleep mode: {type(e).__name__}: {str(e)}"
            )
            return True

        self._append_presentation_terminal_log(f"[sleep] current mode: {sleep_mode}")
        if sleep_mode != 'On':
            return True

        reply = QMessageBox.question(
            self,
            "Режим сна",
            "Устройство в состоянии сна, разбудить его ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply != QMessageBox.Yes:
            self._finish_presentation_terminal("cancelled by user while device was sleeping")
            return False

        wake_up = getattr(handler, 'wake_up', None)
        if callable(wake_up):
            wake_success = wake_up()
            self._append_presentation_terminal_log(f"[sleep] wake command result: {wake_success}")
            if not wake_success:
                self._finish_presentation_terminal("wake command failed")
                QMessageBox.warning(self, "Ошибка", "Не удалось разбудить устройство")
                return False

        if not self._wait_until_device_wakes(handler):
            self._finish_presentation_terminal("device did not leave sleep mode after wake")
            QMessageBox.warning(self, "РћС€РёР±РєР°", "РЈСЃС‚СЂРѕР№СЃС‚РІРѕ РЅРµ РІС‹С€Р»Рѕ РёР· СЂРµР¶РёРјР° СЃРЅР° РїРѕСЃР»Рµ РєРѕРјР°РЅРґС‹ РїСЂРѕР±СѓР¶РґРµРЅРёСЏ")
            return False

        self._run_presentation_countdown(2)
        self._resume_te20_monitor_audio_after_wake()
        return True

    def _wait_until_device_wakes(self, handler, timeout_seconds=15):
        get_sleep_mode = getattr(handler, 'get_sleep_mode', None)
        if not callable(get_sleep_mode):
            return True

        for second in range(timeout_seconds):
            try:
                sleep_mode = get_sleep_mode()
            except Exception as e:
                self._append_presentation_terminal_log(
                    f"[sleep] wake poll failed: {type(e).__name__}: {str(e)}"
                )
                return False

            self._append_presentation_terminal_log(
                f"[sleep] wake poll {second + 1}/{timeout_seconds}: {sleep_mode}"
            )
            if sleep_mode != 'On':
                self._append_presentation_terminal_log("[sleep] device is awake")
                return True

            loop = QEventLoop(self)
            QTimer.singleShot(1000, loop.quit)
            loop.exec_()

        return False

    def _run_presentation_countdown(self, seconds):
        dialog = QProgressDialog(self)
        dialog.setWindowTitle("Пробуждение устройства")
        dialog.setCancelButton(None)
        dialog.setMinimum(0)
        dialog.setMaximum(seconds)
        dialog.setValue(0)
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(True)

        remaining = {'value': seconds}
        loop = QEventLoop(self)
        timer = QTimer(dialog)
        timer.setInterval(1000)

        def update_label():
            dialog.setLabelText(f"Включение презентации через {remaining['value']} сек.")

        def tick():
            remaining['value'] -= 1
            dialog.setValue(seconds - remaining['value'])
            if remaining['value'] <= 0:
                timer.stop()
                dialog.close()
                loop.quit()
            else:
                update_label()

        update_label()
        self._append_presentation_terminal_log(f"[sleep] countdown started: {seconds} sec")
        dialog.show()
        timer.timeout.connect(tick)
        timer.start()
        loop.exec_()
        self._append_presentation_terminal_log("[sleep] countdown completed")

    def set_presentation_buttons_enabled(self, param_name, enabled):
        """Включить или выключить кнопки управления презентацией."""
        buttons = self.presentation_buttons.get(param_name)
        if not buttons:
            return

        for button in buttons.values():
            button.setEnabled(enabled)

    def adjust_volume(self, param_name, direction):
        """Изменение громкости на 1 единицу"""
        min_volume, max_volume = self._get_volume_range(param_name)
        current_volume = self._get_current_volume_value(param_name)
        if current_volume is None:
            current_volume = min_volume
        device_name = (
            self.parent.device_combo.currentText()
            if self.parent and hasattr(self.parent, "device_combo")
            else None
        )
        step = (
            2
            if device_name == "Polycom RPG 310"
            and param_name == "Громкость динамиков"
            else 1
        )

        # Вычисляем новое значение
        if direction == "up":
            new_volume = min(max_volume, current_volume + step)
        else:  # down
            new_volume = max(min_volume, current_volume - step)
        
        print(f"Текущая громкость: {current_volume}, Новое значение: {new_volume}")
        
        # Отправляем команду на устройство через API
        self.set_volume_value(
            param_name,
            new_volume,
            original=current_volume,
            relative=True,
        )
    
    def _get_volume_control_kind(self, param_name):
        if param_name == "Громкость динамиков":
            return "speaker"
        if param_name in self._microphone_param_names():
            return "microphone"
        return None

    def set_volume_value(self, param_name, value, *, original=None, relative=False):
        if self._te20_is_sleeping and param_name in self._microphone_param_names():
            return False

        control_kind = self._get_volume_control_kind(param_name)
        if control_kind == "speaker":
            return self.set_speaker_volume(
                value, original=original, relative=relative
            )
        if control_kind == "microphone":
            return self.set_microphone_volume(
                value, original=original, relative=relative
            )
        return False
    
    def set_speaker_volume(self, value, *, original=None, relative=False):
        """Submit an absolute target, preserving relative-button intent metadata."""
        semantic = (
            OperationSemantic.RELATIVE_AS_ABSOLUTE
            if relative
            else OperationSemantic.ABSOLUTE
        )

        def on_result(_result, _payload):
            self.update_volume_display(value, param_name="Громкость динамиков")
            self.schedule_volume_refresh("Громкость динамиков")

        return self._submit_interactive(
            InteractiveOperation(
                kind="speaker_volume_set",
                method="set_speaker_volume",
                args=(value,),
                semantic=semantic,
                readback_method="get_speaker_volume",
                target=value,
                original=original,
                allow_set_from_any_authoritative=not relative,
            ),
            on_result,
        )

    def set_microphone_volume(self, value, *, original=None, relative=False):
        """Submit mute/gain as an absolute desired state, never as a toggle."""
        uses_mute_state = self._uses_microphone_mute_control()
        if uses_mute_state:
            display_value = "Muted" if int(value) <= 0 else "Unmuted"
            semantic = OperationSemantic.DESIRED_STATE
            reconciliation_original = (
                "Unmuted" if display_value == "Muted" else "Muted"
            )
        else:
            display_value = value
            semantic = (
                OperationSemantic.RELATIVE_AS_ABSOLUTE
                if relative
                else OperationSemantic.ABSOLUTE
            )
            reconciliation_original = original

        def on_result(_result, _payload):
            self.update_volume_display(
                display_value, param_name=self._microphone_param_name()
            )
            self.schedule_volume_refresh(self._microphone_param_name())

        return self._submit_interactive(
            InteractiveOperation(
                kind="microphone_set",
                method="set_microphone_volume",
                args=(value,),
                semantic=semantic,
                readback_method="get_microphone_volume",
                target=display_value,
                original=reconciliation_original,
                allow_set_from_any_authoritative=not relative and not uses_mute_state,
            ),
            on_result,
        )

    def get_speaker_volume(self):
        """Read speaker volume on the serialized background lane."""
        return self._submit_interactive(
            InteractiveOperation(
                kind="speaker_volume_read",
                method="get_speaker_volume",
                semantic=OperationSemantic.READ_ONLY,
                quiet=True,
            ),
            lambda volume, _payload: (
                self.update_volume_display(
                    volume, param_name="Громкость динамиков"
                )
                if volume is not None
                else None
            ),
        )

    def get_microphone_volume(self):
        """Read microphone mute/gain on the serialized background lane."""
        return self._submit_interactive(
            InteractiveOperation(
                kind="microphone_read",
                method="get_microphone_volume",
                semantic=OperationSemantic.READ_ONLY,
                quiet=True,
            ),
            lambda volume, _payload: (
                self.update_volume_display(
                    volume, param_name=self._microphone_param_name()
                )
                if volume is not None
                else None
            ),
        )

    def refresh_pending_volume_status(self):
        self.refresh_volume_status(self._pending_volume_refresh_param)

    def refresh_volume_status(self, param_name):
        control_kind = self._get_volume_control_kind(param_name)
        if control_kind == "speaker":
            return self.get_speaker_volume()
        if control_kind == "microphone":
            return self.get_microphone_volume()
        return None

    def schedule_volume_refresh(self, param_name="Громкость динамиков"):
        if self.parent:
            self.parent.suppress_success_message_once = True
            self.parent.suppress_progress_dialog_once = True
        self._pending_volume_refresh_param = param_name
        self.volume_refresh_timer.start(1500)

    def schedule_presentation_refresh(self):
        self.presentation_refresh_timer.start(1500)

    def refresh_presentation_status(self):
        return self._submit_interactive(
            InteractiveOperation(
                kind="presentation_read",
                method="get_presentation_status",
                semantic=OperationSemantic.READ_ONLY,
                quiet=True,
            ),
            lambda state, _payload: (
                self.update_presentation_display(state)
                if state is not None
                else None
            ),
            lambda payload: self._append_presentation_terminal_log(
                f"[presentation] refresh failed: {payload.get('category')}"
            ),
        )

    def reset_volume_session(self):
        """Invalidate the shared interactive context and all queued old work."""
        self.stop_te20_monitor_audio_polling()
        controller = getattr(self, "interactive_controller", None)
        if controller is not None:
            controller.invalidate_context()

    def _get_volume_range(self, param_name="Громкость динамиков"):
        device_name = self.parent.device_combo.currentText() if self.parent else None
        control_kind = self._get_volume_control_kind(param_name)
        ranges = {
            "speaker": {
                "Huawei TE20": (0, 21),
                "Huawei TE40": (0, 21),
                "CloudLink Bar 310": (0, 15),
                "Polycom RPG 310": (0, 100),
            },
            "microphone": {
                "Huawei TE20": (0, 21),
                "Huawei TE40": (0, 21),
                "CloudLink Bar 310": (0, 15),
                "Polycom RPG 310": (-20, 30),
            },
        }
        return ranges.get(control_kind, {}).get(device_name, (0, 21))

    def _get_current_volume_value(self, param_name):
        """Возвращает текущее значение громкости из кеша или из отображаемой строки."""
        cached_value = self.volume_values.get(param_name)
        if isinstance(cached_value, int):
            return cached_value

        for name_label, value_label in self.param_widgets:
            if name_label == param_name:
                numeric_value = self._extract_numeric_value(value_label.text())
                if numeric_value is not None:
                    self.volume_values[param_name] = numeric_value
                    return numeric_value
                break

        if self.parent and hasattr(self.parent, 'codec_data'):
            device_name = self.parent.device_combo.currentText()
            if device_name in self.parent.codec_data:
                data = self.parent.codec_data[device_name]
                numeric_value = self._extract_numeric_value(data.get(param_name))
                if numeric_value is not None:
                    self.volume_values[param_name] = numeric_value
                    return numeric_value

        return None

    def _should_show_te20_monitor_audio_fields(self):
        if self.parent and hasattr(self.parent, 'device_combo'):
            return self.parent.device_combo.currentText() in {
                "Huawei TE20",
                "Huawei TE40",
            }
        return False

    def _is_codec_screen_active(self):
        if not self.parent:
            return False
        if getattr(self.parent, 'current_screen_type', None) != "codec":
            return False
        if hasattr(self.parent, 'screen_container'):
            return self.parent.screen_container.currentWidget() is self
        return self.isVisible()

    def _sync_te20_monitor_audio_polling(self):
        if self._should_show_te20_monitor_audio_fields() and self._is_codec_screen_active():
            self.start_te20_monitor_audio_polling()
        else:
            self.stop_te20_monitor_audio_polling()

    def start_te20_monitor_audio_polling(self):
        if not self.monitor_audio_timer.isActive():
            self.monitor_audio_timer.start()

    def stop_te20_monitor_audio_polling(self):
        if self.monitor_audio_timer.isActive():
            self.monitor_audio_timer.stop()

    def _set_te20_wake_countdown_visible(self, visible):
        countdown_label = self.wake_countdown_labels.get("Звук в помещении (микрофон)")
        wake_btn = self.wake_buttons.get("Звук в помещении (микрофон)")

        if not self._is_deleted_widget(countdown_label):
            countdown_label.setVisible(visible)

        if not self._is_deleted_widget(wake_btn):
            wake_btn.setVisible(self._te20_is_sleeping and not visible)

    def _stop_te20_wake_countdown(self):
        if self.wake_countdown_timer.isActive():
            self.wake_countdown_timer.stop()
        self._te20_wake_countdown_remaining = 0
        countdown_label = self.wake_countdown_labels.get("Звук в помещении (микрофон)")
        if not self._is_deleted_widget(countdown_label):
            countdown_label.setText("")
        self._set_te20_wake_countdown_visible(False)

    def _start_te20_wake_countdown(self, seconds):
        self.stop_te20_monitor_audio_polling()
        self._te20_wake_countdown_remaining = seconds
        countdown_label = self.wake_countdown_labels.get("Звук в помещении (микрофон)")
        if not self._is_deleted_widget(countdown_label):
            countdown_label.setText(str(seconds))
        self._set_te20_wake_countdown_visible(True)
        if self.parent and hasattr(self.parent, 'append_codec_terminal_line'):
            self._append_te20_monitor_audio_terminal_log(f"[sleep] wake countdown started: {seconds} sec")
        self.wake_countdown_timer.start()

    def _tick_te20_wake_countdown(self):
        if self._te20_wake_countdown_remaining <= 1:
            self._stop_te20_wake_countdown()
            self._append_te20_monitor_audio_terminal_log("[sleep] wake countdown completed")
            self._resume_te20_monitor_audio_after_wake()
            return

        self._te20_wake_countdown_remaining -= 1
        countdown_label = self.wake_countdown_labels.get("Звук в помещении (микрофон)")
        if not self._is_deleted_widget(countdown_label):
            countdown_label.setText(str(self._te20_wake_countdown_remaining))

    def _update_monitor_audio_display(self, mic_value=None, speaker_value=None):
        field_values = {
            "Звук в помещении (микрофон)": mic_value,
            "Звук из динамиков (выход кодека)": speaker_value,
        }
        for param_name, value in field_values.items():
            if value is None:
                continue
            for name_label, value_label in self.param_widgets:
                if name_label == param_name:
                    value_label.setText(
                        format_te20_monitor_audio_level(value)
                    )
                    self._set_widget_state(value_label, "normal")
                    break

    def _resume_te20_monitor_audio_after_wake(self):
        self._set_te20_monitor_audio_sleep_state(False)
        self.poll_te20_monitor_audio()
        self._append_te20_monitor_audio_terminal_log("[sleep] refreshing microphone volume after wake")
        self.refresh_volume_status(self._microphone_param_name())
        if self._should_show_te20_monitor_audio_fields() and self._is_codec_screen_active():
            self.start_te20_monitor_audio_polling()

    def _set_te20_monitor_audio_sleep_state(self, is_sleeping):
        self._te20_is_sleeping = bool(is_sleeping)
        sleep_text = "недоступно в режиме Сна"

        if self.parent and hasattr(self.parent, "set_ui_state") and self._is_te20_device():
            if self._te20_is_sleeping:
                self.parent.set_ui_state(
                    UIState.SLEEPING,
                    "Huawei TE20 находится в спящем режиме",
                    self,
                )
            elif getattr(self.parent, "ui_state", None) == UIState.SLEEPING:
                self.parent.set_ui_state(
                    UIState.CONNECTED,
                    "Huawei TE20 вышел из спящего режима",
                    self,
                )

        for param_name, value_label in self.param_widgets:
            if param_name not in self.TE20_SLEEP_UNAVAILABLE_FIELDS:
                continue

            if self._te20_is_sleeping:
                value_label.setText(sleep_text)
                self._set_widget_state(value_label, "warning")

        self._set_microphone_volume_controls_visible(not self._te20_is_sleeping)

        wake_btn = self.wake_buttons.get("Звук в помещении (микрофон)")
        if not self._is_deleted_widget(wake_btn) and not self.wake_countdown_timer.isActive():
            wake_btn.setVisible(self._te20_is_sleeping)

    def on_wake_te20_clicked(self):
        if not self.parent:
            return

        ip_address = self.parent.ip_entry.text().strip()
        device_name = self.parent.device_combo.currentText()
        if not ip_address or device_name != "Huawei TE20":
            return

        self._append_te20_monitor_audio_terminal_log("[sleep] wake requested from monitor audio row")

        def on_result(_value, _payload):
            self._append_te20_monitor_audio_terminal_log(
                "[sleep] wake command completed"
            )
            self._set_te20_monitor_audio_sleep_state(False)
            self._start_te20_wake_countdown(7)

        self._submit_interactive(
            InteractiveOperation(
                kind="wake",
                method="wake_up",
                semantic=OperationSemantic.DESIRED_STATE,
                readback_method="get_sleep_mode",
                target="Off",
                original="On",
            ),
            on_result,
            lambda payload: self._append_te20_monitor_audio_terminal_log(
                f"[sleep] wake failed: {payload.get('category')}"
            ),
        )

    def _append_te20_monitor_audio_terminal_log(self, message):
        if not self.parent:
            return

        if (
            self._is_te20_device()
            and hasattr(self.parent, 'te20_terminal_dialog')
            and self.parent.te20_terminal_dialog
        ):
            self.parent.te20_terminal_dialog.append_line(message)
            return

        if hasattr(self.parent, 'append_codec_terminal_line'):
            self.parent.append_codec_terminal_line(message)

    def poll_te20_monitor_audio(self):
        if not self._should_show_te20_monitor_audio_fields() or not self._is_codec_screen_active():
            self.stop_te20_monitor_audio_polling()
            return

        ip_address = self.parent.ip_entry.text().strip() if self.parent else None
        device_name = self.parent.device_combo.currentText() if self.parent else None
        if not ip_address or device_name not in {
            "Huawei TE20",
            "Huawei TE40",
        }:
            self.stop_te20_monitor_audio_polling()
            return

        self._append_te20_monitor_audio_terminal_log("[poll] monitor audio tick")

        def on_result(result, _payload):
            if not isinstance(result, dict):
                return
            sleep_mode = result.get("sleep_mode")
            if device_name == "Huawei TE20":
                self._set_te20_monitor_audio_sleep_state(sleep_mode == "On")
                if sleep_mode == "On":
                    return
            data = result.get("audio", {})
            if not isinstance(data, dict):
                return
            self._update_monitor_audio_display(
                mic_value=data.get("MicValueIndex"),
                speaker_value=data.get("SpeakerValueIndex"),
            )
            self._append_te20_monitor_audio_terminal_log(
                "[poll] monitor audio values updated"
            )

        self._submit_interactive(
            InteractiveOperation(
                kind="live_audio",
                method="get_live_audio_status",
                semantic=OperationSemantic.READ_ONLY,
                duplicate_key="live_audio",
                quiet=True,
            ),
            on_result,
            lambda payload: self._append_te20_monitor_audio_terminal_log(
                f"[poll] monitor audio failed: {payload.get('category')}"
            ),
        )

    def update_volume_display(self, volume, param_name="Громкость динамиков"):
        """Обновление отображения громкости в GUI"""
        if self._te20_is_sleeping and param_name in self._microphone_param_names():
            return

        numeric_value = self._extract_numeric_value(volume)
        if param_name in self._microphone_param_names():
            text_value = str(volume).strip().lower()
            if text_value in {"muted", "unmuted"}:
                self.microphone_mute_state = volume
        if numeric_value is not None:
            self.volume_values[param_name] = numeric_value
            self._remember_unmuted_volume(param_name, numeric_value)
        if param_name in self._microphone_param_names():
            self._set_microphone_volume_controls_visible(
                not self._is_microphone_disconnected_value(volume)
            )

        for name_label, value_label in self.param_widgets:
            if name_label == param_name:
                new_value = str(volume)
                value_label.setText(new_value)
                self._set_widget_state(value_label, "normal")
                print(f"Обновлено отображение {param_name}: {new_value}")
                break
        if numeric_value is not None and (param_name == "Громкость динамиков" or param_name in self._microphone_param_names()):
            self.update_mute_button_state(param_name, muted=(numeric_value == 0))
        else:
            self.update_mute_button_state(param_name)
    def update_presentation_display(self, presentation_state):
        """Обновление отображения статуса презентации в GUI."""
        presentation_map = {
            'Start': 'Демонстрируется',
            'Stop': 'Не демонстрируется',
            'Started': 'Демонстрируется',
            'Stopped': 'Не демонстрируется',
            'auxOpen': 'Демонстрируется',
            'auxClose': 'Не демонстрируется',
        }
        new_value = presentation_map.get(presentation_state, presentation_state)

        for name_label, value_label in self.param_widgets:
            if name_label == "Статус презентации":
                value_label.setText(str(new_value))
                self._set_widget_state(value_label, "normal")
                self._sync_presentation_button_state(new_value)
                print(f"Обновлено отображение Статус презентации: {new_value}")
                break


    def lighten_color(self, hex_color, percent):
        """Осветлить HEX цвет на указанный процент"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        r = min(255, int(r + (255 - r) * percent / 100))
        g = min(255, int(g + (255 - g) * percent / 100))
        b = min(255, int(b + (255 - b) * percent / 100))
        
        return f'#{r:02x}{g:02x}{b:02x}'



    def _convert_parser_data_to_gui(self, data):
        """Преобразование данных из парсера в формат GUI"""
        if not data:
            print("⚠ _convert_parser_data_to_gui: data is empty")
            return {}
        
        print("🔍 _convert_parser_data_to_gui получил данные:", data)
        
        # Маппинг ключей из парсера в ключи GUI
        mapping = {
            'Модель': 'Модель кодеков',
            'Версия ПО': 'Версия прошивки',
            'Серийный номер': 'Серийный номер',  # Это ключ, который должен быть
            'MAC адрес': 'MAC адрес',
            'SIP регистрация': 'SIP регистрация',
            'SIP адрес': 'SIP адрес',
            'Время работы': 'Время работы',
            'Температура': 'Температура',
            'Скорость сети': 'Скорость сети',
            'Статус звонка': 'Статус звонка',
            'Режим презентации': 'Статус презентации',
            'Громкость динамика': 'Громкость динамиков',
            'Громкость динамиков': 'Громкость динамиков',
            'Громкость микрофона': 'Громкость микрофона',
            'Mute микрофона': 'Mute микрофона',
            'Статус микрофона': 'Статус микрофона',
            'Статус камеры': 'Статус камеры',
            'Звук в помещении (микрофон)': 'Звук в помещении (микрофон)',
            'Звук из динамиков (выход кодека)': 'Звук из динамиков (выход кодека)',
        }
        
        result = {}
        
        # Прямое преобразование по маппингу
        for parser_key, gui_key in mapping.items():
            if parser_key in data:
                value = data[parser_key]
                print(f"  Найден ключ '{parser_key}' -> '{gui_key}': '{value}'")
                if value and value != 'N/A':
                    result[gui_key] = value
                else:
                    print(f"  ⚠ Значение для '{parser_key}' пустое или N/A")
            else:
                print(f"  ❌ Ключ '{parser_key}' отсутствует в данных")
        
        # Специальные случаи
        if 'mic_mute' in data and 'Статус микрофона' not in result:
            print(f"  Спецслучай mic_mute: {data['mic_mute']}")
            if data['mic_mute'] == 'On':
                result['Статус микрофона'] = 'Выключен'
            elif data['mic_mute'] == 'Off':
                result['Статус микрофона'] = 'Включен'
        
        if 'speaker_volume' in data:
            print(f"  Спецслучай speaker_volume: {data['speaker_volume']}")
            result['Громкость динамиков'] = str(data['speaker_volume'])

        if 'mic_volume' in data:
            print(f"  Спецслучай mic_volume: {data['mic_volume']}")
            microphone_param_name = self._microphone_param_name()
            if microphone_param_name not in result:
                result[microphone_param_name] = str(data['mic_volume'])
        
        if 'call_status' in data:
            print(f"  Спецслучай call_status: {data['call_status']}")
            call_map = {
                'No Call': 'Не в звонке',
                'Calling': 'В звонке',
                'Connected': 'Подключено',
                'Disconnected': 'Разъединен'
            }
            result['Статус звонка'] = call_map.get(data['call_status'], data['call_status'])
        
        if 'presentation' in data:
            print(f"  Спецслучай presentation: {data['presentation']}")
            pres_map = {
                'Start': 'Демонстрируется',
                'Stop': 'Не демонстрируется',
                'auxOpen': 'Демонстрируется',
                'auxClose': 'Не демонстрируется'
            }
            result['Статус презентации'] = pres_map.get(data['presentation'], data['presentation'])
        
        if 'camera_status' in data:
            print(f"  Спецслучай camera_status: {data['camera_status']}")
            camera_map = {
                'OffOff': 'Не подключена',
                'OnOn': 'Обе камеры',
                'OnOff': 'Камера 1',
                'OffOn': 'Камера 2'
            }
            result['Статус камеры'] = camera_map.get(data['camera_status'], data['camera_status'])
        
        print("🔍 _convert_parser_data_to_gui вернул:", result)
        return result

    def refresh(self):
        """Обновление данных экрана"""
        if self.parent and hasattr(self.parent, 'refresh_data'):
            self.parent.refresh_data()
