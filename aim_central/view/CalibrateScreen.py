from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,    
    QHBoxLayout,
    QVBoxLayout,
    QScrollArea,
    QPushButton,
)

from aim_central.view.ContainerSettingsWidget import ContainerSettingsWidget
from aim_central.view.TopBarLayout import TopBarLayout

class CalibrateWindow(QMainWindow):
    def __init__(self, model):
        super().__init__()
        self.setWindowTitle("Weight Calibration Settings")
        self.resize(800, 600)
        self.container_widgets_list = [ContainerSettingsWidget(model, 0)] # 1 indexed for ease of use with container ids, index 0 is not used
        self.row_layouts = []
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

        menu.setStyleSheet("""
            QMenuBar {
                font-size: 24px;
                background-color: #f0f0f0;
            }
            QMenuBar::item {
                spacing: 10px;
                padding: 5px 10px;
                background: transparent;
            }
            QMenu {
                font-size: 22px;
            }
        """)



        file_menu = menu.addMenu("&Menu")
        file_menu.addAction(self.button_action)
        file_menu.addSeparator()
        file_menu.addAction(self.button_action2)

        scroll = QScrollArea()
        container = QWidget()
        mainLayout = QVBoxLayout()
        self.topBarLayout = TopBarLayout("settings")
        row1Containers = QHBoxLayout()

        
        mainLayout.addLayout(self.topBarLayout)

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
            self.container_widgets_list.append(ContainerSettingsWidget(model, i))
            row1Containers.addWidget(self.container_widgets_list[i])

        mainLayout.addLayout(row1Containers)
        self.row_layouts.append(row1Containers)

        if num_containers/containers_per_row >= 1:
            mainLayout.addSpacing(20)
            row2Containers = QHBoxLayout()

            second_row_containers = containers_per_row
            if num_containers < 2*containers_per_row:
                second_row_containers = num_containers - containers_per_row

            for i in range(containers_per_row + 1, containers_per_row + second_row_containers + 1):
                self.container_widgets_list.append(ContainerSettingsWidget(model, i))
                row2Containers.addWidget(self.container_widgets_list[i])

            mainLayout.addLayout(row2Containers)
            self.row_layouts.append(row2Containers)
            mainLayout.addSpacing(20)

        # up to 3 rows, 15 container max support
        if num_containers/containers_per_row >= 2:
            mainLayout.addSpacing(20)
            row3Containers = QHBoxLayout()

            third_row_containers = containers_per_row
            if num_containers < 3*containers_per_row:
                third_row_containers = num_containers - 2*containers_per_row

            for i in range(2*containers_per_row + 1, 2*containers_per_row + third_row_containers + 1):
                self.container_widgets_list.append(ContainerSettingsWidget(model, i))
                row3Containers.addWidget(self.container_widgets_list[i])

            mainLayout.addLayout(row3Containers)
            self.row_layouts.append(row3Containers)
            mainLayout.addSpacing(20)
        

        self.tareAllContainers = QPushButton("Tare All Containers")
        self.tareAllContainers.setFixedHeight(50)
        self.tareAllContainers.setStyleSheet("padding: 10px 20px; font-size: 20px; font-style: bold;")  # Override padding to make text visible
        mainLayout.addWidget(self.tareAllContainers, alignment=Qt.AlignmentFlag.AlignCenter)


        container.setLayout(mainLayout)
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # Disable horizontal scrolling
        self.setCentralWidget(scroll)
    
    def refreshContainerSettings(self):
        num_containers = self.model.getNumContainers()
        for i in range(1, num_containers + 1):
            old_widget = self.container_widgets_list[i]
            new_widget = ContainerSettingsWidget(self.model, i)
            new_widget.addFeatures(self.features)

            # find which row layout contains this widget
            for row_layout in self.row_layouts:
                idx = row_layout.indexOf(old_widget)
                if idx != -1:
                    row_layout.removeWidget(old_widget)
                    old_widget.deleteLater()
                    row_layout.insertWidget(idx, new_widget)
                    break

            self.container_widgets_list[i] = new_widget
            
        #widget = QWidget()
        #widget.setLayout(layout1)
        #self.setCentralWidget(widget)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.showNormal()

    def addFeatures(self, features):
        self.features = features
        self.button_action.triggered.connect(lambda: self.features.toggleHomeWindow(self))
        self.button_action2.triggered.connect(lambda: self.features.toggleGPSWindow(self))
        self.tareAllContainers.clicked.connect(lambda: self.features.tareAllContainers())

        self.topBarLayout.addFeatures(features)
        
        for container_widget in self.container_widgets_list:
            container_widget.addFeatures(features)

