import logging
import sys
from pathlib import Path
from aim_central.utils.config import AIMConfig
from logging.handlers import RotatingFileHandler

"""Logging Module for AIM"""

def init_logging():
  """
  Initialize the logging configuration.
  
  :param name: Name of the logger (default: 'aim')
  :param log_level: Logging level (default: logging.INFO)
  """

  # Create a logger
  logger = logging.getLogger(AIMConfig.LOG_NAME)
  logger.setLevel(AIMConfig.LOG_LEVEL)

  # Clear existing handlers to avoid duplicate logs
  logger.handlers.clear()

  # Format logger
  formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s', # timestamp - logger name - log level - message
    datefmt='%Y-%m-%d %H:%M:%S' # date format
    )
  
  # Console handler (stdout)
  console_handler = logging.StreamHandler(sys.stdout)
  console_handler.setLevel(AIMConfig.LOG_LEVEL)
  console_handler.setFormatter(formatter)
  logger.addHandler(console_handler)

  rotating_handler = RotatingFileHandler(
    AIMConfig.LOG_DIR + '/' + AIMConfig.LOG_NAME + '.log',
    maxBytes=AIMConfig.MAX_LOG_SIZE,
    backupCount=5
  )
  rotating_handler.setLevel(AIMConfig.LOG_LEVEL)
  rotating_handler.setFormatter(formatter)
  logger.addHandler(rotating_handler)

  return logger