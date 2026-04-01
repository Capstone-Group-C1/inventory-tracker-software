import math
import logging
import threading
import time

import serial

from aim_central.config.config import AIMConfig


class GeofenceMonitor:
    """
    Monitors GPS position and fires callbacks when the device enters or exits
    the configured geofence around the ambulance base.

    Uses hysteresis — enter threshold is smaller than exit threshold — to
    prevent flickering at the boundary.

    Usage:
        monitor = GeofenceMonitor(on_enter=start_fn, on_exit=stop_fn)
        monitor.start()
        ...
        monitor.stop()
    """

    def __init__(
        self,
        on_enter=None,
        on_exit=None,
        device=AIMConfig.GPS_DEVICE,
        baudrate=AIMConfig.GPS_BAUDRATE,
        base_lat=AIMConfig.BASE_LAT,
        base_lon=AIMConfig.BASE_LON,
        enter_radius_m=AIMConfig.GEOFENCE_ENTER_RADIUS_M,
        exit_radius_m=AIMConfig.GEOFENCE_EXIT_RADIUS_M,
        poll_interval_s=1.0,
    ):
        self.on_enter = on_enter
        self.on_exit = on_exit
        self.device = device
        self.baudrate = baudrate
        self.base_lat = base_lat
        self.base_lon = base_lon
        self.enter_radius_m = enter_radius_m
        self.exit_radius_m = exit_radius_m
        self.poll_interval_s = poll_interval_s

        self._inside = False
        self._stop_event = threading.Event()
        self._thread = None
        self.logger = logging.getLogger("GeofenceMonitor")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def start(self):
        """Start the background GPS polling thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.logger.info("GeofenceMonitor started.")

    def stop(self):
        """Stop the background GPS polling thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        self.logger.info("GeofenceMonitor stopped.")

    @property
    def inside(self):
        """True if the device is currently inside the geofence."""
        return self._inside

    # ------------------------------------------------------------------
    # Background thread
    # ------------------------------------------------------------------

    def _run(self):
        try:
            with serial.Serial(self.device, self.baudrate, timeout=1) as ser:
                self.logger.info("Opened GPS device %s at %d baud.", self.device, self.baudrate)
                while not self._stop_event.is_set():
                    line = ser.readline().decode('ascii', errors='replace').strip()
                    coords = self._parse_nmea(line)
                    if coords:
                        self._update_fence(*coords)
                    time.sleep(self.poll_interval_s)
        except serial.SerialException as e:
            self.logger.error("GPS serial error: %s", e)

    # ------------------------------------------------------------------
    # NMEA parsing — handles $GPRMC and $GNRMC sentences
    # ------------------------------------------------------------------

    def _parse_nmea(self, sentence):
        """
        Parse a GPRMC or GNRMC NMEA sentence and return (lat, lon) or None.

        Sentence format:
          $GPRMC,hhmmss,A,ddmm.mmmm,N,dddmm.mmmm,W,...
        """
        try:
            if not (sentence.startswith('$GPRMC') or sentence.startswith('$GNRMC')):
                return None

            parts = sentence.split(',')
            if len(parts) < 7:
                return None

            status = parts[2]
            if status != 'A':  # A = active/valid fix, V = void
                return None

            lat = self._nmea_to_decimal(parts[3], parts[4])
            lon = self._nmea_to_decimal(parts[5], parts[6])

            if lat is None or lon is None:
                return None

            return lat, lon
        except (ValueError, IndexError):
            return None

    def _nmea_to_decimal(self, value, direction):
        """Convert NMEA ddmm.mmmm format to decimal degrees."""
        if not value:
            return None

        dot = value.index('.')
        degrees = float(value[:dot - 2])
        minutes = float(value[dot - 2:])
        decimal = degrees + minutes / 60.0

        if direction in ('S', 'W'):
            decimal = -decimal

        return decimal

    # ------------------------------------------------------------------
    # Geofence logic
    # ------------------------------------------------------------------

    def _update_fence(self, lat, lon):
        d = self._distance_meters(lat, lon, self.base_lat, self.base_lon)
        self.logger.debug("GPS: lat=%.6f lon=%.6f distance=%.1fm", lat, lon, d)

        if not self._inside and d <= self.enter_radius_m:
            self._inside = True
            self.logger.info("Entered geofence (%.1fm from base).", d)
            if self.on_enter:
                self.on_enter()

        elif self._inside and d > self.exit_radius_m:
            self._inside = False
            self.logger.info("Exited geofence (%.1fm from base).", d)
            if self.on_exit:
                self.on_exit()

    # ------------------------------------------------------------------
    # Haversine distance
    # ------------------------------------------------------------------

    @staticmethod
    def _distance_meters(lat1, lon1, lat2, lon2):
        R = 6371000.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) *
             math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
