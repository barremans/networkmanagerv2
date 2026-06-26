# =============================================================================
# Networkmap_Creator
# File:    app/gui/action_review_window.py
# Role:    Reviewvenster voor rapport-actiepunten — bekijken en (per object)
#          manueel goedkeuren als uitzondering, of opnieuw openen.
# Version: 1.4.0
# Author:  Barremans
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
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from app.services import report_generator
from app.helpers.i18n import t
from app.helpers.settings_storage import get_all_sites

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
      endpoint_changed()               — na bewerken eindapparaat via MAC-tab
      device_changed()                 — na bewerken device via MAC-tab
      exclusions_changed()             — na wijziging mac_review_exclusions
    """

    approvals_changed  = Signal()
    navigate_requested = Signal(str, str)
    endpoint_changed   = Signal()        # na bewerken eindapparaat via MAC-tab
    device_changed     = Signal()        # na bewerken device via MAC-tab
    exclusions_changed = Signal()        # na uitsluiten/opheffen via MAC-tab

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

        self.setWindowTitle(t("review_title_readonly") if read_only else t("review_title"))
        self.setMinimumSize(1100, 560)   # 1.4.0: was 860 — verhoogd voor kolomzichtbaarheid
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
        btn_close = QPushButton(t("review_btn_close"))
        btn_close.setFixedWidth(90)
        btn_close.clicked.connect(self.close)
        top.addWidget(btn_close)
        root.addLayout(top)

        sep0 = QFrame(); sep0.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep0)

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

    def _reload(self):
        """Herbereken alle actie-objecten en MAC-reviewdata uit de huidige data."""
        try:
            self._items = report_generator.enumerate_action_items(self._data)
        except Exception:
            self._items = []
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

        rows.sort(key=lambda o: (
            _PRIO_RANK.get(o.get("priority", "Laag"), 9),
            o.get("category", ""),
            o.get("label", ""),
        ))

        for o in rows:
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
                    "obj_type":  obj_type,
                    "obj_id":    obj_id,
                    "name":      obj.get("name", "?"),
                    "mac_eth":   mac_eth_raw,
                    "mac_wifi":  mac_wifi,
                    "ip":        ip,
                    "brand":     brand,
                    "model":     model,
                    "issues":    issues,
                    "issue_set": set(issues),
                    "excluded":  obj_id in exclusions,   # 1.4.0
                })

        for dev in self._data.get("devices", []):
            _check(dev, "Device")
        for ep in self._data.get("endpoints", []):
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
            and (self._show_excluded or not r["excluded"])   # 1.4.0
        ]

        self._mac_table.setSortingEnabled(False)
        self._mac_table.setRowCount(len(filtered))

        for row_idx, row in enumerate(filtered):
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
        act_edit = None
        act_exclude = None
        act_include = None

        # 1.4.0 — Bewerken: zowel Eindapparaat als Device (niet in read-only)
        if not self._read_only:
            if row["obj_type"] == "Eindapparaat":
                act_edit = menu.addAction("✏  " + t("ctx_edit"))
            elif row["obj_type"] == "Device":
                act_edit = menu.addAction("✏  " + t("ctx_edit"))

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
        dlg = EndpointDialog(parent=self, endpoint=ep)
        if dlg.exec() and dlg.get_result():
            result = dlg.get_result()
            result["id"] = ep_id
            for i, e in enumerate(self._data.get("endpoints", [])):
                if e["id"] == ep_id:
                    self._data["endpoints"][i] = result
                    break
            self.endpoint_changed.emit()
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
        dlg = DeviceDialog(parent=self, device=dev)
        if dlg.exec() and dlg.get_result():
            result = dlg.get_result()
            result["id"] = dev_id
            for i, d in enumerate(self._data.get("devices", [])):
                if d["id"] == dev_id:
                    self._data["devices"][i].update(result)
                    break
            self.device_changed.emit()
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
        act_approve = act_reopen = act_nav = None
        if not self._read_only:
            if o.get("status") == "approved":
                act_reopen = menu.addAction(t("review_ctx_reopen"))
            else:
                act_approve = menu.addAction(t("review_ctx_approve"))
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
    # Externe verversing (na data-herlaad in MainWindow)
    # ------------------------------------------------------------------

    def update_data(self, data: dict):
        self._data = data
        self._reload()