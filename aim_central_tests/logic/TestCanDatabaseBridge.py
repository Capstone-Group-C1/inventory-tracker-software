import os
import sys
from unittest.mock import MagicMock, call, patch

import pytest

# Skip this test module cleanly if python-can is not installed.
pytest.importorskip("can")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from aim_central.logic.CanDatabaseBridge import CanDatabaseBridge, WEIGHT_MATCH_TOLERANCE, MIN_DELTA_G, LED_YELLOW, LED_GREEN, LED_RED


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_bridge(stability_window=1, publish_led_feedback=False):
    """Create a CanDatabaseBridge with a mocked CANDriver."""
    mock_driver = MagicMock()
    with patch("aim_central.logic.CanDatabaseBridge.CANDriver", return_value=mock_driver):
        bridge = CanDatabaseBridge(
            publish_led_feedback=publish_led_feedback,
            stability_window=stability_window,
        )
    bridge._mock_driver = mock_driver
    return bridge


def make_msg(bin_id=1, weight_g=100.0, status="ok", tare_flag="none"):
    return {"bin_id": bin_id, "weight_g": weight_g, "status": status, "tare_flag": tare_flag}


# ---------------------------------------------------------------------------
# No message
# ---------------------------------------------------------------------------

class TestNoMessage:
    def test_returns_false_when_no_message(self):
        bridge = make_bridge()
        bridge._mock_driver.receive.return_value = None

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event"):
            assert bridge.process_one_message(timeout=0.1) is False


# ---------------------------------------------------------------------------
# Sensor error / not tared
# ---------------------------------------------------------------------------

class TestSensorError:
    def test_skips_db_and_led_on_error(self):
        bridge = make_bridge()
        bridge._mock_driver.receive.return_value = make_msg(status="error")

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.change_stock") as mock_cs:
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event"):
                assert bridge.process_one_message(timeout=0.1) is True

        mock_cs.assert_not_called()
        bridge._mock_driver.set_led.assert_not_called()


class TestNotTared:
    def test_clears_stability_window_and_last_stable_weight(self):
        bridge = make_bridge(stability_window=3)
        bridge._mock_driver.receive.return_value = make_msg(bin_id=1, weight_g=100.0)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event"):
            # Pre-fill window and set a baseline
            bridge.process_one_message()
            bridge.process_one_message()
            bridge._last_stable_weight[1] = 100.0
            assert len(bridge._weight_windows[1]) == 2

            # Now receive not_tared
            bridge._mock_driver.receive.return_value = make_msg(bin_id=1, status="not_tared")
            bridge.process_one_message()

        assert len(bridge._weight_windows[1]) == 0
        assert 1 not in bridge._last_stable_weight

    def test_no_stock_change_on_not_tared(self):
        bridge = make_bridge()
        bridge._mock_driver.receive.return_value = make_msg(status="not_tared")

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.change_stock") as mock_cs:
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event"):
                bridge.process_one_message()

        mock_cs.assert_not_called()


# ---------------------------------------------------------------------------
# Stability window
# ---------------------------------------------------------------------------

class TestStabilityWindow:
    def test_defers_until_window_full(self):
        bridge = make_bridge(stability_window=3)
        bridge._mock_driver.receive.return_value = make_msg(weight_g=100.0)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.change_stock") as mock_cs:
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event"):
                bridge.process_one_message()
                bridge.process_one_message()
                mock_cs.assert_not_called()

    def test_restarts_collection_after_not_tared(self):
        bridge = make_bridge(stability_window=2)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.change_stock") as mock_cs:
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event"):
                with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_item_ids", return_value=[]):
                    # Fill one reading, then interrupt with not_tared
                    bridge._mock_driver.receive.return_value = make_msg(weight_g=100.0)
                    bridge.process_one_message()

                    bridge._mock_driver.receive.return_value = make_msg(status="not_tared")
                    bridge.process_one_message()

                    # One ok reading — window only has 1 sample, not enough
                    bridge._mock_driver.receive.return_value = make_msg(weight_g=100.0)
                    bridge.process_one_message()
                    mock_cs.assert_not_called()


