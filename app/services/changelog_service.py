# =============================================================================
# Networkmap_Creator
# File:    app/services/changelog_service.py
# Role:    Append-only wijzigingslog voor handmatige acties — K3
#          Schrijft naar changelog.jsonl in de data-map.
#          Rotatie: max 3 versies (changelog.jsonl + .1 + .2); oudste wordt
#          automatisch gewist zodat de log niet onbeperkt groeit.
# Version: 1.0.0
# Author:  Barremans
# Changes: 1.0.0 — K3: initiële versie.
#                  append_entry(), load_entries(), get_changelog_path(),
#                  get_all_changelog_paths(), _rotate().
# =============================================================================

import json
import os
from datetime import datetime
from pathlib import Path

# Maximaal aantal versies dat bewaard wordt (huidig + rotaties)
_MAX_VERSIONS  = 3

# Maximaal aantal entries dat load_entries() teruggeeft
_MAX_LOAD      = 500

# Bestandsnaam in de data-map
_CHANGELOG_FILE = "changelog.jsonl"

# Geldige actietypes (informatief — niet afgedwongen bij append)
ACTION_CREATE = "create"
ACTION_UPDATE = "update"
ACTION_DELETE = "delete"
ACTION_APPROVE = "approve"
ACTION_REOPEN  = "reopen"

# Aliassen die main_window.py al gebruikt (Taak2-stubs)
ACTION_ADD  = ACTION_CREATE
ACTION_EDIT = ACTION_UPDATE

# Entity-type constanten
ENTITY_DEVICE     = "device"
ENTITY_CONNECTION = "connection"
ENTITY_ENDPOINT   = "endpoint"
ENTITY_WALL_OUTLET = "wall_outlet"
ENTITY_PORT       = "port"
ENTITY_SITE       = "site"
ENTITY_ROOM       = "room"
ENTITY_RACK       = "rack"
ENTITY_COMPANY    = "company"
ENTITY_VLAN       = "vlan"
ENTITY_APPROVAL   = "approval"


# ---------------------------------------------------------------------------
# Pad helpers
# ---------------------------------------------------------------------------

def get_changelog_path() -> str:
    """Geeft het pad naar het actieve changelog.jsonl bestand."""
    from app.helpers.settings_storage import get_data_dir
    return os.path.join(get_data_dir(), _CHANGELOG_FILE)


def get_all_changelog_paths() -> list[str]:
    """
    Geeft alle aanwezige changelog-bestanden terug, nieuwste eerst:
        changelog.jsonl, changelog.1.jsonl, changelog.2.jsonl
    Alleen bestaande bestanden worden teruggegeven.
    """
    base = Path(get_changelog_path())
    candidates = [base] + [
        base.with_suffix(f".{i}.jsonl") for i in range(1, _MAX_VERSIONS)
    ]
    return [str(p) for p in candidates if p.exists()]


# ---------------------------------------------------------------------------
# Rotatie
# ---------------------------------------------------------------------------

def _rotate() -> None:
    """
    Roteert de changelog-bestanden wanneer een nieuwe versie gestart wordt.
    Werking (max 3 versies: index 0 t/m 2):
        changelog.2.jsonl  →  verwijderd   (was oudste)
        changelog.1.jsonl  →  changelog.2.jsonl
        changelog.jsonl    →  changelog.1.jsonl
        (nieuw leeg)       →  changelog.jsonl

    Fouten worden stilzwijgend genegeerd.
    """
    try:
        base = Path(get_changelog_path())
        slots = [base] + [
            base.with_suffix(f".{i}.jsonl") for i in range(1, _MAX_VERSIONS)
        ]
        # Verwijder oudste
        if slots[-1].exists():
            slots[-1].unlink()
        # Schuif naar rechts (van oud naar nieuw)
        for i in range(len(slots) - 1, 0, -1):
            if slots[i - 1].exists():
                slots[i - 1].rename(slots[i])
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Schrijven
# ---------------------------------------------------------------------------

