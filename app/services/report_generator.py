# =============================================================================
# Networkmap_Creator
# File:    app/services/report_generator.py
# Role:    G3 — Word rapport (.docx) van volledige infrastructuur
# Version: 1.0.0
# Author:  Barremans
# Deps:    python-docx (pip install python-docx)
# =============================================================================

import datetime
from docx import Document
from docx.shared import Pt, RGBColor, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# ---------------------------------------------------------------------------
# Kleuren (als hex-string zonder #)
# ---------------------------------------------------------------------------
_C_DARK_BG    = "1e3a5f"   # donkerblauw — titel/header achtergrond
_C_DARK_TEXT  = "FFFFFF"   # wit — tekst op donker
_C_MID_BG     = "dde8f5"   # lichtblauw — device/sectie header
_C_MID_TEXT   = "1e3a5f"   # donkerblauw — tekst op licht
_C_ROW_ALT    = "f0f4fa"   # zeer lichtblauw — alternerende rij
_C_ROW_NORM   = "FFFFFF"   # wit
_C_BORDER     = "CCCCCC"   # grijs — celrand
_C_MUTED      = "888888"   # grijs — secundaire tekst
_C_EMPTY      = "BBBBBB"   # lichtgrijs — lege U-rijen


# ---------------------------------------------------------------------------
# Hulpfuncties — opmaak
# ---------------------------------------------------------------------------

def _rgb(hex6: str) -> RGBColor:
    r, g, b = int(hex6[0:2], 16), int(hex6[2:4], 16), int(hex6[4:6], 16)
    return RGBColor(r, g, b)


def _set_cell_bg(cell, hex6: str):
    """Celachtergrond instellen via directe XML manipulatie."""
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex6.upper())
    tcPr.append(shd)


def _set_cell_borders(cell):
    """Dunne grijze randen op een cel."""
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"),   "single")
        el.set(qn("w:sz"),    "2")
        el.set(qn("w:color"), _C_BORDER)
        tcBorders.append(el)
    tcPr.append(tcBorders)


def _cell_margins(cell, top=60, bottom=60, left=120, right=120):
    """Cel padding instellen."""
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    mar  = OxmlElement("w:tcMar")
    for side, val in (("top", top), ("bottom", bottom),
                      ("left", left), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"),    str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tcPr.append(mar)


def _add_run(para, text: str, bold=False, italic=False,
             size_pt=10, color_hex=None, font="Arial"):
    run = para.add_run(text)
    run.bold   = bold
    run.italic = italic
    run.font.name = font
    run.font.size = Pt(size_pt)
    if color_hex:
        run.font.color.rgb = _rgb(color_hex)
    return run


def _para(doc_or_cell, text="", bold=False, size_pt=10,
          color_hex="222222", align=None, space_after=4,
          space_before=0, font="Arial"):
    """Voeg een paragraaf toe aan document of cel."""
    if hasattr(doc_or_cell, "add_paragraph"):
        p = doc_or_cell.add_paragraph()
    else:
        p = doc_or_cell.paragraphs[0] if doc_or_cell.paragraphs else doc_or_cell.add_paragraph()

    p.paragraph_format.space_after  = Pt(space_after)
    p.paragraph_format.space_before = Pt(space_before)
    if align:
        p.alignment = align

    if text:
        _add_run(p, text, bold=bold, size_pt=size_pt,
                 color_hex=color_hex, font=font)
    return p


def _heading_para(doc, text: str, level: int):
    """Aangepaste heading — geen built-in stijlen gebruiken voor volledige controle."""
    if level == 1:
        # Site — donkerblauwe balk
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(16)
        p.paragraph_format.space_after  = Pt(6)
        _add_run(p, f"  {text}", bold=True, size_pt=16,
                 color_hex=_C_DARK_TEXT)
        # Achtergrond via XML
        pPr  = p._p.get_or_add_pPr()
        shd  = OxmlElement("w:shd")
        shd.set(qn("w:val"),   "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"),  _C_DARK_BG.upper())
        pPr.append(shd)
        # Linker inspringing
        ind = OxmlElement("w:ind")
        ind.set(qn("w:left"), "0")
        pPr.append(ind)

    elif level == 2:
        # Ruimte — lijngrens onderaan
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after  = Pt(4)
        _add_run(p, text, bold=True, size_pt=13, color_hex=_C_DARK_BG)
        pPr = p._p.get_or_add_pPr()
        pBdr = OxmlElement("w:pBdr")
        bot  = OxmlElement("w:bottom")
        bot.set(qn("w:val"),   "single")
        bot.set(qn("w:sz"),    "6")
        bot.set(qn("w:color"), "2E75B6")
        bot.set(qn("w:space"), "1")
        pBdr.append(bot)
        pPr.append(pBdr)

    elif level == 3:
        # Rack — lichtblauwe achtergrond
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after  = Pt(3)
        _add_run(p, f"  {text}", bold=True, size_pt=11, color_hex=_C_MID_TEXT)
        pPr = p._p.get_or_add_pPr()
        shd  = OxmlElement("w:shd")
        shd.set(qn("w:val"),   "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"),  _C_MID_BG.upper())
        pPr.append(shd)

    return p


