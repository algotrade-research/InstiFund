import os
import sys
from dotenv import load_dotenv
from pathlib import Path
import logging
import logging.config

# Load .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

DEBUG = True

# Database connection
DATABASE = {
    "NAME": os.getenv("DB_NAME"),
    "USER": os.getenv("DB_USER"),
    "PASSWORD": os.getenv("DB_PASSWORD"),
    "HOST": os.getenv("DB_HOST", "localhost"),  # Default: localhost
    "PORT": os.getenv("DB_PORT", "5432"),  # Default: 5432
}

DATA_PATH = os.getenv("DATA_PATH", "data")

# Load logging configuration
LOGGING_CONFIG_PATH = Path(__file__).parent.parent / "config" / "logging.conf"
logging.config.fileConfig(LOGGING_CONFIG_PATH, defaults={
                          'sys.stdout': sys.stdout})
logger = logging.getLogger("my_logger")


TRADING_FEE = float(os.getenv("TRADING_FEE", 0.0047))  # Default: 0.35% + 0.12%
