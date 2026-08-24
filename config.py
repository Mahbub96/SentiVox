"""
config.py — SentiVox Centralized Configuration

Single source of truth for all application settings.
Reads from environment variables with sensible defaults for development.
In production, set these via .env file or system environment.
"""

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root (no-op if file doesn't exist)
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


# ─── Environment Detection ──────────────────────────────────────────────────

ENV = os.environ.get("SENTIVOX_ENV", "development").lower()
IS_PRODUCTION = ENV == "production"
DEBUG = not IS_PRODUCTION


# ─── Security ────────────────────────────────────────────────────────────────

def _get_secret_key() -> str:
    """
    In production: MUST be set via environment variable.
    In development: uses a stable dev-only key with a warning.
    """
    key = os.environ.get("JWT_SECRET_KEY")
    if key:
        return key
    if IS_PRODUCTION:
        raise RuntimeError(
            "CRITICAL: JWT_SECRET_KEY environment variable is not set. "
            "Refusing to start in production without a secure secret key. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
        )
    return "sentivox-dev-only-insecure-key-do-not-use-in-production"


JWT_SECRET_KEY: str = _get_secret_key()
JWT_ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


# ─── Database ─────────────────────────────────────────────────────────────────

DATABASE_URL: str = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'sentivox.db'}")

# SQLite WAL mode for better concurrent read performance
SQLITE_WAL_MODE: bool = "sqlite" in DATABASE_URL


# ─── Server ───────────────────────────────────────────────────────────────────

HOST: str = os.environ.get("HOST", "127.0.0.1")
PORT: int = int(os.environ.get("PORT", "8000"))
WORKERS: int = int(os.environ.get("WORKERS", "1"))

# CORS: comma-separated list of allowed origins
# In development, defaults to "*"; in production, must be explicitly set
_cors_default = "*" if not IS_PRODUCTION else ""
CORS_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", _cors_default).split(",")
    if origin.strip()
]

if IS_PRODUCTION and not CORS_ORIGINS:
    raise RuntimeError(
        "CRITICAL: CORS_ORIGINS environment variable is not set. "
        "Refusing to start in production without explicit CORS origins. "
        "Set CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com"
    )


# ─── Audio Processing ────────────────────────────────────────────────────────

MAX_FILE_SIZE_BYTES: int = int(os.environ.get("MAX_FILE_SIZE_MB", "15")) * 1024 * 1024
MAX_BATCH_FILES: int = int(os.environ.get("MAX_BATCH_FILES", "20"))
ALLOWED_AUDIO_EXTENSIONS: list[str] = [".wav", ".mp3", ".ogg", ".flac"]
SAMPLE_RATE_HZ: int = int(os.environ.get("SAMPLE_RATE_HZ", "16000"))
SILENCE_TRIM_DB: int = int(os.environ.get("SILENCE_TRIM_DB", "25"))


# ─── Model ────────────────────────────────────────────────────────────────────

MODELS_DIR: Path = BASE_DIR / "models"
DEFAULT_MODEL_PATH: Path = MODELS_DIR / "CascadeCovM1_BEST.h5"

# Number of emotion classes and feature dimensions (architecture constants)
NUM_CLASSES: int = 7
FEATURE_DIM: int = 46


# ─── Default Admin Seed ──────────────────────────────────────────────────────

DEFAULT_ADMIN_EMAIL: str = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@sentivox.com")
DEFAULT_ADMIN_PASSWORD: str = os.environ.get("DEFAULT_ADMIN_PASSWORD", "admin123")
DEFAULT_ADMIN_NAME: str = os.environ.get("DEFAULT_ADMIN_NAME", "System Administrator")


# ─── Rate Limiting ────────────────────────────────────────────────────────────

RATE_LIMIT_AUTH: str = os.environ.get("RATE_LIMIT_AUTH", "10/minute")
RATE_LIMIT_PREDICT: str = os.environ.get("RATE_LIMIT_PREDICT", "30/minute")


# ─── Logging ──────────────────────────────────────────────────────────────────

LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "DEBUG" if not IS_PRODUCTION else "INFO")
LOG_FORMAT: str = os.environ.get("LOG_FORMAT", "json" if IS_PRODUCTION else "console")
LOG_DIR: Path = BASE_DIR / "logs"
