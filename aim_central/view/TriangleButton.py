from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QPolygon, QPainter, QRegion, QColor, QBrush

class TriangleButton(QPushButton):
    def __init__(self, direction="up", parent=None):
        super().__init__(parent)
        self.direction = direction
        self.setFixedSize(30, 30)  # Set to 50x50 max

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Define the three points of the triangle based on direction
        size = self.size()
        if self.direction == "up":
            p1 = QPoint(size.width() // 2, 0)
            p2 = QPoint(0, size.height())
            p3 = QPoint(size.width(), size.height())
        elif self.direction == "down":
            p1 = QPoint(0, 0)
            p2 = QPoint(size.width(), 0)
            p3 = QPoint(size.width() // 2, size.height())
        else:
            # Default to up
            p1 = QPoint(size.width() // 2, 0)
            p2 = QPoint(0, size.height())
            p3 = QPoint(size.width(), size.height())
        
        polygon = QPolygon([p1, p2, p3])
        
        # Create a region based on the polygon to set the mask
        self.setMask(QRegion(polygon))
        
        # Customize colors
        painter.setBrush(QBrush(QColor("#4CAF50")))
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Draw the triangle
        painter.drawPolygon(polygon)