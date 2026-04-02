import struct
from unittest.mock import MagicMock, patch

import pytest

# Skip this test module cleanly if python-can is not installed.
pytest.importorskip("can")

import can
from aim_central.drivers.canDriver import (
    CANDriver,
    STM32_TO_PI_ID,
    PI_TO_STM32_ID,
    STATUS_OK,
    STATUS_ERROR,
    STATUS_NOT_TARED,
    TARE_NONE,
    TARE_SUCCESS,
    TARE_FAIL,
    LED_OFF,
    LED_GREEN,
    LED_YELLOW,
    LED_RED,
    BUZZER_OFF,
    BUZZER_ON,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_can_message(bin_id, weight_g, status=STATUS_OK, tare_flag=TARE_NONE, arb_id=None):
    """
    Build a mock can.Message that matches the incoming message layout:
      Byte 0:     Bin ID
      Bytes 1-4:  Weight (float, grams)
      Byte 5:     Sensor status
      Byte 6:     Tare flag
      Byte 7:     Reserved
    """
    weight_bytes = struct.pack('f', weight_g)
    data = bytes([bin_id]) + weight_bytes + bytes([status, tare_flag, 0x00])

    msg = MagicMock(spec=can.Message)
    msg.arbitration_id = arb_id if arb_id is not None else (STM32_TO_PI_ID + bin_id)
    msg.data = data
    return msg


# ---------------------------------------------------------------------------
# Connection tests
# ---------------------------------------------------------------------------

class TestConnection:
    def test_connect_opens_bus(self):
        driver = CANDriver(channel='can0', bitrate=500000)
        with patch("can.interface.Bus") as mock_bus_cls:
            driver.connect()
            mock_bus_cls.assert_called_once_with(
                channel='can0', bustype='socketcan', bitrate=500000
            )
            assert driver.bus is not None

    def test_disconnect_shuts_down_bus(self):
        driver = CANDriver()
        mock_bus = MagicMock()
        driver.bus = mock_bus

        driver.disconnect()

        mock_bus.shutdown.assert_called_once()

    def test_disconnect_does_nothing_when_not_connected(self):
        driver = CANDriver()
        # Should not raise even if bus is None
        driver.disconnect()

    def test_context_manager_connects_and_disconnects(self):
        with patch("can.interface.Bus") as mock_bus_cls:
            mock_bus = MagicMock()
            mock_bus_cls.return_value = mock_bus

            with CANDriver(channel='can0') as driver:
                assert driver.bus is not None

            mock_bus.shutdown.assert_called_once()

    def test_connect_raises_on_failure(self):
        driver = CANDriver()
        with patch("can.interface.Bus", side_effect=OSError("no device")):
            with pytest.raises(OSError):
                driver.connect()


# ---------------------------------------------------------------------------
# Receive / parse tests
# ---------------------------------------------------------------------------

class TestReceive:
    def _make_driver(self):
        driver = CANDriver()
        driver.bus = MagicMock()
        return driver

    def test_receive_returns_none_on_timeout(self):
        driver = self._make_driver()
        driver.bus.recv.return_value = None

        result = driver.receive(timeout=0.1)

        assert result is None

    def test_receive_ignores_messages_outside_stm32_range(self):
        driver = self._make_driver()
        msg = make_can_message(bin_id=1, weight_g=5.0, arb_id=0x050)
        driver.bus.recv.return_value = msg

        result = driver.receive()

        assert result is None

    def test_receive_parses_valid_message(self):
        driver = self._make_driver()
        driver.bus.recv.return_value = make_can_message(bin_id=2, weight_g=10.5)

        result = driver.receive()

        assert result is not None
        assert result["bin_id"] == 2
        assert result["weight_g"] == pytest.approx(10.5, abs=0.01)
        assert result["status"] == "ok"
        assert result["tare_flag"] == "none"

    def test_receive_raises_when_not_connected(self):
        driver = CANDriver()
        with pytest.raises(RuntimeError):
            driver.receive()


class TestParseIncoming:
    def _make_driver(self):
        driver = CANDriver()
        driver.bus = MagicMock()
        return driver

    def test_parses_bin_id(self):
        driver = self._make_driver()
        driver.bus.recv.return_value = make_can_message(bin_id=3, weight_g=0.0)
        result = driver.receive()
        assert result["bin_id"] == 3

    def test_parses_weight_rounded_to_two_decimals(self):
        driver = self._make_driver()
        driver.bus.recv.return_value = make_can_message(bin_id=0, weight_g=7.123456)
        result = driver.receive()
        assert isinstance(result["weight_g"], float)
        assert len(str(result["weight_g"]).split(".")[-1]) <= 2

    def test_parses_status_ok(self):
        driver = self._make_driver()
        driver.bus.recv.return_value = make_can_message(bin_id=0, weight_g=1.0, status=STATUS_OK)
        assert driver.receive()["status"] == "ok"

    def test_parses_status_error(self):
        driver = self._make_driver()
        driver.bus.recv.return_value = make_can_message(bin_id=0, weight_g=1.0, status=STATUS_ERROR)
        assert driver.receive()["status"] == "error"

    def test_parses_status_not_tared(self):
        driver = self._make_driver()
        driver.bus.recv.return_value = make_can_message(bin_id=0, weight_g=1.0, status=STATUS_NOT_TARED)
        assert driver.receive()["status"] == "not_tared"

    def test_parses_tare_flag_none(self):
        driver = self._make_driver()
        driver.bus.recv.return_value = make_can_message(bin_id=0, weight_g=1.0, tare_flag=TARE_NONE)
        assert driver.receive()["tare_flag"] == "none"

    def test_tare_flag_always_none_until_firmware_implements(self):
        # Tare flag byte is intentionally ignored until firmware implements the protocol.
        # All incoming tare flag values should return "none" regardless of byte value.
        driver = self._make_driver()
        driver.bus.recv.return_value = make_can_message(bin_id=0, weight_g=0.0, tare_flag=TARE_SUCCESS)
        assert driver.receive()["tare_flag"] == "none"

        driver.bus.recv.return_value = make_can_message(bin_id=0, weight_g=0.0, tare_flag=TARE_FAIL)
        assert driver.receive()["tare_flag"] == "none"

    def test_returns_none_for_short_message(self):
        driver = self._make_driver()
        msg = MagicMock(spec=can.Message)
        msg.arbitration_id = STM32_TO_PI_ID + 1
        msg.data = bytes([0x01, 0x02])  # too short
        driver.bus.recv.return_value = msg

        result = driver.receive()
        assert result is None

    def test_unknown_status_code_returns_unknown(self):
        driver = self._make_driver()
        driver.bus.recv.return_value = make_can_message(bin_id=0, weight_g=1.0, status=0xFF)
        assert driver.receive()["status"] == "unknown"

    def test_unknown_tare_code_returns_none(self):
        # Tare flag is ignored — unknown codes also return "none".
        driver = self._make_driver()
        driver.bus.recv.return_value = make_can_message(bin_id=0, weight_g=1.0, tare_flag=0xFF)
        assert driver.receive()["tare_flag"] == "none"


# ---------------------------------------------------------------------------
# Send / command tests
# ---------------------------------------------------------------------------

class TestSendCommand:
    def _make_driver(self):
        driver = CANDriver()
        driver.bus = MagicMock()
        return driver

    def test_send_command_raises_when_not_connected(self):
        driver = CANDriver()
        with pytest.raises(RuntimeError):
            driver.send_command(bin_id=1)

    def test_send_command_uses_correct_arbitration_id(self):
        driver = self._make_driver()
        driver.send_command(bin_id=3)

        sent_msg = driver.bus.send.call_args[0][0]
        assert sent_msg.arbitration_id == PI_TO_STM32_ID + 3

    def test_send_command_default_no_tare_no_led_no_buzzer(self):
        driver = self._make_driver()
        driver.send_command(bin_id=1)

        sent_msg = driver.bus.send.call_args[0][0]
        assert sent_msg.data[0] == 1        # bin_id
        assert sent_msg.data[1] == 0x00     # tare off
        assert sent_msg.data[2] == LED_OFF
        assert sent_msg.data[3] == BUZZER_OFF

    def test_send_command_tare_flag_set(self):
        driver = self._make_driver()
        driver.send_command(bin_id=2, tare=True)

        sent_msg = driver.bus.send.call_args[0][0]
        assert sent_msg.data[1] == 0x01

    def test_send_command_led_state_set(self):
        driver = self._make_driver()
        driver.send_command(bin_id=1, led=LED_RED)

        sent_msg = driver.bus.send.call_args[0][0]
        assert sent_msg.data[2] == LED_RED

    def test_send_command_buzzer_on(self):
        driver = self._make_driver()
        driver.send_command(bin_id=1, buzzer=BUZZER_ON)

        sent_msg = driver.bus.send.call_args[0][0]
        assert sent_msg.data[3] == BUZZER_ON

    def test_send_command_reserved_bytes_are_zero(self):
        driver = self._make_driver()
        driver.send_command(bin_id=1, tare=True, led=LED_GREEN, buzzer=BUZZER_ON)

        sent_msg = driver.bus.send.call_args[0][0]
        assert list(sent_msg.data[4:8]) == [0x00, 0x00, 0x00, 0x00]

    def test_send_command_does_not_raise_on_can_error(self):
        driver = self._make_driver()
        driver.bus.send.side_effect = can.CanError("send failed")
        # Should log the error but not propagate it
        driver.send_command(bin_id=1)


# ---------------------------------------------------------------------------
# Convenience method tests
# ---------------------------------------------------------------------------

class TestConvenienceMethods:
    def _make_driver(self):
        driver = CANDriver()
        driver.bus = MagicMock()
        return driver

    def test_tare_bin_sends_tare_true(self):
        driver = self._make_driver()
        driver.tare_bin(bin_id=4)

        sent_msg = driver.bus.send.call_args[0][0]
        assert sent_msg.data[1] == 0x01  # tare byte set

    def test_set_led_green(self):
        driver = self._make_driver()
        driver.set_led(bin_id=1, state=LED_GREEN)

        sent_msg = driver.bus.send.call_args[0][0]
        assert sent_msg.data[2] == LED_GREEN

    def test_set_led_yellow(self):
        driver = self._make_driver()
        driver.set_led(bin_id=1, state=LED_YELLOW)

        sent_msg = driver.bus.send.call_args[0][0]
        assert sent_msg.data[2] == LED_YELLOW

    def test_set_led_red(self):
        driver = self._make_driver()
        driver.set_led(bin_id=1, state=LED_RED)

        sent_msg = driver.bus.send.call_args[0][0]
        assert sent_msg.data[2] == LED_RED

    def test_set_buzzer_on(self):
        driver = self._make_driver()
        driver.set_buzzer(bin_id=2, on=True)

        sent_msg = driver.bus.send.call_args[0][0]
        assert sent_msg.data[3] == BUZZER_ON

    def test_set_buzzer_off(self):
        driver = self._make_driver()
        driver.set_buzzer(bin_id=2, on=False)

        sent_msg = driver.bus.send.call_args[0][0]
        assert sent_msg.data[3] == BUZZER_OFF

    def test_tare_bin_does_not_change_led_or_buzzer(self):
        driver = self._make_driver()
        driver.tare_bin(bin_id=1)

        sent_msg = driver.bus.send.call_args[0][0]
        assert sent_msg.data[2] == LED_OFF
        assert sent_msg.data[3] == BUZZER_OFF

    def test_set_led_does_not_trigger_tare(self):
        driver = self._make_driver()
        driver.set_led(bin_id=1, state=LED_GREEN)

        sent_msg = driver.bus.send.call_args[0][0]
        assert sent_msg.data[1] == 0x00  # tare byte stays off

    def test_set_buzzer_does_not_trigger_tare(self):
        driver = self._make_driver()
        driver.set_buzzer(bin_id=1, on=True)

        sent_msg = driver.bus.send.call_args[0][0]
        assert sent_msg.data[1] == 0x00  # tare byte stays off
