# =============================================================================
# Networkmap_Creator
# File:    app/services/rack_export_md.py
# Role:    Tekstuele rack-export naar Markdown — E2
# Version: 1.3.0
# Author:  Barremans
# Changes: 1.0.0 — E2: initiële versie
#          1.1.0 — Volledige tracing via tracing.py; wandpunt-sectie per site
#          1.2.0 — Patchpanel weergave herschreven:
#                  VOOR-verbinding eerst, ACHTER-verbinding (wandpunt) daarna
#                  Geen inspringing-cascade meer voor PP — twee platte pijlen
#                  Niet-PP poorten: inspringing-cascade zoals voorheen
#          1.3.0 — Direct endpoint: _conn_dest() herkent to_type=="endpoint"
#                  _render_outlets_site() uitgebreid met "Direct verbonden" subsectie
# =============================================================================

from __future__ import annotations
import datetime


# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------

def _build_index(data: dict) -> dict:
    idx = {
        "dev":  {d["id"]: d for d in data.get("devices", [])},
        "port": {p["id"]: p for p in data.get("ports",   [])},
        "ep":   {e["id"]: e for e in data.get("endpoints", [])},
        "wo":   {},
        "wo_room": {},
    }
    for site in data.get("sites", []):
        for room in site.get("rooms", []):
            for wo in room.get("wall_outlets", []):
                idx["wo"][wo["id"]]      = wo
                idx["wo_room"][wo["id"]] = (site, room)
    return idx


# ---------------------------------------------------------------------------
# VLAN naam helper
# ---------------------------------------------------------------------------

def _vlan_label(data: dict, vlan_id) -> str:
    if not vlan_id:
        return ""
    for v in data.get("vlans", []):
        if str(v.get("id")) == str(vlan_id):
            name = v.get("name", "")
            return f"VLAN {vlan_id} ({name})" if name else f"VLAN {vlan_id}"
    return f"VLAN {vlan_id}"


def _is_patchpanel(dev: dict) -> bool:
    return dev.get("type") in ("patch_panel", "patchpanel")


# ---------------------------------------------------------------------------
# Stap-label helpers
# ---------------------------------------------------------------------------

def _step_label_port(step: dict, idx: dict, data: dict) -> str:
    """Geeft 'DevNaam › PortNaam (VOOR/ACHTER)  [VLAN x]' terug voor een port-stap."""
    port = idx["port"].get(step["obj_id"], {})
    dev  = idx["dev"].get(port.get("device_id", ""), {})
    side = {"front": "VOOR", "back": "ACHTER"}.get(step.get("side", ""), "")
    vlan = port.get("vlan")
    vlan_str = f"  [{_vlan_label(data, vlan)}]" if vlan else ""
    return f"{dev.get('name','?')} \u203a {port.get('name','?')} ({side}){vlan_str}"


def _step_label_wo(step: dict, idx: dict) -> str:
    """Geeft 'WP naam  (eindapparaat)' terug voor een wall_outlet-stap."""
    wo     = idx["wo"].get(step["obj_id"], {})
    name   = wo.get("name", step.get("label", "?"))
    ep_id  = wo.get("endpoint_id")
    ep     = idx["ep"].get(ep_id) if ep_id else None
    ep_str = f"  ({ep.get('name','')})" if ep else ""
    return f"WP {name}{ep_str}"


# ---------------------------------------------------------------------------
# Trace-regels voor NIET-patchpanel poorten (cascade inspringing)
# ---------------------------------------------------------------------------

