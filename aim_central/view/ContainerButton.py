from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QPushButton,
    QLabel,
    QVBoxLayout
)


class ContainerButton(QPushButton):
    def __init__(self, containerId, containerText, stockLevel, parent=None):
        super().__init__("", parent)
        self.containerId = containerId
        self.stockLevel = stockLevel
        self.containerText = containerText

        self.setStockLevel(self.stockLevel)

        self.setFixedHeight(250)

        # Create label for text with wrapping
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        self.setContainerText(self.containerText)

        # Create layout and add label
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)


    def setStockLevel(self, newStockLevel):
        color_map = {
            "Green": "#4CAF50",
            "Yellow": "#D8B010",
            "Red": "#e03333"
        }

        self.stockLevel = newStockLevel

        stock_color = "Green"
        if newStockLevel < 2:
            if newStockLevel == 0:
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
                font-size: 24px;
                font-weight: bold;
                margin: 4px 2px;
                border-radius: 12px;
            }}
        """)

    def setContainerText(self, containerText):
        self.label.setText(containerText)
