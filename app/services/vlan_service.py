# =============================================================================
# Networkmap_Creator
# File:    app/services/vlan_service.py
# Role:    VLAN definities laden/opslaan + trace-propagatie
# Version: 1.0.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie
# =============================================================================

import json
import os
from app.services import tracing

_VLAN_CONFIG_PATH = None   # wordt gezet via init()


def _config_path() -> str:
    global _VLAN_CONFIG_PATH
    if _VLAN_CONFIG_PATH:
        return _VLAN_CONFIG_PATH
    # Naast network_data.json — zelfde map
    try:
        from app.helpers import settings_storage
        base = os.path.dirname(settings_storage.get_network_data_path())
    except Exception:
        base = os.path.expanduser("~")
    return os.path.join(base, "vlan_config.json")


# ---------------------------------------------------------------------------
# Laden / Opslaan
# ---------------------------------------------------------------------------

def load_vlans() -> list[dict]:
    """
    Laad VLAN definities uit vlan_config.json.
    Elke entry: {"id": int, "name": str, "description": str, "color": str}
    """
    path = _config_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("vlans", [])
    except Exception:
        return []


def save_vlans(vlans: list[dict]) -> bool:
    """Sla VLAN definities op naar vlan_config.json."""
    path = _config_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"vlans": vlans}, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def get_vlan_by_id(vlan_id: int) -> dict | None:
    for v in load_vlans():
        if v.get("id") == vlan_id:
            return v
    return None


def vlan_label(vlan_id: int) -> str:
    """Geeft 'VLAN 100 — Clients' of 'VLAN 100' als geen naam."""
    v = get_vlan_by_id(vlan_id)
    if v and v.get("name"):
        return f"VLAN {vlan_id} — {v['name']}"
    return f"VLAN {vlan_id}"


# ---------------------------------------------------------------------------
# Propagatie
# ---------------------------------------------------------------------------

def collect_trace_objects(data: dict, start_id: str, start_type: str) -> dict:
    """
    Volg de volledige trace vanuit een poort of wandpunt en
    verzamel alle poort-IDs en wandpunt-IDs in de keten.

    Returns:
        {
            "port_ids":   [str, ...],
            "outlet_ids": [str, ...],
        }
    """
    port_ids   = set()
    outlet_ids = set()

    if start_type == "port":
        steps = tracing.trace_from_port(data, start_id)
    else:
        steps = tracing.trace_from_wall_outlet(data, start_id)

    for step in steps:
        if step["obj_type"] == "port":
            port_ids.add(step["obj_id"])
        elif step["obj_type"] == "wall_outlet":
            outlet_ids.add(step["obj_id"])

    # Startobject zelf ook opnemen
    if start_type == "port":
        port_ids.add(start_id)
    else:
        outlet_ids.add(start_id)

    return {"port_ids": list(port_ids), "outlet_ids": list(outlet_ids)}


def get_trace_vlans(data: dict, port_ids: list, outlet_ids: list) -> set[int]:
    """
    Verzamel alle VLAN nummers die al aanwezig zijn in de trace-objecten.
    """
    vlans = set()
    for p in data.get("ports", []):
        if p["id"] in port_ids and p.get("vlan"):
            vlans.add(int(p["vlan"]))
    for s in data.get("sites", []):
        for r in s.get("rooms", []):
            for wo in r.get("wall_outlets", []):
                if wo["id"] in outlet_ids and wo.get("vlan"):
                    vlans.add(int(wo["vlan"]))
    return vlans


def propagate_vlan(data: dict, port_ids: list, outlet_ids: list,
                   vlan_id: int) -> dict:
    """
    Wijs vlan_id toe aan alle poorten en wandpunten in de trace.
    Retourneert een dict met conflicten voor waarschuwing:
        {
            "port_conflicts":   [{"id": str, "name": str, "current_vlan": int}, ...],
            "outlet_conflicts": [{"id": str, "name": str, "current_vlan": int}, ...],
        }
    """
    port_conflicts   = []
    outlet_conflicts = []

    # Check conflicten
    for p in data.get("ports", []):
        if p["id"] in port_ids:
            existing = p.get("vlan")
            if existing and int(existing) != vlan_id:
                dev = next((d for d in data.get("devices", [])
                            if d["id"] == p.get("device_id")), None)
                dev_name = dev["name"] if dev else "?"
                port_conflicts.append({
                    "id":           p["id"],
                    "name":         f"{dev_name} / {p['name']}",
                    "current_vlan": int(existing),
                })

    for s in data.get("sites", []):
        for r in s.get("rooms", []):
            for wo in r.get("wall_outlets", []):
                if wo["id"] in outlet_ids:
                    existing = wo.get("vlan")
                    if existing and int(existing) != vlan_id:
                        outlet_conflicts.append({
                            "id":           wo["id"],
                            "name":         wo.get("name", wo["id"]),
                            "current_vlan": int(existing),
                        })

    return {
        "port_conflicts":   port_conflicts,
        "outlet_conflicts": outlet_conflicts,
    }


def apply_vlan(data: dict, port_ids: list, outlet_ids: list,
               vlan_id: int | None):
    """
    Pas vlan_id toe op alle opgegeven poorten en wandpunten.
    vlan_id=None verwijdert het VLAN.
    Muteert data in-place.
    """
    port_set   = set(port_ids)
    outlet_set = set(outlet_ids)

    for p in data.get("ports", []):
        if p["id"] in port_set:
            if vlan_id is None:
                p.pop("vlan", None)
            else:
                p["vlan"] = vlan_id

    for s in data.get("sites", []):
        for r in s.get("rooms", []):
            for wo in r.get("wall_outlets", []):
                if wo["id"] in outlet_set:
                    if vlan_id is None:
                        wo.pop("vlan", None)
                    else:
                        wo["vlan"] = vlan_id