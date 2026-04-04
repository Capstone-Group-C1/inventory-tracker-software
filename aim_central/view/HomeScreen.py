from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,    
    QHBoxLayout,
    QVBoxLayout,
    QToolBar,
    QLabel,
    )

from PyQt6.QtGui import QColor, QPalette
from aim_central.view.ContainerButton import ContainerButton
from aim_central.view.ContainerDialog import ContainerDialog
from aim_central.view.CalibrateScreen import CalibrateWindow
from aim_central.view.GPSSettingsScreen import GPSSettingsWindow 
from aim_central.view.TopBarLayout import TopBarLayout


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
        self.container_buttons_list = [0] # 1 indexed for ease of use with container ids, index 0 is not used
        self.model = model # read only
        self.features = None

        self.calibrateWindow = CalibrateWindow(model)
        self.GPSSettingsWindow = GPSSettingsWindow(model)

        button_action = QAction(QIcon("aim_central/view/settings_black.png"), "settings", self)
        button_action.triggered.connect(
            lambda: self.toggleCalibrateWindow(self)
        )


        button_action2 = QAction(QIcon("aim_central/view/gps_black.png"),"gps", self)
        button_action2.triggered.connect(
            lambda: self.toggleGPSWindow(self)
        )

        toolbar = QToolBar()
        toolbar.setIconSize(QSize(50,50))
        self.addToolBar(toolbar)
        toolbar.addAction(button_action)
        toolbar.addWidget(QLabel("    "))
        toolbar.addAction(button_action2)
        
        widget = QWidget()
        widget.setLayout(self.createLayout())
        self.setCentralWidget(widget)
        self.showFullScreen()

        # Setup timer for auto update every second
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_all)
        self.timer.start(1000)  # Update every 1000ms (1 second)

        self.update_all()  # Initial call

    def update_all(self):
        self.refreshContainerButtons()
        self.refreshContainerSettings()

    
    def createLayout(self):
        mainLayout = QVBoxLayout()
        self.topBarLayout = TopBarLayout()
        row1Containers = QHBoxLayout()

        
        mainLayout.addLayout(self.topBarLayout)
        mainLayout.addSpacing(10)
        mainLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        num_containers = self.model.getNumContainers()
        containers_per_row = 5

        if num_containers < 4:
                containers_per_row = num_containers
        elif num_containers % 3 == 0:
            containers_per_row = 3
        elif num_containers % 4 == 0 or num_containers == 7:
            containers_per_row = 4

        for i in range(1, containers_per_row + 1):
            stock_level = self.model.getContainerStockLevel(i)
            self.container_buttons_list.append(ContainerButton(i, self.model))
            row1Containers.addWidget(self.container_buttons_list[i])

        mainLayout.addLayout(row1Containers)


        if num_containers/containers_per_row >= 1:
            mainLayout.addSpacing(20)
            row2Containers = QHBoxLayout()

            second_row_containers = containers_per_row
            if num_containers < 2*containers_per_row:
                second_row_containers = num_containers - containers_per_row

            for i in range(containers_per_row + 1, containers_per_row + second_row_containers + 1):
                stock_level = self.model.getContainerStockLevel(i)
                self.container_buttons_list.append(ContainerButton(i, self.model))
                row2Containers.addWidget(self.container_buttons_list[i])

            mainLayout.addLayout(row2Containers)
            mainLayout.addSpacing(20)

        # up to 3 rows, 15 container max support
        if num_containers/containers_per_row >= 2:
            mainLayout.addSpacing(20)
            row3Containers = QHBoxLayout()

            third_row_containers = containers_per_row
            if num_containers < 3*containers_per_row:
                third_row_containers = num_containers - 2*containers_per_row

            for i in range(2*containers_per_row + 1, 2*containers_per_row + third_row_containers + 1):
                stock_level = self.model.getContainerStockLevel(i)
                self.container_buttons_list.append(ContainerButton(i, self.model))
                row3Containers.addWidget(self.container_buttons_list[i])

            mainLayout.addLayout(row3Containers)
            mainLayout.addSpacing(20)
        
        return mainLayout


    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.showNormal()
    
    def openContainerDetails(self, container_details):
        dialog = ContainerDialog(container_details, self)
        dialog.exec()

    def toggleGPSWindow(self, curWindow):
        curWindow.hide()
        self.GPSSettingsWindow.showFullScreen()
    
    def toggleCalibrateWindow(self, curWindow):
        curWindow.hide()
        self.calibrateWindow.showFullScreen()
    
    def toggleHomeWindow(self, curWindow):
        curWindow.hide()
        self.show()
        self.showFullScreen()
    
    def refreshContainerButtons(self):
        for button in self.container_buttons_list:
            if button != 0: # index 0 is not used, just a placeholder for ease of use with container ids
                containerId = button.containerId
                stockLevel = self.model.getContainerStockLevel(containerId)
                containerName = self.model.getContainerName(containerId)
                items = self.model.findContainer(containerId)["items"]

                containerText = ""

                if len(items) == 1:
                    containerText = f"{containerName} ({items[0]['current_stock']}/{items[0]['needed_stock']})"

                elif len(items) > 1:
                    containerText = f"{containerName}\n"
                    for item in items:
                        containerText += f"{item['item_name']}: {item['current_stock']}/{item['needed_stock']} \n"

                button.setStockLevel(stockLevel)
                button.setText(containerText)
    
    def refreshContainerSettings(self):
        self.calibrateWindow.refreshContainerSettings()

    def addFeatures(self, features):
        self.features = features
        
        self.calibrateWindow.addFeatures(features)
        self.GPSSettingsWindow.addFeatures(features)
        
