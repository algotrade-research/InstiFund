import os
import sys
from dotenv import load_dotenv
from pathlib import Path
import logging
import logging.config
from vnstock import Vnstock
import yaml

# Load .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

CONFIG_YAML_PATH = Path(__file__).parent.parent / "config" / "config.yaml"
with open(CONFIG_YAML_PATH, "r") as file:
    config = yaml.safe_load(file)

DEBUG = config.get("debug", True)

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
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
logger.disabled = config.get("disable_logging", False)

# Init Vnstock
vnstock = Vnstock().stock(symbol="ACB", source="VCI")