def _spacer(doc, pt=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after  = Pt(pt)
    p.paragraph_format.space_before = Pt(0)


def _divider(doc, color="2E75B6"):
    p = doc.add_paragraph()
    p.paragraph_format.space_after  = Pt(4)
    p.paragraph_format.space_before = Pt(0)
    pPr  = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bot  = OxmlElement("w:bottom")
    bot.set(qn("w:val"),   "single")
    bot.set(qn("w:sz"),    "4")
    bot.set(qn("w:color"), color)
    bot.set(qn("w:space"), "1")
    pBdr.append(bot)
    pPr.append(pBdr)


# ---------------------------------------------------------------------------
# Tabel helpers
# ---------------------------------------------------------------------------

def _make_table(doc, headers: list, col_widths_cm: list) -> object:
    """Maak een tabel met header rij."""
    n_cols = len(headers)
    table  = doc.add_table(rows=1, cols=n_cols)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.style     = "Table Grid"

    # Header rij opmaak
    hdr_row = table.rows[0]
    hdr_row.height = Pt(18)
    for i, (cell, hdr) in enumerate(zip(hdr_row.cells, headers)):
        _set_cell_bg(cell, _C_DARK_BG)
        _set_cell_borders(cell)
        _cell_margins(cell, top=60, bottom=60, left=120, right=120)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        _add_run(p, hdr, bold=True, size_pt=9,
                 color_hex=_C_DARK_TEXT)

        # Breedte via XML
        tc   = cell._tc
        tcPr = tc.get_or_add_tcPr()
        tcW  = OxmlElement("w:tcW")
        dxa  = int(col_widths_cm[i] * 567)   # 1 cm = 567 DXA
        tcW.set(qn("w:w"),    str(dxa))
        tcW.set(qn("w:type"), "dxa")
        tcPr.append(tcW)

    return table


def _add_table_row(table, values: list, col_widths_cm: list,
                   shade=False, bold_first=False):
    """Voeg een datarij toe."""
    row = table.add_row()
    row.height = Pt(16)
    bg = _C_ROW_ALT if shade else _C_ROW_NORM

    for i, (cell, val) in enumerate(zip(row.cells, values)):
        _set_cell_bg(cell, bg)
        _set_cell_borders(cell)
        _cell_margins(cell, top=40, bottom=40, left=120, right=120)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        text = str(val) if val is not None else "—"
        _add_run(p, text,
                 bold=(bold_first and i == 0),
                 size_pt=9, color_hex="333333")

        # Breedte
        tc   = cell._tc
        tcPr = tc.get_or_add_tcPr()
        tcW  = OxmlElement("w:tcW")
        dxa  = int(col_widths_cm[i] * 567)
        tcW.set(qn("w:w"),    str(dxa))
        tcW.set(qn("w:type"), "dxa")
        tcPr.append(tcW)


# ---------------------------------------------------------------------------
# Data index opbouwen
# ---------------------------------------------------------------------------

def _build_index(data: dict) -> dict:
    dev_map  = {d["id"]: d for d in data.get("devices", [])}
    port_map = {}
    for p in data.get("ports", []):
        port_map.setdefault(p["device_id"], []).append(p)

    # Slot map: rack_id → {u_start: slot}
    slot_map = {}
    for site in data.get("sites", []):
        for room in site.get("rooms", []):
            for rack in room.get("racks", []):
                slot_map[rack["id"]] = {
                    s["u_start"]: s for s in rack.get("slots", [])
                }

    return {"dev": dev_map, "port": port_map, "slot": slot_map}


def _conn_label(data: dict, idx: dict, port_id: str) -> str:
    """Geef leesbaar label van de andere kant van een verbinding."""
    conn = next(
        (c for c in data.get("connections", [])
         if c.get("from_id") == port_id or c.get("to_id") == port_id),
        None
    )
    if not conn:
        return "—"

    other_id   = conn["to_id"]   if conn["from_id"] == port_id else conn["from_id"]
    other_type = conn["to_type"] if conn["from_id"] == port_id else conn["from_type"]

    if other_type == "port":
        p = next((x for x in data.get("ports", []) if x["id"] == other_id), None)
        d = idx["dev"].get(p["device_id"]) if p else None
        if p and d:
            side = "VOOR" if p["side"] == "front" else "ACHTER"
            return f"{d['name']} — {p['name']} ({side})"

    elif other_type == "wall_outlet":
        for site in data.get("sites", []):
            for room in site.get("rooms", []):
                for wo in room.get("wall_outlets", []):
                    if wo["id"] == other_id:
                        return f"🌐  {wo['name']}  ({room['name']})"

    return other_id


def _outlet_conn_label(data: dict, idx: dict, outlet_id: str) -> str:
    """Geef leesbaar label van de aansluiting van een wandpunt."""
    conn = next(
        (c for c in data.get("connections", [])
         if (c.get("from_id") == outlet_id) or (c.get("to_id") == outlet_id)),
        None
    )
    if not conn:
        return "— geen verbinding"

    port_id = (conn["from_id"] if conn.get("from_type") == "port"
               else conn["to_id"])
    p = next((x for x in data.get("ports", []) if x["id"] == port_id), None)
    d = idx["dev"].get(p["device_id"]) if p else None
    if p and d:
        side = "VOOR" if p["side"] == "front" else "ACHTER"
        return f"{d['name']} — {p['name']} ({side})"
    return "— onbekend"


_CABLE_LABELS = {
    "utp_cat5e":  "UTP Cat5e",
    "utp_cat6":   "UTP Cat6",
    "utp_cat6a":  "UTP Cat6a",
    "fiber_sm":   "Glasvezel SM",
    "fiber_mm":   "Glasvezel MM",
    "dak":        "DAK kabel",
    "other":      "Ander",
}


# ---------------------------------------------------------------------------
# Hoofd-exportfunctie
# ---------------------------------------------------------------------------

def render_report_docx(data: dict, filepath: str) -> tuple[bool, str]:
    """
    G3 — Exporteer volledige infrastructuur als Word document.
    Retourneert (ok: bool, foutmelding: str).
    """
    try:
        _build_docx(data, filepath)
        return (True, "")
    except Exception as e:
        import traceback
        return (False, f"{e}\n{traceback.format_exc()}")


def _build_docx(data: dict, filepath: str):
    doc = Document()
    idx = _build_index(data)

    # ── Pagina instellingen ──────────────────────────────────────────────────
    section = doc.sections[0]
    section.page_width    = Cm(21.0)
    section.page_height   = Cm(29.7)
    section.left_margin   = Cm(2.0)
    section.right_margin  = Cm(2.0)
    section.top_margin    = Cm(2.0)
    section.bottom_margin = Cm(2.0)

    datum = datetime.date.today().strftime("%d/%m/%Y")

    # ── Koptekst ─────────────────────────────────────────────────────────────
    header_p = doc.sections[0].header.paragraphs[0]
    _add_run(header_p, "Networkmap Creator  —  Infrastructuurrapport",
             size_pt=8, color_hex=_C_MUTED)
    _add_run(header_p, f"\t{datum}", size_pt=8, color_hex=_C_MUTED)
    header_p.paragraph_format.space_after = Pt(4)

    # Tab stop rechts voor datum
    pPr  = header_p._p.get_or_add_pPr()
    tabs = OxmlElement("w:tabs")
    tab  = OxmlElement("w:tab")
    tab.set(qn("w:val"), "right")
    tab.set(qn("w:pos"), "9639")   # ~17 cm content breedte
    tabs.append(tab)
    pPr.append(tabs)
    _divider(doc.sections[0].header, "CCCCCC")

    # ── Titelpagina ──────────────────────────────────────────────────────────
    _spacer(doc, 60)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(6)
    _add_run(title, "Networkmap Creator", bold=True, size_pt=28,
             color_hex=_C_DARK_BG)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.paragraph_format.space_after = Pt(4)
    _add_run(sub, "Infrastructuurrapport", size_pt=18, color_hex=_C_MUTED)

    _divider(doc, "2E75B6")

    dt_p = doc.add_paragraph()
    dt_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    dt_p.paragraph_format.space_after = Pt(24)
    _add_run(dt_p, f"Gegenereerd op: {datum}", size_pt=10, color_hex=_C_MUTED)

    # Samenvatting
    total_sites   = len(data.get("sites", []))
    total_rooms   = sum(len(s.get("rooms", [])) for s in data.get("sites", []))
    total_racks   = sum(len(r.get("racks", [])) for s in data.get("sites", [])
                        for r in s.get("rooms", []))
    total_devices = len(data.get("devices", []))
    total_outlets = sum(len(r.get("wall_outlets", [])) for s in data.get("sites", [])
                        for r in s.get("rooms", []))
    total_conns   = len(data.get("connections", []))

    sum_tbl = doc.add_table(rows=2, cols=3)
    sum_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    labels = ["Sites", "Ruimtes", "Racks", "Devices", "Wandpunten", "Verbindingen"]
    vals   = [total_sites, total_rooms, total_racks,
              total_devices, total_outlets, total_conns]
    W_SUM  = [3.0, 3.0, 3.0]
    for row_i, row in enumerate(sum_tbl.rows):
        for col_i, cell in enumerate(row.cells):
            idx_v = row_i * 3 + col_i
            _set_cell_bg(cell, _C_DARK_BG if row_i == 0 else _C_MID_BG)
            _set_cell_borders(cell)
            _cell_margins(cell, top=100, bottom=100, left=160, right=160)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if row_i == 0:
                _add_run(p, labels[idx_v], bold=True, size_pt=9,
                         color_hex=_C_DARK_TEXT)
            else:
                _add_run(p, str(vals[idx_v]), bold=True, size_pt=14,
                         color_hex=_C_MID_TEXT)
            tc   = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcW  = OxmlElement("w:tcW")
            dxa  = int(W_SUM[col_i] * 567)
            tcW.set(qn("w:w"),    str(dxa))
            tcW.set(qn("w:type"), "dxa")
            tcPr.append(tcW)

    # ── Per site ─────────────────────────────────────────────────────────────
    for site in data.get("sites", []):
        _spacer(doc, 16)
        _heading_para(doc, f"📍  {site['name']}", level=1)

        info_parts = []
        if site.get("location"):
            info_parts.append(f"Locatie: {site['location']}")
        n_rooms = len(site.get("rooms", []))
        info_parts.append(f"{n_rooms} ruimte{'s' if n_rooms != 1 else ''}")
        _para(doc, "  ".join(info_parts), size_pt=9, color_hex=_C_MUTED,
              space_after=6)

        for room in site.get("rooms", []):
            _heading_para(doc, f"🚪  {room['name']}", level=2)

            rinfo = []
            if room.get("floor"):
                rinfo.append(f"Verdiep: {room['floor']}")
            if room.get("place"):
                rinfo.append(f"Plaats: {room['place']}")
            if rinfo:
                _para(doc, "  ·  ".join(rinfo), size_pt=9,
                      color_hex=_C_MUTED, space_after=4)

            # ── Racks ────────────────────────────────────────────────────────
            for rack in room.get("racks", []):
                _heading_para(doc,
                    f"🗄  {rack['name']}  ({rack['total_units']}U)",
                    level=3)

                slot_by_u = idx["slot"].get(rack["id"], {})
                u = 1
                while u <= rack["total_units"]:
                    slot = slot_by_u.get(u)
                    if slot:
                        dev    = idx["dev"].get(slot.get("device_id", ""))
                        height = slot.get("height", 1)
                        if dev:
                            # Device label
                            p = doc.add_paragraph()
                            p.paragraph_format.space_before = Pt(5)
                            p.paragraph_format.space_after  = Pt(2)
                            p.paragraph_format.left_indent  = Cm(0.5)
                            _add_run(p,
                                f"U{str(u).zfill(2)}",
                                bold=True, size_pt=10, color_hex="2E75B6")
                            _add_run(p,
                                f"  {dev['name']}",
                                bold=True, size_pt=10, color_hex=_C_DARK_BG)
                            _add_run(p,
                                f"  [{dev.get('type', '')}]",
                                size_pt=9, color_hex=_C_MUTED)

                            # Poorttabel
                            ports = sorted(
                                idx["port"].get(dev["id"], []),
                                key=lambda p: (p["side"], p["number"])
                            )
                            if ports:
                                W_PORT = [1.0, 2.5, 1.5, 12.0 - 1.0 - 2.5 - 1.5]
                                tbl = _make_table(doc,
                                    ["#", "Naam", "Zijde", "Verbonden met"],
                                    W_PORT)
                                for pi, port in enumerate(ports):
                                    dest = _conn_label(data, idx, port["id"])
                                    side = "VOOR" if port["side"] == "front" else "ACHTER"
                                    _add_table_row(tbl, [
                                        str(port["number"]),
                                        port["name"],
                                        side,
                                        dest
                                    ], W_PORT, shade=(pi % 2 == 1))
                                _spacer(doc, 4)
                            else:
                                _para(doc, "    (geen poorten)",
                                      size_pt=9, color_hex=_C_EMPTY,
                                      space_after=3)
                        u += height
                    else:
                        p = doc.add_paragraph()
                        p.paragraph_format.space_after  = Pt(1)
                        p.paragraph_format.space_before = Pt(0)
                        p.paragraph_format.left_indent  = Cm(0.5)
                        _add_run(p, f"U{str(u).zfill(2)}  —  leeg",
                                 size_pt=8, color_hex=_C_EMPTY)
                        u += 1

                _spacer(doc, 6)

            # ── Wandpunten ───────────────────────────────────────────────────
            outlets = room.get("wall_outlets", [])
            if outlets:
                _para(doc,
                    f"  🌐  Wandpunten  ({len(outlets)})",
                    bold=True, size_pt=11, color_hex=_C_MID_TEXT,
                    space_before=8, space_after=3)
                W_WO = [2.5, 4.0, 12.0 - 2.5 - 4.0]
                tbl  = _make_table(doc,
                    ["Naam", "Locatie", "Aansluiting"],
                    W_WO)
                for wi, wo in enumerate(outlets):
                    _add_table_row(tbl, [
                        wo.get("name", wo["id"]),
                        wo.get("location_description", "—"),
                        _outlet_conn_label(data, idx, wo["id"])
                    ], W_WO, shade=(wi % 2 == 1))
                _spacer(doc, 8)

    # ── Verbindingsoverzicht ─────────────────────────────────────────────────
    _spacer(doc, 16)
    _heading_para(doc, "🔗  Verbindingsoverzicht", level=1)
    conns = data.get("connections", [])
    _para(doc, f"  Totaal: {len(conns)} verbindingen",
          size_pt=9, color_hex=_C_MUTED, space_after=6)

    if conns:
        W_CONN = [4.0, 0.8, 4.0, 3.2]
        tbl    = _make_table(doc,
            ["Van", "→", "Naar", "Kabeltype"],
            W_CONN)

        for ci, conn in enumerate(conns):
            # Van
            if conn.get("from_type") == "port":
                p = next((x for x in data.get("ports", [])
                          if x["id"] == conn["from_id"]), None)
                d = idx["dev"].get(p["device_id"]) if p else None
                from_label = (f"{d['name']} — {p['name']}"
                              if p and d else conn["from_id"])
            else:
                from_label = "—"
                for site in data.get("sites", []):
                    for room in site.get("rooms", []):
                        for wo in room.get("wall_outlets", []):
                            if wo["id"] == conn.get("from_id"):
                                from_label = f"🌐  {wo['name']}"

            # Naar
            if conn.get("to_type") == "port":
                p = next((x for x in data.get("ports", [])
                          if x["id"] == conn["to_id"]), None)
                d = idx["dev"].get(p["device_id"]) if p else None
                to_label = (f"{d['name']} — {p['name']}"
                            if p and d else conn["to_id"])
            elif conn.get("to_type") == "wall_outlet":
                to_label = "—"
                for site in data.get("sites", []):
                    for room in site.get("rooms", []):
                        for wo in room.get("wall_outlets", []):
                            if wo["id"] == conn.get("to_id"):
                                to_label = f"🌐  {wo['name']}"
            else:
                to_label = conn.get("to_id", "—")

            cable = _CABLE_LABELS.get(conn.get("cable_type", ""), conn.get("cable_type", "—"))
            _add_table_row(tbl,
                [from_label, "→", to_label, cable],
                W_CONN, shade=(ci % 2 == 1))

    # ── Opslaan ──────────────────────────────────────────────────────────────
    doc.save(filepath)


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json, sys
    if len(sys.argv) < 3:
        print("Gebruik: python report_generator.py data.json output.docx")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        d = json.load(f)
    ok, err = render_report_docx(d, sys.argv[2])
    if ok:
        print(f"OK: {sys.argv[2]}")
    else:
        print(f"FOUT: {err}")
        sys.exit(1)