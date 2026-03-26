# =============================================================================
# Networkmap_Creator
# File:    app/services/backup_service.py
# Role:    Backup beheer — GEEN Qt imports
# Version: 1.3.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie
#          1.1.0 — F3: has_changes_since_last_backup()
#          1.2.0 — F4: UNC-pad fix — mkdir() niet aanroepen op UNC root
#                  (\\server\share kan niet aangemaakt worden, bestaat al of niet)
#                  Betere foutmeldingen bij rechtenprobleem op UNC-paden
#                  _ensure_dir() helper die UNC-root overslaat
#          1.3.0 — B9: import os toegevoegd (ontbrak — has_changes crashte)
#                  Retry-logica in create_backup() en test_path():
#                  bij tijdelijke netwerk/lock fout: 3 pogingen met 1s wachttijd
#                  _copy_with_retry() helper voor shutil.copy2 + PermissionError
# =============================================================================

import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path


# ------------------------------------------------------------------
# Constanten
# ------------------------------------------------------------------

_BACKUP_FILENAME = "network_data.json"
_HISTORY_DIR     = "history"
_TIMESTAMP_FMT   = "%Y%m%d_%H%M%S"
_RETRY_COUNT     = 3      # B9 — aantal pogingen bij tijdelijke fout
_RETRY_DELAY     = 1.0    # B9 — seconden wachten tussen pogingen


# ------------------------------------------------------------------
# Intern — retry helper
# ------------------------------------------------------------------

def _copy_with_retry(src: str, dst: Path) -> tuple[bool, str]:
    """
    B9 — Kopieer bestand met retry bij tijdelijke lock of netwerkverlies.
    Probeert _RETRY_COUNT keer met _RETRY_DELAY seconden ertussen.
    Geeft (True, "") bij succes, (False, foutmelding) bij definitieve fout.
    """
    last_err = ""
    for attempt in range(1, _RETRY_COUNT + 1):
        try:
            shutil.copy2(src, dst)
            return True, ""
        except PermissionError as e:
            last_err = f"Geen schrijfrechten op: {dst}"
        except FileNotFoundError as e:
            last_err = f"Pad niet gevonden: {dst}"
        except OSError as e:
            last_err = str(e)
        if attempt < _RETRY_COUNT:
            time.sleep(_RETRY_DELAY)
    return False, last_err


# ------------------------------------------------------------------
# Publieke API
# ------------------------------------------------------------------

def has_changes_since_last_backup(source_path: str, config: dict) -> bool:
    """
    Geeft True terug als het bronbestand nieuwer is dan de meest recente backup.
    Geeft ook True terug als er nog geen backups bestaan (eerste keer).

    Parameters:
        source_path — volledig pad naar de lokale network_data.json
        config      — backup sectie uit settings.json

    Gebruik dit om onnodige backups te vermijden:
        if has_changes_since_last_backup(source, config):
            create_backup(source, config)
    """
    if not os.path.exists(source_path):
        return False

    network_path = config.get("network_path", "").strip()
    if not network_path:
        return True   # geen pad → kan niet vergelijken → neem aan dat backup nodig is

    history_dir = Path(network_path) / _HISTORY_DIR
    if not history_dir.exists():
        return True   # nog geen history → eerste backup

    backups = sorted(history_dir.glob("network_data_*.json"))
    if not backups:
        return True   # map bestaat maar is leeg

    latest_backup_mtime = backups[-1].stat().st_mtime
    source_mtime        = os.path.getmtime(source_path)

    # Meer dan 2 seconden nieuwer = er zijn wijzigingen (clock skew tolerantie)
    return (source_mtime - latest_backup_mtime) > 2


def _ensure_dir(path: Path) -> tuple[bool, str]:
    r"""
    F4 — Maak een map aan, maar sla UNC-roots over (\\server\share).
    UNC-roots bestaan al of niet — mkdir() daarop crasht altijd.
    Geeft (True, "") bij succes of als map al bestaat.
    Geeft (False, foutmelding) bij fout.
    """
    parts = path.parts  # bv. ('\\\\', 'server', 'share') of ('\\\\', 'server', 'share', 'submap')
    is_unc_root = (
        len(parts) <= 3
        and str(path).startswith("\\\\")
    )
    if is_unc_root:
        if path.exists():
            return True, ""
        return False, f"UNC-pad niet bereikbaar: {path}"

    try:
        path.mkdir(parents=True, exist_ok=True)
        return True, ""
    except PermissionError:
        return False, f"Geen schrijfrechten op: {path}"
    except FileNotFoundError:
        return False, f"Pad niet gevonden: {path}"
    except Exception as e:
        return False, str(e)


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

    B9 — shutil.copy2 vervangt door _copy_with_retry():
         bij tijdelijke lock of netwerkverlies wordt tot 3x opnieuw geprobeerd.
    """
    if not config.get("enabled", False):
        return True, ""   # backup uitgeschakeld — geen fout

    network_path = config.get("network_path", "").strip()
    if not network_path:
        return False, "Geen backup-pad geconfigureerd. Stel dit in via Instellingen."

    try:
        dest_dir = Path(network_path)
        ok, err = _ensure_dir(dest_dir)
        if not ok:
            return False, err

        # Hoofdkopie: network_data.json in de netwerkmap — met retry
        dest_main = dest_dir / _BACKUP_FILENAME
        ok, err = _copy_with_retry(source_path, dest_main)
        if not ok:
            return False, err

        # History backup met timestamp
        if config.get("keep_history", True):
            history_dir = dest_dir / _HISTORY_DIR
            ok_h, err_h = _ensure_dir(history_dir)
            if not ok_h:
                return False, err_h

            ts      = datetime.now().strftime(_TIMESTAMP_FMT)
            dest_ts = history_dir / f"network_data_{ts}.json"
            ok, err = _copy_with_retry(source_path, dest_ts)   # B9 — ook hier retry
            if not ok:
                return False, err

            # Oudste backups verwijderen als max bereikt is
            _trim_history(history_dir, config.get("max_backups", 10))

        return True, ""

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
    F4 — UNC-paden worden correct afgehandeld: geen mkdir op UNC-root.
    B9 — Schrijftest met retry bij tijdelijke lock.
    Returns (True, "") als OK, (False, reden) als niet.
    """
    if not network_path or not network_path.strip():
        return False, "Geen pad opgegeven."
    try:
        p = Path(network_path.strip())

        ok, err = _ensure_dir(p)
        if not ok:
            return False, err

        # B9 — Schrijftest met retry
        test_file = p / ".write_test"
        last_err  = ""
        for attempt in range(1, _RETRY_COUNT + 1):
            try:
                test_file.write_text("test")
                test_file.unlink()
                return True, ""
            except PermissionError:
                last_err = f"Geen schrijfrechten op: {network_path}"
            except Exception as e:
                last_err = str(e)
            if attempt < _RETRY_COUNT:
                time.sleep(_RETRY_DELAY)
        return False, last_err

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