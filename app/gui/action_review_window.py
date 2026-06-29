# =============================================================================
# Networkmap_Creator
# File:    app/gui/action_review_window.py
# Role:    Reviewvenster voor rapport-actiepunten — bekijken en (per object)
#          manueel goedkeuren als uitzondering, of opnieuw openen.
# Version: 1.9.0
# Author:  Barremans
# Changes: 1.9.0 — UX-1: drie verbeteringen:
#                  (1) Ghost-objecten uitgesloten: devices zonder rack-slot en
#                      eindapparaten zonder naam verschijnen niet in review.
#                  (2) Bedrijfsfilter: dropdown bovenaan (boven tabs) laat toe
#                      te kiezen tussen "Alle bedrijven" of één specifiek bedrijf.
#                      Beide tabs (Actiepunten + MAC Review) volgen het filter.
#                  (3) Groepering per bedrijf bij "Alle bedrijven": sectiekoppen
#                      in actiepuntenlijst en MAC-tabel tonen bedrijfsnaam.
#                  (4) Minimumbreedte verhoogd van 1100 naar 1350px.
# Changes: 1.8.0 — EXP-1: Markdown-export vanuit het reviewvenster.
#                  Knop "Exporteer naar Markdown" in titelbalk exporteert
#                  beide tabs naar één .md-bestand via QFileDialog.
#                  Actiepunten als tabel in ##-sectie, MAC Review idem.
#                  Geen externe modules — puur Python standaardbibliotheek.
#                  Afdrukbaar via VS Code / elke Markdown-viewer.
#                  Altijd volledige dataset, ongeacht actief filter.
# Changes: 1.6.0 — Verwijderen van eindapparaten en devices vanuit beide tabs:
#                   (1) MAC Review tab: rechtsklik → "Verwijderen" voor zowel
#                       Eindapparaat als Device. Bevestigingsdialoog verplicht.
#                       Verwijdert object + alle verbindingen die ernaar verwijzen
#                       + wandpunt-koppeling (endpoint_id → ""). Geblokkeerd in
#                       read-only modus.
#                   (2) Actiepunten tab: rechtsklik → "Verwijderen" voor objecten
#                       met object_type "endpoint" of "device". Zelfde logica.
#                   Twee nieuwe signals: endpoint_deleted(ep_id), device_deleted(dev_id)
#                   → MainWindow slaat op + refresht boom (geen validatie nodig
#                   bij verwijderen). LOG-1: log_change met ACTION_DELETE.
# Changes: 1.5.0 — Twee fixes:
#                   (1) focus_ids: endpoint_changed en device_changed emitteren
#                       nu het ID (Signal(str)) zodat main_window _save_validated()
#                       kan aanroepen met focus_ids={id} i.p.v. volledige dataset.
#                       Vermijdt niet-gerelateerde validatiewaarschuwingen bij
#                       bewerken via MAC Review tab.
#                   (2) LOG-1 old/new diff: _mac_edit_endpoint en _mac_edit_device
#                       slaan de oude waarden op vóór de dialoog en roepen
#                       log_change() aan met details={veld: {van, naar}} —
#                       consistent met het patroon in main_window._on_edit_device.
# Changes: 1.4.0 — MAC Review verbeteringen:
#                   (1) Minimumbreedte verhoogd van 860 naar 1100px zodat alle
#                       kolommen zichtbaar zijn zonder horizontaal scrollen.
#                   (2) Devices kunnen nu ook bewerkt worden via rechtsklik en
#                       dubbelklik (DeviceDialog). Enkel basisvelden (naam, IP,
#                       MAC, merk, model) — geen SFP-poort aanmaak (rack-context
#                       niet beschikbaar). Na opslaan: device_changed signal +
#                       reload.
#                   (3) Exclude via rechtsklik: devices en eindapparaten kunnen
#                       worden uitgesloten van de MAC Review via
#                       "Uitsluiten van review". Uitsluitingen opgeslagen in
#                       data["mac_review_exclusions"] (lijst van obj_id's).
#                       Heropnemen via "Uitsluiting opheffen". Filter-combobox
#                       uitgebreid met "Inclusief uitgesloten" optie.
#                       exclusions_changed signal voor MainWindow (opslaan).
#          1.3.0 — MAC-1 fixes + uitbreidingen:
#                   (1) MAC-check normaliseert naar hoofdletters vóór regex →
#                       kleine letters zoals 38:4b:76:... worden nu correct
#                       herkend als formaat-fout (niet als ontbrekend).
#                   (2) IP-controle toegevoegd: ip_format als IP aanwezig maar
#                       geen geldig IPv4 (a.b.c.d, elk 0–255).
#                   (3) Rechtsklik-menu op MAC-tabel: eindapparaten bewerken
#                       via EndpointDialog. Niet beschikbaar voor Devices
#                       (read-only modus respecteerd). Na opslaan: reload +
#                       endpoint_changed signal.
#                   (4) Kolom IP toegevoegd aan MAC-tabel.
#          1.2.0 — MAC-1: tweede tab "MAC Review" toegevoegd.
#          1.1.0 — I18N-REVIEW: alle hardcoded NL-teksten vervangen door t()-sleutels.
#          1.0.1 — read_only-modus: venster opent view-only (geen goedkeuren/
#                  heropenen), navigatie + bekijken blijft mogelijk.
#          1.0.0 — REVIEW-AP stap 2. Object-niveau goedkeuren (reden optioneel),
#                  'door' = meegegeven Azure AD-gebruiker, 'wanneer' = nu.
#                  Bron: report_generator.enumerate_action_items() (zelfde
#                  telling als het rapport). Schrijft naar data["approvals"];
#                  emit approvals_changed zodat MainWindow opslaat + ververst.
#                  Dubbelklik op een navigeerbaar object → navigate_requested.
# =============================================================================

import datetime
import re

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem,
    QLabel, QPushButton, QFrame, QMenu, QInputDialog,
    QTabWidget, QWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QComboBox,
    QMessageBox, QFileDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from app.services import report_generator
from app.helpers.i18n import t
from app.helpers.settings_storage import (
    get_all_sites, get_all_companies, get_company_by_id,
)
from app.services.changelog_service import (
    log_change,
    ACTION_EDIT, ACTION_DELETE,
    ENTITY_ENDPOINT, ENTITY_DEVICE, ENTITY_WALL_OUTLET,
)

