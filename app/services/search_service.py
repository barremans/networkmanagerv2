# =============================================================================
# Networkmap_Creator
# File:    app/services/search_service.py
# Role:    Zoekfunctie over alle objecten — GEEN Qt imports
# Version: 2.3.1
# Author:  Barremans
# Changes: 2.3.1 -- F1: get_all_sites() voor v2 JSON
#          2.3.0 — Orphan devices uitgesloten van zoekresultaten:
#                   Devices zonder rack-slot EN zonder verbonden poorten
#                   worden niet getoond (zijn onnavigeerbaar en vervuilen resultaten)
#                   _build_device_loc_map uitgebreid met set van "navigeerbare" device IDs
#          2.2.0 — Poort zoeklogica uitgebreid:
#                   Specifieke tab zoekt ook op device naam ("switch 3" matcht Port 3 van SWITCH)
#                   Geen minimumlengte voor poorten (1 teken volstaat)
#                   Zoekterm gesplitst: elke component matcht onafhankelijk op poort + device
#          2.1.0 — Zoeklogica verfijnd:
#                   Minimaal 2 tekens vereist
#                   Tab "Alles": begin-van-woord matching op alle velden
#                   Specifieke tab: enkel naam-matching (IP/MAC/S/N = toekomstige uitbreiding)
#                   Poort: notes/vlan/side toegevoegd aan match
#                   _match_name(): begin-van-woord match op primaire naam
#                   _match_extra(): substring match op exacte velden (IP, MAC, S/N)
#                   _word_start_match(): query matcht begin van enig woord in tekst
#          2.0.0 — Extra velden: IP, MAC, serienummer, model, brand in resultaat
#                   "extra" veld voor weergave in zoekvenster
#                   Wandpunt locatielabel ipv raw key
#                   Verbindingsstatus in resultaat (in_use)
#                   _room_id / _site_id / _rack_id altijd aanwezig
#          1.1.0 — Initiële versie
# =============================================================================

import re

from app.helpers.i18n import get_language
from app.helpers.settings_storage import get_outlet_location_label
from app.helpers.settings_storage import get_all_sites

# Minimale querylengte
_MIN_QUERY_LEN = 2


