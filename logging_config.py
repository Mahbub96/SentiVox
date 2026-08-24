"""
logging_config.py — SentiVox Production Logging Configuration

Provides structured, configurable logging across all modules.
Supports both human-readable console output (dev) and JSON format (production).
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path

from config import LOG_LEVEL, LOG_FORMAT, LOG_DIR, IS_PRODUCTION


def setup_logging() -> None:
    """
    Configure the root logger and SentiVox application logger.
    Call once during application startup.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Determine log level
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove any pre-existing handlers (prevents duplicate logs on reload)
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    if LOG_FORMAT == "json":
        console_fmt = logging.Formatter(
            '{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
            datefmt="%Y-%m-%dT%H:%M:%S%z"
        )
    else:
        console_fmt = logging.Formatter(
            "%(asctime)s │ %(levelname)-8s │ %(name)-24s │ %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    console_handler.setFormatter(console_fmt)
    root_logger.addHandler(console_handler)

    # File handler with rotation (always plain text for searchability)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "sentivox.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_fmt = logging.Formatter(
        "%(asctime)s │ %(levelname)-8s │ %(name)-24s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_fmt)
    root_logger.addHandler(file_handler)

    # Quiet down overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING if IS_PRODUCTION else logging.INFO)
    logging.getLogger("tensorflow").setLevel(logging.WARNING)
    logging.getLogger("absl").setLevel(logging.WARNING)
    logging.getLogger("h5py").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger for a SentiVox module."""
    return logging.getLogger(f"sentivox.{name}")