_ROTATE_AFTER = 1_000   # entries per bestand voor automatische rotatie

def append_entry(
    action:      str,
    entity_type: str,
    entity_id:   str,
    label:       str,
    user:        str,
    extra:       dict | None = None,
) -> None:
    """
    Voegt één wijzigingsregel toe aan changelog.jsonl.

    Parameters:
        action       — "create" | "update" | "delete" | "approve" | "reopen" | vrij
        entity_type  — bv. "device", "port", "connection", "wall_outlet",
                       "endpoint", "site", "room", "rack", "company", "vlan",
                       "approval"
        entity_id    — ID van het gewijzigde object (mag leeg zijn)
        label        — leesbare omschrijving, bv. "Switch S1 — naam gewijzigd"
        user         — Azure AD-naam of "offline"
        extra        — optioneel dict met aanvullende velden (bv. old/new waarden)

    Roteert automatisch als het huidige bestand ≥ _ROTATE_AFTER entries bevat.
    Fouten worden stilzwijgend genegeerd zodat de app nooit faalt door logging.
    """
    try:
        path = Path(get_changelog_path())
        path.parent.mkdir(parents=True, exist_ok=True)

        # Roteer als huidig bestand te groot is
        if path.exists():
            with open(path, encoding="utf-8") as f:
                line_count = sum(1 for _ in f)
            if line_count >= _ROTATE_AFTER:
                _rotate()

        entry: dict = {
            "ts":          datetime.now().isoformat(timespec="seconds"),
            "action":      action,
            "entity_type": entity_type,
            "entity_id":   entity_id or "",
            "label":       label,
            "user":        user or "unknown",
        }
        if extra:
            entry["extra"] = extra

        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    except Exception:
        pass  # logging mag de app nooit laten crashen


# ---------------------------------------------------------------------------
# Lezen
# ---------------------------------------------------------------------------

def load_entries(max_entries: int = _MAX_LOAD) -> list[dict]:
    """
    Laadt de meest recente entries uit alle changelog-bestanden.
    Resultaat is gesorteerd van nieuwste naar oudste.

    max_entries: maximaal aantal entries dat teruggegeven wordt (default 500).
    """
    entries: list[dict] = []
    for path in get_all_changelog_paths():
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except Exception:
            pass

    # Nieuwste eerst — sorteer op "ts" veld
    entries.sort(key=lambda e: e.get("ts", ""), reverse=True)
    return entries[:max_entries]


# ---------------------------------------------------------------------------
# Hoog-niveau wrapper — gebruikt door main_window.py (Taak2 API)
# ---------------------------------------------------------------------------

def _get_current_user() -> str:
    """Haalt de huidige gebruikersnaam op zonder Qt-afhankelijkheid."""
    try:
        from app.security.permissions_networkmap import get_cached_user
        u = get_cached_user() or {}
        name = (u.get("displayName") or u.get("userPrincipalName") or "").strip()
        if name:
            return name
    except Exception:
        pass
    try:
        import getpass
        return getpass.getuser()
    except Exception:
        return "unknown"


def log_change(
    action:    str,
    entity:    str,
    entity_id: str = "",
    label:     str = "",
    details:   dict | None = None,
    user:      str = "",
) -> None:
    """
    Hoog-niveau wrapper rond append_entry voor gebruik in main_window.py.

    Parameters:
        action     — gebruik ACTION_ADD / ACTION_EDIT / ACTION_DELETE /
                     ACTION_APPROVE / ACTION_REOPEN (of vrije string)
        entity     — gebruik ENTITY_* constante (bijv. ENTITY_DEVICE)
        entity_id  — ID van het object
        label      — leesbare omschrijving
        details    — optioneel dict met extra info (bv. {"cable_type": "utp"})
        user       — optioneel; wordt automatisch opgehaald indien leeg
    """
    append_entry(
        action=action,
        entity_type=entity,
        entity_id=entity_id,
        label=label,
        user=user or _get_current_user(),
        extra=details or None,
    )