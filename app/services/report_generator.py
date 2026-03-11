# =============================================================================
# Networkmap_Creator
# File:    app/services/report_generator.py
# Role:    Word rapport generator (python-docx)
# Version: 1.2.4
# Author:  Barremans
# Changes: 1.0.0 — Initieel: sites, ruimtes, racks, devices, verbindingen
#          1.1.0 — VLAN sectie toegevoegd
#          1.2.0 — Professionele opmaak: koptekst, inhoudsopgave, samenvatting
#                  VLAN overzicht per VLAN met poorten + wandpunten
#                  Afwisselende rijen, kleur-coded headers, betere layout
# =============================================================================

from __future__ import annotations
import datetime
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm, Twips
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

# ---------------------------------------------------------------------------
# Kleurenpalet
# ---------------------------------------------------------------------------
_C_PRIMARY      = "1E3A5F"   # Donkerblauw — headers
_C_SECONDARY    = "2E75B6"   # Middenblauw — sub-headers
_C_ACCENT       = "00B0F0"   # Lichtblauw — accenten
_C_SUCCESS      = "375623"   # Donkergroen — verbonden
_C_WARNING      = "C55A11"   # Oranje — waarschuwing
_C_MUTED        = "808080"   # Grijs — secundaire tekst
_C_MID_TEXT     = "404040"   # Donkergrijs — body tekst
_C_ROW_ALT      = "EBF3FB"   # Lichtblauw — afwisselende rij
_C_ROW_HEADER   = "1E3A5F"   # Header rij achtergrond
_C_VLAN_HDR     = "154360"   # VLAN header
_C_WHITE        = "FFFFFF"

# ---------------------------------------------------------------------------
# Helper: RGB tuple → hex string
# ---------------------------------------------------------------------------
def _rgb(hex_str: str) -> RGBColor:
    r = int(hex_str[0:2], 16)
    g = int(hex_str[2:4], 16)
    b = int(hex_str[4:6], 16)
    return RGBColor(r, g, b)

# ---------------------------------------------------------------------------
# Document opmaak helpers
# ---------------------------------------------------------------------------

def _set_cell_bg(cell, hex_color: str):
    """Zet achtergrondkleur van een tabelcel."""
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex_color)
    tcPr.append(shd)

def _set_cell_border(cell, **kwargs):
    """Stel celranden in."""
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        cfg = kwargs.get(edge, {})
        if cfg:
            el = OxmlElement(f"w:{edge}")
            el.set(qn("w:val"),   cfg.get("val",   "single"))
            el.set(qn("w:sz"),    cfg.get("sz",    "4"))
            el.set(qn("w:space"), cfg.get("space", "0"))
            el.set(qn("w:color"), cfg.get("color", "CCCCCC"))
            tcBorders.append(el)
    tcPr.append(tcBorders)

def _para(doc, text: str, bold=False, italic=False, size_pt=11,
          color_hex=None, align=None, space_before=0, space_after=6,
          font="Calibri") -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after  = Pt(space_after)
    if align:
        p.alignment = align
    run = p.add_run(text)
    run.bold   = bold
    run.italic = italic
    run.font.name = font
    run.font.size = Pt(size_pt)
    if color_hex:
        run.font.color.rgb = _rgb(color_hex)
    return p

def _spacer(doc, pts=12):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after  = Pt(pts)

def _h1(doc, text: str):
    """Sectie header niveau 1 — donkerblauw balk."""
    p  = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after  = Pt(4)
    # Onderlijn via paragraphborder
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"),   "single")
    bottom.set(qn("w:sz"),    "8")
    bottom.set(qn("w:space"), "2")
    bottom.set(qn("w:color"), _C_SECONDARY)
    pBdr.append(bottom)
    pPr.append(pBdr)
    run = p.add_run(text)
    run.bold = True
    run.font.name  = "Calibri"
    run.font.size  = Pt(16)
    run.font.color.rgb = _rgb(_C_PRIMARY)
    return p

def _h2(doc, text: str):
    """Sub-sectie header niveau 2."""
    p  = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after  = Pt(3)
    run = p.add_run(text)
    run.bold = True
    run.font.name  = "Calibri"
    run.font.size  = Pt(13)
    run.font.color.rgb = _rgb(_C_SECONDARY)
    return p

