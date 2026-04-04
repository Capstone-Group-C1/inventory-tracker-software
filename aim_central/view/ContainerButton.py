from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QPushButton,
    QLabel,
    QVBoxLayout
)


class ContainerButton(QPushButton):
    def __init__(self, containerId, model, parent=None):
        super().__init__("", parent)
        self.containerId = containerId
        self.model = model
        self.containerName = model.getContainerName(containerId)
        self.items = model.findContainer(containerId)["items"]
        self.stockLevel = model.getContainerStockLevel(containerId)

        color_map = {
            "Green": "#4CAF50",
            "Yellow": "#D8B010",
            "Red": "#e03333"
        }

        stock_color = "Green"
        if self.stockLevel < 2:
            if self.stockLevel == 0:
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

        self.setFixedHeight(250)

        # Create label for text with wrapping
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")

        # Create layout and add label
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

        if len(self.items) == 1:
            button_text = f"{self.containerName} ({self.items[0]['current_stock']}/{self.items[0]['needed_stock']})"
            self.label.setText(button_text)

        elif len(self.items) > 1:
            button_text = f"{self.containerName}\n"
            for item in self.model.findContainer(self.containerId)["items"]:
                button_text += f"{item['item_name']}: {item['current_stock']}/{item['needed_stock']} \n"
            self.label.setText(button_text)
