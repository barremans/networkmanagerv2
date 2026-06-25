# =============================================================================
# Networkmap_Creator
# File:    app/services/import_export_service.py
# Role:    JSON import en export — GEEN Qt imports
# Version: 2.3.0
# Author:  Barremans
# Changes: 2.3.0 — K1: write_export_info() toegevoegd — export_info.txt
#                  wordt aangemaakt bij elke succesvolle map-export
#                  (export_to_dir + export_company_to_dir). Aanroeper
#                  geeft optioneel app_version en exported_by mee.
#          2.2.0 — import_replace_dir: auto-migratie v1→v2
#                  v1 data krijgt automatisch company 'Geïmporteerd bedrijf'
#                  zodat app altijd met v2 structuur opstart na replace.
#          2.1.0 — Bedrijfslogica (v2 JSON):
#                  · export_company_to_dir(): export per bedrijf
#                  · import_merge(): fix voor v2 companies[] structuur
#                  · import_merge(): auto-migratie v1→v2 bij import
#                  · _migrate_v1_to_v2(): inline migratie zonder Qt
#                  · _merge_companies(): companies[] samenvoegen
#                  · _collect_all_ids(): bedrijfs-IDs toegevoegd
#          2.0.1 — Fix: validate() accepteert v2 (companies ipv sites)
#          2.0.0 — Export uitgebreid naar map (network_data + settings +
#                  floorplans.json + floorplans/ + vlan_config.json)
#                  Import replace: volledige map inlezen
#                  Import merge: blijft werken op network_data.json alleen
#                  suggested_dirname() toegevoegd
#          1.0.0 — Initiële versie
# =============================================================================

import json
import os
import shutil
import datetime
from datetime import date
from pathlib import Path
from app.helpers.settings_storage import get_all_sites, get_all_companies

REQUIRED_KEYS = ["version", "sites", "devices", "ports", "endpoints", "connections"]

# Vaste bestandsnamen binnen een export-map
_FILE_NETWORK   = "network_data.json"
_FILE_SETTINGS  = "settings.json"
_FILE_FLOORPLAN = "floorplans.json"
_DIR_FLOORPLAN  = "floorplans"
_FILE_VLAN      = "vlan_config.json"
_FILE_INFO      = "export_info.txt"


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
# Export-info bestand (K1)
# ------------------------------------------------------------------

def write_export_info(
    dest_dir: str,
    scope: str = "full",
    company_name: str = "",
    app_version: str = "",
    exported_by: str = "",
) -> None:
    """
    Schrijft export_info.txt in dest_dir met metadata over de export:
    tijdstip, scope, app-versie en gebruiker.

    Wordt aangeroepen na elke succesvolle map-export.
    Fouten worden stilzwijgend genegeerd zodat de export zelf nooit faalt.

    Args:
        dest_dir:      Doelmap (zelfde als de exportmap).
        scope:         "full" of "company" — geeft aan wat geëxporteerd is.
        company_name:  Bedrijfsnaam bij scope="company", anders leeg.
        app_version:   App-versienummer (bijv. "1.84.0"), leeg = onbekend.
        exported_by:   Azure AD-gebruikersnaam of "offline", leeg = onbekend.
    """
    try:
        now = datetime.datetime.now()
        lines = [
            "Networkmap Creator — Export Info",
            "=" * 40,
            f"Date/time : {now.strftime('%Y-%m-%d  %H:%M:%S')}",
            f"Scope     : {'All companies (full export)' if scope == 'full' else f'Company — {company_name}'}",
            f"App ver.  : {app_version or 'unknown'}",
            f"Exported by: {exported_by or 'unknown'}",
            "",
            "Files in this export:",
            f"  {_FILE_NETWORK}   — network topology data",
            f"  {_FILE_SETTINGS}      — application settings",
            f"  {_FILE_FLOORPLAN}    — floorplan metadata",
            f"  {_DIR_FLOORPLAN}/         — SVG floorplan files",
            f"  {_FILE_VLAN}   — VLAN configuration",
            f"  {_FILE_INFO}    — this file",
            "",
            "To restore: use Import → Replace in Networkmap Creator.",
        ]
        if scope == "company":
            lines.append(
                "Note: company export does not include settings.json "
                "(installation-specific)."
            )
        path = Path(dest_dir) / _FILE_INFO
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass  # Info-bestand is niet kritisch — export mag nooit falen hierdoor


