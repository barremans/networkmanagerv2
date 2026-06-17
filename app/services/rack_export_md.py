# =============================================================================
# Networkmap_Creator
# File:    app/services/rack_export_md.py
# Role:    Praktische rack-export naar Markdown — interventiedocumentatie
# Version: 2.9.5
# Author:  Barremans
# Changes: 2.9.5 — Subkoppen switches/patchpanels meeschuiven met heading_level:
#                  {h}# ipv ### voor switch- en patchpanel-namen in §6, §6b, §7.
#                  Volledige heading-hiërarchie correct voor alle scopes:
#                  standalone: ##/### | all+company: ####/#####
#          2.9.4 — h-parameter alle _section_*() functies
#                  Alle _section_*() functies krijgen h="##" parameter.
#                  _build_rackfiche berekent sh (section heading) op basis van
#                  heading_level: "#"→"##", "##"→"###", "###"→"####".
#                  Sectieheadings (1. Identificatie t/m 10. Controlelog)
#                  volgen automatisch het juiste niveau mee.
#          2.9.3 — heading_level parameter _build_rackfiche; aandachtspunten sortering
#                  _build_rackfiche() heading_level parameter (default "#").
#                  render_all + render_company: heading_level="###" zodat
#                  rackfiches correct genest zijn onder # 🏢 / ## 📍.
#                  Aandachtspunten all-scope: bedrijven gesorteerd op
#                  aflopend aantal hoog-items (meeste problemen eerst).
#          2.9.2 — All-scope index/aandachtspunten/rackfiches per bedrijf gegroepeerd
#                  (### 🏢 bedrijfsnaam boven elke groep).
#                  Rackfiches render_all: # 🏢 bedrijf → ## 📍 site hiërarchie.
#                  render_company: site-header ## 📍 (consistent met render_all).
#                  render_tracing_all: # 🏢 bedrijfscheiding toegevoegd.
#                  Aandachtspunten all-scope gesorteerd op bedrijf › ernst › rack.
#                  _global_header: "Bedrijven: N" rij bij meerdere bedrijven.
#          2.9.1 — Bugfix F4: _global_index + _global_attention_summary scoped_sites
#                  render_company(), render_tracing_company() toegevoegd
#                  _global_header: company_name parameter voor bedrijfsnaam in header
#                  get_all_companies geïmporteerd
#                  export_md: scope "company" + company_id doorgeven
#          2.8.0 -- F1: get_all_sites() voor v2 JSON
#          2.7.0 — Rackstatus: att_points is not None fix (lege lijst gaf NIET DEFINITIEF)
#                  Switchlink-telling: zelfde filter als uplink-tabel (beide richtingen)
#                  Summary labels: "Switchlinks (zie tabel §5)" met extern/intern/via-PP
#          2.6.0 — Globale validatiestatus: berekend uit alle rack-aandachtspunten (consistent met header)
#                  Rackstatus GEVALIDEERD voor racks zonder issues (niet meer NIET DEFINITIEF)
#                  Redundantiegroep-info: alleen in racks waar de devices fysiek staan
#                  Switchlink-telling: extern/intern/via-patchpanel apart, consistent met tabel
#                  Rack-layout: top-down gesorteerd op echte U-positie
#          2.5.0 — Rackstatus: apart van globale status (Globale validatiestatus / Rackstatus)
#                  Dubbele eindapparaten in tracing opgelost
#                  SWITCH 9.x stack-waarschuwing als Middel aandachtspunt per rack
#                  Uplink-telling: extern/intern gesplitst
#                  PP SWITCHLINK-logica verbeterd
#                  Tracing-only export: render_tracing_all/site/rack
#                  export_md: tracing_only optie in options-dict
#          2.4.0 — _build_trace: centrale tracing vervat alle stappen (PP(F)/PP(B)/WP/EP)
#                  _trace_to_cascade: cascade-blok hergebruikt _build_trace (geen dubbele lookup)
#                  _section_switch_ports: gebruikt _build_trace, Via achterkant = PP(B)
#                  _section_switch_cascade: gebruikt _build_trace + _trace_to_cascade
#                  _section_patchpanels: gebruikt _build_trace, status SWITCHLINK vs OK/geen EP
#                  _section_identification: rackstatus berekend op att_points van het rack
#                  SWITCHLINK onderscheiden van UPLINK (patchpanel tussen actieve devices)
#          2.3.0 — Validatiestatus: nooit GEVALIDEERD bij open aandachtspunten
#                  Cascade-tracing herschreven: switch→PP(F)→PP(B)→WP→EP (correcte volgorde)
#                  Risico-WP in patchpanelmatrix: ⚠️ geen EP i.p.v. ✅ OK
#                  Eindpunt kolom: wandpuntnaam nooit als eindapparaat
#                  Switchpoort kolommen: Directe verbinding / Via achterkant / Wandpunt / Eindapparaat
#                  Uplinks hernoemd naar Switchlinks voor duidelijkheid
#                  Index: aandachtspunten uniform 🔴/🟠/🟡 per ernst
#          2.2.0 — Patchpanel VOOR/F gecorrigeerd: front=switch, back=wandpunt (geverifieerd via trace-labels)
#                  U-posities hersteld: total_u - u_start + 1 (identiek aan Word)
#                  Validatiestatus dynamisch: NIET DEFINITIEF bij high-priority issues
#                  Redundantiegroep: #=bevestigd (ℹ️), .=onbevestigd (⚠️)
#                  Detailniveaus: kort/technisch/volledig correct gescheiden
#                  Volledig: cascade-tracing als extra sectie 6b
#          2.1.0 — Patchpanel VOOR/ACHTER gecorrigeerd (data: back=switch=VOOR/F, front=wandpunt=ACHTER/B)
#                  U-posities: directe u_start uit data (niet omgekeerd berekend)
#                  Scope-tellingen: header berekent per site/rack/all
#          2.0.0 — Volledige herwerking naar rackfiche-formaat
#                  Structuur per rack: identificatie, samenvatting, U-layout,
#                  actieve devices, uplinks, switchpoorten, patchpanels,
#                  wandpunten/eindapparaten, aandachtspunten, controlelog
#                  Markdown-tabellen i.p.v. codeblokken
#                  Statuscodes: OK / FREE / WARN / UPLINK / PATCHED / WP / EP
#                  SFP/UTP waarschuwingen, redundantiegroepen (#- en .-patroon)
#                  Options-dict voor detailniveau en sectieselectie
#          1.3.0 — Direct endpoint: _conn_dest() herkent to_type=="endpoint"
#          1.2.0 — Patchpanel weergave herschreven
#          1.1.0 — Volledige tracing via tracing.py
#          1.0.0 — E2: initiële versie
# =============================================================================

from __future__ import annotations
import re
import datetime
from collections import defaultdict
from app.helpers.settings_storage import get_all_sites, get_all_companies


# =============================================================================
# CONSTANTEN
# =============================================================================

_TYPE_MAP: dict[str, str] = {
    "switch":           "Switch",
    "patch_panel":      "Patchpanel",
    "patchpanel":       "Patchpanel",
    "cable_management": "Kabelgoot",
    "server":           "Server",
    "router":           "Router",
    "firewall":         "Firewall",
    "ups":              "UPS",
    "nuc":              "NUC / Mini-PC",
    "nuc1":             "NUC / Mini-PC",
    "access_point":     "AP",
    "ap":               "AP",
    "media_converter":  "Mediaconverter",
    "media_conv":       "Mediaconverter",
    "fiber_converter":  "Fiber",
    "fiber":            "Fiber",
    "mediaconverter":   "Mediaconverter",
    "nvr":              "NVR",
    "smartlogger":      "Smartlogger",
    "pc":               "PC",
    "laptop":           "Laptop",
    "sonos":            "Sonos",
    "sonos_server":     "Sonos",
    "gyron":            "Toegangscontroller",
    "distribution_plug":"Verdeelstekker",
    "other":            "Ander",
    "ander":            "Ander",
    "verdeelstekker":   "Verdeelstekker",
}

_EP_TYPE_MAP: dict[str, str] = {
    "pc":               "PC",
    "laptop":           "Laptop",
    "all_in_one":       "All-in-One",
    "access_point":     "Access Point",
    "printer":          "Printer",
    "plotter":          "Plotter",
    "ip_phone":         "IP Telefoon",
    "phone":            "Telefoon",
    "ip_camera":        "IP Camera",
    "camera":           "IP Camera",
    "conference_devices":"Vergaderapparaat",
    "docking_station":  "Docking Station",
    "nvr":              "NVR",
    "server":           "Server",
    "switch":           "Switch",
    "ot_machine":       "OT Machine",
    "ot":               "OT Apparaat",
    "smartlogger":      "Smartlogger",
    "ups":              "UPS",
    "dali":             "DALI Controller",
    "nuc":              "NUC / Mini-PC",
    "sonos":            "Sonos",
    "display":          "Display",
    "other":            "Ander",
}

_CABLE_LABELS: dict[str, str] = {
    "utp_cat5e": "UTP Cat5e",
    "utp_cat6":  "UTP Cat6",
    "utp_cat6a": "UTP Cat6a",
    "sfp_fiber": "SFP Fiber",
    "sfp_dac":   "SFP DAC",
    "other":     "Anders",
}

_DEFAULT_OPTIONS: dict = {
    "include_free_ports":       True,
    "include_patchpanels":      True,
    "include_switches":         True,
    "include_attention_points": True,
    "include_control_log":      True,
    "detail_level":             "technical",  # "short" | "technical" | "full"
}


# =============================================================================
# DATA HELPERS — gedeeld met report_generator logica
# =============================================================================

def _normalize_mac(mac: str) -> str:
    if not mac:
        return "—"
    clean = re.sub(r"[^0-9a-fA-F]", "", mac)
    if len(clean) == 12:
        return ":".join(clean[i:i+2].upper() for i in range(0, 12, 2))
    return mac.upper()


def _normalize_ip(ip: str) -> str:
    if not ip:
        return "—"
    ip = ip.strip()
    ip = re.sub(r"^https?://", "", ip).rstrip("/")
    m = re.search(r"\d+\.\d+\.\d+\.\d+", ip)
    return m.group() if m else ip or "—"


def _stack_group(name: str) -> str:
    """
    Leid redundantiegroepsnaam af:
      SW01#1 / SW01#2  →  'SW01'
      SWITCH 9.1 / 9.2 →  'SWITCH 9'
    """
    if "#" in name:
        return name.split("#")[0].strip()
    m = re.match(r'^(.+?)\.(\d+)$', name)
    if m:
        prefix = m.group(1).strip()
        if re.search(r'[^0-9.]', prefix):
            return prefix
    return name


def _type_label(dev: dict) -> str:
    return _TYPE_MAP.get(dev.get("type", ""), dev.get("type", "") or "—")


def _is_switch(dev: dict) -> bool:
    return dev.get("type") == "switch"


def _is_patchpanel(dev: dict) -> bool:
    return dev.get("type") in ("patch_panel", "patchpanel")


def _is_active(dev: dict) -> bool:
    return dev.get("type") in (
        "switch", "router", "firewall", "server", "ups",
        "nuc", "nuc1", "access_point", "ap", "media_converter",
        "media_conv", "fiber_converter", "fiber", "mediaconverter",
        "nvr", "smartlogger", "sonos", "sonos_server", "gyron",
    )


