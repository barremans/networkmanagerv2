# =============================================================================
# Networkmap_Creator
# File:    app/services/import_export_service.py
# Role:    JSON import en export — GEEN Qt imports
# Version: 1.0.0
# Author:  Barremans
# =============================================================================

import json
import shutil
from datetime import date
from pathlib import Path

REQUIRED_KEYS = ["version", "sites", "devices", "ports", "endpoints", "connections"]


# ------------------------------------------------------------------
# Export
# ------------------------------------------------------------------

def export_to_file(data: dict, filepath: str) -> bool:
    """
    Exporteert de volledige network_data naar een gekozen bestandslocatie.
    Returns True bij succes, False bij fout.
    """
    try:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def suggested_filename() -> str:
    """Geeft een suggestie voor de exportbestandsnaam."""
    return f"networkmap_export_{date.today().isoformat()}.json"


# ------------------------------------------------------------------
# Import
# ------------------------------------------------------------------

def validate(data: dict) -> tuple[bool, str]:
    """
    Valideert een geïmporteerd data dict.
    Returns (True, "") bij geldig, (False, reden) bij ongeldig.
    """
    for key in REQUIRED_KEYS:
        if key not in data:
            return False, f"Verplichte sleutel ontbreekt: '{key}'"
    if not isinstance(data.get("sites"), list):
        return False, "'sites' moet een lijst zijn."
    if not isinstance(data.get("devices"), list):
        return False, "'devices' moet een lijst zijn."
    return True, ""


def import_replace(filepath: str) -> tuple[dict | None, str]:
    """
    Laadt een JSON bestand en vervangt de huidige data volledig.
    Returns (data, "") bij succes, (None, foutmelding) bij fout.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        ok, reason = validate(data)
        if not ok:
            return None, reason
        return data, ""
    except json.JSONDecodeError as e:
        return None, f"Ongeldig JSON: {e}"
    except Exception as e:
        return None, str(e)


def import_merge(filepath: str, current: dict) -> tuple[dict | None, str, dict]:
    """
    Laadt een JSON bestand en voegt objecten samen met de huidige data.
    Bestaande IDs worden overgeslagen.

    Returns (merged_data, "", stats) bij succes,
            (None, foutmelding, {}) bij fout.

    stats = {"added": int, "skipped": int}
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            incoming = json.load(f)
        ok, reason = validate(incoming)
        if not ok:
            return None, reason, {}
    except json.JSONDecodeError as e:
        return None, f"Ongeldig JSON: {e}", {}
    except Exception as e:
        return None, str(e), {}

    added   = 0
    skipped = 0

    # Bouw sets van bestaande IDs
    existing_ids = _collect_all_ids(current)

    merged = {k: list(v) if isinstance(v, list) else v
              for k, v in current.items()}

    # Voeg lijsten samen, sla bestaande IDs over
    for key in ("devices", "ports", "endpoints", "connections"):
        for obj in incoming.get(key, []):
            obj_id = obj.get("id", "")
            if obj_id and obj_id in existing_ids:
                skipped += 1
            else:
                merged.setdefault(key, []).append(obj)
                existing_ids.add(obj_id)
                added += 1

    # Sites samenvoegen — recursief per site/room/rack
    for inc_site in incoming.get("sites", []):
        site_id = inc_site.get("id", "")
        existing_site = next(
            (s for s in merged.get("sites", []) if s["id"] == site_id), None
        )
        if existing_site is None:
            merged.setdefault("sites", []).append(inc_site)
            added += 1
        else:
            # Site bestaat al — ruimtes samenvoegen
            for inc_room in inc_site.get("rooms", []):
                room_id = inc_room.get("id", "")
                ex_room = next(
                    (r for r in existing_site.get("rooms", [])
                     if r["id"] == room_id), None
                )
                if ex_room is None:
                    existing_site.setdefault("rooms", []).append(inc_room)
                    added += 1
                else:
                    # Ruimte bestaat — racks samenvoegen
                    for inc_rack in inc_room.get("racks", []):
                        rack_id = inc_rack.get("id", "")
                        ex_rack = next(
                            (r for r in ex_room.get("racks", [])
                             if r["id"] == rack_id), None
                        )
                        if ex_rack is None:
                            ex_room.setdefault("racks", []).append(inc_rack)
                            added += 1
                        else:
                            skipped += 1
                    # Wandpunten samenvoegen
                    for wo in inc_room.get("wall_outlets", []):
                        if wo.get("id") not in existing_ids:
                            ex_room.setdefault("wall_outlets", []).append(wo)
                            added += 1
                        else:
                            skipped += 1

    return merged, "", {"added": added, "skipped": skipped}


def _collect_all_ids(data: dict) -> set:
    """Verzamelt alle IDs uit de huidige data voor conflict-detectie."""
    ids = set()
    for key in ("devices", "ports", "endpoints", "connections"):
        for obj in data.get(key, []):
            if obj.get("id"):
                ids.add(obj["id"])
    for site in data.get("sites", []):
        ids.add(site.get("id", ""))
        for room in site.get("rooms", []):
            ids.add(room.get("id", ""))
            for rack in room.get("racks", []):
                ids.add(rack.get("id", ""))
            for wo in room.get("wall_outlets", []):
                ids.add(wo.get("id", ""))
    return ids