_USER_ROLE = Qt.ItemDataRole.UserRole

# Statusfilters: (key, i18n_key)
_FILTERS = [
    ("open",     "review_filter_open"),
    ("approved", "review_filter_approved"),
    ("all",      "review_filter_all"),
]

# Prioriteitskleur + sorteervolgorde
_PRIO_RANK  = {"Hoog": 0, "Middel": 1, "Laag": 2}
_PRIO_COLOR = {"Hoog": "#C0392B", "Middel": "#E67E22", "Laag": "#4CAF7D"}

# Objecttypes die navigeerbaar zijn (mappen op MainWindow._on_search_result)
_NAV_TYPES = {"device", "endpoint", "wall_outlet", "port"}

# MAC-1 — regex voor uniform formaat XX:XX:XX:XX:XX:XX (hoofdletters, dubbele punt)
_MAC_RE = re.compile(r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$')

# MAC-1 — geldig IPv4: vier octetten 0–255
_IPV4_RE = re.compile(
    r'^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}'
    r'(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$'
)

# MAC-1 — probleemtype labels (key → display)
_MAC_ISSUES = {
    "mac_missing":  "MAC ontbreekt",
    "mac_format":   "MAC formaat",
    "ip_format":    "IP formaat",
    "brand_missing": "Merk ontbreekt",
    "model_missing": "Model ontbreekt",
}

# MAC-1 — tabelkolommen
_MC_OBJ    = 0
_MC_NAME   = 1
_MC_MAC_E  = 2
_MC_MAC_W  = 3
_MC_IP     = 4
_MC_BRAND  = 5
_MC_MODEL  = 6
_MC_ISSUES = 7
_MC_COLS   = 8

# MAC-1 — UserRole voor tabelrijen
_MC_ROW_ROLE = Qt.ItemDataRole.UserRole


class ActionReviewWindow(QDialog):
    """
    Reviewvenster voor de rapport-actiepunten.

    Signalen:
      approvals_changed()              — na elke wijziging in data["approvals"]
                                         (MainWindow slaat op + ververst rapport)
      navigate_requested(type, id)     — dubbelklik op navigeerbaar object
      endpoint_changed(ep_id)          — na bewerken eindapparaat via MAC-tab
      device_changed(dev_id)           — na bewerken device via MAC-tab
      exclusions_changed()             — na wijziging mac_review_exclusions
      endpoint_deleted(ep_id)          — na verwijderen eindapparaat
      device_deleted(dev_id)           — na verwijderen device
    """

    approvals_changed  = Signal()
    navigate_requested = Signal(str, str)
    endpoint_changed   = Signal(str)     # emitteert ep_id na bewerken eindapparaat via MAC-tab
    device_changed     = Signal(str)     # emitteert dev_id na bewerken device via MAC-tab
    exclusions_changed = Signal()        # na uitsluiten/opheffen via MAC-tab
    endpoint_deleted   = Signal(str)     # emitteert ep_id na verwijderen eindapparaat
    device_deleted     = Signal(str)     # emitteert dev_id na verwijderen device

    def __init__(self, data: dict, current_user: str = "",
                 read_only: bool = False, parent=None):
        super().__init__(parent)
        self._data      = data
        self._user      = (current_user or "").strip()
        self._read_only = bool(read_only)
        self._active_filter = "open"
        self._items: list = []
        # 1.4.0 — toon-uitgesloten flag (False = uitgesloten verborgen, default)
        self._show_excluded = False
        # 1.9.0 — bedrijfsfilter: None = alle bedrijven, str = company_id
        self._company_filter: str | None = None

        self.setWindowTitle(t("review_title_readonly") if read_only else t("review_title"))
        self.setMinimumSize(1350, 600)   # 1.9.0: was 1100 — verhoogd voor bedrijfsfilter + kolommen
        self.setModal(False)
        self._build()
        self._reload()

    # ------------------------------------------------------------------
    # Hulpfunctie: exclusions set ophalen/beheren
    # ------------------------------------------------------------------

    def _get_exclusions(self) -> set:
        return set(self._data.get("mac_review_exclusions", []))

    def _set_exclusions(self, excl: set):
        self._data["mac_review_exclusions"] = sorted(excl)

    # ------------------------------------------------------------------
    # UI opbouw
    # ------------------------------------------------------------------

    def _build(self):
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(10, 10, 10, 10)

        # ── Titel + sluitknop ────────────────────────────────────────
        top = QHBoxLayout()
        title = QLabel("📋  " + t("review_title"))
        f = title.font(); f.setPointSize(f.pointSize() + 2); f.setBold(True)
        title.setFont(f)
        top.addWidget(title)
        top.addStretch()
        btn_export = QPushButton("📥  Exporteer naar Markdown")
        btn_export.setFixedHeight(28)
        btn_export.setToolTip("Exporteer actiepunten en MAC Review naar Markdown (.md)")
        btn_export.clicked.connect(self._export_to_markdown)
        top.addWidget(btn_export)
        btn_close = QPushButton(t("review_btn_close"))
        btn_close.setFixedWidth(90)
        btn_close.clicked.connect(self.close)
        top.addWidget(btn_close)
        root.addLayout(top)

        sep0 = QFrame(); sep0.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep0)

        # ── 1.9.0 — Bedrijfsfilter (boven tabs, gemeenschappelijk) ──
        co_row = QHBoxLayout()
        co_row.setSpacing(8)
        co_lbl = QLabel("Bedrijf:")
        co_lbl.setFixedWidth(60)
        co_row.addWidget(co_lbl)
        self._co_ddl = QComboBox()
        self._co_ddl.setMinimumWidth(240)
        self._co_ddl.addItem("— Alle bedrijven —", None)
        for co in get_all_companies(self._data):
            self._co_ddl.addItem(co.get("name", co["id"]), co["id"])
        self._co_ddl.currentIndexChanged.connect(self._on_company_filter_changed)
        co_row.addWidget(self._co_ddl)
        co_row.addStretch()
        root.addLayout(co_row)

        sep0b = QFrame(); sep0b.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep0b)

        # ── Tabs ─────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        root.addWidget(self._tabs, 1)

        # ── Tab 0: Actiepunten (bestaande inhoud) ────────────────────
        tab_ap = QWidget()
        ap_layout = QVBoxLayout(tab_ap)
        ap_layout.setContentsMargins(0, 6, 0, 0)
        ap_layout.setSpacing(6)

        # Filterrij
        filter_row = QHBoxLayout()
        filter_row.setSpacing(4)
        self._filter_btns: dict = {}
        for key, i18n_key in _FILTERS:
            btn = QPushButton(t(i18n_key))
            btn.setCheckable(True)
            btn.setFixedHeight(26)
            btn.clicked.connect(lambda checked, k=key: self._set_filter(k))
            self._filter_btns[key] = btn
            filter_row.addWidget(btn)
        filter_row.addStretch()
        ap_layout.addLayout(filter_row)

        sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.HLine)
        ap_layout.addWidget(sep1)

        # Lijst
        self._list = QListWidget()
        self._list.setSpacing(2)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        self._list.itemActivated.connect(self._on_activate)
        ap_layout.addWidget(self._list, 1)

        # Statusregel
        bottom = QHBoxLayout()
        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("secondary")
        bottom.addWidget(self._status_lbl)
        bottom.addStretch()
        hint = QLabel(t("review_hint"))
        hint.setObjectName("secondary")
        bottom.addWidget(hint)
        ap_layout.addLayout(bottom)

        self._tabs.addTab(tab_ap, "📋  " + t("review_title"))

        # ── Tab 1: MAC Review ─────────────────────────────────────────
        tab_mac = QWidget()
        mac_layout = QVBoxLayout(tab_mac)
        mac_layout.setContentsMargins(0, 6, 0, 0)
        mac_layout.setSpacing(6)

        mac_filter_row = QHBoxLayout()
        mac_filter_row.setSpacing(8)
        mac_filter_row.addWidget(QLabel("Filter:"))
        self._mac_filter_ddl = QComboBox()
        self._mac_filter_ddl.setMinimumWidth(180)
        self._mac_filter_ddl.addItem("— alle problemen —", "")
        for key, label in _MAC_ISSUES.items():
            self._mac_filter_ddl.addItem(label, key)
        self._mac_filter_ddl.currentIndexChanged.connect(self._render_mac)
        mac_filter_row.addWidget(self._mac_filter_ddl)

        # 1.4.0 — Toon/verberg uitgesloten objecten
        self._btn_toggle_excluded = QPushButton("Toon uitgesloten")
        self._btn_toggle_excluded.setCheckable(True)
        self._btn_toggle_excluded.setFixedHeight(26)
        self._btn_toggle_excluded.clicked.connect(self._toggle_excluded)
        mac_filter_row.addWidget(self._btn_toggle_excluded)

        mac_filter_row.addStretch()
        self._mac_count_lbl = QLabel("")
        self._mac_count_lbl.setObjectName("secondary")
        mac_filter_row.addWidget(self._mac_count_lbl)
        mac_layout.addLayout(mac_filter_row)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        mac_layout.addWidget(sep2)

        self._mac_table = QTableWidget(0, _MC_COLS)
        self._mac_table.setHorizontalHeaderLabels([
            "Object", "Naam", "MAC ETH", "MAC WiFi", "IP", "Merk", "Model", "Problemen",
        ])
        hdr = self._mac_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hdr.setStretchLastSection(True)
        self._mac_table.setColumnWidth(_MC_OBJ,    90)
        self._mac_table.setColumnWidth(_MC_NAME,  180)
        self._mac_table.setColumnWidth(_MC_MAC_E, 150)
        self._mac_table.setColumnWidth(_MC_MAC_W, 150)
        self._mac_table.setColumnWidth(_MC_IP,    120)
        self._mac_table.setColumnWidth(_MC_BRAND, 110)
        self._mac_table.setColumnWidth(_MC_MODEL, 140)
        self._mac_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._mac_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._mac_table.setAlternatingRowColors(True)
        self._mac_table.verticalHeader().setVisible(False)
        self._mac_table.setSortingEnabled(True)
        self._mac_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._mac_table.customContextMenuRequested.connect(self._on_mac_context_menu)
        self._mac_table.itemDoubleClicked.connect(self._on_mac_double_click)
        mac_layout.addWidget(self._mac_table, 1)

        self._tabs.addTab(tab_mac, "🔍  MAC Review")

        self._set_filter("open")

    # ------------------------------------------------------------------
    # Data laden / renderen
    # ------------------------------------------------------------------


    # ------------------------------------------------------------------
    # 1.9.0 — Bedrijfsfilter + ghost-filtering
    # ------------------------------------------------------------------

    def _on_company_filter_changed(self):
        """Sla het gekozen bedrijf op en herlaad beide tabs."""
        self._company_filter = self._co_ddl.currentData()  # None = alle
        self._reload()

    def _get_slotted_device_ids(self) -> set:
        """IDs van devices die in minstens één rack-slot zitten (niet ghost)."""
        slotted: set = set()
        for site in get_all_sites(self._data):
            for room in site.get("rooms", []):
                for rack in room.get("racks", []):
                    for slot in rack.get("slots", []):
                        dev_id = slot.get("device_id", "")
                        if dev_id:
                            slotted.add(dev_id)
        return slotted

    def _get_company_device_ids(self, company_id: str) -> set:
        """IDs van devices die in een rack van het opgegeven bedrijf zitten."""
        ids: set = set()
        co = get_company_by_id(self._data, company_id)
        if not co:
            return ids
        for site in co.get("sites", []):
            for room in site.get("rooms", []):
                for rack in room.get("racks", []):
                    for slot in rack.get("slots", []):
                        dev_id = slot.get("device_id", "")
                        if dev_id:
                            ids.add(dev_id)
        return ids

    def _get_company_endpoint_ids(self, company_id: str) -> set:
        """IDs van eindapparaten die via een wandpunt aan het bedrijf gekoppeld zijn."""
        ids: set = set()
        co = get_company_by_id(self._data, company_id)
        if not co:
            return ids
        for site in co.get("sites", []):
            for room in site.get("rooms", []):
                for wo in room.get("wall_outlets", []):
                    ep_id = wo.get("endpoint_id", "")
                    if ep_id:
                        ids.add(ep_id)
        return ids

    def _get_company_name(self, company_id: str | None) -> str:
        """Bedrijfsnaam voor sectiekoppen, lege string als None."""
        if not company_id:
            return ""
        co = get_company_by_id(self._data, company_id)
        return co.get("name", company_id) if co else company_id

    def _reload(self):
        """
        Herbereken actiepunten + MAC-reviewdata.
        1.9.0: ghost-objecten (device zonder rack-slot, endpoint zonder naam)
        worden uitgefilterd. Bedrijfsfilter beperkt beide tabs.
        """
        slotted = self._get_slotted_device_ids()

        try:
            all_items = report_generator.enumerate_action_items(self._data)
        except Exception:
            all_items = []

        # Ghost-filtering: verwijder items van niet-geplaatste devices/endpoints
        def _is_ghost_item(o: dict) -> bool:
            obj_type = o.get("object_type", "")
            obj_id   = o.get("object_id", "")
            if obj_type == "device" and obj_id not in slotted:
                return True
            if obj_type == "endpoint":
                ep = next((e for e in self._data.get("endpoints", [])
                           if e.get("id") == obj_id), None)
                if ep and not (ep.get("name") or "").strip():
                    return True
            return False

        items = [o for o in all_items if not _is_ghost_item(o)]

        # Bedrijfsfilter op actiepunten
        if self._company_filter:
            co_dev_ids = self._get_company_device_ids(self._company_filter)
            co_ep_ids  = self._get_company_endpoint_ids(self._company_filter)
            def _in_company(o: dict) -> bool:
                obj_type = o.get("object_type", "")
                obj_id   = o.get("object_id", "")
                if obj_type == "device":      return obj_id in co_dev_ids
                if obj_type == "endpoint":    return obj_id in co_ep_ids
                if obj_type == "wall_outlet":
                    # wandpunt: check via site
                    for site in get_all_sites(self._data):
                        co = get_company_by_id(self._data, self._company_filter)
                        if not co:
                            continue
                        site_ids = {s["id"] for s in co.get("sites", [])}
                        if site.get("id") in site_ids:
                            for room in site.get("rooms", []):
                                for wo in room.get("wall_outlets", []):
                                    if wo.get("id") == obj_id:
                                        return True
                    return False
                # site/room/rack: altijd tonen (geen EP/dev koppeling)
                return True
            items = [o for o in items if _in_company(o)]

        self._items = items
        self._mac_rows = self._collect_mac_rows()
        self._render()
        self._render_mac()

    def _set_filter(self, key: str):
        self._active_filter = key
        for k, btn in self._filter_btns.items():
            active = (k == key)
            btn.setChecked(active)
            btn.setObjectName("filter-active" if active else "filter-inactive")
            btn.style().unpolish(btn); btn.style().polish(btn)
        self._render()

    def _render(self):
        self._list.clear()

        n_open     = sum(1 for o in self._items if o.get("status") != "approved")
        n_approved = sum(1 for o in self._items if o.get("status") == "approved")

        if self._active_filter == "open":
            rows = [o for o in self._items if o.get("status") != "approved"]
        elif self._active_filter == "approved":
            rows = [o for o in self._items if o.get("status") == "approved"]
        else:
            rows = list(self._items)

        # 1.9.0 — sorteren: bij alle bedrijven eerst op bedrijf, dan prio
        def _sort_key(o):
            return (
                o.get("company_name", "") if not self._company_filter else "",
                _PRIO_RANK.get(o.get("priority", "Laag"), 9),
                o.get("category", ""),
                o.get("label", ""),
            )
        rows.sort(key=_sort_key)

        # 1.9.0 — sectiekoppen bij "alle bedrijven"
        current_co = None
        for o in rows:
            if not self._company_filter:
                co_name = o.get("company_name", "")
                if co_name != current_co:
                    current_co = co_name
                    hdr = QListWidgetItem("  🏢  " + (co_name or "(geen bedrijf)"))
                    hdr.setFlags(Qt.ItemFlag.NoItemFlags)
                    f = hdr.font(); f.setBold(True); hdr.setFont(f)
                    hdr.setForeground(QColor("#5B9BD5"))
                    self._list.addItem(hdr)
            self._list.addItem(self._make_item(o))

        self._status_lbl.setText(
            f"{n_open} {t('review_filter_open').lower()}  \u00b7  "
            f"{n_approved} {t('review_item_approved')}  \u00b7  "
            f"{len(self._items)} {t('review_status_total')}"
        )

    # ------------------------------------------------------------------
    # MAC Review — data verzamelen en renderen
    # ------------------------------------------------------------------

    def _collect_mac_rows(self) -> list[dict]:
        """
        MAC-1 — Verzamel alle devices en eindapparaten die review nodig hebben.
        Controles per object:
          - mac_missing  : mac_eth leeg (of ontbreekt)
          - mac_format   : mac_eth aanwezig maar niet XX:XX:XX:XX:XX:XX
          - ip_format    : IP aanwezig maar ongeldig IPv4
          - brand_missing: merk leeg
          - model_missing: model leeg
        Alleen objecten met minstens één probleem worden opgenomen.
        1.4.0: excluded vlag toegevoegd op basis van data["mac_review_exclusions"].
        """
        rows: list[dict] = []
        exclusions = self._get_exclusions()

        def _check(obj: dict, obj_type: str):
            mac_eth_raw = (obj.get("mac_eth", "") or obj.get("mac", "") or "").strip()
            mac_wifi    = (obj.get("mac_wifi", "") or "").strip()
            brand       = (obj.get("brand",   "") or "").strip()
            model       = (obj.get("model",   "") or "").strip()
            ip          = (obj.get("ip",      "") or "").strip()

            # Normaliseer MAC naar hoofdletters vóór regex-check
            mac_eth_norm = mac_eth_raw.upper()

            issues: list[str] = []
            if not mac_eth_raw:
                issues.append("mac_missing")
            elif not _MAC_RE.match(mac_eth_norm):
                issues.append("mac_format")
            if ip and not _IPV4_RE.match(ip):
                issues.append("ip_format")
            if not brand:
                issues.append("brand_missing")
            if not model:
                issues.append("model_missing")

            if issues:
                obj_id = obj.get("id", "")
                rows.append({
                    "obj_type":     obj_type,
                    "obj_id":       obj_id,
                    "name":         obj.get("name", "?"),
                    "mac_eth":      mac_eth_raw,
                    "mac_wifi":     mac_wifi,
                    "ip":           ip,
                    "brand":        brand,
                    "model":        model,
                    "issues":       issues,
                    "issue_set":    set(issues),
                    "excluded":     obj_id in exclusions,   # 1.4.0
                    "company_name": _company_name,          # 1.9.0
                })

        # 1.9.0 — ghost-filtering + bedrijfsfilter
        slotted    = self._get_slotted_device_ids()
        co_dev_ids = self._get_company_device_ids(self._company_filter) \
                     if self._company_filter else None
        co_ep_ids  = self._get_company_endpoint_ids(self._company_filter) \
                     if self._company_filter else None

        # Bouw reverse-map: dev_id/ep_id → bedrijfsnaam (voor sectiekoppen)
        _id_to_company: dict[str, str] = {}
        for co in get_all_companies(self._data):
            co_name = co.get("name", "")
            for site in co.get("sites", []):
                for room in site.get("rooms", []):
                    for rack in room.get("racks", []):
                        for slot in rack.get("slots", []):
                            if slot.get("device_id"):
                                _id_to_company[slot["device_id"]] = co_name
                    for wo in room.get("wall_outlets", []):
                        if wo.get("endpoint_id"):
                            _id_to_company[wo["endpoint_id"]] = co_name

        for dev in self._data.get("devices", []):
            if dev.get("id") not in slotted:
                continue
            if co_dev_ids is not None and dev.get("id") not in co_dev_ids:
                continue
            _company_name = _id_to_company.get(dev.get("id", ""), "")
            _check(dev, "Device")

        for ep in self._data.get("endpoints", []):
            if not (ep.get("name") or "").strip():
                continue
            if co_ep_ids is not None and ep.get("id") not in co_ep_ids:
                continue
            _company_name = _id_to_company.get(ep.get("id", ""), "")
            _check(ep, "Eindapparaat")

        rows.sort(key=lambda r: (r["obj_type"], r["name"].lower()))
        return rows

    def _toggle_excluded(self):
        """1.4.0 — Wissel toon/verberg uitgesloten rijen."""
        self._show_excluded = self._btn_toggle_excluded.isChecked()
        self._btn_toggle_excluded.setText(
            "Verberg uitgesloten" if self._show_excluded else "Toon uitgesloten"
        )
        self._render_mac()

    def _render_mac(self):
        """MAC-1 — Vul de MAC-tabel op basis van huidig filter."""
        filter_key = self._mac_filter_ddl.currentData() or ""

        filtered = [
            r for r in self._mac_rows
            if (not filter_key or filter_key in r["issue_set"])
            and (self._show_excluded or not r["excluded"])
        ]

        # 1.9.0 — sortering: bij alle bedrijven eerst op bedrijf
        if not self._company_filter:
            filtered.sort(key=lambda r: (
                r.get("company_name", ""),
                r["obj_type"],
                r["name"].lower(),
            ))

        # 1.9.0 — sectierijen tellen voor juiste rowCount
        n_headers = 0
        if not self._company_filter:
            seen_co: set = set()
            for r in filtered:
                co = r.get("company_name", "")
                if co not in seen_co:
                    seen_co.add(co)
                    n_headers += 1

        self._mac_table.setSortingEnabled(False)
        self._mac_table.setRowCount(len(filtered) + n_headers)

        real_row = 0
        current_co_mac = None
        for row in filtered:
            # 1.9.0 — sectiekoppen per bedrijf bij "alle bedrijven"
            if not self._company_filter:
                co_name = row.get("company_name", "")
                if co_name != current_co_mac:
                    current_co_mac = co_name
                    for col in range(_MC_COLS):
                        hdr_cell = QTableWidgetItem(
                            ("  🏢  " + (co_name or "(geen bedrijf)")) if col == 0 else ""
                        )
                        hdr_cell.setFlags(Qt.ItemFlag.NoItemFlags)
                        f = hdr_cell.font(); f.setBold(True); hdr_cell.setFont(f)
                        hdr_cell.setForeground(QColor("#5B9BD5"))
                        self._mac_table.setItem(real_row, col, hdr_cell)
                    real_row += 1

            row_idx = real_row
            def _cell(val: str, color: str = "") -> QTableWidgetItem:
                it = QTableWidgetItem(val)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if color:
                    it.setForeground(QColor(color))
                return it

            mac_eth_norm = row["mac_eth"].upper()
            mac_eth_ok   = bool(row["mac_eth"]) and _MAC_RE.match(mac_eth_norm)
            mac_color    = "" if mac_eth_ok else "#C0392B"
            ip_ok        = not row["ip"] or _IPV4_RE.match(row["ip"])
            ip_color     = "" if ip_ok else "#C0392B"
            brand_color  = "" if row["brand"] else "#C0392B"
            model_color  = "" if row["model"] else "#C0392B"

            issue_text = "  ·  ".join(
                _MAC_ISSUES.get(i, i) for i in row["issues"]
            )

            # 1.4.0 — uitgesloten rijen grijs weergeven
            row_fg = "#666666" if row["excluded"] else ""

            name_cell = _cell(row["name"], row_fg)
            name_cell.setData(_MC_ROW_ROLE, row)

            self._mac_table.setItem(row_idx, _MC_OBJ,    _cell(row["obj_type"], row_fg))
            self._mac_table.setItem(row_idx, _MC_NAME,   name_cell)
            self._mac_table.setItem(row_idx, _MC_MAC_E,  _cell(row["mac_eth"],  mac_color if not row["excluded"] else row_fg))
            self._mac_table.setItem(row_idx, _MC_MAC_W,  _cell(row["mac_wifi"], row_fg))
            self._mac_table.setItem(row_idx, _MC_IP,     _cell(row["ip"],       ip_color  if not row["excluded"] else row_fg))
            self._mac_table.setItem(row_idx, _MC_BRAND,  _cell(row["brand"],    brand_color if not row["excluded"] else row_fg))
            self._mac_table.setItem(row_idx, _MC_MODEL,  _cell(row["model"],    model_color if not row["excluded"] else row_fg))
            self._mac_table.setItem(row_idx, _MC_ISSUES, _cell(issue_text,      row_fg))
            real_row += 1

        self._mac_table.setSortingEnabled(True)
        total   = len(self._mac_rows)
        visible = len([r for r in self._mac_rows if not r["excluded"]])
        excl    = total - visible
        shown   = len(filtered)

        count_parts = [str(shown)]
        if shown != total:
            count_parts.append(f"van {visible if not self._show_excluded else total}")
        if excl:
            count_parts.append(f"{excl} uitgesloten")
        self._mac_count_lbl.setText("  ·  ".join(count_parts))

    # ------------------------------------------------------------------
    # MAC Review — interactie (contextmenu + bewerken)
    # ------------------------------------------------------------------

    def _mac_row_at(self, pos) -> dict | None:
        """Geeft de row-dict terug voor de tabelrij op positie pos."""
        row_idx = self._mac_table.rowAt(pos.y())
        if row_idx < 0:
            return None
        name_item = self._mac_table.item(row_idx, _MC_NAME)
        if not name_item:
            return None
        return name_item.data(_MC_ROW_ROLE)

    def _on_mac_context_menu(self, pos):
        row = self._mac_row_at(pos)
        if not row:
            return
        menu = QMenu(self)
        act_edit    = None
        act_delete  = None
        act_exclude = None
        act_include = None

        # 1.4.0 — Bewerken: zowel Eindapparaat als Device (niet in read-only)
        if not self._read_only:
            if row["obj_type"] in ("Eindapparaat", "Device"):
                act_edit   = menu.addAction("✏  " + t("ctx_edit"))
                act_delete = menu.addAction("🗑  " + t("ctx_delete"))
                menu.addSeparator()

        # 1.4.0 — Uitsluiten / opheffen
        if row["excluded"]:
            act_include = menu.addAction("✅  Uitsluiting opheffen")
        else:
            act_exclude = menu.addAction("🚫  Uitsluiten van review")

        if not menu.actions():
            return

        chosen = menu.exec(self._mac_table.mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == act_edit:
            if row["obj_type"] == "Eindapparaat":
                self._mac_edit_endpoint(row)
            elif row["obj_type"] == "Device":
                self._mac_edit_device(row)
        elif chosen == act_delete:
            if row["obj_type"] == "Eindapparaat":
                self._delete_endpoint(row["obj_id"], row["name"])
            elif row["obj_type"] == "Device":
                self._delete_device(row["obj_id"], row["name"])
        elif chosen == act_exclude:
            self._mac_exclude(row)
        elif chosen == act_include:
            self._mac_include(row)

    def _on_mac_double_click(self, item):
        name_item = self._mac_table.item(item.row(), _MC_NAME)
        if not name_item:
            return
        row = name_item.data(_MC_ROW_ROLE)
        if not row or self._read_only:
            return
        if row["obj_type"] == "Eindapparaat":
            self._mac_edit_endpoint(row)
        elif row["obj_type"] == "Device":
            self._mac_edit_device(row)

    def _mac_edit_endpoint(self, row: dict):
        """Open EndpointDialog voor het geselecteerde eindapparaat."""
        if self._read_only:
            return
        from app.gui.dialogs.endpoint_dialog import EndpointDialog
        ep_id = row.get("obj_id", "")
        ep = next(
            (e for e in self._data.get("endpoints", []) if e.get("id") == ep_id),
            None,
        )
        if not ep:
            return
        # LOG-1 — oude waarden opslaan vóór dialoog
        _EP_TRACK = ["name", "type", "ip", "mac_eth", "mac_wifi",
                     "brand", "model", "serial", "location", "notes"]
        _old = {k: ep.get(k, "") for k in _EP_TRACK}

        dlg = EndpointDialog(parent=self, endpoint=ep)
        if dlg.exec() and dlg.get_result():
            result = dlg.get_result()
            result["id"] = ep_id
            for i, e in enumerate(self._data.get("endpoints", [])):
                if e["id"] == ep_id:
                    self._data["endpoints"][i] = result
                    break
            # LOG-1 — diff berekenen en loggen
            _new = {k: result.get(k, "") for k in _EP_TRACK}
            _diff = {k: {"van": _old[k], "naar": _new[k]}
                     for k in _EP_TRACK if _old[k] != _new[k]}
            log_change(action=ACTION_EDIT, entity=ENTITY_ENDPOINT,
                       entity_id=ep_id, label=result.get("name", ep_id),
                       details=_diff or None)
            self.endpoint_changed.emit(ep_id)
            self._reload()

    def _mac_edit_device(self, row: dict):
        """1.4.0 — Open DeviceDialog voor het geselecteerde device (MAC Review context).
        Geen SFP-poort aanmaak: geen rack beschikbaar. Enkel basisvelden bijwerken.
        """
        if self._read_only:
            return
        from app.gui.dialogs.device_dialog import DeviceDialog
        dev_id = row.get("obj_id", "")
        dev = next(
            (d for d in self._data.get("devices", []) if d.get("id") == dev_id),
            None,
        )
        if not dev:
            return
        # LOG-1 — oude waarden opslaan vóór dialoog
        _DEV_TRACK = ["name", "type", "ip", "mac_eth", "mac_wifi",
                      "brand", "model", "location", "notes"]
        _old = {k: dev.get(k, "") for k in _DEV_TRACK}

        dlg = DeviceDialog(parent=self, device=dev)
        if dlg.exec() and dlg.get_result():
            result = dlg.get_result()
            result["id"] = dev_id
            for i, d in enumerate(self._data.get("devices", [])):
                if d["id"] == dev_id:
                    self._data["devices"][i].update(result)
                    break
            # LOG-1 — diff berekenen en loggen
            _new = {k: result.get(k, "") for k in _DEV_TRACK}
            _diff = {k: {"van": _old[k], "naar": _new[k]}
                     for k in _DEV_TRACK if _old[k] != _new[k]}
            log_change(action=ACTION_EDIT, entity=ENTITY_DEVICE,
                       entity_id=dev_id, label=result.get("name", dev_id),
                       details=_diff or None)
            self.device_changed.emit(dev_id)
            self._reload()

    # ------------------------------------------------------------------
    # 1.4.0 — Uitsluiten / opheffen
    # ------------------------------------------------------------------

    def _mac_exclude(self, row: dict):
        """Voeg obj_id toe aan mac_review_exclusions en sla op."""
        excl = self._get_exclusions()
        excl.add(row["obj_id"])
        self._set_exclusions(excl)
        self.exclusions_changed.emit()
        self._reload()

    def _mac_include(self, row: dict):
        """Verwijder obj_id uit mac_review_exclusions en sla op."""
        excl = self._get_exclusions()
        excl.discard(row["obj_id"])
        self._set_exclusions(excl)
        self.exclusions_changed.emit()
        self._reload()

    # ------------------------------------------------------------------
    # 1.6.0 — Verwijderen eindapparaat / device
    # ------------------------------------------------------------------

    def _delete_endpoint(self, ep_id: str, label: str):
        """Verwijder eindapparaat uit data + wandpunt-koppelingen + verbindingen."""
        if self._read_only or not ep_id:
            return
        reply = QMessageBox.question(
            self, t("menu_delete"),
            f"{t('msg_confirm_delete')}\n\n🖥  {label}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        # Verwijder uit endpoints
        self._data["endpoints"] = [
            e for e in self._data.get("endpoints", []) if e.get("id") != ep_id
        ]
        # Verwijder wandpunt-koppeling
        for site in get_all_sites(self._data):
            for room in site.get("rooms", []):
                for wo in room.get("wall_outlets", []):
                    if wo.get("endpoint_id") == ep_id:
                        wo["endpoint_id"] = ""
        # Verwijder verbindingen
        self._data["connections"] = [
            c for c in self._data.get("connections", [])
            if c.get("from_id") != ep_id and c.get("to_id") != ep_id
        ]
        # Verwijder uit mac_review_exclusions indien aanwezig
        excl = self._get_exclusions()
        excl.discard(ep_id)
        self._set_exclusions(excl)
        log_change(action=ACTION_DELETE, entity=ENTITY_ENDPOINT,
                   entity_id=ep_id, label=label)
        self.endpoint_deleted.emit(ep_id)
        self._reload()

    def _delete_device(self, dev_id: str, label: str):
        """Verwijder device uit data + poorten + verbindingen."""
        if self._read_only or not dev_id:
            return
        reply = QMessageBox.question(
            self, t("menu_delete"),
            f"{t('msg_confirm_delete')}\n\n🖥  {label}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        # Verzamel poort-IDs van dit device
        port_ids = {
            p["id"] for p in self._data.get("ports", [])
            if p.get("device_id") == dev_id
        }
        # Verwijder device
        self._data["devices"] = [
            d for d in self._data.get("devices", []) if d.get("id") != dev_id
        ]
        # Verwijder poorten
        self._data["ports"] = [
            p for p in self._data.get("ports", []) if p.get("device_id") != dev_id
        ]
        # Verwijder verbindingen van/naar poorten van dit device
        self._data["connections"] = [
            c for c in self._data.get("connections", [])
            if c.get("from_id") not in port_ids and c.get("to_id") not in port_ids
        ]
        # Verwijder rack-slot verwijzingen
        for site in get_all_sites(self._data):
            for room in site.get("rooms", []):
                for rack in room.get("racks", []):
                    rack["slots"] = [
                        s for s in rack.get("slots", [])
                        if s.get("device_id") != dev_id
                    ]
        # Verwijder uit mac_review_exclusions indien aanwezig
        excl = self._get_exclusions()
        excl.discard(dev_id)
        self._set_exclusions(excl)
        log_change(action=ACTION_DELETE, entity=ENTITY_DEVICE,
                   entity_id=dev_id, label=label)
        self.device_deleted.emit(dev_id)
        self._reload()

    def _make_item(self, o: dict) -> QListWidgetItem:
        approved = o.get("status") == "approved"
        prio     = o.get("priority", "")
        badge    = "✅" if approved else {"Hoog": "🔴", "Middel": "🟠", "Laag": "🟢"}.get(prio, "•")

        line1 = f"{badge}  [{o.get('category','')}]  {o.get('label','')}"
        parts2 = [o.get("detail", "")]
        if approved:
            ap = o.get("approval", {}) or {}
            extra = t("review_item_approved")
            if ap.get("by"):
                extra += f" {t('review_item_approved_by')} {ap['by']}"
            if ap.get("at"):
                extra += f" {t('review_item_approved_on')} {str(ap['at'])[:10]}"
            if ap.get("reason"):
                extra += f" \u2014 \u201c{ap['reason']}\u201d"
            parts2.append(extra)
        line2 = "     " + "  ·  ".join(p for p in parts2 if p)

        item = QListWidgetItem(line1 + "\n" + line2)
        item.setData(_USER_ROLE, o)
        if approved:
            item.setForeground(QColor("#888888"))
        else:
            item.setForeground(QColor(_PRIO_COLOR.get(prio, "#333333")))
        return item

    # ------------------------------------------------------------------
    # Contextmenu — goedkeuren / heropenen
    # ------------------------------------------------------------------

    def _on_context_menu(self, pos):
        item = self._list.itemAt(pos)
        if not item:
            return
        o = item.data(_USER_ROLE)
        if not o:
            return

        menu = QMenu(self)
        act_approve = act_reopen = act_nav = act_delete = None
        if not self._read_only:
            if o.get("status") == "approved":
                act_reopen = menu.addAction(t("review_ctx_reopen"))
            else:
                act_approve = menu.addAction(t("review_ctx_approve"))
            # 1.6.0 — Verwijderen voor endpoint en device
            if o.get("object_type") in ("endpoint", "device"):
                if menu.actions():
                    menu.addSeparator()
                act_delete = menu.addAction("🗑  " + t("ctx_delete"))
        if o.get("object_type") in _NAV_TYPES:
            if menu.actions():
                menu.addSeparator()
            act_nav = menu.addAction(t("review_ctx_navigate"))

        chosen = menu.exec(self._list.mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == act_approve:
            self._approve(o)
        elif chosen == act_reopen:
            self._reopen(o)
        elif chosen == act_delete:
            obj_type = o.get("object_type", "")
            obj_id   = o.get("object_id", "")
            obj_lbl  = o.get("label", obj_id)
            if obj_type == "endpoint":
                self._delete_endpoint(obj_id, obj_lbl)
            elif obj_type == "device":
                self._delete_device(obj_id, obj_lbl)
        elif chosen == act_nav:
            self._navigate(o)

    def _approve(self, o: dict):
        if self._read_only:
            return
        # Reden is optioneel: leeg laten mag.
        reason, ok = QInputDialog.getText(
            self, t("review_dlg_approve_title"),
            f"{o.get('category','')} — {o.get('label','')}\n\n{t('review_dlg_approve_reason')}"
        )
        if not ok:
            return
        record = {
            "key":    o["key"],
            "status": "approved",
            "reason": (reason or "").strip(),
            "by":     self._user,
            "at":     datetime.datetime.now().isoformat(timespec="seconds"),
        }
        self._upsert_approval(o["key"], record)
        self.approvals_changed.emit()
        self._reload()

    def _reopen(self, o: dict):
        if self._read_only:
            return
        self._remove_approval(o["key"])
        self.approvals_changed.emit()
        self._reload()

    def _navigate(self, o: dict):
        if o.get("object_type") in _NAV_TYPES:
            self.navigate_requested.emit(o["object_type"], o["object_id"])

    def _on_activate(self, item: QListWidgetItem):
        o = item.data(_USER_ROLE)
        if o and o.get("object_type") in _NAV_TYPES:
            self._navigate(o)

    # ------------------------------------------------------------------
    # data["approvals"] muteren
    # ------------------------------------------------------------------

    def _upsert_approval(self, key: str, record: dict):
        appr = self._data.setdefault("approvals", [])
        appr[:] = [a for a in appr if a.get("key") != key]
        appr.append(record)

    def _remove_approval(self, key: str):
        appr = self._data.get("approvals", [])
        self._data["approvals"] = [a for a in appr if a.get("key") != key]

    # ------------------------------------------------------------------
    # EXP-1 — Excel export
    # ------------------------------------------------------------------

    def _export_to_markdown(self):
        """
        EXP-1 — Exporteer actiepunten en MAC Review naar één Markdown-bestand.
        Geen externe modules nodig — puur Python standaardbibliotheek.
        Altijd volledige dataset, ongeacht actief filter of uitsluitingen.
        """
        import datetime as _dt

        path, _ = QFileDialog.getSaveFileName(
            self, "Exporteer naar Markdown",
            f"networkmap_review_{_dt.date.today().strftime('%Y%m%d')}.md",
            "Markdown bestanden (*.md)",
        )
        if not path:
            return

        try:
            md = self._build_markdown()
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(md)
            QMessageBox.information(
                self, "Export geslaagd",
                f"Export opgeslagen naar:\n{path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Export mislukt",
                f"Kon bestand niet opslaan:\n{e}"
            )

    def _build_markdown(self) -> str:
        """
        Bouw de volledige Markdown-tekst op voor beide tabs.
        Geeft een string terug — geen bestands-I/O hier.
        """
        import datetime as _dt

        lines = []
        today = _dt.date.today().strftime("%d/%m/%Y")

        # ── Koptekst ───────────────────────────────────────────────────
        lines.append(f"# Networkmap Creator — Review Export")
        lines.append(f"")
        lines.append(f"Gegenereerd op: {today}  ")
        lines.append(f"Actiepunten: {len(self._items)}  |  "
                     f"Open: {sum(1 for o in self._items if o.get('status') != 'approved')}  |  "
                     f"Goedgekeurd: {sum(1 for o in self._items if o.get('status') == 'approved')}")
        _mac_visible = [r for r in self._mac_rows if not r.get("excluded")]
        lines.append(f"MAC Review: {len(_mac_visible)} rijen (uitgesloten niet meegenomen)")
        lines.append("")

        # ── Sectie 1: Actiepunten ──────────────────────────────────────
        lines.append("---")
        lines.append("")
        lines.append("## 1. Actiepunten")
        lines.append("")

        # Sorteer: prio dan categorie dan label
        sorted_items = sorted(
            self._items,
            key=lambda o: (
                _PRIO_RANK.get(o.get("priority", "Laag"), 9),
                o.get("category", ""),
                o.get("label", ""),
            )
        )

        approvals = {a["key"]: a for a in self._data.get("approvals", [])}

        _ISSUES_LABELS = {
            'mac_missing':   'MAC ontbreekt',
            'mac_format':    'MAC formaat fout',
            'ip_format':     'IP formaat fout',
            'brand_missing': 'Merk ontbreekt',
            'model_missing': 'Model ontbreekt',
        }

        def _esc(s: str) -> str:
            """Escapeer pipe-tekens in MD-tabelcellen."""
            return str(s or "").replace("|", "&#124;").replace("\n", " ")

        lines.append("| Prioriteit | Check | Object | Locatie | Detail | Status | Reden | ✏ Opmerking |")
        lines.append("|---|---|---|---|---|---|---|---|")

        for item in sorted_items:
            ap   = approvals.get(item.get("key", ""), {})
            stat = "✅ Goedgekeurd" if item.get("status") == "approved" else "⬜ Open"
            lines.append(
                f"| {_esc(item.get('priority',''))} "
                f"| {_esc(item.get('check',''))} "
                f"| {_esc(item.get('label',''))} "
                f"| {_esc(item.get('location',''))} "
                f"| {_esc(item.get('description',''))} "
                f"| {stat} "
                f"| {_esc(ap.get('reason',''))} "
                f"|  |"
            )

        lines.append("")

        # ── Sectie 2: MAC Review ───────────────────────────────────────
        lines.append("---")
        lines.append("")
        lines.append("## 2. MAC Review")
        lines.append("")
        lines.append("| Type | Naam | Problemen | MAC ETH | MAC WiFi | IP | Merk | Model | Uitgesloten | ✏ MAC ETH | ✏ MAC WiFi | ✏ IP | ✏ Merk | ✏ Model | ✏ Opmerking |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

        for row in [r for r in self._mac_rows if not r.get("excluded")]:
            issues_txt = "  ·  ".join(
                _MAC_ISSUES.get(i, i) for i in row.get("issues", [])
            )
            excl = "Ja" if row.get("excluded") else ""
            lines.append(
                f"| {_esc(row.get('obj_type',''))} "
                f"| {_esc(row.get('name',''))} "
                f"| {_esc(issues_txt)} "
                f"| {_esc(row.get('mac_eth',''))} "
                f"| {_esc(row.get('mac_wifi',''))} "
                f"| {_esc(row.get('ip',''))} "
                f"| {_esc(row.get('brand',''))} "
                f"| {_esc(row.get('model',''))} "
                f"| {excl} "
                f"|  |  |  |  |  |  |"
            )

        lines.append("")
        lines.append("---")
        lines.append(f"*Networkmap Creator — export {today}*")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Externe verversing (na data-herlaad in MainWindow)
    # ------------------------------------------------------------------

    def update_data(self, data: dict):
        self._data = data
        self._reload()