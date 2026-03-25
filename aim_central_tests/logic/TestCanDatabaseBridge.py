import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Skip this test module cleanly if python-can is not installed.
pytest.importorskip("can")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from aim_central.logic.CanDatabaseBridge import CanDatabaseBridge, LED_YELLOW


class TestCanDatabaseBridge:
    def test_process_one_message_updates_stock_and_sets_led(self):
        mock_driver = MagicMock()
        mock_driver.receive.return_value = {
            "bin_id": 1,
            "weight_g": 0.05,
            "status": "ok",
            "tare_flag": "none",
        }

        with patch("aim_central.logic.CanDatabaseBridge.CANDriver", return_value=mock_driver):
            bridge = CanDatabaseBridge(publish_led_feedback=True, stability_window=1)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.update_stock_from_weight", return_value=True) as update_mock:
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_stock_level", return_value="Yellow"):
                with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_stock", return_value=50):
                    with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event", return_value=True):
                        processed = bridge.process_one_message(timeout=0.1)

        assert processed is True
        update_mock.assert_called_once_with(container_id=1, measured_weight_g=0.05)
        mock_driver.set_led.assert_called_once_with(bin_id=1, state=LED_YELLOW)

    def test_process_one_message_skips_update_on_sensor_error(self):
        mock_driver = MagicMock()
        mock_driver.receive.return_value = {
            "bin_id": 2,
            "weight_g": 1.25,
            "status": "error",
            "tare_flag": "none",
        }

        with patch("aim_central.logic.CanDatabaseBridge.CANDriver", return_value=mock_driver):
            bridge = CanDatabaseBridge(publish_led_feedback=True, stability_window=1)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.update_stock_from_weight") as update_mock:
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event", return_value=True):
                processed = bridge.process_one_message(timeout=0.1)

        assert processed is True
        update_mock.assert_not_called()
        mock_driver.set_led.assert_not_called()

    def test_not_tared_skips_db_update_and_clears_stability_window(self):
        mock_driver = MagicMock()

        with patch("aim_central.logic.CanDatabaseBridge.CANDriver", return_value=mock_driver):
            bridge = CanDatabaseBridge(publish_led_feedback=True, stability_window=3)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.update_stock_from_weight") as update_mock:
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event", return_value=True):
                # Pre-fill the stability window with ok readings
                mock_driver.receive.return_value = {"bin_id": 4, "weight_g": 5.0, "status": "ok", "tare_flag": "none"}
                bridge.process_one_message(timeout=0.1)
                bridge.process_one_message(timeout=0.1)
                assert len(bridge._weight_windows[4]) == 2

                # Now receive a not_tared message — should clear the window
                mock_driver.receive.return_value = {"bin_id": 4, "weight_g": 5.0, "status": "not_tared", "tare_flag": "none"}
                processed = bridge.process_one_message(timeout=0.1)

        assert processed is True
        update_mock.assert_not_called()
        mock_driver.set_led.assert_not_called()
        assert len(bridge._weight_windows[4]) == 0

    def test_not_tared_window_cleared_so_next_ok_restarts_collection(self):
        mock_driver = MagicMock()

        with patch("aim_central.logic.CanDatabaseBridge.CANDriver", return_value=mock_driver):
            bridge = CanDatabaseBridge(publish_led_feedback=False, stability_window=2)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.update_stock_from_weight", return_value=True) as update_mock:
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event", return_value=True):
                with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_stock", return_value=10):
                    # Fill window, then interrupt with not_tared
                    mock_driver.receive.return_value = {"bin_id": 5, "weight_g": 3.0, "status": "ok", "tare_flag": "none"}
                    bridge.process_one_message(timeout=0.1)

                    mock_driver.receive.return_value = {"bin_id": 5, "weight_g": 3.0, "status": "not_tared", "tare_flag": "none"}
                    bridge.process_one_message(timeout=0.1)

                    # One ok reading after not_tared — window only has 1 sample, not enough to commit
                    mock_driver.receive.return_value = {"bin_id": 5, "weight_g": 3.0, "status": "ok", "tare_flag": "none"}
                    bridge.process_one_message(timeout=0.1)
                    update_mock.assert_not_called()

                    # Second ok reading — now window is full, should commit
                    bridge.process_one_message(timeout=0.1)
                    update_mock.assert_called_once_with(container_id=5, measured_weight_g=3.0)

    def test_tare_confirmed_clears_stability_window_and_skips_db_write(self):
        mock_driver = MagicMock()

        with patch("aim_central.logic.CanDatabaseBridge.CANDriver", return_value=mock_driver):
            bridge = CanDatabaseBridge(publish_led_feedback=True, stability_window=3)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.update_stock_from_weight") as update_mock:
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event", return_value=True):
                # Pre-fill stability window
                mock_driver.receive.return_value = {"bin_id": 6, "weight_g": 4.0, "status": "ok", "tare_flag": "none"}
                bridge.process_one_message(timeout=0.1)
                bridge.process_one_message(timeout=0.1)
                assert len(bridge._weight_windows[6]) == 2

                # Tare confirmation arrives — window should clear, no DB write
                mock_driver.receive.return_value = {"bin_id": 6, "weight_g": 0.1, "status": "ok", "tare_flag": "success"}
                processed = bridge.process_one_message(timeout=0.1)

        assert processed is True
        update_mock.assert_not_called()
        mock_driver.set_led.assert_not_called()
        assert len(bridge._weight_windows[6]) == 0

    def test_tare_confirmed_window_cleared_so_next_readings_restart_collection(self):
        mock_driver = MagicMock()

        with patch("aim_central.logic.CanDatabaseBridge.CANDriver", return_value=mock_driver):
            bridge = CanDatabaseBridge(publish_led_feedback=False, stability_window=2)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.update_stock_from_weight", return_value=True) as update_mock:
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event", return_value=True):
                with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_stock", return_value=5):
                    # Fill window, then receive tare confirmation
                    mock_driver.receive.return_value = {"bin_id": 7, "weight_g": 8.0, "status": "ok", "tare_flag": "none"}
                    bridge.process_one_message(timeout=0.1)

                    mock_driver.receive.return_value = {"bin_id": 7, "weight_g": 0.0, "status": "ok", "tare_flag": "success"}
                    bridge.process_one_message(timeout=0.1)

                    # One ok reading post-tare — not enough for commit yet
                    mock_driver.receive.return_value = {"bin_id": 7, "weight_g": 0.0, "status": "ok", "tare_flag": "none"}
                    bridge.process_one_message(timeout=0.1)
                    update_mock.assert_not_called()

                    # Second ok reading — window full, commit
                    bridge.process_one_message(timeout=0.1)
                    update_mock.assert_called_once_with(container_id=7, measured_weight_g=0.0)

    def test_process_one_message_returns_false_when_no_message(self):
        mock_driver = MagicMock()
        mock_driver.receive.return_value = None

        with patch("aim_central.logic.CanDatabaseBridge.CANDriver", return_value=mock_driver):
            bridge = CanDatabaseBridge(publish_led_feedback=True, stability_window=1)

        processed = bridge.process_one_message(timeout=0.1)
        assert processed is False

    def test_process_one_message_waits_for_stable_window(self):
        mock_driver = MagicMock()
        mock_driver.receive.return_value = {
            "bin_id": 3,
            "weight_g": 2.0,
            "status": "ok",
            "tare_flag": "none",
        }

        with patch("aim_central.logic.CanDatabaseBridge.CANDriver", return_value=mock_driver):
            bridge = CanDatabaseBridge(publish_led_feedback=False, stability_window=3, stability_tolerance_g=0.5)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.update_stock_from_weight", return_value=True) as update_mock:
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.record_sensor_event", return_value=True):
                assert bridge.process_one_message(timeout=0.1) is True
                assert bridge.process_one_message(timeout=0.1) is True
                update_mock.assert_not_called()

                assert bridge.process_one_message(timeout=0.1) is True
                update_mock.assert_called_once_with(container_id=3, measured_weight_g=2.0)
