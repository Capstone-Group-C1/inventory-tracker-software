import time
import math
import board
import busio
import adafruit_gps

# ----------------------------
# Geofence settings
# ----------------------------
FENCE_LAT = 42.3389585
FENCE_LON = -71.0886069
EXIT_RADIUS_M = 110.0
ENTER_RADIUS_M = 90.0

inside_fence = True

# ----------------------------
# Haversine distance function
# ----------------------------
def deg2rad(deg):
    return deg * math.pi / 180.0

def distance_meters(lat1, lon1, lat2, lon2):
    R = 6371000.0  # Earth radius in meters
    dlat = deg2rad(lat2 - lat1)
    dlon = deg2rad(lon2 - lon1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(deg2rad(lat1)) *
         math.cos(deg2rad(lat2)) *
         math.sin(dlon / 2) ** 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# ----------------------------
# Set up UART and GPS
# ----------------------------
uart = busio.UART(board.TX, board.RX, baudrate=9600, timeout=10)
gps = adafruit_gps.GPS(uart, debug=False)

# Configure GPS module
gps.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
gps.send_command(b"PMTK220,1000")  # 1 Hz update rate

print("GPS geofence starting...")

last_print = time.monotonic()

while True:
    gps.update()

    current = time.monotonic()
    if current - last_print >= 1.0:
        last_print = current

        if not gps.has_fix:
            print("Waiting for GPS fix...")
            continue

        lat = gps.latitude
        lon = gps.longitude

        if lat is None or lon is None:
            print("No valid coordinates yet.")
            continue

        d = distance_meters(lat, lon, FENCE_LAT, FENCE_LON)

        print(f"Lat: {lat:.6f}, Lon: {lon:.6f}")
        print(f"Distance from fence center: {d:.2f} m")

        if inside_fence and d > EXIT_RADIUS_M:
            inside_fence = False
            print("ALERT: exited geofence")

        elif not inside_fence and d < ENTER_RADIUS_M:
            inside_fence = True
            print("INFO: re-entered geofence")