def _cable_label(cable_type: str) -> str:
    return _CABLE_LABELS.get(cable_type or "", cable_type or "—")


def _vlan_display(vlan, port_type: str = "") -> str:
    """
    Geeft leesbare VLAN-waarde. Patchpanels krijgen 'n.v.t.', lege waarden
    krijgen 'onbekend'.
    """
    if port_type in ("patch_panel", "patchpanel", "cable_management"):
        return "n.v.t."
    if not vlan:
        return "onbekend"
    return str(vlan)


def _safe_filename(text: str) -> str:
    text = re.sub(r"[/\\]", "_", text)
    text = re.sub(r"[^a-zA-Z0-9_\-]", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


# =============================================================================
# INDEX BUILDER
# =============================================================================

def _build_index(data: dict) -> dict:
    idx: dict = {
        "dev":     {d["id"]: d for d in data.get("devices", [])},
        "port":    {p["id"]: p for p in data.get("ports", [])},
        "ep":      {e["id"]: e for e in data.get("endpoints", [])},
        "wo":      {},
        "wo_room": {},   # wo_id → (site, room)
        "loc":     {},   # dev_id → {site, room, rack, slot, total_u}
    }
    for site in get_all_sites(data):
        for room in site.get("rooms", []):
            for wo in room.get("wall_outlets", []):
                idx["wo"][wo["id"]]      = wo
                idx["wo_room"][wo["id"]] = (site, room)
            for rack in room.get("racks", []):
                total_u = rack.get("total_units", 42)
                for slot in rack.get("slots", []):
                    dev_id = slot.get("device_id")
                    if dev_id:
                        u_start  = slot.get("u_start")
                        height   = slot.get("height", 1)
                        slot_lbl = str(u_start) if u_start is not None else "?"
                        idx["loc"][dev_id] = {
                            "site":    site["name"],
                            "room":    room["name"],
                            "rack":    rack["name"],
                            "slot":    slot_lbl,
                            "u_start": u_start,
                            "height":  height,
                            "total_u": total_u,
                        }
    return idx


# =============================================================================
# VERBINDINGSTRACING (standalone, geen afhankelijkheid van tracing.py)
# =============================================================================

def _connected_to(data: dict, port_id: str) -> dict | None:
    """Geeft de verbinding terug waarbij port_id betrokken is (eerste match)."""
    for conn in data.get("connections", []):
        if conn.get("from_id") == port_id or conn.get("to_id") == port_id:
            return conn
    return None


# Nieuwe centrale tracing-logica
# Vervangt _trace_port, _build_cascade_lines, _section_switch_cascade

_TRACE_FIELDS = [
    "pp_front",       # label PP(F)-poort of "" 
    "pp_front_id",    # port-id PP(F)
    "pp_back",        # label PP(B)-poort of ""
    "pp_back_id",     # port-id PP(B)
    "wallpoint",      # naam wandpunt of ""
    "wallpoint_id",
    "endpoint",       # naam eindapparaat of ""
    "endpoint_id",
    "direct_target",  # label direct verbonden object (PP(F) of switch of WP)
    "direct_is_pp",   # True als direct verbonden met patchpanel
    "direct_is_switch",
    "other_active",   # True als via-achterkant naar actief device gaat
    "status",         # FREE/OK/WARN/UPLINK/SWITCHLINK/PATCHED/WP/EP
    "warnings",
    "cable_type",
]


def _bt_empty() -> dict:
    return {k: "" for k in _TRACE_FIELDS} | {
        "direct_is_pp": False, "direct_is_switch": False,
        "other_active": False, "status": "FREE",
        "warnings": [], "cable_type": "—",
    }


def _build_trace(data: dict, idx: dict, port_id: str) -> dict:
    """
    Centrale tracing-functie. Geeft één dict terug met alle stappen.
    Wordt hergebruikt door switchpoorttabel, patchpanelmatrix en cascadeblok.

    Volgorde:
      switch-poort → PP(F) → PP(B) → wandpunt/eindapparaat
                  of → actieve switch (UPLINK/SWITCHLINK)
                  of → direct wandpunt/eindapparaat

    direct_target = eerste fysieke verbinding vanuit de poort
    pp_front      = PP(F) label als eerste stap patchpanel is
    pp_back       = PP(B) label (partner van pp_front)
    wallpoint     = wandpunt aan het einde van de keten
    endpoint      = eindapparaat (nooit een wandpuntnaam)
    """
    t = _bt_empty()
    conn = _connected_to(data, port_id)
    if not conn:
        return t  # FREE

    # SFP/UTP check
    port_obj = idx["port"].get(port_id, {})
    cable_type  = conn.get("cable_type", "")
    cable_label = _cable_label(cable_type)
    t["cable_type"] = cable_label
    if "SFP" in (port_obj.get("name", "") or "").upper():
        if any(kw in (cable_type or "").upper() for kw in ("UTP", "CAT")):
            t["warnings"].append(f"SFP-poort met {cable_label} — controleer kabeltype")

    # Bepaal het andere uiteinde van de eerste verbinding
    if conn.get("from_id") == port_id:
        other_id, other_type = conn.get("to_id"), conn.get("to_type", "port")
    else:
        other_id, other_type = conn.get("from_id"), conn.get("from_type", "port")

    # --- Direct naar wandpunt ---
    if other_type == "wall_outlet":
        wo  = idx["wo"].get(other_id, {})
        ep  = idx["ep"].get(wo.get("endpoint_id", "")) if wo.get("endpoint_id") else None
        ep_name = ep.get("name", "") if ep else ""
        t["direct_target"]  = f"WP {wo.get('name', other_id)}"
        t["wallpoint"]      = wo.get("name", other_id)
        t["wallpoint_id"]   = other_id
        t["endpoint"]       = ep_name if ep_name and not ep_name.upper().startswith("WP") else ""
        t["endpoint_id"]    = wo.get("endpoint_id", "")
        t["status"] = "OK" if t["endpoint"] else "WP"
        return t

    # --- Direct naar eindapparaat ---
    if other_type == "endpoint":
        ep = idx["ep"].get(other_id, {})
        ep_name = ep.get("name", other_id)
        t["direct_target"] = ep_name
        t["endpoint"]      = ep_name if not ep_name.upper().startswith("WP") else ""
        t["endpoint_id"]   = other_id
        t["status"]        = "EP"
        return t

    # --- Naar een andere poort ---
    if other_type not in ("port", None, ""):
        t["status"] = "WARN"
        return t

    other_port = idx["port"].get(other_id, {})
    if not other_port:
        t["status"] = "WARN"
        return t

    other_dev  = idx["dev"].get(other_port.get("device_id", ""), {})
    other_name = other_dev.get("name", "?")
    port_name  = other_port.get("name", "?")
    side_lbl   = "(F)" if other_port.get("side") == "front" else "(B)"
    target_lbl = f"{other_name} / {port_name} {side_lbl}"
    t["direct_target"] = target_lbl

    # --- Direct naar actieve switch (UPLINK of SWITCHLINK) ---
    if _is_switch(other_dev):
        t["direct_is_switch"] = True
        t["status"] = "UPLINK"
        return t

    # --- Naar patchpanel ---
    if _is_patchpanel(other_dev):
        t["direct_is_pp"] = True
        t["pp_front"]     = target_lbl
        t["pp_front_id"]  = other_id

        # Zoek PP(B): partner-poort (andere zijde, zelfde nummer)
        other_number = other_port.get("number")
        other_side   = other_port.get("side")
        partner_side = "back" if other_side == "front" else "front"
        partner_port = next(
            (p for p in data.get("ports", [])
             if p.get("device_id") == other_dev.get("id")
             and p.get("side") == partner_side
             and p.get("number") == other_number),
            None,
        )
        if partner_port:
            ps = "(B)" if partner_side == "back" else "(F)"
            t["pp_back"]   = f"{other_name} / {partner_port.get('name', '?')} {ps}"
            t["pp_back_id"] = partner_port["id"]

            # Volg PP(B) naar eindbestemming
            b_conn = _connected_to(data, partner_port["id"])
            if b_conn:
                if b_conn.get("from_id") == partner_port["id"]:
                    b_other_id, b_other_type = b_conn.get("to_id"), b_conn.get("to_type", "port")
                else:
                    b_other_id, b_other_type = b_conn.get("from_id"), b_conn.get("from_type", "port")

                if b_other_type == "wall_outlet":
                    wo  = idx["wo"].get(b_other_id, {})
                    ep  = idx["ep"].get(wo.get("endpoint_id", "")) if wo.get("endpoint_id") else None
                    ep_name = ep.get("name", "") if ep else ""
                    t["wallpoint"]   = wo.get("name", b_other_id)
                    t["wallpoint_id"] = b_other_id
                    t["endpoint"]    = ep_name if ep_name and not ep_name.upper().startswith("WP") else ""
                    t["endpoint_id"] = wo.get("endpoint_id", "")
                    t["status"] = "OK" if t["endpoint"] else "WP"

                elif b_other_type == "endpoint":
                    ep = idx["ep"].get(b_other_id, {})
                    ep_name = ep.get("name", b_other_id)
                    t["endpoint"]   = ep_name if not ep_name.upper().startswith("WP") else ""
                    t["endpoint_id"] = b_other_id
                    t["status"] = "EP"

                elif b_other_type in ("port", None, ""):
                    b_port = idx["port"].get(b_other_id, {})
                    b_dev  = idx["dev"].get(b_port.get("device_id", ""), {})
                    b_side = "(F)" if b_port.get("side") == "front" else "(B)"
                    b_lbl  = f"{b_dev.get('name','?')} / {b_port.get('name','?')} {b_side}"
                    if _is_switch(b_dev) or _is_active(b_dev):
                        t["other_active"] = True
                        t["status"]       = "SWITCHLINK"
                        t["endpoint"]     = b_lbl  # bewaar als eindbestemming
                        t["direct_target"] = b_lbl
                    else:
                        t["status"] = "PATCHED"
            else:
                # PP(B) heeft geen verbinding
                t["status"] = "PATCHED"
        else:
            # Geen partner gevonden
            t["status"] = "PATCHED"

        return t

    # --- Naar ander actief device (niet switch, niet PP) ---
    if _is_active(other_dev):
        t["status"] = "OK"
        return t

    t["status"] = "WARN"
    t["warnings"].append("Onbekend verbindingstype")
    return t


def _trace_status_label(t: dict) -> str:
    """Geeft het status-icoon + label voor een trace."""
    s = t.get("status", "FREE")
    return {
        "FREE":       "⬜ FREE",
        "OK":         "✅ OK",
        "WP":         "⚠️ geen EP",
        "EP":         "✅ OK",
        "UPLINK":     "🔁 UPLINK",
        "SWITCHLINK": "🔁 SWITCHLINK via patchpanel",
        "PATCHED":    "🔗 PATCHED",
        "WARN":       "⚠️ WARN",
    }.get(s, "❔")


def _trace_to_cascade(pname: str, t: dict, indent: str = "  ") -> list[str]:
    """
    Zet een trace om naar cascade-tekstregels.
    Volgorde: switch-poort → PP(F) → PP(B) → WP → eindapparaat
    """
    if t["status"] == "FREE":
        return [f"{indent}{pname:<14}  (vrij)"]

    lines = [f"{indent}{pname}"]
    i1 = indent + "        "
    i2 = indent + "              "
    i3 = indent + "                    "

    if t["pp_front"]:
        lines.append(f"{i1}──►  {t['pp_front']}")
    if t["pp_back"]:
        lines.append(f"{i2}──►  {t['pp_back']}")
    if t["wallpoint"]:
        lines.append(f"{i3}──►  WP {t['wallpoint']}")
        if t["endpoint"]:
            lines.append(f"{i3}      ──►  {t['endpoint']}")
    elif not t["pp_front"] and t["direct_target"]:
        # Direct (geen PP): toon direct_target
        lines.append(f"{i1}──►  {t['direct_target']}")
        # Eindapparaat alleen tonen als het verschilt van direct_target
        if t["endpoint"] and t["endpoint"] != t["direct_target"]:
            lines.append(f"{i2}──►  {t['endpoint']}")
    elif t["pp_front"] and not t["wallpoint"] and t["status"] == "SWITCHLINK":
        # Switch via patchpanel
        lines.append(f"{i3}──►  {t['direct_target']}")

    for w in t.get("warnings", []):
        lines.append(f"{i1}⚠️  {w}")
    return lines


def _status_icon(status: str) -> str:
    return {
        "OK":      "✅",
        "FREE":    "⬜",
        "WARN":    "⚠️",
        "UPLINK":  "🔁",
        "PATCHED": "🔗",
        "WP":      "🌐",
        "EP":      "💻",
        "UNKNOWN": "❔",
    }.get(status, "❔")


# =============================================================================
# MARKDOWN TABEL HELPER
# =============================================================================

def _md_table(headers: list[str], rows: list[list[str]],
               alignments: list[str] | None = None) -> list[str]:
    """
    Bouw een Markdown-tabel. alignments: lijst van 'l', 'r', 'c' per kolom.
    Lege rows geeft lege tabel terug (alleen header).
    """
    if not headers:
        return []
    n = len(headers)
    if alignments is None:
        alignments = ["l"] * n

    def align_sep(a: str) -> str:
        return {"r": "---:", "c": ":---:", "l": "---"}.get(a, "---")

    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(align_sep(a) for a in alignments) + " |")
    for row in rows:
        # Zorg dat elk veld str is en pipes escaped
        cells = [str(c).replace("|", "\\|") if c is not None else "—" for c in row]
        # Pad tot juiste breedte
        while len(cells) < n:
            cells.append("—")
        lines.append("| " + " | ".join(cells) + " |")
    return lines