def search(data: dict, query: str, filter_type: str = "all") -> list:
    """
    Zoekt over alle objecten.

    filter_type:
      "all"         — begin-van-woord matching op naam + alle extra velden
      "device"      — enkel naam-matching op devices
      "wall_outlet" — enkel naam-matching op wandpunten
      "endpoint"    — enkel naam-matching op eindapparaten
      "port"        — enkel naam-matching op poorten
      "rack"        — enkel naam-matching op racks/ruimtes/sites

    Resultaat: lijst van dicts met type, id, label, location, extra.
    """
    if not query or not query.strip():
        return []

    q = query.strip().lower()

    if len(q) < _MIN_QUERY_LEN:
        return []

    results = []
    lang    = get_language()

    # Verbonden poorten/wandpunten set
    connected_ports   = set()
    connected_outlets = set()
    for conn in data.get("connections", []):
        if conn.get("from_type") == "port":        connected_ports.add(conn["from_id"])
        if conn.get("to_type")   == "port":        connected_ports.add(conn["to_id"])
        if conn.get("from_type") == "wall_outlet": connected_outlets.add(conn["from_id"])
        if conn.get("to_type")   == "wall_outlet": connected_outlets.add(conn["to_id"])

    # Device locatie map + set van navigeerbare device IDs (in rack-slot)
    dev_loc_map    = _build_device_loc_map(data)
    slotted_devids = set(dev_loc_map.keys())   # 2.3.0 — alleen devices met slot zijn navigeerbaar

    # ── Bepaal welke types te zoeken ──────────────────────────────────
    search_sites    = filter_type in ("all", "rack")
    search_rooms    = filter_type in ("all", "rack")
    search_racks    = filter_type in ("all", "rack")
    search_outlets  = filter_type in ("all", "wall_outlet")
    search_devices  = filter_type in ("all", "device")
    search_ports    = filter_type in ("all", "port")
    search_endpoints = filter_type in ("all", "endpoint")

    for site in get_all_sites(data):
        site_name = site.get("name", "")
        site_id   = site["id"]

        # ── Site ─────────────────────────────────────────────────────
        if search_sites:
            if _name_match(q, site_name, filter_type):
                results.append({
                    "type":     "site",
                    "id":       site_id,
                    "label":    site_name,
                    "location": site.get("location", ""),
                    "extra":    "",
                    "_site_id": site_id,
                    "_room_id": "",
                    "_rack_id": "",
                })

        for room in site.get("rooms", []):
            room_name = room.get("name", "")
            room_id   = room["id"]
            room_loc  = f"{site_name}  →  {room_name}"

            # ── Ruimte ───────────────────────────────────────────────
            if search_rooms:
                if _name_match(q, room_name, filter_type):
                    results.append({
                        "type":     "room",
                        "id":       room_id,
                        "label":    room_name,
                        "location": site_name,
                        "extra":    "",
                        "_site_id": site_id,
                        "_room_id": room_id,
                        "_rack_id": "",
                    })

            # ── Racks ────────────────────────────────────────────────
            if search_racks:
                for rack in room.get("racks", []):
                    rack_name = rack.get("name", "")
                    rack_id   = rack["id"]
                    if _name_match(q, rack_name, filter_type):
                        results.append({
                            "type":     "rack",
                            "id":       rack_id,
                            "label":    rack_name,
                            "location": room_loc,
                            "extra":    f"{rack.get('total_units', '?')}U",
                            "_site_id": site_id,
                            "_room_id": room_id,
                            "_rack_id": rack_id,
                        })

            # ── Wandpunten ───────────────────────────────────────────
            if search_outlets:
                for wo in room.get("wall_outlets", []):
                    wo_name   = wo.get("name", "")
                    loc_key   = wo.get("location_description", "")
                    loc_label = get_outlet_location_label(loc_key, lang) if loc_key else ""
                    ep_name   = ""
                    ep_id_ref = wo.get("endpoint_id", "")
                    if ep_id_ref:
                        ep_obj = next((e for e in data.get("endpoints", [])
                                       if e["id"] == ep_id_ref), None)
                        if ep_obj:
                            ep_name = ep_obj.get("name", "")

                    # Tab "Alles": naam + locatie + endpoint naam
                    # Specifieke tab: alleen wandpunt naam
                    if filter_type == "all":
                        match = _word_start_match(q, wo_name) or \
                                _word_start_match(q, loc_label) or \
                                _word_start_match(q, loc_key) or \
                                _word_start_match(q, ep_name) or \
                                _word_start_match(q, wo.get("notes", ""))
                    else:
                        match = _word_start_match(q, wo_name)

                    if not match:
                        continue

                    extra_parts = []
                    if loc_label:
                        extra_parts.append(loc_label)
                    if ep_name:
                        extra_parts.append(f"🖥 {ep_name}")

                    # Verbindingslabel
                    conn_label = ""
                    for conn in data.get("connections", []):
                        if conn.get("from_id") == wo["id"] or conn.get("to_id") == wo["id"]:
                            port_id = conn["to_id"] if conn.get("from_id") == wo["id"] else conn["from_id"]
                            port = next((p for p in data.get("ports", []) if p["id"] == port_id), None)
                            dev  = next((d for d in data.get("devices", [])
                                         if d["id"] == port.get("device_id", "")), None) if port else None
                            if port and dev:
                                conn_label = f"⬡ {dev['name']} — {port.get('name','?')}"
                            break
                    if conn_label:
                        extra_parts.append(conn_label)

                    results.append({
                        "type":     "wall_outlet",
                        "id":       wo["id"],
                        "label":    wo_name,
                        "location": f"{site_name}  →  {room_name}",
                        "extra":    "  ·  ".join(extra_parts),
                        "in_use":   wo["id"] in connected_outlets,
                        "_site_id": site_id,
                        "_room_id": room_id,
                        "_rack_id": "",
                    })

    # ── Devices ──────────────────────────────────────────────────────
    if search_devices:
        for dev in data.get("devices", []):
            dev_name = dev.get("name", "")
            ip       = dev.get("ip", "")
            mac      = dev.get("mac", "")
            serial   = dev.get("serial", "")
            model    = dev.get("model", "")
            brand    = dev.get("brand", "")

            # 2.3.0 — Sla devices zonder rack-slot over: onnavigeerbaar
            if dev["id"] not in slotted_devids:
                continue

            if filter_type == "all":
                match = _word_start_match(q, dev_name) or \
                        _word_start_match(q, model) or \
                        _word_start_match(q, brand) or \
                        _exact_match(q, ip) or \
                        _exact_match(q, mac) or \
                        _exact_match(q, serial) or \
                        _word_start_match(q, dev.get("notes", ""))
            else:
                # Specifieke tab: enkel naam
                # TODO: v2.4 — ook IP/MAC/S/N bij device-tab
                match = _word_start_match(q, dev_name)

            if not match:
                continue

            loc_info    = dev_loc_map.get(dev["id"], {})
            extra_parts = []
            if ip:     extra_parts.append(f"IP: {ip}")
            if model:  extra_parts.append(model)
            if serial: extra_parts.append(f"S/N: {serial}")
            results.append({
                "type":     "device",
                "id":       dev["id"],
                "label":    dev_name,
                "location": loc_info.get("label", ""),
                "extra":    "  ·  ".join(extra_parts),
                "_site_id": loc_info.get("site_id", ""),
                "_room_id": loc_info.get("room_id", ""),
                "_rack_id": loc_info.get("rack_id", ""),
            })

    # ── Poorten ──────────────────────────────────────────────────────
    if search_ports:
        for port in data.get("ports", []):
            port_name = port.get("name", "")
            side_str  = port.get("side", "")
            vlan      = port.get("vlan")
            notes     = port.get("notes", "")

            dev = next((d for d in data.get("devices", [])
                        if d["id"] == port["device_id"]), None)
            dev_label = dev["name"] if dev else port["device_id"]
            loc_info  = dev_loc_map.get(port["device_id"], {})

            # 2.3.0 — Sla poorten van devices zonder rack-slot over
            if port["device_id"] not in slotted_devids:
                continue

            if filter_type == "all":
                match = _word_start_match(q, port_name) or \
                        _word_start_match(q, dev_label) or \
                        _word_start_match(q, notes) or \
                        _exact_match(q, str(vlan) if vlan else "")
            else:
                # 2.2.0 — Poort tab: zoek op poortnaam EN device naam
                # Ook multi-word queries ondersteunen:
                # "switch 3" → matcht port_name "Port 3" + dev_label "SWITCH ..."
                # "patchpanel 13" → matcht port_name "Port 13" + dev_label "PATCHPANEL ..."
                match = _port_query_match(q, port_name, dev_label)

            if not match:
                continue

            extra_parts = [side_str.upper()] if side_str else []
            if vlan:
                extra_parts.append(f"VLAN {vlan}")
            results.append({
                "type":     "port",
                "id":       port["id"],
                "label":    f"{dev_label}  —  {port_name}",
                "location": loc_info.get("label", ""),
                "extra":    "  ·  ".join(extra_parts),
                "in_use":   port["id"] in connected_ports,
                "_site_id": loc_info.get("site_id", ""),
                "_room_id": loc_info.get("room_id", ""),
                "_rack_id": loc_info.get("rack_id", ""),
            })

    # ── Eindapparaten ────────────────────────────────────────────────
    if search_endpoints:
        for ep in data.get("endpoints", []):
            ep_name = ep.get("name", "")
            ip      = ep.get("ip", "")
            mac     = ep.get("mac", "")
            model   = ep.get("model", "")
            brand   = ep.get("brand", "")
            serial  = ep.get("serial", "")

            if filter_type == "all":
                match = _word_start_match(q, ep_name) or \
                        _word_start_match(q, model) or \
                        _word_start_match(q, brand) or \
                        _word_start_match(q, ep.get("location", "")) or \
                        _exact_match(q, ip) or \
                        _exact_match(q, mac) or \
                        _exact_match(q, serial) or \
                        _word_start_match(q, ep.get("notes", ""))
            else:
                # Specifieke tab: enkel naam
                # TODO: v2.2 — ook IP/MAC/S/N bij endpoint-tab
                match = _word_start_match(q, ep_name)

            if not match:
                continue

            # Zoek via wandpunt
            ep_loc      = ""
            ep_room_id  = ""
            ep_site_id  = ""
            outlet_name = ""
            for site in get_all_sites(data):
                for room in site.get("rooms", []):
                    for wo in room.get("wall_outlets", []):
                        if wo.get("endpoint_id") == ep["id"]:
                            ep_loc      = f"{site['name']}  →  {room['name']}"
                            ep_room_id  = room["id"]
                            ep_site_id  = site["id"]
                            outlet_name = wo.get("name", "")

            extra_parts = []
            if ip:          extra_parts.append(f"IP: {ip}")
            if model:       extra_parts.append(model)
            if serial:      extra_parts.append(f"S/N: {serial}")
            if outlet_name: extra_parts.append(f"🌐 {outlet_name}")

            results.append({
                "type":     "endpoint",
                "id":       ep["id"],
                "label":    ep_name,
                "location": ep_loc,
                "extra":    "  ·  ".join(extra_parts),
                "_site_id": ep_site_id,
                "_room_id": ep_room_id,
                "_rack_id": "",
            })

    return results


