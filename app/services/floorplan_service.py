# =============================================================================
# Networkmap_Creator
# File:    app/services/floorplan_service.py
# Role:    Floorplan beheer — SVG opslag, JSON metadata
# Version: 1.5.0
# Author:  Barremans
# Changes: 1.5.0 — G-OPEN-5/6: replace_svg() toegevoegd
#                  vervangt SVG bestand + updatet svg_file in JSON
#                  verwijdert automatisch verouderde mappings (G-OPEN-6)
#                  via floorplan_svg_service.detect_point_labels()
#          1.4.0 — create_floorplan: naam + description parameters toegevoegd
#          1.3.0 — update_floorplan_meta() toegevoegd
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
    name: str = "",
    description: str = "",
) -> dict:
    """
    Maak nieuw floorplan aan.
    """
    data = load_floorplans()

    fid = f"fp_{uuid.uuid4().hex[:8]}"

    svg_src  = Path(svg_source)
    dest_dir = _get_floorplans_dir()
    dest_name = f"{fid}_{svg_src.name}"
    dest_path = dest_dir / dest_name

    shutil.copy2(svg_src, dest_path)

    floorplan = {
        "id":                  fid,
        "site_id":             site_id,
        "outlet_location_key": outlet_location_key,
        "room_id":             room_id,        # legacy / optioneel
        "name":                name,
        "description":         description,
        "svg_file":            dest_name,
        "mappings":            {},
    }

    data["floorplans"].append(floorplan)
    save_floorplans(data)

    return floorplan


def replace_svg(floorplan_id: str, new_svg_source: str) -> tuple[bool, str, list[str]]:
    """
    G-OPEN-5/6 — Vervang het SVG bestand van een bestaand grondplan.

    Stappen:
    1. Kopieer nieuwe SVG naar de floorplans map met een nieuw bestandsnaam
    2. Verwijder het oude SVG bestand
    3. Update svg_file in floorplans.json
    4. Verwijder mappings waarvan het SVG punt niet meer bestaat (G-OPEN-6)

    Parameters:
        floorplan_id    — id van het te updaten grondplan
        new_svg_source  — volledig pad naar het nieuwe SVG bestand

    Returns:
        (True,  "",    removed_mappings)  bij succes
        (False, fout,  [])               bij fout
        removed_mappings: lijst van SVG punt labels waarvan de mapping verwijderd werd
    """
    from app.services import floorplan_svg_service

    data = load_floorplans()
    floorplan = None
    for fp in data["floorplans"]:
        if fp.get("id") == floorplan_id:
            floorplan = fp
            break

    if not floorplan:
        return False, f"Grondplan niet gevonden: {floorplan_id}", []

    src = Path(new_svg_source)
    if not src.exists() or not src.is_file():
        return False, f"Bestand niet gevonden: {new_svg_source}", []

    dest_dir  = _get_floorplans_dir()
    old_name  = floorplan.get("svg_file", "")
    new_name  = f"{floorplan_id}_{src.name}"
    dest_path = dest_dir / new_name

    try:
        shutil.copy2(src, dest_path)
    except Exception as e:
        return False, str(e), []

    # Verwijder oud SVG bestand (alleen als naam verschilt)
    if old_name and old_name != new_name:
        old_path = dest_dir / old_name
        if old_path.exists():
            try:
                old_path.unlink()
            except OSError:
                pass

    # Update svg_file in JSON
    floorplan["svg_file"] = new_name

    # G-OPEN-6 — verwijder verouderde mappings
    removed: list[str] = []
    try:
        new_labels = set(floorplan_svg_service.detect_point_labels(str(dest_path)))
        mappings   = floorplan.get("mappings", {})
        stale      = [pt for pt in list(mappings.keys()) if pt not in new_labels]
        for pt in stale:
            del mappings[pt]
            removed.append(pt)
    except Exception:
        pass  # detectie mislukt → mappings ongemoeid laten

    save_floorplans(data)
    return True, "", removed


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