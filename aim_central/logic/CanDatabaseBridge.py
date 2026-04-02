import logging
import threading
import time
from collections import defaultdict, deque

from aim_central.drivers.canDriver import CANDriver, LED_GREEN, LED_RED, LED_YELLOW
from aim_central.logic import DatabaseOperations

# Fraction of item weight used as tolerance when matching a weight delta to an item.
# e.g. 0.15 means a 100g item will match any delta between 85g and 115g.
WEIGHT_MATCH_TOLERANCE = 0.15

# Minimum weight delta (grams) to act on — ignores sub-gram sensor drift.
MIN_DELTA_G = 1.0


class CanDatabaseBridge:
    """
    Bridges incoming CAN sensor data to DB stock updates.

    Flow:
    1) Receive parsed message from CANDriver
    2) Compute weight delta since last stable reading
    3) Match delta to an item weight in the bin within WEIGHT_MATCH_TOLERANCE
    4) Increment or decrement that item's stock via DatabaseOperations
    5) Optionally push stock-level LED feedback to STM32
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
        self._last_stable_weight = {}
        self._stop_event = threading.Event()
        self._thread = None
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
        if stock_level == 0:
            return LED_RED
        if stock_level == 1:
            return LED_YELLOW
        return LED_GREEN

    def _match_item_by_delta(self, bin_id, delta_g):
        """
        Find the item in a bin whose weight best matches abs(delta_g).

        Returns item_id if a match is found within WEIGHT_MATCH_TOLERANCE, else None.
        """
        item_ids = DatabaseOperations.get_item_ids(bin_id)
        if not item_ids:
            return None

        abs_delta = abs(delta_g)
        for item_id in item_ids:
            item_weight = DatabaseOperations.get_item_weight(item_id)
            if item_weight and abs(abs_delta - item_weight) / item_weight <= WEIGHT_MATCH_TOLERANCE:
                return item_id

        return None

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
            # and reset state so stale readings don't carry over once tared.
            self._weight_windows[bin_id].clear()
            self._last_stable_weight.pop(bin_id, None)
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

        # First stable reading for this bin — store as baseline, nothing to diff against yet.
        if bin_id not in self._last_stable_weight:
            self._last_stable_weight[bin_id] = stable_weight_g
            DatabaseOperations.record_sensor_event(
                container_id=bin_id,
                raw_weight_g=weight_g,
                net_weight_g=stable_weight_g,
                sensor_status=status,
                decision="baseline_established",
                note="first stable reading stored as baseline",
            )
            self.logger.info("Bin %s baseline established at %.2fg.", bin_id, stable_weight_g)
            return True

        delta_g = self._last_stable_weight[bin_id] - stable_weight_g
        self._last_stable_weight[bin_id] = stable_weight_g

        if abs(delta_g) < MIN_DELTA_G:
            DatabaseOperations.record_sensor_event(
                container_id=bin_id,
                raw_weight_g=weight_g,
                net_weight_g=stable_weight_g,
                sensor_status=status,
                decision="deferred_no_change",
                note=f"delta={delta_g:.2f}g below {MIN_DELTA_G}g threshold",
            )
            return True

        matched_item_id = self._match_item_by_delta(bin_id, delta_g)

        if matched_item_id is None:
            DatabaseOperations.record_sensor_event(
                container_id=bin_id,
                raw_weight_g=weight_g,
                net_weight_g=stable_weight_g,
                sensor_status=status,
                decision="failed_no_weight_match",
                note=f"delta={delta_g:.2f}g matched no item within {WEIGHT_MATCH_TOLERANCE*100:.0f}% tolerance",
            )
            self.logger.warning(
                "No item weight match for bin=%s delta=%.2fg", bin_id, delta_g
            )
            return True

        # delta_g > 0 means weight dropped (item removed), < 0 means item returned
        change = -1 if delta_g > 0 else 1
        updated = DatabaseOperations.change_stock(matched_item_id, change)

        if not updated:
            DatabaseOperations.record_sensor_event(
                container_id=bin_id,
                raw_weight_g=weight_g,
                sensor_status=status,
                decision="failed_update",
                note="change_stock returned False",
            )
            self.logger.error(
                "Failed stock sync for bin=%s delta=%.2fg", bin_id, delta_g
            )
            return True

        DatabaseOperations.record_sensor_event(
            container_id=bin_id,
            raw_weight_g=weight_g,
            net_weight_g=stable_weight_g,
            computed_stock=DatabaseOperations.get_stock(matched_item_id),
            sensor_status=status,
            decision="accepted",
            note=f"delta={delta_g:.2f}g matched item_id={matched_item_id} change={change:+d}",
        )
        self.logger.info(
            "Stock synced: bin=%s item_id=%s delta=%.2fg change=%+d",
            bin_id, matched_item_id, delta_g, change,
        )

        if self.publish_led_feedback:
            stock_level = DatabaseOperations.get_stock_level(matched_item_id)
            led = self._stock_level_to_led(stock_level)
            self.driver.set_led(bin_id=bin_id, state=led)

        return True

    def tare_all_containers(self):
        """
        Sends a tare command to every container currently in the database.
        Should be called after bins have been restocked.
        """
        container_ids = DatabaseOperations.get_all_container_ids()
        for container_id in container_ids:
            self.driver.tare_bin(bin_id=container_id)
            self._weight_windows[container_id].clear()
            self._last_stable_weight.pop(container_id, None)
            self.logger.info("Tare command sent to bin %s.", container_id)

    def start(self, timeout=1.0, idle_sleep_s=0.05):
        """
        Start the CAN polling loop in a background thread.
        Called by the geofence monitor when the ambulance arrives at base.
        """
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, args=(timeout, idle_sleep_s), daemon=True
        )
        self._thread.start()
        self.logger.info("CAN-DB bridge started.")

    def stop(self):
        """
        Stop the CAN polling loop.
        Called by the geofence monitor when the ambulance leaves base.
        """
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        self.driver.disconnect()
        self.logger.info("CAN-DB bridge stopped.")

    def _run(self, timeout=1.0, idle_sleep_s=0.05):
        DatabaseOperations.database_init()
        self.driver.connect()

        self.logger.info("CAN polling loop running.")
        while not self._stop_event.is_set():
            processed = self.process_one_message(timeout=timeout)
            if not processed:
                time.sleep(idle_sleep_s)


def main():
    from aim_central.drivers.gpsDriver import GeofenceMonitor

    logging.basicConfig(level=logging.INFO)

    bridge = CanDatabaseBridge(can_channel='can0', bitrate=500000)

    monitor = GeofenceMonitor(
        on_enter=bridge.start,
        on_exit=bridge.stop,
    )
    monitor.start()

    # Keep the main thread alive — bridge and monitor run in background threads.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()
        bridge.stop()


if __name__ == "__main__":
    main()
