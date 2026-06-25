# =============================================================================
# Networkmap_Creator
# File:    app/gui/search_window.py
# Role:    Unified zoekvenster — devices, wandpunten, eindapparaten, poorten
# Version: 2.4.0
# Author:  Barremans
# Changes: 2.4.0 — F9: placeholder verduidelijkt (naam, IP, MAC, type, VLAN).
#                   Brede matching zit in search_service v2.4.0.
#          2.3.0 — Contextmenu uitgebreid:
#                   Endpoint: 'Detail tonen' toegevoegd (opent _EndpointDetailDialog)
#                   detail_requested signaal ook voor endpoint
#          2.2.0 — Gedrag tab wisselen en dubbelklik herzien:
#                   Tab wisselen: input bewaren + nieuwe search uitvoeren op nieuwe tab
#                   Delete-toets in zoekveld wist input (keyPressEvent)
#                   Dubbelklik op resultaat: geen actie (alleen Enter + rechtsklik)
#                   Poort tab: geen minimum van 2 tekens vereist
#                   _set_filter(): _do_search() aanroepen ipv _render_results()
#          2.1.1 — Focus op zoekveld bewaard bij tab wisselen
#                   Minimaal 2 tekens vereist (status toont hint)
#                   Actieve filterknop visueel onderscheidend (objectName "filter-active")
#                   filter_type doorgegeven aan search_service.search()
#                   Specifieke tab zoekt enkel op naam van dat type
#                   Rechtsklik op resultaat → contextmenu:
#                     "Navigeer" (altijd) + "Detail tonen" (alleen device)
#                   Enter/dubbelklik → altijd navigeren (geen popup)
#                   navigate_to_outlet / navigate_to_endpoint signalen verwijderd
#                   (waren ongebruikt — navigatie via result_selected)
#          2.0.0 — Volledig herbouwd
#                   Één venster vervangt "Zoeken" + "Wandpunten zoeken"
#                   Filterrij: Alles / Device / Wandpunt / Eindapparaat / Poort / Rack
#                   Dubbelklik device   → navigeer naar rack + highlight
#                   Dubbelklik wandpunt → navigeer naar wandpunten view gefilterd
#                   Dubbelklik endpoint → navigeer naar wandpunten view gefilterd
#                   Dubbelklik poort    → navigeer naar rack + highlight trace
#                   Zoekt ook op IP, MAC, serienummer, model
#                   Rijweergave: icon + naam + locatie op tweede rij
#          1.2.0 — showEvent wist zoekveld bij heropenen
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QFrame, QMenu
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from app.helpers.i18n import t
from app.services import search_service

# ── Type iconen ───────────────────────────────────────────────────────────────
_TYPE_ICON = {
    "site":       "📍",
    "room":       "🏢",
    "rack":       "🗄",
    "device":     "⬡",
    "port":       "🔌",
    "wall_outlet":"🌐",
    "endpoint":   "🖥",
}

# ── Filter definitie ──────────────────────────────────────────────────────────
_FILTERS = [
    ("all",         "Alles",        None),
    ("device",      "Device",       ["device"]),
    ("wall_outlet", "Wandpunt",     ["wall_outlet"]),
    ("endpoint",    "Eindapparaat", ["endpoint"]),
    ("port",        "Poort",        ["port"]),
    ("rack",        "Rack/Ruimte",  ["rack", "room", "site"]),
]

_USER_ROLE = Qt.ItemDataRole.UserRole
_MIN_QUERY_LEN = 2


