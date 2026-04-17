import sys
import os
import json
from PyQt5.QtWidgets import (QApplication, QWidget, QDialog, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QComboBox, 
                             QSizePolicy)
from PyQt5.QtGui import QPixmap, QPainter, QColor, QCursor
from PyQt5.QtCore import Qt

# === ИМПОРТ ВАШЕГО ОСНОВНОГО ОКНА ===
try:
    from gui.main_window import VCSDiagnosticApp  
except ImportError:
    # Заглушка, если модуль gui временно недоступен для тестов
    class VCSDiagnosticApp(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("VCSDiagnosticApp (Заглушка)")
            self.resize(300, 100)
            lbl = QLabel("Окно диагностики открыто", self)
            lbl.move(50, 40)
# ======================================

# === ФУНКЦИИ РАБОТЫ С БАЗОЙ ДАННЫХ ===

def load_database_json(file_path):
    """
    Читает базу данных из JSON файла.
    Возвращает словарь: { "Название помещения": { "image": path, "areas": [...] } }
    """
    if not os.path.exists(file_path):
        print(f"Ошибка: Файл базы данных {file_path} не найден!")
        return {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Ошибка чтения JSON: {e}")
        return {}

def load_database_excel(file_path):
    """
    ЗАГОТОВКА НА БУДУЩЕЕ.
    Здесь будет логика чтения через pandas или openpyxl.
    Пока возвращает пустой словарь или вызывает JSON для теста.
    """
    print("Функция чтения Excel пока не активирована, используется JSON.")
    return load_database_json(file_path)

# === ВИДЖЕТ С КАРТИНКОЙ (МОДИФИЦИРОВАННЫЙ) ===

class ClickableImageWidget(QWidget):
    def __init__(self, scale_factor=100):
        super().__init__()
        self.scale_factor = scale_factor
        self.original_pixmap = QPixmap()
        self.pixmap = QPixmap()
        self.areas = []
        self.hovered_area_index = -1
        self.setMouseTracking(True)
        # Минимальный размер, чтобы окно не схлопывалось до загрузки
        self.setMinimumSize(400, 300) 

    def load_scheme(self, image_path, areas):
        """
        Динамическая загрузка новой схемы и зон.
        """
        self.original_pixmap = QPixmap(image_path)
        if self.original_pixmap.isNull():
            print(f"Не удалось загрузить изображение: {image_path}")
            self.areas = []
            self.pixmap = QPixmap() # Сбрасываем pixmap
            self.update()
            return

        # Масштабирование
        width = int(self.original_pixmap.width() * self.scale_factor / 100)
        height = int(self.original_pixmap.height() * self.scale_factor / 100)
        self.pixmap = self.original_pixmap.scaled(width, height, aspectRatioMode=Qt.KeepAspectRatio)
        
        # Пересчет координат зон под масштаб
        self.areas = []
        for x1, y1, x2, y2 in areas:
            self.areas.append((
                int(x1 * self.scale_factor / 100), int(y1 * self.scale_factor / 100),
                int(x2 * self.scale_factor / 100), int(y2 * self.scale_factor / 100)
            ))
        
        # Изменяем размер виджета под картинку
        self.resize(self.pixmap.width(), self.pixmap.height())
        self.hovered_area_index = -1
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            x, y = pos.x(), pos.y()

            for i, (x1, y1, x2, y2) in enumerate(self.areas):
                if x1 <= x <= x2 and y1 <= y <= y2:
                    # --- ОТКРЫТИЕ VCSDiagnosticApp ---
                    cursor_global_pos = QCursor.pos()
                    new_x = cursor_global_pos.x()
                    new_y = self.pos().y()
                    
                    vcs_window = VCSDiagnosticApp()
                    vcs_window.move(new_x, new_y)
                    vcs_window.show()  
                    return

    def mouseMoveEvent(self, event):
        pos = event.pos()
        x, y = pos.x(), pos.y()
        new_hovered = -1
        for i, (x1, y1, x2, y2) in enumerate(self.areas):
            if x1 <= x <= x2 and y1 <= y <= y2:
                new_hovered = i
                break
        if new_hovered != self.hovered_area_index:
            self.hovered_area_index = new_hovered
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Если картинка загружена
        if not self.pixmap.isNull():
            painter.drawPixmap(0, 0, self.pixmap)
            
            # Рисуем зоны
            for i, (x1, y1, x2, y2) in enumerate(self.areas):
                # Если зона активна (ховер) - цвет ярче
                color = QColor(150, 150, 150, 150) if i == self.hovered_area_index else QColor(200, 200, 200, 100)
                painter.setBrush(color)
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(x1, y1, x2 - x1, y2 - y1, 10, 10)
        else:
            # === ИЗМЕНЕНИЕ: Подсказка, если картинка не загружена ===
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(self.rect(), Qt.AlignCenter, "Выберите помещение\nдля отображения схемы")
            # ==============================================

# === ГЛАВНОЕ ОКНО С ПОИСКОМ ===

class MainSchemeWindow(QWidget):
    def __init__(self, database):
        super().__init__()
        self.database = database
        self.all_rooms = list(database.keys())
        self.scale_factor = 50  # Глобальный масштаб
        
        self.init_ui()
        
        # === ИЗМЕНЕНИЕ: Убрано автоматическое загрузка первого помещения ===
        # if self.all_rooms:
        #     self.load_room_data(self.all_rooms[0])
        # ==================================================================

    def init_ui(self):
        self.setWindowTitle("Схема помещений с поиском")
        main_layout = QVBoxLayout()
        
        # --- Верхняя панель (Поиск + Список) ---
        top_panel = QHBoxLayout()
        
        # 1. Поле поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск помещения...")
        self.search_input.textChanged.connect(self.filter_rooms)
        
        # 2. Выпадающий список
        self.room_combo = QComboBox()
        self.room_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.room_combo.currentTextChanged.connect(self.on_room_selected)
        
        # Добавляем виджеты на панель
        top_panel.addWidget(QLabel("Поиск:"))
        top_panel.addWidget(self.search_input, stretch=1)
        top_panel.addWidget(QLabel("Выбор:"))
        top_panel.addWidget(self.room_combo, stretch=1)
        
        main_layout.addLayout(top_panel)
        
        # --- Область схемы ---
        self.image_widget = ClickableImageWidget(scale_factor=self.scale_factor)
        main_layout.addWidget(self.image_widget)
        
        self.setLayout(main_layout)
        
        # Инициализация списка
        self.update_combo_list(self.all_rooms)
        
        # === ИЗМЕНЕНИЕ: Сбрасываем выбор в ComboBox, чтобы не было выбрано первое значение ===
        self.room_combo.setCurrentIndex(-1)
        # ================================================================================

    def filter_rooms(self, text):
        """
        Фильтрует список помещений в ComboBox на основе текста в поиске.
        """
        text = text.lower()
        filtered = [room for room in self.all_rooms if text in room.lower()]
        self.update_combo_list(filtered)

    def update_combo_list(self, rooms_list):
        """
        Обновляет элементы в ComboBox, сохраняя текущий выбор, если возможно.
        """
        current_text = self.room_combo.currentText()
        
        self.room_combo.blockSignals(True) # Блокируем сигнал, чтобы не триггерить загрузку при обновлении
        self.room_combo.clear()
        self.room_combo.addItems(rooms_list)
        
        # Пытаемся вернуть выбор, если он есть в отфильтрованном списке
        index = self.room_combo.findText(current_text)
        if index >= 0:
            self.room_combo.setCurrentIndex(index)
            
        self.room_combo.blockSignals(False)

    def on_room_selected(self, room_name):
        """
        Вызывается при выборе помещения в списке (клик или Enter).
        """
        # Проверка на пустую строку (если выбор сброшен)
        if not room_name:
            return
            
        if room_name in self.database:
            self.load_room_data(room_name)

    def load_room_data(self, room_name):
        """
        Получает данные из БД и передает их в виджет картинки.
        """
        data = self.database[room_name]
        image_path = data.get("image", "")
        areas = data.get("areas", [])
        
        self.image_widget.load_scheme(image_path, areas)

# === MAIN ===
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 1. Загрузка базы данных
    db_path = "database.json" 
    database = load_database_json(db_path)
    
    # Если в будущем будет Excel:
    # database = load_database_excel("database.xlsx")

    if not database:
        print("База данных пуста. Проверьте файл database.json")
        # Создаем тестовую запись, чтобы приложение не упало
        database = {
            "Тестовое помещение": {
                "image": r"C:\Users\all-sp-p03\Documents\test module\pics\Scheme P-6.png",
                "areas": [[925, 425, 1175, 930]]
            }
        }

    # 2. Запуск главного окна
    window = MainSchemeWindow(database)
    window.resize(1000, 800)
    window.move(100, 100)
    window.show()

    sys.exit(app.exec_())