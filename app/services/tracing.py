# =============================================================================
# Networkmap_Creator
# File:    app/services/tracing.py
# Role:    Trace berekening — pure logica, GEEN Qt imports
# Version: 1.0.0
# Author:  Barremans
# =============================================================================
#
# BELANGRIJK: Dit bestand bevat GEEN Qt imports.
# Input:  port_id of wall_outlet_id
# Output: geordende lijst van TraceStep dicts
#
# Trace richting: endpoint → wall_outlet → pp_back → pp_front → switch
#
# Patchpanel interne doorverbinding:
#   back port nummer N ↔ front port nummer N (zelfde nummer = doorverbonden)
# =============================================================================


# ---------------------------------------------------------------------------
# Datastructuur voor één trace stap
# ---------------------------------------------------------------------------

def _make_step(obj_type: str, obj_id: str, label: str,
               side: str = "", cable_type: str = "",
               port_name: str = "") -> dict:
    """
    Maak één trace stap dict aan.

    obj_type  : "port" | "wall_outlet" | "endpoint"
    obj_id    : ID van het object
    label     : leesbare naam (bv. "PP1 — Port 3 (BACK)")
    side      : "front" | "back" | "" (voor wall_outlet/endpoint)
    cable_type: kabeltype van de verbinding die hierna volgt
    port_name : raw poortnaam (bv. "Gi1/0/1")
    """
    return {
        "obj_type":   obj_type,
        "obj_id":     obj_id,
        "label":      label,
        "side":       side,
        "cable_type": cable_type,
        "port_name":  port_name,
    }


# ---------------------------------------------------------------------------
# Hulpfuncties voor data opzoeken
# ---------------------------------------------------------------------------

def _get_port(data: dict, port_id: str) -> dict | None:
    return next((p for p in data.get("ports", []) if p["id"] == port_id), None)


def _get_device(data: dict, device_id: str) -> dict | None:
    return next((d for d in data.get("devices", []) if d["id"] == device_id), None)


def _get_wall_outlet(data: dict, outlet_id: str) -> dict | None:
    for site in data.get("sites", []):
        for room in site.get("rooms", []):
            for wo in room.get("wall_outlets", []):
                if wo["id"] == outlet_id:
                    return wo
    return None


def _get_endpoint(data: dict, endpoint_id: str) -> dict | None:
    return next((e for e in data.get("endpoints", []) if e["id"] == endpoint_id), None)


def _get_connection_from(data: dict, from_id: str, from_type: str) -> dict | None:
    """Zoek verbinding die vertrekt vanuit een bepaald object."""
    return next(
        (c for c in data.get("connections", [])
         if c["from_id"] == from_id and c["from_type"] == from_type),
        None
    )


def _get_connection_to(data: dict, to_id: str, to_type: str) -> dict | None:
    """Zoek verbinding die aankomt bij een bepaald object."""
    return next(
        (c for c in data.get("connections", [])
         if c["to_id"] == to_id and c["to_type"] == to_type),
        None
    )


def _get_connection_for_port(data: dict, port_id: str) -> dict | None:
    """Zoek verbinding waarbij de poort betrokken is (als from of to)."""
    return next(
        (c for c in data.get("connections", [])
         if (c["from_id"] == port_id and c["from_type"] == "port") or
            (c["to_id"]   == port_id and c["to_type"]   == "port")),
        None
    )


def _get_partner_port(data: dict, port_id: str) -> tuple[dict | None, dict | None]:
    """
    Geeft (verbinding, partner_port) terug voor een poort.
    Partner_port is het andere uiteinde van de verbinding (als het een port is).
    """
    conn = _get_connection_for_port(data, port_id)
    if not conn:
        return None, None
    if conn["from_id"] == port_id and conn["to_type"] == "port":
        return conn, _get_port(data, conn["to_id"])
    if conn["to_id"] == port_id and conn["from_type"] == "port":
        return conn, _get_port(data, conn["from_id"])
    return conn, None