def _trace_cascade(steps: list[dict], data: dict, idx: dict,
                   base_indent: str = "      ") -> list[str]:
    """
    Zet trace-stappen om naar ingesprongen regels (cascade).
    Eerste stap wordt overgeslagen (dat is de poort zelf).
    endpoint direct na wall_outlet wordt samengevoegd.
    """
    lines     = []
    indent    = base_indent
    skip_next = False

    for i, step in enumerate(steps):
        if skip_next:
            skip_next = False
            continue

        obj_type = step.get("obj_type", "")

        if obj_type == "port":
            lines.append(f"{indent}\u2500\u2500\u25ba  {_step_label_port(step, idx, data)}")

        elif obj_type == "wall_outlet":
            # Kijk of volgende stap endpoint is
            ep_str = ""
            if i + 1 < len(steps) and steps[i + 1]["obj_type"] == "endpoint":
                ep_name   = steps[i + 1].get("label", "")
                ep_str    = f"  ({ep_name})"
                skip_next = True
            wo   = idx["wo"].get(step["obj_id"], {})
            name = wo.get("name", step.get("label", "?"))
            lines.append(f"{indent}\u2500\u2500\u25ba  WP {name}{ep_str}")

        elif obj_type == "endpoint":
            lines.append(f"{indent}\u2500\u2500\u25ba  {step.get('label','?')}")

        indent = indent + "     "

    return lines


# ---------------------------------------------------------------------------
# Trace-regels voor PATCHPANEL poorten (twee platte pijlen)
# ---------------------------------------------------------------------------

def _trace_patchpanel(steps: list[dict], data: dict, idx: dict,
                      indent: str = "      ") -> list[str]:
    """
    Voor een patchpanel VOOR-poort:
        ──►  <externe VOOR-verbinding>       (switch / ander device)
        ──►  <externe ACHTER-verbinding>     (wandpunt + eindapparaat)

    Voor een patchpanel ACHTER-poort (rechtstreeks aangeklikt):
        ──►  <externe ACHTER-verbinding>     (wandpunt)
        ──►  <externe VOOR-verbinding>       (switch)

    Stappen uit trace_from_port voor PP VOOR:
        [0] PP VOOR   ← startpunt (overslaan, is de poort zelf)
        [1] PP ACHTER ← interne partner
        [2] wall_outlet / endpoint
        ...daarna externe VOOR-verbinding (switch) via stappen na [1]

    De externe VOOR-verbinding staat als laatste stap(pen) in de trace
    omdat tracing.py eerst de interne partner + diens connectie uitwerkt,
    en daarna de externe connectie van de startpoort volgt.
    """
    if not steps:
        return []

    # Splits de stappen in twee groepen:
    # groep A = externe connectie van de startpoort (port→port, bv. switch)
    # groep B = interne partner + diens externe connectie (pp_back→wo→ep)

    # Zoek de interne partner (eerste port-stap na index 0 met andere side)
    start_port  = steps[0]
    start_side  = start_port.get("side", "")

    # Groep B: stappen die beginnen bij de interne partner
    # Groep A: stappen die daarna komen (externe conn van de startpoort)
    # In de trace: [0]=start, [1]=intern partner, [2..n]=partner-extern,
    #              dan [n+1..]=start-extern (switch etc.)

    # Vind de splitspunten
    partner_idx = None
    for i, s in enumerate(steps[1:], 1):
        if s["obj_type"] == "port":
            port_obj = idx["port"].get(s["obj_id"], {})
            dev_obj  = idx["dev"].get(port_obj.get("device_id", ""), {})
            if _is_patchpanel(dev_obj) and s.get("side") != start_side:
                partner_idx = i
                break

    if partner_idx is None:
        # Geen interne partner gevonden — gewone cascade
        return _trace_cascade(steps[1:], data, idx, indent)

    # Stappen na de partner tot aan de volgende port-stap van een ander device
    # zijn de externe conn van de partner (wandpunt, endpoint)
    # Stappen na die groep zijn de externe conn van de startpoort (switch)

    # Bouw groep B (partner + diens extern)
    group_b = []
    group_a = []
    i = partner_idx + 1
    while i < len(steps):
        s = steps[i]
        if s["obj_type"] == "port":
            # Dit is het begin van de externe conn van de startpoort
            group_a = steps[i:]
            break
        group_b.append(s)
        i += 1

    lines = []

    # VOOR-poort: eerst externe VOOR-conn (switch), dan ACHTER-conn (wandpunt)
    # ACHTER-poort: eerst externe ACHTER-conn (wandpunt), dan VOOR-conn (switch)
    if start_side == "front":
        # Eerst switch (group_a), dan wandpunt (group_b)
        if group_a:
            lines.append(f"{indent}\u2500\u2500\u25ba  {_step_label_port(group_a[0], idx, data)}")
        if group_b:
            # group_b = [wall_outlet, (endpoint)]
            wo_step = group_b[0]
            if wo_step["obj_type"] == "wall_outlet":
                ep_str = ""
                if len(group_b) > 1 and group_b[1]["obj_type"] == "endpoint":
                    ep_str = f"  ({group_b[1].get('label','')})"
                wo   = idx["wo"].get(wo_step["obj_id"], {})
                name = wo.get("name", wo_step.get("label", "?"))
                lines.append(f"{indent}\u2500\u2500\u25ba  WP {name}{ep_str}")
    else:
        # ACHTER: eerst wandpunt (group_b), dan switch (group_a)
        if group_b:
            wo_step = group_b[0]
            if wo_step["obj_type"] == "wall_outlet":
                ep_str = ""
                if len(group_b) > 1 and group_b[1]["obj_type"] == "endpoint":
                    ep_str = f"  ({group_b[1].get('label','')})"
                wo   = idx["wo"].get(wo_step["obj_id"], {})
                name = wo.get("name", wo_step.get("label", "?"))
                lines.append(f"{indent}\u2500\u2500\u25ba  WP {name}{ep_str}")
        if group_a:
            lines.append(f"{indent}\u2500\u2500\u25ba  {_step_label_port(group_a[0], idx, data)}")

    return lines


