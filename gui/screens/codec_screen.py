from PyQt5.QtWidgets import QVBoxLayout, QScrollArea, QGridLayout, QFrame, QLabel, QWidget, QPushButton, QMessageBox, QProgressDialog
from PyQt5.QtCore import Qt, QTimer, QEventLoop
from .base_screen import BaseScreen


class CodecScreen(BaseScreen):
    def __init__(self, parent=None):
        self.param_count = 15
        self.param_widgets = []
        self.presentation_buttons = {}
        self.sip_fix_buttons = []  # Храним кнопки для каждого блока
        self.volume_buttons = {}  # Храним кнопки для изменения громкости
        self.volume_values = {}  # Храним текущие значения громкости для каждого параметра
        self.volume_session_handler = None
        self.volume_session_key = None
        super().__init__(parent)
        self.volume_refresh_timer = QTimer(self)
        self.volume_refresh_timer.setSingleShot(True)
        self.volume_refresh_timer.timeout.connect(self.refresh)
        self.colors.setdefault('warning', '#FFA500')

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
        # Добавьте цвет для предупреждений, если его нет в родительском словаре
        if hasattr(self, 'colors') and 'warning' not in self.colors:
            self.colors['warning'] = '#FFA500'


    def clear_data(self):
        """Очистка данных перед новой загрузкой"""
        # Если есть таблицы - очищаем их
        if hasattr(self, 'table'):
            self.table.clearContents()

        self.volume_values.clear()
        
        # Если есть метки с данными - очищаем их
        for widget in self.findChildren(QLabel):
            # Очищаем только те метки, которые отображают данные
            if widget.property("data_field") is True:
                widget.setText("—")
        
        # Показываем статус загрузки
        if hasattr(self, 'status_label'):
            self.status_label.setText("Загрузка данных...")


    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Контейнер для параметров с прокруткой
        container = QWidget()
        container.setStyleSheet(f"background-color: {self.colors['surface']};")
        
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Область с прокруткой
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {self.colors['surface']};
            }}
            QScrollBar:vertical {{
                background-color: {self.colors['background']};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self.colors['divider']};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {self.colors['text_secondary']};
            }}
        """)
        
        # Виджет для параметров
        self.param_widget = QWidget()
        self.param_layout = QVBoxLayout(self.param_widget)
        self.param_layout.setSpacing(0)
        self.param_layout.setContentsMargins(30, 20, 30, 20)
        
        scroll_area.setWidget(self.param_widget)
        main_layout.addWidget(scroll_area, 1)
        
        layout.addWidget(container)
        
        # Инициализируем параметры
        self.update_parameters_display()


    def update_parameters_display(self):
        """Обновление отображения параметров"""
        # Очищаем старые виджеты
        while self.param_layout.count():
            child = self.param_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.param_widgets = []
        
        # Определяем блоки параметров
        block1_params = [
            "Версия прошивки",
            "Модель кодеков",
            "Серийный номер",
            "MAC адрес"
        ]
        
        block2_params = [
            "SIP регистрация",
            "Время работы",
            ###"Температура",
            ###"Скорость сети"
        ]
        
        block3_params = [
            "Статус звонка",
            "Статус презентации",
            ###"Громкость микрофона",
            "Громкость динамиков",
            "Статус камеры",
            "Статус микрофона"
        ]
        
        # Генерируем дополнительные параметры если нужно
        all_params = block1_params + block2_params + block3_params
        if self.param_count > len(all_params):
            for i in range(len(all_params), self.param_count):
                all_params.append(f"Доп. параметр {i+1}")
        
        # Отображаем только нужное количество параметров
        display_params = all_params[:self.param_count]
        
        # Определяем, какие блоки отображать
        block1_display = [p for p in block1_params if p in display_params]
        block2_display = [p for p in block2_params if p in display_params]
        block3_display = [p for p in block3_params if p in display_params]
        
        # Создаем и добавляем блоки с разделителями
        if block1_display:
            self.create_param_block(block1_display)
            
        if block2_display and (block1_display or block3_display):
            self.add_divider()
            self.create_param_block(block2_display)
            
        if block3_display and block2_display:
            self.add_divider()
            self.create_param_block(block3_display)


    def create_param_block(self, params):
        """Создание блока параметров"""
        block_widget = QWidget()
        block_layout = QGridLayout(block_widget)
        block_layout.setSpacing(5)
        block_layout.setContentsMargins(0, 10, 0, 10)
        block_layout.setColumnStretch(0, 1)
        block_layout.setColumnStretch(1, 1)
        block_layout.setColumnStretch(2, 0)  # Добавляем колонку для кнопок
        
        for i, param_name in enumerate(params):
            # Метка имени параметра
            name_label = QLabel(f"{param_name}:")
            name_label.setStyleSheet(f"""
                color: {self.colors['text_primary']};
                font-weight: bold;
                font-size: 11pt;
                padding: 8px 0;
            """)
            name_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            # Метка значения параметра
            value_label = QLabel("Не доступно")
            value_label.setStyleSheet(f"""
                color: {self.colors['text_secondary']};
                font-size: 11pt;
                padding: 8px 0;
            """)
            value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            
            # Добавляем в сетку
            block_layout.addWidget(name_label, i, 0)
            block_layout.addWidget(value_label, i, 1)
            
            # Если это параметр "SIP регистрация", добавляем кнопку
            if param_name == "SIP регистрация":
                fix_btn = QPushButton("Исправить")
                fix_btn.setVisible(False)  # Скрыта по умолчанию
                fix_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.colors['error']};
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 6px 12px;
                        font-size: 10pt;
                        font-weight: bold;
                        min-width: 80px;
                        max-width: 80px;
                    }}
                    QPushButton:hover {{
                        background-color: {self.lighten_color(self.colors['error'], 20)};
                    }}
                    QPushButton:pressed {{
                        background-color: {self.colors['error']};
                    }}
                """)
                fix_btn.clicked.connect(self.on_fix_sip_clicked)
                block_layout.addWidget(fix_btn, i, 2)
                self.sip_fix_buttons.append((value_label, fix_btn))
            elif param_name == "\u0421\u0442\u0430\u0442\u0443\u0441 \u043f\u0440\u0435\u0437\u0435\u043d\u0442\u0430\u0446\u0438\u0438":
                presentation_off_btn = QPushButton("\u0412\u044b\u043a\u043b")
                presentation_off_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.colors['surface']};
                        color: white;
                        border: 1px solid white;
                        border-radius: 4px;
                        padding: 6px 12px;
                        font-size: 10pt;
                        font-weight: bold;
                        min-width: 48px;
                        max-width: 48px;
                        min-height: 15px;
                    }}
                    QPushButton:hover {{
                        background-color: {self.lighten_color(self.colors['surface'], 20)};
                    }}
                    QPushButton:pressed {{
                        background-color: {self.colors['surface']};
                    }}
                """)
                presentation_off_btn.clicked.connect(
                    lambda checked=False, name=param_name: self.on_presentation_button_clicked(name, "off")
                )

                presentation_on_btn = QPushButton("\u0412\u043a\u043b")
                presentation_on_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.colors['surface']};
                        color: white;
                        border: 1px solid white;
                        border-radius: 4px;
                        padding: 6px 12px;
                        font-size: 10pt;
                        font-weight: bold;
                        min-width: 48px;
                        max-width: 48px;
                        min-height: 15px;
                    }}
                    QPushButton:hover {{
                        background-color: {self.lighten_color(self.colors['surface'], 20)};
                    }}
                    QPushButton:pressed {{
                        background-color: {self.colors['surface']};
                    }}
                """)
                presentation_on_btn.clicked.connect(
                    lambda checked=False, name=param_name: self.on_presentation_button_clicked(name, "on")
                )

                block_layout.addWidget(presentation_off_btn, i, 2)
                block_layout.addWidget(presentation_on_btn, i, 3)
                self.presentation_buttons[param_name] = {"on": presentation_on_btn, "off": presentation_off_btn}
            elif param_name == "Статус презентации":
                presentation_off_btn = QPushButton("Выкл")
                presentation_off_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.colors['surface']};
                        color: white;
                        border: 1px solid white;
                        border-radius: 4px;
                        padding: 6px 12px;
                        font-size: 10pt;
                        font-weight: bold;
                        min-width: 48px;
                        max-width: 48px;
                        min-height: 15px;
                    }}
                    QPushButton:hover {{
                        background-color: {self.lighten_color(self.colors['surface'], 20)};
                    }}
                    QPushButton:pressed {{
                        background-color: {self.colors['surface']};
                    }}
                """)
                presentation_off_btn.clicked.connect(
                    lambda checked=False, name=param_name: self.on_presentation_button_clicked(name, "off")
                )

                presentation_on_btn = QPushButton("Вкл")
                presentation_on_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.colors['surface']};
                        color: white;
                        border: 1px solid white;
                        border-radius: 4px;
                        padding: 6px 12px;
                        font-size: 10pt;
                        font-weight: bold;
                        min-width: 48px;
                        max-width: 48px;
                        min-height: 15px;
                    }}
                    QPushButton:hover {{
                        background-color: {self.lighten_color(self.colors['surface'], 20)};
                    }}
                    QPushButton:pressed {{
                        background-color: {self.colors['surface']};
                    }}
                """)
                presentation_on_btn.clicked.connect(
                    lambda checked=False, name=param_name: self.on_presentation_button_clicked(name, "on")
                )

                block_layout.addWidget(presentation_off_btn, i, 2)
                block_layout.addWidget(presentation_on_btn, i, 3)
                self.presentation_buttons[param_name] = {"on": presentation_on_btn, "off": presentation_off_btn}
            # Если это параметр "Громкость динамиков", добавляем кнопки
            elif param_name == "Громкость динамиков":
                volume_down_btn = QPushButton("-")
                volume_down_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.colors['surface']};
                        color: white;
                        border: 1px solid white;
                        border-radius: 4px;
                        padding: 6px 12px;
                        font-size: 10pt;
                        font-weight: bold;
                        min-width: 48px;
                        max-width: 48px;
                        min-height: 15px;
                    }}
                    QPushButton:hover {{
                        background-color: {self.lighten_color(self.colors['surface'], 20)};
                    }}
                    QPushButton:pressed {{
                        background-color: {self.colors['surface']};
                    }}
                """)
                volume_down_btn.clicked.connect(lambda checked, name=param_name: self.on_volume_button_clicked(name, "down"))
                
                volume_up_btn = QPushButton("+")
                volume_up_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.colors['surface']};
                        color: white;
                        border: 1px solid white;
                        border-radius: 4px;
                        padding: 6px 12px;
                        font-size: 10pt;
                        font-weight: bold;
                        min-width: 48px;
                        max-width: 48px;
                        min-height: 15px;
                    }}
                    QPushButton:hover {{
                        background-color: {self.lighten_color(self.colors['surface'], 20)};
                    }}
                    QPushButton:pressed {{
                        background-color: {self.colors['surface']};
                    }}
                """)
                volume_up_btn.clicked.connect(lambda checked, name=param_name: self.on_volume_button_clicked(name, "up"))
                
                block_layout.addWidget(volume_down_btn, i, 2)
                block_layout.addWidget(volume_up_btn, i, 3)
                self.volume_buttons[param_name] = {"up": volume_up_btn, "down": volume_down_btn}
            # Если это параметр "Громкость микрофона", добавляем кнопки
            elif param_name == "Громкость микрофона":
                volume_down_btn = QPushButton("-")
                volume_down_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.colors['surface']};
                        color: white;
                        border: 1px solid white;
                        border-radius: 4px;
                        padding: 6px 12px;
                        font-size: 10pt;
                        font-weight: bold;
                        min-width: 48px;
                        max-width: 48px;
                        min-height: 15px;
                    }}
                    QPushButton:hover {{
                        background-color: {self.lighten_color(self.colors['surface'], 20)};
                    }}
                    QPushButton:pressed {{
                        background-color: {self.colors['surface']};
                    }}
                """)
                volume_down_btn.clicked.connect(lambda checked, name=param_name: self.on_volume_button_clicked(name, "down"))
                
                volume_up_btn = QPushButton("+")
                volume_up_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.colors['surface']};
                        color: white;
                        border: 1px solid white;
                        border-radius: 4px;
                        padding: 6px 12px;
                        font-size: 10pt;
                        font-weight: bold;
                        min-width: 48px;
                        max-width: 48px;
                        min-height: 15px;
                    }}
                    QPushButton:hover {{
                        background-color: {self.lighten_color(self.colors['surface'], 20)};
                    }}
                    QPushButton:pressed {{
                        background-color: {self.colors['surface']};
                    }}
                """)
                volume_up_btn.clicked.connect(lambda checked, name=param_name: self.on_volume_button_clicked(name, "up"))
                
                block_layout.addWidget(volume_down_btn, i, 2)
                block_layout.addWidget(volume_up_btn, i, 3)
                self.volume_buttons[param_name] = {"up": volume_up_btn, "down": volume_down_btn}
            else:
                # Для остальных параметров добавляем пустой виджет для выравнивания
                spacer = QWidget()
                spacer.setFixedWidth(80)
                block_layout.addWidget(spacer, i, 2)
            
            self.param_widgets.append((param_name, value_label))
        
        self.param_layout.addWidget(block_widget)


    def add_divider(self):
        """Добавление горизонтального разделителя"""
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"background-color: {self.colors['divider']}; border: none; height: 1px;")
        divider.setFixedHeight(1)
        
        divider_container = QWidget()
        divider_layout = QVBoxLayout(divider_container)
        divider_layout.setContentsMargins(0, 10, 0, 10)
        divider_layout.addWidget(divider)
        
        self.param_layout.addWidget(divider_container)


    def update_data(self, data):
        """Обновление данных на экране"""
        
        # Преобразуем данные из парсера в формат GUI
        display_data = self._convert_parser_data_to_gui(data)
        
        # Для отладки
        print("Данные из парсера:", data)
        print("Данные для GUI:", display_data)
        
        for param_name, value_label in self.param_widgets:
            if param_name in display_data:
                value = display_data[param_name]
                value_label.setText(str(value))
                if param_name in ("Громкость динамиков", "Громкость микрофона"):
                    numeric_value = self._extract_numeric_value(value)
                    if numeric_value is not None:
                        self.volume_values[param_name] = numeric_value
                
                if param_name == "SIP регистрация" and value == "Не зарегистрирован":
                    value_label.setStyleSheet(f"""
                        color: {self.colors['error']};
                        font-size: 11pt;
                        padding: 8px 0;
                        font-weight: bold;
                    """)
                    # Показываем кнопку "Исправить" для этого параметра
                    for val_label, btn in self.sip_fix_buttons:
                        if val_label is value_label:
                            btn.setVisible(True)
                            break
                elif param_name == "SIP регистрация":
                    # Если SIP зарегистрирован, скрываем кнопку
                    for val_label, btn in self.sip_fix_buttons:
                        if val_label is value_label:
                            btn.setVisible(False)
                            break
                    value_label.setStyleSheet(f"""
                        color: {self.colors['secondary']};
                        font-size: 11pt;
                        padding: 8px 0;
                        font-weight: bold;
                    """)
                elif param_name == "Статус звонка" and value == "В звонке":
                    value_label.setStyleSheet(f"""
                        color: {self.colors['secondary']};
                        font-size: 11pt;
                        padding: 8px 0;
                        font-weight: bold;
                    """)
                elif param_name == "Статус микрофона" and value == "Выключен":
                    value_label.setStyleSheet(f"""
                        color: {self.colors['warning']};
                        font-size: 11pt;
                        padding: 8px 0;
                    """)
                else:
                    value_label.setStyleSheet(f"""
                        color: {self.colors['text_primary']};
                        font-size: 11pt;
                        padding: 8px 0;
                    """)
            else:
                value_label.setText("Не доступно")
                value_label.setStyleSheet(f"""
                    color: {self.colors['text_secondary']};
                    font-size: 11pt;
                    padding: 8px 0;
                """)
                # Скрываем кнопку, если параметр не найден
                for val_label, btn in self.sip_fix_buttons:
                    if val_label is value_label:
                        btn.setVisible(False)
                        break


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
        
        # Меняем цвет кнопки при нажатии (визуальный отклик)
        if param_name in self.volume_buttons:
            btn = self.volume_buttons[param_name][direction]
            original_style = btn.styleSheet()
            btn.setStyleSheet(original_style.replace(
                f"background-color: {self.colors['surface']}",
                f"background-color: {self.lighten_color(self.colors['surface'], 30)}"
            ))
            
            # Возвращаем цвет через короткое время
            QTimer.singleShot(100, lambda: btn.setStyleSheet(original_style))
            
            # Управляем громкостью через API
            self.adjust_volume(param_name, direction)

    def on_presentation_button_clicked(self, param_name, direction):
        """Обработчик нажатия кнопок управления презентацией"""
        print(f"Нажата кнопка presentation {direction} для {param_name}")

        if param_name in self.presentation_buttons:
            self.set_presentation_buttons_enabled(param_name, False)
            btn = self.presentation_buttons[param_name][direction]
            original_style = btn.styleSheet()
            btn.setStyleSheet(original_style.replace(
                f"background-color: {self.colors['surface']}",
                f"background-color: {self.lighten_color(self.colors['surface'], 30)}"
            ))

            QTimer.singleShot(100, lambda: btn.setStyleSheet(original_style))
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
                self.schedule_volume_refresh()
            else:
                print(f"Устройство не подтвердило команду презентации {command}")
                self._finish_presentation_terminal(f"device did not confirm command: {command}")
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

        self._run_presentation_countdown(5)
        return True

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
        dialog.setStyleSheet(f"""
            QProgressDialog {{
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
            }}
            QLabel {{
                color: {self.colors['text_primary']};
                font-size: 11pt;
            }}
        """)

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
        min_volume, max_volume = self._get_volume_range()
        current_volume = self._get_current_volume_value(param_name)
        if current_volume is None:
            current_volume = min_volume

        # Вычисляем новое значение
        if direction == "up":
            new_volume = min(max_volume, current_volume + 1)
        else:  # down
            new_volume = max(min_volume, current_volume - 1)
        
        print(f"Текущая громкость: {current_volume}, Новое значение: {new_volume}")
        
        # Обновляем сохраненное значение
        self.volume_values[param_name] = new_volume
        
        # Отправляем команду на устройство через API
        self.set_speaker_volume(new_volume)
    
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
                        self.schedule_volume_refresh()
                    else:
                        print("Ошибка изменения громкости: устройство не подтвердило команду")
                else:
                    print("Не удалось подключиться к устройству для изменения громкости")
                    
            except Exception as e:
                print(f"Ошибка при изменении громкости: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                self.reset_volume_session()

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
                else:
                    print("Не удалось подключиться к устройству для получения громкости")
                    
            except Exception as e:
                print(f"Ошибка при получении громкости: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                self.reset_volume_session()

    def schedule_volume_refresh(self):
        if self.parent:
            self.parent.suppress_success_message_once = True
        self.volume_refresh_timer.start(1500)

    def reset_volume_session(self):
        """Сбрасывает долгоживущую сессию управления громкостью."""
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
                {"port": 443, "use_ssl": True, "label": "HTTPS:443"},
                {"port": 80, "use_ssl": False, "label": "HTTP:80"},
            ]
        elif device_name == "Huawei TE-40":
            from handlers.huawei.te40 import HuaweiTE40Handler
            handler_class = HuaweiTE40Handler
            connection_profiles = [{"port": 443, "use_ssl": True, "label": "HTTPS:443"}]
        elif device_name == "CloudLink Bar 310":
            from handlers.huawei.bar310 import CloudLinkBar310Handler
            handler_class = CloudLinkBar310Handler
            connection_profiles = [{"port": 443, "use_ssl": True, "label": "HTTPS:443"}]
        elif device_name == "Polycom RPG 310":
            from handlers.polycom.rpg310 import PolycomRPG310Handler
            handler_class = PolycomRPG310Handler
            connection_profiles = [{"port": 22, "label": "SSH:22"}]
        else:
            self.reset_volume_session()
            return None

        session_key = (device_name, ip_address, username, password)
        if self.volume_session_handler is not None and self.volume_session_key == session_key:
            self.volume_session_handler.command_logger = command_logger
            return self.volume_session_handler

        self.reset_volume_session()

        for profile in connection_profiles:
            handler_kwargs = dict(base_handler_kwargs)
            handler_kwargs.update({k: v for k, v in profile.items() if k in {"port", "use_ssl"}})

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

    def _get_volume_range(self):
        device_name = self.parent.device_combo.currentText() if self.parent else None
        ranges = {
            "Huawei TE-20": (0, 21),
            "Huawei TE-40": (0, 21),
            "CloudLink Bar 310": (0, 15),
            "Polycom RPG 310": (0, 50),
        }
        return ranges.get(device_name, (0, 21))

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

    def update_volume_display(self, volume, param_name="Громкость динамиков"):
        """Обновление отображения громкости в GUI"""
        numeric_value = self._extract_numeric_value(volume)
        if numeric_value is not None:
            self.volume_values[param_name] = numeric_value

        for name_label, value_label in self.param_widgets:
            if name_label == param_name:
                new_value = str(volume) if isinstance(volume, int) else volume
                value_label.setText(new_value)
                value_label.setStyleSheet(f"""
                    color: {self.colors['text_primary']};
                    font-size: 11pt;
                    padding: 8px 0;
                """)
                print(f"Обновлено отображение {param_name}: {new_value}")
                break
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
                value_label.setText(new_value)
                value_label.setStyleSheet(f"""
                    color: {self.colors['text_primary']};
                    font-size: 11pt;
                    padding: 8px 0;
                """)
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
            'Статус микрофона': 'Статус микрофона',
            'Статус камеры': 'Статус камеры',
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
        if 'mic_mute' in data:
            print(f"  Спецслучай mic_mute: {data['mic_mute']}")
            if data['mic_mute'] == 'On':
                result['Статус микрофона'] = 'Выключен'
            elif data['mic_mute'] == 'Off':
                result['Статус микрофона'] = 'Включен'
        
        if 'speaker_volume' in data:
            print(f"  Спецслучай speaker_volume: {data['speaker_volume']}")
            result['Громкость динамиков'] = str(data['speaker_volume'])
        
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
