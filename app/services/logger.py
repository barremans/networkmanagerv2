# =============================================================================
# Networkmap_Creator
# File:    app/services/logger.py
# Role:    Centrale logging service — GEEN Qt imports
# Version: 1.0.0
# Author:  Barremans
# =============================================================================

import logging
import os
from pathlib import Path
from datetime import datetime

_LOG_DIR  = Path(__file__).parent.parent.parent / "logs"
_LOG_FILE = _LOG_DIR / "app.log"
_logger   = None


def get_logger() -> logging.Logger:
    """Geeft de applicatie logger terug. Initialiseert bij eerste aanroep."""
    global _logger
    if _logger is not None:
        return _logger

    _LOG_DIR.mkdir(exist_ok=True)

    _logger = logging.getLogger("networkmap")
    _logger.setLevel(logging.DEBUG)

    # Bestandshandler — max 1MB, dan roteren
    from logging.handlers import RotatingFileHandler
    fh = RotatingFileHandler(
        _LOG_FILE, maxBytes=1_000_000, backupCount=3,
        encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(module)s:%(lineno)d  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    # Console handler — alleen WARNING en hoger
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter("%(levelname)s  %(message)s"))

    _logger.addHandler(fh)
    _logger.addHandler(ch)
    _logger.info("=== Networkmap Creator gestart ===")

    return _logger


def log_info(msg: str):
    get_logger().info(msg)

def log_warning(msg: str):
    get_logger().warning(msg)

def log_error(msg: str, exc: Exception = None):
    if exc:
        get_logger().error(f"{msg} — {type(exc).__name__}: {exc}")
    else:
        get_logger().error(msg)

def log_debug(msg: str):
    get_logger().debug(msg)