from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox, QStackedWidget, QMessageBox, QInputDialog, QDialog, QDialogButtonBox, QFormLayout, QPlainTextEdit

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QThreadPool, QDateTime, QEvent
from PyQt5.QtGui import QPalette, QColor
import datetime
import random

from .screens import CodecScreen, MatrixScreen, PDUScreen
from core.worker import HuaweiTE40Worker, HuaweiBar310Worker, HuaweiTE20Worker, PolycomRPG310Worker, CodecSipFixWorker
from core.exceptions import AuthenticationError, ConnectionError
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
        self.resize(820, 420)

        layout = QVBoxLayout(self)
        self.output = QPlainTextEdit(self)
        self.output.setReadOnly(True)
        self.output.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: #0F1115;
                color: #D7FBE8;
                border: 1px solid {self.colors['divider']};
                border-radius: 6px;
                padding: 8px;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 10pt;
            }}
        """)
        layout.addWidget(self.output)

    def reset_session(self, title: str):
        self.setWindowTitle(title)
        self.output.clear()

    def append_line(self, text: str):
        self.output.appendPlainText(text)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

class VCSDiagnosticApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Цветовая схема
        self.colors = {
            'background': '#121212',
            'surface': '#1E1E1E',
            'primary': '#BB86FC',
            'primary_variant': '#3700B3',
            'secondary': '#03DAC6',
            'error': '#CF6679',
            'text_primary': '#FFFFFF',
            'text_secondary': '#B3B3B3',
            'divider': '#2D2D2D'
        }
        
        # Имитация данных
        self.codec_data = {
            "Codec1": self.generate_fake_data("Codec1"),
            "Codec2": self.generate_fake_data("Codec2"),
            "Codec3": self.generate_fake_data("Codec3"),
            "Codec4": self.generate_fake_data("Codec4")
        }
        
        # Маппинг устройств к экранам
        self.device_to_screen = {
            "Huawei TE-20": "codec",
            "Huawei TE-40": "codec", 
            "CloudLink Bar 310": "codec",  # Добавлено новое устройство
            #"CloudLink Box 300": "codec",
            "Polycom RPG 310": "codec",
            "Extron IN1804": "matrix",
            "Aten PE8208AV": "pdu"
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
            'username': 'api',
            'password': '***REMOVED_CREDENTIAL***',
            'use_ssl': True,
            'verify_ssl': False
        }        
        
        # Список credentials для разных устройств
        self.device_credentials = {
            "Huawei TE-40": [
                {'username': 'api', 'password': '***REMOVED_CREDENTIAL***'},        # По умолчанию
                {'username': 'debug', 'password': '***REMOVED_CREDENTIAL***'},          # Альтернатива 1
            ],
            "CloudLink Bar 310": [                          # Добавлено для Bar 310
                {'username': 'api', 'password': '***REMOVED_CREDENTIAL***'},        # По умолчанию
                {'username': 'debug', 'password': '***REMOVED_CREDENTIAL***'},          # Альтернатива 1
                {'username': 'user', 'password': '***REMOVED_CREDENTIAL***'},      # Альтернатива 2
            ],
            "Huawei TE-20": [
                {'username': 'api', 'password': '***REMOVED_CREDENTIAL***'},
                {'username': 'debug', 'password': '***REMOVED_CREDENTIAL***'},
                {'username': 'api', 'password': 'p@ss123456'}               
            ],
            "CloudLink Box 300": [
                {'username': 'admin', 'password': ''},
                {'username': 'api', 'password': 'api'},
            ],
            "Polycom RPG 310": [
                {'username': 'admin', 'password': '***REMOVED_CREDENTIAL***'},
                {'username': 'polycom', 'password': 'polycom'},
            ],
            "Extron IN1804": [
                {'username': 'admin', 'password': 'NbCfD26xm'},     
                {'username': 'admin', 'password': 'Hi-Tech!1'},
                {'username': 'extron', 'password': 'extron'},
            ],      
            "Aten PE8208AV": [
                {'username': 'administrator', 'password': 'w8O0MbQQA1J.'},
                {'username': 'administrator', 'password': 'ZadF123@Hhr6'},
                {'username': 'administrator', 'password': 'Polymedia10@'},
                {'username': 'administrator', 'password': 'A1b2@c3D4_e5'},
                {'username': 'administrator', 'password': 'I5FM95S.T0aI'},
                {'username': 'administrator', 'password': '5'},
                {'username': 'administrator', 'password': '6'},
                {'username': 'administrator', 'password': '7'},
                {'username': 'administrator', 'password': '8'},
                {'username': 'administrator', 'password': '9'},
                {'username': 'administrator', 'password': '0'},
                {'username': 'admin', 'password': ''},
                {'username': 'admin', 'password': 'admin'},
                {'username': 'administrator', 'password': 'administrator'},
            ],            
        }
        
        # Текущий индекс credentials для каждого устройства
        self.current_credential_index = {}
        for device in self.device_credentials:
            self.current_credential_index[device] = 0
        self.device_connection_profiles = {}
        
        
        self.progress_dialog = None
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
        self.update_timer = QTimer()
        self.last_update_time = None
        
        self.init_ui()
    
    def init_ui(self, params=None):
        """Инициализация интерфейса"""
        self.setWindowTitle("Диагностический модуль ММК")
        self.setGeometry(100, 100, 950, 950)
        
        # Установка темной темы
        self.set_dark_theme()
        
        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной вертикальный layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 1. Панель выбора устройства и подключения
        top_panel = self.create_top_panel()
        main_layout.addWidget(top_panel)
        
        # 2. Создаем контейнер для экранов
        self.screen_container = QStackedWidget()
        
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
        
        # По умолчанию показываем первый кодек
        self.device_combo.setCurrentIndex(0)
        
        # Сохраняем текущий выбранный тип экрана
        self.current_screen_type = None
    
    def create_placeholder_widget(self):
        """Создание виджета-заглушки с надписью Обновите данные"""
        placeholder = QWidget()
        placeholder.setStyleSheet(f"""
            QWidget {{
                background-color: {self.colors['surface']};
                border-radius: 8px;
            }}
        """)
        
        layout = QVBoxLayout(placeholder)
        layout.setAlignment(Qt.AlignCenter)
        
        # Создаем метку с надписью
        label = QLabel("Обновите данные")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"""
            QLabel {{
                color: {self.colors['text_secondary']};
                font-size: 18pt;
                font-weight: bold;
                background-color: transparent;
                padding: 50px;
            }}
        """)
        
        # Добавляем иконку или дополнительный текст
        hint_label = QLabel("Нажмите кнопку «Обновить данные» для получения информации об оборудовании")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet(f"""
            QLabel {{
                color: {self.colors['text_secondary']};
                font-size: 10pt;
                background-color: transparent;
                padding: 10px;
            }}
        """)
        
        layout.addWidget(label)
        layout.addWidget(hint_label)
        
        return placeholder

    def create_top_panel(self):
        """Создание верхней панели с выпадающим списком и IP-адресом"""
        group_box = QGroupBox()
        group_box.setStyleSheet(f"""
            QGroupBox {{
                border: none;
                margin-top: 5px;
                padding-top: 5px;
                background-color: {self.colors['surface']};
            }}
            QGroupBox::title {{
                height: 0px;
                padding: 0px;
                margin: 0px;
            }}
        """)
        
        layout = QHBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 15, 20, 15)
        
        # Выпадающий список устройств
        self.device_combo = QComboBox()
        
        # Список заголовков
        headers = ["Кодеки ВКС", "Коммутационное оборудование", "Управление питанием"]
        
        # Список устройств с категориями
        devices = [
            "Кодеки ВКС",
            "Huawei TE-20", 
            "Huawei TE-40", 
            "CloudLink Bar 310",
            #"CloudLink Box 300", 
            "Polycom RPG 310",
            "Коммутационное оборудование",
            "Extron IN1804",
            "Управление питанием",
            "Aten PE8208AV"
        ]
        
        # Цвет для заголовков (спокойный зеленый)
        header_color = "#4CAF50"
        
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
                self.device_combo.model().item(index).setForeground(QColor(header_color))
        
        # Устанавливаем делегат для выравнивания заголовков по правому краю
        delegate = RightAlignHeaderDelegate(self.device_combo, headers)
        self.device_combo.setItemDelegate(delegate)
        
        self.device_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['divider']};
                border-radius: 4px;
                padding: 12px;
                font-size: 11pt;
                min-height: 25px;
                min-width: 250px;
            }}
            QComboBox:hover {{
                border: 1px solid {self.colors['primary']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {self.colors['text_primary']};
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
                selection-background-color: {self.colors['primary']};
                selection-color: black;
                border: 1px solid {self.colors['divider']};
                outline: none;
            }}
            /* Стиль для обычных элементов */
            QComboBox QAbstractItemView::item {{
                padding: 8px 12px;
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
            }}
            /* Стиль для выбранного элемента */
            QComboBox QAbstractItemView::item:selected {{
                background-color: {self.colors['primary']};
                color: black;
            }}
            /* Стиль для неактивных элементов (заголовков категорий) */
            QComboBox QAbstractItemView::item:!enabled {{
                color: {header_color};
                background-color: {self.colors['surface']};
                font-weight: bold;
                font-size: 10pt;
                padding: 10px 12px 6px 12px;
                border-top: 1px solid {self.colors['divider']};
                border-bottom: none;
                margin-top: 6px;
            }}
            /* Убираем верхнюю границу у первого заголовка */
            QComboBox QAbstractItemView::item:!enabled:first {{
                border-top: none;
                margin-top: 0px;
            }}
            /* Стиль для заголовков при наведении */
            QComboBox QAbstractItemView::item:!enabled:hover {{
                background-color: {self.colors['surface']};
                color: {header_color};
            }}
        """)
        
        self.device_combo.currentTextChanged.connect(self.on_device_change)
        self.device_combo.installEventFilter(self)
        
        # Метка и поле для IP-адреса
        ip_label = QLabel("IP адрес:")
        ip_label.setStyleSheet(f"color: {self.colors['text_primary']}; font-size: 11pt; font-weight: bold;")
        ip_label.setFixedWidth(80)
        
        self.ip_entry = QLineEdit()
        self.ip_entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['divider']};
                border-radius: 4px;
                padding: 12px;
                font-size: 11pt;
                min-height: 25px;
                min-width: 200px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.colors['primary']};
            }}
        """)
        self.ip_entry.setText("192.168.1.100")
        self.ip_entry.returnPressed.connect(self.trigger_refresh_from_input)
        
        # Кнопка для ввода пароля
        self.password_btn = QPushButton("Пароль")
        self.password_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['background']};
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['divider']};
                border-radius: 4px;
                padding: 12px 20px;
                font-weight: bold;
                font-size: 11pt;
                min-height: 25px;
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
        self.password_btn.clicked.connect(self.show_password_dialog)
        
        # Кнопка обновления данных
        self.refresh_btn = QPushButton("Обновить данные")
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #026c64;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 14px 30px;
                font-weight: bold;
                font-size: 11pt;
                min-height: 25px;
            }}
            QPushButton:hover {{
                background-color: #02786f;
            }}
            QPushButton:pressed {{
                background-color: #025c56;
            }}
        """)
        self.refresh_btn.clicked.connect(self.refresh_data)

        self.debug_btn = QPushButton("Отладка")
        self.debug_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['background']};
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['divider']};
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 8pt;
                min-height: 25px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['background']};
                border: 1px solid {self.colors['primary']};
            }}
            QPushButton:pressed {{
                background-color: {self.colors['divider']};
            }}
        """)
        self.debug_btn.clicked.connect(self.show_debug_window)
        
        layout.addWidget(self.device_combo)
        layout.addWidget(ip_label)
        layout.addWidget(self.ip_entry)
        layout.addWidget(self.password_btn)
        layout.addWidget(self.refresh_btn)
        layout.addWidget(self.debug_btn)
        layout.addStretch()
        
        group_box.setLayout(layout)
        return group_box
    def set_dark_theme(self):
        """Установка темной темы"""
        # Устанавливаем палитру для всего приложения
        palette = QPalette()
        
        palette.setColor(QPalette.Window, QColor(self.colors['background']))
        palette.setColor(QPalette.WindowText, QColor(self.colors['text_primary']))
        palette.setColor(QPalette.Base, QColor(self.colors['surface']))
        palette.setColor(QPalette.AlternateBase, QColor(self.colors['background']))
        palette.setColor(QPalette.ToolTipBase, QColor(self.colors['surface']))
        palette.setColor(QPalette.ToolTipText, QColor(self.colors['text_primary']))
        palette.setColor(QPalette.Text, QColor(self.colors['text_primary']))
        palette.setColor(QPalette.Button, QColor(self.colors['surface']))
        palette.setColor(QPalette.ButtonText, QColor(self.colors['text_primary']))
        palette.setColor(QPalette.BrightText, Qt.white)
        palette.setColor(QPalette.Highlight, QColor(self.colors['primary']))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        
        self.setPalette(palette)
        
        # Дополнительные стили для всех виджетов
        self.setStyleSheet(f"""
            /* Основной фон главного окна */
            QMainWindow {{
                background-color: {self.colors['background']};
            }}
            
            /* Фон для центрального виджета */
            QWidget#centralWidget {{
                background-color: {self.colors['background']};
            }}
            
            /* Стили для всех QWidget (но осторожно, это может повлиять на все) */
            QWidget {{
                background-color: {self.colors['background']};
                color: {self.colors['text_primary']};
            }}
            
            /* Но оставляем кнопки и поля ввода с их цветами */
            QPushButton, QLineEdit, QComboBox, QGroupBox {{
                background-color: {self.colors['surface']};
            }}
            
            /* Стили для скроллбаров */
            QScrollBar:vertical {{
                background-color: {self.colors['surface']};
                width: 14px;
                border-radius: 7px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {self.colors['divider']};
                min-height: 20px;
                border-radius: 7px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: {self.lighten_color(self.colors['divider'], 20)};
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
            
            QScrollBar:horizontal {{
                background-color: {self.colors['surface']};
                height: 14px;
                border-radius: 7px;
            }}
            
            QScrollBar::handle:horizontal {{
                background-color: {self.colors['divider']};
                min-width: 20px;
                border-radius: 7px;
            }}
            
            QScrollBar::handle:horizontal:hover {{
                background-color: {self.lighten_color(self.colors['divider'], 20)};
            }}
            
            /* Стили для меню */
            QMenuBar {{
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
                border-bottom: 1px solid {self.colors['divider']};
            }}
            
            QMenuBar::item:selected {{
                background-color: {self.colors['primary']};
                color: black;
            }}
            
            QMenu {{
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['divider']};
            }}
            
            QMenu::item:selected {{
                background-color: {self.colors['primary']};
                color: black;
            }}
            
            /* Стили для статусбара */
            QStatusBar {{
                background-color: {self.colors['surface']};
                color: {self.colors['text_secondary']};
                border-top: 1px solid {self.colors['divider']};
            }}
            
            /* Стили для табов, если они есть */
            QTabWidget::pane {{
                border: 1px solid {self.colors['divider']};
                background-color: {self.colors['background']};
            }}
            
            QTabBar::tab {{
                background-color: {self.colors['surface']};
                color: {self.colors['text_secondary']};
                padding: 8px 16px;
                border: 1px solid {self.colors['divider']};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            
            QTabBar::tab:selected {{
                background-color: {self.colors['background']};
                color: {self.colors['primary']};
                border-bottom: 2px solid {self.colors['primary']};
            }}
            
            QTabBar::tab:hover {{
                background-color: {self.lighten_color(self.colors['surface'], 10)};
            }}
            
            /* Стили для групбоксов, которые могут быть проблемными */
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {self.colors['divider']};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: {self.colors['surface']};
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {self.colors['text_primary']};
            }}
        """)



    def init_screens(self):
        """Инициализация всех экранов"""
        self.screens = {
            "codec": CodecScreen(self),
            "matrix": MatrixScreen(self),
            "pdu": PDUScreen(self)
        }
    
    def create_update_time_panel(self):
        """Создание панели времени обновления"""
        panel = QWidget()
        panel.setAutoFillBackground(True)
        palette = panel.palette()
        palette.setColor(panel.backgroundRole(), QColor(self.colors['background']))
        panel.setPalette(palette)
        
        layout = QHBoxLayout(panel)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 5, 20, 5)
        
        time_label = QLabel("Предыдущее обновление данных:")
        time_label.setAutoFillBackground(False)
        palette = time_label.palette()
        palette.setColor(time_label.foregroundRole(), Qt.white)
        time_label.setPalette(palette)
        time_label.setStyleSheet("font-size: 8pt;")
        
        self.time_display = QLabel("Никогда")
        self.time_display.setAutoFillBackground(False)
        palette = self.time_display.palette()
        palette.setColor(self.time_display.foregroundRole(), Qt.white)
        self.time_display.setPalette(palette)
        self.time_display.setStyleSheet("font-size: 8pt; padding: 4px; min-width: 10px;")
        self.time_display.setAlignment(Qt.AlignLeft)
        
        layout.addStretch(0)
        layout.addWidget(time_label)
        layout.addWidget(self.time_display)
        layout.addStretch(0)
        
        return panel
    
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
        
        # Сохраняем тип экрана, который должен отображаться после обновления
        self.current_screen_type = screen_type
        
        # Показываем заглушку вместо экрана
        self.screen_container.setCurrentWidget(self.placeholder_widget)
        
        # Обновляем IP адрес
        
        # Обновляем заголовок окна
        self.setWindowTitle(f"Диагностический модуль ММК - {device_name}")

    def eventFilter(self, obj, event):
        """Запускать обновление по Enter на списке устройств."""
        if obj is getattr(self, 'device_combo', None) and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.trigger_refresh_from_input()
                return True
        return super().eventFilter(obj, event)

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
            "Huawei TE-20": "192.168.1.100",
            "Huawei TE-40": "192.168.1.101",
            "CloudLink Bar 310": "192.168.1.104",  # Добавлено новое устройство
            "CloudLink Box 300": "192.168.1.102",
            "Polycom RPG 310": "192.168.1.103",
            "Extron IN1804": "192.168.1.200"
        }
        
        self.ip_entry.setText(ip_mapping.get(device_name, "192.168.1.100"))
    
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

    def refresh_data(self):
        """Обновление данных в зависимости от устройства"""
        ip_address = self.ip_entry.text().strip()
        device_name = self.device_combo.currentText()
        
        if not ip_address:
            QMessageBox.warning(self, "Внимание", "Введите IP-адрес устройства")
            return
        
        if not self.validate_ip_address(ip_address):
            QMessageBox.warning(self, "Внимание", "Неверный формат IP-адреса")
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
        else:
            target_screen = self.screens["codec"]
        
        # Показываем экран
        self.screen_container.setCurrentWidget(target_screen)
        
        # Если есть метод очистки данных у экрана, вызываем его
        if hasattr(target_screen, 'clear_data'):
            target_screen.clear_data()
        elif hasattr(target_screen, 'update_data'):
            # Если нет clear_data, показываем индикатор загрузки через update_data
            target_screen.update_data({"status": "loading", "message": "Загрузка данных..."})
        
        # Вызываем соответствующий метод обновления
        if device_name == "Aten PE8208AV":
            self.refresh_aten_pdu(ip_address)
        elif device_name == "Huawei TE-40":
            self.refresh_huawei_te40(ip_address)
        elif device_name == "CloudLink Bar 310":  
            self.refresh_huawei_bar310(ip_address)
        elif device_name == "Huawei TE-20":
            self.refresh_huawei_te20(ip_address)
        elif device_name == "Polycom RPG 310":
            self.refresh_polycom_rpg310(ip_address)
        elif device_name == "Extron IN1804":
            self.refresh_extron_in1804(ip_address)            
        elif device_type == "matrix":
            self.refresh_matrix_data(ip_address)
        else:
            QMessageBox.information(
                self,
                "Информация",
                f"Поддержка {device_name} будет добавлена позже"
            )


    def refresh_huawei_bar310(self, ip_address: str):
        """Обновление данных Huawei CloudLink Bar 310 с перебором credentials"""
        print(f"=== Начинаю обновление Huawei CloudLink Bar 310 для {ip_address} ===")
        
        if not self.validate_ip_address(ip_address):
            QMessageBox.warning(self, "Неверный IP адрес", "Введите корректный IP адрес.")
            return
        
        # Получаем список credentials для Bar 310
        device_name = self.device_combo.currentText()
        creds_list = self.device_credentials.get(device_name, [
            {'username': 'api', 'password': '***REMOVED_CREDENTIAL***'},
            {'username': 'debug', 'password': '***REMOVED_CREDENTIAL***'},
            {'username': 'api', 'password': 'Change_Me'}
        ])
        
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
            self.current_worker.signals.result.connect(self.on_device_data_received)
            self.current_worker.signals.error.connect(self.on_device_error)
            self.current_worker.signals.progress.connect(self.on_progress_update)
            self.current_worker.signals.status.connect(self.on_status_update)
            self.current_worker.signals.terminal_log.connect(self.on_codec_poll_terminal_log)
            self.current_worker.signals.finished.connect(self.on_worker_finished)
            
            # Запускаем
            QThreadPool.globalInstance().start(self.current_worker)
            print("Worker для Huawei CloudLink Bar 310 запущен")
            
        except Exception as e:
            print(f"Ошибка создания Worker: {e}")
            self.hide_progress_dialog()
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать Worker: {str(e)}")
            
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText("Обновить данные")

    def refresh_huawei_te20(self, ip_address: str):
        """Обновление данных Huawei TE-20 с перебором credentials"""
        print(f"=== Начинаю обновление TE-20 для {ip_address} ===")
        
        if not self.validate_ip_address(ip_address):
            QMessageBox.warning(self, "Неверный IP адрес", "Введите корректный IP адрес.")
            return
        
        # Получаем список credentials для TE-20
        device_name = self.device_combo.currentText()
        creds_list = self.device_credentials.get(device_name, [{'username': 'api', 'password': '***REMOVED_CREDENTIAL***'}])

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
            self.current_worker.signals.result.connect(self.on_device_data_received)
            self.current_worker.signals.error.connect(self.on_device_error)
            self.current_worker.signals.progress.connect(self.on_progress_update)
            self.current_worker.signals.status.connect(self.on_status_update)
            self.current_worker.signals.terminal_log.connect(self.on_te20_terminal_log)
            self.current_worker.signals.finished.connect(self.on_worker_finished)
            
            # Запускаем
            QThreadPool.globalInstance().start(self.current_worker)
            print("Worker TE-20 запущен")
            
        except Exception as e:
            print(f"Ошибка создания Worker: {e}")
            self.hide_progress_dialog()
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать Worker: {str(e)}")
            
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText("Обновить данные")

    def refresh_huawei_te40(self, ip_address: str):
        """Обновление данных Huawei TE-40 с перебором credentials"""
        print(f"=== Начинаю обновление для {ip_address} ===")
        
        if not self.validate_ip_address(ip_address):
            QMessageBox.warning(self, "Неверный IP адрес", "Введите корректный IP адрес.")
            return
        
        # Получаем список credentials для TE-40
        device_name = self.device_combo.currentText()
        creds_list = self.device_credentials.get(device_name, [{'username': 'api', 'password': ''}])
        
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
            self.current_worker.signals.result.connect(self.on_device_data_received)
            self.current_worker.signals.error.connect(self.on_device_error)
            self.current_worker.signals.progress.connect(self.on_progress_update)
            self.current_worker.signals.status.connect(self.on_status_update)
            self.current_worker.signals.terminal_log.connect(self.on_codec_poll_terminal_log)
            self.current_worker.signals.finished.connect(self.on_worker_finished)
            
            # Запускаем
            QThreadPool.globalInstance().start(self.current_worker)
            print("Worker запущен")
            
        except Exception as e:
            print(f"Ошибка создания Worker: {e}")
            self.hide_progress_dialog()
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
        creds_list = self.device_credentials.get(device_name, [
            {'username': 'admin', 'password': ''},
            {'username': 'polycom', 'password': 'polycom'},
            {'username': 'admin', 'password': 'admin'},
        ])
        
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
                port=22,  # SSH порт
                username=creds['username'],
                password=creds['password']
            )
            
            # Сохраняем информацию для повторных попыток
            self.current_worker.creds_list = creds_list
            self.current_worker.current_idx = current_idx
            self.current_worker.device_name = device_name
            
            # Подключаем сигналы
            self.current_worker.signals.result.connect(self.on_device_data_received)
            self.current_worker.signals.error.connect(self.on_device_error)
            self.current_worker.signals.progress.connect(self.on_progress_update)
            self.current_worker.signals.status.connect(self.on_status_update)
            self.current_worker.signals.terminal_log.connect(self.on_codec_poll_terminal_log)
            self.current_worker.signals.finished.connect(self.on_worker_finished)
            
            # Запускаем
            QThreadPool.globalInstance().start(self.current_worker)
            print("Worker для Polycom RPG 310 запущен")
            
        except Exception as e:
            print(f"Ошибка создания Worker: {e}")
            self.hide_progress_dialog()
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
        creds_list = self.device_credentials.get(device_name, [
            {'username': '', 'password': ''},  # Без аутентификации
            {'username': 'admin', 'password': ''},
            {'username': 'admin', 'password': 'admin'},
        ])
        
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
            self.current_worker.signals.result.connect(self.on_device_data_received)
            self.current_worker.signals.error.connect(self.on_device_error)
            self.current_worker.signals.progress.connect(self.on_progress_update)
            self.current_worker.signals.status.connect(self.on_status_update)
            self.current_worker.signals.terminal_log.connect(self.on_terminal_log)
            self.current_worker.signals.finished.connect(self.on_worker_finished)
            
            # Запускаем
            QThreadPool.globalInstance().start(self.current_worker)
            print("Worker для Extron IN1804 запущен")
            
        except Exception as e:
            print(f"Ошибка создания Worker: {e}")
            self.hide_progress_dialog()
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
        creds_list = self.device_credentials.get(device_name, [
            {'username': 'administrator', 'password': ''},
            {'username': 'administrator', 'password': '1'},
        ])
        
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
            self.current_worker.signals.result.connect(self.on_device_data_received)
            self.current_worker.signals.error.connect(self.on_device_error)
            self.current_worker.signals.progress.connect(self.on_progress_update)
            self.current_worker.signals.status.connect(self.on_status_update)
            self.current_worker.signals.finished.connect(self.on_worker_finished)
            
            # Запускаем
            QThreadPool.globalInstance().start(self.current_worker)
            print("Worker для Aten PDU запущен")
            
        except Exception as e:
            print(f"Ошибка создания Worker: {e}")
            self.hide_progress_dialog()
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
                        QMessageBox.information(
                            self,
                            "Успех",
                            f"Команда '{command}' для розетки {outlet_num} выполнена"
                        )
                        # Обновляем данные после выполнения команды
                        self.refresh_data()
                    else:
                        QMessageBox.warning(
                            self,
                            "Ошибка",
                            f"Не удалось выполнить команду '{command}' для розетки {outlet_num}"
                        )
                    
                    handler.disconnect()
                
            except Exception as e:
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


    @pyqtSlot(dict)
    def on_device_data_received(self, data):
        """Обработка полученных данных от устройства"""
        self.hide_progress_dialog()
        if self.device_combo.currentText() == "Extron IN1804":
            self.finish_matrix_terminal("Опрос завершён успешно")
        elif self.device_combo.currentText() == "Huawei TE-20":
            self.finish_te20_terminal("Опрос завершён успешно")

        meaningful_keys = [
            key for key, value in data.items()
            if key != 'ip_address' and value not in (None, '', {}, [], 'N/A', 'Не доступно')
        ]
        if not meaningful_keys:
            QMessageBox.warning(
                self,
                "Нет данных",
                "Устройство ответило, но полезные данные для отображения не получены.\n"
                "Проверьте API/протокол подключения для выбранной модели."
            )
            return
        
        # Сбрасываем индекс на успешный credentials для этого устройства
        if hasattr(self, 'current_worker') and self.current_worker:
            device_name = getattr(self.current_worker, 'device_name', None)
            current_idx = getattr(self.current_worker, 'current_idx', 0)
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
                    creds_list = getattr(self.current_worker, 'creds_list', [])
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
        if hasattr(self, 'current_screen_type'):
            if self.current_screen_type == "codec":
                current_screen = self.screens["codec"]
            elif self.current_screen_type == "matrix":
                current_screen = self.screens["matrix"]
            elif self.current_screen_type == "pdu":
                current_screen = self.screens["pdu"]
            else:
                current_screen = self.screens["codec"]
            
            if current_screen:
                current_screen.update_data(data)
        
        from PyQt5.QtCore import QDateTime
        self.last_update_time = QDateTime.currentDateTime()
        self.update_time_display()
        
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

   
    @pyqtSlot(tuple)
    def on_device_error(self, error_info):
        """Обработка ошибок от устройства с автоматическим перебором credentials"""
        error_type, error, traceback_text = error_info
        if hasattr(self, 'current_worker') and getattr(self.current_worker, 'device_name', None) == "Extron IN1804":
            self.finish_matrix_terminal(f"Опрос завершён с ошибкой: {error}")
        elif hasattr(self, 'current_worker') and getattr(self.current_worker, 'device_name', None) == "Huawei TE-20":
            self.finish_te20_terminal(f"Опрос завершён с ошибкой: {error}")
        
        # Проверяем, есть ли текущий worker и нужно ли пробовать другие credentials
        if hasattr(self, 'current_worker') and self.current_worker:
            device_name = getattr(self.current_worker, 'device_name', None)
            creds_list = getattr(self.current_worker, 'creds_list', [])
            current_idx = getattr(self.current_worker, 'current_idx', 0)
            
            error_message = str(error)
            is_auth_error = (
                error_type == "authentication_error"
                or "authentication" in error_message.lower()
                or "401" in error_message
                or "403" in error_message
                or "16781315" in error_message
                or "100666780" in error_message
            )

            # Если это ошибка аутентификации и есть еще credentials для проверки
            if is_auth_error and creds_list and current_idx < len(creds_list) - 1:
                
                # Переходим к следующему credentials
                next_idx = current_idx + 1
                self.set_current_credential_index(device_name, next_idx, getattr(self.current_worker, 'ip_address', None))
                
                print(f"Ошибка аутентификации. Пробуем следующие credentials ({next_idx + 1}/{len(creds_list)})...")
                
                # Скрываем текущий прогресс диалог
                self.hide_progress_dialog()
                
                # Повторяем попытку с новыми credentials
                if device_name == "Huawei TE-40":
                    self.refresh_huawei_te40(self.current_worker.ip_address)
                elif device_name == "CloudLink Bar 310":  # Добавлено новое условие
                    self.refresh_huawei_bar310(self.current_worker.ip_address)
                elif device_name == "Huawei TE-20":
                    self.refresh_huawei_te20(self.current_worker.ip_address)
                elif device_name == "Extron IN1804":
                    self.refresh_extron_in1804(self.current_worker.ip_address)
                elif device_name == "Aten PE8208AV":  # Добавить эту ветку
                    self.refresh_aten_pdu(self.current_worker.ip_address)                    
                return
                      
        
        # Если нет других credentials или ошибка не связана с аутентификацией
        self.hide_progress_dialog()
        
        error_message = str(error)
        if "Connection refused" in error_message or "timed out" in error_message:
            user_message = "Не удалось подключиться к устройству.\nПроверьте:\n1. IP адрес\n2. Сетевое подключение\n3. Порт устройства"
        elif "authentication" in error_message.lower() or "401" in error_message:
            user_message = "Ошибка аутентификации.\nПроверьте логин и пароль в настройках.\n\nБыли проверены все доступные варианты credentials."
        elif "SSL" in error_message:
            user_message = "Ошибка SSL соединения.\nПопробуйте отключить проверку SSL сертификата."
        else:
            user_message = f"Ошибка: {error_message}"
        
        QMessageBox.critical(
            self,
            "Ошибка подключения",
            user_message
        )
        
        # Включаем кнопку обратно
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("Обновить данные")
    
    @pyqtSlot(int)
    def on_progress_update(self, progress):
        """Обработка обновления прогресса"""
        if self.progress_dialog is not None:
            try:
                self.progress_dialog.setValue(progress)
                try:
                    if progress < 100:
                        self.progress_dialog.setLabelText(f"Прогресс: {progress}%")
                except AttributeError:
                    # setLabelText уже не работает, но setValue сработал
                    pass
            except AttributeError:
                # Диалог уже закрыт
                self.progress_dialog = None                 
    
    @pyqtSlot(str)
    def on_status_update(self, status):
        """Обработка обновления статуса"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.setLabelText(status)
        print(f"Status: {status}")
    
    @pyqtSlot()
    def on_worker_finished(self):
        """Обработка завершения работы Worker"""
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self.hide_progress_dialog)
        
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
        
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
            }}
            QLabel {{
                color: {self.colors['text_primary']};
                font-size: 11pt;
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
                default_username = 'api'
                
                # Для некоторых устройств нужно использовать другие username
                if device_name == "Aten PE8208AV":
                    default_username = 'administrator'
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
                    print(f"Добавлен новый пароль для {device_name}: {password}")
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
                default_username = 'api'
                if device_name == "Aten PE8208AV":
                    default_username = 'administrator'
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
                print(f"Создана новая запись для {device_name} с паролем: {password}")
    
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
        default_username = 'api'
        if device_name == "Aten PE8208AV":
            default_username = 'administrator'
        elif device_name == "Polycom RPG 310":
            default_username = 'admin'
        elif device_name == "Extron IN1804":
            default_username = 'admin'
        return default_username

    def show_saved_passwords(self):
        """Отобразить список сохраненных паролей (для отладки)"""
        device_name = self.device_combo.currentText()
        if device_name in self.device_credentials:
            creds = self.device_credentials[device_name]
            passwords_list = "\n".join([f"{i+1}. {cred['username']}:{cred['password']}" 
                                        for i, cred in enumerate(creds)])
            QMessageBox.information(
                self,
                "Сохраненные пароли",
                f"Сохраненные пароли для {device_name}:\n\n{passwords_list}"
            )
        else:
            QMessageBox.information(
                self,
                "Сохраненные пароли",
                f"Для {device_name} нет сохраненных паролей"
            )
    
    
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
        """Исправление SIP регистрации для Huawei TE-40"""
        print(f"Исправление SIP регистрации для TE-40 на {ip_address}")
        
        # Жёстко заданный SIP сервер
        sip_server = "vcs-core-a.sber.ru"
        
        # Показываем диалог прогресса
        self.show_progress_dialog(f"Установка SIP сервера {sip_server}...")
        
        try:
            # Получаем текущие credentials
            device_name = "Huawei TE-40"
            creds_list = self.device_credentials.get(device_name, [])
            current_idx = self.current_credential_index.get(device_name, 0)
            creds = creds_list[current_idx] if creds_list else {'username': 'api', 'password': ''}
            
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
        sip_server = "vcs-core-a.sber.ru"
        
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
            if device_name == "Huawei TE-40":
                self.fix_sip_huawei_te40(ip_address)
            elif device_name == "CloudLink Bar 310":
                # TODO: реализовать для Bar 310
                QMessageBox.information(self, "Информация", "Поддержка Bar 310 будет добавлена позже")
            elif device_name == "Huawei TE-20":
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
        """Исправление SIP регистрации для Huawei TE-40"""
        print(f"\n=== fix_sip_huawei_te40 called ===")
        print(f"IP Address: {ip_address}")
        
        sip_server = "vcs-core-a.sber.ru"
        print(f"SIP Server to set: {sip_server}")
        
        self.show_progress_dialog(f"Установка SIP сервера {sip_server}...")
        
        try:
            # Получаем текущие credentials
            device_name = "Huawei TE-40"
            creds_list = self.device_credentials.get(device_name, [])
            current_idx = self.current_credential_index.get(device_name, 0)
            creds = creds_list[current_idx] if creds_list else {'username': 'api', 'password': ''}
            
            print(f"Credentials: username='{creds['username']}', password='{creds['password']}'")
            
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
        """Исправление SIP регистрации для Huawei TE-20"""
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

        if result.get('action') == 'set_sip_server':
            if result.get('success'):
                QMessageBox.information(
                    self,
                    "Успех",
                    result.get('message', 'SIP сервер успешно установлен')
                )
                self.refresh_data()
            else:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    result.get('message', 'Не удалось установить SIP сервер')
                )

    @pyqtSlot(tuple)
    def on_sip_fix_error(self, error_info):
        """Обработка ошибки установки SIP сервера."""
        self.hide_progress_dialog()
        error_type, error, traceback_text = error_info

        QMessageBox.critical(
            self,
            "Ошибка",
            f"Не удалось установить SIP сервер:\n{str(error)}"
        )

    def on_fix_sip_registration(self, ip_address: str, device_name: str):
        """Обработчик нажатия кнопки 'Исправить' для SIP регистрации."""
        print(f"=== Нажата кнопка Исправить для {device_name} ({ip_address}) ===")

        sip_server = "vcs-core-a.sber.ru"
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

        if device_name == "Huawei TE-40":
            self.fix_sip_huawei_te40(ip_address)
        elif device_name == "CloudLink Bar 310":
            self.fix_sip_huawei_bar310(ip_address)
        elif device_name == "Huawei TE-20":
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
        if device_name == "Huawei TE-40":
            port = self.huawei_settings.get('port', 443)
            fallback = {'username': 'api', 'password': ''}
        elif device_name == "CloudLink Bar 310":
            port = self.huawei_settings.get('port', 443)
            fallback = {'username': 'api', 'password': '***REMOVED_CREDENTIAL***'}
        elif device_name == "Polycom RPG 310":
            port = 22
            fallback = {'username': 'admin', 'password': ''}
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
            current_idx = 0
            creds = fallback

        return port, current_idx, creds

    def _start_sip_fix(self, device_name: str, ip_address: str):
        """Запустить установку SIP сервера в фоновом потоке."""
        sip_server = "vcs-core-a.sber.ru"
        port, current_idx, creds = self._get_sip_fix_connection_params(device_name, ip_address)

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

    def fix_sip_huawei_te40(self, ip_address: str):
        """Исправление SIP регистрации для Huawei TE-40."""
        self._start_sip_fix("Huawei TE-40", ip_address)

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
        
        self.progress_dialog = QProgressDialog(message, "Отмена", 0, 0, self)
        self.progress_dialog.setWindowTitle("Выполнение операции")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setCancelButton(None)  # Отключаем кнопку отмены пока
        self.progress_dialog.setStyleSheet(f"""
            QProgressDialog {{
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
            }}
            QLabel {{
                color: {self.colors['text_primary']};
                font-size: 11pt;
            }}
        """)
        self.progress_dialog.show()
    
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

        title = f"Терминал Huawei TE-20 - {ip_address}"
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

        if device_name == "Huawei TE-20":
            if not hasattr(self, 'te20_terminal_dialog') or self.te20_terminal_dialog is None:
                self.te20_terminal_dialog = MatrixTerminalDialog(self.colors, self)
                self.te20_terminal_dialog.setWindowTitle(f"Терминал Huawei TE-20 - {ip_address}")
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
        self.disconnect_matrix_persistent_handler()
        super().closeEvent(event)
            

