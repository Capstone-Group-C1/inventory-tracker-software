from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction, QIcon, QBrush
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLabel,
    QMainWindow,
    QStatusBar,
    QToolBar,
    QWidget,    
    QHBoxLayout,
    QVBoxLayout,
    QPushButton
)

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QWidget, QSizePolicy

class ItemSettingsWidget(QWidget):
    def __init__(self, model, item_id, parent=None):
        super().__init__(parent)
        self.model = model
        self.item_id = item_id
        self.stock_level = model.getStockLevel(item_id)
        self.info = model.findItem(item_id)

        stock_color = "green" if self.stock_level > 1 else "#D4B100" if self.stock_level == 1 else "#e03333"
        stock_level = "Normal" if self.stock_level > 1 else "Low" if self.stock_level == 1 else "Empty"

        # Create layout for the widget
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        self.setAutoFillBackground(False)
        self.setStyleSheet("")
        
        # Make palette transparent so parent background shows through
        palette = self.palette()
        palette.setBrush(QPalette.ColorRole.Window, QBrush(Qt.GlobalColor.transparent))
        self.setPalette(palette)

        self.label = QLabel(f"""Item: {self.info['item_name']}<br>Item Id: {self.info['item_id']}<br>Item Weight: {self.info['item_weight']} g<br>Stock Level: <span style='color: {stock_color};'>{stock_level}</span>""")
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        # Ensure widget expands to fill available space
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)


    def addFeatures(self, features):
        pass