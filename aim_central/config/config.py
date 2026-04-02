import os

class AIMConfig:
    LOG_DIR: str = os.getenv('LOG_DIR', 'logs')
    LOG_NAME: str = os.getenv('LOG_NAME', 'aim')
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'DEBUG')
    MAX_LOG_SIZE: int = int(os.getenv('MAX_LOG_SIZE', 10 * 1024 * 1024))  # 10 MB
    DB_PATH: str = os.getenv('DB_PATH', "inventory.db")

    # GPS geofence settings — update BASE_LAT/BASE_LON to the actual ambulance base location.
    # Current coordinates are Northeastern University (demo/development default).
    GPS_DEVICE: str = os.getenv('GPS_DEVICE', '/dev/ttyUSB0')
    GPS_BAUDRATE: int = int(os.getenv('GPS_BAUDRATE', 9600))
    BASE_LAT: float = float(os.getenv('BASE_LAT', 42.3389585))
    BASE_LON: float = float(os.getenv('BASE_LON', -71.0886069))
    GEOFENCE_ENTER_RADIUS_M: float = float(os.getenv('GEOFENCE_ENTER_RADIUS_M', 90.0))
    GEOFENCE_EXIT_RADIUS_M: float = float(os.getenv('GEOFENCE_EXIT_RADIUS_M', 110.0))