# ------------------------------------------------------------------
# Matchhulpfuncties
# ------------------------------------------------------------------

def _port_query_match(query: str, port_name: str, dev_name: str) -> bool:
    """
    2.2.0 — Slimme poort-matching die werkt voor zowel:
    - poortnaam alleen:    "13"           → matcht "Port 13"
    - device alleen:       "switch"       → matcht alle poorten van SWITCH
    - combinatie:          "switch 3"     → matcht Port 3 van SWITCH
    - combinatie:          "patchpanel 13"→ matcht Port 13 van PATCHPANEL A/B/...

    Strategie: splits query op spaties. Als er meerdere delen zijn,
    dan moet elk deel matchen op port_name OF dev_name (in combinatie).
    Bij één deel: normale word_start_match op beide velden.
    """
    if not query:
        return False
    parts = query.lower().split()
    if len(parts) == 1:
        # Eén woord — matcht op poortnaam of device naam
        return _word_start_match(query, port_name) or _word_start_match(query, dev_name)
    # Meerdere woorden — elk deel moet matchen op port_name of dev_name
    # Voorbeeld: ["switch", "3"] → "switch" matcht dev, "3" matcht port
    for part in parts:
        if not (_word_start_match(part, port_name) or _word_start_match(part, dev_name)):
            return False
    return True