# =============================================================================
# VALIDATIE HELPERS (rack-gefilterd)
# =============================================================================

def _build_duplicate_ip_set(data: dict) -> set:
    ip_to_groups: dict = defaultdict(set)
    for dv in data.get("devices", []):
        ip = _normalize_ip(dv.get("ip", ""))
        if not ip or ip == "—":
            continue
        ip_to_groups[ip].add(_stack_group(dv.get("name", "")))
    return {ip for ip, groups in ip_to_groups.items() if len(groups) > 1}


def _build_wo_connection_map(data: dict) -> dict:
    """wo_id → (port, dev) voor verbonden wandpunten."""
    port_idx = {p["id"]: p for p in data.get("ports", [])}
    dev_idx  = {d["id"]: d for d in data.get("devices", [])}
    result   = {}
    for conn in data.get("connections", []):
        for side, other in (("from", "to"), ("to", "from")):
            if conn.get(f"{side}_type") == "wall_outlet":
                wo_id    = conn.get(f"{side}_id")
                other_id = conn.get(f"{other}_id")
                ot       = conn.get(f"{other}_type", "port")
                if other_id and ot in ("port", None, ""):
                    p   = port_idx.get(other_id)
                    dev = dev_idx.get(p["device_id"]) if p else None
                    result[wo_id] = (p, dev)
    return result


def _rack_attention_points(data: dict, idx: dict,
                            rack: dict, site: dict, room: dict,
                            dup_ips: set) -> list[dict]:
    """
    Verzamel aandachtspunten gefilterd op dit rack.
    Elk punt: {ernst, type, object, detail, actie}
    """
    rack_dev_ids = {
        slot.get("device_id")
        for slot in rack.get("slots", [])
        if slot.get("device_id")
    }
    rack_wo_ids = {
        wo["id"]
        for room_ in site.get("rooms", [])
        for wo in room_.get("wall_outlets", [])
    }
    wo_conn_map = _build_wo_connection_map(data)
    points = []

    # Risico-wandpunten: verbonden maar geen eindapparaat, poort in dit rack
    for wo_id, (port, dev) in wo_conn_map.items():
        if not dev or dev.get("id") not in rack_dev_ids:
            continue
        wo = idx["wo"].get(wo_id, {})
        if not wo.get("endpoint_id"):
            points.append({
                "ernst":  "Hoog",
                "type":   "Risico-WP",
                "object": f"WP {wo.get('name', wo_id)}",
                "detail": "Verbonden aan netwerk zonder geregistreerd eindapparaat",
                "actie":  "Fysiek controleren en eindapparaat registreren of poort blokkeren",
            })

    # Dubbele IP in dit rack (echte conflicten)
    for slot in rack.get("slots", []):
        dev = idx["dev"].get(slot.get("device_id", ""), {})
        if not dev:
            continue
        ip = _normalize_ip(dev.get("ip", ""))
        if ip in dup_ips:
            points.append({
                "ernst":  "Hoog",
                "type":   "Dubbel IP",
                "object": dev.get("name", "?"),
                "detail": f"IP {ip} gedeeld met ander device (geen bevestigde stack)",
                "actie":  "IP-conflict controleren en corrigeren",
            })

    # Switchpoorten zonder VLAN
    for slot in rack.get("slots", []):
        dev = idx["dev"].get(slot.get("device_id", ""), {})
        if not dev or not _is_switch(dev):
            continue
        ports_no_vlan = [
            p for p in data.get("ports", [])
            if p.get("device_id") == dev["id"]
            and p.get("side") == "front"
            and not p.get("vlan")
            and _connected_to(data, p["id"])  # alleen verbonden poorten
        ]
        if ports_no_vlan:
            points.append({
                "ernst":  "Middel",
                "type":   "VLAN ontbreekt",
                "object": dev.get("name", "?"),
                "detail": f"{len(ports_no_vlan)} verbonden switchpoort(en) zonder VLAN-info",
                "actie":  "VLAN-informatie aanvullen per poort",
            })

    # SFP/UTP uplinks in dit rack
    switch_ids = {
        slot.get("device_id")
        for slot in rack.get("slots", [])
        if idx["dev"].get(slot.get("device_id", ""), {}).get("type") == "switch"
    }
    for conn in data.get("connections", []):
        fp = idx["port"].get(conn.get("from_id", ""), {})
        tp = idx["port"].get(conn.get("to_id", ""), {})
        if not fp or not tp:
            continue
        cable = conn.get("cable_type", "") or ""
        if ("SFP" in (fp.get("name", "") + tp.get("name", "")).upper()
                and any(kw in cable.upper() for kw in ("UTP", "CAT"))
                and (fp.get("device_id") in switch_ids or tp.get("device_id") in switch_ids)):
            fd = idx["dev"].get(fp.get("device_id", ""), {})
            td = idx["dev"].get(tp.get("device_id", ""), {})
            points.append({
                "ernst":  "Middel",
                "type":   "SFP/UTP",
                "object": f"{fd.get('name','?')}/{fp.get('name','?')} → {td.get('name','?')}/{tp.get('name','?')}",
                "detail": f"SFP-poort met kabeltype {_cable_label(cable)}",
                "actie":  "Kabeltype controleren: fiber, DAC of koper-SFP",
            })

    # Devices zonder merk/model
    for slot in rack.get("slots", []):
        dev = idx["dev"].get(slot.get("device_id", ""), {})
        if not dev or not _is_switch(dev):
            continue
        if not dev.get("brand") and not dev.get("model"):
            points.append({
                "ernst":  "Laag",
                "type":   "Geen merk/model",
                "object": dev.get("name", "?"),
                "detail": "Switch zonder merk en model in inventaris",
                "actie":  "Merk en model aanvullen",
            })

    # Niet-genormaliseerde MACs
    for slot in rack.get("slots", []):
        dev = idx["dev"].get(slot.get("device_id", ""), {})
        if not dev:
            continue
        mac = dev.get("mac", "")
        if mac and ":" not in mac and "-" not in mac:
            points.append({
                "ernst":  "Laag",
                "type":   "MAC brondata",
                "object": dev.get("name", "?"),
                "detail": f"MAC '{mac}' niet genormaliseerd in brondata",
                "actie":  "Brondata aanpassen naar AA:BB:CC:DD:EE:FF",
            })

    # Mogelijke stack/cluster (dot-patroon, niet bevestigd)
    import re as _re_att
    from collections import defaultdict as _dd_att
    _ip_dot: dict = _dd_att(list)
    for slot in rack.get("slots", []):
        dev = idx["dev"].get(slot.get("device_id", ""), {})
        if not dev:
            continue
        ip   = _normalize_ip(dev.get("ip", ""))
        name = dev.get("name", "")
        if ip and ip != "—" and "#" not in name:
            m = _re_att.match(r'^(.+?)\.(\d+)$', name)
            if m and _re_att.search(r'[^0-9.]', m.group(1)):
                _ip_dot[(ip, m.group(1).strip())].append(name)
    for (ip, grp), names in _ip_dot.items():
        if len(names) > 1:
            points.append({
                "ernst":  "Middel",
                "type":   "Mogelijke stack/cluster",
                "object": ", ".join(sorted(names)),
                "detail": f"Delen IP {ip} — niet bevestigd als redundantiegroep",
                "actie":  "Bevestig stack/cluster of corrigeer IP-conflict",
            })

    return points


# =============================================================================
# REDUNDANTIEGROEP INFO
# =============================================================================

def _stack_info_lines(data: dict) -> list[str]:
    """
    Redundantiegroepen:
      #-patroon (SW01#1 / SW01#2)  = bevestigde redundantiegroep → ℹ️ info
      .-patroon (SWITCH 9.1 / 9.2) = mogelijk stack/cluster → ⚠️ waarschuwing
    """
    from collections import defaultdict
    # Splits per patrontype
    hash_groups: dict = defaultdict(list)   # bevestigd
    dot_groups:  dict = defaultdict(list)   # onbevestigd
    for dv in data.get("devices", []):
        ip   = _normalize_ip(dv.get("ip", ""))
        name = dv.get("name", "")
        if not ip or ip == "—":
            continue
        if "#" in name:
            grp = name.split("#")[0].strip()
            hash_groups[(ip, grp)].append(name)
        else:
            import re as _re2
            m = _re2.match(r'^(.+?)\\.(\\d+)$', name)
            if m and _re2.search(r'[^0-9.]', m.group(1)):
                grp = m.group(1).strip()
                dot_groups[(ip, grp)].append(name)
    lines = []
    for (ip, grp), names in hash_groups.items():
        if len(names) > 1:
            lines.append(
                f"> ℹ️  {' en '.join(sorted(names))} vormen een bevestigde "
                f"redundantiegroep met gedeeld management-IP {ip}."
            )
    for (ip, grp), names in dot_groups.items():
        if len(names) > 1:
            lines.append(
                f"> ⚠️  {', '.join(sorted(names))} delen IP {ip}. "
                f"Bevestig of dit een stack/cluster is of corrigeer als IP-conflict."
            )
    return lines


