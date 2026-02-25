from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLabel,
    QMainWindow,
    QStatusBar,
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

        button_action = QAction("Home", self)
        button_action.triggered.connect(lambda: self.hide())


        button_action2 = QAction("Weight Calibration Settings", self)
        # button_action2.triggered.connect(self.toolbar_button_clicked)

        menu = self.menuBar()

        file_menu = menu.addMenu("&Menu")
        file_menu.addAction(button_action)
        file_menu.addSeparator()
        file_menu.addAction(button_action2)

        layout1 = QVBoxLayout()
        layout1.addWidget(QLabel("GPS Settings"))
        layout1.addSpacing(200)

        widget = QWidget()
        widget.setLayout(layout1)
        self.setCentralWidget(widget)
