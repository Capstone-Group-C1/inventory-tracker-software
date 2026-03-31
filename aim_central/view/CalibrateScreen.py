from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,    
    QHBoxLayout,
    QVBoxLayout,
    QPushButton
)

class CalibrateWindow(QMainWindow):
    def __init__(self, model):
        super().__init__()
        self.setWindowTitle("Weight Calibration Settings")
        self.resize(800, 600)
        self.container_buttons_list = []
        self.model = model # read only
        self.features = None

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
            QPushButton:pressed {
                background-color: #888888;
            }
        """)

        self.button_action = QAction("Home", self)
        self.button_action2 = QAction("GPS Settings", self)

        menu = self.menuBar()

        file_menu = menu.addMenu("&Menu")
        file_menu.addAction(self.button_action)
        file_menu.addSeparator()
        file_menu.addAction(self.button_action2)

        layout1 = QVBoxLayout()
        layout2 = QHBoxLayout()
        layout3 = QHBoxLayout()


        num_containers = model.getNumContainers()
        containers_per_row = 5

        if num_containers < 4:
                containers_per_row = num_containers
        elif num_containers % 3 == 0:
            containers_per_row = 3
        elif num_containers % 4 == 0:
            containers_per_row = 4

        for i in range(containers_per_row):
            container_button = QPushButton(f"Container {i}\nTare: 0.0 g")
            layout2.addWidget(container_button)

        layout1.addLayout(layout2)

        if num_containers/containers_per_row >= 2:
            layout1.addSpacing(20)
            layout3 = QHBoxLayout()

            for i in range(containers_per_row, 2*containers_per_row):
                container_button = QPushButton(f"Container {i}\nTare: 0.0 g")
                layout3.addWidget(container_button)

            layout1.addLayout(layout3)
            layout1.addSpacing(20)

        # up to 3 rows, 15 container max support
        if num_containers/containers_per_row >= 3:
            layout1.addSpacing(20)
            layout4 = QHBoxLayout()

            for i in range(2*containers_per_row, 3*containers_per_row):
                container_button = QPushButton(f"Container {i}\nTare: 0.0 g")
                layout4.addWidget(container_button)

            layout1.addLayout(layout4)
            layout1.addSpacing(20)


        widget = QWidget()
        widget.setLayout(layout1)
        self.setCentralWidget(widget)

    def addFeatures(self, features):
        self.features = features
        self.button_action.triggered.connect(lambda: self.features.toggleHomeWindow(self))
        self.button_action2.triggered.connect(lambda: self.features.toggleGPSWindow(self))