def _h3(doc, text: str):
    """Sub-sub-sectie header niveau 3."""
    p  = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after  = Pt(2)
    run = p.add_run(text)
    run.bold = True
    run.font.name  = "Calibri"
    run.font.size  = Pt(11)
    run.font.color.rgb = _rgb(_C_MID_TEXT)
    return p

def _make_table(doc, headers: list, col_widths_cm: list):
    """Maak een opgemaakte tabel met gekleurde header rij."""
    tbl = doc.add_table(rows=1, cols=len(headers))
    tbl.style = "Table Grid"
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT

    # Kolombreedtes
    for i, w in enumerate(col_widths_cm):
        tbl.columns[i].width = Cm(w)

    # Header rij
    hdr_row = tbl.rows[0]
    hdr_row.height = Cm(0.7)
    for i, hdr_text in enumerate(headers):
        cell = hdr_row.cells[i]
        cell.width = Cm(col_widths_cm[i])
        _set_cell_bg(cell, _C_ROW_HEADER)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after  = Pt(0)
        run = p.add_run(hdr_text)
        run.bold = True
        run.font.name  = "Calibri"
        run.font.size  = Pt(9)
        run.font.color.rgb = _rgb(_C_WHITE)
    return tbl

def _add_row(tbl, values: list, col_widths_cm: list, shade=False, small=False):
    """Voeg een rij toe aan een tabel."""
    row = tbl.add_row()
    for i, val in enumerate(values):
        cell = row.cells[i]
        cell.width = Cm(col_widths_cm[i])
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        if shade:
            _set_cell_bg(cell, _C_ROW_ALT)
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after  = Pt(1)
        # Meerdere regels via \n
        lines = str(val).split("\n")
        for li, line in enumerate(lines):
            if li == 0:
                run = p.add_run(line)
            else:
                run = p.add_run("\n" + line)
            run.font.name = "Calibri"
            run.font.size = Pt(8 if small else 9)
            run.font.color.rgb = _rgb(_C_MID_TEXT)
    return row

# ---------------------------------------------------------------------------
# Verbinding label helper
# ---------------------------------------------------------------------------

def _conn_label(data: dict, idx: dict, port_id: str) -> str:
    """Geef het label terug van wat er verbonden is met port_id."""
    for conn in data.get("connections", []):
        other_id = other_type = None
        if conn.get("from_id") == port_id:
            other_id, other_type = conn.get("to_id"), conn.get("to_type")
        elif conn.get("to_id") == port_id:
            other_id, other_type = conn.get("from_id"), conn.get("from_type")
        if not other_id:
            continue
        if other_type in ("port", None):
            p2  = idx["port"].get(other_id)
            dev = idx["dev"].get(p2["device_id"]) if p2 else None
            if p2 and dev:
                side = "F" if p2["side"] == "front" else "B"
                return f"{dev['name']} / {p2['name']} ({side})"
        elif other_type == "wall_outlet":
            wo = idx["wo"].get(other_id)
            if wo:
                return f"🌐 {wo.get('name', other_id)}"
    return "—"

# ---------------------------------------------------------------------------
# Paginaopmaak
# ---------------------------------------------------------------------------

def _set_page_margins(doc, top=2.0, bottom=2.0, left=2.5, right=2.0):
    """Stel paginamarges in (cm)."""
    section = doc.sections[0]
    section.top_margin    = Cm(top)
    section.bottom_margin = Cm(bottom)
    section.left_margin   = Cm(left)
    section.right_margin  = Cm(right)

def _add_header_footer(doc, title: str, version: str):
    """Voeg koptekst en voettekst toe."""
    section = doc.sections[0]

    # Header
    header = section.header
    header.is_linked_to_previous = False
    ht = header.paragraphs[0]
    ht.clear()
    ht.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = ht.add_run(f"Networkmap Creator  |  {title}")
    run.font.name  = "Calibri"
    run.font.size  = Pt(8)
    run.font.color.rgb = _rgb(_C_MUTED)

    # Koptekst-lijn via border
    pPr = ht._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"),   "single")
    bottom.set(qn("w:sz"),    "4")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), _C_ACCENT)
    pBdr.append(bottom)
    pPr.append(pBdr)

    # Footer
    footer = section.footer
    footer.is_linked_to_previous = False
    ft = footer.paragraphs[0]
    ft.clear()
    ft.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_l = ft.add_run(f"Networkmap Creator {version}  |  Gegenereerd op {datetime.date.today().strftime('%d/%m/%Y')}")
    run_l.font.name  = "Calibri"
    run_l.font.size  = Pt(8)
    run_l.font.color.rgb = _rgb(_C_MUTED)

