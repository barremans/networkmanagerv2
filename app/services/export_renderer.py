# =============================================================================
# Networkmap_Creator
# File:    app/services/export_renderer.py
# Role:    G1/G2 — QPainter renderer voor rack + wandpunten export
#          Genereert QImage (PNG/JPG) en PDF volledig vanuit data,
#          onafhankelijk van de UI / schermweergave.
# Version: 1.0.0
# Author:  Barremans
# =============================================================================

import datetime
from PySide6.QtCore  import Qt, QRect, QPoint, QSize
from PySide6.QtGui   import (
    QPainter, QImage, QColor, QFont, QFontMetrics,
    QPen, QBrush, QPainterPath
)
from PySide6.QtPrintSupport import QPrinter

from app.helpers.i18n import t
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
        for site in data.get("sites", []):
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
                (s for s in data.get("sites", [])
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
            for site in self._data.get("sites", []):
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