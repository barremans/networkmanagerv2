# =============================================================================
# Networkmap_Creator
# File:    app/gui/rack_view.py
# Role:    Pure visuele rack weergave widget
# Version: 1.17.0
# Author:  Barremans
# Changes: 1.4.0 — bezettingsindicator in titelregel (percentage + kleurenbalk)
#          1.5.0 — refresh() hergebruikt bestaande layout via _populate()
#          1.9.0 — revert naar v1.3.0 event handling (QFrame + mousePressEvent)
#          1.9.1 — fix: set_connect_mode kleurt alleen VRIJE poorten rood
#                  verbonden poorten (port-connected) blijven oranje zichtbaar
#          1.9.2 — Qt6 fix: event.position().toPoint() + QMenu(self)
#          1.10.0 — Rack nummering: top_down (1 boven) of bottom_up (1 onder)
#          1.11.0 — Poorten per rij instelbaar per device (ports_per_row)
#          1.12.0 — SFP poorten: aparte sectie rechts van copper poorten
#          1.13.1 — Fix: SFP telt als extra poorten (niet aftrekken van front_ports)
#          1.14.0 — Fix: refresh() gebruikt setParent(None) ipv deleteLater()
#          1.15.0 — device_double_clicked signal + dubbelklik op _DeviceRow
#                   zodat widgets direct verwijderd worden + update() na _populate()
#          1.16.0 — Visuele fix: poortblokken tegen naambord aan (geen stretch tussen
#                   voor/achter), naam gecentreerd in resterende ruimte
#          1.17.0 — Switch nummering: oneven boven, even onder (echte switch layout)
#                   alleen actief bij device type "switch" met 2+ rijen
# =============================================================================

from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QScrollArea,
    QVBoxLayout, QHBoxLayout, QSizePolicy, QMenu
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QMouseEvent

from app.helpers.i18n import t

_UNIT_H        = 30
_UNIT_NUM_W    = 32
_PORT_SIZE     = 14
_PORT_GAP      = 2
_MAX_PORTS_ROW = 12

_ACT_EDIT   = "edit"
_ACT_DELETE = "delete"
_ACT_PORTS  = "ports"

_OCC_WARN     = 0.75
_OCC_CRITICAL = 0.90


