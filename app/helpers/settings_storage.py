# =============================================================================
# Networkmap_Creator
# File:    app/helpers/settings_storage.py
# Role:    Centrale JSON data toegang — laden, opslaan, validatie
# Version: 1.4.0
# Author:  Barremans
# Changes: F2 — Device types configureerbaar via settings.json
#               _DEFAULT_DEVICE_TYPES, load/save/get_device_type_*
#          F3 — Lokaal vs netwerkdata
#               get_network_data_path() kiest netwerkpad als bereikbaar
#               is_network_path_available(), get_network_data_source_label()
#          B  — PyInstaller compatibel pad via sys.frozen
#          D  — update_check_url toegevoegd aan _DEFAULT_SETTINGS
# =============================================================================

import json
import os
import sys
import shutil
from datetime import datetime

# Paden relatief aan de projectroot
# In dev:        één niveau boven app/helpers/ = projectroot
# In PyInstaller EXE: map van de EXE (naast _internal/, css/, data/)
if getattr(sys, 'frozen', False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_DATA_DIR        = os.path.join(_BASE_DIR, "data")
_SETTINGS_FILE   = os.path.join(_DATA_DIR, "settings.json")
_NETWORK_FILE    = os.path.join(_DATA_DIR, "network_data.json")

# Verplichte sleutels voor validatie
_REQUIRED_SETTINGS_KEYS = ["app_version", "language", "backup", "ui"]
_REQUIRED_NETWORK_KEYS  = ["version", "sites", "devices", "ports", "endpoints", "connections"]

# Ingebouwde eindapparaat-types
_DEFAULT_ENDPOINT_TYPES = [
    {"key": "pc",           "label_nl": "PC",           "label_en": "PC"},
    {"key": "laptop",       "label_nl": "Laptop",        "label_en": "Laptop"},
    {"key": "thin_client",  "label_nl": "Thin Client",   "label_en": "Thin Client"},
    {"key": "printer",      "label_nl": "Printer",       "label_en": "Printer"},
    {"key": "plotter",      "label_nl": "Plotter",       "label_en": "Plotter"},
    {"key": "scanner",      "label_nl": "Scanner",       "label_en": "Scanner"},
    {"key": "all_in_one",   "label_nl": "All-in-one",    "label_en": "All-in-One"},
    {"key": "phone",        "label_nl": "IP-telefoon",   "label_en": "IP Phone"},
    {"key": "ip_camera",    "label_nl": "IP-camera",     "label_en": "IP Camera"},
    {"key": "access_point", "label_nl": "Access Point",  "label_en": "Access Point"},
    {"key": "nas",          "label_nl": "NAS",           "label_en": "NAS"},
    {"key": "other",        "label_nl": "Ander",         "label_en": "Other"},
]

# Ingebouwde device-types — F2
_DEFAULT_DEVICE_TYPES = [
    {"key": "patch_panel",  "label_nl": "Patchpanel",       "label_en": "Patch Panel",
     "front_ports": 24, "back_ports": 24},
    {"key": "switch",       "label_nl": "Switch",           "label_en": "Switch",
     "front_ports": 24, "back_ports": 0},
    {"key": "router",       "label_nl": "Router",           "label_en": "Router",
     "front_ports": 4,  "back_ports": 0},
    {"key": "firewall",     "label_nl": "Firewall",         "label_en": "Firewall",
     "front_ports": 4,  "back_ports": 0},
    {"key": "server",       "label_nl": "Server",           "label_en": "Server",
     "front_ports": 2,  "back_ports": 0},
    {"key": "kvm",          "label_nl": "KVM-switch",       "label_en": "KVM Switch",
     "front_ports": 8,  "back_ports": 0},
    {"key": "ups",          "label_nl": "UPS",              "label_en": "UPS",
     "front_ports": 0,  "back_ports": 0},
    {"key": "pdu",          "label_nl": "PDU",              "label_en": "PDU",
     "front_ports": 0,  "back_ports": 0},
    {"key": "media_conv",   "label_nl": "Mediaconverter",   "label_en": "Media Converter",
     "front_ports": 2,  "back_ports": 0},
    {"key": "other",        "label_nl": "Ander",            "label_en": "Other",
     "front_ports": 0,  "back_ports": 0},
]

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
    "last_opened_site": "",
    "endpoint_types": _DEFAULT_ENDPOINT_TYPES,
    "device_types":   _DEFAULT_DEVICE_TYPES,
    # F3 — netwerkdata locatie
    "network_data": {
        "use_network_path": False,
        "network_path":     "",
    },
}

# Fallback defaults bij ontbrekend of corrupt network_data.json
_DEFAULT_NETWORK = {
    "version": "1.0",
    "sites": [],
    "devices": [],
    "ports": [],
    "endpoints": [],
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
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    base, ext   = os.path.splitext(path)
    backup_path = f"{base}_backup_{timestamp}{ext}"
    try:
        shutil.copy2(path, backup_path)
    except OSError:
        pass


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
    nd_cfg   = settings.get("network_data", {})

    if nd_cfg.get("use_network_path", False):
        net_path = nd_cfg.get("network_path", "").strip()
        if net_path and is_network_path_available(net_path):
            return os.path.join(net_path, "network_data.json")

    return _NETWORK_FILE


def get_network_data_source_label() -> tuple[str, bool]:
    settings = load_settings()
    nd_cfg   = settings.get("network_data", {})

    if nd_cfg.get("use_network_path", False):
        net_path = nd_cfg.get("network_path", "").strip()
        if net_path and is_network_path_available(net_path):
            return net_path, True
        elif net_path:
            return "Lokaal (fallback: netwerk niet bereikbaar)", False

    return "Lokaal", False


def get_settings_path() -> str:
    return _SETTINGS_FILE


# ---------------------------------------------------------------------------
# Network data (network_data.json)
# ---------------------------------------------------------------------------

def load_network_data() -> dict:
    """F3 — Laadt network_data van het actieve pad (lokaal of netwerk)."""
    _ensure_data_dir()
    path = get_network_data_path()
    data = _load_json(path)

    if data is None:
        if os.path.exists(path):
            _make_backup(path)
        _save_json(path, _DEFAULT_NETWORK)
        return dict(_DEFAULT_NETWORK)

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


def validate_network_data(data: dict) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "Geen geldig JSON object."
    for key in _REQUIRED_NETWORK_KEYS:
        if key not in data:
            return False, f"Verplichte sleutel ontbreekt: '{key}'"
    return True, ""