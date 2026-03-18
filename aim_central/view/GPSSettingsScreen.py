from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QToolBar,
    QWidget,    
    QHBoxLayout,
    QVBoxLayout,
    QPushButton
)

class GPSSettingsWindow(QMainWindow):
    def __init__(self, model):
        super().__init__()
        self.setWindowTitle("GPS Settings")
        self.resize(800, 600)
        self.container_buttons_list = []
        self.model = model # read only

        self.setStyleSheet("""
            QPushButton {
                background-color: #999999;
                border: none;
                color: white;
                padding: 50px 50px;
                text-align: center;
                font-size: 16px;
                margin: 4px 2px;
                border-radius: 12px;
            }
        """)

        self.button_action = QAction("Home", self)

        self.button_action2 = QAction("Weight Calibration Settings", self)

        menu = self.menuBar()

        file_menu = menu.addMenu("&Menu")
        file_menu.addAction(self.button_action)
        file_menu.addSeparator()
        file_menu.addAction(self.button_action2)

        layout1 = QVBoxLayout()
        layout1.addWidget(QLabel("GPS Settings"))
        layout1.addSpacing(200)

        widget = QWidget()
        widget.setLayout(layout1)
        self.setCentralWidget(widget)

    def addFeatures(self, features):
            self.features = features
            self.button_action.triggered.connect(lambda: self.features.toggleHomeWindow(self))
            self.button_action2.triggered.connect(lambda: self.features.toggleCalibrateWindow(self))

