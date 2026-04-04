from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QLabel,
    QMainWindow,
    QWidget,    
    QVBoxLayout,
    QToolBar,
)

from aim_central.view.TopBarLayout import TopBarLayout

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

        self.button_action = QAction(QIcon("aim_central/view/home_black.png"), "home", self)
        self.button_action2 = QAction(QIcon("aim_central/view/settings_black.png"),"settings", self)


        toolbar = QToolBar()
        toolbar.setIconSize(QSize(50,50))
        self.addToolBar(toolbar)
        toolbar.addAction(self.button_action)
        toolbar.addWidget(QLabel("    "))
        toolbar.addAction(self.button_action2)


        mainLayout = QVBoxLayout()
        self.topBarLayout = TopBarLayout()

        
        mainLayout.addLayout(self.topBarLayout)
        mainLayout.addSpacing(50)
        mainLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        mainLayout.addWidget(QLabel("GPS Settings Not Currently Available"), alignment=Qt.AlignmentFlag.AlignTop)
        mainLayout.addSpacing(200)

        widget = QWidget()
        widget.setLayout(mainLayout)
        self.setCentralWidget(widget)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.showNormal()

    def addFeatures(self, features):
            self.features = features
            self.button_action.triggered.connect(lambda: self.features.toggleHomeWindow(self))
            self.button_action2.triggered.connect(lambda: self.features.toggleCalibrateWindow(self))

