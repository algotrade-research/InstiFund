import os
from dotenv import load_dotenv
from pathlib import Path

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
