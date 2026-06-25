# =============================================================================
# Networkmap_Creator
# File:    app/helpers/settings_storage.py
# Role:    Centrale JSON data toegang — laden, opslaan, validatie
# Version: 1.19.0
# Author:  Barremans
# Changes: 1.19.0 - K-CABLE: _DEFAULT_CABLE_TYPES, load/save/get_cable_type_label.
#          1.18.0 — K3: get_changelog_path() toegevoegd.
#          1.17.0 — GUID-normalisatie: tenant_id/client_id worden lowercase
#                   bewaard én gelezen. MSAL valideert de aud-claim
#                   hoofdlettergevoelig tegen client_id; een uppercase GUID
#                   (bv. via de globale uppercase-filter) brak de login.
#                   Auto-heal: afwijkend opgeslagen waarden worden eenmalig
#                   genormaliseerd teruggeschreven.
#          1.16.0 — S6b migratie fix: required_group → group_admin wordt
#                   eenmalig weggeschreven naar settings.json zodat bestaande
#                   installaties (CGK-APP-L6 als required_group) correct
#                   migreren zonder herstart-probleem.
#          1.15.0 — S6b: twee AD-groepen: group_admin + group_readonly
#                   required_group vervangen door group_admin / group_readonly
#                   get_azure_ad_config() backward compatible (required_group
#                   migreert naar group_admin indien aanwezig)
#          1.14.0 — S6: Azure AD-configuratie generiek gemaakt
#                   azure_ad sectie toegevoegd aan _DEFAULT_SETTINGS
#                   get_azure_ad_config(), save_azure_ad_config()
#          1.13.0 — F1/F2: companies[] structuur (v2 dataformaat)
#                   · _DEFAULT_NETWORK bijgewerkt naar v2 (companies[] ipv sites[])
#                   · _REQUIRED_NETWORK_KEYS aangepast voor v1 én v2
#                   · get_all_companies(data) — geeft companies[] terug
#                   · get_all_sites(data) — geeft alle sites terug (v1 én v2)
#                   · load_network_data(): automatische v1→v2 migratie bij laden
#                   · validate_network_data(): ondersteunt v1 én v2
#                   · save_company(), get_company_by_id() toegevoegd
#          1.12.0 — get_vlan_config_path(): volgt network_data.json pad
#                   zodat vlan_config.json gedeeld wordt via netwerkshare
#          1.11.0 — SVG label prefixen configureerbaar via settings
#                   _DEFAULT_OUTLET_LABEL_PREFIXES, load/save_outlet_label_prefixes
#          1.10.0 — floorplan opslag helpers
#               get_floorplans_path(), get_floorplans_dir()
#               last_folders["floorplan_svg"] toegevoegd
#          F5 — read_only_mode toegevoegd aan _DEFAULT_SETTINGS
#               get_read_only_mode(), set_read_only_mode()
#          F2 — Device types configureerbaar via settings.json
#               _DEFAULT_DEVICE_TYPES, load/save/get_device_type_*
#          F3 — Lokaal vs netwerkdata
#               get_network_data_path() kiest netwerkpad als bereikbaar
#               is_network_path_available(), get_network_data_source_label()
#          B  — PyInstaller compatibel pad via sys.frozen
#          D  — update_check_url toegevoegd aan _DEFAULT_SETTINGS
#          1.5.0 — APPDATA fix: data opslaan in %APPDATA%\Networkmap_Creator
#                  wanneer app draait vanuit write-protected map (Program Files)
#          1.6.0 — Vaste data map: C:\Networkmap_Creator\data\
#                  Data staat altijd op dezelfde plek, onafhankelijk van
#                  installatielocatie. Geen dataverlies bij herinstallatie.
#          1.8.0 — Ontbrekende device types toegevoegd aan _DEFAULT_DEVICE_TYPES:
#                  cable_management, distribution_plug, fiber, nuc1, sonos_server
#          1.7.0 — Wandpunt locatie types configureerbaar via settings.json
#                  _DEFAULT_OUTLET_LOCATIONS, load/save_outlet_locations
# =============================================================================

import json
import os
import sys
import shutil
from datetime import datetime


