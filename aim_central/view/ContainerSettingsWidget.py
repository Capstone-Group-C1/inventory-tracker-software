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
    QSizePolicy
)

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QWidget

from view.ItemSettingsWidget import ItemSettingsWidget

class ContainerSettingsWidget(QWidget):
    def __init__(self, model, container_id, parent=None):
        super().__init__(parent)
        self.model = model
        self.container_id = container_id
        self.container_total_weight = model.getContainerWeight(container_id)

        self.widgetLayout = QVBoxLayout()
        self.widgetLayout.setContentsMargins(10, 10, 10, 10)
        self.widgetLayout.setSpacing(8)
        self.setLayout(self.widgetLayout)

        # Set continuous grey background for the entire widget
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#dddddd"))
        self.setPalette(palette)
        self.setStyleSheet("""
            QLabel {
                background-color: transparent;
            }
            ItemSettingsWidget {
                margin: 4px;
            }
        """)

        self.container_label = QLabel(f"Container {container_id}", self)
        self.widgetLayout.addWidget(self.container_label)
        self.container_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)

        if container_id != 0: # index 0 is not used, just a placeholder for ease of use with container ids
            for item in model.findContainer(container_id)["items"]:
                item_widget = ItemSettingsWidget(model, item["item_id"])
                item_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                self.widgetLayout.addWidget(item_widget)
        
        
        self.container_weight_label = QLabel(f"Container Weight: {self.container_total_weight} g", self)
        self.widgetLayout.addWidget(self.container_weight_label)
        self.container_weight_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom)
        
        self.widgetLayout.addStretch()


    def addFeatures(self, features):
        pass