def _get_patchpanel_partner(data: dict, port: dict) -> dict | None:
    """
    Patchpanel interne doorverbinding:
    back port nummer N ↔ front port nummer N op hetzelfde device.
    """
    device = _get_device(data, port["device_id"])
    if not device or device.get("type") != "patchpanel":
        return None
    target_side = "front" if port["side"] == "back" else "back"
    target_num  = port["number"]
    return next(
        (p for p in data.get("ports", [])
         if p["device_id"] == port["device_id"]
         and p["side"] == target_side
         and p["number"] == target_num),
        None
    )


def _port_label(port: dict, device: dict) -> str:
    """Maak een leesbaar label voor een poort: 'DeviceNaam — PortNaam (SIDE)'."""
    side_str = port["side"].upper()
    return f"{device.get('name', '?')} — {port.get('name', '?')} ({side_str})"


# ---------------------------------------------------------------------------
# Conflict detectie
# ---------------------------------------------------------------------------

def port_has_conflict(data: dict, port_id: str) -> bool:
    """Geeft True terug als de poort al in gebruik is."""
    return _get_connection_for_port(data, port_id) is not None


def get_conflicts(data: dict) -> list[dict]:
    """
    Geeft een lijst van conflicten terug:
    poorten die meer dan één verbinding hebben (zou niet mogen voorkomen).
    """
    from collections import Counter
    port_usage: Counter = Counter()
    for conn in data.get("connections", []):
        if conn["from_type"] == "port":
            port_usage[conn["from_id"]] += 1
        if conn["to_type"] == "port":
            port_usage[conn["to_id"]] += 1

    conflicts = []
    for port_id, count in port_usage.items():
        if count > 1:
            port   = _get_port(data, port_id)
            device = _get_device(data, port["device_id"]) if port else None
            conflicts.append({
                "port_id":   port_id,
                "port_name": port.get("name", "?") if port else "?",
                "device":    device.get("name", "?") if device else "?",
                "count":     count,
            })
    return conflicts


# ---------------------------------------------------------------------------
# Hoofd trace functie — startend vanuit een POORT
# ---------------------------------------------------------------------------

def trace_from_port(data: dict, port_id: str) -> list[dict]:
    """
    Publieke wrapper — berekent de volledige trace startend vanuit een poort.
    Retourneert geordende lijst van stap-dicts inclusief wall_outlet en endpoint.
    """
    return _trace_from_port_internal(data, port_id, skip_outlet_id=None)


