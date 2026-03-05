# =============================================================================
# Networkmap_Creator
# File:    app/services/changelog_service.py
# Role:    Logging van wijzigingen in network_data.json naar logs\changelog.json
# Version: 1.0.0
# Author:  Barremans
# Changes: Taak 2 — logging devices, poorten, verbindingen (add/edit/delete)
# =============================================================================

import json
import os
import sys
from datetime import datetime

if getattr(sys, 'frozen', False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_LOGS_DIR       = os.path.join(_BASE_DIR, "logs")
_CHANGELOG_FILE = os.path.join(_LOGS_DIR, "changelog.json")
_MAX_ENTRIES    = 1000

# Ondersteunde entiteiten
ENTITY_DEVICE     = "device"
ENTITY_PORT       = "port"
ENTITY_CONNECTION = "connection"

# Ondersteunde acties
ACTION_ADD    = "add"
ACTION_EDIT   = "edit"
ACTION_DELETE = "delete"


# ---------------------------------------------------------------------------
# Interne hulpfuncties
# ---------------------------------------------------------------------------

def _ensure_logs_dir():
    os.makedirs(_LOGS_DIR, exist_ok=True)


def _load_changelog() -> list:
    try:
        with open(_CHANGELOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def _save_changelog(entries: list) -> bool:
    _ensure_logs_dir()
    tmp_path = _CHANGELOG_FILE + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        import shutil
        shutil.move(tmp_path, _CHANGELOG_FILE)
        return True
    except OSError:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return False


# ---------------------------------------------------------------------------
# Publieke API
# ---------------------------------------------------------------------------

def log_change(
    action: str,
    entity: str,
    entity_id: str,
    label: str,
    details: dict = None,
    user: str = "system"
) -> bool:
    """
    Voeg een wijziging toe aan changelog.json.

    Parameters
    ----------
    action    : "add" | "edit" | "delete"
    entity    : "device" | "port" | "connection"
    entity_id : unieke ID van het object (bv. device["id"])
    label     : leesbare omschrijving (bv. "Switch - Rack A")
    details   : optioneel dict met extra info (bv. {"from": old, "to": new})
    user      : wie de wijziging deed — later gevuld via Fase F
    """
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "action":    action,
        "entity":    entity,
        "entity_id": entity_id,
        "label":     label,
        "user":      user,
        "details":   details or {}
    }

    entries = _load_changelog()
    entries.append(entry)

    # Max 1000 entries — oudste verwijderen
    if len(entries) > _MAX_ENTRIES:
        entries = entries[-_MAX_ENTRIES:]

    return _save_changelog(entries)


def get_changelog(
    entity: str = None,
    action: str = None,
    limit: int = 100
) -> list:
    """
    Geef changelog entries terug, optioneel gefilterd.

    Parameters
    ----------
    entity : filter op entiteit ("device" / "port" / "connection") of None
    action : filter op actie ("add" / "edit" / "delete") of None
    limit  : max aantal terug te geven entries (meest recent eerst)
    """
    entries = _load_changelog()

    if entity:
        entries = [e for e in entries if e.get("entity") == entity]
    if action:
        entries = [e for e in entries if e.get("action") == action]

    # Meest recent eerst
    entries = list(reversed(entries))
    return entries[:limit]


def get_changelog_path() -> str:
    return _CHANGELOG_FILE