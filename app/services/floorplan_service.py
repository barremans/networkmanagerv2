# =============================================================================
# Networkmap_Creator
# File:    app/services/floorplan_service.py
# Role:    Floorplan beheer — SVG opslag, JSON metadata
# Version: 1.3.0
# Author:  Barremans
# Changes: 1.3.0 — update_floorplan_meta() toegevoegd voor naam + beschrijving
#          1.2.0 — outlet_location_key ipv room_id
#                   backward compatible lezen van bestaande room_id data
#                   helpers toegevoegd voor locatie-gebaseerde lookup
#          1.1.0 — gebruikt centrale floorplan helpers uit settings_storage:
#                           get_floorplans_path(), get_floorplans_dir()
#                   robuustere save/load via centrale datamap
#          1.0.0 — Initiële versie
#                   Floorplan JSON opslag
#                   SVG kopiëren naar data map
#                   koppeling aan site en ruimte
#                   mappings voor SVG punten
#
# BELANGRIJK:
# Dit bestand bevat GEEN Qt imports.
# Zelfde architectuur als tracing.py, backup_service.py, sync_service.py
# =============================================================================

import json
import shutil
import uuid
from pathlib import Path

from app.helpers import settings_storage


# ---------------------------------------------------------------------------
# Paden
# ---------------------------------------------------------------------------

def _get_floorplans_file() -> Path:
    """
    Pad naar floorplans.json via centrale settings_storage helper.
    """
    return Path(settings_storage.get_floorplans_path())


def _get_floorplans_dir() -> Path:
    """
    Map waar SVG bestanden opgeslagen worden via centrale settings_storage helper.
    """
    return Path(settings_storage.get_floorplans_dir())


# ---------------------------------------------------------------------------
# Load / Save
# ---------------------------------------------------------------------------

def load_floorplans() -> dict:
    """
    Laad floorplans.json.
    Bij fout of corrupt bestand: geef lege basisstructuur terug.
    """
    path = _get_floorplans_file()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"floorplans": []}
            if "floorplans" not in data or not isinstance(data["floorplans"], list):
                data["floorplans"] = []
            return data
    except Exception:
        return {"floorplans": []}


def save_floorplans(data: dict):
    """
    Sla floorplans.json op.
    """
    path = _get_floorplans_file()

    if not isinstance(data, dict):
        data = {"floorplans": []}

    if "floorplans" not in data or not isinstance(data["floorplans"], list):
        data["floorplans"] = []

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_floorplan(
    site_id: str,
    svg_source: str,
    outlet_location_key: str = "",
    room_id: str = "",
) -> dict:
    """
    Maak nieuw floorplan aan.

    Nieuwe structuur:
        site_id + outlet_location_key

    Backward compatibility:
        room_id blijft optioneel bewaard als oudere code dat nog doorgeeft.
    """
    data = load_floorplans()

    fid = f"fp_{uuid.uuid4().hex[:8]}"

    svg_src = Path(svg_source)
    dest_dir = _get_floorplans_dir()

    dest_name = f"{fid}_{svg_src.name}"
    dest_path = dest_dir / dest_name

    shutil.copy2(svg_src, dest_path)

    floorplan = {
        "id": fid,
        "site_id": site_id,
        "outlet_location_key": outlet_location_key,
        "room_id": room_id,   # legacy / optioneel
        "svg_file": dest_name,
        "mappings": {},       # SVG point -> outlet_id
    }

    data["floorplans"].append(floorplan)
    save_floorplans(data)

    return floorplan


def delete_floorplan(floorplan_id: str):
    """
    Verwijder floorplan + gekoppelde SVG file indien aanwezig.
    """
    data = load_floorplans()
    new_list = []

    for floorplan in data["floorplans"]:
        if floorplan.get("id") == floorplan_id:
            svg_name = floorplan.get("svg_file", "")
            if svg_name:
                svg_path = _get_floorplans_dir() / svg_name
                if svg_path.exists():
                    try:
                        svg_path.unlink()
                    except OSError:
                        pass
        else:
            new_list.append(floorplan)

    data["floorplans"] = new_list
    save_floorplans(data)


def get_floorplan(floorplan_id: str) -> dict | None:
    """
    Zoek floorplan op id.
    """
    data = load_floorplans()

    for floorplan in data["floorplans"]:
        if floorplan.get("id") == floorplan_id:
            return floorplan

    return None