# ---------------------------------------------------------------------------
# Render één rack
# ---------------------------------------------------------------------------

def _render_rack(data: dict, idx: dict,
                 site: dict, room: dict, rack: dict) -> list[str]:
    from app.services.tracing import trace_from_port

    lines: list[str] = []
    lines.append(f"## \U0001f5c4  {rack.get('name', '?')}")
    lines.append(f"*{site.get('name','?')}  \u203a  {room.get('name','?')}*")
    lines.append("")

    slots_sorted = sorted(rack.get("slots", []),
                          key=lambda s: s.get("u_start", 0))

    if not slots_sorted:
        lines.append("*Leeg rack*")
        lines.append("")
        return lines

    for slot in slots_sorted:
        dev_id = slot.get("device_id")
        if not dev_id:
            continue
        dev = idx["dev"].get(dev_id)
        if not dev:
            continue

        u_start  = slot.get("u_start", "?")
        height   = slot.get("height", 1)
        u_end    = (u_start + height - 1) if isinstance(u_start, int) else "?"
        u_label  = f"U{u_start}" if u_start == u_end else f"U{u_start}\u2013{u_end}"
        is_pp    = _is_patchpanel(dev)

        lines.append(f"### {dev.get('name','?')}")
        lines.append(f"*{dev.get('type','')}  \u00b7  {u_label}*")
        lines.append("")

        ports = [p for p in data.get("ports", []) if p.get("device_id") == dev_id]
        ports_front = sorted([p for p in ports if p.get("side") == "front"],
                             key=lambda p: p.get("number", 0))
        ports_back  = sorted([p for p in ports if p.get("side") == "back"],
                             key=lambda p: p.get("number", 0))

        for side_label, side_ports in [("VOOR", ports_front), ("ACHTER", ports_back)]:
            if not side_ports:
                continue

            lines.append(f"**{side_label}**")
            lines.append("")
            lines.append("```")

            max_pname = max(
                (len(p.get("name", f"P{p.get('number',0)}")) for p in side_ports),
                default=4
            )
            max_pname = max(max_pname, 4)

            for port in side_ports:
                p_name   = port.get("name", f"P{port.get('number', 0)}")
                p_num    = str(port.get("number", "")).rjust(2)
                p_col    = p_name.ljust(max_pname)
                vlan     = port.get("vlan")
                vlan_str = f"  [{_vlan_label(data, vlan)}]" if vlan else ""

                steps = trace_from_port(data, port["id"])

                if len(steps) <= 1:
                    lines.append(f"  {p_num}  {p_col}  (niet verbonden)")
                else:
                    lines.append(f"  {p_num}  {p_col}{vlan_str}")
                    if is_pp:
                        trace_lines = _trace_patchpanel(
                            steps, data, idx, indent="        "
                        )
                    else:
                        trace_lines = _trace_cascade(
                            steps[1:], data, idx, base_indent="        "
                        )
                    lines.extend(trace_lines)

                lines.append("")

            lines.append("```")
            lines.append("")

    return lines