# ------------------------------------------------------------------
# v1 → v2 migratie (inline, geen Qt)
# ------------------------------------------------------------------

def _is_v2(data: dict) -> bool:
    return "companies" in data


def _migrate_v1_to_v2(data: dict, company_name: str = "Geïmporteerd bedrijf") -> dict:
    """
    Converteert v1-structuur (sites[] op top-niveau) naar v2 (companies[]).
    Gebruikt een standaard company-wrapper voor alle geïmporteerde sites.
    """
    import uuid
    company_id = f"company_{uuid.uuid4().hex[:8]}"
    company = {
        "id":      company_id,
        "name":    company_name,
        "address": "",
        "vat":     "",
        "phone":   "",
        "email":   "",
        "website": "",
        "sites":   data.get("sites", []),
    }
    migrated = {"version": "2.0", "companies": [company]}
    for key, value in data.items():
        if key not in ("version", "sites"):
            migrated[key] = value
    return migrated


# ------------------------------------------------------------------
# Export — volledig
# ------------------------------------------------------------------

def export_to_dir(
    dest_dir: str,
    app_version: str = "",
    exported_by: str = "",
) -> tuple[bool, str]:
    """
    Exporteert alle data naar een map:
        <dest_dir>/
            network_data.json
            settings.json
            floorplans.json
            floorplans/
            vlan_config.json
            export_info.txt   ← K1: metadata over de export

    Returns (True, "") bij succes, (False, foutmelding) bij fout.
    """
    try:
        paths = _get_paths()
        d = Path(dest_dir)
        d.mkdir(parents=True, exist_ok=True)

        src = Path(paths["network"])
        if src.is_file():
            shutil.copy2(src, d / _FILE_NETWORK)

        src = Path(paths["settings"])
        if src.is_file():
            shutil.copy2(src, d / _FILE_SETTINGS)

        src = Path(paths["floorplans"])
        if src.is_file():
            shutil.copy2(src, d / _FILE_FLOORPLAN)

        src = Path(paths["floorplans_dir"])
        if src.is_dir():
            dst_fp = d / _DIR_FLOORPLAN
            if dst_fp.exists():
                shutil.rmtree(dst_fp)
            shutil.copytree(src, dst_fp)

        src = Path(paths["vlan"])
        if src.is_file():
            shutil.copy2(src, d / _FILE_VLAN)

        write_export_info(
            dest_dir,
            scope="full",
            app_version=app_version,
            exported_by=exported_by,
        )
        return True, ""
    except Exception:
        import traceback
        return False, traceback.format_exc()


# ------------------------------------------------------------------
# Export — per bedrijf
# ------------------------------------------------------------------

