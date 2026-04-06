# =============================================================================
# Networkmap_Creator
# File:    app/services/import_export_service.py
# Role:    JSON import en export — GEEN Qt imports
# Version: 2.0.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie
#          2.0.0 — Export uitgebreid naar map (network_data + settings +
#                  floorplans.json + floorplans/ + vlan_config.json)
#                  Import replace: volledige map inlezen
#                  Import merge: blijft werken op network_data.json alleen
#                  suggested_dirname() toegevoegd
# =============================================================================

import json
import os
import shutil
from datetime import date
from pathlib import Path

REQUIRED_KEYS = ["version", "sites", "devices", "ports", "endpoints", "connections"]

# Vaste bestandsnamen binnen een export-map
_FILE_NETWORK   = "network_data.json"
_FILE_SETTINGS  = "settings.json"
_FILE_FLOORPLAN = "floorplans.json"
_DIR_FLOORPLAN  = "floorplans"
_FILE_VLAN      = "vlan_config.json"


# ------------------------------------------------------------------
# Paden helpers
# ------------------------------------------------------------------

def _get_paths() -> dict:
    """Geeft alle relevante lokale paden terug via settings_storage."""
    from app.helpers import settings_storage
    return {
        "network":        settings_storage.get_network_data_path(),
        "settings":       settings_storage.get_settings_path(),
        "floorplans":     settings_storage.get_floorplans_path(),
        "floorplans_dir": settings_storage.get_floorplans_dir(),
        "vlan":           settings_storage.get_vlan_config_path(),
    }


# ------------------------------------------------------------------
# Export
# ------------------------------------------------------------------

def export_to_dir(dest_dir: str) -> tuple[bool, str]:
    """
    Exporteert alle data naar een map:
        <dest_dir>/
            network_data.json
            settings.json
            floorplans.json
            floorplans/
            vlan_config.json

    Returns (True, "") bij succes, (False, foutmelding) bij fout.
    """
    try:
        paths = _get_paths()
        d = Path(dest_dir)
        d.mkdir(parents=True, exist_ok=True)

        # network_data.json
        src = Path(paths["network"])
        if src.is_file():
            shutil.copy2(src, d / _FILE_NETWORK)

        # settings.json
        src = Path(paths["settings"])
        if src.is_file():
            shutil.copy2(src, d / _FILE_SETTINGS)

        # floorplans.json
        src = Path(paths["floorplans"])
        if src.is_file():
            shutil.copy2(src, d / _FILE_FLOORPLAN)

        # floorplans/ map
        src = Path(paths["floorplans_dir"])
        if src.is_dir():
            dst_fp = d / _DIR_FLOORPLAN
            if dst_fp.exists():
                shutil.rmtree(dst_fp)
            shutil.copytree(src, dst_fp)

        # vlan_config.json
        src = Path(paths["vlan"])
        if src.is_file():
            shutil.copy2(src, d / _FILE_VLAN)

        return True, ""
    except Exception as e:
        import traceback
        return False, traceback.format_exc()


def suggested_dirname() -> str:
    """Geeft een suggestie voor de exportmapnaam."""
    return f"networkmap_export_{date.today().isoformat()}"


# Achterwaartse compatibiliteit — export_to_file blijft werken
def export_to_file(data: dict, filepath: str) -> bool:
    """Legacy: exporteert alleen network_data naar één JSON bestand."""
    try:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def suggested_filename() -> str:
    """Legacy: suggestie voor enkelvoudige JSON export."""
    return f"networkmap_export_{date.today().isoformat()}.json"


# ------------------------------------------------------------------
# Import
# ------------------------------------------------------------------

def validate(data: dict) -> tuple[bool, str]:
    """
    Valideert een geïmporteerd network_data dict.
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


def is_export_dir(path: str) -> bool:
    """Geeft True als de map een geldige export-map is (bevat network_data.json)."""
    return (Path(path) / _FILE_NETWORK).is_file()


def import_replace_dir(src_dir: str) -> tuple[bool, str]:
    """
    Herstelt een volledige export-map naar de lokale installatie.
    Kopieert: network_data.json, settings.json, floorplans.json,
              floorplans/, vlan_config.json — wat aanwezig is.

    Returns (True, "") bij succes, (False, foutmelding) bij fout.
    """
    try:
        paths = _get_paths()
        d = Path(src_dir)

        if not d.is_dir():
            return False, f"Map niet gevonden: {src_dir}"
        if not (d / _FILE_NETWORK).is_file():
            return False, f"Geen geldige export-map: network_data.json ontbreekt in {src_dir}"

        # network_data.json — valideren voor kopiëren
        with open(d / _FILE_NETWORK, encoding="utf-8") as f:
            nd = json.load(f)
        ok, reason = validate(nd)
        if not ok:
            return False, f"network_data.json ongeldig: {reason}"

        shutil.copy2(d / _FILE_NETWORK, paths["network"])

        src = d / _FILE_SETTINGS
        if src.is_file():
            shutil.copy2(src, paths["settings"])

        src = d / _FILE_FLOORPLAN
        if src.is_file():
            shutil.copy2(src, paths["floorplans"])

        src = d / _DIR_FLOORPLAN
        if src.is_dir():
            dst = Path(paths["floorplans_dir"])
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

        src = d / _FILE_VLAN
        if src.is_file():
            shutil.copy2(src, paths["vlan"])

        return True, ""
    except Exception:
        import traceback
        return False, traceback.format_exc()


def import_replace(filepath: str) -> tuple[dict | None, str]:
    """
    Legacy: laadt een enkelvoudig JSON bestand en vervangt network_data.
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
    Laadt een JSON bestand en voegt network_data samen met de huidige data.
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

    existing_ids = _collect_all_ids(current)
    merged = {k: list(v) if isinstance(v, list) else v
              for k, v in current.items()}

    for key in ("devices", "ports", "endpoints", "connections"):
        for obj in incoming.get(key, []):
            obj_id = obj.get("id", "")
            if obj_id and obj_id in existing_ids:
                skipped += 1
            else:
                merged.setdefault(key, []).append(obj)
                existing_ids.add(obj_id)
                added += 1

    for inc_site in incoming.get("sites", []):
        site_id = inc_site.get("id", "")
        existing_site = next(
            (s for s in merged.get("sites", []) if s["id"] == site_id), None
        )
        if existing_site is None:
            merged.setdefault("sites", []).append(inc_site)
            added += 1
        else:
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
                    for wo in inc_room.get("wall_outlets", []):
                        if wo.get("id") not in existing_ids:
                            ex_room.setdefault("wall_outlets", []).append(wo)
                            added += 1
                        else:
                            skipped += 1

    return merged, "", {"added": added, "skipped": skipped}


def _collect_all_ids(data: dict) -> set:
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