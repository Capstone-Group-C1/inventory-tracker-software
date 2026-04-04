from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel, 
    QGroupBox,  
    QPushButton,
    QVBoxLayout,
    QSizePolicy
)

from aim_central.view.ItemSettingsWidget import ItemSettingsWidget

class ContainerSettingsWidget(QGroupBox):
    def __init__(self, model, container_id, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)  # Fixed width to prevent horizontal scrolling
        self.model = model
        self.item_widgets_list = []

        self.container_id = container_id
        self.container_name = model.getContainerName(container_id)
        self.container_total_weight = model.getContainerWeight(container_id)

        self.widgetLayout = QVBoxLayout()
        self.widgetLayout.setContentsMargins(10, 10, 10, 10)
        self.widgetLayout.setSpacing(0)
        self.setLayout(self.widgetLayout)

        self.setTitle(self.container_name)
        print(f"Title: {self.title()}")

        self.setStyleSheet("""
            QGroupBox {
                background-color: #dddddd;
                border-radius: 8px;
                font-weight: bold;
                font-size: 24px;
                padding-top: 16px;
                margin-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: padding;
                subcontrol-position: top center;
                padding: 10px 10px 10px 10px;
                background-color: transparent;
                font-size: 24px;
            }
            QLabel {
                background-color: transparent;
                padding: 0px;
                margin: 0px;
                font-size: 14px;
            }
        """)

        # self.container_label = QLabel(f"Container {container_id}", self)
        # self.widgetLayout.addWidget(self.container_label)
        # self.container_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)

        self.widgetLayout.addSpacing(15) # space between title and first item

        if container_id != 0: # index 0 is not used, just a placeholder for ease of use with container ids
            for item in model.findContainer(container_id)["items"]:
                item_widget = ItemSettingsWidget(model, item["item_id"])
                self.item_widgets_list.append(item_widget)
                item_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                self.widgetLayout.addWidget(item_widget)
        
            self.widgetLayout.addSpacing(5) # space between last item and weight/tare button
            self.widgetLayout.addStretch() # push weight label and tare button to the bottom
        

            self.container_weight_label = QLabel(f"Container Weight: {round(self.container_total_weight, 1):2f} g", self)
            self.widgetLayout.addWidget(self.container_weight_label)
            self.container_weight_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom)

        self.tare_button = QPushButton("Tare Container")
        self.tare_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: #f3f3f3;
                padding: 5px 10px;
                text-align: center;
                font-size: 20px;
                font-style: bold;
                margin: 4px 2px;
                border-radius: 12px;
            }
            QPushButton::pressed {
                background-color: #3B9E40;
            }
        """)
        self.widgetLayout.addWidget(self.tare_button)
        
        self.widgetLayout.addStretch()

    def addFeatures(self, features):
        self.tare_button.clicked.connect(lambda: features.tareContainer(self.container_id))

        for item_widget in self.item_widgets_list:
            item_widget.addFeatures(features)
