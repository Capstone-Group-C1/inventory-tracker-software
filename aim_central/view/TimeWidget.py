import sys
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import QTimer, QTime, Qt

class TimeDisplay(QLabel):
    def __init__(self):
        super().__init__()
 
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("font-size: 20px; font-weight: bold;")

        # Setup timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)  # Update every 1000ms (1 second)

        self.update_time()  # Initial call

    def update_time(self):
        # Get current time and format as HH:MM:SS
        current_time = QTime.currentTime().toString("HH:mm:ss")
        self.setText(current_time)
