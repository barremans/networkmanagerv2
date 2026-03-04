# =============================================================================
# Networkmap_Creator
# File:    app/services/logger.py
# Role:    Centrale logging service — GEEN Qt imports
# Version: 1.0.1
# Author:  Barremans
# Changes: B — logs map verplaatst naar %APPDATA%\Networkmap Creator\logs
#              zodat schrijven werkt na installatie in Program Files
# =============================================================================
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

# Logs altijd in %APPDATA%\Networkmap Creator\logs
# Werkt zowel in dev als na installatie via Inno Setup
_LOG_DIR  = Path(os.environ.get("APPDATA", Path.home())) / "Networkmap Creator" / "logs"
_LOG_FILE = _LOG_DIR / "app.log"
_logger   = None


def get_logger() -> logging.Logger:
    """Geeft de applicatie logger terug. Initialiseert bij eerste aanroep."""
    global _logger
    if _logger is not None:
        return _logger

    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Kan niet aanmaken (bv. Defender blocked) — alleen console logging
        pass

    _logger = logging.getLogger("networkmap")
    _logger.setLevel(logging.DEBUG)

    # Bestandshandler — alleen als de map beschikbaar is
    if _LOG_DIR.exists():
        try:
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
            _logger.addHandler(fh)
        except OSError:
            pass  # Defender of rechtenprobleem — stil negeren

    # Console handler — alleen WARNING en hoger
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter("%(levelname)s  %(message)s"))
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