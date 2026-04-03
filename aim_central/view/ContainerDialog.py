from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QDialogButtonBox, QVBoxLayout, QLabel

class ContainerDialog(QDialog):
    def __init__(self, containerDetails, parent=None):
        super().__init__(parent)
        self.id = containerDetails['container_id']
        self.contents = containerDetails['items']

        self.setWindowTitle(f"Container {self.id} Details")
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f0f0;  
                border-radius: 10px;
            }
            QLabel {
                font-size: 14px;
                margin: 5px;    
            }
        """)

        QBtn = (QDialogButtonBox.StandardButton.Close)

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()

        title = QLabel(f"Container {self.id} Details")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 15px;")
        layout.addWidget(title)

        for item in self.contents:
            stock_color = "green" if item['stock_level'] > 1 else "#D4B100" if item['stock_level'] == 1 else "#e03333"
            stock_level = "Normal" if item['stock_level'] > 1 else "Low" if item['stock_level'] == 1 else "Empty"

            layout.addWidget(QLabel(f"Item Contents: {item['item_name']}", ))
            layout.addWidget(QLabel(f"Stock Level: <span style='color: {stock_color};'>{stock_level}</span>"))
            layout.addWidget(QLabel(f"Needed Stock: {item['needed_stock']}"))
            layout.addWidget(QLabel(f"Current Stock: {item['current_stock']}"))

            layout.addSpacing(10)

        layout.addWidget(self.buttonBox)
        self.setLayout(layout)