from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,    
    QHBoxLayout,
    QVBoxLayout,
)

from PyQt6.QtGui import QColor, QPalette
from view.ContainerButton import ContainerButton
from view.ContainerDialog import ContainerDialog
from view.CalibrateScreen import CalibrateWindow
from view.GPSSettingsScreen import GPSSettingsWindow 
from view.TopBarLayout import TopBarLayout


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
        self.container_buttons_list = [ContainerButton(0, 2)] # 1 indexed for ease of use with container ids, index 0 is not used
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

        mainLayout = QVBoxLayout()
        self.topBarLayout = TopBarLayout("home")
        row1Containers = QHBoxLayout()

        
        mainLayout.addLayout(self.topBarLayout)
        mainLayout.addSpacing(50)
        mainLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        num_containers = model.getNumContainers()
        containers_per_row = 5

        if num_containers < 4:
                containers_per_row = num_containers
        elif num_containers % 3 == 0:
            containers_per_row = 3
        elif num_containers % 4 == 0 or num_containers == 7:
            containers_per_row = 4

        for i in range(1, containers_per_row + 1):
            stock_level = model.getContainerStockLevel(i)
            self.container_buttons_list.append(ContainerButton(i, stock_level))
            row1Containers.addWidget(self.container_buttons_list[i])

        mainLayout.addLayout(row1Containers)

        if num_containers/containers_per_row >= 1:
            mainLayout.addSpacing(20)
            row2Containers = QHBoxLayout()

            if num_containers < 2*containers_per_row:
                second_row_containers = num_containers - containers_per_row

            for i in range(containers_per_row + 1, containers_per_row + second_row_containers + 1):
                stock_level = model.getContainerStockLevel(i)
                self.container_buttons_list.append(ContainerButton(i, stock_level))
                row2Containers.addWidget(self.container_buttons_list[i])

            mainLayout.addLayout(row2Containers)
            mainLayout.addSpacing(20)

        # up to 3 rows, 15 container max support
        if num_containers/containers_per_row >= 2:
            mainLayout.addSpacing(20)
            row3Containers = QHBoxLayout()

            if num_containers < 3*containers_per_row:
                third_row_containers = num_containers - 2*containers_per_row

            for i in range(2*containers_per_row + 1, 2*containers_per_row + third_row_containers + 1):
                stock_level = model.getContainerStockLevel(i)
                self.container_buttons_list.append(ContainerButton(i, stock_level))
                row3Containers.addWidget(self.container_buttons_list[i])

            mainLayout.addLayout(row3Containers)
            mainLayout.addSpacing(20)

        widget = QWidget()
        widget.setLayout(mainLayout)
        self.setCentralWidget(widget)
    
    def updateContainerDisplay(self, containerId, stockLevel):
        color_map = {
            "Green": "#4CAF50",
            "Yellow": "#EAC225",
            "Red": "#e03333"
        }

        stock_color = "Green"
        if stockLevel < 2:
            if stockLevel == 0:
                stock_color = "Red"
            else:                
                stock_color = "Yellow"
    
        button = self.container_buttons_list[containerId]
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color_map.get(stock_color, "#4CAF50")};
                border: none;
                color: white;
                padding: 50px 50px;
                text-align: center;
                font-size: 16px;
                margin: 4px 2px;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background-color: {color_map.get(stock_color, "#45a049")};
            }}
        """)

    def openContainerDetails(self, container_details):
        dialog = ContainerDialog(container_details, self)
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
    
    def refreshContainerButtons(self):
        for button in self.container_buttons_list:
            containerId = button.containerId
            stockLevel = self.model.getContainerStockLevel(containerId)
            button.stockLevel = stockLevel
            self.updateContainerDisplay(containerId, stockLevel)
    
    def refreshContainerSettings(self):
        self.calibrateWindow.refreshContainerSettings()

    def addFeatures(self, features):
        self.features = features

        for button in self.container_buttons_list:
            button.addFeatures(features)
        
        self.topBarLayout.addFeatures(features)
        self.calibrateWindow.addFeatures(features)
        self.GPSSettingsWindow.addFeatures(features)
        