from PyQt6.QtWidgets import QApplication, QDialog, QMainWindow, QPushButton
from PyQt6.QtWidgets import QDialogButtonBox, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

class CustomDialog(QDialog):
    def __init__(self, containerDetails, parent=None):
        super().__init__(parent)
        self.id = containerDetails['id']
        self.contents = containerDetails['contents']
        self.neededStock = containerDetails['neededStock']
        self.currentStock = containerDetails['currentStock']
        self.currentWeight = containerDetails['currentWeight']

        self.setWindowTitle(f"Container {self.id} Details")

        QBtn = (QDialogButtonBox.StandardButton.Close)

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Details for Container {self.id}"))
        layout.addWidget(QLabel(f"Item Contents: {self.contents}"))
        layout.addWidget(QLabel(f"Needed Stock: {self.neededStock}"))
        layout.addWidget(QLabel(f"Current Stock: {self.currentStock}"))
        layout.addWidget(QLabel(f"Current Weight: {self.currentWeight} g"))

        layout.addWidget(self.buttonBox)
        self.setLayout(layout)