# =============================================================================
# Networkmap_Creator
# File:    app/services/search_service.py
# Role:    Zoekfunctie over alle objecten — GEEN Qt imports
# Version: 2.7.0
# Author:  Barremans
# Changes: 2.7.0 — F12-b: min querylengte 1 voor filter_type="port".
#                  De interne _MIN_QUERY_LEN=2 check respecteert nu filter_type
#                  zodat zoeken op 1 teken werkt in de poort-tab van SearchWindow.
#          2.6.0 — Ranking: resultaten gesorteerd op relevantiescore (_score()).
#                  Exacte naammatch scoort het hoogst, begin-van-woord daarna,
#                  haystack-match het laagst. Bij gelijke score: naamlengte
#                  (kortere naam = specifieker = hogere prioriteit).
#                  Poort-label (device — poort) gescoord op beide delen.
#          2.5.0 — F12: zoeklogica uitgebreid/genormaliseerd.
#                  (1) MAC separator-/case-ongevoelig: query en opgeslagen waarde
#                      worden tot hex genormaliseerd vóór vergelijking, zodat
#                      'bc:f1:05:4f:58:1c', 'bc-f1-..' en 'bcf1054f581c' allemaal
#                      matchen. (helper _mac_match / _norm_hex)
#                  (2) MAC-zoeken over mac_eth + mac_wifi + compat 'mac' (F10).
#                  (3) Multi-token AND: elk spatie-gescheiden woord moet matchen
#                      ('SWITCH 3', 'VLAN 10', 'ROBIN HP' werken, volgorde vrij).
#                      Generieke helper _match_tokens(); naam blijft begin-van-woord,
#                      overige velden (type/label, IP, VLAN, side, locatie, S/N,
#                      model, merk, notes) via een per-object 'haystack'.
#                  Site/ruimte/rack blijven naam-only (geen ruis); device/endpoint/
#                  poort/wandpunt-in-'Alles' blijven breed. Snelle filters (V7)
#                  vallen buiten dit punt.
#          2.4.0 -- F9: zoekvelden uitgebreid. Device- en eindapparaat-tab zoeken
#                  nu net zo breed als 'Alles' (IP/MAC/serienummer/model/merk).
#                  Objecttype doorzoekbaar (raw + vertaald label). Poort-tab matcht
#                  ook VLAN-nummer (incl. 'vlan 10') en side.
#          2.3.1 -- F1: get_all_sites() voor v2 JSON
#          2.3.0 — Orphan devices uitgesloten van zoekresultaten:
#                   Devices zonder rack-slot EN zonder verbonden poorten
#                   worden niet getoond (zijn onnavigeerbaar en vervuilen resultaten)
#          2.2.0 — Poort zoeklogica uitgebreid (device-naam + poortnaam)
#          2.1.0 — Zoeklogica verfijnd (begin-van-woord matching)
#          2.0.0 — Extra velden: IP, MAC, serienummer, model, brand in resultaat
#          1.1.0 — Initiële versie
# =============================================================================

import re

from app.helpers.i18n import get_language, t
from app.helpers.settings_storage import get_outlet_location_label
from app.helpers.settings_storage import get_all_sites

# Minimale querylengte (op de volledige zoekterm)
_MIN_QUERY_LEN = 2


def search(data: dict, query: str, filter_type: str = "all") -> list:
    """
    Zoekt over alle objecten.

    filter_type:
      "all"         — breed: naam (begin-van-woord) + type/IP/MAC/VLAN/locatie/...
      "device"      — devices, breed (zoals 'all')
      "wall_outlet" — wandpunten, naam-only
      "endpoint"    — eindapparaten, breed (zoals 'all')
      "port"        — poorten, breed (poort- + device-naam + VLAN/side)
      "rack"        — racks/ruimtes/sites, naam-only

    Matching is multi-token (AND): elk spatie-gescheiden woord moet matchen.
    Resultaat: lijst van dicts met type, id, label, location, extra.
    """
    if not query or not query.strip():
        return []

    q = query.strip().lower()
    # F12-b — poort-tab: min 1 teken; alle andere: min 2 tekens
    _min_len = 1 if filter_type == "port" else _MIN_QUERY_LEN
    if len(q) < _min_len:
        return []

    tokens = q.split()          # F12 — multi-token AND
    if not tokens:
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
            if _match_tokens(tokens, site_name, broad=False):
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
                if _match_tokens(tokens, room_name, broad=False):
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
                    if _match_tokens(tokens, rack_name, broad=False):
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

                    # Tab "Alles": breed (locatie/endpoint/notes); specifieke tab: naam-only
                    broad = (filter_type == "all")
                    hay   = _hay(loc_label, loc_key, ep_name, wo.get("notes", ""))
                    if not _match_tokens(tokens, wo_name, hay, broad=broad):
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
            serial   = dev.get("serial", "")
            model    = dev.get("model", "")
            brand    = dev.get("brand", "")

            # 2.3.0 — Sla devices zonder rack-slot over: onnavigeerbaar
            if dev["id"] not in slotted_devids:
                continue

            dev_type       = dev.get("type", "other")
            dev_type_label = t(f"device_{dev_type}")

            # F12 — breed: naam (begin-van-woord) + haystack + genormaliseerde MAC's
            hay  = _hay(model, brand, ip, serial, dev_type, dev_type_label, dev.get("notes", ""))
            macs = (dev.get("mac", ""), dev.get("mac_eth", ""), dev.get("mac_wifi", ""))
            if not _match_tokens(tokens, dev_name, hay, macs=macs, broad=True):
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

            # F12 — naam-velden: poortnaam + device-naam; haystack: VLAN + side + notes
            vlan_str = str(vlan).strip() if vlan not in (None, "") else ""
            hay = _hay(f"vlan {vlan_str}" if vlan_str else "", vlan_str, side_str, notes)
            if not _match_tokens(tokens, (port_name, dev_label), hay, broad=True):
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
            model   = ep.get("model", "")
            brand   = ep.get("brand", "")
            serial  = ep.get("serial", "")

            ep_type       = ep.get("type", "other")
            ep_type_label = t(f"endpoint_{ep_type}")

            # F12 — breed: naam (begin-van-woord) + haystack + genormaliseerde MAC's
            hay  = _hay(model, brand, ep.get("location", ""), ip, serial,
                        ep_type, ep_type_label, ep.get("notes", ""))
            macs = (ep.get("mac", ""), ep.get("mac_eth", ""), ep.get("mac_wifi", ""))
            if not _match_tokens(tokens, ep_name, hay, macs=macs, broad=True):
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

    # 2.6.0 — Sorteer op relevantiescore (hoog = beter), daarna naamlengte (kort = specifieker)
    results.sort(key=lambda r: (-_score(tokens, r), len(r.get("label", ""))))
    return results


