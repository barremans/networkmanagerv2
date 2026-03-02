# =============================================================================
# Networkmap_Creator
# File:    app/services/search_service.py
# Role:    Zoekfunctie over alle objecten — GEEN Qt imports
# Version: 1.1.0
# Author:  Barremans
# =============================================================================


def search(data: dict, query: str) -> list:
    """
    Zoekt (case-insensitief) over sites, ruimtes, racks, devices,
    poorten, wall outlets en endpoints.

    Returns lijst van dicts:
        type     — "site" | "room" | "rack" | "device" | "port"
                   | "wall_outlet" | "endpoint"
        id       — object id
        label    — leesbare naam
        location — "Site → Ruimte → Rack → U1" (zoveel als beschikbaar)
    """
    if not query or not query.strip():
        return []

    q = query.strip().lower()
    results = []

    for site in data.get("sites", []):
        site_name = site.get("name", "")
        site_loc  = site_name

        # ── Site ─────────────────────────────────────────────────────
        if _match(q, site_name, site.get("location", "")):
            results.append({
                "type":     "site",
                "id":       site["id"],
                "label":    site_name,
                "location": site.get("location", ""),
            })

        for room in site.get("rooms", []):
            room_name = room.get("name", "")
            room_loc  = f"{site_loc} → {room_name}"

            # ── Ruimte ───────────────────────────────────────────────
            if _match(q, room_name, room.get("floor", "")):
                results.append({
                    "type":     "room",
                    "id":       room["id"],
                    "label":    room_name,
                    "location": site_loc,
                })

            for rack in room.get("racks", []):
                rack_name = rack.get("name", "")
                rack_loc  = f"{room_loc} → {rack_name}"

                # ── Rack ─────────────────────────────────────────────
                if _match(q, rack_name, rack.get("notes", "")):
                    results.append({
                        "type":     "rack",
                        "id":       rack["id"],
                        "label":    rack_name,
                        "location": room_loc,
                        # Extra navigatiedata
                        "_room_id": room["id"],
                        "_site_id": site["id"],
                    })

            # ── Wall outlets ─────────────────────────────────────────
            for wo in room.get("wall_outlets", []):
                if _match(q, wo.get("name", ""),
                             wo.get("location_description", "")):
                    results.append({
                        "type":     "wall_outlet",
                        "id":       wo["id"],
                        "label":    f"{wo.get('name', '')} — {wo.get('location_description', '')}",
                        "location": room_loc,
                        "_room_id": room["id"],
                        "_site_id": site["id"],
                    })

    # Bouw device-locatie map (device_id → rack/room/site info)
    dev_loc_map = _build_device_loc_map(data)

    # ── Devices ──────────────────────────────────────────────────────
    for dev in data.get("devices", []):
        if _match(q, dev.get("name", ""), dev.get("ip", ""),
                     dev.get("mac", ""), dev.get("serial", ""),
                     dev.get("model", ""), dev.get("brand", "")):
            loc_info = dev_loc_map.get(dev["id"], {})
            results.append({
                "type":     "device",
                "id":       dev["id"],
                "label":    dev.get("name", dev["id"]),
                "location": loc_info.get("label", ""),
                "_rack_id": loc_info.get("rack_id", ""),
                "_room_id": loc_info.get("room_id", ""),
                "_site_id": loc_info.get("site_id", ""),
            })

    # ── Poorten ──────────────────────────────────────────────────────
    for port in data.get("ports", []):
        if _match(q, port.get("name", "")):
            dev = next((d for d in data.get("devices", [])
                        if d["id"] == port["device_id"]), None)
            dev_label = dev["name"] if dev else port["device_id"]
            loc_info  = dev_loc_map.get(port["device_id"], {})
            results.append({
                "type":     "port",
                "id":       port["id"],
                "label":    f"{dev_label} — {port.get('name', '')} ({port.get('side', '')})",
                "location": loc_info.get("label", ""),
                "_rack_id": loc_info.get("rack_id", ""),
                "_room_id": loc_info.get("room_id", ""),
                "_site_id": loc_info.get("site_id", ""),
            })

    # ── Endpoints ────────────────────────────────────────────────────
    for ep in data.get("endpoints", []):
        if _match(q, ep.get("name", ""), ep.get("ip", ""),
                     ep.get("mac", ""), ep.get("model", ""),
                     ep.get("brand", "")):
            # Zoek via wall outlet
            ep_loc = ""
            ep_room_id = ""
            ep_site_id = ""
            for site in data.get("sites", []):
                for room in site.get("rooms", []):
                    for wo in room.get("wall_outlets", []):
                        if wo.get("endpoint_id") == ep["id"]:
                            ep_loc     = f"{site['name']} → {room['name']} → {wo.get('name', '')}"
                            ep_room_id = room["id"]
                            ep_site_id = site["id"]
            results.append({
                "type":     "endpoint",
                "id":       ep["id"],
                "label":    ep.get("name", ep["id"]),
                "location": ep_loc,
                "_room_id": ep_room_id,
                "_site_id": ep_site_id,
            })

    return results


# ------------------------------------------------------------------
# Hulpfuncties
# ------------------------------------------------------------------

def _match(query: str, *fields) -> bool:
    """True als query (lowercase) voorkomt in één van de velden."""
    return any(query in str(f).lower() for f in fields if f)


def _build_device_loc_map(data: dict) -> dict:
    """Bouwt device_id → {label, rack_id, room_id, site_id} map."""
    result = {}
    for site in data.get("sites", []):
        for room in site.get("rooms", []):
            for rack in room.get("racks", []):
                for slot in rack.get("slots", []):
                    dev_id = slot.get("device_id", "")
                    u      = slot.get("u_start", "?")
                    result[dev_id] = {
                        "label":   f"{site['name']} → {room['name']} → {rack['name']} → U{u}",
                        "rack_id": rack["id"],
                        "room_id": room["id"],
                        "site_id": site["id"],
                    }
    return result