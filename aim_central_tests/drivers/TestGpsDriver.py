import os
import sys
import time
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from aim_central.drivers.gpsDriver import GeofenceMonitor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_monitor(on_enter=None, on_exit=None, enter_radius_m=90.0, exit_radius_m=110.0):
    """Create a GeofenceMonitor with NEU as base, no real serial port."""
    return GeofenceMonitor(
        on_enter=on_enter,
        on_exit=on_exit,
        base_lat=42.3389585,
        base_lon=-71.0886069,
        enter_radius_m=enter_radius_m,
        exit_radius_m=exit_radius_m,
    )


def make_gprmc(lat_deg, lon_deg, status='A'):
    """
    Build a $GPRMC NMEA sentence from decimal degree coordinates.
    Positive lat = N, negative = S. Positive lon = E, negative = W.
    """
    lat_abs = abs(lat_deg)
    lat_d = int(lat_abs)
    lat_m = (lat_abs - lat_d) * 60
    lat_dir = 'N' if lat_deg >= 0 else 'S'

    lon_abs = abs(lon_deg)
    lon_d = int(lon_abs)
    lon_m = (lon_abs - lon_d) * 60
    lon_dir = 'E' if lon_deg >= 0 else 'W'

    return (
        f"$GPRMC,120000,{status},"
        f"{lat_d:02d}{lat_m:07.4f},{lat_dir},"
        f"{lon_d:03d}{lon_m:07.4f},{lon_dir},"
        f"0.0,0.0,010101,,*00"
    )


# ---------------------------------------------------------------------------
# Haversine distance tests
# ---------------------------------------------------------------------------

class TestDistanceMeters:

    def test_same_point_is_zero(self):
        d = GeofenceMonitor._distance_meters(42.0, -71.0, 42.0, -71.0)
        assert d == pytest.approx(0.0, abs=0.01)

    def test_known_distance(self):
        # ~111km per degree of latitude
        d = GeofenceMonitor._distance_meters(42.0, -71.0, 43.0, -71.0)
        assert d == pytest.approx(111_195, rel=0.01)

    def test_symmetry(self):
        d1 = GeofenceMonitor._distance_meters(42.0, -71.0, 42.001, -71.0)
        d2 = GeofenceMonitor._distance_meters(42.001, -71.0, 42.0, -71.0)
        assert d1 == pytest.approx(d2, rel=1e-6)

    def test_small_distance(self):
        # ~50m north of base
        d = GeofenceMonitor._distance_meters(42.3389585, -71.0886069, 42.3394085, -71.0886069)
        assert d == pytest.approx(50, rel=0.05)


# ---------------------------------------------------------------------------
# NMEA parsing tests
# ---------------------------------------------------------------------------

class TestParseNmea:

    def test_valid_gprmc_returns_coords(self):
        monitor = make_monitor()
        sentence = make_gprmc(42.3389585, -71.0886069)
        result = monitor._parse_nmea(sentence)
        assert result is not None
        lat, lon = result
        assert lat == pytest.approx(42.3389585, abs=0.0001)
        assert lon == pytest.approx(-71.0886069, abs=0.0001)

    def test_valid_gnrmc_returns_coords(self):
        monitor = make_monitor()
        sentence = make_gprmc(42.0, -71.0).replace('$GPRMC', '$GNRMC')
        result = monitor._parse_nmea(sentence)
        assert result is not None

    def test_void_fix_returns_none(self):
        monitor = make_monitor()
        sentence = make_gprmc(42.0, -71.0, status='V')
        assert monitor._parse_nmea(sentence) is None

    def test_unrelated_sentence_returns_none(self):
        monitor = make_monitor()
        assert monitor._parse_nmea("$GPGGA,120000,,,,,0,,,,,,,,*66") is None

    def test_empty_string_returns_none(self):
        monitor = make_monitor()
        assert monitor._parse_nmea("") is None

    def test_too_short_sentence_returns_none(self):
        monitor = make_monitor()
        assert monitor._parse_nmea("$GPRMC,120000,A") is None

    def test_southern_hemisphere(self):
        monitor = make_monitor()
        sentence = make_gprmc(-33.8688, 151.2093)  # Sydney
        result = monitor._parse_nmea(sentence)
        assert result is not None
        lat, lon = result
        assert lat == pytest.approx(-33.8688, abs=0.001)
        assert lon == pytest.approx(151.2093, abs=0.001)

    def test_western_longitude_is_negative(self):
        monitor = make_monitor()
        sentence = make_gprmc(42.3389585, -71.0886069)
        lat, lon = monitor._parse_nmea(sentence)
        assert lon < 0


# ---------------------------------------------------------------------------
# Geofence logic tests
# ---------------------------------------------------------------------------

