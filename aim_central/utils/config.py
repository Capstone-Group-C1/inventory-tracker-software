import os

class AIMConfig:
    LOG_DIR: str = os.getenv('LOG_DIR', 'logs')
    LOG_NAME: str = os.getenv('LOG_NAME', 'aim')
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'DEBUG')
    MAX_LOG_SIZE: int = int(os.getenv('MAX_LOG_SIZE', 10 * 1024 * 1024))  # 10 MB