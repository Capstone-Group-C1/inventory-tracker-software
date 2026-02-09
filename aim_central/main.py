from PyQt6.QtWidgets import QApplication, QWidget
from view.HomeScreen import MainWindow
from controller.Inventory import Controller
from logic.CentralSystem import CentralSystem
from aim_central.utils.logging import init_logging
from aim_central.utils.config import AIMConfig
# Only needed for access to command line arguments
import sys

# Initialize logging
logger = init_logging()

logger.info("Starting AIM Central System...")

# You need one (and only one) QApplication instance per application.
# Pass in sys.argv to allow command line arguments for your app.
# If you know you won't use command line arguments QApplication([]) works too.
app = QApplication(sys.argv)

model = CentralSystem()
view = MainWindow(model)
controller = Controller(view)

controller.launch(model)


logger.info("AIM Central System launched successfully.")

# Create a Qt widget, which will be our window.
window = view
logger.debug("Main window created.")
window.show()  # IMPORTANT!!!!! Windows are hidden by default.
logger.debug("Main window shown.")

# Start the event loop.
logger.debug("Starting the event loop.")
app.exec()