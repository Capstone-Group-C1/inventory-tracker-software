from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
)

from PyQt6.QtSvgWidgets import QSvgWidget
from aim_central.view.TimeWidget import TimeDisplay


class TopBarLayout(QHBoxLayout):
    def __init__(self):
        super().__init__()

        logo = QSvgWidget("aim_central/AIMlogo.svg")
        logo.setFixedSize(750, 150)
        self.addWidget(logo, alignment=Qt.AlignmentFlag.AlignLeft)

        self.addStretch()

        # Add time display to the top bar
        time_display = TimeDisplay()
        self.addWidget(time_display, alignment=Qt.AlignmentFlag.AlignRight)

        self.addSpacing(20)
        
