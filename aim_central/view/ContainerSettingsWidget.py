from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction, QIcon
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
from PyQt6.QtWidgets import QWidget

class ContainerSettingsWidget(QPushButton):
    def __init__(self, model, container_id, parent=None):
        super().__init__("", parent)
        self.model = model
        self.container_id = container_id

        color_map = {
            "Green": "#4CAF50",
            "Yellow": "#EAC225",
            "Red": "#e03333"
        }

        stock_color = "Green"
        if stockLevel < 2:
            if stockLevel == 0:
                stock_color = "Red"
            else:                
                stock_color = "Yellow"

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color_map.get(stock_color, "#4CAF50")};
                border: none;
                color: white;
                padding: 50px 50px;
                text-align: center;
                font-size: 16px;
                margin: 4px 2px;
                border-radius: 12px;
            }}
        """)

    def addFeatures(self, features):
        self.clicked.connect(lambda: features.ContainerButtonClick(self.containerId))