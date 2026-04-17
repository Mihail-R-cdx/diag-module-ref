from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QLabel, QFrame
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont
from .base_screen import BaseScreen

class MatrixScreen(BaseScreen):
    def __init__(self, parent=None):
        self.matrix_data = None
        self.current_connection = 1
        self.inputs_num = 8
        self.outputs_num = 1
        self.input_names = []
        self.output_names = ["Main Output"]
        self.matrix_table = None
        self.info_panel_layout = None
        self.output_column_width = 150
        self.main_window = parent
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
        if hasattr(self, 'protocol_value'):
            self.protocol_value.setText("—")
    
    def init_ui(self, params=None):
        """Инициализация UI матрицы"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Параметры матрицы
        if params:
            self.inputs_num = params.get('num_inputs', 8)
            self.outputs_num = params.get('num_outputs', 1)
            self.input_names = params.get('input_names', [])
            self.output_names = params.get('output_names', ["Main Output"])
        else:
            self.inputs_num = 8
            self.outputs_num = 1
            self.input_names = [
                "Ноутбук 1", "Ноутбук 2", "Apple TV", "ВКС система",
                "Документ-камера", "Системный ПК", "Резерв 1", "Резерв 2"
            ]
            self.output_names = ["Main Output"]
        
        # Таблица матрицы
        matrix_container = self.create_matrix_table()
        layout.addWidget(matrix_container, 1)
        
        # Информационная панель (только температура и модель)
        info_panel = self.create_info_panel()
        layout.addWidget(info_panel)
    

    def create_matrix_table(self):
        """Создание таблицы матрицы"""
        container = QWidget()
        container.setStyleSheet(f"background-color: {self.colors['surface']}; border-radius: 8px;")
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Столбцы: Сигнал, HDCP, Входы, Выход
        num_columns = 3 + self.outputs_num
        
        self.matrix_table = QTableWidget(self.inputs_num, num_columns)
        self.matrix_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
                gridline-color: {self.colors['divider']};
                border: none;
                font-size: 12pt;
                outline: 0;  /* Убираем рамку фокуса */
            }}
            QTableWidget::item {{
                padding: 4px 5px;
                text-align: center;
                background-color: {self.colors['surface']};
                border: none;  /* Убираем границы у ячеек */
            }}
            QTableWidget::item:selected {{
                background-color: {self.colors['surface']};  /* Убираем выделение */
                color: {self.colors['text_primary']};
            }}
            QTableWidget::item:hover {{
                background-color: {self.colors['surface']};  /* Убираем эффект наведения */
                border: none;
            }}
            QTableWidget:focus {{
                outline: none;  /* Убираем рамку фокуса с таблицы */
            }}
            QHeaderView::section {{
                background-color: {self.colors['background']};
                color: {self.colors['text_primary']};
                padding: 4px;
                border: 1px solid {self.colors['divider']};
                font-weight: bold;
                font-size: 13pt;
                text-align: center;
            }}
        """)
        
        # Отключаем выделение
        self.matrix_table.setSelectionMode(QTableWidget.NoSelection)
        self.matrix_table.setFocusPolicy(Qt.NoFocus)  # Отключаем фокус
        
        # Подключаем обработчик кликов на ячейки
        self.matrix_table.cellClicked.connect(self.on_output_cell_clicked)
        
        # Устанавливаем заголовки через отдельный метод
        self.update_table_headers()
        
        # Настройка заголовков
        vertical_header = self.matrix_table.verticalHeader()
        vertical_header.setDefaultSectionSize(40)
        vertical_header.setSectionResizeMode(QHeaderView.Fixed)
        
        # Растягивание столбцов
        horizontal_header = self.matrix_table.horizontalHeader()
        
        # Сигнал и HDCP - фиксированная ширина
        horizontal_header.setSectionResizeMode(0, QHeaderView.Fixed)
        horizontal_header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.matrix_table.setColumnWidth(0, 80)   # Сигнал
        self.matrix_table.setColumnWidth(1, 80)   # HDCP
        
        # Входы - растягиваются, но с ограничением
        horizontal_header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.matrix_table.setColumnWidth(2, 200)  # Начальная ширина
        
        # Выход - растягивается с приоритетом
        horizontal_header.setSectionResizeMode(3, QHeaderView.Stretch)
        
        # Заполняем таблицу
        self.fill_matrix_table()
        
        layout.addWidget(self.matrix_table)
        return container



    def fill_matrix_table(self):
        """Заполнение таблицы данными"""
        if not self.matrix_table:
            return
        
        for row in range(self.inputs_num):
            # Сигнал
            signal_item = QTableWidgetItem()
            signal_item.setTextAlignment(Qt.AlignCenter)
            signal_font = QFont()
            signal_font.setPointSize(20)  # Увеличенный размер
            signal_item.setFont(signal_font)
            
            if self.matrix_data and 'signal_status' in self.matrix_data:
                signal_info = self.matrix_data['signal_status'].get(row + 1, {})
                has_signal = signal_info.get('has_signal', False)
                
                if has_signal:
                    signal_item.setText("●")
                    signal_item.setForeground(QColor("#4CAF50"))
                    signal_item.setToolTip("Сигнал присутствует")
                else:
                    signal_item.setText("●")
                    signal_item.setForeground(QColor(self.colors['error']))
                    signal_item.setToolTip("Нет сигнала")
            else:
                signal_item.setText("●")
                signal_item.setForeground(QColor(self.colors['error']))
                signal_item.setToolTip("Нет данных")
            
            self.matrix_table.setItem(row, 0, signal_item)
            
            # HDCP
            hdcp_item = QTableWidgetItem()
            hdcp_item.setTextAlignment(Qt.AlignCenter)
            
            if self.matrix_data:
                input_hdcp_status = self.matrix_data.get('input_hdcp_status', [])
                input_hdcp_auth = self.matrix_data.get('input_hdcp_auth', [])
                
                if row < len(input_hdcp_status):
                    hdcp_status = input_hdcp_status[row]
                    hdcp_auth = input_hdcp_auth[row] if row < len(input_hdcp_auth) else 0
                    
                    if hdcp_status not in ['0', '1']:
                        if hdcp_auth == 1:
                            hdcp_item.setText("●")
                            hdcp_item.setForeground(QColor("#4CAF50"))
                            hdcp_item.setToolTip("HDCP включен")
                        else:
                            hdcp_item.setText("○")
                            hdcp_item.setForeground(QColor(self.colors['text_secondary']))
                            hdcp_item.setToolTip("HDCP выключен")
                    else:
                        hdcp_item.setText("○")
                        hdcp_item.setForeground(QColor(self.colors['text_secondary']))
                        hdcp_item.setToolTip("HDCP не активен")
                else:
                    hdcp_item.setText("○")
                    hdcp_item.setForeground(QColor(self.colors['text_secondary']))
                    hdcp_item.setToolTip("Нет данных")
            else:
                hdcp_item.setText("○")
                hdcp_item.setForeground(QColor(self.colors['text_secondary']))
                hdcp_item.setToolTip("Нет данных")
            
            self.matrix_table.setItem(row, 1, hdcp_item)
            
            # Название входа
            if row < len(self.input_names):
                input_name = self.input_names[row]
            else:
                input_name = f"Вход {row + 1}"
            input_item = QTableWidgetItem(input_name)
            input_item.setTextAlignment(Qt.AlignVCenter)
            self.matrix_table.setItem(row, 2, input_item)
            
            # Выход
            if self.outputs_num > 0:
                current_connection = self.current_connection
                if self.matrix_data and 'current_connection' in self.matrix_data:
                    current_connection = self.matrix_data['current_connection']
                
                is_connected = (row + 1 == current_connection)
                
                output_item = QTableWidgetItem()
                output_item.setTextAlignment(Qt.AlignCenter)
                
                if is_connected:
                    output_item.setText("●")
                    output_item.setForeground(QColor(self.colors['primary']))
                    output_item.setToolTip("Активное подключение")
                else:
                    output_item.setText("○")
                    output_item.setForeground(QColor(self.colors['text_secondary']))
                    output_item.setToolTip("Нет подключения")
                
                self.matrix_table.setItem(row, 3, output_item)
    
    def create_info_panel(self):
        """Создание информационной панели (только температура и модель)"""
        panel = QWidget()
        panel.setStyleSheet(f"""
            background-color: {self.colors['surface']};
            border-radius: 8px;
            padding: 10px;
        """)
        
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Температура
        temp_label = QLabel("Температура:")
        temp_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 10pt;")
        
        self.temp_value = QLabel("—")
        self.temp_value.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 10pt;")
        
        # Модель
        model_label = QLabel("Модель:")
        model_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 10pt;")
        
        self.model_value = QLabel("—")
        self.model_value.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 10pt;")

        protocol_label = QLabel("Протокол:")
        protocol_label.setStyleSheet(f"color: {self.colors['text_secondary']}; font-size: 10pt;")

        self.protocol_value = QLabel("—")
        self.protocol_value.setStyleSheet(f"color: {self.colors['text_primary']}; font-weight: bold; font-size: 10pt;")
        
        layout.addWidget(temp_label)
        layout.addWidget(self.temp_value)
        layout.addSpacing(30)
        layout.addWidget(model_label)
        layout.addWidget(self.model_value)
        layout.addSpacing(30)
        layout.addWidget(protocol_label)
        layout.addWidget(self.protocol_value)
        layout.addStretch()
        
        return panel
    
    def update_data(self, data=None):
        """Обновление данных матрицы"""
        print(f"MatrixScreen.update_data called with data: {data}")
        
        if data:
            self.matrix_data = data
            
            # Обновляем параметры
            self.inputs_num = data.get('inputs_num', self.inputs_num)
            self.input_names = data.get('input_names', self.input_names)
            self.output_names = data.get('output_names', self.output_names)
            self.current_connection = data.get('current_connection', 1)
            
            print(f"inputs_num: {self.inputs_num}")
            print(f"input_names: {self.input_names}")
            print(f"output_names: {self.output_names}")
            print(f"current_connection: {self.current_connection}")
            
            # Обновляем заголовки
            self.update_table_headers()
            
            # Обновляем таблицу
            if self.matrix_table:
                self.matrix_table.setRowCount(self.inputs_num)
                self.fill_matrix_table()
            
            # Обновляем информационную панель - ИСПРАВЛЕНО
            # Модель берем прямо из корневого словаря
            model = data.get('model', 'Unknown')
            print(f"model from data: {model}")
            self.model_value.setText(model)
            
            # Температуру берем прямо из корневого словаря
            temperature = data.get('temperature', 0)
            print(f"temperature from data: {temperature}")
            self.temp_value.setText(f"{temperature}°C")

            protocol = data.get('connection_protocol', 'Unknown')
            print(f"protocol from data: {protocol}")
            self.protocol_value.setText(protocol)
            
        else:
            print("No data received")
            if self.matrix_table:
                self.fill_matrix_table()

    def update_table_headers(self):
        """Обновление заголовков таблицы"""
        if not self.matrix_table:
            return
        
        headers = ["Сигнал", "HDCP", "Входы"]
        if self.output_names and len(self.output_names) > 0:
            headers.append(self.output_names[0])  # Название первого (и единственного) выхода
        else:
            headers.append("Выход")
        
        self.matrix_table.setHorizontalHeaderLabels(headers)


    def on_output_cell_clicked(self, row, column):
        """Обработка клика на ячейку выхода для переключения коммутации"""
        if column != 3:  # Только для столбца выхода
            return
        
        input_num = row + 1  # Номер входа (1-based)
        print(f"Clicked on output cell for input {input_num}")
        
        # Получаем параметры подключения из главного окна
        if not self.main_window:
            print("No main window reference")
            return
        
        ip_address = self.main_window.ip_entry.text().strip()
        device_name = self.main_window.device_combo.currentText()
        
        # Получаем credentials для устройства
        creds_list = self.main_window.device_credentials.get(device_name, [])
        if not creds_list:
            print("No credentials found")
            return
        
        current_idx = self.main_window.current_credential_index.get(device_name, 0)
        if current_idx >= len(creds_list):
            current_idx = 0
        creds = creds_list[current_idx]
        
        # Создаем временное соединение для отправки команды
        from handlers.extron.in1804 import ExtronIN1804Handler
        
        try:
            # Создаем обработчик и подключаемся
            handler = ExtronIN1804Handler(
                ip_address=ip_address,
                port=22023,
                username=creds.get('username', ''),
                password=creds.get('password', '')
            )
            
            # Подключаемся (с аутентификацией)
            print("Connecting to matrix for switch command...")
            handler.connect()
            
            # Отправляем команду переключения
            print(f"Sending switch command to input {input_num}")
            handler.set_connection(1, input_num)
            
            # Закрываем соединение
            handler.disconnect()
            
            print(f"Successfully switched to input {input_num}")
            
            # Быстрое обновление только статуса коммутации
            QTimer.singleShot(300, self.request_status_update)
            
        except Exception as e:
            print(f"Error switching matrix: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось переключить матрицу: {str(e)}"
            )


    def update_info_panel(self):
        """Обновление информационной панели"""
        if hasattr(self, 'temp_value') and hasattr(self, 'model_value') and hasattr(self, 'protocol_value'):
            # Обновляем только если есть данные
            if self.matrix_data:
                model = self.matrix_data.get('model', 'Unknown')
                temperature = self.matrix_data.get('temperature', 0)
                protocol = self.matrix_data.get('connection_protocol', 'Unknown')
                self.model_value.setText(model)
                self.temp_value.setText(f"{temperature}°C")
                self.protocol_value.setText(protocol)

    def update_connection_display(self):
        """Быстрое обновление только отображения коммутации в таблице"""
        if not self.matrix_table:
            return
        
        # Обновляем только 3-й столбец (индекс 3) для всех строк
        for row in range(self.inputs_num):
            is_connected = (row + 1 == self.current_connection)
            
            output_item = self.matrix_table.item(row, 3)
            if not output_item:
                output_item = QTableWidgetItem()
                self.matrix_table.setItem(row, 3, output_item)
            
            output_item.setTextAlignment(Qt.AlignCenter)
            
            if is_connected:
                output_item.setText("●")
                output_item.setForeground(QColor(self.colors['primary']))
                output_item.setToolTip("Активное подключение")
            else:
                output_item.setText("○")
                output_item.setForeground(QColor(self.colors['text_secondary']))
                output_item.setToolTip("Нет подключения")
        
        # Принудительно обновляем таблицу
        self.matrix_table.viewport().update()

    def request_status_update(self):
        """Быстрое обновление только статуса коммутации после переключения"""
        if not self.main_window:
            return
        
        ip_address = self.main_window.ip_entry.text().strip()
        device_name = self.main_window.device_combo.currentText()
        
        # Получаем credentials для устройства
        creds_list = self.main_window.device_credentials.get(device_name, [])
        if not creds_list:
            return
        
        current_idx = self.main_window.current_credential_index.get(device_name, 0)
        if current_idx >= len(creds_list):
            current_idx = 0
        creds = creds_list[current_idx]
        
        # Создаем временное соединение для быстрого опроса
        from handlers.extron.in1804 import ExtronIN1804Handler
        
        try:
            # Создаем обработчик и подключаемся
            handler = ExtronIN1804Handler(
                ip_address=ip_address,
                port=22023,
                username=creds.get('username', ''),
                password=creds.get('password', '')
            )
            
            # Подключаемся (с аутентификацией)
            print("Quick connecting to update connection status...")
            handler.connect()
            
            # Получаем только текущие коммутации (быстрая команда)
            connections = handler.get_connections()
            
            # Закрываем соединение
            handler.disconnect()
            
            if connections:
                self.current_connection = connections[0]
                print(f"Updated connection: {self.current_connection}")
                
                # Обновляем только столбец с коммутацией в таблице
                self.update_connection_display()
            
        except Exception as e:
            print(f"Error quick updating status: {e}")
        
    def refresh_statuses(self):
        """Обновление статусов"""
        self.update_data()