def _refresh_style(widget: QWidget):
    """Forceert QSS herlaad — betrouwbaar op Windows."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def _rack_occupancy(rack: dict, slots: list | None = None) -> tuple[int, int]:
    total = rack.get("total_units", 0)
    used  = sum(s.get("height", 1) for s in rack.get("slots", []))
    return used, total


def _occupancy_color(used: int, total: int) -> str:
    if total == 0:
        return "#4a9eda"
    ratio = used / total
    if ratio >= _OCC_CRITICAL:
        return "#e05252"
    if ratio >= _OCC_WARN:
        return "#e09a2a"
    return "#4caf7d"


class OccupancyBar(QWidget):
    def __init__(self, used: int, total: int, parent=None):
        super().__init__(parent)
        self._used  = used
        self._total = total
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        used, total = self._used, self._total
        pct   = (used / total * 100) if total else 0
        color = _occupancy_color(used, total)

        bar_container = QFrame()
        bar_container.setFixedSize(80, 10)
        bar_container.setStyleSheet(
            "QFrame { background-color: #2a3a4a; border-radius: 4px; }"
        )
        bar_inner = QFrame(bar_container)
        fill_w = max(4, int(80 * pct / 100)) if total else 0
        bar_inner.setGeometry(0, 0, fill_w, 10)
        bar_inner.setStyleSheet(
            f"QFrame {{ background-color: {color}; border-radius: 4px; }}"
        )
        layout.addWidget(bar_container)

        pct_lbl = QLabel(f"{pct:.0f}%  ({used}/{total}U)")
        pct_lbl.setObjectName("secondary")
        pct_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
        layout.addWidget(pct_lbl)


class RackView(QWidget):
    port_clicked              = Signal(str, str, str)   # port_id, device_id, side
    port_selected_for_connect = Signal(str)             # port_id
    device_context_menu       = Signal(str, str)        # device_id, actie ("edit"|"delete")
    port_context_menu         = Signal(str, object)     # port_id, global QPoint
    device_double_clicked     = Signal(str)              # device_id

    def __init__(self, rack, room, site, data, parent=None):
        super().__init__(parent)
        self._rack          = rack
        self._room          = room
        self._site          = site
        self._data          = data
        self._connect_mode  = False
        self._selected_port = None
        self._port_widgets  = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self._populate(outer)

    # ------------------------------------------------------------------
    # Nummering helper — 1.10.0
    # ------------------------------------------------------------------

    def _display_unit_number(self, u: int) -> str:
        numbering = self._rack.get("numbering", "top_down")
        if numbering == "bottom_up":
            total = self._rack.get("total_units", 1)
            return str(total - u + 1)
        return str(u)

    # ------------------------------------------------------------------
    # Inhoud opbouwen
    # ------------------------------------------------------------------

    def _populate(self, outer: QVBoxLayout):
        """Vult de gegeven layout met titelregel + rack inhoud."""

        title_bar = QFrame()
        title_bar.setObjectName("rack_frame")
        tl = QHBoxLayout(title_bar)
        tl.setContentsMargins(8, 4, 8, 4)

        title_lbl = QLabel(
            f"{self._rack['name']}  —  {self._room['name']}  —  {self._site['name']}"
        )
        title_lbl.setObjectName("rack_title")

        used, total = _rack_occupancy(self._rack)
        occ_bar = OccupancyBar(used, total)
        occ_bar.setToolTip(
            f"{t('rack_occupancy_tooltip')}: {used}/{total}U  "
            f"({used/total*100:.0f}%)" if total else t('rack_occupancy_tooltip')
        )

        numbering = self._rack.get("numbering", "top_down")
        num_lbl_title = QLabel(
            f"↓ 1…{self._rack['total_units']}" if numbering == "top_down"
            else f"↑ 1…{self._rack['total_units']}"
        )
        num_lbl_title.setObjectName("secondary")
        num_lbl_title.setStyleSheet("font-size: 11px;")

        units_lbl = QLabel(f"{self._rack['total_units']}U")
        units_lbl.setObjectName("secondary")
        units_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        tl.addWidget(title_lbl)
        tl.addStretch()
        tl.addWidget(num_lbl_title)
        tl.addSpacing(8)
        tl.addWidget(occ_bar)
        tl.addSpacing(12)
        tl.addWidget(units_lbl)
        outer.addWidget(title_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        total_u  = self._rack.get("total_units", 12)
        slot_map = {s["u_start"]: s for s in self._rack.get("slots", [])}
        dev_map  = {d["id"]: d for d in self._data.get("devices", [])}

        port_map = {}
        for p in self._data.get("ports", []):
            port_map.setdefault(p["device_id"], []).append(p)

        connected_ports = set()
        for conn in self._data.get("connections", []):
            if conn["from_type"] == "port":
                connected_ports.add(conn["from_id"])
            if conn["to_type"] == "port":
                connected_ports.add(conn["to_id"])

        u = 1
        while u <= total_u:
            if u in slot_map:
                slot   = slot_map[u]
                device = dev_map.get(slot["device_id"])
                height = slot.get("height", 1)
                if device:
                    bl.addWidget(self._build_device_row(
                        u, device, height,
                        port_map.get(device["id"], []),
                        connected_ports
                    ))
                    u += height
                    continue
            bl.addWidget(self._build_empty_row(u))
            u += 1

        bl.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------
    # Rijen bouwen
    # ------------------------------------------------------------------

    def _build_empty_row(self, u_num):
        row = QFrame()
        row.setObjectName("rack_unit_empty")
        row.setFixedHeight(_UNIT_H)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        num_lbl = QLabel(self._display_unit_number(u_num))
        num_lbl.setObjectName("unit_number")
        num_lbl.setFixedWidth(_UNIT_NUM_W)
        num_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(num_lbl)
        spacer = QLabel("")
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(spacer)
        return row

    def _build_device_row(self, u_num, device, height, ports, connected_ports):
        dev_type    = device.get("type", "unknown")
        heeft_front = device.get("front_ports", 0) > 0
        heeft_back  = device.get("back_ports",  0) > 0

        row = _DeviceRow(device["id"], self)
        row.setObjectName(f"device-{dev_type}")
        row.setFixedHeight(_UNIT_H * height)
        row.device_right_clicked.connect(self._show_device_context_menu)

        layout = QHBoxLayout(row)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        # Unitnummer
        num_lbl = QLabel(self._display_unit_number(u_num))
        num_lbl.setObjectName("unit_number")
        num_lbl.setFixedWidth(_UNIT_NUM_W)
        num_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(num_lbl)

        front_ports = [p for p in ports if p["side"] == "front"]
        back_ports  = [p for p in ports if p["side"] == "back"]

        ppr       = device.get("ports_per_row", _MAX_PORTS_ROW)
        sfp_count = device.get("sfp_ports", 0)

        # VOOR-poorten — direct naast unitnummer, geen stretch ervoor
        if heeft_front:
            total_front = device["front_ports"]
            if sfp_count > 0:
                copper_ports = [p for p in front_ports if p["number"] <= total_front]
                sfp_ports_l  = [p for p in front_ports if p["number"] > total_front]
                copper_block = self._build_port_block(
                    copper_ports, "front", total_front, connected_ports, ppr, dev_type)
                sfp_block = self._build_sfp_block(
                    sfp_ports_l, sfp_count, total_front, connected_ports)
                layout.addWidget(copper_block)
                sep = QFrame()
                sep.setFixedWidth(6)
                sep.setStyleSheet("background: transparent;")
                layout.addWidget(sep)
                layout.addWidget(sfp_block)
            else:
                layout.addWidget(self._build_port_block(
                    front_ports, "front", total_front, connected_ports, ppr, dev_type))

        # Naam gecentreerd in de resterende ruimte
        lw = QWidget()
        ll = QVBoxLayout(lw)
        ll.setContentsMargins(4, 0, 4, 0)
        ll.setSpacing(0)
        ll.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        name_lbl = QLabel(device.get("name", ""))
        name_lbl.setObjectName("device-label")
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        type_lbl = QLabel(t(f"device_{dev_type}"))
        type_lbl.setObjectName("device-sublabel")
        type_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ll.addWidget(name_lbl)
        ll.addWidget(type_lbl)
        layout.addWidget(lw, stretch=1)

        # ACHTER-poorten — direct naast naambord rechts, geen stretch erna
        if heeft_back:
            layout.addWidget(self._build_port_block(
                back_ports, "back", device["back_ports"], connected_ports, ppr, dev_type))

        return row

    # ------------------------------------------------------------------
    # Context menu device
    # ------------------------------------------------------------------

    def _show_device_context_menu(self, device_id: str, global_pos):
        menu = QMenu(self)
        act_ports  = menu.addAction(t("ctx_ports_device"))
        menu.addSeparator()
        act_edit   = menu.addAction(t("ctx_edit_device"))
        act_delete = menu.addAction(t("ctx_delete_device"))
        chosen = menu.exec(global_pos)
        if chosen == act_ports:
            self.device_context_menu.emit(device_id, _ACT_PORTS)
        elif chosen == act_edit:
            self.device_context_menu.emit(device_id, _ACT_EDIT)
        elif chosen == act_delete:
            self.device_context_menu.emit(device_id, _ACT_DELETE)

    # ------------------------------------------------------------------
    # Poort blok
    # ------------------------------------------------------------------

    def _build_port_block(self, ports, side, total, connected_ports, ports_per_row: int = _MAX_PORTS_ROW, dev_type: str = ""):
        container = QWidget()
        container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        grid = QVBoxLayout(container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(_PORT_GAP)
        grid.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        port_by_num  = {p["number"]: p for p in ports}
        port_numbers = list(range(1, total + 1))

        # Switches met 2+ rijen: oneven boven, even onder (echte switch nummering)
        if dev_type == "switch" and total > ports_per_row:
            odd_nums  = [n for n in port_numbers if n % 2 == 1]
            even_nums = [n for n in port_numbers if n % 2 == 0]
            rows = []
            for i in range(0, max(len(odd_nums), len(even_nums)), ports_per_row):
                rows.append(odd_nums[i:i + ports_per_row])
                rows.append(even_nums[i:i + ports_per_row])
        else:
            rows = [port_numbers[i:i + ports_per_row]
                    for i in range(0, len(port_numbers), ports_per_row)]

        for row_nums in rows:
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.setSpacing(_PORT_GAP)

            for num in row_nums:
                port    = port_by_num.get(num)
                port_id = port["id"] if port else None
                obj_name = (
                    "port-connected" if port_id and port_id in connected_ports
                    else f"port-{side}"
                )
                btn = QFrame()
                btn.setObjectName(obj_name)
                btn.setFixedSize(_PORT_SIZE, _PORT_SIZE)
                btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

                if port_id:
                    self._port_widgets[port_id] = btn
                    port_name = port.get("name", f"Port {num}")
                    btn.setToolTip(
                        f"{port_name}  ({t('label_' + side)})  "
                        f"{'🔗' if port_id in connected_ports else '○'}"
                    )
                    self._attach_port_click(btn, port_id,
                                            port.get("device_id", ""), side)
                row_l.addWidget(btn)

            row_l.addStretch()
            grid.addWidget(row_w)

        return container

    def _build_sfp_block(self, sfp_ports, sfp_count, copper_offset, connected_ports):
        """SFP poorten: groter, geen label (enkel tooltip), zelfde hoogte als copper rij."""
        _SFP_SIZE = 18

        container = QWidget()
        container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        hl = QHBoxLayout(container)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        sep_lbl = QLabel("SFP")
        sep_lbl.setStyleSheet("font-size: 8px; color: #7ecfff; padding: 0 2px;")
        sep_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        hl.addWidget(sep_lbl)

        port_by_num = {p["number"]: p for p in sfp_ports}
        ports_row = QWidget()
        ports_hl  = QHBoxLayout(ports_row)
        ports_hl.setContentsMargins(0, 0, 0, 0)
        ports_hl.setSpacing(_PORT_GAP)
        ports_hl.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        for i in range(1, sfp_count + 1):
            actual_num = copper_offset + i
            port    = port_by_num.get(actual_num)
            port_id = port["id"] if port else None
            obj_name = (
                "port-connected" if port_id and port_id in connected_ports
                else "port-sfp"
            )
            btn = QFrame()
            btn.setObjectName(obj_name)
            btn.setFixedSize(_SFP_SIZE, _SFP_SIZE)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

            if port_id:
                self._port_widgets[port_id] = btn
                port_name = port.get("name", f"SFP {i}")
                icon = "🔗" if port_id in connected_ports else "o"
                btn.setToolTip(f"{port_name}  (SFP uplink)  {icon}")
                self._attach_port_click(btn, port_id,
                                        port.get("device_id", ""), "front")
            ports_hl.addWidget(btn)

        ports_hl.addStretch()
        hl.addWidget(ports_row)
        return container

    # ------------------------------------------------------------------
    # Poort klik handlers
    # ------------------------------------------------------------------

    def _attach_port_click(self, widget, port_id, device_id, side):
        def on_click(event: QMouseEvent, pid=port_id, did=device_id, s=side):
            if event.button() == Qt.MouseButton.RightButton:
                self.port_context_menu.emit(pid, widget.mapToGlobal(event.position().toPoint()))
                event.accept()
                return
            if self._connect_mode:
                self._handle_connect_click(pid, widget)
            else:
                self._handle_normal_click(pid, did, s, widget)
        widget.mousePressEvent = on_click

    def _handle_normal_click(self, port_id, device_id, side, widget):
        if self._selected_port and self._selected_port in self._port_widgets:
            self._restore_port_style(
                self._selected_port,
                self._port_widgets[self._selected_port]
            )
        self._selected_port = port_id
        widget.setObjectName("port-selected")
        _refresh_style(widget)
        self.port_clicked.emit(port_id, device_id, side)

    def _handle_connect_click(self, port_id, widget):
        if self._selected_port is None:
            self._selected_port = port_id
            widget.setObjectName("port-selected")
            _refresh_style(widget)
            self.port_selected_for_connect.emit(port_id)
        else:
            self._selected_port = None
            self.port_selected_for_connect.emit(port_id)

    def _restore_port_style(self, port_id, widget):
        for p in self._data.get("ports", []):
            if p["id"] == port_id:
                connected = any(
                    c for c in self._data.get("connections", [])
                    if (c["from_type"] == "port" and c["from_id"] == port_id) or
                       (c["to_type"]   == "port" and c["to_id"]   == port_id)
                )
                is_sfp = False
                dev = next((d for d in self._data.get("devices", [])
                            if d["id"] == p.get("device_id")), None)
                if dev and dev.get("sfp_ports", 0) > 0:
                    front = dev.get("front_ports", 0)
                    if p.get("side") == "front" and p.get("number", 0) > front:
                        is_sfp = True
                if connected:
                    obj = "port-connected"
                elif is_sfp:
                    obj = "port-sfp"
                else:
                    obj = f"port-{p['side']}"
                widget.setObjectName(obj)
                _refresh_style(widget)
                return

    # ------------------------------------------------------------------
    # Publieke methodes
    # ------------------------------------------------------------------

    def set_connect_mode(self, active):
        self._connect_mode  = active
        self._selected_port = None

        if active:
            for pid, w in self._port_widgets.items():
                self._restore_port_style(pid, w)
            for pid, w in self._port_widgets.items():
                current = w.objectName()
                if current not in ("port-connected", "port-selected"):
                    w.setObjectName("port-connect-mode")
                    _refresh_style(w)
        else:
            for pid, w in self._port_widgets.items():
                self._restore_port_style(pid, w)

    def refresh(self, data):
        """Herlaad rack inhoud — verwijdert bestaande widgets direct via setParent(None)."""
        self._data = data
        self._port_widgets.clear()
        self._selected_port = None

        layout = self.layout()

        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

        self._populate(layout)

        self.updateGeometry()
        self.update()

    def highlight_trace(self, port_ids: list):
        for pid, widget in self._port_widgets.items():
            if pid in port_ids:
                widget.setObjectName("port-trace")
                _refresh_style(widget)
            elif pid != self._selected_port:
                self._restore_port_style(pid, widget)

    def clear_trace_highlight(self):
        for pid, widget in self._port_widgets.items():
            if widget.objectName() == "port-trace":
                self._restore_port_style(pid, widget)


# ---------------------------------------------------------------------------
# _DeviceRow
# ---------------------------------------------------------------------------

class _DeviceRow(QFrame):
    device_right_clicked = Signal(str, object)

    def __init__(self, device_id: str, parent=None):
        super().__init__(parent)
        self._device_id = device_id

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            self.device_right_clicked.emit(
                self._device_id,
                self.mapToGlobal(event.position().toPoint())
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            rack_view = self.parent()
            while rack_view and not hasattr(rack_view, "device_double_clicked"):
                rack_view = rack_view.parent()
            if rack_view:
                rack_view.device_double_clicked.emit(self._device_id)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)