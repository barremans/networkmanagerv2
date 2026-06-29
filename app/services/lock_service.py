# =============================================================================
# Networkmap_Creator
# File:    app/services/lock_service.py
# Role:    File locking voor network_data.json — GEEN Qt imports
# Version: 1.0.0
# Author:  Barremans
# Changes: 1.0.0 — LCK-1: file locking / atomic write bescherming.
#                  Voorkomt dat twee gelijktijdige gebruikers elkaars
#                  data overschrijven.
#
#                  Aanpak: .lock-bestand naast network_data.json.
#                  Inhoud: JSON met pid, hostname, username, timestamp.
#                  Bij acquire: lock lezen → stale check → schrijven.
#                  Bij release: lock verwijderen.
#                  Stale lock: ouder dan LOCK_TIMEOUT_S seconden →
#                  automatisch verwijderd (crash of harde afsluiting).
#
#                  Publieke API:
#                    acquire_lock(path)  → (bool, str)
#                    release_lock(path)  → None
#                    read_lock_info(path)→ dict | None
#                    is_stale(path)      → bool
# =============================================================================

import json
import os
import socket
import time
from pathlib import Path


# Maximale leeftijd van een lock in seconden.
# Na deze tijd wordt de lock als verouderd (crash) beschouwd.
LOCK_TIMEOUT_S = 60

# Wachttijd tussen retries bij acquire.
_RETRY_INTERVAL_S = 0.5

# Maximaal aantal retries bij acquire (= max wachttijd / interval).
_RETRY_COUNT = 10   # 5 seconden totaal


# ---------------------------------------------------------------------------
# Intern
# ---------------------------------------------------------------------------

def _lock_path(network_data_path: str) -> Path:
    """Geef het pad van het .lock-bestand terug naast network_data.json."""
    return Path(network_data_path).with_suffix(".lock")


def _lock_info() -> dict:
    """Bouw de inhoud van een nieuw lock-bestand op."""
    try:
        hostname = socket.gethostname()
    except OSError:
        hostname = "onbekend"

    try:
        username = os.environ.get("USERNAME") or os.environ.get("USER") or "onbekend"
    except OSError:
        username = "onbekend"

    return {
        "pid":       os.getpid(),
        "hostname":  hostname,
        "username":  username,
        "timestamp": time.time(),
    }


def _write_lock(lock_file: Path, info: dict) -> bool:
    """
    Schrijf het lock-bestand atomisch via een .tmp tussenbestand.
    Geeft True bij succes.
    """
    tmp = lock_file.with_suffix(".lock.tmp")
    try:
        tmp.write_text(json.dumps(info), encoding="utf-8")
        tmp.replace(lock_file)
        return True
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def _read_lock(lock_file: Path) -> dict | None:
    """Lees en parseer het lock-bestand. Geeft None bij ontbrekend of corrupt bestand."""
    try:
        text = lock_file.read_text(encoding="utf-8")
        return json.loads(text)
    except (OSError, json.JSONDecodeError):
        return None


def _is_own_lock(info: dict) -> bool:
    """Geeft True als de lock van het huidige proces is."""
    return (
        info.get("pid") == os.getpid()
        and info.get("hostname") == socket.gethostname()
    )


def _is_stale_info(info: dict) -> bool:
    """
    Geeft True als de lock ouder is dan LOCK_TIMEOUT_S seconden.
    Een verouderde lock duidt op een eerder gecrasht of abrupt afgesloten proces.
    """
    ts = info.get("timestamp", 0)
    return (time.time() - ts) > LOCK_TIMEOUT_S


# ---------------------------------------------------------------------------
# Publieke API
# ---------------------------------------------------------------------------

