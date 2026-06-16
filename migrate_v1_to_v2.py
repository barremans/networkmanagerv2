# =============================================================================
# Networkmap_Creator
# File:    migrate_v1_to_v2.py
# Role:    Eenmalig migratiescript: network_data.json v1 → v2
#          Voegt companies[] wrapper toe rond bestaande sites[]
# Version: 1.0.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie
#
# Gebruik:
#   python migrate_v1_to_v2.py
#   python migrate_v1_to_v2.py --input pad/naar/network_data.json
#   python migrate_v1_to_v2.py --input network_data.json --output network_data_v2.json
#
# Het originele bestand wordt automatisch gebackupt als network_data.backup.json
# tenzij --no-backup opgegeven wordt.
# =============================================================================

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Standaard bedrijfsgegevens — pas aan voor CGK Group
# ---------------------------------------------------------------------------

DEFAULT_COMPANY = {
    "id":      "company_cgk_group",
    "name":    "CGK Group",
    "address": "",
    "vat":     "",
    "phone":   "",
    "email":   "",
    "website": "",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _is_v2(data: dict) -> bool:
    return "companies" in data


def _is_v1(data: dict) -> bool:
    return "sites" in data and "companies" not in data


# ---------------------------------------------------------------------------
# Migratie
# ---------------------------------------------------------------------------

def migrate(data: dict, company_defaults: dict) -> dict:
    """
    Converteert v1-structuur naar v2.

    v1:
        {
            "version": "1.0",
            "sites": [...],
            "devices": [...],
            ...
        }

    v2:
        {
            "version": "2.0",
            "companies": [
                {
                    "id": "...",
                    "name": "...",
                    "address": "",
                    "vat": "",
                    "phone": "",
                    "email": "",
                    "website": "",
                    "sites": [...]
                }
            ],
            "devices": [...],
            ...
        }
    """
    company = {**company_defaults, "sites": data.get("sites", [])}

    migrated = {
        "version":   "2.0",
        "companies": [company],
    }

    # Kopieer resterende top-level sleutels (devices, ports, endpoints, connections, ...)
    for key, value in data.items():
        if key not in ("version", "sites"):
            migrated[key] = value

    return migrated


# ---------------------------------------------------------------------------
# Validatie
# ---------------------------------------------------------------------------

def validate_v2(data: dict) -> list[str]:
    """Geeft een lijst van waarschuwingen terug. Lege lijst = OK."""
    warnings = []

    if "companies" not in data:
        warnings.append("'companies' sleutel ontbreekt na migratie.")
        return warnings

    if not isinstance(data["companies"], list) or len(data["companies"]) == 0:
        warnings.append("'companies' is leeg na migratie.")
        return warnings

    for ci, company in enumerate(data["companies"]):
        for field in ("id", "name", "sites"):
            if field not in company:
                warnings.append(f"companies[{ci}]: sleutel '{field}' ontbreekt.")
        sites = company.get("sites", [])
        if not isinstance(sites, list):
            warnings.append(f"companies[{ci}].sites is geen lijst.")
        else:
            for si, site in enumerate(sites):
                for sf in ("id", "name"):
                    if sf not in site:
                        warnings.append(
                            f"companies[{ci}].sites[{si}]: sleutel '{sf}' ontbreekt."
                        )

    for key in ("devices", "ports", "endpoints", "connections"):
        if key not in data:
            warnings.append(f"Top-level sleutel '{key}' ontbreekt na migratie.")

    return warnings


# ---------------------------------------------------------------------------
# Rapportage
# ---------------------------------------------------------------------------

def _print_summary(original: dict, migrated: dict) -> None:
    print("\n── Migratieresultaat ──────────────────────────────────")
    print(f"  Versie:       {original.get('version')} → {migrated.get('version')}")

    companies = migrated.get("companies", [])
    print(f"  Bedrijven:    {len(companies)}")
    for c in companies:
        sites = c.get("sites", [])
        print(f"    · {c['name']} ({c['id']}) — {len(sites)} site(s)")
        for s in sites:
            rooms = s.get("rooms", [])
            print(f"        – {s['name']} ({s['id']}) — {len(rooms)} ruimte(s)")

    original_sites = original.get("sites", [])
    migrated_sites = [
        s for c in companies for s in c.get("sites", [])
    ]
    print(f"\n  Sites origineel:  {len(original_sites)}")
    print(f"  Sites gemigreerd: {len(migrated_sites)}")

    for key in ("devices", "ports", "endpoints", "connections"):
        orig_count  = len(original.get(key, []))
        migr_count  = len(migrated.get(key, []))
        status = "✓" if orig_count == migr_count else "⚠ VERSCHIL"
        print(f"  {key:<15} {orig_count} → {migr_count}  {status}")

    print("───────────────────────────────────────────────────────\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migreert network_data.json van v1 (sites[]) naar v2 (companies[])."
    )
    parser.add_argument(
        "--input", "-i",
        default="network_data.json",
        help="Pad naar het te migreren bestand (default: network_data.json)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Pad voor het gemigreerde bestand (default: overschrijft --input)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Geen backup aanmaken van het originele bestand",
    )
    parser.add_argument(
        "--company-name",
        default=DEFAULT_COMPANY["name"],
        help=f"Naam van het standaard bedrijf (default: '{DEFAULT_COMPANY['name']}')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Voer de migratie uit maar schrijf geen bestanden",
    )
    args = parser.parse_args()

    input_path  = Path(args.input)
    output_path = Path(args.output) if args.output else input_path

    # --- Bestand laden ---
    if not input_path.exists():
        print(f"FOUT: bestand niet gevonden: {input_path}", file=sys.stderr)
        return 1

    print(f"Laden: {input_path}")
    original = _load_json(input_path)

    # --- Reeds gemigreerd? ---
    if _is_v2(original):
        print("INFO: bestand is reeds in v2-formaat (companies[] aanwezig). Niets te doen.")
        return 0

    if not _is_v1(original):
        print("FOUT: bestand heeft geen 'sites' sleutel — onbekend formaat.", file=sys.stderr)
        return 1

    # --- Migreren ---
    company_defaults = {**DEFAULT_COMPANY, "name": args.company_name}
    migrated = migrate(original, company_defaults)

    # --- Valideren ---
    warnings = validate_v2(migrated)
    if warnings:
        print("\n⚠ Validatiewaarschuwingen:")
        for w in warnings:
            print(f"  · {w}")
        print()

    # --- Samenvatting tonen ---
    _print_summary(original, migrated)

    if args.dry_run:
        print("DRY-RUN: geen bestanden geschreven.")
        return 0

    # --- Backup ---
    if not args.no_backup and input_path.exists():
        ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
        bck     = input_path.with_name(f"{input_path.stem}.backup_{ts}.json")
        shutil.copy2(input_path, bck)
        print(f"Backup:  {bck}")

    # --- Schrijven ---
    _save_json(output_path, migrated)
    print(f"Geschreven: {output_path}")
    print("Migratie voltooid.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())