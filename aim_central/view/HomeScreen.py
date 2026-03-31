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
)

from PyQt6.QtGui import QColor, QPalette
from view.ContainerButton import ContainerButton
from view.ContainerDialog import CustomDialog
from view.CalibrateScreen import CalibrateWindow
from view.GPSSettingsScreen import GPSSettingsWindow 


class Color(QWidget):
    def __init__(self, color):
        super().__init__()
        self.setAutoFillBackground(True)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(color))
        self.setPalette(palette)

class MainWindow(QMainWindow):
    def __init__(self, model):
        super().__init__()
        self.setWindowTitle("Ambulance Inventory Tracker")
        self.resize(800, 600)
        self.container_buttons_list = []
        self.model = model # read only
        self.features = None

        self.calibrateWindow = CalibrateWindow(model)
        self.GPSSettingsWindow = GPSSettingsWindow(model)

        button_action = QAction("GPS Settings", self)
        button_action.triggered.connect(
            lambda: self.toggleGPSWindow(self)
        )


        button_action2 = QAction("Weight Calibration Settings", self)
        button_action2.triggered.connect(
            lambda: self.toggleCalibrateWindow(self)
        )


        menu = self.menuBar()

        file_menu = menu.addMenu("&Menu")
        file_menu.addAction(button_action2)
        file_menu.addSeparator()
        file_menu.addAction(button_action)

        layout1 = QVBoxLayout()
        layout2 = QHBoxLayout()

        num_containers = model.getNumContainers()
        containers_per_row = 5

        if num_containers < 4:
                containers_per_row = num_containers
        elif num_containers % 3 == 0:
            containers_per_row = 3
        elif num_containers % 4 == 0:
            containers_per_row = 4

        for i in range(containers_per_row):
            self.container_buttons_list.append(ContainerButton(i))
            layout2.addWidget(self.container_buttons_list[i])

        layout1.addLayout(layout2)

        if num_containers/containers_per_row >= 2:
            layout1.addSpacing(20)
            layout3 = QHBoxLayout()

            for i in range(containers_per_row, 2*containers_per_row):
                self.container_buttons_list.append(ContainerButton(i))
                layout3.addWidget(self.container_buttons_list[i])

            layout1.addLayout(layout3)
            layout1.addSpacing(20)

        # up to 3 rows, 15 container max support
        if num_containers/containers_per_row >= 3:
            layout1.addSpacing(20)
            layout4 = QHBoxLayout()

            for i in range(2*containers_per_row, 3*containers_per_row):
                self.container_buttons_list.append(ContainerButton(i))
                layout4.addWidget(self.container_buttons_list[i])

            layout1.addLayout(layout4)
            layout1.addSpacing(20)

        widget = QWidget()
        widget.setLayout(layout1)
        self.setCentralWidget(widget)
    
    def updateContainerDisplay(self, containerId, stockLevel):
        color_map = {
            "Green": "#4CAF50",
            "Yellow": "#FFEB3B",
            "Red": "#F44336"
        }
        button = self.container_buttons_list[containerId]
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color_map.get(stockLevel, "#4CAF50")};
                border: none;
                color: white;
                padding: 50px 50px;
                text-align: center;
                font-size: 16px;
                margin: 4px 2px;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background-color: {color_map.get(stockLevel, "#45a049")};
            }}
        """)

    def openContainerDetails(self, container_details):
        dialog = CustomDialog(container_details, self)
        dialog.exec()


    def toggleGPSWindow(self, curWindow):
        curWindow.hide()
        self.GPSSettingsWindow.show()
    
    def toggleCalibrateWindow(self, curWindow):
        curWindow.hide()
        self.calibrateWindow.show()
    
    def toggleHomeWindow(self, curWindow):
        curWindow.hide()
        self.show()


    def addFeatures(self, features):
        self.features = features

        for button in self.container_buttons_list:
            button.addFeatures(features)
        
        self.calibrateWindow.addFeatures(features)
        self.GPSSettingsWindow.addFeatures(features)
        