def acquire_lock(network_data_path: str) -> tuple[bool, str]:
    """
    Probeer de schrijflock te verkrijgen voor network_data.json.

    Retourneert (True, "") bij succes.
    Retourneert (False, foutmelding) als de lock bezet is door een andere
    gebruiker/machine na het verstrijken van de wachttijd.

    Strategie:
      1. Lock-bestand bestaat niet          → direct schrijven → OK
      2. Lock-bestand is van eigen proces   → OK (re-entrant)
      3. Lock-bestand is verouderd (stale)  → verwijderen + opnieuw proberen
      4. Lock-bestand van ander proces      → wachten met retry (max 5s)
      5. Na 5s nog bezet                    → foutmelding teruggeven
    """
    lock_file = _lock_path(network_data_path)
    info_to_write = _lock_info()

    for attempt in range(_RETRY_COUNT + 1):
        existing = _read_lock(lock_file)

        if existing is None:
            # Geen lock aanwezig → probeer te schrijven
            if _write_lock(lock_file, info_to_write):
                # Verifieer dat ons lock-bestand er staat (race condition check)
                verify = _read_lock(lock_file)
                if verify and verify.get("pid") == info_to_write["pid"] \
                        and verify.get("timestamp") == info_to_write["timestamp"]:
                    return True, ""
                # Ander proces was sneller → volgend retry
            if attempt < _RETRY_COUNT:
                time.sleep(_RETRY_INTERVAL_S)
            continue

        if _is_own_lock(existing):
            # Re-entrant: eigen lock → bijwerken timestamp
            info_to_write["timestamp"] = time.time()
            _write_lock(lock_file, info_to_write)
            return True, ""

        if _is_stale_info(existing):
            # Verouderde lock (crash) → verwijderen
            try:
                lock_file.unlink(missing_ok=True)
            except OSError:
                pass
            if attempt < _RETRY_COUNT:
                time.sleep(_RETRY_INTERVAL_S)
            continue

        # Lock bezet door actief ander proces → wachten
        if attempt < _RETRY_COUNT:
            time.sleep(_RETRY_INTERVAL_S)

    # Na alle retries nog steeds bezet → foutmelding opbouwen
    last = _read_lock(lock_file)
    if last:
        who  = last.get("username", "?")
        host = last.get("hostname", "?")
        age  = int(time.time() - last.get("timestamp", time.time()))
        return False, (
            f"Het bestand is vergrendeld door {who} op {host} "
            f"(al {age}s geleden).\n"
            f"Wacht tot die sessie klaar is, of neem contact op met die gebruiker."
        )
    return False, "Bestand is vergrendeld door een andere gebruiker."


def release_lock(network_data_path: str) -> None:
    """
    Geef de schrijflock vrij door het lock-bestand te verwijderen.
    Alleen de eigenaar van de lock mag vrijgeven — andere locks blijven staan.
    Fouten worden stilzwijgend genegeerd.
    """
    lock_file = _lock_path(network_data_path)
    existing = _read_lock(lock_file)

    if existing is None:
        return  # Geen lock aanwezig

    if not _is_own_lock(existing):
        return  # Nooit lock van een ander verwijderen

    try:
        lock_file.unlink(missing_ok=True)
    except OSError:
        pass


def read_lock_info(network_data_path: str) -> dict | None:
    """
    Geeft de huidige lock-informatie terug, of None als er geen lock is.
    Bruikbaar voor diagnostiek in de UI.
    """
    return _read_lock(_lock_path(network_data_path))


def is_stale(network_data_path: str) -> bool:
    """
    Geeft True als er een verouderd lock-bestand bestaat.
    Bruikbaar bij opstarten om stale locks te detecteren.
    """
    info = _read_lock(_lock_path(network_data_path))
    if info is None:
        return False
    return _is_stale_info(info)


def cleanup_stale_lock(network_data_path: str) -> bool:
    """
    Verwijdert een verouderd lock-bestand bij opstarten van de app.
    Geeft True terug als een stale lock verwijderd werd.
    Bedoeld om aan te roepen in main.py na het laden van de data.
    """
    lock_file = _lock_path(network_data_path)
    info = _read_lock(lock_file)
    if info is None:
        return False
    if _is_stale_info(info):
        try:
            lock_file.unlink(missing_ok=True)
            return True
        except OSError:
            pass
    return False