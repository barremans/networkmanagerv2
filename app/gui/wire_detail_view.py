# =============================================================================
# Networkmap_Creator
# File:    app/gui/wire_detail_view.py
# Role:    Trace visualisatie in het detail frame onderaan
# Version: 1.6.0
# Author:  Barremans
# Changes: 1.4.0 — edit_connection signal + bewerk-knop + refresh_info()
#          1.5.0 — VLAN label tonen per stap: "Port 1 (FRONT) (VLAN 110)"
#          1.6.0 — B2: rack-nav knoppen alleen tonen bij 2+ racks (cross-rack trace)
#                   B5: rack-wissel zichtbaar als tussenstap in de ketting bij cross-rack traces
# =============================================================================

from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton,
    QHBoxLayout, QVBoxLayout, QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt, Signal

from app.helpers.i18n import t

# Kabeltype → i18n sleutel + QSS objectName
_CABLE_META = {
    "utp_cat5e":  ("cable_utp_cat5e",  "cable-utp-cat5e"),
    "utp_cat6":   ("cable_utp_cat6",   "cable-utp-cat6"),
    "utp_cat6a":  ("cable_utp_cat6a",  "cable-utp-cat6a"),
    "fiber_sm":   ("cable_fiber_sm",   "cable-fiber-sm"),
    "fiber_mm":   ("cable_fiber_mm",   "cable-fiber-mm"),
    "dak":        ("cable_dak",        "cable-dak"),
    "other":      ("cable_other",      "cable-other"),
    "":           ("cable_other",      "cable-other"),
}

# Icoon per staptype
_STEP_ICON = {
    "endpoint":    "💻",
    "wall_outlet": "🌐",
    "port":        "⬡",
}


def _vlan_for_step(step: dict, data: dict | None) -> int | None:
    """
    Geef het VLAN nummer terug voor een stap, of None.
    - port      → data["ports"][x]["vlan"]
    - wall_outlet → data["sites"][..]["wall_outlets"][x]["vlan"]
    """
    if not data:
        return None
    obj_type = step.get("obj_type", "")
    obj_id   = step.get("obj_id", "")

    if obj_type == "port":
        for p in data.get("ports", []):
            if p["id"] == obj_id:
                v = p.get("vlan")
                return int(v) if v else None

    elif obj_type == "wall_outlet":
        for s in data.get("sites", []):
            for r in s.get("rooms", []):
                for wo in r.get("wall_outlets", []):
                    if wo["id"] == obj_id:
                        v = wo.get("vlan")
                        return int(v) if v else None
    return None