# ---------------------------------------------------------------------------
# Wandpunt-sectie per site
# ---------------------------------------------------------------------------

def _render_outlets_site(data: dict, idx: dict, site: dict) -> list[str]:
    from app.services.tracing import trace_from_wall_outlet

    lines: list[str] = []
    lines.append(f"## \U0001f310  Wandpunten \u2014 {site.get('name','?')}")
    lines.append("")

    any_outlet = False
    for room in site.get("rooms", []):
        outlets = room.get("wall_outlets", [])
        if not outlets:
            continue

        lines.append(f"### {room.get('name','?')}")
        lines.append("")
        lines.append("```")

        for wo in sorted(outlets, key=lambda w: w.get("name", "")):
            wo_name = wo.get("name", wo["id"])
            ep_id   = wo.get("endpoint_id")
            ep      = idx["ep"].get(ep_id) if ep_id else None
            ep_str  = f"  ({ep.get('name','')})" if ep else ""

            lines.append(f"  WP {wo_name}{ep_str}")

            steps = trace_from_wall_outlet(data, wo["id"])
            # Zoek index na het wandpunt zelf
            start = 0
            for si, s in enumerate(steps):
                if s["obj_type"] == "wall_outlet" and s["obj_id"] == wo["id"]:
                    start = si + 1
                    break

            if start < len(steps):
                trace_rest = _trace_cascade(
                    steps[start:], data, idx, base_indent="       "
                )
                lines.extend(trace_rest)

            lines.append("")
            any_outlet = True

        lines.append("```")
        lines.append("")

    if not any_outlet:
        lines.append("*Geen wandpunten geconfigureerd.*")
        lines.append("")

    # 1.3.0 — Direct verbonden endpoints (port -> endpoint, binnen deze site)
    site_device_ids = {
        slot.get("device_id")
        for room in site.get("rooms", [])
        for rack in room.get("racks", [])
        for slot in rack.get("slots", [])
        if slot.get("device_id")
    }
    direct_conns = [
        c for c in data.get("connections", [])
        if c.get("to_type") == "endpoint" or c.get("from_type") == "endpoint"
    ]
    # Filter op verbindingen waarbij de poort tot deze site behoort
    site_direct = []
    for conn in direct_conns:
        if conn.get("to_type") == "endpoint":
            ep_id, port_id = conn["to_id"], conn["from_id"]
        else:
            ep_id, port_id = conn["from_id"], conn["to_id"]
        port = idx["port"].get(port_id, {})
        if port.get("device_id") not in site_device_ids:
            continue
        ep  = idx["ep"].get(ep_id)
        dev = idx["dev"].get(port.get("device_id", ""), {})
        if ep:
            site_direct.append((ep, dev, port, conn))

    if site_direct:
        lines.append("### 🖥 Direct verbonden")
        lines.append("")
        lines.append("| Naam | Type | Locatie | Poort | Kabeltype |")
        lines.append("|---|---|---|---|---|")
        for ep, dev, port, conn in sorted(site_direct, key=lambda x: x[0].get("name", "")):
            port_label = (f"{dev.get('name','?')} / {port.get('name','?')}"
                          if dev else port.get("name", "?"))
            lines.append(
                f"| {ep.get('name','?')} | {ep.get('type','—')} | "
                f"{ep.get('location','—')} | {port_label} | "
                f"{conn.get('cable_type','—')} |"
            )
        lines.append("")

    return lines


