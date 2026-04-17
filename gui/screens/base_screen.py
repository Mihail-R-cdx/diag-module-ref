from PyQt5.QtWidgets import QWidget


class BaseScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.colors = parent.colors if parent else None
        self.init_ui()
    
    def init_ui(self):
        raise NotImplementedError
    
    def update_data(self, data):
        raise NotImplementedError
    
    def refresh(self):
        """Обновление данных экрана"""
        pass
