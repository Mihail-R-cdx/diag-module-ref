from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox, QStackedWidget, QMessageBox, QInputDialog, QDialog, QDialogButtonBox, QFormLayout, QPlainTextEdit, QSizePolicy

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QThreadPool, QDateTime, QEvent
from PyQt5.QtGui import QColor
import datetime
import os
import random
import platform
import subprocess
import traceback

from .screens import CodecScreen, MatrixScreen, PDUScreen, AudioDSPScreen
from .components import EmptyState, StatusIndicator
from .theme import SPACING, apply_theme, legacy_colors
from .ui_states import UIState, coerce_ui_state, state_spec
from core.worker import HuaweiTE40Worker, HuaweiBar310Worker, HuaweiTE20Worker, PolycomRPG310Worker, CodecSipFixWorker, BiampTesiraForteCIWorker
from core.exceptions import AuthenticationError, ConnectionError
from core.credentials import JsonCredentialProvider, resolve_request_credentials
from core.exceptions import CredentialConfigurationError
from core.redaction import redact_exception, redact_text
from PyQt5.QtWidgets import QStyledItemDelegate, QStyle
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPainter

class RightAlignHeaderDelegate(QStyledItemDelegate):
    """Делегат для выравнивания заголовков по правому краю"""
    def __init__(self, parent=None, header_list=None):
        super().__init__(parent)
        self.header_list = header_list or []
    
    def paint(self, painter, option, index):
        text = index.data()
        
        # Проверяем, является ли элемент заголовком
        if text in self.header_list:
            # Для заголовков рисуем с выравниванием по правому краю
            painter.save()
            
            # Рисуем фон
            if option.state & QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())
            
            # Рисуем текст с выравниванием по правому краю
            text_rect = QRect(option.rect)
            text_rect.setRight(option.rect.right() - 10)  # Отступ справа 10px
            painter.drawText(text_rect, Qt.AlignRight | Qt.AlignVCenter, text)
            
            painter.restore()
        else:
            # Для обычных элементов используем стандартное рисование
            # Вызываем родительский метод
            QStyledItemDelegate.paint(self, painter, option, index)


class MatrixTerminalDialog(QDialog):
    def __init__(self, colors, parent=None):
        super().__init__(parent)
        self.colors = colors
        self.setWindowTitle("Терминал Extron IN1804")
        self.resize(760, 420)

        layout = QVBoxLayout(self)
        self.output = QPlainTextEdit(self)
        self.output.setReadOnly(True)
        self.output.setProperty("uiRole", "terminal")
        layout.addWidget(self.output)

    def reset_session(self, title: str):
        self.setWindowTitle(title)
        self.output.clear()

    def append_line(self, text: str):
        self.output.appendPlainText(text)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())


class RequestCredentialStore(dict):
    """Compatibility bridge for explicit UI/test credentials and the provider."""

    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def get(self, device_name, default=None):
        if device_name in self:
            return super().get(device_name)
        return [self.owner.resolve_device_credentials(device_name)]

class VCSDiagnosticApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Цветовая схема
        self.colors = legacy_colors()
        
        # Имитация данных
        self.codec_data = {
            "Codec1": self.generate_fake_data("Codec1"),
            "Codec2": self.generate_fake_data("Codec2"),
            "Codec3": self.generate_fake_data("Codec3"),
            "Codec4": self.generate_fake_data("Codec4")
        }
        
        # Маппинг устройств к экранам
        self.device_to_screen = {
            "Huawei TE20": "codec",
            "Huawei TE40": "codec",
            "CloudLink Bar 310": "codec",  # Добавлено новое устройство
            #"CloudLink Box 300": "codec",
            "Polycom RPG 310": "codec",
            "Extron IN1804": "matrix",
            "Aten PE8208AV": "pdu",
            "Biamp Tesira Forte CI": "audio_dsp"
        }
        
        self.matrix_params = {
            'num_inputs': 8,
            'num_outputs': 6,
            'input_names': [
                "Ноутбук 1", "Ноутбук 2", "Apple TV", "ВКС система",
                "Документ-камера", "Системный ПК", "Резерв 1", "Резерв 2"
            ],
            'output_names': ["ТВ зал 1", "ТВ зал 2", "ВКС кам", "ВКС през", "Выход 5", "Выход 6"]
        }
        
        self.huawei_settings = {
            'port': 443,
            'use_ssl': True,
            'verify_ssl': False
        }        
        
        # Список credentials для разных устройств
        self.credential_provider = JsonCredentialProvider()
        self.device_credentials = RequestCredentialStore(self)
        
        # Текущий индекс credentials для каждого устройства
        self.current_credential_index = {}
        for device in self.device_credentials:
            self.current_credential_index[device] = 0
        self.device_connection_profiles = {}
        self.progress_dialog = None
        self.ui_state = UIState.IDLE
        self._request_serial = 0
        self._active_request = None
        self.matrix_persistent_handler = None
        self.matrix_persistent_ip = None
        self.matrix_persistent_username = None
        self.matrix_persistent_password = None
        self.matrix_keepalive_timer = QTimer(self)
        self.matrix_keepalive_timer.setInterval(15000)
        self.matrix_keepalive_timer.timeout.connect(self.on_matrix_keepalive)
        
        # Инициализация экранов
        self.screens = {}
        self.current_screen = None
        
        # Таймер для обновления времени
        self.update_timer = QTimer(self)
        self.last_update_time = None
        self._last_logged_button_event = None
        self.button_log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "logs"))
        self.button_log_path = os.path.join(self.button_log_dir, "button_clicks.log")
        
        self.init_ui()
        self.update_timer.setInterval(30000)
        self.update_timer.timeout.connect(self.update_time_display)
        self.update_timer.start()

    def resolve_device_credentials(self, device_name, profile_name=None, explicit_credentials=None):
        """Resolve credentials once in the GUI composition layer."""
        credential = resolve_request_credentials(
            self.credential_provider,
            device_model=device_name,
            profile_name=profile_name,
            explicit_credentials=explicit_credentials,
        )
        return credential.as_handler_kwargs()
    
    def init_ui(self, params=None):
        """Инициализация интерфейса"""
        self.setWindowTitle("Диагностический модуль ММК")
        self.setMinimumSize(800, 700)
        self.setGeometry(100, 0, 950, 1000)
        
        # Установка темной темы
        self.set_dark_theme()
        
        # Создаем центральный виджет
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        
        # Основной вертикальный layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(SPACING["md"])
        main_layout.setContentsMargins(
            SPACING["lg"], SPACING["lg"], SPACING["lg"], SPACING["md"]
        )
        
        # 1. Панель выбора устройства и подключения
        top_panel = self.create_top_panel()
        main_layout.addWidget(top_panel)
        
        # 2. Создаем контейнер для экранов
        self.screen_container = QStackedWidget()
        self.screen_container.setObjectName("screenContainer")
        self.screen_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Создаем экраны
        self.init_screens()
        
        # Добавляем экраны в контейнер
        for screen_name, screen in self.screens.items():
            self.screen_container.addWidget(screen)
        
        # 3. Создаем страницу-заглушку с надписью "Обновите данные"
        self.placeholder_widget = self.create_placeholder_widget()
        self.screen_container.addWidget(self.placeholder_widget)
        
        # Показываем заглушку
        self.screen_container.setCurrentWidget(self.placeholder_widget)
        
        main_layout.addWidget(self.screen_container, 1)
        
        # 4. Панель времени обновления
        update_time_panel = self.create_update_time_panel()
        main_layout.addWidget(update_time_panel)
        
        # Сохраняем текущий выбранный тип экрана
        self.current_screen_type = None

        # По умолчанию выбираем первую конкретную модель, а не заголовок группы.
        self.device_combo.setCurrentIndex(1)

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
    
    def create_placeholder_widget(self):
        """Создание виджета-заглушки с надписью Обновите данные"""
        return EmptyState(
            "Обновите данные",
            "Нажмите кнопку «Обновить данные» для получения информации об оборудовании",
        )

    def create_top_panel(self):
        """Создание верхней панели с выпадающим списком и IP-адресом"""
        group_box = QGroupBox()
        group_box.setObjectName("connectionPanel")
        group_box.setProperty("uiRole", "toolbar")
        
        layout = QGridLayout()
        layout.setHorizontalSpacing(SPACING["sm"])
        layout.setVerticalSpacing(SPACING["xs"])
        layout.setContentsMargins(
            SPACING["md"], SPACING["md"], SPACING["md"], SPACING["lg"]
        )
        
        # Выпадающий список устройств
        self.device_combo = QComboBox()
        self.device_combo.setObjectName("deviceCombo")
        self.device_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # The longest device name must not dictate the minimum width of the
        # entire window.  The combo remains expandable, while its compact
        # size hint keeps the 950 px baseline usable at scaled DPI.
        self.device_combo.setMinimumContentsLength(8)
        self.device_combo.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon
        )
        
        # Список заголовков
        headers = ["Кодеки ВКС", "Коммутационное оборудование", "Audio DSP", "Управление питанием"]
        
        # Список устройств с категориями
        devices = [
            "Кодеки ВКС",
            "Huawei TE20",
            "Huawei TE40",
            "CloudLink Bar 310",
            #"CloudLink Box 300", 
            "Polycom RPG 310",
            "Коммутационное оборудование",
            "Extron IN1804",
            "Audio DSP",
            "Biamp Tesira Forte CI",
            "Управление питанием",
            "Aten PE8208AV"
        ]
        
        # Добавляем элементы в combo box
        for device in devices:
            self.device_combo.addItem(device)
            index = self.device_combo.count() - 1
            
            # Если это заголовок
            if device in headers:
                # Делаем заголовок невыбираемым
                self.device_combo.model().item(index).setEnabled(False)
                # Устанавливаем шрифт для заголовка
                font = self.device_combo.font()
                font.setPointSize(10)
                font.setBold(True)
                self.device_combo.model().item(index).setFont(font)
                # Устанавливаем цвет для заголовка
                self.device_combo.model().item(index).setForeground(QColor(self.colors["secondary"]))
        
        # Устанавливаем делегат для выравнивания заголовков по правому краю
        delegate = RightAlignHeaderDelegate(self.device_combo, headers)
        self.device_combo.setItemDelegate(delegate)
        
        self.device_combo.currentTextChanged.connect(self.on_device_change)
        self.device_combo.installEventFilter(self)
        
        device_label = QLabel("Устройство")
        device_label.setProperty("uiRole", "fieldLabel")

        # Метка и поле для IP-адреса
        ip_label = QLabel("IP-адрес")
        ip_label.setProperty("uiRole", "fieldLabel")
        
        self.ip_entry = QLineEdit()
        self.ip_entry.setObjectName("ipEntry")
        self.ip_entry.setMinimumWidth(160)
        self.ip_entry.setPlaceholderText("link.ru")
        self.ip_entry.setText("link.ru")
        self.ip_entry.returnPressed.connect(self.trigger_refresh_from_input)
        self.ip_entry.installEventFilter(self)
        
        # Кнопка для ввода пароля
        self.password_btn = QPushButton("Пароль")
        self.password_btn.setObjectName("passwordButton")
        self.password_btn.setProperty("uiRole", "secondary")
        self.password_btn.clicked.connect(self.show_password_dialog)
        
        # Кнопка обновления данных
        self.refresh_btn = QPushButton("Обновить данные")
        self.refresh_btn.setObjectName("refreshButton")
        self.refresh_btn.setProperty("uiRole", "primary")
        self.refresh_btn.clicked.connect(self.refresh_data)

        self.debug_btn = QPushButton("Отладка")
        self.debug_btn.setObjectName("debugButton")
        self.debug_btn.setProperty("uiRole", "secondary")
        self.debug_btn.clicked.connect(self.show_debug_window)

        self.setTabOrder(self.device_combo, self.ip_entry)
        self.setTabOrder(self.ip_entry, self.password_btn)
        self.setTabOrder(self.password_btn, self.refresh_btn)
        self.setTabOrder(self.refresh_btn, self.debug_btn)
        
        layout.addWidget(device_label, 0, 0)
        layout.addWidget(ip_label, 0, 1)
        layout.addWidget(self.device_combo, 1, 0)
        layout.addWidget(self.ip_entry, 1, 1)
        layout.addWidget(self.password_btn, 1, 2)
        layout.addWidget(self.refresh_btn, 1, 3)
        layout.addWidget(self.debug_btn, 1, 4)
        layout.setColumnStretch(0, 5)
        layout.setColumnStretch(1, 4)
        layout.setColumnStretch(2, 0)
        layout.setColumnStretch(3, 0)
        layout.setColumnStretch(4, 0)
        
        group_box.setLayout(layout)
        self.connection_panel = group_box
        return group_box
    def set_dark_theme(self):
        """Apply the centralized theme for direct window construction."""
        apply_theme(self)



    def init_screens(self):
        """Инициализация всех экранов"""
        self.screens = {
            "codec": CodecScreen(self),
            "matrix": MatrixScreen(self),
            "pdu": PDUScreen(self),
            "audio_dsp": AudioDSPScreen(self)
        }
    
    def create_update_time_panel(self):
        """Создание панели времени обновления"""
        panel = QWidget()
        panel.setObjectName("connectionStatusBar")
        panel.setProperty("uiRole", "statusBar")
        
        layout = QHBoxLayout(panel)
        layout.setSpacing(SPACING["sm"])
        layout.setContentsMargins(
            SPACING["sm"], SPACING["sm"], SPACING["sm"], 0
        )

        self.connection_indicator = StatusIndicator("inactive", show_text=False)
        self.connection_indicator.setObjectName("connectionIndicator")
        self.connection_indicator.setAccessibleName("Состояние соединения")

        self.connection_status = QLabel("Соединение: не установлено")
        self.connection_status.setObjectName("connectionStatus")
        self.connection_status.setProperty("uiRole", "secondary")
        
        time_label = QLabel("Последнее обновление:")
        time_label.setProperty("uiRole", "secondary")
        
        self.time_display = QLabel("Никогда")
        self.time_display.setProperty("uiRole", "secondary")
        self.time_display.setMinimumWidth(10)
        self.time_display.setAlignment(Qt.AlignLeft)
        
        layout.addWidget(self.connection_indicator)
        layout.addWidget(self.connection_status)
        layout.addStretch(1)
        layout.addWidget(time_label)
        layout.addWidget(self.time_display)
        
        return panel

    def set_connection_status(self, status: str, text: str):
        """Update the persistent connection summary without changing device logic."""
        if not hasattr(self, "connection_indicator"):
            return
        self.connection_indicator.set_status(status)
        self.connection_status.setText(text)
        for widget in (self.connection_indicator, self.connection_status):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def set_ui_state(self, state, text=None, screen=None):
        """Set the persistent state summary and, when requested, a screen state."""
        self.ui_state = coerce_ui_state(state)
        spec = state_spec(self.ui_state)
        self.setProperty("uiState", self.ui_state.value)
        self.set_connection_status(
            spec.indicator,
            text or f"Состояние: {spec.default_text}",
        )
        if screen is not None and hasattr(screen, "set_ui_state"):
            screen.set_ui_state(self.ui_state, text or spec.default_text)

    def _begin_request(self, device_name, ip_address, screen):
        self._request_serial += 1
        self._active_request = {
            "id": self._request_serial,
            "device": device_name,
            "ip": ip_address,
            "screen": screen,
        }
        self.set_ui_state(
            UIState.LOADING,
            f"Подключение к {device_name} ({ip_address})…",
            screen,
        )
        return self._active_request

    def _request_is_current(self, request_id, worker=None):
        request = self._active_request
        if request is None or request_id != request["id"]:
            return False
        return worker is None or worker is getattr(self, "current_worker", None)

    def _bind_worker(self, worker):
        """Bind worker signals to the request that created it."""
        if self._active_request is None:
            screen_type = self.device_to_screen.get(
                getattr(worker, "device_name", self.device_combo.currentText()),
                "codec",
            )
            self._begin_request(
                getattr(worker, "device_name", self.device_combo.currentText()),
                getattr(worker, "ip_address", self.ip_entry.text().strip()),
                self.screens.get(screen_type),
            )
        request_id = self._active_request["id"]
        worker.signals.result.connect(
            lambda data, w=worker, rid=request_id:
            self.on_device_data_received(data, w, rid)
        )
        worker.signals.error.connect(
            lambda error, w=worker, rid=request_id:
            self.on_device_error(error, w, rid)
        )
        worker.signals.progress.connect(
            lambda progress, w=worker, rid=request_id:
            self.on_progress_update(progress, w, rid)
        )
        worker.signals.status.connect(
            lambda status, w=worker, rid=request_id:
            self.on_status_update(status, w, rid)
        )
        worker.signals.finished.connect(
            lambda w=worker, rid=request_id:
            self.on_worker_finished(w, rid)
        )

    def _fail_request_start(self, error):
        """Leave loading deterministically when worker construction fails."""
        self.hide_progress_dialog()
        self.set_ui_state(
            UIState.REQUEST_ERROR,
            f"Не удалось запустить запрос: {error}",
            (self._active_request or {}).get("screen"),
        )
        if hasattr(self, "refresh_btn"):
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("Обновить данные")
    
    def generate_fake_data(self, codec_name):
        """Генерация тестовых данных для кодеков"""
        data = {
            "Версия прошивки": f"v{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
            "Модель кодеков": codec_name,
            "Серийный номер": f"SN{random.randint(100000, 999999)}",
            "MAC адрес": ":".join([f"{random.randint(0x00, 0xff):02x}" for _ in range(6)]),
            "SIP регистрация": random.choice(["Зарегистрирован", "Не зарегистрирован"]),
            "Время работы": f"{random.randint(1, 100)} дней",
            "Температура": f"{random.randint(30, 60)}°C",
            "Скорость сети": f"{random.randint(10, 1000)} Мбит/с",
            "Статус звонка": random.choice(["Подключено", "Не подключено"]),
            "Статус презентации": random.choice(["Подключено", "Не подключено"]),
            "Громкость микрофона": f"{random.randint(0, 100)}%",
            "Громкость динамиков": f"{random.randint(0, 100)}%",
            "Статус камеры": random.choice(["Подключена", "Отключена"]),
            "Статус микрофона": random.choice(["Подключен", "Отключен"])
        }
        
        return data
    
    def on_device_change(self, device_name):
        """Обработка изменения выбранного устройства"""
        codec_screen = self.screens.get("codec") if hasattr(self, 'screens') else None
        if codec_screen and hasattr(codec_screen, 'reset_volume_session'):
            codec_screen.reset_volume_session()
        if codec_screen and hasattr(codec_screen, 'stop_te20_monitor_audio_polling'):
            codec_screen.stop_te20_monitor_audio_polling()
        if device_name != "Extron IN1804":
            self.disconnect_matrix_persistent_handler()

        screen_type = self.device_to_screen.get(device_name, "codec")
        if screen_type == "codec" and codec_screen and hasattr(codec_screen, 'update_parameters_display'):
            codec_screen.update_parameters_display()
        
        # Сохраняем тип экрана, который должен отображаться после обновления
        self.current_screen_type = screen_type
        
        # Показываем заглушку вместо экрана
        self.screen_container.setCurrentWidget(self.placeholder_widget)
        self._active_request = None
        self.hide_progress_dialog()
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("Обновить данные")
        self.set_ui_state(UIState.IDLE, "Данные ещё не запрашивались")
        
        # Обновляем IP адрес
        
        # Обновляем заголовок окна
        self.setWindowTitle(f"Диагностический модуль ММК - {device_name}")

    def eventFilter(self, obj, event):
        """Запускать обновление по Enter на списке устройств."""
        if isinstance(obj, QPushButton) and self._is_user_button_activation(obj, event):
            self.log_button_click(obj)

        # Выделение всего текста в IP-поле при клике
        if obj is getattr(self, 'ip_entry', None) and event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                QTimer.singleShot(0, self.ip_entry.selectAll)

        if obj is getattr(self, 'device_combo', None) and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.trigger_refresh_from_input()
                return True
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        super().showEvent(event)
        self._top_alignment_attempts = 0
        QTimer.singleShot(0, self._align_frame_to_screen_top)

    def _align_frame_to_screen_top(self):
        window_handle = self.windowHandle()
        screen = window_handle.screen() if window_handle is not None else QApplication.primaryScreen()
        if screen is None:
            return
        top = screen.availableGeometry().top()
        delta = top - self.frameGeometry().top()
        if delta:
            self.move(self.x(), self.y() + delta)
        self._top_alignment_attempts = getattr(self, "_top_alignment_attempts", 0) + 1
        if self._top_alignment_attempts < 3:
            QTimer.singleShot(0, self._align_frame_to_screen_top)

    def _is_user_button_activation(self, button, event):
        if not button.isEnabled():
            return False

        event_type = event.type()
        if event_type == QEvent.MouseButtonRelease:
            if event.button() != Qt.LeftButton or not button.rect().contains(event.pos()):
                return False
        elif event_type == QEvent.KeyRelease:
            if event.key() not in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
                return False
        else:
            return False

        event_key = (id(button), event_type, int(datetime.datetime.now().timestamp() * 1000))
        if event_key == self._last_logged_button_event:
            return False
        self._last_logged_button_event = event_key
        return True

    def _get_button_log_label(self, button):
        text = button.text().strip()
        tooltip = button.toolTip().strip()
        object_name = button.objectName().strip()

        if text and tooltip:
            return f"{text} ({tooltip})"
        if text:
            return text
        if tooltip:
            return tooltip
        if object_name:
            return object_name
        return button.__class__.__name__

    def log_button_click(self, button):
        try:
            os.makedirs(self.button_log_dir, exist_ok=True)

            device_model = self.device_combo.currentText() if hasattr(self, 'device_combo') else ""
            device_ip = self.ip_entry.text().strip() if hasattr(self, 'ip_entry') else ""
            clean_value = lambda value: str(value).replace("\r", " ").replace("\n", " ")
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_line = (
                f"[{timestamp}] "
                f"Модель: {clean_value(device_model)} | "
                f"IP: {clean_value(device_ip)} | "
                f"Кнопка: {clean_value(self._get_button_log_label(button))}\n"
            )

            with open(self.button_log_path, "a", encoding="utf-8") as log_file:
                log_file.write(log_line)
        except Exception as e:
            print(f"Button click log write failed: {e}")

    def trigger_refresh_from_input(self):
        """Унифицированный запуск обновления из полей ввода."""
        if hasattr(self, 'refresh_btn') and self.refresh_btn.isEnabled():
            self.refresh_btn.click()

    def get_current_matrix_credentials(self):
        device_name = "Extron IN1804"
        creds_list = self.device_credentials.get(device_name, [])
        if not creds_list:
            return None

        current_idx = self.get_current_credential_index(device_name, self.ip_entry.text().strip())
        if current_idx >= len(creds_list):
            current_idx = 0
        return creds_list[current_idx]

    def get_credential_key(self, device_name: str, ip_address: str = None):
        if ip_address:
            return f"{device_name}|{ip_address}"
        return device_name

    def get_current_credential_index(self, device_name: str, ip_address: str = None):
        key = self.get_credential_key(device_name, ip_address)
        if key in self.current_credential_index:
            return self.current_credential_index[key]
        return self.current_credential_index.get(device_name, 0)

    def set_current_credential_index(self, device_name: str, index: int, ip_address: str = None):
        self.current_credential_index[device_name] = index
        if ip_address:
            self.current_credential_index[self.get_credential_key(device_name, ip_address)] = index

    def get_device_connection_profile(self, device_name: str, ip_address: str = None):
        if ip_address:
            return self.device_connection_profiles.get((device_name, ip_address))
        return self.device_connection_profiles.get(device_name)

    def set_device_connection_profile(self, device_name: str, profile: dict, ip_address: str = None):
        self.device_connection_profiles[device_name] = profile
        if ip_address:
            self.device_connection_profiles[(device_name, ip_address)] = profile

    def ensure_matrix_persistent_handler(self, ip_address=None, username=None, password=None, force_reconnect=False):
        from handlers.extron.in1804 import ExtronIN1804Handler

        creds = None
        if username is None or password is None:
            creds = self.get_current_matrix_credentials()
            if not creds:
                raise RuntimeError("Нет credentials для Extron IN1804")
            username = creds.get('username', '')
            password = creds.get('password', '')

        if ip_address is None:
            ip_address = self.ip_entry.text().strip()

        same_connection = (
            self.matrix_persistent_handler is not None and
            self.matrix_persistent_ip == ip_address and
            self.matrix_persistent_username == username and
            self.matrix_persistent_password == password and
            self.matrix_persistent_handler.is_connected()
        )
        if same_connection and not force_reconnect:
            return self.matrix_persistent_handler

        self.disconnect_matrix_persistent_handler()

        handler = ExtronIN1804Handler(
            ip_address=ip_address,
            port=22023,
            username=username,
            password=password
        )
        handler.connect()

        self.matrix_persistent_handler = handler
        self.matrix_persistent_ip = ip_address
        self.matrix_persistent_username = username
        self.matrix_persistent_password = password
        self.matrix_keepalive_timer.start()
        print(f"Persistent Extron handler connected for {ip_address}")
        return handler

    def disconnect_matrix_persistent_handler(self):
        if hasattr(self, 'matrix_keepalive_timer') and self.matrix_keepalive_timer.isActive():
            self.matrix_keepalive_timer.stop()

        if self.matrix_persistent_handler:
            try:
                self.matrix_persistent_handler.disconnect()
            except Exception as e:
                print(f"Error disconnecting persistent Extron handler: {e}")

        self.matrix_persistent_handler = None
        self.matrix_persistent_ip = None
        self.matrix_persistent_username = None
        self.matrix_persistent_password = None

    @pyqtSlot()
    def on_matrix_keepalive(self):
        if not self.matrix_persistent_handler or not self.matrix_persistent_handler.is_connected():
            self.disconnect_matrix_persistent_handler()
            return

        original_log_callback = self.matrix_persistent_handler.log_callback
        try:
            self.matrix_persistent_handler.log_callback = None
            result = self.matrix_persistent_handler.send_command('w20STAT')
            if not result or not result.get('success'):
                raise RuntimeError(result.get('error', 'keepalive failed') if result else 'keepalive failed')
        except Exception as e:
            print(f"Matrix keepalive failed: {e}")
            self.disconnect_matrix_persistent_handler()
        finally:
            if self.matrix_persistent_handler:
                self.matrix_persistent_handler.log_callback = original_log_callback

    
    def switch_screen(self, screen_type):
        """Переключение между экранами"""
        if screen_type in self.screens:
            screen_index = list(self.screens.keys()).index(screen_type)
            self.screen_container.setCurrentIndex(screen_index)
            self.current_screen = self.screens[screen_type]
    
    def update_ip_for_device(self, device_name):
        """Обновление IP адреса для выбранного устройства"""
        ip_mapping = {
            "Huawei TE20": "link.ru",
            "Huawei TE40": "link.ru",
            "CloudLink Bar 310": "link.ru",  # Добавлено новое устройство
            "CloudLink Box 300": "link.ru",
            "Polycom RPG 310": "link.ru",
            "Extron IN1804": "link.ru"
        }
        
        self.ip_entry.setText(ip_mapping.get(device_name, "link.ru"))
    
    def validate_ip_address(self, ip: str) -> bool:
        """Валидация IP адреса"""
        import re
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        
        parts = ip.split('.')
        for part in parts:
            if not 0 <= int(part) <= 255:
                return False
        
        return True

    def ping_device(self, ip_address: str) -> bool:
        if platform.system().lower() == "windows":
            command = ["ping", "-n", "1", "-w", "1000", ip_address]
        else:
            command = ["ping", "-c", "1", "-W", "1", ip_address]

        try:
            startupinfo = None
            if platform.system().lower() == "windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo,
                timeout=2,
                check=False
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Ping check failed for {ip_address}: {e}")
            return False

    def ensure_ping_success(self, ip_address: str) -> bool:
        if self.ping_device(ip_address):
            return True

        self.set_ui_state(UIState.DISCONNECTED, f"Нет соединения с {ip_address}")
        QMessageBox.warning(self, "Внимание", "Ping неуспешен")
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("Обновить данные")
        return False

    def is_vcs_codec_device(self, device_name: str) -> bool:
        return self.device_to_screen.get(device_name) == "codec"

    def is_authentication_error(self, error_type: str, error_message: str) -> bool:
        message = str(error_message).lower()
        return (
            error_type == "authentication_error"
            or "authentication" in message
            or "аутентификац" in message
            or "авторизац" in message
            or "auth" in message
            or "401" in message
            or "403" in message
            or "16781315" in message
            or "100666780" in message
        )

    def refresh_data(self):
        """Обновление данных в зависимости от устройства"""
        ip_address = self.ip_entry.text().strip()
        device_name = self.device_combo.currentText()
        
        if not ip_address:
            self.set_ui_state(UIState.REQUEST_ERROR, "Не указан IP-адрес устройства")
            QMessageBox.warning(self, "Внимание", "Введите IP-адрес устройства")
            return
        
        if not self.validate_ip_address(ip_address):
            self.set_ui_state(UIState.REQUEST_ERROR, "Неверный формат IP-адреса")
            QMessageBox.warning(self, "Внимание", "Неверный формат IP-адреса")
            return

        try:
            # Credential resolution is deliberately before ping or worker network I/O.
            self._active_request_credentials = self.device_credentials.get(device_name)
        except CredentialConfigurationError as error:
            message = str(error)
            self.set_ui_state(UIState.REQUEST_ERROR, message)
            QMessageBox.warning(self, "Настройка credentials", message)
            return

        if not self.ensure_ping_success(ip_address):
            return

        self.set_current_credential_index(device_name, 0, ip_address)
        if device_name == "Extron IN1804":
            self.disconnect_matrix_persistent_handler()
        
        device_type = self.device_to_screen.get(device_name, "codec")
        
        # Определяем, какой экран нужно показывать после успешного обновления
        if device_type == "codec":
            target_screen = self.screens["codec"]
        elif device_type == "matrix":
            target_screen = self.screens["matrix"]
        elif device_type == "pdu":
            target_screen = self.screens["pdu"]
        elif device_type == "audio_dsp":
            target_screen = self.screens["audio_dsp"]
        else:
            target_screen = self.screens["codec"]

        self._begin_request(device_name, ip_address, target_screen)
        
        # Показываем экран
        self.screen_container.setCurrentWidget(target_screen)
        if device_type == "codec" and hasattr(target_screen, 'update_parameters_display'):
            target_screen.update_parameters_display()
        
        # Если есть метод очистки данных у экрана, вызываем его
        if hasattr(target_screen, 'clear_data'):
            target_screen.clear_data()
        elif hasattr(target_screen, 'update_data'):
            # Если нет clear_data, показываем индикатор загрузки через update_data
            target_screen.update_data({"status": "loading", "message": "Загрузка данных..."})
        if hasattr(target_screen, "set_ui_state"):
            target_screen.set_ui_state(UIState.LOADING, "Загрузка данных…")
        
        # Вызываем соответствующий метод обновления
        if device_name == "Aten PE8208AV":
            self.refresh_aten_pdu(ip_address)
        elif device_name == "Huawei TE40":
            self.refresh_huawei_te40(ip_address)
        elif device_name == "CloudLink Bar 310":  
            self.refresh_huawei_bar310(ip_address)
        elif device_name == "Huawei TE20":
            self.refresh_huawei_te20(ip_address)
        elif device_name == "Polycom RPG 310":
            self.refresh_polycom_rpg310(ip_address)
        elif device_name == "Extron IN1804":
            self.refresh_extron_in1804(ip_address)            
        elif device_name == "Biamp Tesira Forte CI":
            self.refresh_biamp_tesira_forte_ci(ip_address)
        elif device_type == "matrix":
            self.refresh_matrix_data(ip_address)
        else:
            QMessageBox.information(
                self,
                "Информация",
                f"Поддержка {device_name} будет добавлена позже"
            )


    def refresh_biamp_tesira_forte_ci(self, ip_address: str):
        """Refresh Biamp Tesira Forte CI read-only audio-DSP status."""
        if not self.validate_ip_address(ip_address):
            QMessageBox.warning(self, "Invalid IP", "Enter a valid IP address.")
            return

        device_name = self.device_combo.currentText()
        creds_list = self.device_credentials.get(device_name)
        current_idx = self.get_current_credential_index(device_name, ip_address)
        if current_idx >= len(creds_list):
            current_idx = 0
        creds = creds_list[current_idx]

        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("Connecting...")

        self.show_progress_dialog(f"Connecting to {device_name} (attempt {current_idx + 1}/{len(creds_list)})...")
        self.show_codec_poll_terminal(device_name, ip_address, current_idx + 1, len(creds_list), reset=(current_idx == 0))

        try:
            self.current_worker = BiampTesiraForteCIWorker(
                ip_address=ip_address,
                username=creds['username'],
                password=creds['password']
            )
            self.current_worker.creds_list = creds_list
            self.current_worker.current_idx = current_idx
            self.current_worker.device_name = device_name

            self._bind_worker(self.current_worker)
            self.current_worker.signals.terminal_log.connect(self.on_codec_poll_terminal_log)

            QThreadPool.globalInstance().start(self.current_worker)
        except Exception as e:
            self._fail_request_start(e)
            QMessageBox.critical(self, "Error", f"Could not create worker: {str(e)}")
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText("РћР±РЅРѕРІРёС‚СЊ РґР°РЅРЅС‹Рµ")


    def refresh_huawei_bar310(self, ip_address: str):
        """Обновление данных Huawei CloudLink Bar 310 с перебором credentials"""
        print(f"=== Начинаю обновление Huawei CloudLink Bar 310 для {ip_address} ===")
        
        if not self.validate_ip_address(ip_address):
            QMessageBox.warning(self, "Неверный IP адрес", "Введите корректный IP адрес.")
            return
        
        # Получаем список credentials для Bar 310
        device_name = self.device_combo.currentText()
        creds_list = self.device_credentials.get(device_name)
        
        # Создаем worker с текущими credentials
        current_idx = self.get_current_credential_index(device_name, ip_address)
        creds = creds_list[current_idx]
        
        
        # Отключаем кнопку
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("Подключение...")
        
        # Показываем прогресс
        self.show_progress_dialog(f"Подключение к {device_name} (попытка {current_idx + 1}/{len(creds_list)})...")
        self.show_codec_poll_terminal(device_name, ip_address, current_idx + 1, len(creds_list), reset=(current_idx == 0))
        
        try:
            from core.worker import HuaweiBar310Worker
            
            # Передаем creds_list в конструктор worker для корректной работы перебора
            self.current_worker = HuaweiBar310Worker(
                ip_address=ip_address,
                port=self.huawei_settings.get('port', 443),
                username=creds['username'],
                password=creds['password'],
                creds_list=creds_list
            )
            
            # Сохраняем информацию для повторных попыток
            self.current_worker.current_idx = current_idx
            self.current_worker.device_name = device_name
            
            # Подключаем сигналы
            self._bind_worker(self.current_worker)
            self.current_worker.signals.terminal_log.connect(self.on_codec_poll_terminal_log)
            
            # Запускаем
            QThreadPool.globalInstance().start(self.current_worker)
            print("Worker для Huawei CloudLink Bar 310 запущен")
            
        except Exception as e:
            print(f"Ошибка создания Worker: {e}")
            self._fail_request_start(e)
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать Worker: {str(e)}")
            
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText("Обновить данные")

    def refresh_huawei_te20(self, ip_address: str):
        """Обновление данных Huawei TE20 с перебором credentials"""
        print(f"=== Начинаю обновление TE-20 для {ip_address} ===")
        
        if not self.validate_ip_address(ip_address):
            QMessageBox.warning(self, "Неверный IP адрес", "Введите корректный IP адрес.")
            return
        
        # Получаем список credentials для TE-20
        device_name = self.device_combo.currentText()
        creds_list = self.device_credentials.get(device_name)

        # Создаем worker с текущими credentials
        current_idx = self.get_current_credential_index(device_name, ip_address)
        creds = creds_list[current_idx]
        
        
        # Отключаем кнопку
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("Подключение...")
        
        # Показываем прогресс
        self.show_progress_dialog(f"Подключение к {device_name} (попытка {current_idx + 1}/{len(creds_list)})...")
        self.show_te20_terminal(ip_address, current_idx + 1, len(creds_list), reset=(current_idx == 0))
        
        try:
            from core.te20_worker import HuaweiTE20Worker
            
            self.current_worker = HuaweiTE20Worker(
                ip_address=ip_address,
                port=80,  # TE-20 использует HTTP порт 80
                username=creds['username'],
                password=creds['password']
            )
            
            # Сохраняем информацию для повторных попыток
            self.current_worker.creds_list = creds_list
            self.current_worker.current_idx = current_idx
            self.current_worker.device_name = device_name
            
            # Подключаем сигналы
            self._bind_worker(self.current_worker)
            self.current_worker.signals.terminal_log.connect(self.on_te20_terminal_log)
            
            # Запускаем
            QThreadPool.globalInstance().start(self.current_worker)
            print("Worker TE-20 запущен")
            
        except Exception as e:
            print(f"Ошибка создания Worker: {e}")
            self._fail_request_start(e)
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать Worker: {str(e)}")
            
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText("Обновить данные")

    def refresh_huawei_te40(self, ip_address: str):
        """Обновление данных Huawei TE40 с перебором credentials"""
        print(f"=== Начинаю обновление для {ip_address} ===")
        
        if not self.validate_ip_address(ip_address):
            QMessageBox.warning(self, "Неверный IP адрес", "Введите корректный IP адрес.")
            return
        
        # Получаем список credentials для TE-40
        device_name = self.device_combo.currentText()
        creds_list = self.device_credentials.get(device_name)
        
        # Создаем worker с текущими credentials
        current_idx = self.get_current_credential_index(device_name, ip_address)
        creds = creds_list[current_idx]
        
        
        # Отключаем кнопку
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("Подключение...")
        
        # Показываем прогресс
        self.show_progress_dialog(f"Подключение к {device_name} (попытка {current_idx + 1}/{len(creds_list)})...")
        self.show_codec_poll_terminal(device_name, ip_address, current_idx + 1, len(creds_list), reset=(current_idx == 0))
        
        try:
            from core.worker import HuaweiTE40Worker
            
            self.current_worker = HuaweiTE40Worker(
                ip_address=ip_address,
                port=self.huawei_settings.get('port', 443),
                username=creds['username'],
                password=creds['password']
            )
            
            # Сохраняем информацию для повторных попыток
            self.current_worker.creds_list = creds_list
            self.current_worker.current_idx = current_idx
            self.current_worker.device_name = device_name
            
            # Подключаем сигналы
            self._bind_worker(self.current_worker)
            self.current_worker.signals.terminal_log.connect(self.on_codec_poll_terminal_log)
            
            # Запускаем
            QThreadPool.globalInstance().start(self.current_worker)
            print("Worker запущен")
            
        except Exception as e:
            print(f"Ошибка создания Worker: {e}")
            self._fail_request_start(e)
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать Worker: {str(e)}")
            
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText("Обновить данные")

    def refresh_polycom_rpg310(self, ip_address: str):
        """Обновление данных Polycom RPG 310 с перебором credentials"""
        print(f"=== Начинаю обновление Polycom RPG 310 для {ip_address} ===")
        
        if not self.validate_ip_address(ip_address):
            QMessageBox.warning(self, "Неверный IP адрес", "Введите корректный IP адрес.")
            return
        
        # Получаем список credentials для Polycom
        device_name = self.device_combo.currentText()
        creds_list = self.device_credentials.get(device_name)
        
        # Создаем worker с текущими credentials
        current_idx = self.current_credential_index.get(device_name, 0)
        creds = creds_list[current_idx]
        
        
        # Отключаем кнопку
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("Подключение...")
        
        # Показываем прогресс
        self.show_progress_dialog(f"Подключение к {device_name} (попытка {current_idx + 1}/{len(creds_list)})...")
        self.show_codec_poll_terminal(device_name, ip_address, current_idx + 1, len(creds_list), reset=(current_idx == 0))
        
        try:
            from core.worker import PolycomRPG310Worker
            
            self.current_worker = PolycomRPG310Worker(
                ip_address=ip_address,
                port=443,
                username=creds['username'],
                password=creds['password']
            )
            
            # Сохраняем информацию для повторных попыток
            self.current_worker.creds_list = creds_list
            self.current_worker.current_idx = current_idx
            self.current_worker.device_name = device_name
            
            # Подключаем сигналы
            self._bind_worker(self.current_worker)
            self.current_worker.signals.terminal_log.connect(self.on_codec_poll_terminal_log)
            
            # Запускаем
            QThreadPool.globalInstance().start(self.current_worker)
            print("Worker для Polycom RPG 310 запущен")
            
        except Exception as e:
            print(f"Ошибка создания Worker: {e}")
            self._fail_request_start(e)
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать Worker: {str(e)}")
            
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText("Обновить данные")

    def refresh_extron_in1804(self, ip_address: str):
        """Обновление данных Extron IN1804 с перебором credentials"""
        print(f"=== Начинаю обновление Extron IN1804 для {ip_address} ===")
        
        if not self.validate_ip_address(ip_address):
            QMessageBox.warning(self, "Неверный IP адрес", "Введите корректный IP адрес.")
            return
        
        # Получаем список credentials для Extron IN1804
        device_name = self.device_combo.currentText()
        creds_list = self.device_credentials.get(device_name)
        
        # Создаем worker с текущими credentials
        current_idx = self.current_credential_index.get(device_name, 0)
        creds = creds_list[current_idx]
        
        
        # Отключаем кнопку
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("Подключение...")
        
        # Показываем прогресс
        self.show_progress_dialog(f"Подключение к {device_name} (попытка {current_idx + 1}/{len(creds_list)})...")
        self.show_matrix_terminal(ip_address, current_idx + 1, len(creds_list), reset=(current_idx == 0))
        
        try:
            from core.worker import ExtronIN1804Worker
            
            self.current_worker = ExtronIN1804Worker(
                ip_address=ip_address,
                port=22023,
                username=creds['username'],
                password=creds['password']
            )
            
            # Сохраняем информацию для повторных попыток
            self.current_worker.creds_list = creds_list
            self.current_worker.current_idx = current_idx
            self.current_worker.device_name = device_name
            
            # Подключаем сигналы
            self._bind_worker(self.current_worker)
            self.current_worker.signals.terminal_log.connect(self.on_terminal_log)
            
            # Запускаем
            QThreadPool.globalInstance().start(self.current_worker)
            print("Worker для Extron IN1804 запущен")
            
        except Exception as e:
            print(f"Ошибка создания Worker: {e}")
            self._fail_request_start(e)
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать Worker: {str(e)}")
            
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText("Обновить данные")

    def refresh_aten_pdu(self, ip_address: str):
        """Обновление данных Aten PDU с перебором credentials"""
        print(f"=== Начинаю обновление Aten PE8208AV для {ip_address} ===")
        
        if not self.validate_ip_address(ip_address):
            QMessageBox.warning(self, "Неверный IP адрес", "Введите корректный IP адрес.")
            return
        
        # Получаем список credentials для PDU
        device_name = self.device_combo.currentText()
        creds_list = self.device_credentials.get(device_name)
        
        # Создаем worker с текущими credentials
        current_idx = self.current_credential_index.get(device_name, 0)
        creds = creds_list[current_idx]
        
        
        # Отключаем кнопку
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("Подключение...")
        
        # Показываем прогресс
        self.show_progress_dialog(f"Подключение к {device_name} (попытка {current_idx + 1}/{len(creds_list)})...")
        
        try:
            from core.worker import AtenPDUWorker
            
            self.current_worker = AtenPDUWorker(
                ip_address=ip_address,
                port=443,
                username=creds['username'],
                password=creds['password']
            )
            
            # Сохраняем информацию для повторных попыток
            self.current_worker.creds_list = creds_list
            self.current_worker.current_idx = current_idx
            self.current_worker.device_name = device_name
            
            # Подключаем сигналы
            self._bind_worker(self.current_worker)
            
            # Запускаем
            QThreadPool.globalInstance().start(self.current_worker)
            print("Worker для Aten PDU запущен")
            
        except Exception as e:
            print(f"Ошибка создания Worker: {e}")
            self._fail_request_start(e)
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать Worker: {str(e)}")
            
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText("Обновить данные")
    
    def control_pdu_outlet(self, outlet_num: int, command: str):
        """Управление розеткой PDU"""
        device_name = self.device_combo.currentText()
        ip_address = self.ip_entry.text().strip()
        
        if device_name != "Aten PE8208AV":
            return

        self.set_ui_state(
            UIState.COMMAND,
            f"Выполнение команды для розетки {outlet_num}…",
        )
        
        print(f"Управление PDU: розетка {outlet_num}, команда {command}")
        
        # Получаем текущие credentials
        current_idx = self.current_credential_index.get(device_name, 0)
        creds_list = self.device_credentials.get(device_name, [])
        
        if current_idx < len(creds_list):
            creds = creds_list[current_idx]
            
            # Создаем обработчик для отправки команды
            try:
                from handlers.aten.pdu import AtenPDUHandler
                
                handler = AtenPDUHandler(
                    ip_address=ip_address,
                    port=443,
                    username=creds['username'],
                    password=creds['password']
                )
                
                if handler.connect():
                    if command == "on":
                        success = handler.turn_on(outlet_num)
                    elif command == "off":
                        success = handler.turn_off(outlet_num)
                    elif command == "reboot":
                        success = handler.reboot(outlet_num)
                    else:
                        success = False
                    
                    if success:
                        self.set_ui_state(
                            UIState.CONNECTED,
                            f"Команда для розетки {outlet_num} выполнена",
                        )
                        QMessageBox.information(
                            self,
                            "Успех",
                            f"Команда '{command}' для розетки {outlet_num} выполнена"
                        )
                        # Обновляем данные после выполнения команды
                        self.refresh_data()
                    else:
                        self.set_ui_state(
                            UIState.REQUEST_ERROR,
                            f"Команда для розетки {outlet_num} не выполнена",
                        )
                        QMessageBox.warning(
                            self,
                            "Ошибка",
                            f"Не удалось выполнить команду '{command}' для розетки {outlet_num}"
                        )
                    
                    handler.disconnect()
                
            except Exception as e:
                self.set_ui_state(
                    UIState.REQUEST_ERROR,
                    f"Ошибка команды PDU: {e}",
                )
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Ошибка при управлении PDU: {str(e)}"
                )


    def update_time_display(self):
        """Обновление отображения времени"""
        
        from PyQt5.QtCore import QDateTime
        
        if self.last_update_time and isinstance(self.last_update_time, QDateTime):
            current_time = QDateTime.currentDateTime()
            seconds = self.last_update_time.secsTo(current_time)
            
            if seconds < 60:
                time_text = "Только что"
            elif seconds < 3600:
                minutes = seconds // 60
                if minutes == 1:
                    time_text = "1 минуту назад"
                elif minutes < 5:
                    time_text = f"{minutes} минуты назад"
                else:
                    time_text = f"{minutes} минут назад"
            elif seconds < 86400:
                hours = seconds // 3600
                if hours == 1:
                    time_text = "1 час назад"
                elif hours < 5:
                    time_text = f"{hours} часа назад"
                else:
                    time_text = f"{hours} часов назад"
            else:
                days = seconds // 86400
                if days == 1:
                    time_text = "1 день назад"
                else:
                    time_text = f"{days} дней назад"
            
            self.time_display.setText(time_text)
        else:
            self.time_display.setText("Никогда")


    def on_device_data_received(self, data, worker=None, request_id=None):
        """Обработка полученных данных от устройства"""
        if request_id is not None and not self._request_is_current(request_id, worker):
            return
        worker = worker or getattr(self, "current_worker", None)
        data = dict(data)
        partial_update = bool(data.pop('_partial_update', False))
        if not partial_update:
            self.hide_progress_dialog()
        if not partial_update and self.device_combo.currentText() == "Extron IN1804":
            self.finish_matrix_terminal("Опрос завершён успешно")
        elif not partial_update and self.device_combo.currentText() == "Huawei TE20":
            self.finish_te20_terminal("Опрос завершён успешно")

        meaningful_keys = [
            key for key, value in data.items()
            if key != 'ip_address' and value not in (None, '', {}, [], 'N/A', 'Не доступно')
        ]
        if not meaningful_keys:
            screen = (self._active_request or {}).get("screen")
            self.set_ui_state(
                UIState.UNAVAILABLE,
                "Устройство ответило, но доступных значений нет",
                screen,
            )
            QMessageBox.warning(
                self,
                "Нет данных",
                "Устройство ответило, но полезные данные для отображения не получены.\n"
                "Проверьте API/протокол подключения для выбранной модели."
            )
            return
        
        # Сбрасываем индекс на успешный credentials для этого устройства
        if worker:
            device_name = getattr(worker, 'device_name', None)
            current_idx = getattr(worker, 'current_idx', 0)
            if device_name:
                self.set_current_credential_index(device_name, current_idx, data.get('ip_address', self.ip_entry.text()))
                connection_profile = data.get('connection_profile')
                if isinstance(connection_profile, dict) and connection_profile:
                    self.set_device_connection_profile(
                        device_name,
                        connection_profile,
                        data.get('ip_address', self.ip_entry.text())
                    )
                print(f"Запомнен успешный credentials #{current_idx + 1} для {device_name}")
                if device_name == "Extron IN1804":
                    creds_list = getattr(worker, 'creds_list', [])
                    if creds_list and current_idx < len(creds_list):
                        creds = creds_list[current_idx]
                        try:
                            self.ensure_matrix_persistent_handler(
                                ip_address=data.get('ip_address', self.ip_entry.text()),
                                username=creds.get('username', ''),
                                password=creds.get('password', '')
                            )
                        except Exception as e:
                            print(f"Failed to establish persistent Extron handler: {e}")
        
        # Обновляем данные на текущем экране
        current_screen = (self._active_request or {}).get("screen")
        if current_screen is None and hasattr(self, 'current_screen_type'):
            current_screen = self.screens.get(self.current_screen_type)
        if current_screen:
            current_screen.update_data(data)
        
        from PyQt5.QtCore import QDateTime
        self.last_update_time = QDateTime.currentDateTime()
        self.update_time_display()
        if partial_update:
            self.set_ui_state(
                UIState.LOADING,
                "Получены частичные данные; запрос продолжается…",
            )
            if (
                worker
                and getattr(worker, 'device_name', None) == "Polycom RPG 310"
            ):
                if self.progress_dialog is None:
                    self.show_progress_dialog("Подключение по SSH для дополнительных параметров...")
                if self.progress_dialog is not None:
                    self.progress_dialog.setRange(0, 100)
                    self.progress_dialog.setValue(60)
                    self.progress_dialog.setLabelText("Подключение по SSH для дополнительных параметров...")
                    self.progress_dialog.show()
                    self.progress_dialog.raise_()
                    self.progress_dialog.activateWindow()
            return

        self.set_ui_state(
            UIState.CONNECTED,
            "Соединение установлено; данные обновлены",
        )

        if getattr(self, 'suppress_success_message_once', False):
            self.suppress_success_message_once = False
            return

        device_name = self.device_combo.currentText()
        message_text = (
            f"Данные для {device_name} успешно получены\n"
            f"IP: {data.get('ip_address', self.ip_entry.text())}"
        )
        protocol = data.get('connection_protocol')
        if protocol:
            message_text += f"\nПротокол: {protocol}"

        QMessageBox.information(
            self,
            "Данные получены",
            message_text
        )

   
    def on_device_error(self, error_info, worker=None, request_id=None):
        """Обработка ошибок от устройства с автоматическим перебором credentials"""
        if request_id is not None and not self._request_is_current(request_id, worker):
            return
        worker = worker or getattr(self, "current_worker", None)
        error_type, error, traceback_text = error_info
        if worker and getattr(worker, 'device_name', None) == "Extron IN1804":
            self.finish_matrix_terminal(f"Опрос завершён с ошибкой: {error}")
        elif worker and getattr(worker, 'device_name', None) == "Huawei TE20":
            self.finish_te20_terminal(f"Опрос завершён с ошибкой: {error}")
        
        # Проверяем, есть ли текущий worker и нужно ли пробовать другие credentials
        if worker:
            device_name = getattr(worker, 'device_name', None)
            creds_list = getattr(worker, 'creds_list', [])
            current_idx = getattr(worker, 'current_idx', 0)
            
            error_message = str(error)
            is_auth_error = self.is_authentication_error(error_type, error_message)

            # Если это ошибка аутентификации и есть еще credentials для проверки
            if is_auth_error and creds_list and current_idx < len(creds_list) - 1:
                
                # Переходим к следующему credentials
                next_idx = current_idx + 1
                self.set_current_credential_index(device_name, next_idx, getattr(worker, 'ip_address', None))
                
                print(f"Ошибка аутентификации. Пробуем следующие credentials ({next_idx + 1}/{len(creds_list)})...")
                
                # Скрываем текущий прогресс диалог
                self.hide_progress_dialog()
                self.set_ui_state(
                    UIState.LOADING,
                    f"Ошибка авторизации; попытка {next_idx + 1} из {len(creds_list)}…",
                )
                
                # Повторяем попытку с новыми credentials
                if device_name == "Huawei TE40":
                    self.refresh_huawei_te40(worker.ip_address)
                elif device_name == "CloudLink Bar 310":  # Добавлено новое условие
                    self.refresh_huawei_bar310(worker.ip_address)
                elif device_name == "Huawei TE20":
                    self.refresh_huawei_te20(worker.ip_address)
                elif device_name == "Polycom RPG 310":
                    self.refresh_polycom_rpg310(worker.ip_address)
                elif device_name == "Extron IN1804":
                    self.refresh_extron_in1804(worker.ip_address)
                elif device_name == "Aten PE8208AV":  # Добавить эту ветку
                    self.refresh_aten_pdu(worker.ip_address)
                elif device_name == "Biamp Tesira Forte CI":
                    self.refresh_biamp_tesira_forte_ci(worker.ip_address)
                return
                      
        
        # Если нет других credentials или ошибка не связана с аутентификацией
        self.hide_progress_dialog()
        
        error_message = str(error)
        is_auth_error = self.is_authentication_error(error_type, error_message)
        device_name = getattr(worker, 'device_name', self.device_combo.currentText())

        if is_auth_error and self.is_vcs_codec_device(device_name):
            user_message = "Авторизация неуспешна"
        elif "Connection refused" in error_message or "timed out" in error_message:
            user_message = "Не удалось подключиться к устройству.\nПроверьте:\n1. IP адрес\n2. Сетевое подключение\n3. Порт устройства"
        elif is_auth_error:
            user_message = "Авторизация неуспешна"
        elif "SSL" in error_message:
            user_message = "Ошибка SSL соединения.\nПопробуйте отключить проверку SSL сертификата."
        else:
            user_message = f"Ошибка: {error_message}"
        
        if is_auth_error:
            self.set_ui_state(
                UIState.AUTH_ERROR,
                "Ошибка авторизации: проверьте учётные данные",
                (self._active_request or {}).get("screen"),
            )
            QMessageBox.warning(
                self,
                "Авторизация",
                user_message
            )
        else:
            self.set_ui_state(
                UIState.REQUEST_ERROR,
                f"Ошибка запроса: {error_message}",
                (self._active_request or {}).get("screen"),
            )
            QMessageBox.critical(
                self,
                "Ошибка подключения",
                user_message
            )
        
        # Включаем кнопку обратно
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("Обновить данные")
    
    def on_progress_update(self, progress, worker=None, request_id=None):
        """Обработка обновления прогресса"""
        if request_id is not None and not self._request_is_current(request_id, worker):
            return
        if self.progress_dialog is not None:
            try:
                if self.progress_dialog.maximum() == 0:
                    self.progress_dialog.setRange(0, 100)
                self.progress_dialog.setValue(progress)
                try:
                    if progress < 100:
                        self.progress_dialog.setLabelText(f"Прогресс: {progress}%")
                except AttributeError:
                    # setLabelText уже не работает, но setValue сработал
                    pass
                if (
                    progress >= 68
                    and worker
                    and getattr(worker, 'device_name', None) == "Polycom RPG 310"
                ):
                    self.progress_dialog.show()
                    self.progress_dialog.raise_()
                    self.progress_dialog.activateWindow()
            except AttributeError:
                # Диалог уже закрыт
                self.progress_dialog = None                 
    
    def on_status_update(self, status, worker=None, request_id=None):
        """Обработка обновления статуса"""
        if request_id is not None and not self._request_is_current(request_id, worker):
            return
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.setLabelText(status)
        if self.ui_state in {UIState.LOADING, UIState.COMMAND}:
            self.set_connection_status("loading", status)
        print(f"Status: {status}")
    
    def on_worker_finished(self, worker=None, request_id=None):
        """Обработка завершения работы Worker"""
        if request_id is not None and not self._request_is_current(request_id, worker):
            return
        self.hide_progress_dialog()
        
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("Обновить данные")
    

    def on_progress_canceled(self):
        """Обработка отмены прогресса"""
        print("Operation cancelled by user")
        self.hide_progress_dialog()
    
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("Обновить данные")
    

    
    def show_success_message(self, message: str):
        """Показать сообщение об успехе"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Данные обновлены")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.exec_()

    def generate_matrix_data(self):
        """Генерация тестовых данных для матрицы"""
        return {
            "Температура": f"{random.randint(35, 55)}°C",
            "Версия прошивки": f"{random.randint(1, 5)}.{random.randint(0, 9)}",
            "Время работы": f"{random.randint(1, 365)} дней"
        }

    def show_password_dialog(self):
        """Показать диалог ввода пароля с кастомными стилями"""
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Ввод нестандартного пароля")
        dialog.setLabelText(f"Введите нестандартный пароль для {self.device_combo.currentText()}:\nIP: {self.ip_entry.text()}")
        dialog.setTextEchoMode(QLineEdit.Password)
        
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
            }}
            QLabel {{
                color: {self.colors['text_primary']};
                font-size: 11pt;
            }}
            QLineEdit {{
                background-color: {self.colors['background']};
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['divider']};
                border-radius: 4px;
                padding: 10px;
                font-size: 11pt;
                selection-background-color: {self.colors['primary']};
                selection-color: black;
            }}
            QLineEdit:focus {{
                border: 2px solid {self.colors['primary']};
            }}
            QPushButton {{
                background-color: {self.colors['background']};
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['divider']};
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 11pt;
                font-weight: bold;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['divider']};
                border: 1px solid {self.colors['primary']};
            }}
            QPushButton:pressed {{
                background-color: {self.colors['primary']};
                color: black;
            }}
        """)
        
        dialog.resize(400, 200)
        result = dialog.exec_()
        
        if result and dialog.textValue():
            password = dialog.textValue()
            device_name = self.device_combo.currentText()
            
            # Добавляем новый пароль в начало списка credentials для текущего устройства
            if device_name in self.device_credentials:
                # Создаем новый credentials с пустым username (или можно спросить username)
                # По умолчанию используем username 'api' для большинства устройств
                default_username = 'admin'
                
                # Для некоторых устройств нужно использовать другие username
                if device_name == "Aten PE8208AV":
                    default_username = 'admin'
                elif device_name == "Polycom RPG 310":
                    default_username = 'admin'
                elif device_name == "Extron IN1804":
                    default_username = 'admin'
                
                # Создаем новый credentials
                new_credential = {'username': default_username, 'password': password}
                
                # Проверяем, нет ли уже такого пароля в списке
                exists = False
                for cred in self.device_credentials[device_name]:
                    if cred['password'] == password:
                        exists = True
                        break
                
                if not exists:
                    # Добавляем новый пароль в начало списка
                    self.device_credentials[device_name].insert(0, new_credential)
                    
                    # Сбрасываем индекс на новый credentials
                    self.current_credential_index[device_name] = 0
                    
                    QMessageBox.information(
                        self, 
                        "Успех", 
                        f"Пароль для {device_name} успешно сохранен\n"
                        f"Username: {default_username}\n"
                        f"Пароль будет использован при следующем подключении"
                    )
                    print(f"Добавлены новые credentials для {device_name}")
                else:
                    QMessageBox.information(
                        self, 
                        "Информация", 
                        f"Пароль для {device_name} уже существует в списке\n"
                        f"Пароль будет использован при следующем подключении"
                    )
                    # Находим индекс существующего пароля и делаем его первым
                    for i, cred in enumerate(self.device_credentials[device_name]):
                        if cred['password'] == password:
                            # Перемещаем в начало
                            self.device_credentials[device_name].insert(0, self.device_credentials[device_name].pop(i))
                            self.current_credential_index[device_name] = 0
                            break
            else:
                # Если устройство еще не в словаре, создаем новую запись
                default_username = 'admin'
                if device_name == "Aten PE8208AV":
                    default_username = 'admin'
                elif device_name == "Polycom RPG 310":
                    default_username = 'admin'
                elif device_name == "Extron IN1804":
                    default_username = 'admin'
                
                self.device_credentials[device_name] = [
                    {'username': default_username, 'password': password}
                ]
                self.current_credential_index[device_name] = 0
                
                QMessageBox.information(
                    self, 
                    "Успех", 
                    f"Пароль для {device_name} успешно сохранен\n"
                    f"Username: {default_username}\n"
                    f"Пароль будет использован при следующем подключении"
                )
                print(f"Создана новая запись credentials для {device_name}")
    
    def show_password_dialog(self):
        """Показать диалог ввода логина и пароля."""
        device_name = self.device_combo.currentText()
        default_username = self.get_default_username_for_device(device_name)

        dialog = QDialog(self)
        dialog.setWindowTitle("Ввод нестандартных credentials")
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        info_label = QLabel(f"Введите логин и пароль для {device_name}:\nIP: {self.ip_entry.text()}")
        info_label.setWordWrap(True)

        form_layout = QFormLayout()
        username_entry = QLineEdit()
        username_entry.setText(default_username)
        password_entry = QLineEdit()
        password_entry.setEchoMode(QLineEdit.Password)

        form_layout.addRow("Логин:", username_entry)
        form_layout.addRow("Пароль:", password_entry)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        layout.addWidget(info_label)
        layout.addLayout(form_layout)
        layout.addWidget(buttons)

        dialog.resize(420, 220)
        if dialog.exec_() != QDialog.Accepted:
            return

        username = username_entry.text().strip()
        password = password_entry.text()

        if not username or not password:
            QMessageBox.warning(self, "Внимание", "Заполните и логин, и пароль.")
            return

        new_credential = {'username': username, 'password': password}
        creds_list = self.device_credentials.setdefault(device_name, [])

        existing_index = None
        for i, cred in enumerate(creds_list):
            if cred.get('username') == username and cred.get('password') == password:
                existing_index = i
                break

        if existing_index is None:
            creds_list.insert(0, new_credential)
            message_title = "Успех"
            message_text = (
                f"Credentials для {device_name} успешно сохранены\n"
                f"Username: {username}\n"
                f"Логин и пароль будут использованы при следующем подключении"
            )
        else:
            creds_list.insert(0, creds_list.pop(existing_index))
            message_title = "Информация"
            message_text = (
                f"Такие credentials для {device_name} уже есть в списке\n"
                f"Логин и пароль будут использованы при следующем подключении"
            )

        self.set_current_credential_index(device_name, 0, self.ip_entry.text().strip())
        QMessageBox.information(self, message_title, message_text)
        print(f"Сохранены credentials для {device_name}: {username}:***")

    def get_default_username_for_device(self, device_name):
        """Вернуть логин по умолчанию для устройства."""
        default_username = 'admin'
        if device_name == "Aten PE8208AV":
            default_username = 'admin'
        elif device_name == "Polycom RPG 310":
            default_username = 'admin'
        elif device_name == "Extron IN1804":
            default_username = 'admin'
        return default_username

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


    def fix_sip_huawei_te40(self, ip_address: str):
        """Исправление SIP регистрации для Huawei TE40"""
        print(f"Исправление SIP регистрации для TE-40 на {ip_address}")
        
        # Жёстко заданный SIP сервер
        sip_server = "link.ru"
        
        # Показываем диалог прогресса
        self.show_progress_dialog(f"Установка SIP сервера {sip_server}...")
        
        try:
            # Получаем текущие credentials
            device_name = "Huawei TE40"
            creds_list = self.device_credentials.get(device_name, [])
            current_idx = self.current_credential_index.get(device_name, 0)
            if not creds_list:
                raise CredentialConfigurationError("Credentials are required before setting a SIP server.")
            creds = creds_list[current_idx]
            
            # Создаем worker для установки SIP
            from core.worker import HuaweiTE40Worker
            
            self.fix_worker = HuaweiTE40Worker(
                ip_address=ip_address,
                port=self.huawei_settings.get('port', 443),
                username=creds['username'],
                password=creds['password']
            )
            
            # Подключаем сигналы
            self.fix_worker.signals.result.connect(self.on_sip_fix_result)
            self.fix_worker.signals.error.connect(self.on_sip_fix_error)
            self.fix_worker.signals.status.connect(self.on_status_update)
            self.fix_worker.signals.finished.connect(self.on_worker_finished)
            
            # Запускаем установку SIP сервера
            QThreadPool.globalInstance().start(self.fix_worker)
            self.fix_worker.set_sip_server(sip_server)
            
        except Exception as e:
            self.hide_progress_dialog()
            QMessageBox.critical(self, "Ошибка", f"Не удалось установить SIP сервер: {str(e)}")

  
    @pyqtSlot(dict)
    def on_sip_fix_result(self, result):
        """Обработка результата установки SIP сервера"""
        self.hide_progress_dialog()
        
        if result.get('action') == 'set_sip_server':
            if result.get('success'):
                QMessageBox.information(
                    self,
                    "Успех",
                    result.get('message', 'SIP сервер успешно установлен')
                )
                # Обновляем данные после успешной установки
                self.refresh_data()
            else:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    result.get('message', 'Не удалось установить SIP сервер')
                )
    
    @pyqtSlot(tuple)
    def on_sip_fix_error(self, error_info):
        """Обработка ошибки установки SIP сервера"""
        self.hide_progress_dialog()
        error_type, error, traceback_text = error_info
        
        QMessageBox.critical(
            self,
            "Ошибка",
            f"Не удалось установить SIP сервер:\n{str(error)}"
        )



    def on_fix_sip_registration(self, ip_address: str, device_name: str):
        """Обработчик нажатия кнопки 'Исправить' для SIP регистрации"""
        print(f"=== Нажата кнопка Исправить для {device_name} ({ip_address}) ===")
        
        # Жёстко заданный SIP сервер
        sip_server = "link.ru"
        
        # Показываем диалог с вопросом
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы действительно хотите установить SIP сервер\n"
            f"{sip_server}\n\n"
            f"на устройстве {device_name}?\nIP: {ip_address}\n\n"
            f"Это действие может занять несколько секунд.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # В зависимости от типа устройства вызываем соответствующий метод
            if device_name == "Huawei TE40":
                self.fix_sip_huawei_te40(ip_address)
            elif device_name == "CloudLink Bar 310":
                # TODO: реализовать для Bar 310
                QMessageBox.information(self, "Информация", "Поддержка Bar 310 будет добавлена позже")
            elif device_name == "Huawei TE20":
                # TODO: реализовать для TE-20
                QMessageBox.information(self, "Информация", "Поддержка TE-20 будет добавлена позже")
            elif device_name == "Polycom RPG 310":
                # TODO: реализовать для Polycom
                QMessageBox.information(self, "Информация", "Поддержка Polycom будет добавлена позже")
            else:
                QMessageBox.information(
                    self,
                    "Информация",
                    f"Исправление SIP регистрации для {device_name} будет добавлено позже"
                )


    def fix_sip_huawei_te40(self, ip_address: str):
        """Исправление SIP регистрации для Huawei TE40"""
        print(f"\n=== fix_sip_huawei_te40 called ===")
        print(f"IP Address: {ip_address}")
        
        sip_server = "link.ru"
        print(f"SIP Server to set: {sip_server}")
        
        self.show_progress_dialog(f"Установка SIP сервера {sip_server}...")
        
        try:
            # Получаем текущие credentials
            device_name = "Huawei TE40"
            creds_list = self.device_credentials.get(device_name, [])
            current_idx = self.current_credential_index.get(device_name, 0)
            if not creds_list:
                raise CredentialConfigurationError("Credentials are required before setting a SIP server.")
            creds = creds_list[current_idx]
            
            # Создаем worker для установки SIP
            from core.worker import HuaweiTE40Worker
            
            self.fix_worker = HuaweiTE40Worker(
                ip_address=ip_address,
                port=self.huawei_settings.get('port', 443),
                username=creds['username'],
                password=creds['password']
            )
            
            print(f"Worker created for {ip_address}:{self.huawei_settings.get('port', 443)}")
            
            # Подключаем сигналы
            self.fix_worker.signals.result.connect(self.on_sip_fix_result)
            self.fix_worker.signals.error.connect(self.on_sip_fix_error)
            self.fix_worker.signals.status.connect(self.on_status_update)
            self.fix_worker.signals.finished.connect(self.on_worker_finished)
            
            print("Starting worker...")
            # Запускаем установку SIP сервера
            QThreadPool.globalInstance().start(self.fix_worker)
            self.fix_worker.set_sip_server(sip_server)
            print("Worker started")
            
        except Exception as e:
            print(f"Error in fix_sip_huawei_te40: {e}")
            import traceback
            traceback.print_exc()
            self.hide_progress_dialog()
            QMessageBox.critical(self, "Ошибка", f"Не удалось установить SIP сервер: {str(e)}")
    
    
    
        def fix_sip_huawei_bar310(self, ip_address: str):
            """Исправление SIP регистрации для CloudLink Bar 310"""
            print(f"Исправление SIP регистрации для Bar 310 на {ip_address}")
            self.show_progress_dialog("Исправление SIP регистрации...")
            
            # TODO: Реализовать для Bar 310
            import time
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self.on_fix_complete(True, "SIP регистрация успешно исправлена"))
    
    def fix_sip_huawei_te20(self, ip_address: str):
        """Исправление SIP регистрации для Huawei TE20"""
        print(f"Исправление SIP регистрации для TE-20 на {ip_address}")
        self.show_progress_dialog("Исправление SIP регистрации...")
        
        # TODO: Реализовать для TE-20
        import time
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self.on_fix_complete(True, "SIP регистрация успешно исправлена"))
    
    def fix_sip_polycom_rpg310(self, ip_address: str):
        """Исправление SIP регистрации для Polycom RPG 310"""
        print(f"Исправление SIP регистрации для Polycom RPG 310 на {ip_address}")
        self.show_progress_dialog("Исправление SIP регистрации...")
        
        # TODO: Реализовать для Polycom
        import time
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self.on_fix_complete(True, "SIP регистрация успешно исправлена"))
    
    def on_fix_complete(self, success: bool, message: str):
        """Обработчик завершения исправления SIP"""
        self.hide_progress_dialog()
        
        if success:
            QMessageBox.information(self, "Успех", message)
            # После успешного исправления обновляем данные
            self.refresh_data()
        else:
            QMessageBox.critical(self, "Ошибка", message)    
            
            
    @pyqtSlot(dict)
    def on_sip_fix_result(self, result):
        """Обработка результата установки SIP сервера."""
        self.hide_progress_dialog()
        self._set_sip_fix_busy(False)

        if result.get('action') == 'set_sip_server':
            if result.get('success'):
                self.set_ui_state(UIState.CONNECTED, "Команда SIP выполнена")
                QMessageBox.information(
                    self,
                    "Успех",
                    result.get('message', 'SIP сервер успешно установлен')
                )
                self.refresh_data()
            else:
                self.set_ui_state(
                    UIState.REQUEST_ERROR,
                    result.get('message', 'Не удалось установить SIP сервер'),
                )
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    result.get('message', 'Не удалось установить SIP сервер')
                )

    @pyqtSlot(tuple)
    def on_sip_fix_error(self, error_info):
        """Обработка ошибки установки SIP сервера."""
        self.hide_progress_dialog()
        self._set_sip_fix_busy(False)
        error_type, error, traceback_text = error_info
        self.set_ui_state(UIState.REQUEST_ERROR, f"Ошибка команды SIP: {error}")

        QMessageBox.critical(
            self,
            "Ошибка",
            f"Не удалось установить SIP сервер:\n{str(error)}"
        )

    def on_fix_sip_registration(self, ip_address: str, device_name: str):
        """Обработчик нажатия кнопки 'Исправить' для SIP регистрации."""
        print(f"=== Нажата кнопка Исправить для {device_name} ({ip_address}) ===")

        sip_server = "link.ru"
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы действительно хотите установить SIP сервер\n"
            f"{sip_server}\n\n"
            f"на устройстве {device_name}?\nIP: {ip_address}\n\n"
            f"Это действие может занять несколько секунд.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        if device_name == "Huawei TE40":
            self.fix_sip_huawei_te40(ip_address)
        elif device_name == "CloudLink Bar 310":
            self.fix_sip_huawei_bar310(ip_address)
        elif device_name == "Huawei TE20":
            QMessageBox.information(self, "Информация", "Поддержка TE-20 будет добавлена позже")
        elif device_name == "Polycom RPG 310":
            self.fix_sip_polycom_rpg310(ip_address)
        else:
            QMessageBox.information(
                self,
                "Информация",
                f"Исправление SIP регистрации для {device_name} будет добавлено позже"
            )

    def _get_sip_fix_connection_params(self, device_name: str, ip_address: str):
        """Подготовить параметры подключения для SIP fix."""
        if device_name == "Huawei TE40":
            port = self.huawei_settings.get('port', 443)
        elif device_name == "CloudLink Bar 310":
            port = self.huawei_settings.get('port', 443)
        elif device_name == "Polycom RPG 310":
            port = 22
        else:
            raise ValueError(f"SIP fix не поддерживается для {device_name}")

        creds_list = self.device_credentials.get(device_name, [])
        current_idx = self.get_current_credential_index(device_name, ip_address)
        if creds_list and 0 <= current_idx < len(creds_list):
            creds = creds_list[current_idx]
        elif creds_list:
            current_idx = 0
            creds = creds_list[0]
        else:
            raise CredentialConfigurationError(
                "Credentials are required before setting a SIP server."
            )

        return port, current_idx, creds

    def _start_sip_fix(self, device_name: str, ip_address: str):
        """Запустить установку SIP сервера в фоновом потоке."""
        sip_server = "link.ru"
        port, current_idx, creds = self._get_sip_fix_connection_params(device_name, ip_address)

        self.set_ui_state(UIState.COMMAND, "Установка SIP-сервера…")
        self._set_sip_fix_busy(True)
        self.show_progress_dialog(f"Установка SIP сервера {sip_server}...")
        self.show_codec_poll_terminal(device_name, ip_address, current_idx + 1, 1, reset=True)

        self.fix_worker = CodecSipFixWorker(
            device_name=device_name,
            ip_address=ip_address,
            port=port,
            username=creds['username'],
            password=creds['password'],
            sip_server=sip_server,
        )
        self.fix_worker.signals.result.connect(self.on_sip_fix_result)
        self.fix_worker.signals.error.connect(self.on_sip_fix_error)
        self.fix_worker.signals.status.connect(self.on_status_update)
        self.fix_worker.signals.terminal_log.connect(self.on_codec_poll_terminal_log)
        self.fix_worker.signals.finished.connect(self.on_worker_finished)
        QThreadPool.globalInstance().start(self.fix_worker)

    def _set_sip_fix_busy(self, busy: bool):
        codec_screen = self.screens.get("codec") if hasattr(self, "screens") else None
        for entry in getattr(codec_screen, "sip_fix_buttons", []):
            button = entry[1] if isinstance(entry, tuple) else entry
            if hasattr(button, "set_loading"):
                button.set_loading(busy, "Выполнение…")
            else:
                button.setEnabled(not busy)

    def fix_sip_huawei_te40(self, ip_address: str):
        """Исправление SIP регистрации для Huawei TE40."""
        creds = {}
        try:
            _port, _current_idx, creds = self._get_sip_fix_connection_params(
                "Huawei TE40", ip_address
            )
            self._start_sip_fix("Huawei TE40", ip_address)
        except Exception as error:
            secrets = (creds.get("username"), creds.get("password"))
            safe_error = redact_exception(error, secrets)
            safe_traceback = redact_text(traceback.format_exc(), secrets)
            print(f"SIP fix failed: {safe_error}")
            print(safe_traceback)
            self.hide_progress_dialog()
            self._set_sip_fix_busy(False)
            QMessageBox.critical(
                self,
                "Ошибка",
                "Не удалось установить SIP сервер. Проверьте настройки подключения.",
            )

    def fix_sip_huawei_bar310(self, ip_address: str):
        """Исправление SIP регистрации для CloudLink Bar 310."""
        self._start_sip_fix("CloudLink Bar 310", ip_address)

    def fix_sip_polycom_rpg310(self, ip_address: str):
        """Исправление SIP регистрации для Polycom RPG 310."""
        self._start_sip_fix("Polycom RPG 310", ip_address)

    def show_progress_dialog(self, message: str):
        """Показать диалог прогресса"""
        from PyQt5.QtWidgets import QProgressDialog

        if getattr(self, 'suppress_progress_dialog_once', False):
            self.suppress_progress_dialog_once = False
            return
        
        self.progress_dialog = QProgressDialog(message, "Отмена", 0, 100, self)
        self.progress_dialog.setWindowTitle("Выполнение операции")
        self.progress_dialog.setWindowModality(Qt.NonModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.setValue(0)
        self.progress_dialog.setCancelButton(None)  # Отключаем кнопку отмены пока
        self.progress_dialog.show()
        self.progress_dialog.raise_()
        self.progress_dialog.activateWindow()
    
    def hide_progress_dialog(self):
        """Скрыть диалог прогресса"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None         

    def show_matrix_terminal(self, ip_address: str, attempt_no: int, total_attempts: int, reset: bool = True):
        if not hasattr(self, 'matrix_terminal_dialog') or self.matrix_terminal_dialog is None:
            self.matrix_terminal_dialog = MatrixTerminalDialog(self.colors, self)

        title = f"Терминал Extron IN1804 - {ip_address}"
        if reset:
            self.matrix_terminal_dialog.reset_session(title)
            self.matrix_terminal_dialog.append_line(f"[session] start {ip_address}")
        else:
            self.matrix_terminal_dialog.setWindowTitle(title)
        self.matrix_terminal_dialog.append_line(f"[session] attempt {attempt_no}/{total_attempts}")

    @pyqtSlot(str)
    def on_terminal_log(self, message: str):
        if hasattr(self, 'matrix_terminal_dialog') and self.matrix_terminal_dialog:
            self.matrix_terminal_dialog.append_line(message)

    def finish_matrix_terminal(self, message: str):
        if hasattr(self, 'matrix_terminal_dialog') and self.matrix_terminal_dialog:
            self.matrix_terminal_dialog.append_line(f"[session] {message}")

    def show_te20_terminal(self, ip_address: str, attempt_no: int, total_attempts: int, reset: bool = True):
        if not hasattr(self, 'te20_terminal_dialog') or self.te20_terminal_dialog is None:
            self.te20_terminal_dialog = MatrixTerminalDialog(self.colors, self)

        title = f"Терминал Huawei TE20 - {ip_address}"
        if reset:
            self.te20_terminal_dialog.reset_session(title)
            self.te20_terminal_dialog.append_line(f"[session] start {ip_address}")
        else:
            self.te20_terminal_dialog.setWindowTitle(title)
        self.te20_terminal_dialog.append_line(f"[session] attempt {attempt_no}/{total_attempts}")

    @pyqtSlot(str)
    def on_te20_terminal_log(self, message: str):
        if hasattr(self, 'te20_terminal_dialog') and self.te20_terminal_dialog:
            self.te20_terminal_dialog.append_line(message)

    def finish_te20_terminal(self, message: str):
        if hasattr(self, 'te20_terminal_dialog') and self.te20_terminal_dialog:
            self.te20_terminal_dialog.append_line(f"[session] {message}")

    def show_codec_poll_terminal(self, device_name: str, ip_address: str, attempt_no: int, total_attempts: int, reset: bool = True):
        if not hasattr(self, 'codec_terminal_dialog') or self.codec_terminal_dialog is None:
            self.codec_terminal_dialog = MatrixTerminalDialog(self.colors, self)

        title = f"Терминал {device_name} - {ip_address}"
        if reset:
            self.codec_terminal_dialog.reset_session(title)
            self.codec_terminal_dialog.append_line(f"[session] start {ip_address}")
        else:
            self.codec_terminal_dialog.setWindowTitle(title)
        self.codec_terminal_dialog.append_line(f"[session] attempt {attempt_no}/{total_attempts}")

    @pyqtSlot(str)
    def on_codec_poll_terminal_log(self, message: str):
        if hasattr(self, 'codec_terminal_dialog') and self.codec_terminal_dialog:
            self.codec_terminal_dialog.append_line(message)

    def show_codec_terminal(self, device_name: str, ip_address: str, action: str, reset: bool = True):
        if not hasattr(self, 'codec_terminal_dialog') or self.codec_terminal_dialog is None:
            self.codec_terminal_dialog = MatrixTerminalDialog(self.colors, self)

        title = f"Терминал управления презентацией - {device_name} - {ip_address}"
        if reset:
            self.codec_terminal_dialog.reset_session(title)
            self.codec_terminal_dialog.append_line(f"[session] start {ip_address}")
            self.codec_terminal_dialog.append_line(f"[session] action presentation {action}")
        else:
            self.codec_terminal_dialog.setWindowTitle(title)

    def append_codec_terminal_line(self, message: str):
        if hasattr(self, 'codec_terminal_dialog') and self.codec_terminal_dialog:
            self.codec_terminal_dialog.append_line(message)

    def finish_codec_terminal(self, message: str):
        if hasattr(self, 'codec_terminal_dialog') and self.codec_terminal_dialog:
            self.codec_terminal_dialog.append_line(f"[session] {message}")

    def show_debug_window(self):
        device_name = self.device_combo.currentText()
        ip_address = self.ip_entry.text().strip()

        if device_name == "Huawei TE20":
            if not hasattr(self, 'te20_terminal_dialog') or self.te20_terminal_dialog is None:
                self.te20_terminal_dialog = MatrixTerminalDialog(self.colors, self)
                self.te20_terminal_dialog.setWindowTitle(f"Терминал Huawei TE20 - {ip_address}")
            dialog = self.te20_terminal_dialog
        elif device_name == "Extron IN1804":
            if not hasattr(self, 'matrix_terminal_dialog') or self.matrix_terminal_dialog is None:
                self.matrix_terminal_dialog = MatrixTerminalDialog(self.colors, self)
                self.matrix_terminal_dialog.setWindowTitle(f"Терминал Extron IN1804 - {ip_address}")
            dialog = self.matrix_terminal_dialog
        else:
            if not hasattr(self, 'codec_terminal_dialog') or self.codec_terminal_dialog is None:
                self.codec_terminal_dialog = MatrixTerminalDialog(self.colors, self)
                self.codec_terminal_dialog.setWindowTitle(
                    f"Терминал управления устройством - {device_name} - {ip_address}"
                )
            dialog = self.codec_terminal_dialog

        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def closeEvent(self, event):
        codec_screen = self.screens.get("codec") if hasattr(self, "screens") else None
        if codec_screen and hasattr(codec_screen, "reset_volume_session"):
            codec_screen.reset_volume_session()
        self.disconnect_matrix_persistent_handler()
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        super().closeEvent(event)
            