# ---------------------------------------------------------------------------
# Publieke render functies
# ---------------------------------------------------------------------------

def render_all(data: dict) -> str:
    idx   = _build_index(data)
    lines = _header(data, "Volledig overzicht \u2014 alle sites")

    for site in data.get("sites", []):
        lines.append(f"# \U0001f4cd  {site.get('name','?')}")
        lines.append("")
        for room in site.get("rooms", []):
            for rack in room.get("racks", []):
                lines += _render_rack(data, idx, site, room, rack)
        lines += _render_outlets_site(data, idx, site)
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def render_site(data: dict, site_id: str) -> str:
    idx  = _build_index(data)
    site = next((s for s in data.get("sites", []) if s["id"] == site_id), None)
    if not site:
        return f"# Site niet gevonden: {site_id}\n"

    lines = _header(data, f"Site: {site.get('name','?')}")
    lines.append(f"# \U0001f4cd  {site.get('name','?')}")
    lines.append("")

    for room in site.get("rooms", []):
        for rack in room.get("racks", []):
            lines += _render_rack(data, idx, site, room, rack)
    lines += _render_outlets_site(data, idx, site)
    return "\n".join(lines)


def render_rack_only(data: dict, rack_id: str) -> str:
    idx = _build_index(data)
    for site in data.get("sites", []):
        for room in site.get("rooms", []):
            for rack in room.get("racks", []):
                if rack["id"] == rack_id:
                    lines = _header(
                        data,
                        f"{site.get('name','?')} \u203a {room.get('name','?')} \u203a {rack.get('name','?')}"
                    )
                    lines += _render_rack(data, idx, site, room, rack)
                    return "\n".join(lines)
    return f"# Rack niet gevonden: {rack_id}\n"


# ---------------------------------------------------------------------------
# Hoofd export functie
# ---------------------------------------------------------------------------

def export_md(
    data: dict,
    filepath: str,
    scope: str = "all",
    site_id: str = "",
    rack_id: str = "",
) -> tuple[bool, str]:
    try:
        if scope == "rack":
            content = render_rack_only(data, rack_id)
        elif scope == "site":
            content = render_site(data, site_id)
        else:
            content = render_all(data)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True, ""
    except Exception:
        import traceback
        return False, traceback.format_exc()


# ---------------------------------------------------------------------------
# Intern — documentheader
# ---------------------------------------------------------------------------

def _header(data: dict, subtitle: str) -> list[str]:
    datum  = datetime.date.today().strftime("%d/%m/%Y")
    try:
        from app import version as _ver
        ver = _ver.__version__
    except Exception:
        ver = "\u2014"

    sites  = data.get("sites", [])
    n_rack = sum(len(r.get("racks", [])) for s in sites for r in s.get("rooms", []))
    n_dev  = len(data.get("devices", []))
    n_conn = len(data.get("connections", []))
    n_wo   = sum(len(r.get("wall_outlets", [])) for s in sites for r in s.get("rooms", []))

    return [
        "# Networkmap Creator \u2014 Rack Export",
        "",
        f"**{subtitle}**  \u00b7  gegenereerd op {datum}  \u00b7  versie {ver}",
        "",
        f"*{n_rack} rack(s)  \u00b7  {n_dev} device(s)  \u00b7  {n_conn} verbinding(en)  \u00b7  {n_wo} wandpunt(en)*",
        "",
        "---",
        "",
    ]