# =============================================================================
# RACK SECTIE BUILDERS
# =============================================================================


def _stack_info_lines_for_rack(data: dict, rack_dev_ids: set, idx: dict) -> list[str]:
    """
    Redundantiegroep-info beperkt tot devices in dit rack.
    #-patroon in rack → bevestigde groep.
    Uplink-relatie naar groep elders → kortere tekst.
    Dot-patroon → waarschuwing (wordt al als aandachtspunt getoond).
    """
    from collections import defaultdict
    hash_groups: dict = defaultdict(list)
    for dev_id in rack_dev_ids:
        dv   = idx["dev"].get(dev_id, {})
        ip   = _normalize_ip(dv.get("ip", ""))
        name = dv.get("name", "")
        if not ip or ip == "—" or "#" not in name:
            continue
        grp = name.split("#")[0].strip()
        hash_groups[(ip, grp)].append(name)

    lines = []
    for (ip, grp), names in hash_groups.items():
        if len(names) > 1:
            lines.append(
                f"> ℹ️  {' en '.join(sorted(names))} vormen een bevestigde "
                f"redundantiegroep met gedeeld management-IP {ip}."
            )
    return lines


def _section_identification(site: dict, room: dict, rack: dict,
                              data: dict, version: str,
                              att_points: list | None = None,
                              global_status: str = "",
                              h: str = "##") -> list[str]:
    # Rackstatus: altijd op basis van rack-aandachtspunten.
    # att_points is altijd een lijst (ook leeg []); None betekent niet berekend.
    if att_points is not None:
        _r_high = sum(1 for a in att_points if a["ernst"] == "Hoog")
        _r_med  = sum(1 for a in att_points if a["ernst"] == "Middel")
        _r_low  = sum(1 for a in att_points if a["ernst"] == "Laag")
        if _r_high > 0:
            val_status = "NIET DEFINITIEF"
        elif _r_med > 0 or _r_low > 0:
            val_status = "TE CONTROLEREN"
        else:
            val_status = "GEVALIDEERD"
    else:
        # att_points niet beschikbaar: veilige fallback
        val_status = global_status or "NIET DEFINITIEF"
    datum = datetime.date.today().strftime("%d/%m/%Y")
    # Globale validatiestatus: gebruik doorgegeven waarde (berekend in _build_rackfiche)
    # zodat dit consistent is met de export-header
    glob_status = global_status or "NIET DEFINITIEF"
    rows = [
        ["Site",                     site.get("name", "—")],
        ["Ruimte",                   room.get("name", "—")],
        ["Rack",                     rack.get("name", "—")],
        ["Locatie",                  site.get("location", "—")],
        ["Gegenereerd op",           datum],
        ["Bron",                     f"Networkmap Creator {version}"],
        ["Globale validatiestatus",  glob_status],
        ["Rackstatus",               val_status],
    ]
    lines = [f"{h} 1. Identificatie", ""]
    lines += _md_table(["Veld", "Waarde"], rows)
    lines.append("")
    return lines


def _section_summary(rack: dict, idx: dict, data: dict,
                      attention_points: list[dict], h: str = "##") -> list[str]:
    rack_dev_ids = {
        slot.get("device_id")
        for slot in rack.get("slots", [])
        if slot.get("device_id")
    }
    devices    = [idx["dev"].get(d) for d in rack_dev_ids if idx["dev"].get(d)]
    switches   = [d for d in devices if _is_switch(d)]
    patches    = [d for d in devices if _is_patchpanel(d)]
    cables_mgmt= [d for d in devices if d.get("type") == "cable_management"]
    actives    = [d for d in devices if _is_active(d) and not _is_switch(d)]

    all_ports  = [p for p in data.get("ports", []) if p.get("device_id") in rack_dev_ids]
    connected  = [p for p in all_ports if _connected_to(data, p["id"])]
    free       = [p for p in all_ports if not _connected_to(data, p["id"])]

    # Switchlinks: zelfde filter als _section_uplinks (tabel)
    # Minstens één kant in rack + beide zijn switches
    switch_ids  = {d["id"] for d in switches}
    uplinks     = set()
    seen_conns: set = set()
    extern_links = 0  # switch in rack → switch in ander rack
    intern_links = 0  # beide switches in hetzelfde rack

    for conn in data.get("connections", []):
        fp = idx["port"].get(conn.get("from_id", ""), {})
        tp = idx["port"].get(conn.get("to_id", ""), {})
        fd = idx["dev"].get(fp.get("device_id", ""), {})
        td = idx["dev"].get(tp.get("device_id", ""), {})
        if not _is_switch(fd) or not _is_switch(td) or fd.get("id") == td.get("id"):
            continue
        # Minstens één kant in dit rack
        if fd.get("id") not in switch_ids and td.get("id") not in switch_ids:
            continue
        key = tuple(sorted([conn.get("from_id", ""), conn.get("to_id", "")]))
        if key in seen_conns:
            continue
        seen_conns.add(key)
        uplinks.add(key)
        dev_f_in = fd.get("id") in rack_dev_ids
        dev_t_in = td.get("id") in rack_dev_ids
        if dev_f_in and dev_t_in:
            intern_links += 1
        else:
            extern_links += 1

    # SWITCHLINK via patchpanel
    switchlinks_pp: set = set()
    for sw in switches:
        for p in data.get("ports", []):
            if p.get("device_id") != sw["id"] or p.get("side") != "front":
                continue
            t = _build_trace(data, idx, p["id"])
            if t["status"] == "SWITCHLINK" and t.get("other_active"):
                ep_lbl  = t.get("endpoint", "") or t.get("direct_target", "")
                key_pp  = tuple(sorted([p["id"], ep_lbl]))
                if key_pp not in seen_conns:
                    seen_conns.add(key_pp)
                    switchlinks_pp.add(key_pp)
                    extern_links += 1  # via patchpanel = naar ander rack

    # Wandpunten en eindapparaten bereikbaar via dit rack
    wo_conn_map  = _build_wo_connection_map(data)
    rack_wps     = [wid for wid, (p, d) in wo_conn_map.items()
                    if d and d.get("id") in rack_dev_ids]
    rack_ep_ids  = set()
    for wid in rack_wps:
        wo = idx["wo"].get(wid, {})
        if wo.get("endpoint_id"):
            rack_ep_ids.add(wo["endpoint_id"])
    # Direct verbonden endpoints
    for conn in data.get("connections", []):
        if conn.get("to_type") == "endpoint":
            p = idx["port"].get(conn.get("from_id", ""), {})
            if p.get("device_id") in rack_dev_ids:
                rack_ep_ids.add(conn["to_id"])
        elif conn.get("from_type") == "endpoint":
            p = idx["port"].get(conn.get("to_id", ""), {})
            if p.get("device_id") in rack_dev_ids:
                rack_ep_ids.add(conn["from_id"])

    n_warn = len(attention_points)
    high   = sum(1 for a in attention_points if a["ernst"] == "Hoog")

    rows = [
        ["Devices in rack",       str(len(devices))],
        ["Switches",              str(len(switches))],
        ["Patchpanels",           str(len(patches))],
        ["Kabelgoten",            str(len(cables_mgmt))],
        ["Andere actieve devices", str(len(actives))],
        ["Poorten totaal",        str(len(all_ports))],
        ["Verbonden poorten",     str(len(connected))],
        ["Vrije poorten",         str(len(free))],
        ["Switchlinks (zie tabel §5)", str(len(uplinks) + len(switchlinks_pp))],
        ["  extern / core",      str(extern_links)],
        ["  intern (zelfde rack)", str(intern_links)],
        ["  via patchpanel",     str(len(switchlinks_pp))],

        ["Wandpunten gekoppeld",  str(len(rack_wps))],
        ["Eindapparaten bereikbaar", str(len(rack_ep_ids))],
        ["Aandachtspunten",
         f"{'⚠️ ' if high else ''}{n_warn} ({high} hoog)" if n_warn else "✅ geen"],
    ]
    lines = [f"{h} 2. Korte samenvatting", ""]
    lines += _md_table(["Item", "Aantal"], rows,
                        alignments=["l", "r"])
    lines.append("")
    return lines


def _section_layout(rack: dict, idx: dict, h: str = "##") -> list[str]:
    total_u = rack.get("total_units", 42)
    # Sorteer top-down: hoge U-positie bovenaan (u_start laag = hoge U)
    slots = sorted(
        rack.get("slots", []),
        key=lambda s: (total_u - s.get("u_start", 0) + 1) if s.get("u_start") else 0,
        reverse=True,  # hoogste U bovenaan
    )
    if not slots:
        return [f"{h} 3. Rack-layout", "", "*Leeg rack.*", ""]

    rows = []
    for slot in slots:
        dev = idx["dev"].get(slot.get("device_id", ""), {})
        if not dev:
            continue
        u_start = slot.get("u_start")
        height  = slot.get("height", 1)
        # U-positie: total_u - u_start + 1 geeft echte U zoals in Word-rapport
        # (u_start=1 in data = bovenste positie = U42 bij total_u=42)
        u_real  = (total_u - u_start + 1) if u_start is not None else None
        u_display = str(u_real) if u_real is not None else "?"
        u_end_real = (total_u - (u_start + height - 1) + 1) if (
            u_real is not None and height > 1
        ) else u_real
        u_end_disp = str(u_end_real) if u_end_real is not None else u_display
        u_label = f"{u_end_disp}–{u_display}" if height > 1 else u_display

        ip  = _normalize_ip(dev.get("ip", ""))
        bm  = " ".join(filter(None, [dev.get("brand", ""), dev.get("model", "")])) or "—"
        rows.append([
            u_label,
            dev.get("name", "?"),
            _type_label(dev),
            f"{height}U",
            ip,
            dev.get("notes", "") or "—",
        ])

    lines = [f"{h} 3. Rack-layout", ""]
    lines += _md_table(
        ["U", "Device", "Type", "Hoogte", "IP", "Opmerking"],
        rows,
        alignments=["r", "l", "l", "r", "l", "l"],
    )
    lines.append("")
    return lines


