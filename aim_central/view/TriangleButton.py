from PyQt6.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPainter, QPolygon, QRegion, QColor, QBrush
from PyQt6.QtCore import QPoint

class TriangleButton(QPushButton):
    def __init__(self, direction,parent=None):
        super().__init__(parent)
        self.setFixedSize(QSize(10, 10))
        # Define the triangle points
        if direction == "left":
            self.points = [QPoint(10, 0), QPoint(10, 10), QPoint(0, 5)]
        elif direction == "right":
            self.points = [QPoint(0, 0), QPoint(0, 10), QPoint(10, 5)]
        
        # Create a mask so only the triangle is clickable
        polygon = QPolygon(self.points)
        self.setMask(QRegion(polygon))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set color and draw
        if self.isDown():
            painter.setBrush(QBrush(QColor("#666666"))) # Pressed color
        elif self.underMouse():
            painter.setBrush(QBrush(QColor("#999999"))) # Hover color
        else:
            painter.setBrush(QBrush(QColor("#bbbbbb"))) # Normal color
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygon(self.points))
    

    def addFeatures(self, features):
        pass
