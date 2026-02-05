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

class ContainerButton(QPushButton):
    def __init__(self, containerId, parent=None):
        super().__init__("", parent)
        self.containerId = containerId
        self.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 50px 50px;
                text-align: center;
                font-size: 16px;
                margin: 4px 2px;
                border-radius: 12px;
            }
        """)

    def addFeatures(self, features):
        self.clicked.connect(lambda: features.ContainerButtonClick(self.containerId))