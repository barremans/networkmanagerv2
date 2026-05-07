# =============================================================================
# Networkmap_Creator
# File:    app/security/offline_auth.py
# Role:    Offline poweruser login + toegangslogging
# Version: 1.0.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie
#                  Poweruser login als Azure AD niet bereikbaar is
#                  App start in read-only modus na succesvolle login
#                  Elke login (geslaagd + mislukt) wordt gelogd
#
# Geen Qt imports — pure service
# =============================================================================

from __future__ import annotations
import datetime
import hashlib
import os
import socket

# ---------------------------------------------------------------------------
# Poweruser wachtwoord (gehashed opgeslagen)
# ---------------------------------------------------------------------------

_POWERUSER_HASH = hashlib.sha256(b"zombiekillers.be8560!").hexdigest()


def check_poweruser_password(password: str) -> bool:
    """Controleer het ingevoerde wachtwoord tegen de hash."""
    return hashlib.sha256(password.encode()).hexdigest() == _POWERUSER_HASH


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _get_log_path() -> str:
    """
    Logbestand staat naast network_data.json.
    Fallback: naast de executable.
    """
    try:
        from app.helpers import settings_storage
        data_path = settings_storage.get_network_data_path()
        log_dir   = os.path.dirname(data_path)
        return os.path.join(log_dir, "security_log.txt")
    except Exception:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "..", "security_log.txt")


def _write_log(event: str, username: str, success: bool, reason: str = ""):
    """
    Schrijft een regel naar security_log.txt.
    Formaat: DATUM TIJD | EVENT | PC | GEBRUIKER | OK/FAIL | REDEN
    """
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pc        = socket.gethostname()
        status    = "OK" if success else "FAIL"
        parts     = [timestamp, event, pc, username or "onbekend", status]
        if reason:
            parts.append(reason)
        line = " | ".join(parts)

        log_path = _get_log_path()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        print(f"[SECURITY LOG] {line}")

    except Exception as e:
        print(f"[SECURITY LOG] Schrijven mislukt: {e}")


# ---------------------------------------------------------------------------
# Publieke API
# ---------------------------------------------------------------------------

def log_ad_login(display_name: str, upn: str, success: bool, reason: str = ""):
    """Log een Azure AD loginpoging."""
    username = f"{display_name} <{upn}>" if display_name or upn else ""
    _write_log("AD_LOGIN", username, success, reason)


def log_offline_login(username: str, success: bool, reason: str = ""):
    """Log een offline poweruser loginpoging."""
    _write_log("OFFLINE_LOGIN", username, success, reason)


def log_app_start(display_name: str, mode: str):
    """Log het starten van de app (mode: 'readwrite' of 'readonly')."""
    _write_log("APP_START", display_name, True, f"mode={mode}")