# ---------------------------------------------------------------------------
# Titelblad
# ---------------------------------------------------------------------------

def _build_titlepage(doc, data: dict, version: str):
    """Maak professioneel titelblad."""
    # Verticale witruimte
    for _ in range(4):
        _spacer(doc, 20)

    # Bedrijfsnaam / hoofdtitel
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_after = Pt(6)
    run = p_title.add_run("Networkmap Creator")
    run.bold = True
    run.font.name  = "Calibri"
    run.font.size  = Pt(28)
    run.font.color.rgb = _rgb(_C_PRIMARY)

    # Subtitel
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(4)
    run2 = p_sub.add_run("Netwerkinfrastructuur Rapport")
    run2.font.name  = "Calibri"
    run2.font.size  = Pt(16)
    run2.font.color.rgb = _rgb(_C_SECONDARY)

    # Scheidingslijn
    _spacer(doc, 8)
    p_line = doc.add_paragraph()
    p_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pPr = p_line._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    for edge in ("top", "bottom"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"),   "single")
        el.set(qn("w:sz"),    "12")
        el.set(qn("w:space"), "4")
        el.set(qn("w:color"), _C_ACCENT)
        pBdr.append(el)
    pPr.append(pBdr)
    _spacer(doc, 8)

    # Datum en versie
    p_date = doc.add_paragraph()
    p_date.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_date.paragraph_format.space_after = Pt(4)
    run3 = p_date.add_run(f"Gegenereerd op: {datetime.date.today().strftime('%d %B %Y')}")
    run3.font.name  = "Calibri"
    run3.font.size  = Pt(11)
    run3.font.color.rgb = _rgb(_C_MUTED)

    p_ver = doc.add_paragraph()
    p_ver.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run4 = p_ver.add_run(f"Versie software: {version}")
    run4.font.name  = "Calibri"
    run4.font.size  = Pt(10)
    run4.italic = True
    run4.font.color.rgb = _rgb(_C_MUTED)

    _spacer(doc, 20)

    # Statistieken samenvatting op titelblad
    sites    = data.get("sites", [])
    n_sites  = len(sites)
    n_rooms  = sum(len(s.get("rooms", [])) for s in sites)
    n_racks  = sum(len(r.get("racks", [])) for s in sites for r in s.get("rooms", []))
    n_devs   = len(data.get("devices", []))
    n_ports  = len(data.get("ports", []))
    n_conns  = len(data.get("connections", []))
    n_wo     = sum(len(r.get("wall_outlets", [])) for s in sites for r in s.get("rooms", []))
    n_vlans  = len({p.get("vlan") for p in data.get("ports", []) if p.get("vlan")})

    stats = [
        ("📍 Sites",        str(n_sites)),
        ("🚪 Ruimtes",      str(n_rooms)),
        ("🗄 Racks",        str(n_racks)),
        ("💻 Devices",      str(n_devs)),
        ("⬡ Poorten",      str(n_ports)),
        ("🔗 Verbindingen", str(n_conns)),
        ("🌐 Wandpunten",   str(n_wo)),
        ("🔷 VLANs",        str(n_vlans)),
    ]

    W_STAT = [6.0, 3.0]
    tbl = doc.add_table(rows=0, cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.columns[0].width = Cm(6.0)
    tbl.columns[1].width = Cm(3.0)

    for i, (label, val) in enumerate(stats):
        row = tbl.add_row()
        c0, c1 = row.cells[0], row.cells[1]
        c0.width = Cm(6.0)
        c1.width = Cm(3.0)
        if i % 2 == 0:
            _set_cell_bg(c0, _C_ROW_ALT)
            _set_cell_bg(c1, _C_ROW_ALT)

        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_before = Pt(2)
        p0.paragraph_format.space_after  = Pt(2)
        r0 = p0.add_run(label)
        r0.font.name = "Calibri"
        r0.font.size = Pt(10)
        r0.font.color.rgb = _rgb(_C_MID_TEXT)

        p1 = c1.paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p1.paragraph_format.space_before = Pt(2)
        p1.paragraph_format.space_after  = Pt(2)
        r1 = p1.add_run(val)
        r1.bold = True
        r1.font.name = "Calibri"
        r1.font.size = Pt(10)
        r1.font.color.rgb = _rgb(_C_PRIMARY)

    doc.add_page_break()

# ---------------------------------------------------------------------------
# Samenvatting sectie
# ---------------------------------------------------------------------------

def _build_summary(doc, data: dict, idx: dict):
    """Overzichtspagina met bezettingsgraad per rack."""
    _h1(doc, "📊  Samenvatting")

    sites = data.get("sites", [])
    for site in sites:
        _h2(doc, f"📍  {site['name']}")
        if site.get("location"):
            _para(doc, f"  Locatie: {site['location']}", size_pt=9,
                  color_hex=_C_MUTED, space_after=4)

        for room in site.get("rooms", []):
            n_racks = len(room.get("racks", []))
            n_wo    = len(room.get("wall_outlets", []))
            _h3(doc, f"🚪  {room['name']}")

            parts = []
            if room.get("floor"):  parts.append(f"Verdieping {room['floor']}")
            if room.get("place"):  parts.append(room["place"])
            if parts:
                _para(doc, "  " + "  ·  ".join(parts), size_pt=9,
                      color_hex=_C_MUTED, space_after=4)

            if n_racks:
                W_RACK = [4.0, 2.5, 2.5, 2.5, 2.0]
                tbl = _make_table(doc, ["Rack", "Units", "Bezet", "Vrij", "Bezetting"], W_RACK)
                for ri, rack in enumerate(room.get("racks", [])):
                    total = rack.get("total_units", 42)
                    used  = sum(s.get("units", 1) for s in rack.get("slots", []))
                    free  = total - used
                    pct   = int(used / total * 100) if total else 0
                    bar   = "█" * (pct // 10) + "░" * (10 - pct // 10)
                    _add_row(tbl, [
                        rack["name"],
                        str(total),
                        str(used),
                        str(free),
                        f"{pct}%  {bar}"
                    ], W_RACK, shade=(ri % 2 == 1))

            if n_wo:
                _para(doc, f"  {n_wo} wandpunt(en) geconfigureerd.",
                      size_pt=9, color_hex=_C_MUTED, space_after=4)

    _spacer(doc, 8)

# ---------------------------------------------------------------------------
# Devices sectie
# ---------------------------------------------------------------------------

def _build_devices_section(doc, data: dict, idx: dict):
    """Alle devices per site/ruimte/rack."""
    _h1(doc, "💻  Devices")

    sites = data.get("sites", [])
    for site in sites:
        for room in site.get("rooms", []):
            for rack in room.get("racks", []):
                if not rack.get("slots"):
                    continue
                _h2(doc, f"🗄  {rack['name']}  —  {room['name']}  —  {site['name']}")

                W_DEV = [3.5, 2.5, 2.0, 1.5, 1.5, 2.5]
                tbl = _make_table(doc,
                    ["Device", "Type", "Merk / Model", "IP", "Slot", "Notitie"],
                    W_DEV)

                # Sorteer slots op rack richting
                # Sortering: hoogste rack unit (= laagste u_start) bovenaan
                # zoals weergegeven in de app
                _sorted_slots = sorted(
                    rack.get("slots", []),
                    key=lambda s: (s.get("u_start") or 0),
                    reverse=False
                )
                _type_map = {
                    "switch":           "Switch",
                    "patch_panel":      "Patchpanel",
                    "patchpanel":       "Patchpanel",
                    "cable_management": "Kabelgoot",
                    "server":           "Server",
                    "router":           "Router",
                    "firewall":         "Firewall",
                    "ups":              "UPS",
                    "other":            "Overige",
                }
                for si, slot in enumerate(_sorted_slots):
                    dev = idx["dev"].get(slot.get("device_id", ""))
                    if not dev:
                        continue
                    raw_type   = dev.get("type", "")
                    type_label = _type_map.get(raw_type, raw_type or "—")
                    try:
                        from app.helpers.i18n import t as _t
                        lbl = _t(f"device_{raw_type}")
                        if lbl and not lbl.startswith("["):
                            type_label = lbl
                    except Exception:
                        pass
                    ip_label    = dev.get("ip", "") or "—"
                    note_label  = dev.get("notes", "") or "—"
                    brand_model = " ".join(filter(None, [dev.get("brand",""), dev.get("model","")])) or "—"
                    # slot unit: probeer meerdere veldnamen
                    # Toon echte rack unit positie
                    u_start   = slot.get("u_start")
                    total_u   = rack.get("total_units", 42)
                    if u_start is not None:
                        # u_start is altijd van onderaf geteld (fysieke positie)
                        # Weergave = total_units - u_start + 1 (rack unit label)
                        unit_val = total_u - u_start + 1
                    else:
                        unit_val = "—"
                    _add_row(tbl, [
                        dev["name"],
                        type_label,
                        brand_model,
                        ip_label,
                        str(unit_val),
                        note_label,
                    ], W_DEV, shade=(si % 2 == 1))

                _spacer(doc, 6)

# ---------------------------------------------------------------------------
# Poorten sectie
# ---------------------------------------------------------------------------

def _build_ports_section(doc, data: dict, idx: dict):
    """Poortoverzicht per device met verbindingen."""
    _h1(doc, "⬡  Poortoverzicht")

    sites = data.get("sites", [])
    for site in sites:
        for room in site.get("rooms", []):
            for rack in room.get("racks", []):
                if not rack.get("slots"):
                    continue
                _h2(doc, f"🗄  {rack['name']}  —  {room['name']}")

                for slot in rack.get("slots", []):
                    dev = idx["dev"].get(slot.get("device_id", ""))
                    if not dev:
                        continue

                    ports_front = sorted(
                        [p for p in data.get("ports", [])
                         if p["device_id"] == dev["id"] and p["side"] == "front"],
                        key=lambda p: p["number"]
                    )
                    ports_back = sorted(
                        [p for p in data.get("ports", [])
                         if p["device_id"] == dev["id"] and p["side"] == "back"],
                        key=lambda p: p["number"]
                    )

                    if not ports_front and not ports_back:
                        continue

                    _h3(doc, f"  💻  {dev['name']}")

                    W_PORT = [2.0, 1.5, 1.2, 7.3]
                    tbl = _make_table(doc,
                        ["Poort", "Zijde", "VLAN", "Verbonden met"],
                        W_PORT)

                    all_ports = ports_front + ports_back
                    for pi, port in enumerate(all_ports):
                        side_str = "VOOR" if port["side"] == "front" else "ACHTER"
                        vlan_str = str(port.get("vlan", "")) or "—"
                        dest     = _conn_label(data, idx, port["id"])
                        _add_row(tbl, [
                            port.get("name", f"Port {port['number']}"),
                            side_str,
                            vlan_str,
                            dest,
                        ], W_PORT, shade=(pi % 2 == 1))

                _spacer(doc, 4)

# ---------------------------------------------------------------------------
# Wandpunten sectie
# ---------------------------------------------------------------------------

def _build_outlets_section(doc, data: dict, idx: dict):
    """Alle wandpunten per ruimte."""
    _h1(doc, "🌐  Wandpunten")

    sites = data.get("sites", [])
    for site in sites:
        has_outlets = any(
            room.get("wall_outlets")
            for room in site.get("rooms", [])
        )
        if not has_outlets:
            continue

        _h2(doc, f"📍  {site['name']}")

        for room in site.get("rooms", []):
            outlets = room.get("wall_outlets", [])
            if not outlets:
                continue

            _h3(doc, f"🚪  {room['name']}  ({len(outlets)} wandpunten)")

            W_WO = [2.5, 3.0, 1.5, 2.5, 3.5]
            tbl = _make_table(doc,
                ["Naam", "Locatie", "VLAN", "Endpoint", "Verbonden met"],
                W_WO)

            for wi, wo in enumerate(sorted(outlets, key=lambda w: w.get("name",""))):
                ep = idx["ep"].get(wo.get("endpoint_id", ""))
                ep_name = ep["name"] if ep else "—"
                loc_desc = wo.get("location_description", "") or "—"
                vlan_str = str(wo.get("vlan", "")) or "—"

                # Verbonden met (via connection)
                dest = "—"
                for conn in data.get("connections", []):
                    if conn.get("from_id") == wo["id"] or conn.get("to_id") == wo["id"]:
                        other_id   = conn["to_id"] if conn["from_id"] == wo["id"] else conn["from_id"]
                        other_type = conn["to_type"] if conn["from_id"] == wo["id"] else conn["from_type"]
                        if other_type in ("port", None):
                            p2  = idx["port"].get(other_id)
                            dev = idx["dev"].get(p2["device_id"]) if p2 else None
                            if p2 and dev:
                                side = "F" if p2["side"] == "front" else "B"
                                dest = f"{dev['name']} / {p2['name']} ({side})"
                        break

                _add_row(tbl, [
                    wo.get("name", wo["id"]),
                    loc_desc,
                    vlan_str,
                    ep_name,
                    dest,
                ], W_WO, shade=(wi % 2 == 1))

            _spacer(doc, 6)

# ---------------------------------------------------------------------------
# Verbindingen sectie
# ---------------------------------------------------------------------------

def _build_connections_section(doc, data: dict, idx: dict):
    """Alle verbindingen overzicht."""
    _h1(doc, "🔗  Verbindingen")

    connections = data.get("connections", [])
    if not connections:
        _para(doc, "  Geen verbindingen gevonden.", size_pt=10,
              color_hex=_C_MUTED, italic=True)
        return

    W_CONN = [3.5, 3.5, 2.0, 1.5, 2.5]
    tbl = _make_table(doc,
        ["Van", "Naar", "Kabeltype", "VLAN", "Label / Notitie"],
        W_CONN)

    cable_labels = {
        "utp_cat5e": "UTP Cat5e",
        "utp_cat6":  "UTP Cat6",
        "utp_cat6a": "UTP Cat6a",
        "sfp_fiber": "SFP Fiber",
        "sfp_dac":   "SFP DAC",
        "other":     "Anders",
    }

    for ci, conn in enumerate(connections):
        from_label = _resolve_endpoint(data, idx, conn.get("from_id"), conn.get("from_type","port"))
        to_label   = _resolve_endpoint(data, idx, conn.get("to_id"),   conn.get("to_type","port"))
        cable      = cable_labels.get(conn.get("cable_type",""), conn.get("cable_type","—"))
        note       = conn.get("label") or conn.get("notes") or "—"

        # VLAN via poort
        vlan_str = "—"
        for end_id, end_type in [
            (conn.get("from_id"), conn.get("from_type","port")),
            (conn.get("to_id"),   conn.get("to_type","port")),
        ]:
            if end_type in ("port", None):
                p = idx["port"].get(end_id)
                if p and p.get("vlan"):
                    vlan_str = str(p["vlan"])
                    break

        _add_row(tbl, [
            from_label, to_label, cable, vlan_str, note
        ], W_CONN, shade=(ci % 2 == 1))

    _spacer(doc, 8)

def _resolve_endpoint(data: dict, idx: dict, obj_id: str, obj_type: str) -> str:
    if not obj_id:
        return "—"
    if obj_type in ("port", None, ""):
        p   = idx["port"].get(obj_id)
        dev = idx["dev"].get(p["device_id"]) if p else None
        if p and dev:
            side = "F" if p["side"] == "front" else "B"
            return f"{dev['name']} / {p['name']} ({side})"
    elif obj_type == "wall_outlet":
        wo = idx["wo"].get(obj_id)
        if wo:
            return f"🌐 {wo.get('name', obj_id)}"
    return obj_id

# ---------------------------------------------------------------------------
# VLAN overzicht sectie
# ---------------------------------------------------------------------------

def _build_vlan_section(doc, data: dict, idx: dict):
    """Volledig VLAN overzicht: per VLAN alle poorten en wandpunten."""

    # Laad VLAN configuratie
    vlan_names = {}
    try:
        from app.services import vlan_service
        vlans = vlan_service.load_vlans()
        vlan_names = {v["id"]: v for v in vlans}
    except Exception:
        pass

    # Verzamel alle VLAN nummers via poorten
    vlan_map = {}   # vlan_id → {"ports": [...], "outlets_direct": [...]}
    for p in data.get("ports", []):
        v = p.get("vlan")
        if v:
            try:
                vi = int(v)
            except Exception:
                vi = v
            vlan_map.setdefault(vi, {"ports": [], "outlets_direct": []})
            vlan_map[vi]["ports"].append(p)

    # Wandpunten met direct VLAN
    for site in data.get("sites", []):
        for room in site.get("rooms", []):
            for wo in room.get("wall_outlets", []):
                v = wo.get("vlan")
                if v:
                    try:
                        vi = int(v)
                    except Exception:
                        vi = v
                    vlan_map.setdefault(vi, {"ports": [], "outlets_direct": []})
                    vlan_map[vi]["outlets_direct"].append((wo, room))

    if not vlan_map:
        _h1(doc, "🔷  VLAN Overzicht")
        _para(doc, "  Geen VLAN toewijzingen gevonden.", size_pt=10,
              color_hex=_C_MUTED, italic=True)
        return

    _h1(doc, f"🔷  VLAN Overzicht  ({len(vlan_map)} VLAN's)")

    # Device locatie index
    device_location = {}
    for site in data.get("sites", []):
        for room in site.get("rooms", []):
            for rack in room.get("racks", []):
                for slot in rack.get("slots", []):
                    dev_id = slot.get("device_id")
                    if dev_id:
                        device_location[dev_id] = (site, room, rack)

    for vlan_num in sorted(vlan_map.keys()):
        entry   = vlan_map[vlan_num]
        ports   = entry["ports"]
        outlets_direct = entry["outlets_direct"]

        # VLAN naam uit configuratie
        vlan_cfg  = vlan_names.get(vlan_num, {})
        vlan_name = vlan_cfg.get("name", "")
        vlan_desc = vlan_cfg.get("description", "")

        title = f"VLAN {vlan_num}"
        if vlan_name:
            title += f"  —  {vlan_name}"

        _h2(doc, f"🔷  {title}")

        if vlan_desc:
            _para(doc, f"  {vlan_desc}", size_pt=9,
                  color_hex=_C_MUTED, italic=True, space_after=4)

        n_ports   = len(ports)
        n_outlets = len(outlets_direct)
        _para(doc,
              f"  {n_ports} poort{'en' if n_ports != 1 else ''}  ·  "
              f"{n_outlets} wandpunt{'en' if n_outlets != 1 else ''} direct",
              size_pt=9, color_hex=_C_MUTED, space_after=6)

        # Poorten tabel
        if ports:
            _h3(doc, "  Poorten")
            W_PORT_VLAN = [3.5, 2.0, 1.5, 2.0, 4.0]
            tbl = _make_table(doc,
                ["Device", "Rack / Ruimte", "Poort", "Zijde", "Verbonden met"],
                W_PORT_VLAN)

            for pi, p in enumerate(sorted(ports, key=lambda x: (
                    x.get("device_id",""), x["side"], x["number"]))):
                dev = idx["dev"].get(p["device_id"])
                loc = device_location.get(p["device_id"])
                dev_label  = dev["name"] if dev else p["device_id"]
                loc_label  = "—"
                if loc:
                    _, room_l, rack_l = loc
                    loc_label = f"{rack_l['name']}\n{room_l['name']}"

                side_str = "VOOR" if p["side"] == "front" else "ACHTER"
                dest     = _conn_label(data, idx, p["id"])

                _add_row(tbl, [
                    dev_label,
                    loc_label,
                    p.get("name", f"Port {p['number']}"),
                    side_str,
                    dest,
                ], W_PORT_VLAN, shade=(pi % 2 == 1))

        # Wandpunten via verbinding
        vlan_port_ids = {p["id"] for p in ports}
        outlet_via = []
        for conn in data.get("connections", []):
            outlet_id = port_id = None
            if (conn.get("from_type") in ("port", None)
                    and conn.get("from_id") in vlan_port_ids
                    and conn.get("to_type") == "wall_outlet"):
                outlet_id = conn["to_id"]
                port_id   = conn["from_id"]
            elif (conn.get("to_type") in ("port", None)
                    and conn.get("to_id") in vlan_port_ids
                    and conn.get("from_type") == "wall_outlet"):
                outlet_id = conn["from_id"]
                port_id   = conn["to_id"]
            if outlet_id:
                outlet_via.append((outlet_id, port_id))

        # Wandpunten tabel (via poort + direct)
        all_wo_rows = []
        for outlet_id, port_id in outlet_via:
            wo = room_name = None
            for s in data.get("sites", []):
                for r in s.get("rooms", []):
                    for w in r.get("wall_outlets", []):
                        if w["id"] == outlet_id:
                            wo        = w
                            room_name = f"{r['name']}, {s['name']}"
            p_obj   = idx["port"].get(port_id)
            d_obj   = idx["dev"].get(p_obj["device_id"]) if p_obj else None
            via_lbl = (f"{d_obj['name']} / {p_obj['name']}"
                       if p_obj and d_obj else port_id)
            if wo:
                all_wo_rows.append((
                    wo.get("name", outlet_id),
                    room_name or "—",
                    via_lbl,
                    "Via poort"
                ))

        for wo, room in outlets_direct:
            all_wo_rows.append((
                wo.get("name", wo["id"]),
                f"{room['name']}",
                "—",
                "Direct"
            ))

        if all_wo_rows:
            _h3(doc, "  Wandpunten")
            W_WO_VLAN = [3.0, 3.5, 3.5, 2.0]
            tbl_wo = _make_table(doc,
                ["Wandpunt", "Locatie", "Via poort", "Type"],
                W_WO_VLAN)
            for wi, row_data in enumerate(all_wo_rows):
                _add_row(tbl_wo, list(row_data),
                         W_WO_VLAN, shade=(wi % 2 == 1))

        _spacer(doc, 8)

# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------

def _build_index(data: dict) -> dict:
    """Bouw snelle opzoek-index van alle objecten."""
    idx = {
        "dev":  {d["id"]: d for d in data.get("devices", [])},
        "port": {p["id"]: p for p in data.get("ports",   [])},
        "ep":   {e["id"]: e for e in data.get("endpoints", [])},
        "wo":   {},
    }
    for site in data.get("sites", []):
        for room in site.get("rooms", []):
            for wo in room.get("wall_outlets", []):
                idx["wo"][wo["id"]] = wo
    return idx

# ---------------------------------------------------------------------------
# Hoofd render functie
# ---------------------------------------------------------------------------

def render_report_docx(data: dict, filepath: str) -> tuple[bool, str]:
    """
    Genereer volledig Word rapport.
    Returns: (success: bool, error_message: str)
    """
    try:
        from app import version as _ver
        version = _ver.__version__
    except Exception:
        version = "—"

    try:
        doc = Document()
        _set_page_margins(doc)

        idx = _build_index(data)

        # Sitename voor header
        sites     = data.get("sites", [])
        site_name = sites[0]["name"] if sites else "Netwerk"

        _add_header_footer(doc, site_name, version)

        # 1. Titelblad
        _build_titlepage(doc, data, version)

        # 2. Samenvatting
        _build_summary(doc, data, idx)
        doc.add_page_break()

        # 3. Devices
        _build_devices_section(doc, data, idx)
        doc.add_page_break()

        # 4. Poortoverzicht
        _build_ports_section(doc, data, idx)
        doc.add_page_break()

        # 5. Wandpunten
        _build_outlets_section(doc, data, idx)
        doc.add_page_break()

        # 6. Verbindingen
        _build_connections_section(doc, data, idx)
        doc.add_page_break()

        # 7. VLAN overzicht
        _build_vlan_section(doc, data, idx)

        doc.save(filepath)
        return True, ""

    except Exception as exc:
        import traceback
        return False, traceback.format_exc()


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from app.helpers import settings_storage
    data = settings_storage.load_network_data()
    ok, err = render_report_docx(data, "/tmp/test_rapport.docx")
    print("OK" if ok else f"FOUT: {err}")