def _section_active_devices(rack: dict, idx: dict, dup_ips: set,
                              data: dict, h: str = "##") -> list[str]:
    actives = []
    for slot in rack.get("slots", []):
        dev = idx["dev"].get(slot.get("device_id", ""), {})
        if dev and _is_active(dev):
            actives.append(dev)

    if not actives:
        return []

    # Uplink-tellingen
    switch_ids = {d["id"] for d in actives if _is_switch(d)}
    uplink_count: dict = defaultdict(int)
    seen: set = set()
    for conn in data.get("connections", []):
        fp = idx["port"].get(conn.get("from_id", ""), {})
        tp = idx["port"].get(conn.get("to_id", ""), {})
        fd = idx["dev"].get(fp.get("device_id", ""), {})
        td = idx["dev"].get(tp.get("device_id", ""), {})
        if (fd.get("id") in switch_ids and _is_switch(td)
                and fd.get("id") != td.get("id")):
            key = tuple(sorted([conn.get("from_id", ""), conn.get("to_id", "")]))
            if key not in seen:
                seen.add(key)
                uplink_count[fd["id"]] += 1
                uplink_count[td["id"]] += 1

    rows = []
    for dev in sorted(actives, key=lambda d: d.get("name", "")):
        ip     = _normalize_ip(dev.get("ip", ""))
        ip_dup = ip in dup_ips and ip != "—"
        ip_lbl = f"{ip} ⚠️" if ip_dup else ip
        mac    = _normalize_mac(dev.get("mac", ""))
        bm     = " ".join(filter(None, [dev.get("brand", ""), dev.get("model", "")])) or "—"
        rol    = "Access" if _is_switch(dev) else _type_label(dev)
        n_up   = uplink_count.get(dev["id"], 0)
        status = "⚠️" if ip_dup else "✅"
        rows.append([
            dev.get("name", "?"),
            _type_label(dev),
            bm, ip_lbl, mac, rol,
            str(n_up) if _is_switch(dev) else "—",
            status,
        ])

    lines = [f"{h} 4. Actieve netwerkapparaten", ""]
    lines += _md_table(
        ["Device", "Type", "Model", "IP", "MAC", "Rol", "Uplinks", "Status"],
        rows,
    )
    lines.append("")

    # Redundantiegroep-info: alleen voor devices in dit rack
    rack_dev_ids_local = {
        slot.get("device_id")
        for slot in rack.get("slots", [])
        if slot.get("device_id")
    }
    stack_lines = _stack_info_lines_for_rack(data, rack_dev_ids_local, idx)
    for sl in stack_lines:
        lines.append(sl)
    if stack_lines:
        lines.append("")

    return lines


def _section_uplinks(rack: dict, idx: dict, data: dict, h: str = "##") -> list[str]:
    switch_ids = {
        slot.get("device_id")
        for slot in rack.get("slots", [])
        if idx["dev"].get(slot.get("device_id", ""), {}).get("type") == "switch"
    }
    uplinks = []
    seen: set = set()
    for conn in data.get("connections", []):
        fp = idx["port"].get(conn.get("from_id", ""), {})
        tp = idx["port"].get(conn.get("to_id", ""), {})
        if not fp or not tp:
            continue
        fd = idx["dev"].get(fp.get("device_id", ""), {})
        td = idx["dev"].get(tp.get("device_id", ""), {})
        if not _is_switch(fd) or not _is_switch(td) or fd.get("id") == td.get("id"):
            continue
        if fd.get("id") not in switch_ids and td.get("id") not in switch_ids:
            continue
        key = tuple(sorted([conn.get("from_id", ""), conn.get("to_id", "")]))
        if key in seen:
            continue
        seen.add(key)
        cable  = _cable_label(conn.get("cable_type", ""))
        sfp_warn = (
            "SFP" in (fp.get("name", "") + tp.get("name", "")).upper()
            and any(kw in (conn.get("cable_type", "") or "").upper()
                    for kw in ("UTP", "CAT"))
        )
        vlan_str = str(fp.get("vlan") or tp.get("vlan") or "—")
        status = f"⚠️ SFP/{cable}" if sfp_warn else "✅"
        uplinks.append([
            fd.get("name", "?"), fp.get("name", "?"),
            td.get("name", "?"), tp.get("name", "?"),
            cable, vlan_str, status,
        ])

    if not uplinks:
        return []

    lines = [f"{h} 5. Uplinks", ""]
    lines += _md_table(
        ["Van device", "Poort", "Naar device", "Poort", "Kabeltype", "VLAN", "Status"],
        sorted(uplinks, key=lambda r: (r[0], r[1])),
    )
    lines.append("")
    return lines


def _section_switch_ports(rack: dict, idx: dict, data: dict,
                           options: dict, h: str = "##") -> list[str]:
    include_free = options.get("include_free_ports", True)
    switches = [
        idx["dev"].get(slot.get("device_id", ""))
        for slot in rack.get("slots", [])
        if idx["dev"].get(slot.get("device_id", ""), {}).get("type") == "switch"
    ]
    switches = [s for s in switches if s]
    if not switches:
        return []

    lines = [f"{h} 6. Switchpoorten", ""]

    for sw in sorted(switches, key=lambda d: d.get("name", "")):
        ip = _normalize_ip(sw.get("ip", ""))
        lines.append(f"{h}# {sw.get('name', '?')} — {ip}")
        lines.append("")

        ports_front = sorted(
            [p for p in data.get("ports", [])
             if p.get("device_id") == sw["id"] and p.get("side") == "front"],
            key=lambda p: p.get("number", 0),
        )
        if not ports_front:
            lines.append("*Geen frontpoorten.*")
            lines.append("")
            continue

        rows = []
        warns = []
        for port in ports_front:
            t      = _build_trace(data, idx, port["id"])
            status = t["status"]
            if status == "FREE" and not include_free:
                continue

            vlan   = _vlan_display(port.get("vlan"), sw.get("type", ""))
            pname  = port.get("name", f"Port {port.get('number', '?')}")

            if status == "FREE":
                rows.append([pname, vlan, "vrij", "—", "—", "—", "⬜ FREE"])
                continue

            _direct = t["pp_front"] or t["direct_target"] or "—"
            _via    = t["pp_back"] or "—"
            _wp     = f"WP {t['wallpoint']}" if t["wallpoint"] else "—"
            _ep     = t["endpoint"] if t["endpoint"] and not t["endpoint"].upper().startswith("WP") else "—"
            rows.append([pname, vlan, _direct, _via, _wp, _ep, _trace_status_label(t)])

            for w in t.get("warnings", []):
                warns.append(f"- ⚠️  {pname}: {w}")

        lines += _md_table(
            ["Poort", "VLAN", "Directe verbinding", "Via achterkant", "Wandpunt", "Eindapparaat", "Status"],
            rows,
        )
        lines.append("")
        if warns:
            lines.append("**Waarschuwingen:**")
            lines.extend(warns)
            lines.append("")

    return lines


def _section_patchpanels(rack: dict, idx: dict, data: dict,
                          options: dict, h: str = "##") -> list[str]:
    include_free = options.get("include_free_ports", True)
    panels = [
        idx["dev"].get(slot.get("device_id", ""))
        for slot in rack.get("slots", [])
        if _is_patchpanel(idx["dev"].get(slot.get("device_id", ""), {}))
    ]
    panels = [p for p in panels if p]
    if not panels:
        return []

    lines = [f"{h} 7. Patchpanels", ""]

    for pp in sorted(panels, key=lambda d: d.get("name", "")):
        lines.append(f"{h}# {pp.get('name', '?')}")
        lines.append("")

        # Data-conventie: side="front" = switchzijde = VOOR/F in rapport
        #                  side="back"  = wandpuntzijde = ACHTER/B in rapport
        # Verificatie: _trace_port toont verbonden switch met label (F), dus front=switch.
        ports_switch = {
            p.get("number"): p
            for p in data.get("ports", [])
            if p.get("device_id") == pp["id"] and p.get("side") == "front"
        }
        ports_wall = {
            p.get("number"): p
            for p in data.get("ports", [])
            if p.get("device_id") == pp["id"] and p.get("side") == "back"
        }
        all_numbers = sorted(set(ports_switch) | set(ports_wall))

        rows = []
        for num in all_numbers:
            pf = ports_switch.get(num)   # VOOR/F = switchzijde = side=front in data
            pb = ports_wall.get(num)     # ACHTER/B = wandpuntzijde = side=back in data

            # VOOR/F-kant: trace vanuit de switch-zijde poort (side=front in data)
            if pf:
                tf = _build_trace(data, idx, pf["id"])
                # Voor patchpanel VOOR/F: de directe verbinding is de switch
                voor_lbl   = tf["direct_target"] or "vrij"
                for_status = tf["status"]
                # Uplink op PP-niveau = beide kanten actieve devices
                # Gewone switch → PP → WP/EP is GEEN uplink
                if for_status == "UPLINK" and not tf.get("direct_is_switch", False):
                    for_status = "OK"
            else:
                tf         = {}
                voor_lbl   = "—"
                for_status = "FREE"

            # ACHTER/B-kant: trace vanuit de wandpunt-zijde poort (side=back in data)
            if pb:
                tb = _build_trace(data, idx, pb["id"])
                achter_lbl = tb["direct_target"] or "vrij"
                _raw_ep    = tb.get("endpoint", "")
                back_ep    = _raw_ep if (_raw_ep and not _raw_ep.upper().startswith("WP")) else "—"
                back_status = tb["status"]
            else:
                tb          = {}
                achter_lbl  = "—"
                back_ep     = "—"
                back_status = "FREE"

            # Sla vrije rijen over indien gewenst
            if (for_status == "FREE" and back_status == "FREE"
                    and not include_free):
                continue

            # Gecombineerde status voor de patchpanelrij
            _has_wp  = bool(tb.get("wallpoint")) if pb else False
            _has_ep  = bool(back_ep and back_ep != "—")
            _is_risk = _has_wp and not _has_ep
            # SWITCHLINK: beide kanten zijn actieve devices
            # for_status=UPLINK of SWITCHLINK (switch-zijde)
            # back-zijde status=SWITCHLINK of other_active=True
            _is_switchlink = (
                for_status in ("UPLINK", "SWITCHLINK")
                and (
                    back_status in ("UPLINK", "SWITCHLINK")
                    or tb.get("other_active", False)
                    or (back_status == "OK" and tb.get("direct_is_switch", False))
                )
            )
            if for_status == "FREE" and back_status == "FREE":
                combined = "⬜ FREE"
            elif _is_switchlink:
                combined = "🔁 SWITCHLINK via patchpanel"
            elif _is_risk:
                combined = "⚠️ geen EP"
            elif for_status == "WARN" or back_status == "WARN":
                combined = "⚠️ WARN"
            elif _has_ep:
                combined = "✅ OK"
            elif _has_wp:
                combined = "⚠️ geen EP"
            elif for_status != "FREE":
                combined = "🔗 PATCHED"
            else:
                combined = "❔"

            rows.append([
                str(num),
                voor_lbl,
                achter_lbl,
                back_ep,
                combined,
            ])

        if rows:
            lines += _md_table(
                ["Poort", "VOOR/F (switch)", "ACHTER/B (wandpunt/EP)", "Eindpunt", "Status"],
                rows,
                alignments=["r", "l", "l", "l", "l"],
            )
        else:
            lines.append("*Geen poorten of alle vrij (weergave uitgeschakeld).*")
        lines.append("")

    return lines


