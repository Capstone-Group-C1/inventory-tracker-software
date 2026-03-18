import logging
import time

from aim_central.drivers.canDriver import CANDriver, LED_GREEN, LED_RED, LED_YELLOW
from aim_central.logic import DatabaseOperations


class CanDatabaseBridge:
    """
    Bridges incoming CAN sensor data to DB stock updates.

    Flow:
    1) Receive parsed message from CANDriver
    2) Convert measured weight to stock count via DatabaseOperations
    3) Optionally push stock-level LED feedback to STM32
    """

    def __init__(self, can_channel='can0', bitrate=500000, publish_led_feedback=True):
        self.driver = CANDriver(channel=can_channel, bitrate=bitrate)
        self.publish_led_feedback = publish_led_feedback
        self.logger = logging.getLogger("CanDatabaseBridge")

    def _stock_level_to_led(self, stock_level):
        if stock_level == "Red":
            return LED_RED
        if stock_level == "Yellow":
            return LED_YELLOW
        return LED_GREEN

    def process_one_message(self, timeout=1.0):
        """
        Process exactly one CAN message and sync DB state.

        Returns:
            True if a message was processed, False otherwise.
        """
        msg = self.driver.receive(timeout=timeout)
        if msg is None:
            return False

        bin_id = msg["bin_id"]
        weight_g = msg["weight_g"]
        status = msg["status"]

        if status != "ok":
            self.logger.warning(
                "Skipping DB update for bin %s due to status=%s",
                bin_id,
                status,
            )
            return True

        updated = DatabaseOperations.update_stock_from_weight(
            container_id=bin_id,
            measured_weight_g=weight_g,
        )

        if not updated:
            self.logger.error(
                "Failed stock sync for bin=%s weight_g=%s",
                bin_id,
                weight_g,
            )
            return True

        self.logger.info("Stock synced: bin=%s weight_g=%s", bin_id, weight_g)

        if self.publish_led_feedback:
            stock_level = DatabaseOperations.get_stock_level(bin_id)
            led = self._stock_level_to_led(stock_level)
            self.driver.set_led(bin_id=bin_id, state=led)

        return True

    def run_forever(self, timeout=1.0, idle_sleep_s=0.05):
        """
        Run polling loop for Raspberry Pi service usage.
        """
        DatabaseOperations.database_init()

        with self.driver:
            self.logger.info("CAN-DB bridge started.")
            while True:
                processed = self.process_one_message(timeout=timeout)
                if not processed:
                    time.sleep(idle_sleep_s)


def main():
    logging.basicConfig(level=logging.INFO)
    bridge = CanDatabaseBridge(can_channel='can0', bitrate=500000)
    bridge.run_forever()


if __name__ == "__main__":
    main()