# ---------------------------------------------------------------------------
# Baseline establishment
# ---------------------------------------------------------------------------

class TestBaseline:
    def test_first_stable_reading_stored_as_baseline(self):
        bridge = make_bridge(stability_window=1)
        bridge._mock_driver.receive.return_value = make_msg(bin_id=1, weight_g=200.0)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.change_stock") as mock_cs:
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event"):
                bridge.process_one_message()

        assert bridge._last_stable_weight[1] == pytest.approx(200.0)
        mock_cs.assert_not_called()

    def test_second_stable_reading_triggers_delta_check(self):
        bridge = make_bridge(stability_window=1)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event"):
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_item_ids", return_value=[]) as mock_ids:
                # First reading → baseline
                bridge._mock_driver.receive.return_value = make_msg(weight_g=200.0)
                bridge.process_one_message()
                mock_ids.assert_not_called()

                # Second reading → delta computed, get_item_ids called
                bridge._mock_driver.receive.return_value = make_msg(weight_g=150.0)
                bridge.process_one_message()
                mock_ids.assert_called_once()


# ---------------------------------------------------------------------------
# Delta below threshold
# ---------------------------------------------------------------------------

class TestDeltaThreshold:
    def test_no_action_when_delta_below_min(self):
        bridge = make_bridge(stability_window=1)
        bridge._last_stable_weight[1] = 100.0

        # delta = 100.0 - 100.0 = 0.0 → below MIN_DELTA_G
        bridge._mock_driver.receive.return_value = make_msg(bin_id=1, weight_g=100.0)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.change_stock") as mock_cs:
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event"):
                bridge.process_one_message()

        mock_cs.assert_not_called()


# ---------------------------------------------------------------------------
# Delta matching and stock updates
# ---------------------------------------------------------------------------

class TestDeltaMatching:
    def test_item_removal_decrements_stock(self):
        """Weight drops by ~item_weight → change_stock called with -1."""
        bridge = make_bridge(stability_window=1)
        bridge._last_stable_weight[1] = 200.0  # baseline

        # Weight drops by 50g → matches item with weight 50g
        bridge._mock_driver.receive.return_value = make_msg(bin_id=1, weight_g=150.0)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_item_ids", return_value=[10]):
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_item_weight", return_value=50.0):
                with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.change_stock", return_value=True) as mock_cs:
                    with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_stock", return_value=9):
                        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event"):
                            bridge.process_one_message()

        mock_cs.assert_called_once_with(10, -1)

    def test_item_returned_increments_stock(self):
        """Weight increases by ~item_weight → change_stock called with +1."""
        bridge = make_bridge(stability_window=1)
        bridge._last_stable_weight[1] = 100.0  # baseline

        # Weight increases by 50g → item was put back
        bridge._mock_driver.receive.return_value = make_msg(bin_id=1, weight_g=150.0)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_item_ids", return_value=[10]):
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_item_weight", return_value=50.0):
                with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.change_stock", return_value=True) as mock_cs:
                    with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_stock", return_value=6):
                        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event"):
                            bridge.process_one_message()

        mock_cs.assert_called_once_with(10, +1)

    def test_no_match_skips_stock_update(self):
        """Delta doesn't match any item weight → no stock change."""
        bridge = make_bridge(stability_window=1)
        bridge._last_stable_weight[1] = 200.0

        # Delta = 50g but item weights don't match
        bridge._mock_driver.receive.return_value = make_msg(bin_id=1, weight_g=150.0)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_item_ids", return_value=[10]):
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_item_weight", return_value=200.0):
                with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.change_stock") as mock_cs:
                    with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event"):
                        bridge.process_one_message()

        mock_cs.assert_not_called()

    def test_no_items_in_bin_skips_stock_update(self):
        """Bin has no items configured → no stock change."""
        bridge = make_bridge(stability_window=1)
        bridge._last_stable_weight[1] = 200.0

        bridge._mock_driver.receive.return_value = make_msg(bin_id=1, weight_g=150.0)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_item_ids", return_value=[]):
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.change_stock") as mock_cs:
                with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event"):
                    bridge.process_one_message()

        mock_cs.assert_not_called()

    def test_correct_item_matched_from_multiple(self):
        """When bin has two items, delta matches the right one."""
        bridge = make_bridge(stability_window=1)
        bridge._last_stable_weight[1] = 500.0

        # Delta = 30g → should match child gloves (30g), not adult gloves (50g)
        bridge._mock_driver.receive.return_value = make_msg(bin_id=1, weight_g=470.0)

        def mock_get_weight(item_id):
            return {10: 50.0, 11: 30.0}[item_id]

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_item_ids", return_value=[10, 11]):
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_item_weight", side_effect=mock_get_weight):
                with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.change_stock", return_value=True) as mock_cs:
                    with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_stock", return_value=4):
                        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event"):
                            bridge.process_one_message()

        mock_cs.assert_called_once_with(11, -1)

    def test_last_stable_weight_updated_after_delta(self):
        """After a stable reading, _last_stable_weight reflects the new weight."""
        bridge = make_bridge(stability_window=1)
        bridge._last_stable_weight[1] = 200.0

        bridge._mock_driver.receive.return_value = make_msg(bin_id=1, weight_g=150.0)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_item_ids", return_value=[]):
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event"):
                bridge.process_one_message()

        assert bridge._last_stable_weight[1] == pytest.approx(150.0)


