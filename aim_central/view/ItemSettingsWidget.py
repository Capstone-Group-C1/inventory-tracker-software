from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QWidget,    
    QHBoxLayout,
    QVBoxLayout,
    QSpinBox,
)

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
        layout.setContentsMargins(0, 0, 0, 0) # take out for more space btwn items
        layout.setSpacing(0)
        self.setStyleSheet("background-color: transparent;")
        self.setLayout(layout)
        

        self.label = QLabel(f"""Item: {self.info['item_name']}<br>Item Id: {self.info['item_id']}<br>Item Weight: {self.info['item_weight']} g<br>Stock Level: <span style='color: {stock_color};'>{stock_level}</span>""")
        self.label.setWordWrap(True)
        self.label.setStyleSheet("padding: 4px; margin: 0px; background-color: transparent; font-size: 20px;")
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        changeStockLayout = QHBoxLayout()
        changeStockLayout.setContentsMargins(0,0,0,0)
        changeStockLayout.setSpacing(0)
        stockLabel = QLabel(f"Manual Stock Adjust: ")
        stockLabel.setStyleSheet("font-size: 20px")
        changeStockLayout.addWidget(stockLabel)

        self.incrementer = QSpinBox()
        self.incrementer.setRange(0, 20)
        self.incrementer.setValue(self.info['current_stock'])
        self.incrementer.setStyleSheet("font-size: 20px")
        changeStockLayout.addWidget(self.incrementer)
        layout.addLayout(changeStockLayout)


        # Ensure widget expands to fill available space
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)


    def addFeatures(self, features):
        self.incrementer.valueChanged.connect(lambda: features.manualStockChange(self.item_id, self.incrementer.value()))