class SearchWindow(QDialog):
    """
    Unified zoekvenster.
    Signaal result_selected(type, id) bij Enter of contextmenu-navigeer.
    Signaal detail_requested(type, id) bij contextmenu "Detail tonen" (device + endpoint).
    """
    result_selected = Signal(str, str)   # type, id
    detail_requested = Signal(str, str)  # type, id — voor rechtsklik "Detail tonen"

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self._data          = data
        self._active_filter = "all"
        self._all_results   : list[dict] = []

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(180)
        self._timer.timeout.connect(self._do_search)

        self.setWindowTitle(t("menu_search"))
        self.setMinimumSize(560, 480)
        self.setModal(False)
        self._build()

    # ------------------------------------------------------------------
    # UI opbouw
    # ------------------------------------------------------------------

    def _build(self):
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(10, 10, 10, 10)

        # ── Zoekveld + sluitknop ─────────────────────────────────────
        search_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("🔍  " + t("menu_search") + "  —  naam, IP, MAC, type, VLAN...")
        self._input.textChanged.connect(self._on_text_changed)
        self._input.returnPressed.connect(self._activate_first)
        search_row.addWidget(self._input)
        btn_close = QPushButton(t("btn_close"))
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(self.close)
        search_row.addWidget(btn_close)
        root.addLayout(search_row)

        # ── Filterrij ────────────────────────────────────────────────
        filter_row = QHBoxLayout()
        filter_row.setSpacing(4)
        self._filter_btns: dict[str, QPushButton] = {}
        for key, label, _ in _FILTERS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(26)
            btn.clicked.connect(lambda checked, k=key: self._set_filter(k))
            self._filter_btns[key] = btn
            filter_row.addWidget(btn)
        filter_row.addStretch()
        root.addLayout(filter_row)

        # ── Separator ────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        # ── Resultatenlijst ──────────────────────────────────────────
        self._list = QListWidget()
        self._list.setSpacing(2)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        # 2.2.0 — itemDoubleClicked niet gekoppeld: dubbelklik doet niets
        self._list.itemActivated.connect(self._on_activate)
        root.addWidget(self._list, 1)

        # ── Statusregel ──────────────────────────────────────────────
        bottom_row = QHBoxLayout()
        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("secondary")
        bottom_row.addWidget(self._status_lbl)
        bottom_row.addStretch()
        hint = QLabel("↵  navigeer  ·  rechtsklik  voor opties")
        hint.setObjectName("secondary")
        bottom_row.addWidget(hint)
        root.addLayout(bottom_row)

        # Initieel filter instellen
        self._set_filter("all")
        self._input.setFocus()

    # ------------------------------------------------------------------
    # Toetsenbord — Delete wist input
    # ------------------------------------------------------------------

    def keyPressEvent(self, event):
        """2.2.0 — Delete-toets wist het zoekveld."""
        if event.key() in (Qt.Key.Key_Delete,):
            self._input.blockSignals(True)
            self._input.clear()
            self._input.blockSignals(False)
            self._list.clear()
            self._all_results = []
            self._status_lbl.setText("")
            self._input.setFocus()
            event.accept()
            return
        super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Filter
    # ------------------------------------------------------------------

    def _set_filter(self, key: str):
        self._active_filter = key
        for k, btn in self._filter_btns.items():
            is_active = (k == key)
            btn.setChecked(is_active)
            btn.setObjectName("filter-active" if is_active else "filter-inactive")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        # 2.1.1 — focus terug naar zoekveld na stijl-refresh
        self._input.setFocus()
        # 2.2.0 — nieuwe search uitvoeren op de nieuwe tab (behoudt input)
        self._do_search()

    # ------------------------------------------------------------------
    # Zoeken
    # ------------------------------------------------------------------

    def _on_text_changed(self):
        self._timer.start()

    def _do_search(self):
        query = self._input.text().strip()
        self._list.clear()
        self._all_results = []

        if not query:
            self._status_lbl.setText("")
            return

        # 2.2.0 — Poort tab: geen minimumlengte (port 3 / poort 1 moet werken)
        min_len = 1 if self._active_filter == "port" else _MIN_QUERY_LEN
        if len(query) < min_len:
            self._status_lbl.setText(f"Typ minstens {min_len} teken{'s' if min_len > 1 else ''} om te zoeken...")
            return

        # filter_type doorgeven aan service — service doet de juiste matching
        self._all_results = search_service.search(
            self._data, query, filter_type=self._active_filter
        )
        self._render_results()

    def _render_results(self):
        self._list.clear()

        query = self._input.text().strip()
        min_len = 1 if self._active_filter == "port" else _MIN_QUERY_LEN
        if not query or len(query) < min_len:
            return

        # Client-side type-filter (voor weergave bij tab-wissel zonder herzoeken)
        filter_types = None
        for key, _, types in _FILTERS:
            if key == self._active_filter:
                filter_types = types
                break

        results = self._all_results
        if filter_types:
            results = [r for r in results if r["type"] in filter_types]

        if not results:
            self._status_lbl.setText(t("search_no_results"))
            return

        n = len(results)
        self._status_lbl.setText(
            t("search_result_count_one") if n == 1
            else t("search_result_count").format(n=n)
        )

        for r in results:
            item = self._make_item(r)
            self._list.addItem(item)

    def _make_item(self, r: dict) -> QListWidgetItem:
        icon  = _TYPE_ICON.get(r["type"], "•")
        name  = r["label"]
        loc   = r.get("location", "")
        extra = r.get("extra", "")

        line1 = f"{icon}  {name}"
        parts2 = []
        if loc:
            parts2.append(loc)
        if extra:
            parts2.append(extra)
        line2 = "     " + "  ·  ".join(parts2) if parts2 else ""

        display = line1 + ("\n" + line2 if line2 else "")
        item = QListWidgetItem(display)
        item.setData(_USER_ROLE, r)

        if r.get("in_use"):
            from PySide6.QtGui import QColor
            item.setForeground(QColor("#888888"))

        return item

    # ------------------------------------------------------------------
    # Activatie (Enter / dubbelklik) — altijd navigeren
    # ------------------------------------------------------------------

    def _activate_first(self):
        if self._list.count() > 0:
            self._on_activate(self._list.item(0))

    def _on_activate(self, item: QListWidgetItem):
        """Enter of dubbelklik → altijd navigeren."""
        r = item.data(_USER_ROLE)
        if not r:
            return
        self.result_selected.emit(r["type"], r["id"])
        self.close()

    # ------------------------------------------------------------------
    # Rechtsklik contextmenu
    # ------------------------------------------------------------------

    def _on_context_menu(self, pos):
        item = self._list.itemAt(pos)
        if not item:
            return
        r = item.data(_USER_ROLE)
        if not r:
            return

        menu = QMenu(self)

        act_navigate = menu.addAction("🔍  Navigeer")
        act_detail   = None

        # Detail tonen voor device en endpoint
        if r["type"] in ("device", "endpoint"):
            act_detail = menu.addAction("ℹ  Detail tonen")

        chosen = menu.exec(self._list.mapToGlobal(pos))

        if chosen == act_navigate:
            self.result_selected.emit(r["type"], r["id"])
            self.close()
        elif act_detail and chosen == act_detail:
            self.detail_requested.emit(r["type"], r["id"])
            self.close()

    # ------------------------------------------------------------------
    # Data verversen
    # ------------------------------------------------------------------

    def update_data(self, data: dict):
        self._data = data

    # ------------------------------------------------------------------
    # Heropenen
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        self._timer.stop()
        self._input.blockSignals(True)
        self._input.clear()
        self._input.blockSignals(False)
        self._list.clear()
        self._all_results = []
        self._status_lbl.setText("")
        self._set_filter("all")
        self._input.setFocus()