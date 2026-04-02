from PyQt6.QtWidgets import QApplication, QWidget
from view.HomeScreen import MainWindow
from controller.Inventory import Controller
from logic.CentralSystem import CentralSystem
from logic.CanDatabaseBridge import CanDatabaseBridge
from drivers.gpsDriver import GeofenceMonitor
from utils.logger import init_logging
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

# Create the CAN bridge and wire the geofence to start/stop it.
bridge = CanDatabaseBridge(can_channel='can0', bitrate=500000)
monitor = GeofenceMonitor(on_enter=bridge.start, on_exit=bridge.stop)
monitor.start()
controller.set_bridge(bridge)

logger.info("AIM Central System launched successfully.")

window = view
window.show()

# Qt event loop keeps everything alive; clean up on exit.
exit_code = app.exec()
monitor.stop()
bridge.stop()
sys.exit(exit_code)