import sys
from PyQt5.QtWidgets import QApplication, QWidget, QDialog, QVBoxLayout, QLabel
from PyQt5.QtGui import QPixmap, QPainter, QColor, QCursor
from PyQt5.QtCore import Qt

# === ИМПОРТ ВАШЕГО ОСНОВНОГО ОКНА ===
# Убедитесь, что папка gui находится рядом с этим скриптом
from gui.main_window import VCSDiagnosticApp  
# ======================================

class ClickableImageWidget(QWidget):
    def __init__(self, image_path, scale_factor=100):
        super().__init__()
        # ... (остальной код __init__ без изменений) ...
        self.original_pixmap = QPixmap(image_path)
        self.scale_factor = scale_factor
        width = int(self.original_pixmap.width() * scale_factor / 100)
        height = int(self.original_pixmap.height() * scale_factor / 100)
        self.pixmap = self.original_pixmap.scaled(width, height, aspectRatioMode=Qt.KeepAspectRatio)
        self.resize(self.pixmap.width(), self.pixmap.height())
        self.setMouseTracking(True)
        
        original_areas = [(925, 425, 1175, 930)]
        self.areas = []
        for x1, y1, x2, y2 in original_areas:
            self.areas.append((
                int(x1 * scale_factor / 100), int(y1 * scale_factor / 100),
                int(x2 * scale_factor / 100), int(y2 * scale_factor / 100)
            ))
        self.hovered_area_index = -1

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            x, y = pos.x(), pos.y()

            for i, (x1, y1, x2, y2) in enumerate(self.areas):
                if x1 <= x <= x2 and y1 <= y <= y2:
                    # --- ОТКРЫТИЕ VCSDiagnosticApp ---
                    
                    # 1. Получаем координаты
                    cursor_global_pos = QCursor.pos()
                    new_x = cursor_global_pos.x()
                    new_y = self.pos().y()
                    
                    # 2. Создаем экземпляр вашего реального приложения
                    # Важно: QApplication уже запущен в main, поэтому создаем только окно
                    vcs_window = VCSDiagnosticApp()
                    
                    # 3. Устанавливаем позицию
                    vcs_window.move(new_x, new_y)
                    
                    # 4. Показываем окно
                    # Используем show(), а не exec_(), так как это скорее всего QMainWindow
                    vcs_window.show()  
                    return

    # ... (остальные методы mouseMoveEvent и paintEvent без изменений) ...
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
        painter.drawPixmap(0, 0, self.pixmap)
        for i, (x1, y1, x2, y2) in enumerate(self.areas):
            color = QColor(150, 150, 150, 150) if i == self.hovered_area_index else QColor(200, 200, 200, 100)
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x1, y1, x2 - x1, y2 - y1, 10, 10)

# === MAIN ===
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Добавил стиль, как в вашем main.py

    image_path = r"C:\Users\all-sp-p0007133\Documents\test module\pics\Scheme P-6.png"
    scale_factor = 70

    widget = ClickableImageWidget(image_path, scale_factor)
    widget.move(40, 40)
    widget.show()

    sys.exit(app.exec_())