# ---------------------------------------------------------------------------
# LED feedback
# ---------------------------------------------------------------------------

class TestLedFeedback:
    def test_led_set_after_stock_update(self):
        bridge = make_bridge(stability_window=1, publish_led_feedback=True)
        bridge._last_stable_weight[1] = 200.0

        bridge._mock_driver.receive.return_value = make_msg(bin_id=1, weight_g=150.0)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_item_ids", return_value=[10]):
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_item_weight", return_value=50.0):
                with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.change_stock", return_value=True):
                    with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_stock", return_value=9):
                        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_stock_level", return_value="Yellow"):
                            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event"):
                                bridge.process_one_message()

        bridge._mock_driver.set_led.assert_called_once_with(bin_id=1, state=LED_YELLOW)

    def test_no_led_when_feedback_disabled(self):
        bridge = make_bridge(stability_window=1, publish_led_feedback=False)
        bridge._last_stable_weight[1] = 200.0

        bridge._mock_driver.receive.return_value = make_msg(bin_id=1, weight_g=150.0)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_item_ids", return_value=[10]):
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_item_weight", return_value=50.0):
                with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.change_stock", return_value=True):
                    with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_stock", return_value=9):
                        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event"):
                            bridge.process_one_message()

        bridge._mock_driver.set_led.assert_not_called()


# ---------------------------------------------------------------------------
# tare_all_containers
# ---------------------------------------------------------------------------

class TestTareAllContainers:
    def test_tares_all_containers(self):
        bridge = make_bridge()

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_all_container_ids", return_value=[1, 2, 3]):
            bridge.tare_all_containers()

        expected = [call(bin_id=1), call(bin_id=2), call(bin_id=3)]
        bridge._mock_driver.tare_bin.assert_has_calls(expected, any_order=False)

    def test_clears_state_for_all_containers(self):
        bridge = make_bridge()
        bridge._last_stable_weight[1] = 100.0
        bridge._last_stable_weight[2] = 200.0

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_all_container_ids", return_value=[1, 2]):
            bridge.tare_all_containers()

        assert 1 not in bridge._last_stable_weight
        assert 2 not in bridge._last_stable_weight

    def test_no_tare_sent_when_no_containers(self):
        bridge = make_bridge()

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_all_container_ids", return_value=[]):
            bridge.tare_all_containers()

        bridge._mock_driver.tare_bin.assert_not_called()