class TestUpdateFence:

    def test_on_enter_fires_when_inside_radius(self):
        on_enter = MagicMock()
        monitor = make_monitor(on_enter=on_enter, enter_radius_m=90.0)

        # Feed exact base coordinates — distance = 0, well inside 90m
        monitor._update_fence(42.3389585, -71.0886069)

        on_enter.assert_called_once()
        assert monitor.inside is True

    def test_on_enter_does_not_fire_outside_radius(self):
        on_enter = MagicMock()
        monitor = make_monitor(on_enter=on_enter, enter_radius_m=90.0)

        # ~200m north of base — outside enter radius
        monitor._update_fence(42.3407585, -71.0886069)

        on_enter.assert_not_called()
        assert monitor.inside is False

    def test_on_exit_fires_when_leaving(self):
        on_exit = MagicMock()
        monitor = make_monitor(on_exit=on_exit, enter_radius_m=90.0, exit_radius_m=110.0)

        # Enter first
        monitor._update_fence(42.3389585, -71.0886069)
        assert monitor.inside is True

        # Move far away — outside exit radius
        monitor._update_fence(43.0, -71.0)

        on_exit.assert_called_once()
        assert monitor.inside is False

    def test_on_enter_not_fired_twice_without_exit(self):
        on_enter = MagicMock()
        monitor = make_monitor(on_enter=on_enter)

        monitor._update_fence(42.3389585, -71.0886069)
        monitor._update_fence(42.3389585, -71.0886069)

        on_enter.assert_called_once()

    def test_on_exit_not_fired_twice_without_reentry(self):
        on_exit = MagicMock()
        monitor = make_monitor(on_exit=on_exit)

        monitor._update_fence(42.3389585, -71.0886069)  # enter
        monitor._update_fence(43.0, -71.0)               # exit
        monitor._update_fence(43.0, -71.0)               # still outside

        on_exit.assert_called_once()

    def test_hysteresis_prevents_reentry_between_thresholds(self):
        """
        A point between enter (90m) and exit (110m) radii should not
        trigger on_enter after exiting — prevents boundary flickering.
        """
        on_enter = MagicMock()
        on_exit = MagicMock()
        monitor = make_monitor(on_enter=on_enter, on_exit=on_exit,
                               enter_radius_m=90.0, exit_radius_m=110.0)

        monitor._update_fence(42.3389585, -71.0886069)  # enter (0m)
        assert monitor.inside is True

        monitor._update_fence(43.0, -71.0)               # exit (far away)
        assert monitor.inside is False

        # Now move to ~100m — between enter and exit thresholds
        # Should NOT re-trigger on_enter since 100m > enter_radius (90m)
        monitor._update_fence(42.3398585, -71.0886069)
        assert monitor.inside is False
        assert on_enter.call_count == 1

    def test_no_callback_when_none(self):
        monitor = make_monitor(on_enter=None, on_exit=None)
        # Should not raise
        monitor._update_fence(42.3389585, -71.0886069)
        monitor._update_fence(43.0, -71.0)


# ---------------------------------------------------------------------------
# Background thread tests
# ---------------------------------------------------------------------------

class TestBackgroundThread:

    def test_start_and_stop(self):
        monitor = make_monitor()

        with patch('serial.Serial') as mock_serial_cls:
            mock_serial = MagicMock()
            mock_serial.__enter__ = MagicMock(return_value=mock_serial)
            mock_serial.__exit__ = MagicMock(return_value=False)
            mock_serial.readline.return_value = b""
            mock_serial_cls.return_value = mock_serial

            monitor.start()
            assert monitor._thread is not None
            assert monitor._thread.is_alive()

            monitor.stop()
            assert not monitor._thread.is_alive()

    def test_on_enter_fires_from_valid_nmea(self):
        on_enter = MagicMock()
        monitor = make_monitor(on_enter=on_enter, enter_radius_m=90.0)

        sentence = make_gprmc(42.3389585, -71.0886069).encode('ascii') + b'\r\n'

        with patch('serial.Serial') as mock_serial_cls:
            mock_serial = MagicMock()
            mock_serial.__enter__ = MagicMock(return_value=mock_serial)
            mock_serial.__exit__ = MagicMock(return_value=False)
            # Return the valid sentence once, then empty to avoid busy loop
            mock_serial.readline.side_effect = [sentence] + [b""] * 100
            mock_serial_cls.return_value = mock_serial

            monitor.start()
            time.sleep(0.2)
            monitor.stop()

        on_enter.assert_called_once()

    def test_serial_error_does_not_crash_thread(self):
        monitor = make_monitor()

        import serial as _serial
        with patch('serial.Serial', side_effect=_serial.SerialException("no device")):
            monitor.start()
            time.sleep(0.1)
            monitor.stop()

        # Thread should have exited cleanly without raising
        assert not monitor._thread.is_alive()
