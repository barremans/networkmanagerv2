# =============================================================================
# Networkmap_Creator
# File:    app/gui/outlet_locator_view.py
# Role:    Wandpunten zoek- en trace view — omgekeerde trace UX
# Version: 1.0.1
# Author:  Barremans
# =============================================================================
#
# Use case: technicus staat in een ruimte, kiest ruimte → ziet wandpunten →
# klikt op wandpunt → ziet trace naar patchpanel/switch in één compacte regel.
#
# Bereikbaar via: Hulpmiddelen → Wandpunten zoeken (Ctrl+W)
# Ruimte kiezen: dropdown of klik op ruimte in de linkerboom (via set_room())
# =============================================================================

from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QComboBox, QLineEdit,
    QScrollArea, QVBoxLayout, QHBoxLayout, QGridLayout,
    QSizePolicy, QToolButton
)
from PySide6.QtCore import Qt, Signal
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

    # Alle port-stappen
    port_steps = [s for s in steps if s["obj_type"] == "port"]
    ep_steps   = [s for s in steps if s["obj_type"] == "endpoint"]

    if not port_steps:
        if ep_steps:
            return f"💻  {ep_steps[0]['label']}"
        return t("outlet_no_trace")

    # Eerste poort (patchpanel back) en laatste poort (switch)
    first = port_steps[0]
    last  = port_steps[-1]

    # Kabeltype uit eerste verbinding
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
    """Klikbaar kaartje voor één wandpunt met naam, locatie en compacte trace."""

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

        # Naam
        name_lbl = QLabel(f"🌐  {outlet.get('name', '')}")
        name_lbl.setObjectName("outlet-label")
        layout.addWidget(name_lbl)

        # Locatie
        loc = outlet.get("location_description", "")
        if loc:
            loc_lbl = QLabel(loc)
            loc_lbl.setObjectName("secondary")
            loc_lbl.setWordWrap(False)
            layout.addWidget(loc_lbl)

        layout.addStretch()

        # Compacte trace
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
    Wandpunten zoek- en trace view.

    Signalen:
      outlet_selected(outlet_id, steps)  — trace beschikbaar voor wire_detail
      room_navigate_requested(room_id)   — vraag boom om ruimte te selecteren
    """

    outlet_selected          = Signal(str, list)   # outlet_id, trace steps
    room_navigate_requested  = Signal(str)          # room_id

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self._data        = data
        self._current_room_id = None
        self._cards       = {}   # outlet_id → _OutletCard
        self._selected_id = None
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

        title_lbl = QLabel(f"🌐  {t('menu_outlet_locator')}")
        title_lbl.setObjectName("rack_title")
        tl.addWidget(title_lbl)
        tl.addStretch()
        outer.addWidget(title_bar)

        # ── Filter balk ─────────────────────────────────────────────
        filter_bar = QFrame()
        filter_bar.setObjectName("toolbar_frame")
        fl = QHBoxLayout(filter_bar)
        fl.setContentsMargins(8, 6, 8, 6)
        fl.setSpacing(8)

        # Ruimte dropdown
        room_lbl = QLabel(t("label_room") + ":")
        room_lbl.setFixedWidth(60)
        fl.addWidget(room_lbl)

        self._ddl_room = QComboBox()
        self._ddl_room.setMinimumWidth(200)
        self._ddl_room.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._ddl_room.currentIndexChanged.connect(self._on_room_changed)
        fl.addWidget(self._ddl_room)

        # Zoekfilter
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

        # Eerste populatie
        self._populate_room_ddl()
        self._refresh_cards()

    # ------------------------------------------------------------------
    # Dropdown populeren
    # ------------------------------------------------------------------

    def _populate_room_ddl(self, select_room_id: str = None):
        """Vul de ruimte-dropdown met alle ruimtes van alle sites."""
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
        """Herbouw kaartjes voor de geselecteerde ruimte."""
        # Verwijder oude kaartjes
        while self._body_layout.count():
            item = self._body_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
        self._cards.clear()
        self._selected_id = None

        room = self._find_room(self._current_room_id)
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

        # Info
        site_name = ""
        for site in self._data.get("sites", []):
            for r in site.get("rooms", []):
                if r["id"] == self._current_room_id:
                    site_name = site["name"]
        self._info_lbl.setText(
            f"{site_name}  ·  {room['name']}"
            f"  —  {len(outlets)} {t('tree_wall_outlets').lower()}"
        )

        # Kaartjes in grid (3 per rij)
        col_count = 3
        grid = QGridLayout()
        grid.setSpacing(8)

        for idx, outlet in enumerate(outlets):
            trace = tracing.trace_from_wall_outlet(self._data, outlet["id"])
            card  = _OutletCard(outlet, trace, parent=self._body)
            card.clicked.connect(self._on_card_clicked)
            self._cards[outlet["id"]] = card
            grid.addWidget(card, idx // col_count, idx % col_count)

        # Opvullen
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

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_room_changed(self, _index: int):
        self._current_room_id = self._ddl_room.currentData() or None
        self._search.clear()
        self._refresh_cards()
        if self._current_room_id:
            self.room_navigate_requested.emit(self._current_room_id)

    def _on_filter_changed(self, _text: str):
        self._refresh_cards()

    def _on_card_clicked(self, outlet_id: str):
        """Wandpunt geselecteerd — highlight kaartje, emit trace."""
        # Deselecteer vorige
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

    # ------------------------------------------------------------------
    # Publieke API
    # ------------------------------------------------------------------

    def set_room(self, room_id: str):
        """
        Gestuurd door main_window wanneer gebruiker op ruimte klikt in boom.
        Selecteert de ruimte in de dropdown en herlaadt de kaartjes.
        """
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
        """Data verversen na wijzigingen."""
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