def _section_wallpoints(rack: dict, idx: dict, data: dict,
                         site: dict, h: str = "##") -> list[str]:
    rack_dev_ids = {
        slot.get("device_id")
        for slot in rack.get("slots", [])
        if slot.get("device_id")
    }
    wo_conn_map = _build_wo_connection_map(data)

    rows = []
    for wo_id, (port, dev) in sorted(
        wo_conn_map.items(),
        key=lambda kv: idx["wo"].get(kv[0], {}).get("name", ""),
    ):
        if not dev or dev.get("id") not in rack_dev_ids:
            continue
        wo   = idx["wo"].get(wo_id, {})
        ep   = idx["ep"].get(wo.get("endpoint_id", "")) if wo.get("endpoint_id") else None
        _, room_obj = idx["wo_room"].get(wo_id, (site, {}))

        # Via patchpanel?
        # Zoek of er een patchpanel tussen zit door te kijken welk device de poort heeft
        pp_lbl = "—"
        if port and _is_patchpanel(dev):
            # Port is in een patchpanel → zoek de switch die de andere kant heeft
            pp_lbl  = f"{dev.get('name','?')} / {port.get('name','?')}"
            sw_port = None
            partner_side = "front" if port.get("side") == "back" else "back"
            partner = next(
                (p for p in data.get("ports", [])
                 if p.get("device_id") == dev.get("id")
                 and p.get("side") == partner_side
                 and p.get("number") == port.get("number")),
                None,
            )
            if partner:
                sw_conn = _connected_to(data, partner["id"])
                if sw_conn:
                    oid  = sw_conn["to_id"] if sw_conn["from_id"] == partner["id"] else sw_conn["from_id"]
                    sp   = idx["port"].get(oid, {})
                    sdv  = idx["dev"].get(sp.get("device_id", ""), {})
                    sw_port = f"{sdv.get('name','?')} / {sp.get('name','?')}"
        else:
            sw_port = f"{dev.get('name','?')} / {port.get('name','?')}" if port else "—"

        status = "✅ OK" if ep else "⚠️ geen EP"
        rows.append([
            wo.get("name", wo_id),
            room_obj.get("name", "—") if room_obj else "—",
            ep.get("name", "—") if ep else "—",
            pp_lbl,
            sw_port or "—",
            status,
        ])

    if not rows:
        return []

    lines = [f"{h} 8. Wandpunten en eindapparaten", ""]
    lines += _md_table(
        ["Wandpunt", "Ruimte", "Eindapparaat", "Via patchpanel", "Switchpoort", "Status"],
        rows,
    )
    lines.append("")
    return lines


def _section_attention_points(attention_points: list[dict], h: str = "##") -> list[str]:
    if not attention_points:
        lines = [f"{h} 9. Aandachtspunten", ""]
        lines.append("✅ Geen aandachtspunten voor dit rack.")
        lines.append("")
        return lines

    rows = []
    order = {"Hoog": 0, "Middel": 1, "Laag": 2}
    for ap in sorted(attention_points, key=lambda a: order.get(a["ernst"], 9)):
        ernst_lbl = {"Hoog": "🔴 Hoog", "Middel": "🟠 Middel", "Laag": "🟡 Laag"}.get(
            ap["ernst"], ap["ernst"]
        )
        rows.append([ernst_lbl, ap["type"], ap["object"], ap["detail"], ap["actie"]])

    lines = [f"{h} 9. Aandachtspunten", ""]
    lines += _md_table(
        ["Ernst", "Type", "Object", "Detail", "Actie"],
        rows,
    )
    lines.append("")
    return lines




def _section_switch_cascade(rack: dict, idx: dict, data: dict, h: str = "##") -> list[str]:
    """
    Volledig niveau: cascade-tracing per switch als leesbaar tekstblok.
    Hergebruikt _build_trace + _trace_to_cascade voor consistentie met de tabel.
    """
    switches = [
        idx["dev"].get(slot.get("device_id", ""))
        for slot in rack.get("slots", [])
        if idx["dev"].get(slot.get("device_id", ""), {}).get("type") == "switch"
    ]
    switches = [s for s in switches if s]
    if not switches:
        return []

    lines = [f"{h} 6b. Switchpoorten — volledige tracing", ""]

    for sw in sorted(switches, key=lambda d: d.get("name", "")):
        ip = _normalize_ip(sw.get("ip", ""))
        lines.append(f"{h}# {sw.get('name', '?')} — {ip}")
        lines.append("")
        lines.append("```")

        ports_front = sorted(
            [p for p in data.get("ports", [])
             if p.get("device_id") == sw["id"] and p.get("side") == "front"],
            key=lambda p: p.get("number", 0),
        )
        for port in ports_front:
            pname = port.get("name", f"Port {port.get('number', '?')}") 
            t     = _build_trace(data, idx, port["id"])
            lines.extend(_trace_to_cascade(pname, t))
            lines.append("")

        lines.append("```")
        lines.append("")

    return lines

def _section_control_log(h: str = "##") -> list[str]:
    rows = [
        ["", "", "Fysieke rackcontrole",    "☐ OK  /  ☐ Niet OK", ""],
        ["", "", "Patchpanelcontrole",      "☐ OK  /  ☐ Niet OK", ""],
        ["", "", "Switchpoortcontrole",     "☐ OK  /  ☐ Niet OK", ""],
        ["", "", "VLAN-controle",           "☐ OK  /  ☐ Niet OK", ""],
        ["", "", "Uplink-controle",         "☐ OK  /  ☐ Niet OK", ""],
        ["", "", "Aandachtspunten afgewerkt","☐ OK  /  ☐ Niet OK", ""],
    ]
    lines = [f"{h} 10. Controlelog", ""]
    lines += _md_table(
        ["Datum", "Uitvoerder", "Controle", "Resultaat", "Opmerking"],
        rows,
    )
    lines.append("")
    return lines


# =============================================================================
# HOOFD RACKFICHE BUILDER
# =============================================================================

def _build_rackfiche(data: dict, idx: dict,
                     site: dict, room: dict, rack: dict,
                     version: str, options: dict,
                     heading_level: str = "#") -> list[str]:
    dup_ips     = _build_duplicate_ip_set(data)
    att_points  = _rack_attention_points(data, idx, rack, site, room, dup_ips)

    # Globale status: tel alle aandachtspunten over alle racks heen
    # Dit is dezelfde berekening als de export-header gebruikt.
    _raw_status = data.get("_validation_status", "")
    if _raw_status and _raw_status != "GEVALIDEERD":
        _global_status = _raw_status
    else:
        _all_high = sum(
            1 for s in get_all_sites(data)
            for r in s.get("rooms", [])
            for rk in r.get("racks", [])
            for a in _rack_attention_points(data, idx, rk, s, r, dup_ips)
            if a["ernst"] == "Hoog"
        )
        _all_issues = sum(
            1 for s in get_all_sites(data)
            for r in s.get("rooms", [])
            for rk in r.get("racks", [])
            for _ in _rack_attention_points(data, idx, rk, s, r, dup_ips)
        )
        if _all_high > 0:
            _global_status = "NIET DEFINITIEF"
        elif _all_issues > 0:
            _global_status = "TE CONTROLEREN"
        else:
            _global_status = "GEVALIDEERD"

    rack_name = rack.get("name", "?")
    lines: list[str] = []
    lines.append(f"{heading_level} Rackfiche — {rack_name}")
    lines.append("")

    # Sectie-headings zijn altijd één niveau dieper dan de rackfiche-header
    _h_map = {"#": "##", "##": "###", "###": "####"}
    sh = _h_map.get(heading_level, "##")  # section heading

    # Aandachtspunten bovenaan bij technisch/volledig niveau
    level = options.get("detail_level", "technical")
    high_points = [a for a in att_points if a["ernst"] == "Hoog"]
    if high_points and level in ("technical", "full"):
        lines.append("> ⚠️  **Let op: dit rack heeft hoog-prioriteit aandachtspunten.**")
        for hp in high_points:
            lines.append(f"> - {hp['type']}: {hp['object']} — {hp['detail']}")
        lines.append("")

    lines += _section_identification(site, room, rack, data, version,
                                     att_points, global_status=_global_status, h=sh)
    lines += _section_summary(rack, idx, data, att_points, h=sh)
    lines += _section_layout(rack, idx, h=sh)

    # Detailniveaus:
    #   kort      = identificatie + samenvatting + U-layout + aandachtspunten + controlelog
    #   technisch = alles in tabelvorm
    #   volledig  = technisch + cascade-tracing als extra tekstblok per switch
    if level in ("technical", "full"):
        lines += _section_active_devices(rack, idx, dup_ips, data, h=sh)
        lines += _section_uplinks(rack, idx, data, h=sh)

        if options.get("include_switches", True):
            lines += _section_switch_ports(rack, idx, data, options, h=sh)
            if level == "full":
                lines += _section_switch_cascade(rack, idx, data, h=sh)

        if options.get("include_patchpanels", True):
            lines += _section_patchpanels(rack, idx, data, options, h=sh)

        lines += _section_wallpoints(rack, idx, data, site, h=sh)

    if options.get("include_attention_points", True):
        lines += _section_attention_points(att_points, h=sh)

    if options.get("include_control_log", True):
        lines += _section_control_log(h=sh)

    lines.append("---")
    lines.append("")
    return lines


# =============================================================================
# GLOBALE HEADER / INDEX
# =============================================================================

def _global_header(data: dict, subtitle: str, version: str,
                   scoped_sites: list | None = None,
                   company_name: str = "") -> list[str]:
    """
    scoped_sites: lijst van site-dicts voor deze scope.
    Als None, worden globale tellingen gebruikt (all-scope).
    company_name: optionele bedrijfsnaam — verschijnt als extra rij in header.
    """
    datum     = datetime.date.today().strftime("%d/%m/%Y")
    sites     = scoped_sites if scoped_sites is not None else get_all_sites(data)
    # Apparaten en verbindingen filteren op de devices in scope
    scope_dev_ids: set = {
        slot.get("device_id")
        for s in sites
        for r in s.get("rooms", [])
        for rack in r.get("racks", [])
        for slot in rack.get("slots", [])
        if slot.get("device_id")
    }
    if scoped_sites is not None:
        n_dev  = len(scope_dev_ids)
        n_conn = sum(
            1 for c in data.get("connections", [])
            if (idx_port := {p["id"]: p for p in data.get("ports", [])})
            and (
                idx_port.get(c.get("from_id", ""), {}).get("device_id") in scope_dev_ids
                or idx_port.get(c.get("to_id", ""), {}).get("device_id") in scope_dev_ids
            )
        )
    else:
        n_dev  = len(data.get("devices", []))
        n_conn = len(data.get("connections", []))
    n_sites   = len(sites)
    n_racks   = sum(len(r.get("racks", [])) for s in sites for r in s.get("rooms", []))
    n_wo      = sum(len(r.get("wall_outlets", [])) for s in sites for r in s.get("rooms", []))
    # Validatiestatus: gebruik data-waarde als aanwezig, anders dynamisch berekenen.
    # NOOIT GEVALIDEERD tonen als er nog aandachtspunten zijn.
    _raw_status = data.get("_validation_status", "")
    _ap = data.get("_action_counts", {})
    _ap_high   = _ap.get("high", 0)
    _ap_medium = _ap.get("medium", 0)
    _ap_low    = _ap.get("low", 0)
    _ap_total  = _ap.get("total", _ap_high + _ap_medium + _ap_low)
    if _raw_status and _raw_status != "GEVALIDEERD":
        # Gebruik data-waarde tenzij die GEVALIDEERD zegt terwijl er issues zijn
        val_status = _raw_status
    elif _ap_high > 0:
        val_status = "NIET DEFINITIEF"
    elif _ap_medium > 0 or _ap_low > 0:
        val_status = "TE CONTROLEREN"
    elif _raw_status == "GEVALIDEERD":
        val_status = "GEVALIDEERD"
    else:
        # Geen _action_counts beschikbaar: veilige default
        val_status = "NIET DEFINITIEF"

    rows = [
        ["Scope",            subtitle],
        ["Gegenereerd op",   datum],
        ["Versie",           version],
    ]
    if company_name:
        lbl = "Bedrijven" if company_name.endswith("bedrijven") else "Bedrijf"
        rows.append([lbl, company_name])
    rows += [
        ["Sites",            str(n_sites)],
        ["Racks",            str(n_racks)],
        ["Devices",          str(n_dev)],
        ["Verbindingen",     str(n_conn)],
        ["Wandpunten",       str(n_wo)],
        ["Validatiestatus",  val_status],
    ]
    lines = [
        "# Networkmap Creator — Rack Export",
        "",
    ]
    lines += _md_table(["Veld", "Waarde"], rows)
    lines.append("")
    lines.append("---")
    lines.append("")
    return lines


