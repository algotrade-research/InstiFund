import os
import sys
from dotenv import load_dotenv
from pathlib import Path
import logging
import logging.config
from vnstock import Vnstock
import yaml
import random
import numpy as np

# Load .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

CONFIG_YAML_PATH = Path(__file__).parent.parent / "config" / "config.yaml"
with open(CONFIG_YAML_PATH, "r") as file:
    config = yaml.safe_load(file)

DEBUG = config.get("debug", True)

# Load logging configuration
LOGGING_CONFIG_PATH = Path(__file__).parent.parent / "config" / "logging.conf"
logging.config.fileConfig(LOGGING_CONFIG_PATH, defaults={
                          'sys.stdout': sys.stdout})
logger = logging.getLogger("my_logger")
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
logger.disabled = config.get("disable_logging", False)

# Database connection
DATABASE = {
    "NAME": os.getenv("DB_NAME"),
    "USER": os.getenv("DB_USER"),
    "PASSWORD": os.getenv("DB_PASSWORD"),
    "HOST": os.getenv("DB_HOST", "localhost"),  # Default: localhost
    "PORT": os.getenv("DB_PORT", "5432"),  # Default: 5432
}

DATA_PATH = os.getenv("DATA_PATH", Path(__file__).parent.parent / "data")

if not os.path.exists(DATA_PATH):
    os.makedirs(DATA_PATH)
    logger.info(f"Data path created at {DATA_PATH}")
else:
    logger.info(f"Data path already exists at {DATA_PATH}")


# Init Vnstock
vnstock = Vnstock().stock(symbol="ACB", source="VCI")

# Set random seed for reproducibility
random_seed = config.get("random_seed", 42)
random.seed(random_seed)
np.random.seed(random_seed)