def export_company_to_dir(
    dest_dir: str,
    company_id: str,
    app_version: str = "",
    exported_by: str = "",
) -> tuple[bool, str]:
    """
    Exporteert data van één bedrijf naar een map.

    Exporteert:
      - network_data.json: gefilterd op het bedrijf (company + gelinkte
        devices/ports/endpoints/connections via sites van dat bedrijf)
      - floorplans.json: alleen grondplannen van sites van dat bedrijf
      - floorplans/: alleen de SVG-bestanden van die grondplannen
      - vlan_config.json: volledig (gedeeld)
      - settings.json: NIET (installatie-specifiek)
      - export_info.txt: metadata over de export (K1)

    Returns (True, "") bij succes, (False, foutmelding) bij fout.
    """
    try:
        from app.helpers import settings_storage
        from app.services import floorplan_service

        paths = _get_paths()

        # Laad volledige network_data
        with open(paths["network"], encoding="utf-8") as f:
            full_data = json.load(f)

        # Zoek het bedrijf
        company = next(
            (c for c in full_data.get("companies", []) if c.get("id") == company_id),
            None
        )
        if not company:
            return False, f"Bedrijf niet gevonden: {company_id}"

        # Verzamel site-IDs van dit bedrijf
        site_ids = {s["id"] for s in company.get("sites", [])}

        # Verzamel alle room-IDs van deze sites
        room_ids = {
            r["id"]
            for s in company.get("sites", [])
            for r in s.get("rooms", [])
        }

        # Verzamel alle wandpunt-IDs van deze sites
        outlet_ids = {
            wo["id"]
            for s in company.get("sites", [])
            for r in s.get("rooms", [])
            for wo in r.get("wall_outlets", [])
        }

        # Filter devices: die in racks van deze sites zitten
        rack_ids = {
            ra["id"]
            for s in company.get("sites", [])
            for r in s.get("rooms", [])
            for ra in r.get("racks", [])
        }
        device_ids = {
            sl.get("device_id")
            for s in company.get("sites", [])
            for r in s.get("rooms", [])
            for ra in r.get("racks", [])
            for sl in ra.get("slots", [])
            if sl.get("device_id")
        }

        filtered_devices = [
            d for d in full_data.get("devices", [])
            if d.get("id") in device_ids
        ]
        filtered_device_ids = {d["id"] for d in filtered_devices}

        filtered_ports = [
            p for p in full_data.get("ports", [])
            if p.get("device_id") in filtered_device_ids
        ]
        filtered_port_ids = {p["id"] for p in filtered_ports}

        # Endpoints gekoppeld aan wandpunten van dit bedrijf
        filtered_endpoint_ids = {
            wo.get("endpoint_id")
            for s in company.get("sites", [])
            for r in s.get("rooms", [])
            for wo in r.get("wall_outlets", [])
            if wo.get("endpoint_id")
        }
        filtered_endpoints = [
            e for e in full_data.get("endpoints", [])
            if e.get("id") in filtered_endpoint_ids
        ]

        # Connections: beide kanten binnen gefilterde set
        all_filtered_ids = (
            filtered_device_ids | filtered_port_ids |
            {e["id"] for e in filtered_endpoints} | outlet_ids
        )
        filtered_connections = [
            c for c in full_data.get("connections", [])
            if c.get("from_id") in all_filtered_ids
            and c.get("to_id") in all_filtered_ids
        ]

        # Bouw gefilterde network_data (v2, enkel dit bedrijf)
        filtered_network = {
            "version":     "2.0",
            "companies":   [company],
            "devices":     filtered_devices,
            "ports":       filtered_ports,
            "endpoints":   filtered_endpoints,
            "connections": filtered_connections,
        }
        # Kopieer eventuele extra top-level keys
        for key in full_data:
            if key not in filtered_network:
                filtered_network[key] = full_data[key]

        # Maak export-map aan
        d = Path(dest_dir)
        d.mkdir(parents=True, exist_ok=True)

        with open(d / _FILE_NETWORK, "w", encoding="utf-8") as f:
            json.dump(filtered_network, f, indent=2, ensure_ascii=False)

        # Grondplannen filteren op sites van dit bedrijf
        fp_data = floorplan_service.load_floorplans()
        filtered_fps = [
            fp for fp in fp_data.get("floorplans", [])
            if fp.get("site_id") in site_ids
        ]
        filtered_fp_data = {"floorplans": filtered_fps}
        with open(d / _FILE_FLOORPLAN, "w", encoding="utf-8") as f:
            json.dump(filtered_fp_data, f, indent=2, ensure_ascii=False)

        # Kopieer alleen de relevante SVG-bestanden
        fp_dir_src = Path(paths["floorplans_dir"])
        fp_dir_dst = d / _DIR_FLOORPLAN
        fp_dir_dst.mkdir(exist_ok=True)
        for fp in filtered_fps:
            svg_name = fp.get("svg_file", "")
            if svg_name:
                src_svg = fp_dir_src / svg_name
                if src_svg.exists():
                    shutil.copy2(src_svg, fp_dir_dst / svg_name)

        # VLAN config (volledig, gedeeld)
        src = Path(paths["vlan"])
        if src.is_file():
            shutil.copy2(src, d / _FILE_VLAN)

        write_export_info(
            dest_dir,
            scope="company",
            company_name=company.get("name", ""),
            app_version=app_version,
            exported_by=exported_by,
        )
        return True, ""
    except Exception:
        import traceback
        return False, traceback.format_exc()


