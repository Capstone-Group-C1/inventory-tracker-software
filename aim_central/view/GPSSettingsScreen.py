from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QLabel,
    QMainWindow,
    QWidget,    
    QVBoxLayout,
)

from view.TopBarLayout import TopBarLayout

class GPSSettingsWindow(QMainWindow):
    def __init__(self, model):
        super().__init__()
        self.setWindowTitle("GPS Settings")
        self.resize(800, 600)
        self.container_buttons_list = []
        self.model = model # read only

        self.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
            }
        """)

        self.button_action = QAction("Home", self)

        self.button_action2 = QAction("Weight Calibration Settings", self)

        menu = self.menuBar()

        file_menu = menu.addMenu("&Menu")
        file_menu.addAction(self.button_action)
        file_menu.addSeparator()
        file_menu.addAction(self.button_action2)

        mainLayout = QVBoxLayout()
        self.topBarLayout = TopBarLayout("gps")

        
        mainLayout.addLayout(self.topBarLayout)
        mainLayout.addSpacing(50)
        mainLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        mainLayout.addWidget(QLabel("GPS Settings Not Currently Available"), alignment=Qt.AlignmentFlag.AlignTop)
        mainLayout.addSpacing(200)

        widget = QWidget()
        widget.setLayout(mainLayout)
        self.setCentralWidget(widget)

    def addFeatures(self, features):
            self.features = features
            self.button_action.triggered.connect(lambda: self.features.toggleHomeWindow(self))
            self.button_action2.triggered.connect(lambda: self.features.toggleCalibrateWindow(self))

            self.topBarLayout.addFeatures(features)