# ---------------------------------------------------------------------------
# Pad bepaling — v1.5.0
#
# Prioriteit:
#   1. Dev (niet frozen)          → projectroot/data/
#   2. Frozen + schrijfbaar       → naast .exe / data/
#   3. Frozen + niet schrijfbaar  → %APPDATA%\Networkmap_Creator\data/
#      (treedt op bij installatie in C:\Program Files\)
# ---------------------------------------------------------------------------

_APP_NAME   = "Networkmap_Creator"
_FIXED_DATA = r"C:\Networkmap_Creator"   # Vaste datamap — altijd schrijfbaar


def _get_base_dir() -> str:
    """
    Bepaal de basismap voor data opslag.

    Development (niet frozen):
        Projectroot — twee niveaus boven app/helpers/

    PyInstaller exe (frozen):
        Altijd C:\\Networkmap_Creator\\
        → buiten Program Files → altijd schrijfbaar
        → vaste locatie → geen dataverlies bij herinstallatie

    Fallback (C:\\ niet schrijfbaar, bijv. gelimiteerde omgeving):
        %APPDATA%\\Networkmap_Creator\\
    """
    if not getattr(sys, "frozen", False):
        # Development
        return os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

    # PyInstaller exe — gebruik altijd de vaste map op C:\
    try:
        os.makedirs(_FIXED_DATA, exist_ok=True)
        test_file = os.path.join(_FIXED_DATA, ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return _FIXED_DATA      # ✅ C:\Networkmap_Creator — beschrijfbaar
    except OSError:
        pass

    # Fallback: C:\ niet schrijfbaar → gebruik APPDATA
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    appdata_dir = os.path.join(appdata, _APP_NAME)
    os.makedirs(appdata_dir, exist_ok=True)
    return appdata_dir


_BASE_DIR        = _get_base_dir()
_DATA_DIR        = os.path.join(_BASE_DIR, "data")
_SETTINGS_FILE   = os.path.join(_DATA_DIR, "settings.json")
_NETWORK_FILE    = os.path.join(_DATA_DIR, "network_data.json")
_FLOORPLANS_FILE = os.path.join(_DATA_DIR, "floorplans.json")
_FLOORPLANS_DIR  = os.path.join(_DATA_DIR, "floorplans")
_CHANGELOG_FILE  = os.path.join(_DATA_DIR, "changelog.jsonl")

# Verplichte sleutels voor validatie — v1 én v2 worden ondersteund
_REQUIRED_SETTINGS_KEYS    = ["app_version", "language", "backup", "ui", "last_folders"]
_REQUIRED_NETWORK_KEYS_V1  = ["version", "sites", "devices", "ports", "endpoints", "connections"]
_REQUIRED_NETWORK_KEYS_V2  = ["version", "companies", "devices", "ports", "endpoints", "connections"]

# Standaard bedrijf bij v1→v2 migratie
_DEFAULT_COMPANY = {
    "id":      "company_cgk_group",
    "name":    "CGK Group",
    "address": "",
    "vat":     "",
    "phone":   "",
    "email":   "",
    "website": "",
}

# Ingebouwde eindapparaat-types
_DEFAULT_ENDPOINT_TYPES = [
    {"key": "pc",           "label_nl": "PC",           "label_en": "PC"},
    {"key": "laptop",       "label_nl": "Laptop",       "label_en": "Laptop"},
    {"key": "thin_client",  "label_nl": "Thin Client",  "label_en": "Thin Client"},
    {"key": "printer",      "label_nl": "Printer",      "label_en": "Printer"},
    {"key": "plotter",      "label_nl": "Plotter",      "label_en": "Plotter"},
    {"key": "scanner",      "label_nl": "Scanner",      "label_en": "Scanner"},
    {"key": "all_in_one",   "label_nl": "All-in-one",   "label_en": "All-in-One"},
    {"key": "phone",        "label_nl": "IP-telefoon",  "label_en": "IP Phone"},
    {"key": "ip_camera",    "label_nl": "IP-camera",    "label_en": "IP Camera"},
    {"key": "access_point", "label_nl": "Access Point", "label_en": "Access Point"},
    {"key": "nas",          "label_nl": "NAS",          "label_en": "NAS"},
    {"key": "other",        "label_nl": "Ander",        "label_en": "Other"},
]

# Ingebouwde device-types — F2
_DEFAULT_DEVICE_TYPES = [
    {"key": "patch_panel",       "label_nl": "Patchpanel",       "label_en": "Patch Panel",
     "front_ports": 24, "back_ports": 24},
    {"key": "switch",            "label_nl": "Switch",           "label_en": "Switch",
     "front_ports": 24, "back_ports": 0},
    {"key": "router",            "label_nl": "Router",           "label_en": "Router",
     "front_ports": 4,  "back_ports": 0},
    {"key": "firewall",          "label_nl": "Firewall",         "label_en": "Firewall",
     "front_ports": 4,  "back_ports": 0},
    {"key": "server",            "label_nl": "Server",           "label_en": "Server",
     "front_ports": 2,  "back_ports": 0},
    {"key": "kvm",               "label_nl": "KVM-switch",       "label_en": "KVM Switch",
     "front_ports": 8,  "back_ports": 0},
    {"key": "ups",               "label_nl": "UPS",              "label_en": "UPS",
     "front_ports": 0,  "back_ports": 0},
    {"key": "pdu",               "label_nl": "PDU",              "label_en": "PDU",
     "front_ports": 0,  "back_ports": 0},
    {"key": "media_conv",        "label_nl": "Mediaconverter",   "label_en": "Media Converter",
     "front_ports": 2,  "back_ports": 0},
    {"key": "other",             "label_nl": "Ander",            "label_en": "Other",
     "front_ports": 0,  "back_ports": 0},
    {"key": "cable_management",  "label_nl": "Kabelgoot",        "label_en": "Cable Management",
     "front_ports": 0,  "back_ports": 0},
    {"key": "distribution_plug", "label_nl": "Verdeelstekker",   "label_en": "Distribution Plug",
     "front_ports": 0,  "back_ports": 0},
    {"key": "fiber",             "label_nl": "Fiber converter",  "label_en": "Fiber Converter",
     "front_ports": 2,  "back_ports": 2},
    {"key": "nuc1",              "label_nl": "NUC / Mini-PC",    "label_en": "NUC / Mini-PC",
     "front_ports": 2,  "back_ports": 0},
    {"key": "sonos_server",      "label_nl": "Sonos server",     "label_en": "Sonos Server",
     "front_ports": 1,  "back_ports": 0},
]

# Ingebouwde wandpunt locatie types — configureerbaar
# Ingebouwde kabeltypes -- configureerbaar (K-CABLE)
_DEFAULT_CABLE_TYPES = [
    {"key": "utp_cat5e", "label_nl": "UTP Cat5e", "label_en": "UTP Cat5e", "color": "#95A5A6"},
    {"key": "utp_cat6",  "label_nl": "UTP Cat6",  "label_en": "UTP Cat6",  "color": "#4A90D9"},
    {"key": "utp_cat6a", "label_nl": "UTP Cat6a", "label_en": "UTP Cat6a", "color": "#27AE60"},
    {"key": "fiber_sm",  "label_nl": "Fiber SM",  "label_en": "Fiber SM",  "color": "#F39C12"},
    {"key": "fiber_mm",  "label_nl": "Fiber MM",  "label_en": "Fiber MM",  "color": "#E67E22"},
    {"key": "dak",       "label_nl": "DAK",       "label_en": "DAK",       "color": "#8E44AD"},
    {"key": "other",     "label_nl": "Ander",     "label_en": "Other",     "color": "#7F8C8D"},
]

_DEFAULT_OUTLET_LOCATIONS = [
    {"key": "links",    "label_nl": "Links",    "label_en": "Left"},
    {"key": "rechts",   "label_nl": "Rechts",   "label_en": "Right"},
    {"key": "voor",     "label_nl": "Voor",     "label_en": "Front"},
    {"key": "achter",   "label_nl": "Achter",   "label_en": "Rear"},
    {"key": "boven",    "label_nl": "Boven",    "label_en": "Top"},
    {"key": "onder",    "label_nl": "Onder",    "label_en": "Bottom"},
    {"key": "hoek",     "label_nl": "Hoek",     "label_en": "Corner"},
    {"key": "plafond",  "label_nl": "Plafond",  "label_en": "Ceiling"},
    {"key": "vloer",    "label_nl": "Vloer",    "label_en": "Floor"},
    {"key": "bureau",   "label_nl": "Bureau",   "label_en": "Desk"},
    {"key": "kast",     "label_nl": "Kast",     "label_en": "Cabinet"},
    {"key": "other",    "label_nl": "Ander",    "label_en": "Other"},
]

# Ingebouwde SVG label prefixen voor wandpunten — configureerbaar
_DEFAULT_OUTLET_LABEL_PREFIXES = ["M", "WO", "WP", "WAP"]

# Fallback defaults bij ontbrekend of corrupt settings.json
_DEFAULT_SETTINGS = {
    "app_version": "1.0",
    "language": "nl",
    "update_check_url": "",          # D — leeg = hardcoded GitHub URL gebruiken
    "backup": {
        "enabled": False,
        "network_path": "",
        "keep_history": True,
        "max_backups": 10
    },
    "ui": {
        "theme": "dark",
        "rack_unit_height": 30,
        "rack_unit_width": 400
    },
    "last_folders": {
        "export_json":   "",
        "import_json":   "",
        "export_image":  "",
        "export_pdf":    "",
        "export_report": "",
        "floorplan_svg": "",
    },
    "last_opened_site": "",
    "endpoint_types": _DEFAULT_ENDPOINT_TYPES,
    "device_types": _DEFAULT_DEVICE_TYPES,
    "outlet_locations": _DEFAULT_OUTLET_LOCATIONS,
    "outlet_label_prefixes": _DEFAULT_OUTLET_LABEL_PREFIXES,
    # F3 — netwerkdata locatie
    "network_data": {
        "use_network_path": False,
        "network_path": "",
    },
    # F5 — toegangsmodus: standaard read-only bij opstarten
    "read_only_mode": True,
    # S6 — Azure AD configuratie (generiek, niet meer hardcoded voor CGK)
    "azure_ad": {
        "enabled":        True,
        "tenant_id":      "",
        "client_id":      "",
        "group_admin":    "",   # S6b — volledige toegang
        "group_readonly": "",   # S6b — enkel lezen
    },
}

# Fallback defaults bij ontbrekend of corrupt network_data.json — v2
_DEFAULT_NETWORK = {
    "version": "2.0",
    "companies": [
        {**_DEFAULT_COMPANY, "sites": []}
    ],
    "devices":     [],
    "ports":       [],
    "endpoints":   [],
    "connections": []
}


# ---------------------------------------------------------------------------
# Interne hulpfuncties
# ---------------------------------------------------------------------------

def _ensure_data_dir():
    os.makedirs(_DATA_DIR, exist_ok=True)


def _load_json(path: str) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _save_json(path: str, data: dict) -> bool:
    # Zorg dat de doelmap bestaat (ook voor netwerkpaden)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except OSError:
        pass

    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        shutil.move(tmp_path, path)
        return True
    except OSError:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return False


def _validate_keys(data: dict, required_keys: list) -> bool:
    return all(key in data for key in required_keys)


def _make_backup(path: str):
    if not os.path.exists(path):
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base, ext = os.path.splitext(path)
    backup_path = f"{base}_backup_{timestamp}{ext}"

    try:
        shutil.copy2(path, backup_path)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# v1 → v2 migratie (in-memory, geen bestandsschrijven)
# ---------------------------------------------------------------------------

def _migrate_v1_to_v2(data: dict) -> dict:
    """
    Converteert v1-structuur (sites[] op top-niveau) naar v2 (companies[]).
    Werkt in-memory — het bestand wordt daarna opgeslagen door load_network_data().
    """
    company = {**_DEFAULT_COMPANY, "sites": data.get("sites", [])}
    migrated = {
        "version":   "2.0",
        "companies": [company],
    }
    for key, value in data.items():
        if key not in ("version", "sites"):
            migrated[key] = value
    return migrated


def _is_v1(data: dict) -> bool:
    return "sites" in data and "companies" not in data


def _is_v2(data: dict) -> bool:
    return "companies" in data


# ---------------------------------------------------------------------------
# Settings (settings.json)
# ---------------------------------------------------------------------------

def load_settings() -> dict:
    _ensure_data_dir()
    data = _load_json(_SETTINGS_FILE)

    if data is None:
        _save_json(_SETTINGS_FILE, _DEFAULT_SETTINGS)
        return dict(_DEFAULT_SETTINGS)

    changed = False
    for key, value in _DEFAULT_SETTINGS.items():
        if key not in data:
            data[key] = value
            changed = True

    # Zorg dat nested last_folders sleutels ook bestaan
    if "last_folders" not in data or not isinstance(data["last_folders"], dict):
        data["last_folders"] = dict(_DEFAULT_SETTINGS["last_folders"])
        changed = True
    else:
        for key, value in _DEFAULT_SETTINGS["last_folders"].items():
            if key not in data["last_folders"]:
                data["last_folders"][key] = value
                changed = True

    if changed:
        _save_json(_SETTINGS_FILE, data)

    return data


def save_settings(settings: dict) -> bool:
    return _save_json(_SETTINGS_FILE, settings)


def save_setting(key: str, value) -> bool:
    settings = load_settings()
    settings[key] = value
    return _save_json(_SETTINGS_FILE, settings)


def get_setting(key: str, default=None):
    settings = load_settings()
    return settings.get(key, default)


# ---------------------------------------------------------------------------
# Eindapparaat-types (configureerbaar)
# ---------------------------------------------------------------------------

def load_endpoint_types() -> list:
    settings = load_settings()
    types = settings.get("endpoint_types")
    if not isinstance(types, list) or len(types) == 0:
        return list(_DEFAULT_ENDPOINT_TYPES)
    return types


def save_endpoint_types(types: list) -> bool:
    return save_setting("endpoint_types", types)


def get_endpoint_type_label(key: str, lang: str = "nl") -> str:
    for et in load_endpoint_types():
        if et.get("key") == key:
            return et.get(f"label_{lang}", et.get("label_nl", key))
    return key


# ---------------------------------------------------------------------------
# Device-types (configureerbaar) — F2
# ---------------------------------------------------------------------------

def load_device_types() -> list:
    settings = load_settings()
    types = settings.get("device_types")
    if not isinstance(types, list) or len(types) == 0:
        return list(_DEFAULT_DEVICE_TYPES)
    return types


def save_device_types(types: list) -> bool:
    return save_setting("device_types", types)


def get_device_type_label(key: str, lang: str = "nl") -> str:
    for dt in load_device_types():
        if dt.get("key") == key:
            return dt.get(f"label_{lang}", dt.get("label_nl", key))
    return key


def get_device_type_defaults(key: str) -> tuple[int, int]:
    """Geef standaard (front_ports, back_ports) voor een device-type key."""
    for dt in load_device_types():
        if dt.get("key") == key:
            return dt.get("front_ports", 0), dt.get("back_ports", 0)
    return 0, 0


# ---------------------------------------------------------------------------
# Kabeltypes (configureerbaar) — K-CABLE
# ---------------------------------------------------------------------------

def load_cable_types() -> list:
    """
    Geeft de geconfigureerde kabeltypes terug.
    Elk item: {"key": str, "label_nl": str, "label_en": str, "color": str}
    Valt terug op _DEFAULT_CABLE_TYPES als de instelling leeg of ongeldig is.
    """
    settings = load_settings()
    types = settings.get("cable_types")
    if not isinstance(types, list) or len(types) == 0:
        return list(_DEFAULT_CABLE_TYPES)
    return types


def save_cable_types(types: list) -> bool:
    return save_setting("cable_types", types)


def get_cable_type_label(key: str, lang: str = "nl") -> str:
    """Geeft het label voor een kabeltype-key terug in de opgegeven taal."""
    for ct in load_cable_types():
        if ct.get("key") == key:
            return ct.get(f"label_{lang}", ct.get("label_nl", key))
    return key


def get_cable_type_color(key: str) -> str:
    """Geeft de kleurcode (#rrggbb) voor een kabeltype-key terug."""
    for ct in load_cable_types():
        if ct.get("key") == key:
            return ct.get("color", "#7F8C8D")
    return "#7F8C8D"


def load_cable_types_for_ddl(lang: str = "nl") -> list[tuple[str, str]]:
    """
    Hulpfunctie voor DDL-populatie in verbindingsdialogen.
    Geeft lijst van (key, label) tuples terug in de juiste taal.
    """
    return [
        (ct["key"], ct.get(f"label_{lang}", ct.get("label_nl", ct["key"])))
        for ct in load_cable_types()
    ]


# ---------------------------------------------------------------------------
# Netwerkdata pad — F3
# ---------------------------------------------------------------------------

def is_network_path_available(path: str) -> bool:
    if not path or not path.strip():
        return False
    try:
        return os.path.isdir(path) and os.access(path, os.R_OK | os.W_OK)
    except OSError:
        return False


def get_network_data_path() -> str:
    settings = load_settings()
    nd_cfg = settings.get("network_data", {})

    if nd_cfg.get("use_network_path", False):
        net_path = nd_cfg.get("network_path", "").strip()
        if net_path and is_network_path_available(net_path):
            return os.path.join(net_path, "network_data.json")

    return _NETWORK_FILE


def get_network_data_source_label() -> tuple[str, bool]:
    settings = load_settings()
    nd_cfg = settings.get("network_data", {})

    if nd_cfg.get("use_network_path", False):
        net_path = nd_cfg.get("network_path", "").strip()
        if net_path and is_network_path_available(net_path):
            return net_path, True
        if net_path:
            return "Lokaal (fallback: netwerk niet bereikbaar)", False

    return "Lokaal", False


def get_settings_path() -> str:
    return _SETTINGS_FILE


def get_data_dir() -> str:
    """Geeft de actieve data map terug — handig voor diagnostiek."""
    return _DATA_DIR


# ---------------------------------------------------------------------------
# Floorplans pad — G4
# ---------------------------------------------------------------------------

def get_floorplans_path() -> str:
    """
    Geeft het pad naar floorplans.json terug.
    Bestand wordt automatisch aangemaakt indien het nog niet bestaat.
    """
    _ensure_data_dir()

    if not os.path.exists(_FLOORPLANS_FILE):
        _save_json(_FLOORPLANS_FILE, {"floorplans": []})

    return _FLOORPLANS_FILE


def get_floorplans_dir() -> str:
    """
    Geeft de map terug waar SVG floorplan-bestanden bewaard worden.
    Map wordt automatisch aangemaakt indien nodig.
    """
    _ensure_data_dir()
    os.makedirs(_FLOORPLANS_DIR, exist_ok=True)
    return _FLOORPLANS_DIR


def get_vlan_config_path() -> str:
    """
    Geeft het pad naar vlan_config.json terug.
    Volgt network_data.json — als de app via een netwerk-pad draait,
    staat vlan_config.json in dezelfde map als network_data.json.
    Zo zijn VLAN-definities gedeeld tussen alle gebruikers van dezelfde share.
    """
    return os.path.join(
        os.path.dirname(get_network_data_path()),
        "vlan_config.json"
    )


def get_changelog_path() -> str:
    """
    Geeft het pad naar changelog.jsonl terug (K3).
    Staat altijd in de lokale data-map (_DATA_DIR), ook bij netwerkdata.
    De log is installatie-specifiek — niet gedeeld via netwerk-pad.
    """
    _ensure_data_dir()
    return _CHANGELOG_FILE


# ---------------------------------------------------------------------------
# Network data (network_data.json)
# ---------------------------------------------------------------------------

def load_network_data() -> dict:
    """
    F3 — Laadt network_data van het actieve pad (lokaal of netwerk).
    v1.13.0: automatische v1→v2 migratie bij laden indien nodig.
    """
    _ensure_data_dir()
    path = get_network_data_path()
    data = _load_json(path)

    if data is None:
        if os.path.exists(path):
            _make_backup(path)
        _save_json(path, _DEFAULT_NETWORK)
        return dict(_DEFAULT_NETWORK)

    # Automatische v1 → v2 migratie
    if _is_v1(data):
        _make_backup(path)
        data = _migrate_v1_to_v2(data)
        _save_json(path, data)

    # Ontbrekende top-level sleutels aanvullen vanuit v2 default
    changed = False
    for key, value in _DEFAULT_NETWORK.items():
        if key not in data:
            data[key] = value
            changed = True

    if changed:
        _save_json(path, data)

    return data


def save_network_data(data: dict) -> bool:
    """F3 — Slaat network_data op naar het actieve pad (lokaal of netwerk)."""
    path = get_network_data_path()
    return _save_json(path, data)


# ---------------------------------------------------------------------------
# Companies helpers — F1 (v1.13.0)
# ---------------------------------------------------------------------------

def get_all_companies(data: dict) -> list:
    """
    Geeft de companies[] lijst terug.
    Werkt voor v2-structuur. Voor v1 (nog niet gemigreerd): geeft lege lijst.
    Gebruik load_network_data() om zeker v2-data te krijgen.
    """
    return data.get("companies", [])


def get_all_sites(data: dict) -> list:
    """
    Geeft alle sites terug over alle companies heen.
    Ondersteunt zowel v1 (sites[] op top-niveau) als v2 (companies[].sites[]).
    Zo blijft bestaande code die over sites itereert ongewijzigd werken.

    Gebruik:
        for site in get_all_sites(self._data):
            ...
    """
    if _is_v2(data):
        return [
            site
            for company in data.get("companies", [])
            for site in company.get("sites", [])
        ]
    # v1 fallback (zou normaal niet meer voorkomen na migratie)
    return data.get("sites", [])


def get_company_by_id(data: dict, company_id: str) -> dict | None:
    """Geeft een company dict terug op basis van id, of None."""
    for company in data.get("companies", []):
        if company.get("id") == company_id:
            return company
    return None


def get_company_for_site(data: dict, site_id: str) -> dict | None:
    """Geeft de company terug waartoe een site behoort, of None."""
    for company in data.get("companies", []):
        for site in company.get("sites", []):
            if site.get("id") == site_id:
                return company
    return None


def save_company(data: dict, company: dict) -> None:
    """
    Voegt een nieuwe company toe of vervangt een bestaande (op id).
    Werkt in-place op data — daarna save_network_data(data) aanroepen.
    """
    companies = data.setdefault("companies", [])
    for i, c in enumerate(companies):
        if c.get("id") == company.get("id"):
            companies[i] = company
            return
    companies.append(company)


def delete_company(data: dict, company_id: str) -> bool:
    """
    Verwijdert een company op id. Geeft True als gevonden en verwijderd.
    Werkt in-place op data — daarna save_network_data(data) aanroepen.
    Weigert als er maar één company is (minimaal 1 vereist).
    """
    companies = data.get("companies", [])
    if len(companies) <= 1:
        return False
    original_len = len(companies)
    data["companies"] = [c for c in companies if c.get("id") != company_id]
    return len(data["companies"]) < original_len


# ---------------------------------------------------------------------------
# Wandpunt locatie types (configureerbaar)
# ---------------------------------------------------------------------------

def load_outlet_locations() -> list:
    settings = load_settings()
    locs = settings.get("outlet_locations")
    if not isinstance(locs, list) or len(locs) == 0:
        return list(_DEFAULT_OUTLET_LOCATIONS)
    return locs


def save_outlet_locations(locations: list) -> bool:
    return save_setting("outlet_locations", locations)


def get_outlet_location_label(key: str, lang: str = "nl") -> str:
    for loc in load_outlet_locations():
        if loc.get("key") == key:
            return loc.get(f"label_{lang}", loc.get("label_nl", key))
    return key


# ---------------------------------------------------------------------------
# SVG label prefixen voor wandpunten (configureerbaar)
# ---------------------------------------------------------------------------

def load_outlet_label_prefixes() -> list[str]:
    """Geeft de lijst van SVG label prefixen terug (bv. ['M', 'WO', 'WAP'])."""
    settings = load_settings()
    prefixes = settings.get("outlet_label_prefixes")
    if not isinstance(prefixes, list) or len(prefixes) == 0:
        return list(_DEFAULT_OUTLET_LABEL_PREFIXES)
    return [str(p).strip().upper() for p in prefixes if str(p).strip()]


def save_outlet_label_prefixes(prefixes: list[str]) -> bool:
    cleaned = [str(p).strip().upper() for p in prefixes if str(p).strip()]
    return save_setting("outlet_label_prefixes", cleaned)


# ---------------------------------------------------------------------------
# Laatste gebruikte mappen per export type
# ---------------------------------------------------------------------------

def get_last_folder(key: str) -> str:
    """Geeft de laatste gebruikte map terug voor het gegeven type."""
    settings = load_settings()
    return settings.get("last_folders", {}).get(key, "")


def set_last_folder(key: str, path: str) -> None:
    """Slaat de laatste gebruikte map op voor het gegeven type."""
    settings = load_settings()
    if "last_folders" not in settings or not isinstance(settings["last_folders"], dict):
        settings["last_folders"] = {}
    settings["last_folders"][key] = path
    save_settings(settings)


# ---------------------------------------------------------------------------
# Toegangsmodus — F5
# ---------------------------------------------------------------------------

def get_read_only_mode() -> bool:
    """Geeft True als de applicatie in read-only modus staat (standaard True)."""
    return load_settings().get("read_only_mode", True)


def set_read_only_mode(read_only: bool) -> bool:
    """Slaat de toegangsmodus op. Geeft True bij succes."""
    return save_setting("read_only_mode", read_only)


# ---------------------------------------------------------------------------
# Azure AD configuratie — S6
# ---------------------------------------------------------------------------

_DEFAULT_AZURE_AD = {
    "enabled":        True,
    "tenant_id":      "",
    "client_id":      "",
    "group_admin":    "",
    "group_readonly": "",
}


def get_azure_ad_config() -> dict:
    """
    Geeft de Azure AD-configuratie terug. Vult ontbrekende sleutels aan.

    GUID-velden (tenant_id, client_id) worden naar lowercase genormaliseerd:
    MSAL valideert de 'aud'-claim hoofdlettergevoelig tegen client_id, en Azure
    levert GUIDs altijd lowercase. Zonder normalisatie faalt de tokenvalidatie
    ("aud claim must contain this client's client_id, case-sensitively") als de
    waarde ooit in hoofdletters is opgeslagen (bv. door de globale uppercase-
    filter in het instellingenvenster).

    Auto-heal: afwijkend opgeslagen waarden (uppercase GUIDs of de oude sleutel
    'required_group') worden eenmalig genormaliseerd teruggeschreven.
    """
    cfg    = load_settings().get("azure_ad", {})
    result = dict(_DEFAULT_AZURE_AD)
    result.update(cfg)

    # GUIDs altijd lowercase
    result["tenant_id"] = str(result.get("tenant_id", "")).strip().lower()
    result["client_id"] = str(result.get("client_id", "")).strip().lower()

    migrated = False
    # Eenmalige migratie: oude 'required_group' → group_admin
    if "required_group" in cfg and not result.get("group_admin"):
        result["group_admin"] = cfg["required_group"]
        result.pop("required_group", None)
        migrated = True

    # Eenmalig terugschrijven als de opgeslagen waarden afwijken
    # (uppercase GUIDs of oude sleutel), zodat dit niet elke start herhaalt.
    need_write = migrated or (
        bool(cfg) and (
            str(cfg.get("tenant_id", "")) != result["tenant_id"]
            or str(cfg.get("client_id", "")) != result["client_id"]
        )
    )
    if need_write:
        save_setting("azure_ad", result)

    return result


def save_azure_ad_config(config: dict) -> bool:
    """
    Slaat de Azure AD-configuratie op. Geeft True bij succes.
    GUID-velden (tenant_id, client_id) worden lowercase bewaard; groepsnamen
    blijven ongewijzigd (de groepsvergelijking is al hoofdletter-ongevoelig).
    """
    return save_setting("azure_ad", {
        "enabled":        bool(config.get("enabled", True)),
        "tenant_id":      str(config.get("tenant_id",      "")).strip().lower(),
        "client_id":      str(config.get("client_id",      "")).strip().lower(),
        "group_admin":    str(config.get("group_admin",    "")).strip(),
        "group_readonly": str(config.get("group_readonly", "")).strip(),
    })


# ---------------------------------------------------------------------------
# Validatie
# ---------------------------------------------------------------------------

def validate_network_data(data: dict) -> tuple[bool, str]:
    """
    Valideert network_data voor v1 én v2.
    v1: vereist 'sites' op top-niveau.
    v2: vereist 'companies' op top-niveau.
    """
    if not isinstance(data, dict):
        return False, "Geen geldig JSON object."

    if _is_v2(data):
        for key in _REQUIRED_NETWORK_KEYS_V2:
            if key not in data:
                return False, f"Verplichte sleutel ontbreekt: '{key}'"
    elif _is_v1(data):
        for key in _REQUIRED_NETWORK_KEYS_V1:
            if key not in data:
                return False, f"Verplichte sleutel ontbreekt: '{key}'"
    else:
        return False, "Onbekend dataformaat: 'sites' noch 'companies' aanwezig."

    return True, ""


def validate_settings_data(data: dict) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "Geen geldig JSON object."
    for key in _REQUIRED_SETTINGS_KEYS:
        if key not in data:
            return False, f"Verplichte sleutel ontbreekt: '{key}'"
    return True, ""