# gui/screens/pdu_screen.py

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                             QLabel, QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot  # Добавлен pyqtSlot
from PyQt5.QtGui import QColor, QBrush, QFont

from .base_screen import BaseScreen


class PDUScreen(BaseScreen):
    """Экран отображения и управления PDU Aten"""
    
    # Сигналы для управления розетками
    outlet_control_signal = pyqtSignal(int, str)  # (номер_розетки, команда)
    
    def __init__(self, parent=None):
        # Имена розеток по умолчанию
        self.outlet_names = [
            "Розетка 1", "Розетка 2", "Розетка 3", "Розетка 4",
            "Розетка 5", "Розетка 6", "Розетка 7", "Розетка 8"
        ]
        
        # Состояние розеток
        self.outlets = []
        
        # Информация об устройстве
        self.device_info = {}
        
        super().__init__(parent)
    
    def clear_data(self):
        """Очистка данных перед новой загрузкой"""
        # Если есть таблицы - очищаем их
        if hasattr(self, 'table'):
            self.table.clearContents()
        
        # Если есть метки с данными - очищаем их
        for widget in self.findChildren(QLabel):
            # Очищаем только те метки, которые отображают данные
            if widget.property("data_field") is True:
                widget.setText("—")
        
        # Показываем статус загрузки
        if hasattr(self, 'status_label'):
            self.status_label.setText("Загрузка данных...")      
    
    def init_ui(self):
        """Инициализация интерфейса"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # 1. Панель с информацией об устройстве
        self.create_info_panel(main_layout)
        
        # 2. Таблица розеток
        self.create_outlets_table(main_layout)
        
        # Подключаем сигналы
        self.outlet_control_signal.connect(self.on_outlet_control)
    
    def create_info_panel(self, parent_layout):
        """Создание панели информации об устройстве"""
        info_group = QGroupBox("Информация об устройстве")
        info_group.setStyleSheet(f"""
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
        
        info_layout = QHBoxLayout()
        
        # Создаем метки для информации
        self.info_labels = {}
        info_fields = [
            ('model', 'Модель:'),
            ('ip_address', 'IP адрес:')
        ]
        
        for field, label in info_fields:
            container = QWidget()
            h_layout = QHBoxLayout(container)
            h_layout.setContentsMargins(5, 2, 5, 2)
            
            label_widget = QLabel(label)
            label_widget.setStyleSheet(f"color: {self.colors['text_secondary']}; font-weight: normal;")
            
            value_widget = QLabel("—")
            value_widget.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold;")
            value_widget.setAlignment(Qt.AlignLeft)
            
            h_layout.addWidget(label_widget)
            h_layout.addWidget(value_widget)
            h_layout.addStretch()
            
            self.info_labels[field] = value_widget
            info_layout.addWidget(container)
        
        info_layout.addStretch()
        info_group.setLayout(info_layout)
        parent_layout.addWidget(info_group)
    

    def create_outlets_table(self, parent_layout):
        """Создание таблицы розеток"""
        table_group = QGroupBox("Управление розетками")
        table_group.setStyleSheet(f"""
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
        
        table_layout = QVBoxLayout()
        
        # Добавляем кнопку обновления над таблицей
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()
        
        btn_refresh = QPushButton("Обновить статус")
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['background']};
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['divider']};
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            QPushButton:hover {{
                background-color: {self.colors['divider']};
                border: 1px solid {self.colors['primary']};
            }}
        """)
        btn_refresh.clicked.connect(self.refresh)
        refresh_layout.addWidget(btn_refresh)
        
        table_layout.addLayout(refresh_layout)
        
        # Создаем таблицу
        self.outlets_table = QTableWidget()
        self.outlets_table.setColumnCount(6)
        self.outlets_table.setHorizontalHeaderLabels([
            "№", "Статус", "Название", "Вкл", "Выкл", "Перезаг"
        ])
        
        # Настройка таблицы
        self.outlets_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.outlets_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.outlets_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.outlets_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.outlets_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.outlets_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        self.outlets_table.verticalHeader().setVisible(False)
        self.outlets_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # ОТКЛЮЧАЕМ ВЫДЕЛЕНИЕ СТРОК
        self.outlets_table.setSelectionMode(QTableWidget.NoSelection)  # <- ЭТО ВАЖНО
        self.outlets_table.setFocusPolicy(Qt.NoFocus)  # <- И ЭТО
        
        # Установим минимальную высоту таблицы
        self.outlets_table.setMinimumHeight(300)
        
        # Стили для таблицы
        self.outlets_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.colors['background']};
                color: {self.colors['text_primary']};
                gridline-color: {self.colors['divider']};
                border: 1px solid {self.colors['divider']};
            }}
            QTableWidget::item {{
                padding: 5px;
                border-bottom: 1px solid {self.colors['divider']};
            }}
            QTableWidget::item:selected {{
                background-color: transparent;  /* Убираем фон при выделении */
                color: {self.colors['text_primary']};
            }}
            QHeaderView::section {{
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
                padding: 8px;
                border: none;
                border-bottom: 2px solid {self.colors['primary']};
                font-weight: bold;
            }}
            QTableCornerButton::section {{
                background-color: {self.colors['surface']};
                border: none;
            }}
        """)
        
        table_layout.addWidget(self.outlets_table)
        table_group.setLayout(table_layout)
        parent_layout.addWidget(table_group, 1)
    
    def update_data(self, data):
        """Обновление данных на экране"""
        print(f"PDU Screen update_data called with: {data}")  # Отладка
        
        if not data:
            print("No data received")  # Отладка
            return
        
        # Обновляем информацию об устройстве
        if 'device_info' in data:
            self.device_info = data['device_info']
            print(f"Device info: {self.device_info}")  # Отладка
            self.update_info_panel()
        
        # Обновляем статус розеток
        if 'outlets' in data:
            self.outlets = data['outlets']
            print(f"Outlets data: {self.outlets}")  # Отладка
            
            # Обновляем имена розеток, если они есть в данных
            for outlet in self.outlets:
                if 'name' in outlet and outlet['name']:
                    idx = outlet['number'] - 1
                    if 0 <= idx < len(self.outlet_names):
                        self.outlet_names[idx] = outlet['name']
            
            print(f"Updating table with {len(self.outlets)} outlets")  # Отладка
            self.update_outlets_table()
        else:
            print("No 'outlets' key in data")  # Отладка
    
    def update_info_panel(self):
        """Обновление панели информации"""
        if 'model' in self.device_info:
            self.info_labels['model'].setText(self.device_info['model'])
        
        if 'ip_address' in self.device_info:
            self.info_labels['ip_address'].setText(self.device_info['ip_address'])
        
        if 'firmware' in self.device_info:
            self.info_labels['firmware'].setText(self.device_info['firmware'])
        
        # Обновляем статус подключения
        if 'connected' in self.device_info:
            status = "Подключено" if self.device_info['connected'] else "Отключено"
            status_color = self.colors['secondary'] if self.device_info['connected'] else self.colors['error']
            self.info_labels['status'].setText(status)
            self.info_labels['status'].setStyleSheet(f"color: {status_color}; font-weight: bold;")
    

    def update_outlets_table(self):
        """Обновление таблицы розеток"""
        print(f"Updating outlets table. Outlets count: {len(self.outlets)}")  # Отладка
        
        # Очищаем таблицу
        self.outlets_table.clearContents()
        self.outlets_table.setRowCount(0)
        
        # Устанавливаем количество строк
        self.outlets_table.setRowCount(len(self.outlets))
        print(f"Table rows set to: {self.outlets_table.rowCount()}")  # Отладка
        
        for row, outlet in enumerate(self.outlets):
            print(f"Processing outlet {row+1}: {outlet}")  # Отладка
            
            # Номер розетки
            num_item = QTableWidgetItem(str(outlet.get('number', row + 1)))
            num_item.setTextAlignment(Qt.AlignCenter)
            self.outlets_table.setItem(row, 0, num_item)
            
            # Статус (иконка)
            status_widget = QWidget()
            status_layout = QHBoxLayout(status_widget)
            status_layout.setContentsMargins(0, 0, 0, 0)
            status_layout.setAlignment(Qt.AlignCenter)
            
            status_label = QLabel()
            status_label.setAlignment(Qt.AlignCenter)
            
            status = outlet.get('status', 'off').lower()
            
            # Устанавливаем иконку в зависимости от статуса
            if status == 'on' or status == '1' or status == 'true':
                status_label.setText("✅")  # Зеленая галочка для включено
                status_label.setStyleSheet("""
                    font-size: 16pt;
                    color: #4CAF50;
                """)
            else:
                status_label.setText("❌")  # Красный крестик для выключено
                status_label.setStyleSheet("""
                    font-size: 16pt;
                    color: #f44336;
                """)
            
            status_layout.addWidget(status_label)
            self.outlets_table.setCellWidget(row, 1, status_widget)
            
            # Название розетки
            outlet_name = outlet.get('name', self.outlet_names[row] if row < len(self.outlet_names) else f"Розетка {row + 1}")
            name_item = QTableWidgetItem(outlet_name)
            name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.outlets_table.setItem(row, 2, name_item)
            
            # Кнопки управления
            for col, (action, symbol, tooltip) in enumerate([
                (3, "✅", "Включить"),
                (4, "❌", "Выключить"), 
                (5, "🔄", "Перезагрузить")
            ], start=3):
                btn = QPushButton(symbol)
                btn.setToolTip(tooltip)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.colors['background']};
                        color: {self.colors['text_primary']};
                        border: 1px solid {self.colors['divider']};
                        border-radius: 3px;
                        padding: 5px;
                        font-size: 14pt;
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
                
                # Привязываем данные к кнопке
                btn.clicked.connect(lambda checked, r=row, a=action: self.on_outlet_button_click(r, a))
                
                self.outlets_table.setCellWidget(row, col, btn)
        
        # Подгоняем высоту строк
        for row in range(self.outlets_table.rowCount()):
            self.outlets_table.setRowHeight(row, 40)
        
        # Автоматически подгоняем ширину колонок под содержимое заголовков
        self.outlets_table.resizeColumnsToContents()
        
        # Немного увеличиваем ширину для удобства
        self.outlets_table.setColumnWidth(3, self.outlets_table.columnWidth(3) + 10)
        self.outlets_table.setColumnWidth(4, self.outlets_table.columnWidth(4) + 10)
        self.outlets_table.setColumnWidth(5, self.outlets_table.columnWidth(5) + 10)
        
        # Обновляем таблицу
        self.outlets_table.viewport().update()
        print("Table update complete")  # Отладка
      

    def on_outlet_button_click(self, row, action):
        """Обработчик нажатия на кнопку управления розеткой"""
        outlet_num = row + 1
        
        # Маппинг колонок на команды
        action_commands = {3: "on", 4: "off", 5: "reboot"}
        action_names = {3: "Включить", 4: "Выключить", 5: "Перезагрузить"}
        
        if action in action_commands:
            command = action_commands[action]
            action_name = action_names[action]
            outlet_name = self.outlet_names[row] if row < len(self.outlet_names) else f"Розетка {outlet_num}"
            
            # Подтверждение действия
            reply = QMessageBox.question(
                self,
                "Подтверждение",
                f"{action_name} {outlet_name}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.outlet_control_signal.emit(outlet_num, command)
    
    @pyqtSlot(int, str)
    def on_outlet_control(self, outlet_num: int, command: str):
        """Обработка сигнала управления розеткой"""
        if self.parent and hasattr(self.parent, 'control_pdu_outlet'):
            self.parent.control_pdu_outlet(outlet_num, command)
    
    def refresh(self):
        """Обновление данных"""
        if self.parent and hasattr(self.parent, 'refresh_data'):
            self.parent.refresh_data()