def suggested_dirname(company_name: str = "") -> str:
    """Geeft een suggestie voor de exportmapnaam."""
    today = date.today().isoformat()
    if company_name:
        slug = "".join(c if c.isalnum() else "_" for c in company_name).strip("_")
        return f"networkmap_export_{slug}_{today}"
    return f"networkmap_export_{today}"


# Achterwaartse compatibiliteit
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
    return f"networkmap_export_{date.today().isoformat()}.json"


# ------------------------------------------------------------------
# Validatie
# ------------------------------------------------------------------

def validate(data: dict) -> tuple[bool, str]:
    """
    Valideert een geïmporteerd network_data dict.
    Accepteert zowel v1 (sites[]) als v2 (companies[]).
    """
    for key in REQUIRED_KEYS:
        if key not in data:
            if key == "sites" and "companies" in data:
                continue
            return False, f"Verplichte sleutel ontbreekt: '{key}'"
    if "companies" in data:
        if not isinstance(data.get("companies"), list):
            return False, "'companies' moet een lijst zijn."
    else:
        if not isinstance(data.get("sites"), list):
            return False, "'sites' moet een lijst zijn."
    if not isinstance(data.get("devices"), list):
        return False, "'devices' moet een lijst zijn."
    return True, ""


def is_export_dir(path: str) -> bool:
    return (Path(path) / _FILE_NETWORK).is_file()


# ------------------------------------------------------------------
# Import — replace (volledig)
# ------------------------------------------------------------------

def import_replace_dir(src_dir: str) -> tuple[bool, str]:
    """
    Herstelt een volledige export-map naar de lokale installatie.
    v1 data wordt automatisch gemigreerd naar v2 voor opslaan.
    """
    try:
        paths = _get_paths()
        d = Path(src_dir)

        if not d.is_dir():
            return False, f"Map niet gevonden: {src_dir}"
        if not (d / _FILE_NETWORK).is_file():
            return False, f"Geen geldige export-map: network_data.json ontbreekt in {src_dir}"

        with open(d / _FILE_NETWORK, encoding="utf-8") as f:
            nd = json.load(f)
        ok, reason = validate(nd)
        if not ok:
            return False, f"network_data.json ongeldig: {reason}"

        # Auto-migratie v1 → v2: standaard bedrijf aanmaken
        if not _is_v2(nd):
            nd = _migrate_v1_to_v2(nd, company_name="Geïmporteerd bedrijf")

        with open(paths["network"], "w", encoding="utf-8") as f:
            json.dump(nd, f, indent=2, ensure_ascii=False)

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
    """Legacy: laadt een enkelvoudig JSON bestand."""
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


# ------------------------------------------------------------------
# Import — merge (v1 én v2)
# ------------------------------------------------------------------

