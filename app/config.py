"""Configuration for the local-first P2C service."""
import os
from pathlib import Path

APP_VERSION = "0.2.0"
DATA_DIR = Path(os.environ.get("P2C_DATA_DIR", Path.home() / ".p2c")).expanduser()
DB_PATH = Path(os.environ.get("P2C_DB_PATH", DATA_DIR / "p2c.sqlite3")).expanduser()
SESSION_TTL_SECONDS = max(300, int(os.environ.get("P2C_SESSION_TTL_SECONDS", "28800")))
PAIRING_TTL_SECONDS = max(60, min(600, int(os.environ.get("P2C_PAIRING_TTL_SECONDS", "180"))))
COOKIE_SECURE = os.environ.get("P2C_COOKIE_SECURE", "0") == "1"
COOKIE_NAME = "p2c_session"
MAX_OUTPUT_BYTES = 8192
