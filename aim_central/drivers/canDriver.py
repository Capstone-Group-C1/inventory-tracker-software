import can
import struct
import logging

# CAN IDs
STM32_TO_PI_ID = 0x100  # STM32 sends weight data  (0x100 + bin_id)
PI_TO_STM32_ID = 0x200  # Pi sends commands         (0x200 + bin_id)

# Sensor status codes (Byte 5 in incoming message)
STATUS_OK       = 0x00
STATUS_ERROR    = 0x01
STATUS_NOT_TARED = 0x02

# Tare flag codes (Byte 6 in incoming message)
TARE_NONE    = 0x00
TARE_SUCCESS = 0x01
TARE_FAIL    = 0x02

# LED state codes (Byte 2 in outgoing command)
LED_OFF    = 0x00
LED_GREEN  = 0x01
LED_YELLOW = 0x02
LED_RED    = 0x03

# Buzzer codes (Byte 3 in outgoing command)
BUZZER_OFF = 0x00
BUZZER_ON  = 0x01


class CANDriver:
    """
    Handles CAN communication between the Raspberry Pi and STM32 bin nodes.

    Incoming (STM32 → Pi):  weight data, sensor status, tare confirmation
    Outgoing (Pi → STM32):  tare command, LED state, buzzer command
    """

    def __init__(self, channel='can0', bitrate=500000):
        """
        Initialize the CAN interface.

        :param channel: CAN interface name (default 'can0' for MCP2515 over SPI)
        :param bitrate: CAN bus speed in bits/sec (must match STM32 config)
        """
        self.channel = channel
        self.bitrate = bitrate
        self.bus = None
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("CANDriver")

    # ------------------------------------------------------------------
    # CONNECTION
    # ------------------------------------------------------------------

    def connect(self):
        """Open the CAN bus connection."""
        try:
            self.bus = can.interface.Bus(
                channel=self.channel,
                bustype='socketcan',
                bitrate=self.bitrate
            )
            self.logger.info(f"Connected to CAN bus on {self.channel}")
        except Exception as e:
            self.logger.error(f"Failed to connect to CAN bus: {e}")
            raise

    def disconnect(self):
        """Close the CAN bus connection cleanly."""
        if self.bus:
            self.bus.shutdown()
            self.logger.info("CAN bus disconnected.")

    # ------------------------------------------------------------------
    # RECEIVING — STM32 → Pi
    # ------------------------------------------------------------------

    def receive(self, timeout=1.0):
        """
        Wait for an incoming CAN message and parse it.

        Incoming message layout (8 bytes):
          Byte 0:     Bin ID
          Bytes 1-4:  Raw weight (float, grams)
          Byte 5:     Sensor status (0=ok, 1=error, 2=not tared)
          Byte 6:     Tare flag (0=none, 1=success, 2=fail)
          Byte 7:     Reserved

        :param timeout: seconds to wait for a message
        :return: parsed dict, or None if timeout
        """
        if not self.bus:
            raise RuntimeError("CAN bus not connected. Call connect() first.")

        msg = self.bus.recv(timeout=timeout)

        if msg is None:
            self.logger.warning("No message received within timeout.")
            return None

        # Only process messages from STM32 nodes (ID range 0x100 - 0x1FF)
        if not (0x100 <= msg.arbitration_id <= 0x1FF):
            return None

        return self._parse_incoming(msg)

    def _parse_incoming(self, msg):
        """
        Unpack raw CAN bytes into a readable dictionary.

        :param msg: raw can.Message object
        :return: dict with bin_id, weight_g, status, tare_flag
        """
        if len(msg.data) < 7:
            self.logger.error("Malformed message: too short.")
            return None

        bin_id      = msg.data[0]
        weight_g    = struct.unpack('f', bytes(msg.data[1:5]))[0]  # 4-byte float
        status      = msg.data[5]
        tare_flag   = msg.data[6]

        parsed = {
            "bin_id":    bin_id,
            "weight_g":  round(weight_g, 2),
            "status":    self._decode_status(status),
            "tare_flag": self._decode_tare(tare_flag)
        }

        self.logger.info(f"Received: {parsed}")
        return parsed

    def _decode_status(self, code):
        return {STATUS_OK: "ok", STATUS_ERROR: "error", STATUS_NOT_TARED: "not_tared"}.get(code, "unknown")

    def _decode_tare(self, code):
        return {TARE_NONE: "none", TARE_SUCCESS: "success", TARE_FAIL: "fail"}.get(code, "unknown")

    # ------------------------------------------------------------------
    # SENDING — Pi → STM32
    # ------------------------------------------------------------------

    def send_command(self, bin_id, tare=False, led=LED_OFF, buzzer=BUZZER_OFF):
        """
        Send a command message to a specific bin's STM32.

        Outgoing message layout (8 bytes):
          Byte 0:   Bin ID
          Byte 1:   Tare command  (1 = tare, 0 = no action)
          Byte 2:   LED state     (0=off, 1=green, 2=yellow, 3=red)
          Byte 3:   Buzzer        (0=off, 1=on)
          Bytes 4-7: Reserved (zeroed)

        :param bin_id: which bin to command
        :param tare:   True to send a tare command
        :param led:    LED state constant (LED_OFF, LED_GREEN, LED_YELLOW, LED_RED)
        :param buzzer: BUZZER_ON or BUZZER_OFF
        """
        if not self.bus:
            raise RuntimeError("CAN bus not connected. Call connect() first.")

        data = [
            bin_id,
            0x01 if tare else 0x00,
            led,
            buzzer,
            0x00, 0x00, 0x00, 0x00  # reserved
        ]

        msg = can.Message(
            arbitration_id=PI_TO_STM32_ID + bin_id,
            data=data,
            is_extended_id=False
        )

        try:
            self.bus.send(msg)
            self.logger.info(f"Command sent to bin {bin_id}: tare={tare}, led={led}, buzzer={buzzer}")
        except can.CanError as e:
            self.logger.error(f"Failed to send command: {e}")

    # ------------------------------------------------------------------
    # CONVENIENCE COMMAND METHODS
    # ------------------------------------------------------------------

    def tare_bin(self, bin_id):
        """Send a tare command to a specific bin."""
        self.send_command(bin_id, tare=True)

    def set_led(self, bin_id, state):
        """Set the LED state for a specific bin."""
        self.send_command(bin_id, led=state)

    def set_buzzer(self, bin_id, on: bool):
        """Turn the buzzer on or off for a specific bin."""
        self.send_command(bin_id, buzzer=BUZZER_ON if on else BUZZER_OFF)

    # ------------------------------------------------------------------
    # CONTEXT MANAGER — allows use of 'with CANDriver() as driver'
    # ------------------------------------------------------------------

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


# ------------------------------------------------------------------
# BASIC USAGE EXAMPLE
# ------------------------------------------------------------------

if __name__ == "__main__":
    with CANDriver(channel='can0', bitrate=500000) as driver:

        # Listen for one incoming message
        data = driver.receive(timeout=2.0)
        if data:
            print(f"Bin {data['bin_id']} — Weight: {data['weight_g']}g — Status: {data['status']}")

        # Send a tare command to bin 1
        driver.tare_bin(bin_id=1)

        # Set bin 2 LED to red
        driver.set_led(bin_id=2, state=LED_RED)

        # Turn on buzzer for bin 3
        driver.set_buzzer(bin_id=3, on=True)