# ------------------------------------------------------------------
# Matchhulpfuncties
# ------------------------------------------------------------------

def _match_tokens(tokens, names, haystack: str = "", macs=(), broad: bool = True) -> bool:
    """
    F12 — multi-token AND. Elk token moet matchen op:
      - de naam/namen via begin-van-woord (_word_start_match), of
      - (alleen breed) een substring van de 'haystack', of
      - (alleen breed) een genormaliseerde MAC-match.
    `names` mag een string of een tuple van strings zijn.
    """
    if isinstance(names, str):
        names = (names,)
    for tok in tokens:
        hit = any(_word_start_match(tok, n) for n in names)
        if not hit and broad:
            hit = (tok in haystack) or _mac_match(tok, *macs)
        if not hit:
            return False
    return True


def _hay(*parts) -> str:
    """Bouw een lowercase 'haystack' string uit niet-lege velden."""
    return " ".join(str(p).lower() for p in parts if p not in (None, ""))


def _norm_hex(s) -> str:
    """Strip alles behalve hex-tekens en zet om naar lowercase (voor MAC-vergelijking)."""
    return re.sub(r"[^0-9a-f]", "", str(s).lower())


def _mac_match(query: str, *macs) -> bool:
    """
    F12 — separator-/case-ongevoelige MAC-match. Normaliseert zowel de query als
    elke opgeslagen MAC tot louter hex en vergelijkt als substring.
    Token korter dan 2 hex-tekens wordt genegeerd (voorkomt ruis op '1', 'ip', ...).
    """
    qn = _norm_hex(query)
    if len(qn) < 2:
        return False
    for m in macs:
        mn = _norm_hex(m)
        if mn and qn in mn:
            return True
    return False


def _word_start_match(query: str, text: str) -> bool:
    """
    True als query matcht aan het begin van enig woord in text.
    Woorden gescheiden door spatie, koppelteken, underscore, punt, etc.
    Case-insensitief.
    """
    if not query or not text:
        return False
    t_low = text.lower()
    q_low = query.lower()
    if t_low.startswith(q_low):
        return True
    pattern = r'(?<![a-z0-9])' + re.escape(q_low)
    return bool(re.search(pattern, t_low))




def _score(tokens: list[str], result: dict) -> int:
    """
    2.6.0 — Relevantiescore voor een zoekresultaat. Hogere score = beter.

    Per token:
      +40  exacte naammatch  (volledige label == token)
      +30  begin-van-naam    (label start met token)
      +20  begin-van-woord   (woord in label start met token, via _word_start_match)
      +10  haystack-match    (token gevonden in extra of location)
       +5  typematch         (poort: device-naam deel matcht begin-van-woord)

    Score = som over alle tokens. Gelijke score → kortere naam wint (buiten deze fn).
    """
    label    = result.get("label", "").lower()
    extra    = result.get("extra", "").lower()
    location = result.get("location", "").lower()
    hay      = f"{extra} {location}"

    score = 0
    for tok in tokens:
        t_low = tok.lower()
        if label == t_low:
            score += 40
        elif label.startswith(t_low):
            score += 30
        elif _word_start_match(t_low, label):
            score += 20
        elif t_low in hay:
            score += 10
        # Poort: label is "device — poort"; check ook device-deel apart
        if result.get("type") == "port" and "  —  " in label:
            dev_part, port_part = label.split("  —  ", 1)
            if _word_start_match(t_low, port_part) and score < 20:
                score += 20
            elif _word_start_match(t_low, dev_part) and score < 5:
                score += 5
    return score


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