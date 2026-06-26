# =============================================================================
# Networkmap_Creator
# File:    app/services/export_renderer.py
# Role:    G1/G2 — QPainter renderer voor rack + wandpunten export
#          Genereert QImage (PNG/JPG) en PDF volledig vanuit data,
#          onafhankelijk van de UI / schermweergave.
# Version: 1.6.0
# Author:  Barremans
# Changes: 1.6.0 — FloorplanRenderer respecteert SVG-oriëntatie.
#                  _IMG_W/_IMG_H zijn nu instantievariabelen berekend via
#                  de SVG viewBox. Portret-SVG → portret PNG (1754×2480px);
#                  landscape-SVG → landscape PNG (2480×1754px, ongewijzigd).
#                  _SVG_MAX_H aangepast voor portret.
#          1.5.0 — Kaartjes gebruiken setPointSize() ipv setPixelSize()
#                   _fp_font_pt() + _fp_draw_pt() toegevoegd voor geschaald canvas
#                   Fontgroottes: labels 9pt, data 10pt, badge 13pt, secties 9pt
#          1.4.0 — Kaartjes volledige A4-breedte, 1 per rij
#                   Fontgrootte 15px data, 13px labels
#                   Eindapparaat: merk, model, notities toegevoegd
#                   Eindapparaat 2-koloms layout in ep-kaartje
#                   Constanten voor alle font- en kaartje-afmetingen
#          1.3.0 — Pagina's 2/3/5 verwijderd — PDF heeft nu 2 pagina's
#                   Pagina 1: grondplan, Pagina 2: gekoppelde kaartjes
#                   Badge header toont svg_pt + type + objectnaam
#                   Locatie wandpunt via get_outlet_location_label()
#          1.2.0 — G-OPEN-8: FloorplanRenderer volledig herschreven
#                   PDF heeft vaste 5-paginastructuur per grondplan:
#                     Pagina 1: SVG grondplan + overlays + legenda
#                     Pagina 2: Alle wandpunten van de site
#                     Pagina 3: Alle devices van de site
#                     Pagina 4: Gekoppelde wandpunten / devices
#                     Pagina 5: Niet-gekoppelde wandpunten / devices
#                   PNG: enkel pagina 1
#                   render_pdf_pages() via QPrinter
#          1.1.0 — G-OPEN-8: FloorplanRenderer initieel toegevoegd
# =============================================================================

import datetime
from PySide6.QtCore  import Qt, QRect, QPoint, QSize
from PySide6.QtGui   import (
    QPainter, QImage, QColor, QFont, QFontMetrics,
    QPen, QBrush, QPainterPath
)
from PySide6.QtPrintSupport import QPrinter

from app.helpers.i18n import t
from app.helpers.settings_storage import get_all_sites
from app.services     import tracing

# ---------------------------------------------------------------------------
# Constanten — afmetingen in pixels (300 dpi equivalent voor hoge kwaliteit)
# ---------------------------------------------------------------------------

_SCALE       = 2          # 2x voor hoge resolutie output
_MARGIN      = 40 * _SCALE
_UNIT_H      = 28 * _SCALE
_PORT_SIZE   = 10 * _SCALE
_PORT_GAP    = 3  * _SCALE
_MAX_PRT_ROW = 12
_PAGE_W      = 1240 * _SCALE   # A4 landscape ~297mm @ 96dpi × scale
_COL_W       = 900 * _SCALE    # Breedte van het rack diagram
_TABLE_ROW_H = 20 * _SCALE

# ---------------------------------------------------------------------------
# Kleurenpalet
# ---------------------------------------------------------------------------

_C_BG          = QColor("#1e1e2e")
_C_HEADER_BG   = QColor("#2a2a3e")
_C_UNIT_EMPTY  = QColor("#252535")
_C_UNIT_DEV    = QColor("#2d3250")
_C_PORT_FRONT  = QColor("#4a9eff")
_C_PORT_BACK   = QColor("#ff9f43")
_C_PORT_CONN   = QColor("#2ecc71")
_C_PORT_LINE   = QColor("#2ecc71")
_C_TEXT_MAIN   = QColor("#e8e8f0")
_C_TEXT_SUB    = QColor("#8888aa")
_C_TEXT_TABLE  = QColor("#c8c8e0")
_C_BORDER      = QColor("#3a3a5e")
_C_TABLE_ALT   = QColor("#252538")
_C_TABLE_HDR   = QColor("#2a2a4e")

# ---------------------------------------------------------------------------
# Hulpfuncties
# ---------------------------------------------------------------------------