def get_floorplan_for_room(room_id: str) -> dict | None:
    """
    Legacy helper voor oudere code.
    """
    data = load_floorplans()

    for floorplan in data["floorplans"]:
        if floorplan.get("room_id") == room_id:
            return floorplan

    return None


def get_floorplan_for_location(site_id: str, outlet_location_key: str) -> dict | None:
    """
    Zoek floorplan op site + wandpunt locatie key.
    """
    data = load_floorplans()

    for floorplan in data["floorplans"]:
        if (
            floorplan.get("site_id") == site_id
            and floorplan.get("outlet_location_key", "") == outlet_location_key
        ):
            return floorplan

    return None


def get_floorplans_for_site(site_id: str) -> list[dict]:
    """
    Geef alle floorplans voor een site terug.
    """
    data = load_floorplans()
    return [
        floorplan for floorplan in data["floorplans"]
        if floorplan.get("site_id") == site_id
    ]


def update_floorplan_location(
    floorplan_id: str,
    site_id: str,
    outlet_location_key: str,
) -> bool:
    """
    Verplaats of herkoppel een floorplan naar een andere site / wandpuntlocatie.
    """
    data = load_floorplans()

    for floorplan in data["floorplans"]:
        if floorplan.get("id") == floorplan_id:
            floorplan["site_id"] = site_id
            floorplan["outlet_location_key"] = outlet_location_key
            save_floorplans(data)
            return True

    return False


def update_floorplan_meta(
    floorplan_id: str,
    name: str = "",
    description: str = "",
    site_id: str = "",
    outlet_location_key: str = "",
) -> bool:
    """
    Pas naam, beschrijving, site en/of wandpuntlocatie aan van een floorplan.
    Lege strings worden genegeerd (veld blijft ongewijzigd).
    """
    data = load_floorplans()

    for floorplan in data["floorplans"]:
        if floorplan.get("id") == floorplan_id:
            if name:
                floorplan["name"] = name
            if description is not None:
                floorplan["description"] = description
            if site_id:
                floorplan["site_id"] = site_id
            if outlet_location_key:
                floorplan["outlet_location_key"] = outlet_location_key
            save_floorplans(data)
            return True

    return False


# ---------------------------------------------------------------------------
# Mappings
# ---------------------------------------------------------------------------

def set_mapping(floorplan_id: str, svg_point: str, outlet_id: str):
    """
    Koppel SVG punt aan wandpunt.
    """
    data = load_floorplans()

    for floorplan in data["floorplans"]:
        if floorplan.get("id") == floorplan_id:
            mappings = floorplan.setdefault("mappings", {})
            mappings[svg_point] = outlet_id
            save_floorplans(data)
            return


def remove_mapping(floorplan_id: str, svg_point: str):
    """
    Verwijder koppeling voor één SVG punt.
    """
    data = load_floorplans()

    for floorplan in data["floorplans"]:
        if floorplan.get("id") == floorplan_id:
            mappings = floorplan.setdefault("mappings", {})
            if svg_point in mappings:
                del mappings[svg_point]
            save_floorplans(data)
            return


def clear_mappings(floorplan_id: str):
    """
    Wis alle mappings van een floorplan.
    """
    data = load_floorplans()

    for floorplan in data["floorplans"]:
        if floorplan.get("id") == floorplan_id:
            floorplan["mappings"] = {}
            save_floorplans(data)
            return


def get_mapping(floorplan_id: str, svg_point: str) -> str | None:
    """
    Geef gekoppeld outlet_id terug voor een SVG punt.
    """
    floorplan = get_floorplan(floorplan_id)

    if not floorplan:
        return None

    mappings = floorplan.get("mappings", {})
    return mappings.get(svg_point)


def get_mapped_outlet_id(floorplan: dict, svg_point: str) -> str | None:
    """
    Helper voor UI code: haal mapping op uit reeds geladen floorplan dict.
    """
    if not floorplan:
        return None
    return floorplan.get("mappings", {}).get(svg_point)


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def get_svg_path(floorplan: dict) -> Path:
    """
    Volledig pad naar SVG bestand.
    """
    return _get_floorplans_dir() / floorplan.get("svg_file", "")


def svg_exists(floorplan: dict) -> bool:
    """
    Controleer of het gekoppelde SVG bestand bestaat.
    """
    return get_svg_path(floorplan).exists()