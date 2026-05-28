# =============================================================================
# Networkmap_Creator
# File:    app/gui/outlet_locator_view.py
# Role:    Wandpunten overzicht — omgekeerde trace UX
# Version: 1.1.0
# Author:  Barremans
# Changes: 1.1.0 — Titel toont site naam ipv generieke label
#                   Dubbelklik op kaartje → _OutletDetailDialog (zelfde als WallOutletView)
#                   Rechtsklik op kaartje → contextmenu (Bewerken, Eindapparaat,
#                   Koppelen/Loskoppelen, Dupliceren, Verwijderen)
#                   Signals toegevoegd: outlet_edit_requested, outlet_delete_requested,
#                   outlet_duplicate_requested, outlet_endpoint_requested,
#                   outlet_connect_port_requested, outlet_disconnect_requested
#          1.0.1 — Initiële versie
# =============================================================================
#
# Use case: technicus staat in een ruimte, kiest ruimte → ziet wandpunten →
# klikt op wandpunt → ziet trace naar patchpanel/switch in één compacte regel.
#
# Bereikbaar via: Toolbar → Wandpunten overzicht (Ctrl+W)
# Ruimte kiezen: dropdown of klik op ruimte in de linkerboom (via set_room())
# =============================================================================

from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QComboBox, QLineEdit,
    QScrollArea, QVBoxLayout, QHBoxLayout, QGridLayout,
    QSizePolicy, QMenu
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QCursor

from app.helpers.i18n import t
from app.services import tracing


# ---------------------------------------------------------------------------
# Hulp — compacte trace samenvatting op één regel
# ---------------------------------------------------------------------------

def _compact_trace(steps: list[dict]) -> str:
    """
    Bouw één compacte regel: PP-naam poort N ► switch-naam poort M
    Toont enkel de zinvolle eindpunten, geen tussenliggende stappen.
    """
    if not steps:
        return t("outlet_no_trace")

    port_steps = [s for s in steps if s["obj_type"] == "port"]
    ep_steps   = [s for s in steps if s["obj_type"] == "endpoint"]

    if not port_steps:
        if ep_steps:
            return f"💻  {ep_steps[0]['label']}"
        return t("outlet_no_trace")

    first = port_steps[0]
    last  = port_steps[-1]

    cable = next((s.get("cable_type", "") for s in steps if s.get("cable_type")), "")
    cable_icon = {
        "utp_cat5e": "🔵", "utp_cat6": "🟢", "utp_cat6a": "🔷",
        "fiber_sm":  "🟡", "fiber_mm": "🟠",
        "dak":       "🟥", "other":    "🟣",
    }.get(cable, "⚪")

    parts = []
    if ep_steps:
        parts.append(f"💻 {ep_steps[0]['label']}")
    parts.append(f"⬡ {first['label']}")
    if first["obj_id"] != last["obj_id"]:
        parts.append(f"⬡ {last['label']}")

    return f"  {cable_icon}  " + "  ►  ".join(parts)


# ---------------------------------------------------------------------------
# Wandpunt kaartje
# ---------------------------------------------------------------------------

class _OutletCard(QFrame):
    """
    Klikbaar kaartje voor één wandpunt met naam, locatie en compacte trace.
    1.1.0 — dubbelklik en rechtsklik worden afgehandeld door OutletLocatorView.
    """

    clicked = Signal(str)   # outlet_id

    def __init__(self, outlet: dict, trace: list, parent=None):
        super().__init__(parent)
        self._outlet_id = outlet["id"]
        self.setObjectName("wall-outlet")
        self.setFixedSize(240, 76)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 4)
        layout.setSpacing(2)

        name_lbl = QLabel(f"🌐  {outlet.get('name', '')}")
        name_lbl.setObjectName("outlet-label")
        layout.addWidget(name_lbl)

        loc = outlet.get("location_description", "")
        if loc:
            loc_lbl = QLabel(loc)
            loc_lbl.setObjectName("secondary")
            loc_lbl.setWordWrap(False)
            layout.addWidget(loc_lbl)

        layout.addStretch()

        trace_lbl = QLabel(_compact_trace(trace))
        trace_lbl.setObjectName("secondary")
        trace_lbl.setWordWrap(False)
        layout.addWidget(trace_lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._outlet_id)
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# Hoofd view
# ---------------------------------------------------------------------------

class OutletLocatorView(QWidget):
    """
    Wandpunten overzicht en trace view.

    Signalen:
      outlet_selected(outlet_id, steps)       — trace beschikbaar voor wire_detail
      room_navigate_requested(room_id)         — vraag boom om ruimte te selecteren
      outlet_edit_requested(outlet_id)         — 1.1.0: bewerken
      outlet_delete_requested(outlet_id)       — 1.1.0: verwijderen
      outlet_duplicate_requested(outlet_id)    — 1.1.0: dupliceren
      outlet_endpoint_requested(outlet_id)     — 1.1.0: eindapparaat toevoegen/bewerken
      outlet_connect_port_requested(outlet_id) — 1.1.0: koppelen aan poort
      outlet_disconnect_requested(outlet_id)   — 1.1.0: verbinding verwijderen
    """

    outlet_selected              = Signal(str, list)
    room_navigate_requested      = Signal(str)
    outlet_edit_requested        = Signal(str)
    outlet_delete_requested      = Signal(str)
    outlet_duplicate_requested   = Signal(str)
    outlet_endpoint_requested    = Signal(str)
    outlet_connect_port_requested = Signal(str)
    outlet_disconnect_requested  = Signal(str)

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self._data            = data
        self._current_room_id = None
        self._cards           = {}   # outlet_id → _OutletCard
        self._outlets_map     = {}   # outlet_id → outlet dict
        self._selected_id     = None
        self._build()

    # ------------------------------------------------------------------
    # UI opbouw
    # ------------------------------------------------------------------

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Titelregel ──────────────────────────────────────────────
        title_bar = QFrame()
        title_bar.setObjectName("rack_frame")
        tl = QHBoxLayout(title_bar)
        tl.setContentsMargins(8, 4, 8, 4)
        tl.setSpacing(8)

        self._title_lbl = QLabel(f"🌐  {t('menu_outlet_locator')}")
        self._title_lbl.setObjectName("rack_title")
        tl.addWidget(self._title_lbl)
        tl.addStretch()
        outer.addWidget(title_bar)

        # ── Filter balk ─────────────────────────────────────────────
        filter_bar = QFrame()
        filter_bar.setObjectName("toolbar_frame")
        fl = QHBoxLayout(filter_bar)
        fl.setContentsMargins(8, 6, 8, 6)
        fl.setSpacing(8)

        room_lbl = QLabel(t("label_room") + ":")
        room_lbl.setFixedWidth(60)
        fl.addWidget(room_lbl)

        self._ddl_room = QComboBox()
        self._ddl_room.setMinimumWidth(200)
        self._ddl_room.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._ddl_room.currentIndexChanged.connect(self._on_room_changed)
        fl.addWidget(self._ddl_room)

        self._search = QLineEdit()
        self._search.setPlaceholderText(f"🔍  {t('outlet_filter_placeholder')}")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._on_filter_changed)
        fl.addWidget(self._search, stretch=1)

        outer.addWidget(filter_bar)

        # ── Info regel ──────────────────────────────────────────────
        self._info_lbl = QLabel("")
        self._info_lbl.setObjectName("secondary")
        self._info_lbl.setContentsMargins(12, 4, 12, 0)
        outer.addWidget(self._info_lbl)

        # ── Kaartjes gebied ─────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(12, 12, 12, 12)
        self._body_layout.setSpacing(8)
        self._body_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._scroll.setWidget(self._body)
        outer.addWidget(self._scroll, stretch=1)

        self._populate_room_ddl()
        self._refresh_cards()

    # ------------------------------------------------------------------
    # Dropdown populeren
    # ------------------------------------------------------------------

    def _populate_room_ddl(self, select_room_id: str = None):
        self._ddl_room.blockSignals(True)
        self._ddl_room.clear()
        self._ddl_room.addItem(f"— {t('label_room')} —", "")

        select_idx = 0
        for site in self._data.get("sites", []):
            for room in site.get("rooms", []):
                n_outlets = len(room.get("wall_outlets", []))
                label = (
                    f"{site['name']}  /  {room['name']}"
                    f"  ({n_outlets})"
                )
                self._ddl_room.addItem(label, room["id"])
                if room["id"] == select_room_id:
                    select_idx = self._ddl_room.count() - 1

        self._ddl_room.blockSignals(False)
        self._ddl_room.setCurrentIndex(select_idx)
        self._current_room_id = self._ddl_room.currentData() or None

    # ------------------------------------------------------------------
    # Kaartjes
    # ------------------------------------------------------------------

    def _refresh_cards(self):
        while self._body_layout.count():
            item = self._body_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
        self._cards.clear()
        self._outlets_map.clear()
        self._selected_id = None

        # 1.1.0 — Titel bijwerken met site naam
        self._update_title()

        room    = self._find_room(self._current_room_id)
        outlets = room.get("wall_outlets", []) if room else []
        filter_text = self._search.text().strip().lower()

        if filter_text:
            outlets = [
                wo for wo in outlets
                if filter_text in wo.get("name", "").lower()
                or filter_text in wo.get("location_description", "").lower()
            ]

        if not outlets:
            msg = (
                t("outlet_locator_choose_room")
                if not self._current_room_id
                else t("outlet_locator_no_outlets")
            )
            empty = QLabel(msg)
            empty.setObjectName("secondary")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._body_layout.addWidget(
                empty, alignment=Qt.AlignmentFlag.AlignCenter)
            self._info_lbl.setText("")
            return

        site_name = ""
        for site in self._data.get("sites", []):
            for r in site.get("rooms", []):
                if r["id"] == self._current_room_id:
                    site_name = site["name"]
        self._info_lbl.setText(
            f"{site_name}  ·  {room['name']}"
            f"  —  {len(outlets)} {t('tree_wall_outlets').lower()}"
        )

        col_count = 3
        grid = QGridLayout()
        grid.setSpacing(8)

        for idx, outlet in enumerate(outlets):
            self._outlets_map[outlet["id"]] = outlet
            trace = tracing.trace_from_wall_outlet(self._data, outlet["id"])
            card  = _OutletCard(outlet, trace, parent=self._body)
            card.clicked.connect(self._on_card_clicked)

            # 1.1.0 — dubbelklik en rechtsklik
            card.mouseDoubleClickEvent = lambda e, oid=outlet["id"], o=outlet: \
                self._on_card_double_clicked(oid, o)
            card.contextMenuEvent = lambda e, oid=outlet["id"]: \
                self._on_card_context_menu(oid, e)

            self._cards[outlet["id"]] = card
            grid.addWidget(card, idx // col_count, idx % col_count)

        remainder = len(outlets) % col_count
        if remainder:
            for i in range(col_count - remainder):
                spacer = QWidget()
                spacer.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Preferred)
                grid.addWidget(
                    spacer,
                    len(outlets) // col_count,
                    remainder + i)

        self._body_layout.addLayout(grid)
        self._body_layout.addStretch()

    def _update_title(self):
        """1.1.0 — Titelregel bijwerken met site naam als ruimte geselecteerd is."""
        if self._current_room_id:
            for site in self._data.get("sites", []):
                for room in site.get("rooms", []):
                    if room["id"] == self._current_room_id:
                        self._title_lbl.setText(
                            f"🌐  {t('menu_outlet_locator')}  —  {site['name']}"
                        )
                        return
        self._title_lbl.setText(f"🌐  {t('menu_outlet_locator')}")

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ------------------------------------------------------------------
    # Handlers — klik, dubbelklik, rechtsklik
    # ------------------------------------------------------------------

    def _on_card_clicked(self, outlet_id: str):
        """Enkele klik — highlight kaartje + emit trace."""
        if self._selected_id and self._selected_id in self._cards:
            prev = self._cards[self._selected_id]
            prev.setObjectName("wall-outlet")
            prev.setStyle(prev.style())

        self._selected_id = outlet_id
        card = self._cards.get(outlet_id)
        if card:
            card.setObjectName("wall-outlet-selected")
            card.setStyle(card.style())

        steps = tracing.trace_from_wall_outlet(self._data, outlet_id)
        self.outlet_selected.emit(outlet_id, steps)

    def _on_card_double_clicked(self, outlet_id: str, outlet: dict):
        """
        1.1.0 — Dubbelklik → detail popup (zelfde als WallOutletView).
        Gebruikt _OutletDetailDialog uit wall_outlet_view.
        """
        from app.gui.wall_outlet_view import _OutletDetailDialog
        from PySide6.QtCore import QTimer

        ep_map = {e["id"]: e for e in self._data.get("endpoints", [])}
        ep     = ep_map.get(outlet.get("endpoint_id", ""))

        def _emit_edit():
            QTimer.singleShot(0, lambda: self.outlet_edit_requested.emit(outlet_id))

        def _emit_connect():
            QTimer.singleShot(0, lambda: self.outlet_connect_port_requested.emit(outlet_id))

        def _emit_ep():
            QTimer.singleShot(0, lambda: self.outlet_endpoint_requested.emit(outlet_id))

        dlg = _OutletDetailDialog(
            outlet, ep, self._data, parent=self,
            on_endpoint_clicked=_emit_ep,
            on_edit_clicked=_emit_edit,
            on_connect_clicked=_emit_connect,
        )
        dlg.exec()

    def _on_card_context_menu(self, outlet_id: str, event):
        """
        1.1.0 — Rechtsklik → contextmenu (zelfde opties als WallOutletView).
        """
        is_connected = any(
            c for c in self._data.get("connections", [])
            if c.get("from_id") == outlet_id or c.get("to_id") == outlet_id
        )
        menu = QMenu(self)
        act_edit    = menu.addAction("✏  " + t("ctx_edit"))
        act_ep      = menu.addAction("🖥  " + t("btn_new_endpoint"))
        act_connect    = None
        act_disconnect = None
        if not is_connected:
            act_connect = menu.addAction("🔌  " + t("ctx_connect_outlet_to_port"))
        else:
            act_disconnect = menu.addAction("✂  " + t("ctx_disconnect_port"))
        act_dup = menu.addAction("⧉  " + t("ctx_duplicate"))
        menu.addSeparator()
        act_del = menu.addAction("🗑  " + t("ctx_delete"))

        action = menu.exec(QCursor.pos())
        if action == act_edit:
            self.outlet_edit_requested.emit(outlet_id)
        elif action == act_ep:
            self.outlet_endpoint_requested.emit(outlet_id)
        elif act_connect and action == act_connect:
            self.outlet_connect_port_requested.emit(outlet_id)
        elif act_disconnect and action == act_disconnect:
            self.outlet_disconnect_requested.emit(outlet_id)
        elif action == act_dup:
            self.outlet_duplicate_requested.emit(outlet_id)
        elif action == act_del:
            self.outlet_delete_requested.emit(outlet_id)

    # ------------------------------------------------------------------
    # Handlers — dropdown en filter
    # ------------------------------------------------------------------

    def _on_room_changed(self, _index: int):
        self._current_room_id = self._ddl_room.currentData() or None
        self._search.clear()
        self._refresh_cards()
        if self._current_room_id:
            self.room_navigate_requested.emit(self._current_room_id)

    def _on_filter_changed(self, _text: str):
        self._refresh_cards()

    # ------------------------------------------------------------------
    # Publieke API
    # ------------------------------------------------------------------

    def set_room(self, room_id: str):
        if room_id == self._current_room_id:
            return
        idx = self._ddl_room.findData(room_id)
        if idx >= 0:
            self._ddl_room.blockSignals(True)
            self._ddl_room.setCurrentIndex(idx)
            self._ddl_room.blockSignals(False)
            self._current_room_id = room_id
            self._search.clear()
            self._refresh_cards()

    def refresh(self, data: dict):
        self._data = data
        cur = self._current_room_id
        self._populate_room_ddl(select_room_id=cur)
        self._refresh_cards()

    # ------------------------------------------------------------------
    # Hulp
    # ------------------------------------------------------------------

    def _find_room(self, room_id: str) -> dict | None:
        if not room_id:
            return None
        for site in self._data.get("sites", []):
            for room in site.get("rooms", []):
                if room["id"] == room_id:
                    return room
        return None