# =============================================================================
# Networkmap_Creator
# File:    app/services/sync_service.py
# Role:    Synchronisatie lokaal ↔ netwerk — GEEN Qt imports
# Version: 1.0.0
# Author:  Barremans
# Changes: 1.0.0 — F3: lokaal ↔ netwerk sync op basis van bestandstimestamp
#                  check_sync()  → bepaal richting (push/pull/equal/unavailable)
#                  sync()        → voer sync uit
#                  get_sync_status_label() → leesbaar statuslabel voor UI
# =============================================================================
#
# Sync logica:
#   lokaal nieuwer  → push: lokaal → netwerk kopiëren
#   netwerk nieuwer → pull: netwerk → lokaal kopiëren
#   gelijk          → geen actie
#   netwerk niet bereikbaar → geen actie, lokaal blijft actief
#
# Timestamp vergelijking via os.path.getmtime() — seconde-nauwkeurig.
# Verschil < SYNC_TOLERANCE_S wordt beschouwd als "gelijk" (clock skew).
# =============================================================================

import os
import shutil

_NETWORK_FILENAME  = "network_data.json"
_SYNC_TOLERANCE_S  = 2   # seconden verschil wordt genegeerd (clock skew tussen machines)


# ---------------------------------------------------------------------------
# Publieke API
# ---------------------------------------------------------------------------

def check_sync(local_path: str, network_dir: str) -> str:
    """
    Vergelijk lokaal bestand met netwerkbestand op basis van mtime.

    Returns één van:
        "push"                — lokaal nieuwer → naar netwerk kopiëren
        "pull"                — netwerk nieuwer → lokaal updaten
        "equal"               — bestanden zijn even oud (binnen tolerantie)
        "network_unavailable" — netwerkpad niet bereikbaar
        "network_missing"     — netwerkpad bereikbaar maar bestand bestaat nog niet
        "local_missing"       — lokaal bestand bestaat niet (onverwacht)
    """
    if not _path_accessible(network_dir):
        return "network_unavailable"

    network_path = os.path.join(network_dir, _NETWORK_FILENAME)

    if not os.path.exists(local_path):
        return "local_missing"

    if not os.path.exists(network_path):
        return "network_missing"

    local_mtime   = os.path.getmtime(local_path)
    network_mtime = os.path.getmtime(network_path)
    diff          = local_mtime - network_mtime

    if abs(diff) <= _SYNC_TOLERANCE_S:
        return "equal"
    elif diff > 0:
        return "push"
    else:
        return "pull"


def sync(local_path: str, network_dir: str) -> tuple[str, bool, str]:
    """
    Voer sync uit tussen lokaal en netwerk.

    Returns (actie, success, foutmelding):
        actie  : "push" | "pull" | "equal" | "network_unavailable" | "network_missing"
        success: True als actie succesvol uitgevoerd of niet nodig
        fout   : foutmelding bij success=False, anders ""
    """
    action = check_sync(local_path, network_dir)

    if action in ("equal", "network_unavailable", "local_missing"):
        return action, True, ""

    network_path = os.path.join(network_dir, _NETWORK_FILENAME)

    try:
        if action == "push" or action == "network_missing":
            # Lokaal → netwerk
            os.makedirs(network_dir, exist_ok=True)
            _safe_copy(local_path, network_path)
            return "push", True, ""

        elif action == "pull":
            # Netwerk → lokaal
            _safe_copy(network_path, local_path)
            return "pull", True, ""

    except Exception as e:
        return action, False, str(e)

    return action, True, ""


def get_sync_status_label(action: str) -> str:
    """Geef een leesbaar Nederlandstalig statuslabel terug voor de sync actie."""
    return {
        "push":                "↑  Lokaal gekopieerd naar netwerk",
        "pull":                "↓  Netwerkversie geladen (nieuwer dan lokaal)",
        "equal":               "✓  Lokaal en netwerk zijn gesynchroniseerd",
        "network_unavailable": "⚠  Netwerk niet bereikbaar — lokaal actief",
        "network_missing":     "↑  Netwerk bestand aangemaakt (eerste sync)",
        "local_missing":       "⚠  Lokaal bestand niet gevonden",
    }.get(action, f"?  {action}")


def needs_push(local_path: str, network_dir: str) -> bool:
    """Snelle check: is lokaal bestand nieuwer dan het netwerkbestand?"""
    return check_sync(local_path, network_dir) in ("push", "network_missing")


# ---------------------------------------------------------------------------
# Intern
# ---------------------------------------------------------------------------

def _path_accessible(path: str) -> bool:
    if not path or not path.strip():
        return False
    try:
        return os.path.isdir(path) and os.access(path, os.R_OK | os.W_OK)
    except OSError:
        return False


def _safe_copy(src: str, dst: str):
    """Kopieer via tijdelijk bestand om corruptie te voorkomen bij onderbreking."""
    tmp = dst + ".tmp"
    try:
        shutil.copy2(src, tmp)
        shutil.move(tmp, dst)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise