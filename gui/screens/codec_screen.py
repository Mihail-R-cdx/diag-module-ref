from PyQt5.QtWidgets import (
    QVBoxLayout,
    QScrollArea,
    QGridLayout,
    QFrame,
    QLabel,
    QWidget,
    QMessageBox,
    QProgressDialog,
)
from PyQt5.QtCore import Qt, QTimer, QEventLoop
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
from ..theme import SPACING
from ..ui_states import UIState
from .base_screen import BaseScreen


class CodecScreen(BaseScreen):
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
        self.volume_session_handler = None
        self.volume_session_key = None
        self._show_te20_monitor_audio_fields = False
        self.wake_buttons = {}
        self.wake_countdown_labels = {}
        self.parameter_rows = {}
        self.sip_status_indicators = {}
        self._te20_is_sleeping = False
        self._te20_wake_countdown_remaining = 0
        super().__init__(parent)
        self.volume_refresh_timer = QTimer(self)
        self.volume_refresh_timer.setSingleShot(True)
        self._pending_volume_refresh_param = "Громкость динамиков"
        self.volume_refresh_timer.timeout.connect(self.refresh_pending_volume_status)
        self.presentation_refresh_timer = QTimer(self)
        self.presentation_refresh_timer.setSingleShot(True)
        self.presentation_refresh_timer.timeout.connect(self.refresh_presentation_status)
        self.monitor_audio_timer = QTimer(self)
        self.monitor_audio_timer.setInterval(3000)
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
            and self.parent.device_combo.currentText() == "Huawei TE-20"
        )

    def _uses_microphone_mute_control(self):
        return bool(
            self.parent
            and hasattr(self.parent, 'device_combo')
            and self.parent.device_combo.currentText() in {"Huawei TE-20", "Huawei TE-40", "Polycom RPG 310"}
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

        primary_params = [
            "Версия прошивки",
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
        self.info_grid.setVerticalSpacing(SPACING["md"])
        self.info_left_column = self._create_param_column(primary_params)
        self.info_right_column = self._create_param_column(secondary_params)
        self.info_card.add_widget(self.info_columns_widget)

        self.controls_card = SectionCard("Параметры и управление", "⚙", self.param_widget)
        self.create_param_block(control_params, self.controls_card.body_layout)

        self.param_layout.addWidget(self.info_card)
        self.param_layout.addWidget(self.controls_card)
        self.param_layout.addStretch(1)
        self._apply_responsive_layout()


    def _create_param_column(self, params):
        column = QWidget(self.info_columns_widget)
        column_layout = QVBoxLayout(column)
        column_layout.setContentsMargins(0, 0, 0, 0)
        column_layout.setSpacing(0)
        self.create_param_block(params, column_layout)
        return column

    def create_param_block(self, params, target_layout=None):
        """Создаёт строки через общие компоненты этапа 4."""
        if target_layout is None:
            target_layout = self.param_layout

        for param_name in params:
            row = ParameterRow(param_name, "—", self.param_widget)
            row.setObjectName("codecParameterRow")
            row.value_display.setProperty("data_field", True)
            row.value_display.setAccessibleName(param_name)
            self.parameter_rows[param_name] = row
            value_label = row.value_display

            if param_name == self.CALL_LOG_PARAM:
                value_label.setVisible(False)
                call_log_btn = SemanticButton("Открыть журнал", "primary", row)
                call_log_btn.clicked.connect(self.open_call_log_window)
                row.add_action(call_log_btn)
            elif param_name == "SIP регистрация":
                indicator = StatusIndicator("inactive", "", False, row)
                indicator.setToolTip("Статус SIP-регистрации")
                fix_btn = SemanticButton("Исправить", "danger", row)
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
                wake_btn = SemanticButton("Разбудить", "primary", row)
                wake_btn.clicked.connect(self.on_wake_te20_clicked)
                wake_btn.setVisible(False)
                row.add_action(wake_btn)
                self.wake_buttons[param_name] = wake_btn
                countdown_label = StatusIndicator("warning", "", True, row)
                countdown_label.setAlignment(Qt.AlignCenter)
                countdown_label.setVisible(False)
                row.add_action(countdown_label)
                self.wake_countdown_labels[param_name] = countdown_label

            if param_name != self.CALL_LOG_PARAM:
                self.param_widgets.append((param_name, value_label))
            target_layout.addWidget(row)

    def _apply_responsive_layout(self):
        if not hasattr(self, "info_grid"):
            return
        available_width = self.scroll_area.viewport().width()
        narrow = available_width < 840
        positions = (
            ((self.info_left_column, 0, 0), (self.info_right_column, 1, 0))
            if narrow
            else ((self.info_left_column, 0, 0), (self.info_right_column, 0, 1))
        )
        for widget, row, column in positions:
            self.info_grid.removeWidget(widget)
            self.info_grid.addWidget(widget, row, column)
        self.info_grid.setColumnStretch(0, 1)
        self.info_grid.setColumnStretch(1, 0 if narrow else 1)

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

        if device_name not in {"Huawei TE-20", "Huawei TE-40", "CloudLink Bar 310", "Polycom RPG 310"}:
            self.call_log_window.status_label.setText("Получение журнала звонков для этого устройства будет добавлено позже.")
            return

        creds, current_idx, creds_list = self._get_current_device_credentials(device_name, ip_address)
        if creds is None:
            QMessageBox.warning(self, "Ошибка", f"Не найдены credentials для {device_name}")
            return

        try:
            self.call_log_window.status_label.setText("Загрузка журнала звонков...")
            handler = self._get_or_create_volume_handler(
                ip_address=ip_address,
                device_name=device_name,
                username=creds['username'],
                password=creds['password'],
            )
            if handler is None:
                QMessageBox.warning(self, "Ошибка", f"Не удалось подключиться к {device_name} для получения журнала звонков")
                self.call_log_window.status_label.setText("Не удалось загрузить журнал звонков.")
                return

            records = handler.get_call_records()
            self.call_log_window.set_call_records(records)
        except Exception as e:
            self.call_log_window.status_label.setText(f"Не удалось загрузить журнал звонков: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось получить журнал звонков:\n{str(e)}")


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
        return str(value).strip().lower() == "микрофон не подключён"

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
            self.set_volume_value(param_name, restore_value)
        else:
            self._remember_unmuted_volume(param_name, current_value)
            self.set_volume_value(param_name, 0)

    def on_presentation_button_clicked(self, param_name, direction):
        """Обработчик нажатия кнопок управления презентацией"""
        print(f"Нажата кнопка presentation {direction} для {param_name}")

        if param_name in self.presentation_buttons:
            self.set_presentation_buttons_enabled(param_name, False)
            QTimer.singleShot(1500, lambda name=param_name: self.set_presentation_buttons_enabled(name, True))
            self.set_presentation_state(direction)

    def set_presentation_state(self, direction):
        """Отправка команды включения или выключения презентации."""
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
        print(f"Отправка команды управления презентацией на {device_name} ({ip_address}): {command}")

        creds, current_idx, creds_list = self._get_current_device_credentials(device_name, ip_address)

        if creds is None:
            print(f"Не найдены credentials для {device_name}")
            QMessageBox.warning(self, "Ошибка", f"Не найдены credentials для {device_name}")
            return

        self._append_presentation_terminal_log(
            f"[session] credential {current_idx + 1}/{len(creds_list)} user={creds['username']}"
        )

        try:
            handler = self._get_or_create_volume_handler(
                ip_address=ip_address,
                device_name=device_name,
                username=creds['username'],
                password=creds['password'],
                command_logger=self._append_presentation_terminal_log,
            )

            if handler is None:
                print("Не удалось подключиться к устройству для управления презентацией")
                self._finish_presentation_terminal("connection failed")
                QMessageBox.warning(self, "Ошибка", "Не удалось подключиться к устройству для управления презентацией")
                return

            if not hasattr(handler, 'set_presentation'):
                print(f"Устройство {device_name} пока не поддерживает управление презентацией")
                self._finish_presentation_terminal("presentation control is not supported")
                QMessageBox.information(self, "Информация", f"Устройство {device_name} пока не поддерживает управление презентацией")
                return

            if command == "Start" and not self._prepare_sleeping_device_for_presentation(handler):
                return

            success = handler.set_presentation(command)
            if success:
                print(f"Команда презентации {command} успешно отправлена")
                self._finish_presentation_terminal(f"completed successfully: {command}")
                self.update_presentation_display(command)
                self.schedule_presentation_refresh()
            else:
                print(f"Устройство не подтвердило команду презентации {command}")
                self._finish_presentation_terminal(f"device did not confirm command: {command}")
                detailed_error = getattr(handler, 'last_presentation_error_message', None)
                if detailed_error:
                    QMessageBox.warning(self, "Ошибка", detailed_error)
                    return
                QMessageBox.warning(self, "Ошибка", f"Устройство не подтвердило команду презентации: {command}")

        except Exception as e:
            print(f"Ошибка при управлении презентацией: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            self.reset_volume_session()
            for name in self.presentation_buttons:
                self.set_presentation_buttons_enabled(name, True)
            self._finish_presentation_terminal(f"failed: {type(e).__name__}: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось выполнить команду презентации:\n{str(e)}")

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

        # Вычисляем новое значение
        if direction == "up":
            new_volume = min(max_volume, current_volume + 1)
        else:  # down
            new_volume = max(min_volume, current_volume - 1)
        
        print(f"Текущая громкость: {current_volume}, Новое значение: {new_volume}")
        
        # Отправляем команду на устройство через API
        self.set_volume_value(param_name, new_volume)
    
    def _get_volume_control_kind(self, param_name):
        if param_name == "Громкость динамиков":
            return "speaker"
        if param_name in self._microphone_param_names():
            return "microphone"
        return None

    def set_volume_value(self, param_name, value):
        if self._te20_is_sleeping and param_name in self._microphone_param_names():
            return False

        control_kind = self._get_volume_control_kind(param_name)
        if control_kind == "speaker":
            return self.set_speaker_volume(value)
        if control_kind == "microphone":
            return self.set_microphone_volume(value)
        return False
    
    def set_speaker_volume(self, value):
        """Отправка команды изменения громкости на устройство через API"""
        # Получаем текущие credentials и IP адрес
        ip_address = self.parent.ip_entry.text().strip() if self.parent else None
        device_name = self.parent.device_combo.currentText() if self.parent else None
        
        if not ip_address or not device_name:
            print("Не удалось получить IP адрес или имя устройства для изменения гро��кости")
            return
        
        print(f"Отправка команды изменения громкости на {device_name} ({ip_address}): {value}")
        
        # Получаем текущие credentials
        creds, current_idx, creds_list = self._get_current_device_credentials(device_name, ip_address)
        
        if creds is not None:
            
            # Создаем обработчик для отправки команды
            try:
                handler = self._get_or_create_volume_handler(
                    ip_address=ip_address,
                    device_name=device_name,
                    username=creds['username'],
                    password=creds['password'],
                )

                if handler:
                    success = handler.set_speaker_volume(value)
                    if success:
                        print(f"Громкость успешно изменена на {value}")
                        self.update_volume_display(value, param_name="Громкость динамиков")
                        self.schedule_volume_refresh("Громкость динамиков")
                    else:
                        print("Ошибка изменения громкости: устройство не подтвердило команду")
                        self.refresh_volume_status("Громкость динамиков")
                else:
                    print("Не удалось подключиться к устройству для изменения громкости")
                    
            except Exception as e:
                print(f"Ошибка при изменении громкости: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                self.reset_volume_session()

    def set_microphone_volume(self, value):
        """Отправка команды изменения громкости микрофона на устройство через API."""
        ip_address = self.parent.ip_entry.text().strip() if self.parent else None
        device_name = self.parent.device_combo.currentText() if self.parent else None

        if not ip_address or not device_name:
            print("Не удалось получить IP адрес или имя устройства для изменения громкости микрофона")
            return False

        print(f"Отправка команды изменения громкости микрофона на {device_name} ({ip_address}): {value}")

        creds, current_idx, creds_list = self._get_current_device_credentials(device_name, ip_address)

        if creds is not None:
            try:
                handler = self._get_or_create_volume_handler(
                    ip_address=ip_address,
                    device_name=device_name,
                    username=creds['username'],
                    password=creds['password'],
                )

                if handler:
                    success = handler.set_microphone_volume(value)
                    if success:
                        print(f"Состояние микрофона успешно изменено на {value}")
                        display_value = "Muted" if self._uses_microphone_mute_control() and int(value) <= 0 else (
                            "Unmuted" if self._uses_microphone_mute_control() else value
                        )
                        self.update_volume_display(display_value, param_name=self._microphone_param_name())
                        self.schedule_volume_refresh(self._microphone_param_name())
                    else:
                        print("Изменение громкости микрофона не подтверждено или не поддерживается этим кодеком")
                        self.refresh_volume_status(self._microphone_param_name())
                    return success

                print("Не удалось подключиться к устройству для изменения громкости микрофона")
            except Exception as e:
                print(f"Ошибка при изменении громкости микрофона: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                self.reset_volume_session()

        return False

    def get_speaker_volume(self):
        """Получение текущей громкости с устройства через API"""
        # Получаем текущие credentials и IP адрес
        ip_address = self.parent.ip_entry.text().strip() if self.parent else None
        device_name = self.parent.device_combo.currentText() if self.parent else None
        
        if not ip_address or not device_name:
            print("Не удалось получить IP адрес или имя устройства для получения громкости")
            return
        
        print(f"Запрос текущей громкости с устройства {device_name} ({ip_address})...")
        
        # Получаем текущие credentials
        creds, current_idx, creds_list = self._get_current_device_credentials(device_name, ip_address)
        
        if creds is not None:
            
            # Создаем обработчик для запроса данных
            try:
                handler = self._get_or_create_volume_handler(
                    ip_address=ip_address,
                    device_name=device_name,
                    username=creds['username'],
                    password=creds['password'],
                )

                if handler:
                    volume = handler.get_speaker_volume()
                    if volume is not None:
                        print(f"Текущая громкость с устройства: {volume}")
                        self.update_volume_display(volume, param_name="Громкость динамиков")
                    else:
                        print("Ошибка получения громкости: устройство не вернуло значение")
                    return volume
                else:
                    print("Не удалось подключиться к устройству для получения громкости")
                    
            except Exception as e:
                print(f"Ошибка при получении громкости: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                self.reset_volume_session()

        return None

    def get_microphone_volume(self):
        """Получение текущей громкости микрофона с устройства через API."""
        ip_address = self.parent.ip_entry.text().strip() if self.parent else None
        device_name = self.parent.device_combo.currentText() if self.parent else None

        if not ip_address or not device_name:
            print("Не удалось получить IP адрес или имя устройства для получения громкости микрофона")
            return None

        print(f"Запрос текущей громкости микрофона с устройства {device_name} ({ip_address})...")

        creds, current_idx, creds_list = self._get_current_device_credentials(device_name, ip_address)

        if creds is not None:
            try:
                handler = self._get_or_create_volume_handler(
                    ip_address=ip_address,
                    device_name=device_name,
                    username=creds['username'],
                    password=creds['password'],
                )

                if handler:
                    volume = None
                    get_audio_status = getattr(handler, 'get_audio_status', None)
                    if callable(get_audio_status):
                        audio_status = get_audio_status()
                        if isinstance(audio_status, dict):
                            if audio_status.get('mute') is not None:
                                self.microphone_mute_state = audio_status.get('mute')
                                if self._uses_microphone_mute_control():
                                    volume = self._format_microphone_mute_state(self.microphone_mute_state)
                            if not self._uses_microphone_mute_control():
                                volume = audio_status.get('microphone_volume')

                    if volume is None:
                        volume = handler.get_microphone_volume()
                    if volume is not None:
                        print(f"Текущая громкость микрофона с устройства: {volume}")
                        self.update_volume_display(volume, param_name=self._microphone_param_name())
                    else:
                        print("Ошибка получения громкости микрофона: устройство не вернуло значение")
                    return volume

                print("Не удалось подключиться к устройству для получения громкости микрофона")
            except Exception as e:
                print(f"Ошибка при получении громкости микрофона: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                self.reset_volume_session()

        return None

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
        ip_address = self.parent.ip_entry.text().strip() if self.parent else None
        device_name = self.parent.device_combo.currentText() if self.parent else None

        if not ip_address or not device_name:
            return

        creds, current_idx, creds_list = self._get_current_device_credentials(device_name, ip_address)
        if creds is None:
            return

        try:
            handler = self._get_or_create_volume_handler(
                ip_address=ip_address,
                device_name=device_name,
                username=creds['username'],
                password=creds['password'],
                command_logger=self._append_presentation_terminal_log,
            )
            if not handler:
                return

            get_presentation_status = getattr(handler, 'get_presentation_status', None)
            if not callable(get_presentation_status):
                return

            presentation_state = get_presentation_status()
            if presentation_state is not None:
                self.update_presentation_display(presentation_state)
        except Exception as e:
            self._append_presentation_terminal_log(
                f"[presentation] refresh failed: {type(e).__name__}: {str(e)}"
            )

    def reset_volume_session(self):
        """Сбрасывает долгоживущую сессию управления громкостью."""
        self.stop_te20_monitor_audio_polling()
        if self.volume_session_handler is not None:
            try:
                self.volume_session_handler.disconnect()
            except Exception:
                pass
        self.volume_session_handler = None
        self.volume_session_key = None

    def _get_or_create_volume_handler(self, ip_address, device_name, username, password, command_logger=None):
        """Возвращает существующую сессию громкости или создаёт новую."""
        handler_class = None
        base_handler_kwargs = {
            "ip_address": ip_address,
            "username": username,
            "password": password,
        }
        connection_profiles = []

        if device_name == "Huawei TE-20":
            from handlers.huawei.te20 import HuaweiTE20Handler
            handler_class = HuaweiTE20Handler
            connection_profiles = [
                {"port": 80, "use_ssl": False, "label": "HTTP:80"},
                {"port": 443, "use_ssl": True, "label": "HTTPS:443"},
            ]
        elif device_name == "Huawei TE-40":
            from handlers.huawei.te40 import HuaweiTE40Handler
            handler_class = HuaweiTE40Handler
            connection_profiles = [
                {"port": 443, "use_ssl": True, "label": "HTTPS:443"},
                {"port": 80, "use_ssl": False, "label": "HTTP:80"},
            ]
        elif device_name == "CloudLink Bar 310":
            from handlers.huawei.bar310 import CloudLinkBar310Handler
            handler_class = CloudLinkBar310Handler
            connection_profiles = [{"port": 443, "use_ssl": True, "label": "HTTPS:443"}]
        elif device_name == "Polycom RPG 310":
            from handlers.polycom.rpg310 import PolycomRPG310Handler
            handler_class = PolycomRPG310Handler
            connection_profiles = [{"port": 443, "label": "HTTPS:443"}]
        else:
            self.reset_volume_session()
            return None

        preferred_profile = None
        if self.parent and hasattr(self.parent, 'get_device_connection_profile'):
            preferred_profile = self.parent.get_device_connection_profile(device_name, ip_address)
        if device_name in {"Huawei TE-20", "Huawei TE-40"}:
            preferred_profile = None
        if isinstance(preferred_profile, dict) and preferred_profile:
            preferred_port = preferred_profile.get("port")
            preferred_use_ssl = preferred_profile.get("use_ssl")
            prioritized_profiles = []
            if preferred_port is not None:
                preferred_entry = {
                    "port": preferred_port,
                    "label": preferred_profile.get(
                        "label",
                        f"{'HTTPS' if preferred_use_ssl else 'HTTP'}:{preferred_port}"
                    ),
                }
                if device_name != "Polycom RPG 310":
                    preferred_entry["use_ssl"] = preferred_use_ssl
                prioritized_profiles.append(preferred_entry)
            prioritized_profiles.extend(connection_profiles)

            seen_profiles = set()
            connection_profiles = []
            for profile in prioritized_profiles:
                key = (profile.get("port"), profile.get("use_ssl"))
                if key in seen_profiles:
                    continue
                seen_profiles.add(key)
                connection_profiles.append(profile)

        profile_signature = tuple(
            (profile.get("port"), profile.get("use_ssl"))
            for profile in connection_profiles
        )
        session_key = (device_name, ip_address, username, password, profile_signature)
        if self.volume_session_handler is not None and self.volume_session_key == session_key:
            self.volume_session_handler.command_logger = command_logger
            return self.volume_session_handler

        self.reset_volume_session()

        for profile in connection_profiles:
            handler_kwargs = dict(base_handler_kwargs)
            allowed_profile_keys = {"port"} if device_name == "Polycom RPG 310" else {"port", "use_ssl"}
            handler_kwargs.update({k: v for k, v in profile.items() if k in allowed_profile_keys})

            handler = handler_class(**handler_kwargs)
            handler.command_logger = command_logger

            if callable(command_logger):
                command_logger(f"[connect] control via {profile['label']}")

            if handler.connect():
                self.volume_session_handler = handler
                self.volume_session_key = session_key
                return handler

            try:
                handler.disconnect()
            except Exception:
                pass

        return None

    def _get_volume_range(self, param_name="Громкость динамиков"):
        device_name = self.parent.device_combo.currentText() if self.parent else None
        control_kind = self._get_volume_control_kind(param_name)
        ranges = {
            "speaker": {
                "Huawei TE-20": (0, 21),
                "Huawei TE-40": (0, 21),
                "CloudLink Bar 310": (0, 15),
                "Polycom RPG 310": (0, 100),
            },
            "microphone": {
                "Huawei TE-20": (0, 21),
                "Huawei TE-40": (0, 21),
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
            return self.parent.device_combo.currentText() == "Huawei TE-20"
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
            numeric_value = self._extract_numeric_value(value)
            for name_label, value_label in self.param_widgets:
                if name_label == param_name:
                    value_label.setText(str(value))
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
                    "Huawei TE-20 находится в спящем режиме",
                    self,
                )
            elif getattr(self.parent, "ui_state", None) == UIState.SLEEPING:
                self.parent.set_ui_state(
                    UIState.CONNECTED,
                    "Huawei TE-20 вышел из спящего режима",
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
        if not ip_address or device_name != "Huawei TE-20":
            return

        creds, current_idx, creds_list = self._get_current_device_credentials(device_name, ip_address)
        if creds is None:
            return

        self._append_te20_monitor_audio_terminal_log("[sleep] wake requested from monitor audio row")

        try:
            handler = self._get_or_create_volume_handler(
                ip_address=ip_address,
                device_name=device_name,
                username=creds['username'],
                password=creds['password'],
                command_logger=self._append_te20_monitor_audio_terminal_log,
            )
            if not handler:
                self._append_te20_monitor_audio_terminal_log("[sleep] wake failed: handler unavailable")
                return

            wake_up = getattr(handler, 'wake_up', None)
            if not callable(wake_up):
                self._append_te20_monitor_audio_terminal_log("[sleep] wake failed: command is not supported")
                return

            wake_success = wake_up()
            self._append_te20_monitor_audio_terminal_log(f"[sleep] wake command result: {wake_success}")
            if wake_success:
                self._set_te20_monitor_audio_sleep_state(False)
                self._start_te20_wake_countdown(7)
        except Exception as e:
            self._append_te20_monitor_audio_terminal_log(
                f"[sleep] wake exception: {type(e).__name__}: {str(e)}"
            )

    def _append_te20_monitor_audio_terminal_log(self, message):
        if not self.parent:
            return

        if hasattr(self.parent, 'te20_terminal_dialog') and self.parent.te20_terminal_dialog:
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
        if not ip_address or device_name != "Huawei TE-20":
            self.stop_te20_monitor_audio_polling()
            return

        creds, current_idx, creds_list = self._get_current_device_credentials(device_name, ip_address)
        if creds is None:
            return

        try:
            self._append_te20_monitor_audio_terminal_log("[poll] monitor audio tick")
            handler = self._get_or_create_volume_handler(
                ip_address=ip_address,
                device_name=device_name,
                username=creds['username'],
                password=creds['password'],
                command_logger=self._append_te20_monitor_audio_terminal_log,
            )
            if not handler:
                self._append_te20_monitor_audio_terminal_log("[poll] monitor audio handler is unavailable")
                return

            get_sleep_mode = getattr(handler, 'get_sleep_mode', None)
            if callable(get_sleep_mode):
                sleep_mode = get_sleep_mode()
                self._append_te20_monitor_audio_terminal_log(f"[sleep] current mode: {sleep_mode}")
                if sleep_mode == 'On':
                    self._set_te20_monitor_audio_sleep_state(True)
                    return

            self._set_te20_monitor_audio_sleep_state(False)
            result = handler.send_command('get_monitor_audio_params')
            if not result or result.get('success') != 1:
                self._append_te20_monitor_audio_terminal_log(f"[poll] monitor audio failed: {result}")
                return

            data = result.get('data', {})
            if not isinstance(data, dict):
                self._append_te20_monitor_audio_terminal_log("[poll] monitor audio returned non-dict data")
                return

            self._update_monitor_audio_display(
                mic_value=data.get('MicValueIndex'),
                speaker_value=data.get('SpeakerValueIndex'),
            )
            self._append_te20_monitor_audio_terminal_log(
                f"[poll] monitor audio values mic={data.get('MicValueIndex')} speaker={data.get('SpeakerValueIndex')}"
            )
        except Exception as e:
            self._append_te20_monitor_audio_terminal_log(
                f"[poll] monitor audio exception: {type(e).__name__}: {str(e)}"
            )
            print(f"Ошибка при опросе monitor audio TE-20: {type(e).__name__}: {str(e)}")

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