class WireDetailView(QWidget):
    """
    Toont de volledige trace als horizontale ketting van stappen.
    Signalen:
      delete_connection(conn_id)          — verbinding verwijderen
      edit_connection(conn_id)            — verbinding bewerken  [1.4.0]
      navigate_to_rack(rack_id, port_ids) — E5: navigeer naar rack + highlight
    """
    delete_connection = Signal(str)
    edit_connection   = Signal(str)
    navigate_to_rack  = Signal(str, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_conn_id = None
        self._current_data    = None
        self._build_skeleton()
        self.hide()

    # ------------------------------------------------------------------
    # Skelet opbouw (eenmalig)
    # ------------------------------------------------------------------

    def _build_skeleton(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 4, 12, 4)
        outer.setSpacing(2)

        title_row = QHBoxLayout()
        self._title_lbl = QLabel("")
        self._title_lbl.setObjectName("trace_title")

        self._btn_edit = QPushButton(t("wire_edit_btn"))
        self._btn_edit.setObjectName("btn_secondary")
        self._btn_edit.setFixedHeight(22)
        self._btn_edit.hide()
        self._btn_edit.clicked.connect(self._on_edit_clicked)

        self._btn_delete = QPushButton(t("wire_delete_btn"))
        self._btn_delete.setObjectName("btn_danger")
        self._btn_delete.setFixedHeight(22)
        self._btn_delete.hide()
        self._btn_delete.clicked.connect(self._on_delete_clicked)

        title_row.addWidget(self._title_lbl)
        title_row.addStretch()
        title_row.addWidget(self._btn_edit)
        title_row.addWidget(self._btn_delete)
        outer.addLayout(title_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFixedHeight(38)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._chain_widget = QWidget()
        self._chain_layout = QHBoxLayout(self._chain_widget)
        self._chain_layout.setContentsMargins(0, 0, 0, 0)
        self._chain_layout.setSpacing(0)
        self._chain_layout.setAlignment(Qt.AlignmentFlag.AlignLeft |
                                        Qt.AlignmentFlag.AlignVCenter)
        scroll.setWidget(self._chain_widget)
        outer.addWidget(scroll)

        self._info_lbl = QLabel("")
        self._info_lbl.setObjectName("trace_info")
        outer.addWidget(self._info_lbl)

        self._rack_nav_row = QHBoxLayout()
        self._rack_nav_row.setSpacing(6)
        self._rack_nav_row.setContentsMargins(0, 2, 0, 0)
        self._rack_nav_lbl = QLabel(f"🗄  {t('trace_racks')}:")
        self._rack_nav_lbl.setObjectName("trace_info")
        self._rack_nav_row.addWidget(self._rack_nav_lbl)
        self._rack_nav_frame = QWidget()
        self._rack_nav_frame_layout = QHBoxLayout(self._rack_nav_frame)
        self._rack_nav_frame_layout.setContentsMargins(0, 0, 0, 0)
        self._rack_nav_frame_layout.setSpacing(4)
        self._rack_nav_row.addWidget(self._rack_nav_frame)
        self._rack_nav_row.addStretch()
        self._rack_nav_widget = QWidget()
        self._rack_nav_widget.setLayout(self._rack_nav_row)
        self._rack_nav_widget.hide()
        outer.addWidget(self._rack_nav_widget)

    # ------------------------------------------------------------------
    # Publieke API
    # ------------------------------------------------------------------

    def set_trace(self, steps: list[dict], origin_label: str = "",
                  conn_id: str = "", data: dict = None):
        self._clear_chain()
        self._current_conn_id = conn_id
        self._current_data    = data
        self._clear_rack_nav()

        if not steps:
            self.hide()
            return

        self._title_lbl.setText(f"📌  {origin_label}" if origin_label else "📌")

        cable_type = next(
            (s["cable_type"] for s in steps if s.get("cable_type")), ""
        )
        i18n_key, _ = _CABLE_META.get(cable_type, ("cable_other", "cable-other"))
        self._update_info_lbl(i18n_key, data, conn_id)

        # B5 — bouw een port_id → (rack_id, rack_name) lookup voor cross-rack labels
        _port_rack: dict[str, tuple[str, str]] = {}
        if data:
            for _s in data.get("sites", []):
                for _r in _s.get("rooms", []):
                    for _rk in _r.get("racks", []):
                        for _sl in _rk.get("slots", []):
                            _dev_id = _sl.get("device_id", "")
                            for _p in data.get("ports", []):
                                if _p.get("device_id") == _dev_id:
                                    _port_rack[_p["id"]] = (_rk["id"], _rk["name"])

        _prev_rack_id: str | None = None
        for idx, step in enumerate(steps):
            # B5 — injecteer rack-label als de rack wisselt tussen opeenvolgende port-stappen
            if step["obj_type"] == "port":
                rack_info = _port_rack.get(step["obj_id"])
                if rack_info:
                    cur_rack_id, cur_rack_name = rack_info
                    if _prev_rack_id is not None and cur_rack_id != _prev_rack_id:
                        self._chain_layout.addWidget(
                            self._make_rack_label(cur_rack_name)
                        )
                    _prev_rack_id = cur_rack_id

            self._chain_layout.addWidget(self._make_node(step, data))
            if idx < len(steps) - 1:
                self._chain_layout.addWidget(
                    self._make_arrow(step.get("cable_type", ""))
                )

        self._chain_layout.addStretch()

        if conn_id:
            self._btn_edit.show()
            self._btn_delete.show()
        else:
            self._btn_edit.hide()
            self._btn_delete.hide()

        if data:
            self._build_rack_nav(steps, data)

        self.show()

    def refresh_info(self, data: dict):
        if not self._current_conn_id or not data:
            return
        conn = next(
            (c for c in data.get("connections", [])
             if c.get("id") == self._current_conn_id),
            None
        )
        if not conn:
            return
        cable_type = conn.get("cable_type", "")
        i18n_key, _ = _CABLE_META.get(cable_type, ("cable_other", "cable-other"))
        self._update_info_lbl(i18n_key, data, self._current_conn_id)

    def _update_info_lbl(self, i18n_key: str, data: dict | None, conn_id: str):
        parts = [f"{t('label_cable_type')}: {t(i18n_key)}"]
        if data and conn_id:
            conn = next(
                (c for c in data.get("connections", []) if c.get("id") == conn_id),
                None
            )
            if conn and conn.get("label"):
                parts.append(f"  ·  🏷  {conn['label']}")
        self._info_lbl.setText("".join(parts))

    def _on_delete_clicked(self):
        if self._current_conn_id:
            self.delete_connection.emit(self._current_conn_id)

    def _on_edit_clicked(self):
        if self._current_conn_id:
            self.edit_connection.emit(self._current_conn_id)

    def clear(self):
        self._clear_chain()
        self._clear_rack_nav()
        self._title_lbl.setText("")
        self._info_lbl.setText("")
        self._current_conn_id = None
        self._current_data    = None
        self._btn_edit.hide()
        self._btn_delete.hide()
        self.hide()

    def _build_rack_nav(self, steps: list[dict], data: dict):
        port_to_rack = {}
        for site in data.get("sites", []):
            for room in site.get("rooms", []):
                for rack in room.get("racks", []):
                    for slot in rack.get("slots", []):
                        dev_id = slot.get("device_id", "")
                        for port in data.get("ports", []):
                            if port.get("device_id") == dev_id:
                                dev = next(
                                    (d for d in data.get("devices", [])
                                     if d["id"] == dev_id), None
                                )
                                port_to_rack[port["id"]] = (
                                    rack["id"],
                                    rack["name"],
                                    dev["name"] if dev else "",
                                    room["name"],
                                )

        seen_racks = {}
        rack_order = []
        for step in steps:
            if step["obj_type"] == "port":
                info = port_to_rack.get(step["obj_id"])
                if info:
                    rack_id, rack_name, dev_name, room_name = info
                    if rack_id not in seen_racks:
                        seen_racks[rack_id] = (rack_name, room_name, [])
                        rack_order.append(rack_id)
                    seen_racks[rack_id][2].append(step["obj_id"])

        # B2 — rack-nav knoppen alleen tonen bij 2+ racks (cross-rack trace)
        if len(rack_order) < 2:
            self._rack_nav_widget.hide()
            return

        for rack_id in rack_order:
            rack_name, room_name, port_ids = seen_racks[rack_id]
            btn = QPushButton(f"🗄  {rack_name}")
            btn.setObjectName("btn_rack_nav")
            btn.setToolTip(f"{room_name}  —  {len(port_ids)} poort(en) in trace")
            btn.setFixedHeight(22)
            btn.clicked.connect(
                lambda checked=False, rid=rack_id, pids=list(port_ids):
                    self.navigate_to_rack.emit(rid, pids)
            )
            self._rack_nav_frame_layout.addWidget(btn)

        self._rack_nav_widget.show()

    def _clear_rack_nav(self):
        while self._rack_nav_frame_layout.count():
            item = self._rack_nav_frame_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._rack_nav_widget.hide()

    # ------------------------------------------------------------------
    # Stap node — 1.5.0: VLAN label toevoegen
    # ------------------------------------------------------------------

    def _make_node(self, step: dict, data: dict | None = None) -> QFrame:
        """Bouwt één stap blokje: [icoon  label  (VLAN x)]."""
        obj_type = step.get("obj_type", "port")
        label    = step.get("label", "?")
        icon     = _STEP_ICON.get(obj_type, "⬡")

        # VLAN ophalen voor deze stap
        vlan = _vlan_for_step(step, data)

        frame = QFrame()
        frame.setObjectName("trace_step")
        frame.setSizePolicy(QSizePolicy.Policy.Preferred,
                            QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(4)

        icon_lbl = QLabel(icon)
        icon_lbl.setObjectName("trace_step")
        icon_lbl.setFixedWidth(14)

        text_lbl = QLabel(label)
        text_lbl.setObjectName("trace_step")
        text_lbl.setSizePolicy(QSizePolicy.Policy.Preferred,
                               QSizePolicy.Policy.Fixed)

        layout.addWidget(icon_lbl)
        layout.addWidget(text_lbl)

        # VLAN badge
        if vlan is not None:
            try:
                from app.services.vlan_service import get_vlan_by_id
                vdef   = get_vlan_by_id(vlan)
                color  = vdef.get("color", "#4a9eda") if vdef else "#4a9eda"
                vlabel = f"VLAN {vlan}"
            except Exception:
                color  = "#4a9eda"
                vlabel = f"VLAN {vlan}"

            vlan_lbl = QLabel(f"({vlabel})")
            vlan_lbl.setStyleSheet(
                f"color: {color}; font-size: 9pt; font-style: italic;"
            )
            vlan_lbl.setSizePolicy(QSizePolicy.Policy.Preferred,
                                   QSizePolicy.Policy.Fixed)
            layout.addWidget(vlan_lbl)

        side = step.get("side", "")
        if side:
            frame.setToolTip(f"{t('label_' + side)}")

        return frame

    # ------------------------------------------------------------------
    # Rack-wissel label — B5
    # ------------------------------------------------------------------

    def _make_rack_label(self, rack_name: str) -> QFrame:
        """B5 — Visuele tussenstap die een rack-wissel aangeeft in de ketting."""
        frame = QFrame()
        frame.setObjectName("trace_step_rack")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)
        lbl = QLabel(f"🗄 {rack_name}")
        lbl.setObjectName("trace_step_rack")
        lbl.setStyleSheet("color: #E69F00; font-size: 8pt; font-style: italic;")
        layout.addWidget(lbl)
        return frame

    # ------------------------------------------------------------------
    # Pijl tussen stappen
    # ------------------------------------------------------------------

    def _make_arrow(self, cable_type: str) -> QLabel:
        _, obj_name = _CABLE_META.get(cable_type, ("cable_other", "cable-other"))
        arrow = QLabel(" ──► ")
        arrow.setObjectName("trace_arrow")
        arrow.setProperty("cable", obj_name)
        arrow.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        color_map = {
            "cable-utp-cat5e":  ("#56B4E9", "══"),
            "cable-utp-cat6":   ("#009E73", "══"),
            "cable-utp-cat6a":  ("#0072B2", "══"),
            "cable-fiber-sm":   ("#F0E442", "──"),
            "cable-fiber-mm":   ("#E69F00", "──"),
            "cable-dak":        ("#D55E00", "~~"),
            "cable-other":      ("#CC79A7", "··"),
        }
        color, symbol = color_map.get(obj_name, ("#CC79A7", "··"))
        arrow.setText(f" {symbol}► ")
        arrow.setStyleSheet(f"color: {color}; font-size: 10pt;")
        return arrow

    # ------------------------------------------------------------------
    # Intern: ketting leegmaken
    # ------------------------------------------------------------------

    def _clear_chain(self):
        while self._chain_layout.count():
            item = self._chain_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()