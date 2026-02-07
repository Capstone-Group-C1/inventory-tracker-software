from PyQt6.QtWidgets import QApplication, QWidget
from view.HomeScreen import MainWindow
from aim_central.controller.Inventory import Controller
from aim_central.logic.CentralSystem import CentralSystem
# Only needed for access to command line arguments
import sys

# You need one (and only one) QApplication instance per application.
# Pass in sys.argv to allow command line arguments for your app.
# If you know you won't use command line arguments QApplication([]) works too.
app = QApplication(sys.argv)

model = CentralSystem()
view = MainWindow(model)
controller = Controller(view)

controller.launch(model)


# Create a Qt widget, which will be our window.
window = view
window.show()  # IMPORTANT!!!!! Windows are hidden by default.

# Start the event loop.
app.exec()