def _global_index(data: dict, idx: dict, dup_ips: set,
                  scoped_sites: list | None = None) -> list[str]:
    lines = ["## Index", ""]

    def _site_rows(site: dict) -> list[list]:
        rows = []
        for room in site.get("rooms", []):
            for rack in room.get("racks", []):
                rack_dev_ids = {
                    slot.get("device_id")
                    for slot in rack.get("slots", [])
                    if slot.get("device_id")
                }
                devs   = [idx["dev"].get(d) for d in rack_dev_ids if idx["dev"].get(d)]
                n_sw   = sum(1 for d in devs if _is_switch(d))
                n_pp   = sum(1 for d in devs if _is_patchpanel(d))
                att    = _rack_attention_points(data, idx, rack, site, room, dup_ips)
                high   = sum(1 for a in att if a["ernst"] == "Hoog")
                _med   = sum(1 for a in att if a["ernst"] == "Middel")
                _low   = sum(1 for a in att if a["ernst"] == "Laag")
                if not att:
                    warn_lbl = "✅ 0"
                else:
                    _parts_w = []
                    if high:  _parts_w.append(f"🔴 {high}")
                    if _med:  _parts_w.append(f"🟠 {_med}")
                    if _low:  _parts_w.append(f"🟡 {_low}")
                    warn_lbl = " / ".join(_parts_w)
                rows.append([
                    room.get("name", "?"),
                    rack.get("name", "?"),
                    str(len(devs)),
                    str(n_sw),
                    str(n_pp),
                    warn_lbl,
                ])
        return rows

    _tbl_headers   = ["Ruimte", "Rack", "Devices", "Switches", "Patchpanels", "Aandachtspunten"]
    _tbl_align     = ["l", "l", "r", "r", "r", "l"]

    if scoped_sites is not None:
        # Gefilterde scope (company of site): gewoon per site
        for site in scoped_sites:
            lines.append(f"### {site.get('name', '?')}")
            lines.append("")
            lines += _md_table(_tbl_headers, _site_rows(site), alignments=_tbl_align)
            lines.append("")
    else:
        # All-scope: groepeer per bedrijf
        for company in get_all_companies(data):
            lines.append(f"### 🏢 {company.get('name', '?')}")
            lines.append("")
            for site in company.get("sites", []):
                lines.append(f"**{site.get('name', '?')}**")
                lines.append("")
                lines += _md_table(_tbl_headers, _site_rows(site), alignments=_tbl_align)
                lines.append("")

    lines.append("---")
    lines.append("")
    return lines


def _global_attention_summary(data: dict, idx: dict, dup_ips: set,
                              scoped_sites: list | None = None) -> list[str]:
    """Alle aandachtspunten over alle racks, gesorteerd op ernst."""
    # Bouw site_id → bedrijfsnaam mapping voor all-scope
    site_to_company: dict[str, str] = {}
    for company in get_all_companies(data):
        for s in company.get("sites", []):
            site_to_company[s["id"]] = company.get("name", "")

    all_points = []
    for site in (scoped_sites if scoped_sites is not None else get_all_sites(data)):
        company_name = site_to_company.get(site.get("id", ""), "") if scoped_sites is None else ""
        for room in site.get("rooms", []):
            for rack in room.get("racks", []):
                rack_name = f"{site.get('name','?')} › {room.get('name','?')} › {rack.get('name','?')}"
                pts = _rack_attention_points(data, idx, rack, site, room, dup_ips)
                for p in pts:
                    all_points.append({**p, "rack": rack_name, "_company": company_name})

    if not all_points:
        return [
            "## Aandachtspunten — alle racks",
            "",
            "✅ Geen aandachtspunten gevonden.",
            "",
            "---",
            "",
        ]

    order = {"Hoog": 0, "Middel": 1, "Laag": 2}
    # Per bedrijf: tel hoog-items voor volgorde (meeste hoog eerst)
    company_order: dict[str, int] = {}
    for ap in all_points:
        c = ap["_company"]
        if c not in company_order:
            company_order[c] = 0
        if ap["ernst"] == "Hoog":
            company_order[c] += 1
    # Sorteer: bedrijf op aflopend hoog-count, daarbinnen ernst → rack
    all_points.sort(key=lambda a: (
        -company_order.get(a["_company"], 0),
        a["_company"],
        order.get(a["ernst"], 9),
        a["rack"],
    ))

    # Bij all-scope: groepeer per bedrijf met een scheidingskop
    use_company_groups = scoped_sites is None and any(a["_company"] for a in all_points)

    if use_company_groups:
        lines = ["## Aandachtspunten — alle racks", ""]
        current_company = None
        current_rows: list[list] = []

        def _flush(company: str, rows: list[list]) -> list[str]:
            out = []
            if rows:
                out.append(f"### 🏢 {company}")
                out.append("")
                out += _md_table(["Ernst", "Rack", "Type", "Object", "Detail"], rows)
                out.append("")
            return out

        for ap in all_points:
            ernst_lbl = {"Hoog": "🔴 Hoog", "Middel": "🟠 Middel", "Laag": "🟡 Laag"}.get(
                ap["ernst"], ap["ernst"]
            )
            if ap["_company"] != current_company:
                if current_company is not None:
                    lines += _flush(current_company, current_rows)
                current_company = ap["_company"]
                current_rows = []
            current_rows.append([ernst_lbl, ap["rack"], ap["type"], ap["object"], ap["detail"]])
        if current_company is not None:
            lines += _flush(current_company, current_rows)
        lines.append("---")
        lines.append("")
        return lines

    # Enkelvoudige scope: platte tabel zoals voorheen
    rows = []
    for ap in all_points:
        ernst_lbl = {"Hoog": "🔴 Hoog", "Middel": "🟠 Middel", "Laag": "🟡 Laag"}.get(
            ap["ernst"], ap["ernst"]
        )
        rows.append([ernst_lbl, ap["rack"], ap["type"], ap["object"], ap["detail"]])

    lines = ["## Aandachtspunten — alle racks", ""]
    lines += _md_table(["Ernst", "Rack", "Type", "Object", "Detail"], rows)
    lines.append("")
    lines.append("---")
    lines.append("")
    return lines


# =============================================================================
# RENDER FUNCTIES (publieke API — zelfde signatuur als v1)
# =============================================================================

def _get_version() -> str:
    try:
        from app import version as _ver
        return _ver.__version__
    except Exception:
        return "—"


def _merged_options(user_options: dict | None) -> dict:
    opts = dict(_DEFAULT_OPTIONS)
    if user_options:
        opts.update(user_options)
    return opts


# =============================================================================
# TRACING-ONLY EXPORT
# Compacte rackfiche voor fysiek gebruik bij het rack.
# Per rack een nieuwe sectie (--- pagebreak hint), alleen tracing + samenvatting.
# Geen patchpanelmatrix, geen wandpunttabel, geen controlelog.
# =============================================================================

def _render_tracing_fiche(data: dict, idx: dict,
                           site: dict, room: dict, rack: dict,
                           version: str) -> list[str]:
    """
    Compacte rackfiche met alleen:
      - identificatie (1 regel header)
      - rack-layout tabel (U-posities)
      - aandachtspunten (compact)
      - uplinks
      - switchpoorten volledig cascade-tracing
    Bedoeld om uitgedrukt bij het rack te leggen.
    Elke rack begint met een nieuwe duidelijke scheiding.
    """
    dup_ips    = _build_duplicate_ip_set(data)
    att_points = _rack_attention_points(data, idx, rack, site, room, dup_ips)

    rack_name  = rack.get("name", "?")
    site_name  = site.get("name", "?")
    room_name  = room.get("name", "?")
    datum      = datetime.date.today().strftime("%d/%m/%Y")

    # Rackstatus
    _r_high = sum(1 for a in att_points if a["ernst"] == "Hoog")
    _r_med  = sum(1 for a in att_points if a["ernst"] == "Middel")
    _r_low  = sum(1 for a in att_points if a["ernst"] == "Laag")
    if _r_high > 0:
        rack_status = f"NIET DEFINITIEF — {_r_high} hoog-prioriteit"
    elif _r_med > 0 or _r_low > 0:
        rack_status = "TE CONTROLEREN"
    else:
        rack_status = "GEVALIDEERD"

    lines: list[str] = []

    # ── Header ──────────────────────────────────────────────────────────────
    lines.append(f"# 🗄 {rack_name}  ·  {room_name}  ·  {site_name}")
    lines.append("")
    lines.append(f"*Gegenereerd op {datum}  ·  Versie {version}  ·  Status: **{rack_status}***")
    lines.append("")

    # ── Rack-layout compact ─────────────────────────────────────────────────
    slots = sorted(
        rack.get("slots", []),
        key=lambda s: s.get("u_start", 0),
        reverse=True,
    )
    total_u = rack.get("total_units", 42)
    layout_rows = []
    for slot in slots:
        dev = idx["dev"].get(slot.get("device_id", ""), {})
        if not dev:
            continue
        u_start = slot.get("u_start")
        height  = slot.get("height", 1)
        u_real  = (total_u - u_start + 1) if u_start is not None else None
        u_end   = (total_u - (u_start + height - 1) + 1) if (u_real and height > 1) else u_real
        u_lbl   = f"{u_end}–{u_real}" if height > 1 else str(u_real or "?")
        ip      = _normalize_ip(dev.get("ip", ""))
        layout_rows.append([u_lbl, dev.get("name", "?"), _type_label(dev), ip])

    if layout_rows:
        lines.append("## Rack-layout")
        lines.append("")
        lines += _md_table(["U", "Device", "Type", "IP"],
                            layout_rows,
                            alignments=["r", "l", "l", "l"])
        lines.append("")

    # ── Aandachtspunten compact ─────────────────────────────────────────────
    if att_points:
        lines.append("## ⚠️ Aandachtspunten")
        lines.append("")
        order = {"Hoog": 0, "Middel": 1, "Laag": 2}
        for ap in sorted(att_points, key=lambda a: order.get(a["ernst"], 9)):
            icon = {"Hoog": "🔴", "Middel": "🟠", "Laag": "🟡"}.get(ap["ernst"], "❔")
            lines.append(f"- {icon} **{ap['type']}** — {ap['object']}: {ap['detail']}")
        lines.append("")

    # Redundantiegroep info
    stack_lines = _stack_info_lines(data)
    if stack_lines:
        for sl in stack_lines:
            lines.append(sl)
        lines.append("")

    # ── Uplinks compact ─────────────────────────────────────────────────────
    switch_ids = {
        slot.get("device_id")
        for slot in rack.get("slots", [])
        if idx["dev"].get(slot.get("device_id", ""), {}).get("type") == "switch"
    }
    uplinks: list[list[str]] = []
    seen_ul: set = set()
    for conn in data.get("connections", []):
        fp = idx["port"].get(conn.get("from_id", ""), {})
        tp = idx["port"].get(conn.get("to_id", ""), {})
        fd = idx["dev"].get(fp.get("device_id", ""), {})
        td = idx["dev"].get(tp.get("device_id", ""), {})
        if not (_is_switch(fd) and _is_switch(td) and fd.get("id") != td.get("id")):
            continue
        if fd.get("id") not in switch_ids and td.get("id") not in switch_ids:
            continue
        key = tuple(sorted([conn.get("from_id", ""), conn.get("to_id", "")]))
        if key in seen_ul:
            continue
        seen_ul.add(key)
        cable = _cable_label(conn.get("cable_type", ""))
        sfp_warn = (
            "SFP" in (fp.get("name", "") + tp.get("name", "")).upper()
            and any(kw in (conn.get("cable_type", "") or "").upper()
                    for kw in ("UTP", "CAT"))
        )
        status = "⚠️ SFP/" + cable if sfp_warn else "✅"
        uplinks.append([
            fd.get("name", "?"), fp.get("name", "?"),
            td.get("name", "?"), tp.get("name", "?"),
            cable, status,
        ])

    if uplinks:
        lines.append("## 🔁 Uplinks / Switchlinks")
        lines.append("")
        lines += _md_table(
            ["Van", "Poort", "Naar", "Poort", "Kabel", "Status"],
            sorted(uplinks, key=lambda r: (r[0], r[1])),
        )
        lines.append("")

    # ── Switchpoorten volledige tracing ────────────────────────────────────
    switches = [
        idx["dev"].get(slot.get("device_id", ""))
        for slot in rack.get("slots", [])
        if idx["dev"].get(slot.get("device_id", ""), {}).get("type") == "switch"
    ]
    switches = [s for s in switches if s]

    if switches:
        lines.append("## 🔌 Switchpoorten — volledige tracing")
        lines.append("")

        for sw in sorted(switches, key=lambda d: d.get("name", "")):
            ip = _normalize_ip(sw.get("ip", ""))
            lines.append(f"{h}# {sw.get('name', '?')}  ·  {ip}")
            lines.append("")
            lines.append("```")

            ports_front = sorted(
                [p for p in data.get("ports", [])
                 if p.get("device_id") == sw["id"] and p.get("side") == "front"],
                key=lambda p: p.get("number", 0),
            )
            for port in ports_front:
                pname = port.get("name", f"Port {port.get('number', '?')}")
                t     = _build_trace(data, idx, port["id"])
                lines.extend(_trace_to_cascade(pname, t))
                lines.append("")

            lines.append("```")
            lines.append("")

    # ── Einde rackfiche ─────────────────────────────────────────────────────
    lines.append("---")
    lines.append("")
    return lines


