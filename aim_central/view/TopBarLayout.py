from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QPushButton,   
    QHBoxLayout,
)

from PyQt6.QtSvgWidgets import QSvgWidget
from view.TimeWidget import TimeDisplay


class TopBarLayout(QHBoxLayout):
    def __init__(self):
        super().__init__()
        self.features = None

        logo = QSvgWidget("aim_central/AIMlogo.svg")
        logo.setFixedSize(500, 100)
        self.addWidget(logo, alignment=Qt.AlignmentFlag.AlignLeft)

        # Add time display to the top bar
        time_display = TimeDisplay()
        self.addWidget(time_display, alignment=Qt.AlignmentFlag.AlignRight)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #e03333;
                border: none;
                color: #f3f3f3;
                padding: 10px 20px;
                text-align: center;
                font-size: 16px;
                font-weight: bold;
                margin: 4px 2px;
                border-radius: 12px;
            }
        """)

        self.addWidget(self.refresh_button, alignment=Qt.AlignmentFlag.AlignRight)
    

    
    def addFeatures(self, features):
        self.refresh_button.clicked.connect(lambda: features.refreshContainerButtons())
        