def _word_start_match(query: str, text: str) -> bool:
    """
    True als query matcht aan het begin van enig woord in text.
    Woorden worden gescheiden door spatie, koppelteken, underscore, punt, cijfer-letter-overgang.
    Case-insensitief.
    """
    if not query or not text:
        return False
    t = text.lower()
    q = query.lower()
    # Direct prefix van de hele string
    if t.startswith(q):
        return True
    # Begin van een woord (na niet-alfanumeriek teken)
    pattern = r'(?<![a-z0-9])' + re.escape(q)
    return bool(re.search(pattern, t))


def _exact_match(query: str, text: str) -> bool:
    """
    Exacte substring match — voor IP, MAC, serienummer.
    Case-insensitief.
    """
    if not query or not text:
        return False
    return query.lower() in text.lower()


def _name_match(query: str, name: str, filter_type: str) -> bool:
    """
    Naam-matching: altijd begin-van-woord.
    """
    return _word_start_match(query, name)


# ------------------------------------------------------------------
# Legacy wrapper — compatibiliteit met bestaande aanroepen zonder filter_type
# ------------------------------------------------------------------

def _match(query: str, *fields) -> bool:
    """Legacy — niet meer primair gebruikt, behouden voor achterwaartse compat."""
    return any(query in str(f).lower() for f in fields if f)


def _build_device_loc_map(data: dict) -> dict:
    result = {}
    for site in get_all_sites(data):
        for room in site.get("rooms", []):
            for rack in room.get("racks", []):
                for slot in rack.get("slots", []):
                    dev_id = slot.get("device_id", "")
                    u      = slot.get("u_start", "?")
                    result[dev_id] = {
                        "label":   f"{site['name']}  →  {room['name']}  →  {rack['name']}  U{u}",
                        "rack_id": rack["id"],
                        "room_id": room["id"],
                        "site_id": site["id"],
                    }
    return result