def render_tracing_all(data: dict) -> str:
    """Tracing-only export: alle sites en racks, per rack nieuwe sectie."""
    idx     = _build_index(data)
    version = _get_version()
    datum   = datetime.date.today().strftime("%d/%m/%Y")

    n_racks = sum(
        len(r.get("racks", []))
        for s in get_all_sites(data)
        for r in s.get("rooms", [])
    )

    lines = [
        "# Networkmap Creator — Racktracing",
        "",
        f"*Gegenereerd op {datum}  ·  Versie {version}  ·  {n_racks} racks*",
        "",
        "> Dit document bevat alleen de switchpoort-tracing per rack.",
        "> Bedoeld om uitgedrukt bij het rack te leggen.",
        "> Eén sectie per rack.",
        "",
        "---",
        "",
    ]
    for company in get_all_companies(data):
        lines.append(f"# 🏢 {company.get('name', '?')}")
        lines.append("")
        for site in company.get("sites", []):
            for room in site.get("rooms", []):
                for rack in room.get("racks", []):
                    lines += _render_tracing_fiche(
                        data, idx, site, room, rack, version
                    )
    return "\n".join(lines)


def render_tracing_site(data: dict, site_id: str) -> str:
    """Tracing-only export: één site."""
    idx     = _build_index(data)
    version = _get_version()
    datum   = datetime.date.today().strftime("%d/%m/%Y")
    site    = next((s for s in get_all_sites(data) if s["id"] == site_id), None)
    if not site:
        return f"# Site niet gevonden: {site_id}\n"

    lines = [
        f"# Networkmap Creator — Racktracing  ·  {site.get('name', '?')}",
        "",
        f"*Gegenereerd op {datum}  ·  Versie {version}*",
        "",
        "---",
        "",
    ]
    for room in site.get("rooms", []):
        for rack in room.get("racks", []):
            lines += _render_tracing_fiche(data, idx, site, room, rack, version)
    return "\n".join(lines)


def render_tracing_rack(data: dict, rack_id: str) -> str:
    """Tracing-only export: één rack."""
    idx     = _build_index(data)
    version = _get_version()
    for site in get_all_sites(data):
        for room in site.get("rooms", []):
            for rack in room.get("racks", []):
                if rack["id"] == rack_id:
                    lines = _render_tracing_fiche(
                        data, idx, site, room, rack, version
                    )
                    return "\n".join(lines)
    return f"# Rack niet gevonden: {rack_id}\n"


def render_company(data: dict, company_id: str, options: dict | None = None) -> str:
    """F4 — Rack export voor één bedrijf."""
    opts    = _merged_options(options)
    idx     = _build_index(data)
    version = _get_version()
    dup_ips = _build_duplicate_ip_set(data)

    company = next((c for c in get_all_companies(data) if c["id"] == company_id), None)
    if not company:
        return f"# Bedrijf niet gevonden: {company_id}\n"

    company_name = company.get("name", "?")
    sites        = company.get("sites", [])

    lines = _global_header(
        data,
        f"Bedrijf: {company_name}",
        version,
        scoped_sites=sites,
        company_name=company_name,
    )
    lines += _global_index(data, idx, dup_ips, scoped_sites=sites)
    lines += _global_attention_summary(data, idx, dup_ips, scoped_sites=sites)

    lines.append("## Rackfiches")
    lines.append("")

    for site in sites:
        lines.append(f"## 📍 {site.get('name', '?')}")
        lines.append("")
        for room in site.get("rooms", []):
            for rack in room.get("racks", []):
                lines += _build_rackfiche(
                    data, idx, site, room, rack, version, opts,
                    heading_level="###"
                )

    return "\n".join(lines)


def render_tracing_company(data: dict, company_id: str) -> str:
    """F4 — Tracing-only export voor één bedrijf."""
    idx     = _build_index(data)
    version = _get_version()
    datum   = datetime.date.today().strftime("%d/%m/%Y")

    company = next((c for c in get_all_companies(data) if c["id"] == company_id), None)
    if not company:
        return f"# Bedrijf niet gevonden: {company_id}\n"

    company_name = company.get("name", "?")
    sites        = company.get("sites", [])

    n_racks = sum(
        len(r.get("racks", []))
        for s in sites
        for r in s.get("rooms", [])
    )

    lines = [
        f"# Networkmap Creator — Racktracing  ·  {company_name}",
        "",
        f"*Gegenereerd op {datum}  ·  Versie {version}  ·  {n_racks} racks*",
        "",
        "---",
        "",
    ]
    for site in sites:
        for room in site.get("rooms", []):
            for rack in room.get("racks", []):
                lines += _render_tracing_fiche(data, idx, site, room, rack, version)
    return "\n".join(lines)


def render_all(data: dict, options: dict | None = None) -> str:
    opts    = _merged_options(options)
    idx     = _build_index(data)
    version = _get_version()
    dup_ips = _build_duplicate_ip_set(data)

    n_companies = len(get_all_companies(data))
    lines = _global_header(data, "Alle sites en racks", version,
                           company_name=f"{n_companies} bedrijven" if n_companies > 1 else "")
    lines += _global_index(data, idx, dup_ips)
    lines += _global_attention_summary(data, idx, dup_ips)

    lines.append("## Rackfiches")
    lines.append("")

    for company in get_all_companies(data):
        company_name = company.get("name", "?")
        lines.append(f"# 🏢 {company_name}")
        lines.append("")
        for site in company.get("sites", []):
            lines.append(f"## 📍 {site.get('name', '?')}")
            lines.append("")
            for room in site.get("rooms", []):
                for rack in room.get("racks", []):
                    lines += _build_rackfiche(
                        data, idx, site, room, rack, version, opts,
                        heading_level="###"
                    )

    return "\n".join(lines)


def render_site(data: dict, site_id: str, options: dict | None = None) -> str:
    opts    = _merged_options(options)
    idx     = _build_index(data)
    version = _get_version()
    dup_ips = _build_duplicate_ip_set(data)

    site = next((s for s in get_all_sites(data) if s["id"] == site_id), None)
    if not site:
        return f"# Site niet gevonden: {site_id}\n"

    lines = _global_header(data, f"Site: {site.get('name','?')}", version,
                           scoped_sites=[site])
    lines += _global_index(data, idx, dup_ips, scoped_sites=[site])
    lines += _global_attention_summary(data, idx, dup_ips, scoped_sites=[site])

    for room in site.get("rooms", []):
        for rack in room.get("racks", []):
            lines += _build_rackfiche(
                data, idx, site, room, rack, version, opts
            )

    return "\n".join(lines)


def render_rack_only(data: dict, rack_id: str, options: dict | None = None) -> str:
    opts    = _merged_options(options)
    idx     = _build_index(data)
    version = _get_version()

    for site in get_all_sites(data):
        for room in site.get("rooms", []):
            for rack in room.get("racks", []):
                if rack["id"] == rack_id:
                    datum = datetime.date.today().strftime("%d/%m/%Y")
                    rack_name = rack.get("name", "?")
                    header = [
                        "# Networkmap Creator — Rack Export",
                        "",
                        f"**{site.get('name','?')} › {room.get('name','?')} › {rack_name}**"
                        f"  ·  gegenereerd op {datum}  ·  versie {version}",
                        "",
                        "---",
                        "",
                    ]
                    fiche = _build_rackfiche(
                        data, idx, site, room, rack, version, opts
                    )
                    return "\n".join(header + fiche)

    return f"# Rack niet gevonden: {rack_id}\n"


# =============================================================================
# HOOFD EXPORT FUNCTIE — zelfde signatuur als v1 + optioneel options-dict
# =============================================================================

def export_md(
    data:       dict,
    filepath:   str,
    scope:      str = "all",
    company_id: str = "",
    site_id:    str = "",
    rack_id:    str = "",
    options:    dict | None = None,
) -> tuple[bool, str]:
    """
    Schrijf de rack-export naar filepath.
    Signatuur is volledig achterwaarts compatibel met v1.
    options-dict is optioneel en overschrijft _DEFAULT_OPTIONS.
    scope "company" + company_id: export gefilterd op één bedrijf (F4).
    """
    try:
        opts = _merged_options(options)
        _tracing_only = opts.get("tracing_only", False)

        if _tracing_only:
            if scope == "rack":
                file_content = render_tracing_rack(data, rack_id)
            elif scope == "site":
                file_content = render_tracing_site(data, site_id)
            elif scope == "company":
                file_content = render_tracing_company(data, company_id)
            else:
                file_content = render_tracing_all(data)
        else:
            if scope == "rack":
                file_content = render_rack_only(data, rack_id, options)
            elif scope == "site":
                file_content = render_site(data, site_id, options)
            elif scope == "company":
                file_content = render_company(data, company_id, options)
            else:
                file_content = render_all(data, options)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(file_content)
        return True, ""
    except Exception:
        import traceback
        return False, traceback.format_exc()