def _font(size: int, bold: bool = False) -> QFont:
    f = QFont("Consolas", size * _SCALE // 2)
    f.setBold(bold)
    return f


def _fp_font(size_px: int, bold: bool = False) -> QFont:
    """
    Font voor FloorplanRenderer header — setPixelSize() zodat QPainter.scale()
    het font NIET vergroot. Alleen gebruiken voor tekst buiten de printer-schaling.
    """
    f = QFont("Arial")
    f.setPixelSize(size_px)
    f.setBold(bold)
    return f


def _fp_font_pt(size_pt: int, bold: bool = False) -> QFont:
    """
    Font voor kaartjes op het geschaalde printer-canvas.
    setPointSize() schaalt mee met QPainter.scale() → correcte grootte op papier.
    Verhouding: 1pt ≈ 1/72 inch; A4 landscape = 297mm breed ≈ 842pt.
    Canvas _IMG_W = 4960px → schaal ≈ 842/4960 ≈ 0.17 pt/px.
    size_pt waarden: 8=klein, 10=normaal, 12=groot, 14=titel
    """
    f = QFont("Arial")
    f.setPointSize(size_pt)
    f.setBold(bold)
    return f


def _fp_draw_text(p: "QPainter", rect: "QRect", text: str, color: "QColor",
                  size_px: int = 18, bold: bool = False,
                  align=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft):
    """_draw_text voor header (buiten printer-schaling) — pixel-font."""
    p.setFont(_fp_font(size_px, bold))
    p.setPen(color)
    p.drawText(rect, align, text)


def _fp_draw_pt(p: "QPainter", rect: "QRect", text: str, color: "QColor",
                size_pt: int = 10, bold: bool = False,
                align=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft):
    """_draw_text voor kaartjes op geschaald printer-canvas — point-font."""
    p.setFont(_fp_font_pt(size_pt, bold))
    p.setPen(color)
    p.drawText(rect, align, text)


def _draw_text(p: QPainter, rect: QRect, text: str, color: QColor,
               size: int = 8, bold: bool = False,
               align=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft):
    p.setFont(_font(size, bold))
    p.setPen(color)
    p.drawText(rect, align, text)


def _connected_ports(data: dict) -> set:
    s = set()
    for c in data.get("connections", []):
        if c.get("from_type") == "port":
            s.add(c["from_id"])
        if c.get("to_type") == "port":
            s.add(c["to_id"])
    return s


def _port_label(data: dict, port_id: str) -> str:
    """Geeft een leesbaar label voor de bestemming van een poort verbinding."""
    conn = next(
        (c for c in data.get("connections", [])
         if c.get("from_id") == port_id or c.get("to_id") == port_id),
        None
    )
    if not conn:
        return ""

    other_id   = conn["to_id"]   if conn["from_id"] == port_id else conn["from_id"]
    other_type = conn["to_type"] if conn["from_id"] == port_id else conn["from_type"]

    if other_type == "port":
        port = next((p for p in data.get("ports", []) if p["id"] == other_id), None)
        dev  = next((d for d in data.get("devices", [])
                     if d["id"] == port["device_id"]), None) if port else None
        if port and dev:
            return f"{dev['name']} — {port['name']} ({port.get('side','').upper()})"
        return other_id

    if other_type == "wall_outlet":
        for site in get_all_sites(data):
            for room in site.get("rooms", []):
                for wo in room.get("wall_outlets", []):
                    if wo["id"] == other_id:
                        return f"🌐 {wo['name']}  ({room['name']})"
        return other_id

    return other_id


# ===========================================================================
# RACK RENDERER
# ===========================================================================

class RackRenderer:
    """
    Tekent één rack volledig via QPainter.

    Sectie 1: Visueel rack diagram
      - U-rijen met device blokken
      - Poortblokjes (front=blauw, back=oranje, verbonden=groen)
      - Verbindingslijnen tussen verbonden poorten

    Sectie 2: Aansluitingstabel
      - Per device: poort | zijde | verbonden met
      - Alternerend gekleurde rijen
    """

    def __init__(self, rack: dict, room: dict, site: dict, data: dict):
        self._rack = rack
        self._room = room
        self._site = site
        self._data = data

        self._dev_map   = {d["id"]: d for d in data.get("devices", [])}
        self._port_map  = {}
        for p in data.get("ports", []):
            self._port_map.setdefault(p["device_id"], []).append(p)
        self._conn_ports = _connected_ports(data)

        # slot_map: u_start → slot
        self._slot_map = {s["u_start"]: s for s in rack.get("slots", [])}

    # ------------------------------------------------------------------
    # Publieke entry points
    # ------------------------------------------------------------------

    def render_image(self) -> QImage:
        """Retourneert een QImage met volledig getekend rack."""
        h = self._calc_total_height()
        img = QImage(QSize(_PAGE_W, h), QImage.Format.Format_ARGB32)
        img.fill(_C_BG)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw(p, 0)
        p.end()
        return img

    def render_to_painter(self, p: QPainter, y_offset: int = 0) -> int:
        """Tekent op een bestaande QPainter. Geeft nieuwe y terug."""
        return self._draw(p, y_offset)

    # ------------------------------------------------------------------
    # Layout berekening
    # ------------------------------------------------------------------

    def _calc_total_height(self) -> int:
        total_u    = self._rack.get("total_units", 12)
        diag_h     = _MARGIN + 60 * _SCALE + total_u * _UNIT_H + _MARGIN
        table_h    = self._calc_table_height()
        return diag_h + _MARGIN + table_h + _MARGIN

    def _calc_table_height(self) -> int:
        rows = 1  # header
        for slot in self._rack.get("slots", []):
            dev = self._dev_map.get(slot.get("device_id", ""))
            if dev:
                ports = self._port_map.get(dev["id"], [])
                rows += max(len(ports), 1) + 1  # ports + device header rij
        return rows * _TABLE_ROW_H + 60 * _SCALE

    # ------------------------------------------------------------------
    # Tekenen
    # ------------------------------------------------------------------

    def _draw(self, p: QPainter, y: int) -> int:
        y = self._draw_header(p, y)
        y = self._draw_rack_diagram(p, y)
        y += _MARGIN
        y = self._draw_table(p, y)
        return y

    def _draw_header(self, p: QPainter, y: int) -> int:
        """Header: site / ruimte / rack naam + datum."""
        rect = QRect(_MARGIN, y + _MARGIN, _PAGE_W - 2 * _MARGIN, 40 * _SCALE)

        title = (f"{self._rack['name']}  —  "
                 f"{self._room['name']}  —  "
                 f"{self._site['name']}")
        _draw_text(p, rect, title, _C_TEXT_MAIN, size=14, bold=True,
                   align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        datum = datetime.date.today().strftime("%d/%m/%Y")
        sub   = f"{self._rack.get('total_units', 0)}U  ·  {datum}"
        _draw_text(p, rect, sub, _C_TEXT_SUB, size=9,
                   align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        y += _MARGIN + 40 * _SCALE

        # Scheidingslijn
        p.setPen(QPen(_C_BORDER, 1 * _SCALE))
        p.drawLine(_MARGIN, y, _PAGE_W - _MARGIN, y)
        return y + 8 * _SCALE

    def _draw_rack_diagram(self, p: QPainter, y: int) -> int:
        """Tekent het visuele rack — U-rijen + poorten + verbindingslijnen."""
        total_u  = self._rack.get("total_units", 12)
        rack_x   = _MARGIN
        rack_w   = _COL_W
        num_w    = 30 * _SCALE
        port_rects: dict[str, QRect] = {}  # port_id → center QPoint voor lijnen

        u = 1
        while u <= total_u:
            row_y = y + (u - 1) * _UNIT_H
            if u in self._slot_map:
                slot   = self._slot_map[u]
                device = self._dev_map.get(slot.get("device_id", ""))
                height = slot.get("height", 1)
                if device:
                    rects = self._draw_device_row(
                        p, rack_x, row_y, num_w, rack_w,
                        u, device, height
                    )
                    port_rects.update(rects)
                    u += height
                    continue
            self._draw_empty_row(p, rack_x, row_y, num_w, rack_w, u)
            u += 1

        y += total_u * _UNIT_H

        # Verbindingslijnen tussen verbonden poorten in dit rack
        self._draw_connection_lines(p, port_rects)

        return y

    def _draw_empty_row(self, p: QPainter, x: int, y: int,
                        num_w: int, rack_w: int, u_num: int):
        rect = QRect(x, y, rack_w, _UNIT_H - 1)
        p.fillRect(rect, _C_UNIT_EMPTY)
        p.setPen(QPen(_C_BORDER, 1))
        p.drawRect(rect)
        _draw_text(p, QRect(x + 2, y, num_w, _UNIT_H),
                   str(u_num), _C_TEXT_SUB, size=7,
                   align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def _draw_device_row(self, p: QPainter, x: int, y: int,
                         num_w: int, rack_w: int,
                         u_num: int, device: dict, height: int) -> dict:
        """Tekent één device rij. Retourneert {port_id: center_QPoint}."""
        h     = _UNIT_H * height
        rect  = QRect(x, y, rack_w, h - 1)
        p.fillRect(rect, _C_UNIT_DEV)
        p.setPen(QPen(_C_BORDER, 1))
        p.drawRect(rect)

        # U-nummer
        _draw_text(p, QRect(x + 2, y, num_w, h),
                   str(u_num), _C_TEXT_SUB, size=7,
                   align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        ports     = self._port_map.get(device["id"], [])
        front_pts = [p2 for p2 in ports if p2["side"] == "front"]
        back_pts  = [p2 for p2 in ports if p2["side"] == "back"]

        port_rects = {}
        cursor_x   = x + num_w + 6 * _SCALE

        # Front poorten
        if device.get("front_ports", 0) > 0:
            rects, cursor_x = self._draw_port_block(
                p, cursor_x, y, h, front_pts, "front",
                device["front_ports"]
            )
            port_rects.update(rects)

        # Device naam + type (midden)
        label_x = cursor_x
        label_w = rack_w - (cursor_x - x) - 200 * _SCALE
        dev_type = device.get("type", "")
        _draw_text(p, QRect(label_x, y, label_w, h // 2),
                   device.get("name", ""), _C_TEXT_MAIN, size=8, bold=True,
                   align=Qt.AlignmentFlag.AlignCenter)
        _draw_text(p, QRect(label_x, y + h // 2, label_w, h // 2),
                   t(f"device_{dev_type}"), _C_TEXT_SUB, size=7,
                   align=Qt.AlignmentFlag.AlignCenter)
        cursor_x = label_x + label_w

        # Back poorten
        if device.get("back_ports", 0) > 0:
            rects, cursor_x = self._draw_port_block(
                p, cursor_x, y, h, back_pts, "back",
                device["back_ports"]
            )
            port_rects.update(rects)

        return port_rects

    def _draw_port_block(self, p: QPainter, x: int, row_y: int, row_h: int,
                         ports: list, side: str, total: int):
        """Tekent een blok poorten. Retourneert ({port_id: center}, nieuwe x)."""
        port_by_num = {pt["number"]: pt for pt in ports}
        numbers     = list(range(1, total + 1))
        rows        = [numbers[i:i + _MAX_PRT_ROW]
                       for i in range(0, len(numbers), _MAX_PRT_ROW)]

        block_w = (_PORT_SIZE + _PORT_GAP) * _MAX_PRT_ROW
        port_rects = {}

        for r_idx, row_nums in enumerate(rows):
            row_top = row_y + (row_h - len(rows) * (_PORT_SIZE + _PORT_GAP)) // 2 \
                      + r_idx * (_PORT_SIZE + _PORT_GAP)
            for c_idx, num in enumerate(row_nums):
                px = x + c_idx * (_PORT_SIZE + _PORT_GAP)
                py = row_top
                pt = port_by_num.get(num)
                pid = pt["id"] if pt else None

                if pid and pid in self._conn_ports:
                    color = _C_PORT_CONN
                elif side == "front":
                    color = _C_PORT_FRONT
                else:
                    color = _C_PORT_BACK

                p.fillRect(QRect(px, py, _PORT_SIZE, _PORT_SIZE), color)
                p.setPen(QPen(_C_BORDER, 1))
                p.drawRect(QRect(px, py, _PORT_SIZE, _PORT_SIZE))

                if pid:
                    center = QPoint(px + _PORT_SIZE // 2, py + _PORT_SIZE // 2)
                    port_rects[pid] = center

        new_x = x + block_w + 8 * _SCALE
        return port_rects, new_x

    def _draw_connection_lines(self, p: QPainter, port_rects: dict):
        """Teken verbindingslijnen tussen verbonden poorten die beide in dit rack zitten."""
        drawn = set()
        pen = QPen(_C_PORT_LINE, 1 * _SCALE, Qt.PenStyle.DotLine)
        p.setPen(pen)

        for conn in self._data.get("connections", []):
            if conn.get("from_type") != "port" or conn.get("to_type") != "port":
                continue
            fid = conn["from_id"]
            tid = conn["to_id"]
            if fid not in port_rects or tid not in port_rects:
                continue
            key = tuple(sorted([fid, tid]))
            if key in drawn:
                continue
            drawn.add(key)

            a = port_rects[fid]
            b = port_rects[tid]

            # Bezier curve voor mooiere lijn
            path = QPainterPath()
            path.moveTo(a)
            mid_x = (a.x() + b.x()) // 2
            path.cubicTo(
                QPoint(mid_x, a.y()),
                QPoint(mid_x, b.y()),
                b
            )
            p.drawPath(path)

    def _draw_table(self, p: QPainter, y: int) -> int:
        """Aansluitingstabel: per device alle poorten met bestemming."""
        # Tabel header
        _draw_text(p,
                   QRect(_MARGIN, y, _PAGE_W - 2 * _MARGIN, 28 * _SCALE),
                   t("export_table_title"), _C_TEXT_MAIN, size=10, bold=True)
        y += 32 * _SCALE

        # Kolombreedtes
        col_x    = _MARGIN
        col_port = 160 * _SCALE
        col_side = 80  * _SCALE
        col_dest = _PAGE_W - 2 * _MARGIN - col_port - col_side

        # Tabelkop
        p.fillRect(QRect(col_x, y, _PAGE_W - 2 * _MARGIN, _TABLE_ROW_H), _C_TABLE_HDR)
        _draw_text(p, QRect(col_x + 4, y, col_port, _TABLE_ROW_H),
                   t("export_col_port"), _C_TEXT_MAIN, size=8, bold=True)
        _draw_text(p, QRect(col_x + col_port + 4, y, col_side, _TABLE_ROW_H),
                   t("export_col_side"), _C_TEXT_MAIN, size=8, bold=True)
        _draw_text(p, QRect(col_x + col_port + col_side + 4, y, col_dest, _TABLE_ROW_H),
                   t("export_col_dest"), _C_TEXT_MAIN, size=8, bold=True)
        y += _TABLE_ROW_H

        alt = False
        for slot in self._rack.get("slots", []):
            dev = self._dev_map.get(slot.get("device_id", ""))
            if not dev:
                continue

            # Device header rij
            p.fillRect(QRect(col_x, y, _PAGE_W - 2 * _MARGIN, _TABLE_ROW_H),
                       _C_UNIT_DEV)
            dev_type = dev.get("type", "")
            _draw_text(p,
                       QRect(col_x + 4, y, _PAGE_W - 2 * _MARGIN - 8, _TABLE_ROW_H),
                       f"  {dev['name']}  [{t(f'device_{dev_type}')}]  "
                       f"U{slot.get('u_start', '?')}",
                       _C_TEXT_MAIN, size=8, bold=True)
            y += _TABLE_ROW_H

            ports = sorted(self._port_map.get(dev["id"], []),
                           key=lambda pt: (pt.get("side", ""), pt.get("number", 0)))
            for pt in ports:
                bg = _C_TABLE_ALT if alt else _C_BG
                p.fillRect(QRect(col_x, y, _PAGE_W - 2 * _MARGIN, _TABLE_ROW_H), bg)
                alt = not alt

                dest = _port_label(self._data, pt["id"])
                side_lbl = t(f"label_{pt.get('side', '')}")

                _draw_text(p, QRect(col_x + 16, y, col_port, _TABLE_ROW_H),
                           pt.get("name", ""), _C_TEXT_TABLE, size=7)
                _draw_text(p, QRect(col_x + col_port + 4, y, col_side, _TABLE_ROW_H),
                           side_lbl, _C_TEXT_SUB, size=7)
                _draw_text(p, QRect(col_x + col_port + col_side + 4, y, col_dest, _TABLE_ROW_H),
                           dest if dest else "—", _C_TEXT_TABLE, size=7)
                y += _TABLE_ROW_H

        return y


# ===========================================================================
# WANDPUNTEN RENDERER
# ===========================================================================

class OutletsRenderer:
    """
    Tekent wandpunten als lijst:
    naam | locatie | trace naar eindpunt

    Groepeert per ruimte als mode='site'.
    """

    def __init__(self, room_or_site: dict, data: dict, mode: str = "room"):
        self._data = data
        self._mode = mode
        if mode == "site":
            self._site = room_or_site
            self._room = None
        else:
            self._room = room_or_site
            self._site = next(
                (s for s in get_all_sites(data)
                 for r in s.get("rooms", [])
                 if r["id"] == room_or_site["id"]),
                {"name": ""}
            )

    def render_image(self) -> QImage:
        h = self._calc_total_height()
        img = QImage(QSize(_PAGE_W, h), QImage.Format.Format_ARGB32)
        img.fill(_C_BG)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw(p, 0)
        p.end()
        return img

    def render_to_painter(self, p: QPainter, y_offset: int = 0) -> int:
        return self._draw(p, y_offset)

    def _groups(self) -> list[tuple[dict, list[dict]]]:
        """Geeft [(room, [outlets])] — één groep per ruimte."""
        if self._mode == "site":
            result = []
            for site in self._get_all_sites(data):
                if site["id"] == self._site["id"]:
                    for room in site.get("rooms", []):
                        outlets = room.get("wall_outlets", [])
                        if outlets:
                            result.append((room, outlets))
            return result
        return [(self._room, self._room.get("wall_outlets", []))]

    def _calc_total_height(self) -> int:
        groups = self._groups()
        rows   = sum(len(outlets) for _, outlets in groups)
        grp_h  = len(groups) * (28 * _SCALE + _TABLE_ROW_H)
        return (_MARGIN + 60 * _SCALE + _TABLE_ROW_H +
                rows * _TABLE_ROW_H + grp_h + _MARGIN)

    def _draw(self, p: QPainter, y: int) -> int:
        y = self._draw_header(p, y)
        y = self._draw_list(p, y)
        return y

    def _draw_header(self, p: QPainter, y: int) -> int:
        y += _MARGIN
        rect = QRect(_MARGIN, y, _PAGE_W - 2 * _MARGIN, 40 * _SCALE)

        if self._mode == "site":
            title = f"🌐  {t('title_wall_outlets')}  —  {self._site['name']}"
        else:
            title = (f"🌐  {t('title_wall_outlets')}  —  "
                     f"{self._room['name']}  —  {self._site['name']}")

        _draw_text(p, rect, title, _C_TEXT_MAIN, size=14, bold=True)

        datum = datetime.date.today().strftime("%d/%m/%Y")
        _draw_text(p, rect, datum, _C_TEXT_SUB, size=9,
                   align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        y += 40 * _SCALE + 8 * _SCALE

        p.setPen(QPen(_C_BORDER, 1 * _SCALE))
        p.drawLine(_MARGIN, y, _PAGE_W - _MARGIN, y)
        return y + 8 * _SCALE

    def _draw_list(self, p: QPainter, y: int) -> int:
        # Kolombreedtes
        col_x      = _MARGIN
        col_name   = 200 * _SCALE
        col_loc    = 260 * _SCALE
        col_trace  = _PAGE_W - 2 * _MARGIN - col_name - col_loc

        # Koptekst
        p.fillRect(QRect(col_x, y, _PAGE_W - 2 * _MARGIN, _TABLE_ROW_H), _C_TABLE_HDR)
        _draw_text(p, QRect(col_x + 4, y, col_name, _TABLE_ROW_H),
                   t("export_col_outlet"), _C_TEXT_MAIN, size=8, bold=True)
        _draw_text(p, QRect(col_x + col_name + 4, y, col_loc, _TABLE_ROW_H),
                   t("export_col_location"), _C_TEXT_MAIN, size=8, bold=True)
        _draw_text(p, QRect(col_x + col_name + col_loc + 4, y, col_trace, _TABLE_ROW_H),
                   t("export_col_trace"), _C_TEXT_MAIN, size=8, bold=True)
        y += _TABLE_ROW_H

        alt = False
        for room, outlets in self._groups():
            # Ruimte groepkop (alleen site-modus of altijd voor duidelijkheid)
            p.fillRect(QRect(col_x, y, _PAGE_W - 2 * _MARGIN, _TABLE_ROW_H + 4 * _SCALE),
                       _C_UNIT_DEV)
            _draw_text(p,
                       QRect(col_x + 4, y, _PAGE_W - 2 * _MARGIN, _TABLE_ROW_H + 4 * _SCALE),
                       f"  🚪  {room['name']}  ({len(outlets)} {t('tree_wall_outlets').lower()})",
                       _C_TEXT_MAIN, size=8, bold=True)
            y += _TABLE_ROW_H + 4 * _SCALE

            for outlet in outlets:
                bg = _C_TABLE_ALT if alt else _C_BG
                p.fillRect(QRect(col_x, y, _PAGE_W - 2 * _MARGIN, _TABLE_ROW_H), bg)
                alt = not alt

                # Trace samenvatting
                steps     = tracing.trace_from_wall_outlet(self._data, outlet["id"])
                trace_lbl = self._trace_summary(steps)
                loc       = outlet.get("location_description", "—")

                _draw_text(p, QRect(col_x + 16, y, col_name - 16, _TABLE_ROW_H),
                           outlet.get("name", ""), _C_TEXT_TABLE, size=7)
                _draw_text(p, QRect(col_x + col_name + 4, y, col_loc, _TABLE_ROW_H),
                           loc, _C_TEXT_SUB, size=7)
                _draw_text(p, QRect(col_x + col_name + col_loc + 4, y, col_trace, _TABLE_ROW_H),
                           trace_lbl, _C_TEXT_TABLE, size=7)
                y += _TABLE_ROW_H

        return y

    def _trace_summary(self, steps: list) -> str:
        if not steps:
            return "—"
        last_port = next((s for s in reversed(steps) if s["obj_type"] == "port"), None)
        first_ep  = next((s for s in steps if s["obj_type"] == "endpoint"), None)
        parts = []
        if first_ep:
            parts.append(f"💻 {first_ep['label']}")
        if last_port:
            parts.append(f"⬡ {last_port['label']}")
        return "  →  ".join(parts) if parts else "—"


# ===========================================================================
# PUBLIEKE API — entry points voor main_window
# ===========================================================================

def render_rack_image(rack: dict, room: dict, site: dict, data: dict,
                      filepath: str) -> tuple[bool, str]:
    """
    Exporteer rack als PNG/JPG.
    Retourneert (ok, foutmelding).
    """
    try:
        renderer = RackRenderer(rack, room, site, data)
        img      = renderer.render_image()
        ext      = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else "png"
        fmt      = "JPEG" if ext in ("jpg", "jpeg") else "PNG"
        ok       = img.save(filepath, fmt)
        return (ok, "" if ok else "Opslaan mislukt")
    except Exception as e:
        return (False, str(e))


def render_rack_pdf(rack: dict, room: dict, site: dict, data: dict,
                    filepath: str) -> tuple[bool, str]:
    """
    Exporteer rack als PDF.
    Retourneert (ok, foutmelding).
    """
    try:
        renderer = RackRenderer(rack, room, site, data)

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(filepath)
        printer.setPageOrientation(
            __import__("PySide6.QtGui", fromlist=["QPageLayout"]).QPageLayout.Orientation.Landscape
        )
        from PySide6.QtGui import QPageSize
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setFullPage(True)

        p = QPainter(printer)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Scale naar printer DPI
        scale_f = printer.logicalDpiX() / 96.0
        p.scale(scale_f / _SCALE, scale_f / _SCALE)

        p.fillRect(0, 0, _PAGE_W * 4, renderer._calc_total_height() * 4, _C_BG)
        renderer.render_to_painter(p, 0)
        p.end()
        return (True, "")
    except Exception as e:
        return (False, str(e))


def render_outlets_image(room_or_site: dict, data: dict, mode: str,
                         filepath: str) -> tuple[bool, str]:
    """
    Exporteer wandpunten overzicht als PNG/JPG.
    """
    try:
        renderer = OutletsRenderer(room_or_site, data, mode)
        img      = renderer.render_image()
        ext      = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else "png"
        fmt      = "JPEG" if ext in ("jpg", "jpeg") else "PNG"
        ok       = img.save(filepath, fmt)
        return (ok, "" if ok else "Opslaan mislukt")
    except Exception as e:
        return (False, str(e))


def render_outlets_pdf(room_or_site: dict, data: dict, mode: str,
                       filepath: str) -> tuple[bool, str]:
    """
    Exporteer wandpunten overzicht als PDF.
    """
    try:
        renderer = OutletsRenderer(room_or_site, data, mode)

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(filepath)
        printer.setPageOrientation(
            __import__("PySide6.QtGui", fromlist=["QPageLayout"]).QPageLayout.Orientation.Landscape
        )
        from PySide6.QtGui import QPageSize
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setFullPage(True)

        p = QPainter(printer)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        scale_f = printer.logicalDpiX() / 96.0
        p.scale(scale_f / _SCALE, scale_f / _SCALE)

        p.fillRect(0, 0, _PAGE_W * 4, renderer._calc_total_height() * 4, _C_BG)
        renderer.render_to_painter(p, 0)
        p.end()
        return (True, "")
    except Exception as e:
        return (False, str(e))

# ===========================================================================
# FLOORPLAN RENDERER  (G-OPEN-8)
# ===========================================================================

# Overlay kleuren — zelfde palet als floorplan_view.py
_C_OL_MAPPED    = QColor("#4caf7d")   # groen  — wandpunt
_C_OL_ENDPOINT  = QColor("#2196f3")   # blauw  — direct endpoint
_C_OL_PORT      = QColor("#ff7043")   # oranje — poort-koppeling
_C_OL_UNMAPPED  = QColor("#f0a030")   # amber  — ongekoppeld
_OVERLAY_R_EXP  = 8 * _SCALE          # overlay straal in export-pixels

# Paginastructuur PDF
# Pagina 1 : SVG grondplan + overlay-cirkels + legenda
# Pagina 2 : Alle wandpunten van de site
# Pagina 3 : Alle devices van de site (in rack-slots)
# Pagina 4 : Gekoppelde wandpunten & devices (via SVG-mapping)
# Pagina 5 : Niet-gekoppelde wandpunten & devices


class FloorplanRenderer:
    """
    G-OPEN-8 — Exporteer grondplan als PDF of PNG.

    PDF-structuur (vaste pagina-indeling):
      Pagina 1 : SVG grondplan met overlay-cirkels + legenda
      Pagina 2 : Alle wandpunten van de site
      Pagina 3 : Alle devices van de site
      Pagina 4 : Gekoppelde wandpunten / devices (aanwezig in SVG-mappings)
      Pagina 5 : Niet-gekoppelde wandpunten / devices

    PNG : enkel pagina 1 (grondplan + legenda).

    Werkt headless — geen Qt-venster nodig.
    SVG gerenderd via QSvgRenderer naar tussentijds QImage.
    """

    # Kleuren voor witte PDF-achtergrond (afwijkend van donker UI-thema)
    _C_TITLE     = QColor("#111111")   # bijna zwart
    _C_DATE      = QColor("#444444")   # donkergrijs
    _C_TBL_MAIN  = QColor("#111111")   # tabelkoptekst
    _C_TBL_SUB   = QColor("#333333")   # tabeldata
    _C_GRP_TXT   = QColor("#111111")   # groep-scheidingsbalk tekst
    _C_BORDER_FP = QColor("#aaaaaa")   # scheidingslijn

    _IMG_W       = 2480 * _SCALE   # A4 landscape @150dpi equivalent
    _IMG_H       = 1754 * _SCALE   # A4 landscape hoogte
    _SVG_MAX_H   = 1400 * _SCALE   # maximale SVG-hoogte op pagina 1
    _LEGEND_H    = 64  * _SCALE    # legenda-balk hoogte
    _SEC_HDR_H   = 32  * _SCALE    # sectiekoptekst hoogte
    _COL_HDR_H   = 24  * _SCALE    # kolomkoptekst hoogte
    _ROW_H       = 20  * _SCALE    # tabelrij hoogte

    def __init__(
        self,
        floorplan: dict,
        site: dict,
        data: dict,
    ):
        self._floorplan = floorplan
        self._site      = site
        self._data      = data

        # 1.6.0 — Oriëntatie bepalen via SVG viewBox
        # Portret-SVG (h > w) → portret canvas; landscape → landscape (ongewijzigd)
        self._IMG_W, self._IMG_H, self._SVG_MAX_H = self._calc_canvas_dims()

        # Gemapte SVG punten: {svg_point: mapped_val}
        self._mappings: dict[str, str] = floorplan.get("mappings", {})

        # Gecachede lookups
        self._outlet_map: dict[str, dict] = {}
        self._device_map: dict[str, dict] = {}
        self._port_map:   dict[str, dict] = {}
        self._ep_map:     dict[str, dict] = {}
        self._build_maps()

    def _calc_canvas_dims(self) -> tuple[int, int, int]:
        """
        1.6.0 — Bereken canvas-afmetingen op basis van SVG-oriëntatie.
        Portret (ratio < 1): breedte en hoogte omgewisseld t.o.v. landscape.
        """
        try:
            import xml.etree.ElementTree as ET
            from app.services import floorplan_service as _fps
            svg_path = _fps.get_svg_path(self._floorplan)
            if svg_path.exists():
                tree = ET.parse(str(svg_path))
                root = tree.getroot()
                vb = root.get("viewBox") or ""
                if vb:
                    parts = vb.replace(",", " ").split()
                    if len(parts) == 4:
                        svg_w, svg_h = float(parts[2]), float(parts[3])
                        if svg_h > 0 and svg_w / svg_h < 1.0:
                            # Portret — wissel breedte en hoogte om
                            img_w    = self.__class__._IMG_H   # 1754 * _SCALE
                            img_h    = self.__class__._IMG_W   # 2480 * _SCALE
                            svg_maxh = int(img_h * 0.85)
                            return img_w, img_h, svg_maxh
        except Exception:
            pass
        # Landscape (standaard)
        return self.__class__._IMG_W, self.__class__._IMG_H, self.__class__._SVG_MAX_H

    # ------------------------------------------------------------------
    # Cache opbouwen
    # ------------------------------------------------------------------

    def _build_maps(self):
        data = self._data
        for s in get_all_sites(data):
            for r in s.get("rooms", []):
                for wo in r.get("wall_outlets", []):
                    self._outlet_map[wo["id"]] = wo
        for d in data.get("devices", []):
            self._device_map[d["id"]] = d
        for p in data.get("ports", []):
            self._port_map[p["id"]] = p
        for e in data.get("endpoints", []):
            self._ep_map[e["id"]] = e

    # ------------------------------------------------------------------
    # PNG entry point — enkel grondplan-pagina
    # ------------------------------------------------------------------

    def render_image(self) -> "QImage":
        img = QImage(QSize(self._IMG_W, self._IMG_H), QImage.Format.Format_ARGB32)
        img.fill(QColor("#ffffff"))
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._draw_page1(p)
        p.end()
        return img

    # ------------------------------------------------------------------
    # PDF entry point — alle pagina's via printer
    # ------------------------------------------------------------------

    def render_pdf_pages(self, printer: "QPrinter"):
        """
        Tekent alle PDF-pagina's op de gegeven QPrinter.
        Aanroeper is verantwoordelijk voor printer setup en p.end().
        """
        p = QPainter(printer)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Schaal van printer-coördinaten naar onze canvas-ruimte
        pw = printer.width()
        ph = printer.height()
        sx = pw / self._IMG_W
        sy = ph / self._IMG_H
        scale = min(sx, sy)

        def new_canvas():
            """Reset transform en vul achtergrond."""
            p.resetTransform()
            p.scale(scale, scale)
            p.fillRect(0, 0, self._IMG_W, self._IMG_H, QColor("#ffffff"))

        # Pagina 1 — grondplan + overlay-cirkels
        new_canvas()
        self._draw_page1(p)

        # Pagina 2 — gekoppelde punten (kaartjes)
        printer.newPage()
        new_canvas()
        self._draw_page_coupled(p)

        p.end()

    # ==================================================================
    # PAGINA 1 — SVG grondplan + overlays + legenda
    # ==================================================================

    def _draw_page1(self, p: "QPainter"):
        y = self._draw_page_header(p, 0)
        self._draw_svg_with_overlays(p, y)

    def _draw_svg_with_overlays(self, p: "QPainter", y: int) -> int:
        from app.services import floorplan_service, floorplan_svg_service

        svg_path = floorplan_service.get_svg_path(self._floorplan)
        if not svg_path.exists():
            _draw_text(p, QRect(_MARGIN, y, self._IMG_W - 2*_MARGIN, 40*_SCALE),
                       "⚠  SVG bestand ontbreekt", _C_OL_UNMAPPED, size=10)
            return y + 60 * _SCALE

        svg_img = self._render_svg_to_image(svg_path, floorplan_svg_service)
        if svg_img is None or svg_img.isNull():
            _draw_text(p, QRect(_MARGIN, y, self._IMG_W - 2*_MARGIN, 40*_SCALE),
                       "⚠  SVG kon niet worden geladen", _C_OL_UNMAPPED, size=10)
            return y + 60 * _SCALE

        # Beschikbare ruimte: vanaf y tot onderaan pagina, min legenda + marges
        # 1.6.0 — correctie: avail_h is de ruimte die de SVG mag innemen,
        # zodat SVG + header + legenda altijd binnen _IMG_H passen.
        avail_h = self._IMG_H - y - self._LEGEND_H - 2 * _MARGIN
        avail_h = max(avail_h, 100 * _SCALE)

        src_w = svg_img.width()
        src_h = svg_img.height()
        max_w = self._IMG_W - 2 * _MARGIN
        # Schaal zodat SVG past binnen (max_w × avail_h) — aspect ratio bewaard
        scale = min(max_w / max(src_w, 1), avail_h / max(src_h, 1))
        # Nooit opschalen voorbij de beschikbare breedte
        scale = min(scale, max_w / max(src_w, 1))
        dst_w = int(src_w * scale)
        dst_h = int(src_h * scale)
        dst_x = _MARGIN + (max_w - dst_w) // 2

        p.drawImage(QRect(dst_x, y, dst_w, dst_h), svg_img)

        # Overlays
        from PySide6.QtSvg import QSvgRenderer as _QSvgRenderer
        positions = floorplan_svg_service.detect_point_positions(svg_path)
        rdr = _QSvgRenderer(str(svg_path))
        vb  = rdr.viewBoxF()
        vb_w = vb.width()  if vb.width()  > 0 else src_w
        vb_h = vb.height() if vb.height() > 0 else src_h
        sx = dst_w / max(vb_w, 1)
        sy = dst_h / max(vb_h, 1)

        r = _OVERLAY_R_EXP
        for label, (ox, oy) in positions.items():
            mapped_val = self._mappings.get(label, "")
            if not mapped_val:
                continue   # enkel gekoppelde punten tonen
            px = dst_x + int(ox * sx)
            py = y     + int(oy * sy)
            color = self._overlay_color(mapped_val)
            fill = QColor(color); fill.setAlpha(220)
            p.setBrush(QBrush(fill))
            p.setPen(QPen(QColor("#ffffff"), 1 * _SCALE))
            p.drawEllipse(px - r, py - r, r * 2, r * 2)

        return y + dst_h + _MARGIN

    def _render_svg_to_image(self, svg_path, floorplan_svg_service) -> "QImage | None":
        import tempfile, os
        from PySide6.QtSvg import QSvgRenderer as _QSvgRenderer

        cleaned = floorplan_svg_service.get_cleaned_svg_text(svg_path)
        if not cleaned:
            return None
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".svg", delete=False, mode="w", encoding="utf-8"
            ) as f:
                f.write(cleaned)
                tmp = f.name
            rdr = _QSvgRenderer(tmp)
            if not rdr.isValid():
                return None
            vb    = rdr.viewBoxF()
            src_w = int(vb.width())  if vb.width()  > 0 else 800
            src_h = int(vb.height()) if vb.height() > 0 else 600
            rw = min(src_w * 2, self._IMG_W)
            rh = int(src_h * (rw / max(src_w, 1)))
            img = QImage(QSize(rw, rh), QImage.Format.Format_ARGB32)
            img.fill(QColor("#ffffff"))
            pp = QPainter(img)
            pp.setRenderHint(QPainter.RenderHint.Antialiasing)
            pp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            rdr.render(pp)
            pp.end()
            return img
        except Exception:
            return None
        finally:
            if tmp:
                try: os.unlink(tmp)
                except OSError: pass

    def _draw_legend(self, p: "QPainter", y: int):
        items = [
            (_C_OL_MAPPED,   "Wandpunt"),
            (_C_OL_ENDPOINT, "Eindapparaat (direct)"),
            (_C_OL_PORT,     "Poort-koppeling"),
            (_C_OL_UNMAPPED, "Ongekoppeld punt"),
        ]
        total_w = self._IMG_W - 2 * _MARGIN
        p.fillRect(QRect(_MARGIN, y, total_w, self._LEGEND_H), _C_HEADER_BG)
        item_w = total_w // len(items)
        cx = _MARGIN
        r  = 10 * _SCALE
        cy = y + self._LEGEND_H // 2
        for color, label in items:
            fill = QColor(color); fill.setAlpha(200)
            p.setBrush(QBrush(fill))
            p.setPen(QPen(color, 2 * _SCALE))
            p.drawEllipse(cx + 8*_SCALE, cy - r, r*2, r*2)
            _draw_text(p, QRect(cx + 8*_SCALE + r*2 + 6*_SCALE, y,
                                item_w - r*2 - 20*_SCALE, self._LEGEND_H),
                       label, _C_TEXT_MAIN, size=7)
            cx += item_w

    # ==================================================================
    # PAGINA 2 — Alle wandpunten van de site
    # ==================================================================

    def _draw_page_outlets_all(self, p: "QPainter"):
        from app.helpers.i18n import t
        y = self._draw_page_header(p, 0,
            title=f"Alle wandpunten  —  {self._site.get('name', '')}")

        # Kolommen: Ruimte | Naam | Locatie | Eindapparaat | Trace
        cols = [
            ("Ruimte",       0.16),
            ("Wandpunt",     0.14),
            ("Locatie",      0.20),
            ("Eindapparaat", 0.22),
            ("Trace",        0.28),
        ]
        y = self._draw_col_header(p, y, cols)

        site_id = self._floorplan.get("site_id", "")
        alt = False
        for site in self._get_all_sites(data):
            if site["id"] != site_id:
                continue
            for room in site.get("rooms", []):
                room_name = room.get("name", "")
                outlets   = room.get("wall_outlets", [])
                if not outlets:
                    continue
                # Ruimte-scheidingsbalk
                y = self._draw_group_row(p, y, f"🚪  {room_name}  ({len(outlets)})")
                for wo in outlets:
                    ep_name = ""
                    ep_id   = wo.get("endpoint_id", "")
                    if ep_id and ep_id in self._ep_map:
                        ep_name = self._ep_map[ep_id].get("name", "")
                    from app.services import tracing as _tr
                    steps = _tr.trace_from_wall_outlet(self._data, wo["id"])
                    trace = self._trace_summary(steps)
                    row = [
                        (room_name, 0.16),
                        (wo.get("name", ""), 0.14),
                        (wo.get("location_description", "—"), 0.20),
                        (ep_name or "—", 0.22),
                        (trace, 0.28),
                    ]
                    y = self._draw_data_row(p, y, row, alt)
                    alt = not alt
                    y = self._check_page_overflow(p, y)

    # ==================================================================
    # PAGINA 3 — Alle devices van de site
    # ==================================================================

    def _draw_page_devices_all(self, p: "QPainter"):
        y = self._draw_page_header(p, 0,
            title=f"Alle devices  —  {self._site.get('name', '')}")

        cols = [
            ("Rack",          0.18),
            ("Device",        0.20),
            ("Type",          0.14),
            ("IP",            0.16),
            ("Poorten",       0.10),
            ("Verbindingen",  0.22),
        ]
        y = self._draw_col_header(p, y, cols)

        site_id     = self._floorplan.get("site_id", "")
        conn_ports  = _connected_ports(self._data)
        alt = False

        for site in self._get_all_sites(data):
            if site["id"] != site_id:
                continue
            for room in site.get("rooms", []):
                for rack in room.get("racks", []):
                    rack_name = f"{room['name']} / {rack['name']}"
                    slots = rack.get("slots", [])
                    if not slots:
                        continue
                    y = self._draw_group_row(p, y, f"🗄  {rack_name}  ({len(slots)} devices)")
                    for slot in slots:
                        dev = self._device_map.get(slot.get("device_id", ""))
                        if not dev:
                            continue
                        ports     = [pp for pp in self._data.get("ports", [])
                                     if pp.get("device_id") == dev["id"]]
                        connected = sum(1 for pp in ports if pp["id"] in conn_ports)
                        ip        = dev.get("ip", "—") or "—"
                        dev_type  = dev.get("type", "—") or "—"
                        row = [
                            (rack_name,                    0.18),
                            (dev.get("name", ""),          0.20),
                            (dev_type,                     0.14),
                            (ip,                           0.16),
                            (f"{len(ports)}",              0.10),
                            (f"{connected} verbonden",     0.22),
                        ]
                        y = self._draw_data_row(p, y, row, alt)
                        alt = not alt
                        y = self._check_page_overflow(p, y)

    # ==================================================================
    # PAGINA 4 — Gekoppelde punten — kaartjes per SVG-punt
    # ==================================================================

    # Kaartje-afmetingen (volledige breedte, leesbaar op A4)
    _CARD_GAP    = 20 * _SCALE   # ruimte tussen kaartjes
    _CARD_HDR_H  = 38 * _SCALE   # badge-balk hoogte
    _CARD_ROW_H  = 26 * _SCALE   # rij-hoogte in kaartje
    _CARD_SEC_H  = 22 * _SCALE   # sectie-label hoogte
    _CARD_PAD    = 14 * _SCALE   # interne padding
    _CARD_LBL_W  = 0.25           # fractie label-kolom breedte
    _CARD_TXT_PX = 15             # font grootte data rijen (px)
    _CARD_HDR_PX = 20             # font grootte badge (px)
    _CARD_SEC_PX = 13             # font grootte sectie-kop (px)
    _CARD_LBL_PX = 13             # font grootte label (px)

    def _draw_page_coupled(self, p: "QPainter"):
        y = self._draw_page_header(p, 0,
            title=f"Gekoppelde punten  —  {self._site.get('name', '')}")

        if not self._mappings:
            _fp_draw_text(p, QRect(_MARGIN, y + _MARGIN, self._IMG_W - 2*_MARGIN, 40*_SCALE),
                          "Geen koppelingen gevonden in dit grondplan.",
                          self._C_DATE, size_pt=10)
            return

        from app.services import tracing as _tr

        # Eén kaartje per rij — volledige breedte
        card_w = self._IMG_W - 2 * _MARGIN

        for svg_pt, mapped_val in sorted(self._mappings.items()):
            card_h = self._calc_card_height(mapped_val)
            self._draw_coupled_card(p, _MARGIN, y, card_w, svg_pt, mapped_val, _tr)
            y += card_h + self._CARD_GAP

    def _calc_card_height(self, mapped_val: str) -> int:
        """Berekent de hoogte van een kaartje op basis van het type koppeling."""
        R  = self._CARD_ROW_H
        S  = self._CARD_SEC_H
        P  = self._CARD_PAD
        h  = self._CARD_HDR_H + P  # badge + top-padding

        if mapped_val.startswith("port:"):
            # Wandpunt (3) + Device (6) + Poort (2) als 3 kolommen naast elkaar
            h += S + 6 * R   # hoogste kolom = device (naam,type,ip,mac,rack,model)
            h += P
            h += S + 5 * R   # trace: max 5 stappen
        elif mapped_val.startswith("ep:"):
            # Eindapparaat: naam,type,ip,mac,sn,merk,model,notities
            h += S + 8 * R
            h += P
            h += S + 5 * R   # trace
        else:
            # Wandpunt (links) + Eindapparaat (rechts): max(5,8) = 8 rijen
            h += S + 8 * R
            h += P
            h += S + 5 * R   # trace

        h += P   # bottom padding
        return h

    def _draw_coupled_card(
        self, p: "QPainter", cx: int, cy: int, cw: int,
        svg_pt: str, mapped_val: str, _tracing
    ):
        """Tekent één kaartje voor een gekoppeld SVG-punt."""
        card_h = self._calc_card_height(mapped_val)
        color  = self._overlay_color(mapped_val)

        # ── Kaartje-kader ─────────────────────────────────────────────
        p.setPen(QPen(QColor("#cccccc"), 1 * _SCALE))
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawRoundedRect(QRect(cx, cy, cw, card_h), 6 * _SCALE, 6 * _SCALE)

        # ── Badge-balk (gekleurde header) ──────────────────────────────
        badge_rect = QRect(cx, cy, cw, self._CARD_HDR_H)
        badge_color = QColor(color); badge_color.setAlpha(40)
        p.fillRect(badge_rect, badge_color)

        # Gekleurde cirkel
        r  = 12 * _SCALE
        bx = cx + self._CARD_PAD + r
        by = cy + self._CARD_HDR_H // 2
        fill = QColor(color); fill.setAlpha(220)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(QColor("#ffffff"), 1 * _SCALE))
        p.drawEllipse(bx - r, by - r, r * 2, r * 2)

        # SVG-label en type
        # Type label + object naam in badge
        if mapped_val.startswith("ep:"):
            type_lbl = "Eindapparaat"
            ep = self._ep_map.get(mapped_val[3:])
            obj_name = ep.get("name", "") if ep else ""
        elif mapped_val.startswith("port:"):
            type_lbl = "Poort"
            port = self._port_map.get(mapped_val[5:])
            dev  = self._device_map.get(port.get("device_id","")) if port else None
            obj_name = dev.get("name","") if dev else ""
        else:
            type_lbl = "Wandpunt"
            wo = self._outlet_map.get(mapped_val)
            obj_name = wo.get("name","") if wo else ""

        badge_text = f"{svg_pt}   {type_lbl}"
        if obj_name:
            badge_text += f"   |   {obj_name}"
        lbl_rect = QRect(bx + r + 10*_SCALE, cy, self._IMG_W, self._CARD_HDR_H)
        _fp_draw_pt(p, lbl_rect, badge_text, self._C_TITLE,
                    size_pt=13, bold=True)

        y = cy + self._CARD_HDR_H + self._CARD_PAD
        inner_x = cx + self._CARD_PAD
        inner_w = cw - 2 * self._CARD_PAD

        # ── Inhoud op basis van type ───────────────────────────────────
        if mapped_val.startswith("port:"):
            y = self._card_section_port(p, inner_x, y, inner_w, mapped_val, _tracing)
        elif mapped_val.startswith("ep:"):
            y = self._card_section_ep(p, inner_x, y, inner_w, mapped_val, _tracing)
        else:
            y = self._card_section_outlet(p, inner_x, y, inner_w, mapped_val, _tracing)

    # ------------------------------------------------------------------
    # Kaartje-secties
    # ------------------------------------------------------------------

    def _card_label_row(self, p, x, y, w, label, value, size_px=None):
        """Één label:waarde rij in een kaartje."""
        if size_px is None:
            size_px = self._CARD_TXT_PX
        lw = int(w * self._CARD_LBL_W)
        vw = w - lw
        _fp_draw_pt(p, QRect(x, y, lw, self._CARD_ROW_H),
                    label, self._C_DATE, size_pt=9)
        _fp_draw_pt(p, QRect(x + lw, y, vw, self._CARD_ROW_H),
                    value or "—", self._C_TITLE, size_pt=10, bold=True)
        return y + self._CARD_ROW_H

    def _card_section_header(self, p, x, y, w, label):
        """Grijze sectietitel binnen een kaartje."""
        p.fillRect(QRect(x, y, w, self._CARD_SEC_H), QColor("#eeeeee"))
        _fp_draw_pt(p, QRect(x + 6*_SCALE, y, w, self._CARD_SEC_H),
                    label, QColor("#444444"), size_pt=9, bold=True)
        return y + self._CARD_SEC_H

    def _card_section_outlet(self, p, x, y, w, mapped_val, _tracing):
        """Wandpunt + Eindapparaat naast elkaar, daarna Trace."""
        wo  = self._outlet_map.get(mapped_val)
        ep  = self._ep_map.get(wo.get("endpoint_id", "")) if wo else None

        # 2 kolommen
        col_w = (w - 8*_SCALE) // 2

        # Kolom 1: Wandpunt
        y1 = self._card_section_header(p, x, y, col_w, "Wandpunt")
        from app.helpers.settings_storage import get_outlet_location_label
        wo_loc_key = wo.get("location_description", "") if wo else ""
        wo_loc_lbl = get_outlet_location_label(wo_loc_key) if wo_loc_key else "—"
        y1 = self._card_label_row(p, x, y1, col_w, "Naam:",    wo.get("name", "—") if wo else "—")
        y1 = self._card_label_row(p, x, y1, col_w, "Locatie:", wo_loc_lbl)
        y1 = self._card_label_row(p, x, y1, col_w, "VLAN:",    wo.get("vlan", "—") if wo else "—")
        y1 = self._card_label_row(p, x, y1, col_w, "Notities:", wo.get("notes", "—") if wo else "—")

        # Kolom 2: Eindapparaat
        ex = x + col_w + 8*_SCALE
        y2 = self._card_section_header(p, ex, y, col_w, "Eindapparaat")
        if ep:
            y2 = self._card_label_row(p, ex, y2, col_w, "Naam:",     ep.get("name", "—"))
            y2 = self._card_label_row(p, ex, y2, col_w, "Type:",     ep.get("type", "—"))
            y2 = self._card_label_row(p, ex, y2, col_w, "IP:",       ep.get("ip", "—") or "—")
            y2 = self._card_label_row(p, ex, y2, col_w, "MAC:",      ep.get("mac", "—") or "—")
            y2 = self._card_label_row(p, ex, y2, col_w, "S/N:",      ep.get("serial", "—") or "—")
            y2 = self._card_label_row(p, ex, y2, col_w, "Merk:",     ep.get("brand", "—") or "—")
            y2 = self._card_label_row(p, ex, y2, col_w, "Model:",    ep.get("model", "—") or "—")
            y2 = self._card_label_row(p, ex, y2, col_w, "Notities:", ep.get("notes", "—") or "—")
        else:
            _fp_draw_text(p, QRect(ex, y2, col_w, self._CARD_ROW_H),
                          "Geen eindapparaat", self._C_DATE, size_pt=9)
            y2 += self._CARD_ROW_H

        # Trace — onder beide kolommen
        y_after = max(y1, y2) + self._CARD_PAD
        steps = _tracing.trace_from_wall_outlet(self._data, mapped_val)
        y_after = self._card_trace(p, x, y_after, w, steps)
        return y_after

    def _card_section_ep(self, p, x, y, w, mapped_val, _tracing):
        """Eindapparaat-info + Trace."""
        ep_id = mapped_val[3:]
        ep    = self._ep_map.get(ep_id)

        y = self._card_section_header(p, x, y, w, "Eindapparaat")
        if ep:
            # 2 kolommen naast elkaar voor compactheid
            col_w = (w - 8*_SCALE) // 2
            col2  = x + col_w + 8*_SCALE
            ya = y; yb = y
            ya = self._card_label_row(p, x,    ya, col_w, "Naam:",     ep.get("name", "—"))
            ya = self._card_label_row(p, x,    ya, col_w, "Type:",     ep.get("type", "—"))
            ya = self._card_label_row(p, x,    ya, col_w, "IP adres:", ep.get("ip", "—") or "—")
            ya = self._card_label_row(p, x,    ya, col_w, "MAC adres:",ep.get("mac", "—") or "—")
            yb = self._card_label_row(p, col2, yb, col_w, "S/N:",      ep.get("serial", "—") or "—")
            yb = self._card_label_row(p, col2, yb, col_w, "Merk:",     ep.get("brand", "—") or "—")
            yb = self._card_label_row(p, col2, yb, col_w, "Model:",    ep.get("model", "—") or "—")
            yb = self._card_label_row(p, col2, yb, col_w, "Locatie:",  ep.get("location", "—") or "—")
            yb = self._card_label_row(p, col2, yb, col_w, "Notities:", ep.get("notes", "—") or "—")
            y  = max(ya, yb)
        else:
            _fp_draw_text(p, QRect(x, y, w, self._CARD_ROW_H),
                          "Eindapparaat niet gevonden", self._C_DATE, size_pt=9)
            y += self._CARD_ROW_H

        y += self._CARD_PAD
        conn = next(
            (c for c in self._data.get("connections", [])
             if (c.get("to_type") == "endpoint" and c["to_id"] == ep_id) or
                (c.get("from_type") == "endpoint" and c["from_id"] == ep_id)),
            None,
        )
        steps = []
        if conn:
            pid   = conn["from_id"] if conn.get("to_type") == "endpoint" else conn["to_id"]
            steps = _tracing.trace_from_port(self._data, pid)
        y = self._card_trace(p, x, y, w, steps)
        return y

    def _card_section_port(self, p, x, y, w, mapped_val, _tracing):
        """Wandpunt (indien van toepassing) + Device + Poort + Trace in 3 kolommen."""
        from app.helpers.settings_storage import get_outlet_location_label

        port_id = mapped_val[5:]
        port    = self._port_map.get(port_id)
        dev     = self._device_map.get(port.get("device_id", "")) if port else None

        # Wandpunt zoeken dat aan deze poort gekoppeld is
        wo = None
        for s in self._get_all_sites(data):
            for r in s.get("rooms", []):
                for outlet in r.get("wall_outlets", []):
                    if outlet.get("port_id") == port_id:
                        wo = outlet
                        break

        # Rack-locatie
        loc = "—"
        if dev:
            for s in self._get_all_sites(data):
                for r in s.get("rooms", []):
                    for ra in r.get("racks", []):
                        for sl in ra.get("slots", []):
                            if sl.get("device_id") == dev["id"]:
                                loc = f"{r['name']} / {ra['name']}"

        # 3 kolommen als wandpunt beschikbaar, anders 2
        if wo:
            col_w = (w - 16*_SCALE) // 3
            # Kolom 1: Wandpunt
            loc_key = wo.get("location_description", "") or ""
            loc_lbl = get_outlet_location_label(loc_key) if loc_key else "—"
            y1 = self._card_section_header(p, x, y, col_w, "Wandpunt")
            y1 = self._card_label_row(p, x, y1, col_w, "Naam:",     wo.get("name", "—"))
            y1 = self._card_label_row(p, x, y1, col_w, "Locatie:",  loc_lbl)
            y1 = self._card_label_row(p, x, y1, col_w, "VLAN:",     wo.get("vlan", "—") or "—")
            y1 = self._card_label_row(p, x, y1, col_w, "Notities:", wo.get("notes", "—") or "—")
            x2 = x + col_w + 8*_SCALE
            x3 = x2 + col_w + 8*_SCALE
        else:
            col_w = (w - 8*_SCALE) // 2
            y1 = y
            x2 = x
            x3 = x + col_w + 8*_SCALE

        # Kolom 2: Device
        y2 = self._card_section_header(p, x2, y, col_w, "Device")
        if dev:
            y2 = self._card_label_row(p, x2, y2, col_w, "Naam:",  dev.get("name", "—"))
            y2 = self._card_label_row(p, x2, y2, col_w, "Type:",  dev.get("type", "—"))
            y2 = self._card_label_row(p, x2, y2, col_w, "IP:",    dev.get("ip", "—") or "—")
            y2 = self._card_label_row(p, x2, y2, col_w, "MAC:",   dev.get("mac", "—") or "—")
            y2 = self._card_label_row(p, x2, y2, col_w, "Rack:",  loc)
        else:
            _fp_draw_text(p, QRect(x2, y2, col_w, self._CARD_ROW_H),
                          "Device niet gevonden", self._C_DATE, size_pt=9)
            y2 += self._CARD_ROW_H

        # Kolom 3: Poort
        y3 = self._card_section_header(p, x3, y, col_w, "Poort")
        if port:
            side = port.get("side", "")
            y3 = self._card_label_row(p, x3, y3, col_w, "Naam:", port.get("name", "—"))
            y3 = self._card_label_row(p, x3, y3, col_w, "Kant:", side.upper() if side else "—")
        else:
            _fp_draw_text(p, QRect(x3, y3, col_w, self._CARD_ROW_H),
                          "Poort niet gevonden", self._C_DATE, size_pt=9)
            y3 += self._CARD_ROW_H

        y_after = max(y1, y2, y3) + self._CARD_PAD
        steps   = _tracing.trace_from_port(self._data, port_id)
        return self._card_trace(p, x, y_after, w, steps)

    def _card_trace(self, p, x, y, w, steps: list) -> int:
        """Trace-sectie onderaan een kaartje."""
        y = self._card_section_header(p, x, y, w, "Trace")
        if not steps:
            _fp_draw_text(p, QRect(x, y, w, self._CARD_ROW_H),
                          "Geen trace beschikbaar", self._C_DATE, size_pt=9)
            return y + self._CARD_ROW_H + self._CARD_PAD

        # Toon max 4 stappen, daarna "..."
        shown = steps[:4]
        for step in shown:
            label = step.get("label", "")
            stype = step.get("obj_type", "")
            prefix = {"port": "⬡", "endpoint": "💻", "wall_outlet": "◈"}.get(stype, "→")
            # Geen emoji — gebruik ASCII alternatieven die altijd renderen
            prefix = {"port": "->", "endpoint": ">", "wall_outlet": ">>"}.get(stype, "->")
            _fp_draw_text(p, QRect(x + 8*_SCALE, y, w - 8*_SCALE, self._CARD_ROW_H),
                          f"{prefix}  {label}", self._C_TBL_SUB, size_pt=10)
            y += self._CARD_ROW_H

        if len(steps) > 4:
            _fp_draw_text(p, QRect(x + 8*_SCALE, y, w, self._CARD_ROW_H),
                          f"... (+{len(steps)-4} stappen)", self._C_DATE, size_pt=9)
            y += self._CARD_ROW_H

        return y + self._CARD_PAD

    # ==================================================================
    # PAGINA 5 — Niet-gekoppelde wandpunten & devices
    # ==================================================================

    def _draw_page_uncoupled(self, p: "QPainter"):
        y = self._draw_page_header(p, 0,
            title=f"Niet-gekoppelde punten  —  {self._site.get('name', '')}")

        # Gemapte outlet/ep/port IDs verzamelen
        mapped_outlet_ids: set[str] = set()
        mapped_ep_ids:     set[str] = set()
        mapped_port_ids:   set[str] = set()
        for mv in self._mappings.values():
            if mv.startswith("ep:"):
                mapped_ep_ids.add(mv[3:])
            elif mv.startswith("port:"):
                mapped_port_ids.add(mv[5:])
            else:
                mapped_outlet_ids.add(mv)

        site_id = self._floorplan.get("site_id", "")
        alt = False

        # ── Niet-gekoppelde wandpunten ────────────────────────────────
        y = self._draw_group_row(p, y, "🌐  Wandpunten zonder SVG-koppeling")

        cols_wo = [
            ("Ruimte",      0.18),
            ("Wandpunt",    0.16),
            ("Locatie",     0.24),
            ("Eindapparaat",0.22),
            ("Trace",       0.20),
        ]
        y = self._draw_col_header(p, y, cols_wo)

        from app.services import tracing as _tr
        any_wo = False
        for site in self._get_all_sites(data):
            if site["id"] != site_id:
                continue
            for room in site.get("rooms", []):
                for wo in room.get("wall_outlets", []):
                    if wo["id"] in mapped_outlet_ids:
                        continue
                    any_wo = True
                    ep_name = ""
                    ep_id   = wo.get("endpoint_id", "")
                    if ep_id and ep_id in self._ep_map:
                        ep_name = self._ep_map[ep_id].get("name", "")
                    steps = _tr.trace_from_wall_outlet(self._data, wo["id"])
                    trace = self._trace_summary(steps)
                    row = [
                        (room.get("name", ""),               0.18),
                        (wo.get("name", ""),                 0.16),
                        (wo.get("location_description", "—"),0.24),
                        (ep_name or "—",                     0.22),
                        (trace,                              0.20),
                    ]
                    y = self._draw_data_row(p, y, row, alt)
                    alt = not alt
                    y = self._check_page_overflow(p, y)

        if not any_wo:
            y = self._draw_data_row(p, y, [("Alle wandpunten zijn gekoppeld.", 1.0)], False)

        # ── Niet-gekoppelde devices ───────────────────────────────────
        y += _MARGIN
        y = self._draw_group_row(p, y, "🗄  Devices zonder SVG-koppeling (via poort)")

        cols_dev = [
            ("Rack",    0.20),
            ("Device",  0.22),
            ("Type",    0.14),
            ("IP",      0.16),
            ("Poorten", 0.10),
            ("",        0.18),
        ]
        y = self._draw_col_header(p, y, cols_dev)

        conn_ports = _connected_ports(self._data)
        any_dev    = False
        alt        = False
        for site in self._get_all_sites(data):
            if site["id"] != site_id:
                continue
            for room in site.get("rooms", []):
                for rack in room.get("racks", []):
                    rack_name = f"{room['name']} / {rack['name']}"
                    for slot in rack.get("slots", []):
                        dev = self._device_map.get(slot.get("device_id", ""))
                        if not dev:
                            continue
                        ports = [pp for pp in self._data.get("ports", [])
                                 if pp.get("device_id") == dev["id"]]
                        # Device is niet-gekoppeld als geen van zijn poorten in mapped_port_ids zit
                        if any(pp["id"] in mapped_port_ids for pp in ports):
                            continue
                        any_dev = True
                        connected = sum(1 for pp in ports if pp["id"] in conn_ports)
                        row = [
                            (rack_name,                0.20),
                            (dev.get("name", ""),      0.22),
                            (dev.get("type", "—"),     0.14),
                            (dev.get("ip", "—") or "—",0.16),
                            (f"{len(ports)}",          0.10),
                            (f"{connected} verbonden", 0.18),
                        ]
                        y = self._draw_data_row(p, y, row, alt)
                        alt = not alt
                        y = self._check_page_overflow(p, y)

        if not any_dev:
            self._draw_data_row(p, y, [("Alle devices zijn gekoppeld.", 1.0)], False)

    # ==================================================================
    # Gedeelde teken-helpers
    # ==================================================================

    def _draw_page_header(self, p: "QPainter", y: int, title: str = "") -> int:
        """Paginaheader: grondplan-naam (of custom titel), site, datum."""
        if not title:
            fp_name   = self._floorplan.get("name", "") or self._floorplan.get("outlet_location_key", "")
            site_name = self._site.get("name", "")
            title = f"{fp_name}  |  {site_name}" if site_name else fp_name

        y += _MARGIN
        hdr_h = 28 * _SCALE
        rect = QRect(_MARGIN, y, self._IMG_W - 2*_MARGIN, hdr_h)
        # Pixel-fonts: niet beïnvloed door QPainter.scale()
        _fp_draw_text(p, rect, title, self._C_TITLE, size_px=22, bold=True)
        datum = datetime.date.today().strftime("%d/%m/%Y")
        _fp_draw_text(p, rect, datum, self._C_DATE, size_px=16,
                      align=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        y += hdr_h + 3 * _SCALE
        p.setPen(QPen(self._C_BORDER_FP, 1 * _SCALE))
        p.drawLine(_MARGIN, y, self._IMG_W - _MARGIN, y)
        p.setPen(QPen(_C_BORDER, 1))   # reset pen
        return y + _MARGIN

    def _draw_group_row(self, p: "QPainter", y: int, label: str) -> int:
        """Gekleurde groep-scheidingsbalk met label."""
        total_w = self._IMG_W - 2 * _MARGIN
        h = self._SEC_HDR_H
        p.fillRect(QRect(_MARGIN, y, total_w, h), _C_UNIT_DEV)
        _fp_draw_text(p, QRect(_MARGIN + 8*_SCALE, y, total_w, h),
                      label, self._C_GRP_TXT, size_px=16, bold=True)
        return y + h

    def _draw_col_header(self, p: "QPainter", y: int,
                         cols: list[tuple[str, float]]) -> int:
        """Kolomkoptekst-balk."""
        total_w = self._IMG_W - 2 * _MARGIN
        h = self._COL_HDR_H
        p.fillRect(QRect(_MARGIN, y, total_w, h), _C_TABLE_HDR)
        cx = _MARGIN + 4 * _SCALE
        for label, frac in cols:
            cw = int(total_w * frac)
            _fp_draw_text(p, QRect(cx, y, cw, h), label, self._C_TBL_MAIN, size_px=14, bold=True)
            cx += cw
        return y + h

    def _draw_data_row(self, p: "QPainter", y: int,
                       cols: list[tuple[str, float]], alt: bool) -> int:
        """Één tabelrij met alternerende achtergrond."""
        total_w = self._IMG_W - 2 * _MARGIN
        h = self._ROW_H
        bg = _C_TABLE_ALT if alt else _C_BG
        p.fillRect(QRect(_MARGIN, y, total_w, h), bg)
        cx = _MARGIN + 4 * _SCALE
        for text, frac in cols:
            cw = int(total_w * frac)
            _fp_draw_text(p, QRect(cx, y, cw - 4*_SCALE, h), text, self._C_TBL_SUB, size_px=13)
            cx += cw
        return y + h

    def _check_page_overflow(self, p: "QPainter", y: int) -> int:
        """
        Simpele overflow-beveiliging: als y dicht bij de onderkant komt,
        teken een indicatie. Echte paginaoverloop bij tabellen is
        zelden nodig voor het huidige datavolume; bij grote datasets
        kan dit uitgebreid worden met printer.newPage().
        """
        limit = self._IMG_H - self._LEGEND_H - _MARGIN * 3
        if y > limit:
            # Clip stil — rijen die over de rand gaan worden gewoon niet getoond
            return limit + 1  # signaal dat overflow optrad
        return y

    # ==================================================================
    # Data-resolvers
    # ==================================================================

    @staticmethod
    def _overlay_color(mapped_val: str) -> "QColor":
        if mapped_val.startswith("port:"):
            return _C_OL_PORT
        if mapped_val.startswith("ep:"):
            return _C_OL_ENDPOINT
        if mapped_val:
            return _C_OL_MAPPED
        return _C_OL_UNMAPPED

    def _resolve_full(
        self, mapped_val: str, _tracing
    ) -> tuple[str, str, str, str]:
        """Geeft (type, naam, locatie, trace) terug voor één mapping-waarde."""
        data = self._data

        if mapped_val.startswith("port:"):
            port_id  = mapped_val[5:]
            port     = self._port_map.get(port_id)
            dev      = self._device_map.get(port.get("device_id", "")) if port else None
            dev_name = dev.get("name", "") if dev else ""
            pname    = port.get("name", port_id) if port else port_id
            side     = port.get("side", "") if port else ""
            name     = f"{dev_name} — {pname} ({side.upper()})" if dev_name else pname
            loc      = ""
            # Zoek rack-locatie
            for s in get_all_sites(data):
                for r in s.get("rooms", []):
                    for ra in r.get("racks", []):
                        for sl in ra.get("slots", []):
                            if sl.get("device_id") == (dev["id"] if dev else ""):
                                loc = f"{r['name']} / {ra['name']}"
            steps = _tracing.trace_from_port(data, port_id)
            return "Poort", name, loc, self._trace_summary(steps)

        if mapped_val.startswith("ep:"):
            ep_id = mapped_val[3:]
            ep    = self._ep_map.get(ep_id)
            name  = ep.get("name", ep_id) if ep else ep_id
            loc   = ep.get("location", "—") if ep else "—"
            conn  = next(
                (c for c in data.get("connections", [])
                 if (c.get("to_type") == "endpoint" and c["to_id"] == ep_id) or
                    (c.get("from_type") == "endpoint" and c["from_id"] == ep_id)),
                None,
            )
            steps = []
            if conn:
                pid   = conn["from_id"] if conn.get("to_type") == "endpoint" else conn["to_id"]
                steps = _tracing.trace_from_port(data, pid)
            return "Eindapparaat", name, loc, self._trace_summary(steps)

        # Wandpunt
        wo = self._outlet_map.get(mapped_val)
        if wo:
            name = wo.get("name", mapped_val)
            loc  = wo.get("location_description", "—") or "—"
            steps = _tracing.trace_from_wall_outlet(data, mapped_val)
            return "Wandpunt", name, loc, self._trace_summary(steps)

        return "?", mapped_val, "—", "—"

    @staticmethod
    def _trace_summary(steps: list) -> str:
        if not steps:
            return "—"
        last_port = next((s for s in reversed(steps) if s["obj_type"] == "port"), None)
        first_ep  = next((s for s in steps          if s["obj_type"] == "endpoint"), None)
        parts = []
        if first_ep:
            parts.append(f"💻 {first_ep['label']}")
        if last_port:
            parts.append(f"⬡ {last_port['label']}")
        return "  →  ".join(parts) if parts else "—"


# ===========================================================================
# PUBLIEKE API — FloorplanRenderer entry points
# ===========================================================================

def render_floorplan_image(
    floorplan: dict,
    site: dict,
    data: dict,
    filepath: str,
) -> tuple[bool, str]:
    """
    G-OPEN-8 — Exporteer grondplan pagina 1 als PNG.
    """
    try:
        renderer = FloorplanRenderer(floorplan, site, data)
        img      = renderer.render_image()
        ext      = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else "png"
        fmt      = "JPEG" if ext in ("jpg", "jpeg") else "PNG"
        ok       = img.save(filepath, fmt)
        return (ok, "" if ok else "Opslaan mislukt")
    except Exception as e:
        return (False, str(e))


def render_floorplan_pdf(
    floorplans: list[dict],
    site: dict,
    data: dict,
    filepath: str,
) -> tuple[bool, str]:
    """
    G-OPEN-8 — Exporteer één of meerdere grondplannen als PDF.
    Per grondplan: 5 pagina's (grondplan, alle WP, alle devices,
    gekoppeld, niet-gekoppeld).
    """
    try:
        from PySide6.QtGui import QPageLayout, QPageSize

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(filepath)
        printer.setPageOrientation(QPageLayout.Orientation.Landscape)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setFullPage(True)

        first = True
        for floorplan in floorplans:
            renderer = FloorplanRenderer(floorplan, site, data)
            if first:
                renderer.render_pdf_pages(printer)
                first = False
            else:
                # Volgende grondplan: nieuwe reeks pagina's
                printer.newPage()
                renderer.render_pdf_pages(printer)

        return (True, "")
    except Exception as e:
        return (False, str(e))