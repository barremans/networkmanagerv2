# =============================================================================
# Networkmap_Creator
# File:    app/services/backup_service.py
# Role:    Backup beheer — GEEN Qt imports
# Version: 1.0.0
# Author:  Barremans
# =============================================================================

import json
import shutil
from datetime import datetime
from pathlib import Path


# ------------------------------------------------------------------
# Constanten
# ------------------------------------------------------------------

_BACKUP_FILENAME = "network_data.json"
_HISTORY_DIR     = "history"
_TIMESTAMP_FMT   = "%Y%m%d_%H%M%S"


# ------------------------------------------------------------------
# Publieke API
# ------------------------------------------------------------------

def create_backup(source_path: str, config: dict) -> tuple[bool, str]:
    """
    Maakt een backup van network_data.json naar de geconfigureerde netwerkmap.

    Parameters:
        source_path — volledig pad naar de lokale network_data.json
        config      — backup sectie uit settings.json:
                      {
                        "enabled":      bool,
                        "network_path": str,
                        "keep_history": bool,
                        "max_backups":  int
                      }

    Returns:
        (True,  "")           bij succes
        (False, foutmelding)  bij fout
    """
    if not config.get("enabled", False):
        return True, ""   # backup uitgeschakeld — geen fout

    network_path = config.get("network_path", "").strip()
    if not network_path:
        return False, "Geen backup-pad geconfigureerd. Stel dit in via Instellingen."

    try:
        dest_dir = Path(network_path)
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Hoofdkopie: network_data.json in de netwerkmap
        dest_main = dest_dir / _BACKUP_FILENAME
        shutil.copy2(source_path, dest_main)

        # History backup met timestamp
        if config.get("keep_history", True):
            history_dir = dest_dir / _HISTORY_DIR
            history_dir.mkdir(exist_ok=True)

            ts       = datetime.now().strftime(_TIMESTAMP_FMT)
            dest_ts  = history_dir / f"network_data_{ts}.json"
            shutil.copy2(source_path, dest_ts)

            # Oudste backups verwijderen als max bereikt is
            _trim_history(history_dir, config.get("max_backups", 10))

        return True, ""

    except PermissionError:
        return False, f"Geen schrijfrechten op: {network_path}"
    except FileNotFoundError:
        return False, f"Pad niet gevonden: {network_path}"
    except Exception as e:
        return False, str(e)


def list_backups(config: dict) -> list[dict]:
    """
    Geeft een lijst van beschikbare history-backups terug.

    Returns lijst van dicts:
        { "filename": str, "timestamp": str, "path": str }
    Gesorteerd van nieuwste naar oudste.
    """
    network_path = config.get("network_path", "").strip()
    if not network_path:
        return []

    history_dir = Path(network_path) / _HISTORY_DIR
    if not history_dir.exists():
        return []

    backups = []
    for f in sorted(history_dir.glob("network_data_*.json"), reverse=True):
        # Haal timestamp op uit bestandsnaam
        stem = f.stem  # bv. "network_data_20260222_143500"
        ts_part = stem.replace("network_data_", "")
        try:
            dt = datetime.strptime(ts_part, _TIMESTAMP_FMT)
            ts_label = dt.strftime("%d/%m/%Y %H:%M:%S")
        except ValueError:
            ts_label = ts_part
        backups.append({
            "filename":  f.name,
            "timestamp": ts_label,
            "path":      str(f),
        })
    return backups


def restore_backup(backup_path: str, dest_path: str) -> tuple[bool, str]:
    """
    Herstelt een backup naar de lokale network_data.json locatie.

    Returns (True, "") bij succes, (False, foutmelding) bij fout.
    """
    try:
        shutil.copy2(backup_path, dest_path)
        return True, ""
    except Exception as e:
        return False, str(e)


def test_path(network_path: str) -> tuple[bool, str]:
    """
    Test of een netwerkpad bereikbaar en beschrijfbaar is.
    Returns (True, "") als OK, (False, reden) als niet.
    """
    if not network_path or not network_path.strip():
        return False, "Geen pad opgegeven."
    try:
        p = Path(network_path.strip())
        p.mkdir(parents=True, exist_ok=True)
        test_file = p / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
        return True, ""
    except PermissionError:
        return False, f"Geen schrijfrechten op: {network_path}"
    except FileNotFoundError:
        return False, f"Pad niet gevonden: {network_path}"
    except Exception as e:
        return False, str(e)


# ------------------------------------------------------------------
# Intern
# ------------------------------------------------------------------

def _trim_history(history_dir: Path, max_backups: int):
    """Verwijdert oudste backups als het maximum overschreden wordt."""
    files = sorted(history_dir.glob("network_data_*.json"))
    while len(files) > max_backups:
        files[0].unlink()
        files = files[1:]