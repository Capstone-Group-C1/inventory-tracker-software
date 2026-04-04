from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QWidget,    
    QHBoxLayout,
    QVBoxLayout,
    QSpinBox,
)

from PyQt6.QtWidgets import QWidget, QSizePolicy
from aim_central.view.TriangleButton import TriangleButton

class ItemSettingsWidget(QWidget):
    def __init__(self, model, item_id, parent=None):
        super().__init__(parent)
        self.model = model
        self.item_id = item_id
        self.stock_level = model.getStockLevel(item_id)
        self.info = model.findItem(item_id)

        stock_color = "green" if self.stock_level > 1 else "#D8B010" if self.stock_level == 1 else "#e03333"
        stock_level = "Normal" if self.stock_level > 1 else "Low" if self.stock_level == 1 else "Empty"

        # Create layout for the widget
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0) # take out for more space btwn items
        layout.setSpacing(0)
        self.setStyleSheet("background-color: transparent;")
        self.setLayout(layout)
        

        self.label = QLabel(f"""Item: {self.info['item_name']}<br>Item Weight: {self.info['item_weight']} g<br>Stock Level: <span style='color: {stock_color};'>{stock_level}</span><br>Manual Stock Adjust:""")
        self.label.setWordWrap(True)
        self.label.setStyleSheet("padding: 4px; margin: 0px; background-color: transparent; font-size: 20px;")
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        changeStockLayout = QHBoxLayout()
        changeStockLayout.setContentsMargins(0, 0, 0, 0)
        changeStockLayout.setSpacing(4)
        changeStockLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.decreaseStockButton = TriangleButton("down")
        changeStockLayout.addStretch(1)
        changeStockLayout.addWidget(self.decreaseStockButton, alignment=Qt.AlignmentFlag.AlignVCenter)

        stockLabel = QLabel(f"{self.info['current_stock']} / {self.info['needed_stock']}")
        stockLabel.setStyleSheet("font-size: 20px; margin: 0px; padding: 0px;")
        stockLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stockLabel.setContentsMargins(10, 10, 10, 10)
        changeStockLayout.addWidget(stockLabel)

        self.increaseStockButton = TriangleButton("up")
        changeStockLayout.addWidget(self.increaseStockButton, alignment=Qt.AlignmentFlag.AlignVCenter)
        changeStockLayout.addStretch(1)

        layout.addLayout(changeStockLayout)


        # Ensure widget expands to fill available space
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)


    def addFeatures(self, features):
        self.decreaseStockButton.clicked.connect(lambda: features.manualStockChange(self.item_id, -1))
        self.increaseStockButton.clicked.connect(lambda: features.manualStockChange(self.item_id, 1))

