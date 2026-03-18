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
            bridge = CanDatabaseBridge(publish_led_feedback=True)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.update_stock_from_weight", return_value=True) as update_mock:
            with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.get_stock_level", return_value="Yellow"):
                processed = bridge.process_one_message(timeout=0.1)

        assert processed is True
        update_mock.assert_called_once_with(container_id=1, measured_weight_g=0.05)
        mock_driver.set_led.assert_called_once_with(bin_id=1, state=LED_YELLOW)

    def test_process_one_message_skips_update_when_status_not_ok(self):
        mock_driver = MagicMock()
        mock_driver.receive.return_value = {
            "bin_id": 2,
            "weight_g": 1.25,
            "status": "error",
            "tare_flag": "none",
        }

        with patch("aim_central.logic.CanDatabaseBridge.CANDriver", return_value=mock_driver):
            bridge = CanDatabaseBridge(publish_led_feedback=True)

        with patch("aim_central.logic.CanDatabaseBridge.DatabaseOperations.update_stock_from_weight") as update_mock:
            processed = bridge.process_one_message(timeout=0.1)

        assert processed is True
        update_mock.assert_not_called()
        mock_driver.set_led.assert_not_called()

    def test_process_one_message_returns_false_when_no_message(self):
        mock_driver = MagicMock()
        mock_driver.receive.return_value = None

        with patch("aim_central.logic.CanDatabaseBridge.CANDriver", return_value=mock_driver):
            bridge = CanDatabaseBridge(publish_led_feedback=True)

        processed = bridge.process_one_message(timeout=0.1)
        assert processed is False
