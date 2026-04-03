from PyQt6.QtWidgets import QApplication, QWidget
from aim_central.view.HomeScreen import MainWindow
from aim_central.controller.Inventory import Controller
from aim_central.logic.CentralSystem import CentralSystem
from aim_central.logic.CanDatabaseBridge import CanDatabaseBridge
from aim_central.utils.logger import init_logging
import sys

# Initialize logging
logger = init_logging()

logger.info("Starting AIM Central System...")

app = QApplication(sys.argv)

model = CentralSystem()
model.import_db("aim_central/SimpleSampleCSV.csv")

view = MainWindow(model)
controller = Controller(view)
controller.launch(model)

# Start the CAN bridge directly (geofence removed for demo).
bridge = CanDatabaseBridge(can_channel='can0', bitrate=500000)
bridge.start()
controller.set_bridge(bridge)

logger.info("AIM Central System launched successfully.")

window = view
window.show()

# Qt event loop keeps everything alive; clean up on exit.
exit_code = app.exec()
bridge.stop()
sys.exit(exit_code)