def _trace_from_port_internal(data: dict, port_id: str,
                               skip_outlet_id: str | None) -> list[dict]:
    """
    Interne trace implementatie.
    skip_outlet_id: wall_outlet ID dat niet opnieuw toegevoegd mag worden
                    (gebruikt door trace_from_wall_outlet om lussen te vermijden).
    """
    steps   : list[dict] = []
    visited : set[str]   = set()
    max_steps = 20

    def _follow(current_port_id: str):
        if len(steps) >= max_steps or current_port_id in visited:
            return
        visited.add(current_port_id)

        port   = _get_port(data, current_port_id)
        if not port:
            return
        device = _get_device(data, port["device_id"])
        if not device:
            return

        label = _port_label(port, device)
        conn, partner_port = _get_partner_port(data, current_port_id)
        cable = conn["cable_type"] if conn else ""

        steps.append(_make_step(
            obj_type   = "port",
            obj_id     = current_port_id,
            label      = label,
            side       = port["side"],
            cable_type = cable,
            port_name  = port.get("name", ""),
        ))

        if not conn:
            # Geen externe verbinding — maar als dit een patchpanel poort is,
            # volg de interne doorverbinding naar de andere kant
            if device.get("type") == "patchpanel":
                internal = _get_patchpanel_partner(data, port)
                if internal and internal["id"] not in visited:
                    _follow(internal["id"])
            return

        # Verbinding naar wall_outlet?
        if conn["from_id"] == current_port_id and conn["to_type"] == "wall_outlet":
            if conn["to_id"] != skip_outlet_id:
                _follow_wall_outlet(conn["to_id"], cable)
            elif device.get("type") == "patchpanel":
                # We komen van wall_outlet kant — volg intern door naar front
                internal = _get_patchpanel_partner(data, port)
                if internal and internal["id"] not in visited:
                    _follow(internal["id"])
            return
        if conn["to_id"] == current_port_id and conn["from_type"] == "wall_outlet":
            if conn["from_id"] != skip_outlet_id:
                _follow_wall_outlet(conn["from_id"], cable)
            elif device.get("type") == "patchpanel":
                # We komen van wall_outlet kant — volg intern door naar front
                internal = _get_patchpanel_partner(data, port)
                if internal and internal["id"] not in visited:
                    _follow(internal["id"])
            return

        # Verbinding naar andere poort?
        if partner_port and partner_port["id"] not in visited:
            partner_device = _get_device(data, partner_port["device_id"])
            if partner_device and partner_device.get("type") == "patchpanel":
                visited.add(partner_port["id"])
                steps.append(_make_step(
                    obj_type   = "port",
                    obj_id     = partner_port["id"],
                    label      = _port_label(partner_port, partner_device),
                    side       = partner_port["side"],
                    cable_type = "",
                    port_name  = partner_port.get("name", ""),
                ))
                internal = _get_patchpanel_partner(data, partner_port)
                if internal and internal["id"] not in visited:
                    _follow(internal["id"])
            else:
                _follow(partner_port["id"])

    def _follow_wall_outlet(outlet_id: str, cable: str):
        outlet = _get_wall_outlet(data, outlet_id)
        if not outlet:
            return
        steps.append(_make_step(
            obj_type   = "wall_outlet",
            obj_id     = outlet_id,
            label      = outlet.get("name", "?"),
            side       = "",
            cable_type = cable,
            port_name  = "",
        ))
        ep_id = outlet.get("endpoint_id")
        if ep_id:
            ep = _get_endpoint(data, ep_id)
            if ep:
                steps.append(_make_step(
                    obj_type="endpoint", obj_id=ep_id,
                    label=ep.get("name", "?"),
                ))

    _follow(port_id)
    return steps


# ---------------------------------------------------------------------------
# Hoofd trace functie — startend vanuit een WALL OUTLET
# ---------------------------------------------------------------------------

def trace_from_wall_outlet(data: dict, outlet_id: str) -> list[dict]:
    """
    Berekent de volledige trace startend vanuit een wandpunt.
    Retourneert stappen van endpoint → wall_outlet → ... → switch.
    """
    outlet = _get_wall_outlet(data, outlet_id)
    if not outlet:
        return []

    steps: list[dict] = []

    # Endpoint toevoegen indien aanwezig
    ep_id = outlet.get("endpoint_id")
    if ep_id:
        ep = _get_endpoint(data, ep_id)
        if ep:
            steps.append(_make_step(
                obj_type="endpoint", obj_id=ep_id,
                label=ep.get("name", "?"),
            ))

    # Verbinding opzoeken voor het wandpunt
    conn = _get_connection_to(data, outlet_id, "wall_outlet")
    if not conn:
        conn = _get_connection_from(data, outlet_id, "wall_outlet")

    cable = conn["cable_type"] if conn else ""

    # Wandpunt zelf toevoegen
    steps.append(_make_step(
        obj_type="wall_outlet", obj_id=outlet_id,
        label=outlet.get("name", "?"), cable_type=cable,
    ))

    if not conn:
        return steps

    # Volg verbinding naar poort — geef outlet_id mee als al-bezochte stap
    # zodat trace_from_port de wall_outlet NIET opnieuw opneemt
    next_port_id = None
    if conn["from_type"] == "port":
        next_port_id = conn["from_id"]
    elif conn["to_type"] == "port":
        next_port_id = conn["to_id"]

    if next_port_id:
        # Bouw de port-trace op maar skip de terugkeer naar de wall_outlet
        port_steps = _trace_from_port_internal(data, next_port_id,
                                               skip_outlet_id=outlet_id)
        steps.extend(port_steps)

    return steps