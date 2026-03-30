import logging
import time
from collections import defaultdict, deque

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

    def __init__(
        self,
        can_channel='can0',
        bitrate=500000,
        publish_led_feedback=True,
        stability_window=3,
        stability_tolerance_g=2.0,
    ):
        self.driver = CANDriver(channel=can_channel, bitrate=bitrate)
        self.publish_led_feedback = publish_led_feedback
        self.stability_window = max(1, int(stability_window))
        self.stability_tolerance_g = float(stability_tolerance_g)
        self._weight_windows = defaultdict(lambda: deque(maxlen=self.stability_window))
        self.logger = logging.getLogger("CanDatabaseBridge")

    def _stable_weight(self, bin_id, latest_weight_g):
        """
        Return a stable weight average only when recent samples are consistent.

        Returns None while collecting samples or when the window is unstable.
        """
        window = self._weight_windows[bin_id]
        window.append(float(latest_weight_g))

        if len(window) < self.stability_window:
            return None

        spread = max(window) - min(window)
        if spread > self.stability_tolerance_g:
            return None

        return sum(window) / len(window)


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
        tare_flag = msg["tare_flag"]

        if status == "not_tared":
            # Bin has not been tared since boot — hold off on all DB writes
            # and clear the stability window so stale readings don't carry over
            # once the STM32 is eventually tared.
            self._weight_windows[bin_id].clear()
            DatabaseOperations.record_sensor_event(
                container_id=bin_id,
                raw_weight_g=weight_g,
                sensor_status=status,
                decision="rejected_not_tared",
                note="bin not tared since boot — DB update withheld",
            )
            self.logger.warning("Bin %s is not tared — holding off DB updates.", bin_id)
            return True

        if status == "error":
            DatabaseOperations.record_sensor_event(
                container_id=bin_id,
                raw_weight_g=weight_g,
                sensor_status=status,
                decision="rejected_error",
                note="sensor reported hardware error",
            )
            self.logger.warning("Bin %s reported sensor error — skipping.", bin_id)
            return True

        if tare_flag == "success":
            # STM32 just confirmed a tare completed — reset the stability window
            # so we start fresh from a clean baseline.
            self._weight_windows[bin_id].clear()
            DatabaseOperations.record_sensor_event(
                container_id=bin_id,
                raw_weight_g=weight_g,
                sensor_status=status,
                decision="tare_confirmed",
                note="tare success acknowledged — stability window reset",
            )
            self.logger.info("Bin %s tare confirmed — stability window reset.", bin_id)
            return True

        stable_weight_g = self._stable_weight(bin_id, weight_g)
        if stable_weight_g is None:
            DatabaseOperations.record_sensor_event(
                container_id=bin_id,
                raw_weight_g=weight_g,
                sensor_status=status,
                decision="deferred_unstable",
                note="collecting stability window or spread too high",
            )
            return True

        updated = DatabaseOperations.update_stock_from_weight(
            container_id=bin_id,
            measured_weight_g=stable_weight_g,
        )

        if not updated:
            DatabaseOperations.record_sensor_event(
                container_id=bin_id,
                raw_weight_g=weight_g,
                sensor_status=status,
                decision="failed_update",
                note="update_stock_from_weight returned False",
            )
            self.logger.error(
                "Failed stock sync for bin=%s weight_g=%s",
                bin_id,
                weight_g,
            )
            return True

        DatabaseOperations.record_sensor_event(
            container_id=bin_id,
            raw_weight_g=weight_g,
            net_weight_g=stable_weight_g,
            computed_stock=DatabaseOperations.get_stock(bin_id),
            sensor_status=status,
            decision="accepted",
            note=f"stable window={self.stability_window}",
        )

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