def import_merge(
    filepath: str,
    current: dict,
    target_company_id: str = "",
) -> tuple[dict | None, str, dict]:
    """
    Laadt een JSON bestand (v1 of v2) en voegt samen met de huidige data.

    - v1 import: wordt automatisch gemigreerd naar v2 voor merge.
    - v2 import: companies worden samengevoegd.
    - target_company_id: bij v1 import, het bedrijf waaraan de geïmporteerde
      sites toegevoegd worden. Leeg = nieuw bedrijf aanmaken.
    - Bestaande IDs worden overgeslagen (geen duplicaten).

    Returns (merged_data, "", stats) bij succes,
            (None, foutmelding, {}) bij fout.
    stats = {"added": int, "skipped": int, "migrated": bool}
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

    migrated_v1 = False

    # Auto-migratie v1 → v2
    if not _is_v2(incoming):
        incoming = _migrate_v1_to_v2(incoming, company_name="Geïmporteerd")
        migrated_v1 = True

    added   = 0
    skipped = 0

    existing_ids = _collect_all_ids(current)
    merged = {k: (list(v) if isinstance(v, list) else v)
              for k, v in current.items()}

    # ── Devices, ports, endpoints, connections ──────────────────────
    for key in ("devices", "ports", "endpoints", "connections"):
        for obj in incoming.get(key, []):
            obj_id = obj.get("id", "")
            if obj_id and obj_id in existing_ids:
                skipped += 1
            else:
                merged.setdefault(key, []).append(obj)
                existing_ids.add(obj_id)
                added += 1

    # ── Companies + sites (v2) ──────────────────────────────────────
    merged_companies = merged.setdefault("companies", [])

    for inc_company in incoming.get("companies", []):
        company_id = inc_company.get("id", "")

        # Bepaal doelbedrijf: target_company_id overschrijft company_id uit import
        effective_id = target_company_id or company_id

        existing_company = next(
            (c for c in merged_companies if c.get("id") == effective_id),
            None
        )

        if existing_company is None:
            # Nieuw bedrijf toevoegen
            new_company = {**inc_company, "id": effective_id}
            merged_companies.append(new_company)
            added += 1
        else:
            # Bedrijf bestaat al — sites samenvoegen
            for inc_site in inc_company.get("sites", []):
                site_id = inc_site.get("id", "")
                existing_site = next(
                    (s for s in existing_company.get("sites", [])
                     if s["id"] == site_id),
                    None
                )
                if existing_site is None:
                    existing_company.setdefault("sites", []).append(inc_site)
                    added += 1
                else:
                    # Site bestaat — rooms samenvoegen
                    for inc_room in inc_site.get("rooms", []):
                        room_id = inc_room.get("id", "")
                        ex_room = next(
                            (r for r in existing_site.get("rooms", [])
                             if r["id"] == room_id),
                            None
                        )
                        if ex_room is None:
                            existing_site.setdefault("rooms", []).append(inc_room)
                            added += 1
                        else:
                            # Room bestaat — racks + wandpunten samenvoegen
                            for inc_rack in inc_room.get("racks", []):
                                if inc_rack.get("id") not in existing_ids:
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

    # Verwijder verouderde top-level sites[] als die nog aanwezig is
    merged.pop("sites", None)

    return merged, "", {"added": added, "skipped": skipped, "migrated": migrated_v1}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _collect_all_ids(data: dict) -> set:
    ids = set()
    for key in ("devices", "ports", "endpoints", "connections"):
        for obj in data.get(key, []):
            if obj.get("id"):
                ids.add(obj["id"])
    # v2: companies
    for company in data.get("companies", []):
        ids.add(company.get("id", ""))
        for site in company.get("sites", []):
            ids.add(site.get("id", ""))
            for room in site.get("rooms", []):
                ids.add(room.get("id", ""))
                for rack in room.get("racks", []):
                    ids.add(rack.get("id", ""))
                for wo in room.get("wall_outlets", []):
                    ids.add(wo.get("id", ""))
    # v1 fallback
    for site in get_all_sites(data):
        ids.add(site.get("id", ""))
        for room in site.get("rooms", []):
            ids.add(room.get("id", ""))
            for rack in room.get("racks", []):
                ids.add(rack.get("id", ""))
            for wo in room.get("wall_outlets", []):
                ids.add(wo.get("id", ""))
    return ids