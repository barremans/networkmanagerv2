# =============================================================================
# Networkmap_Creator
# File:    app/gui/action_review_window.py
# Role:    Reviewvenster voor rapport-actiepunten — bekijken en (per object)
#          manueel goedkeuren als uitzondering, of opnieuw openen.
# Version: 1.1.0
# Author:  Barremans
# Changes: 1.1.0 — I18N-REVIEW: alle hardcoded NL-teksten vervangen door t()-sleutels.
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

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem,
    QLabel, QPushButton, QFrame, QMenu, QInputDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from app.services import report_generator
from app.helpers.i18n import t

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


class ActionReviewWindow(QDialog):
    """
    Reviewvenster voor de rapport-actiepunten.

    Signalen:
      approvals_changed()              — na elke wijziging in data["approvals"]
                                         (MainWindow slaat op + ververst rapport)
      navigate_requested(type, id)     — dubbelklik op navigeerbaar object
    """

    approvals_changed  = Signal()
    navigate_requested = Signal(str, str)

    def __init__(self, data: dict, current_user: str = "",
                 read_only: bool = False, parent=None):
        super().__init__(parent)
        self._data      = data
        self._user      = (current_user or "").strip()
        self._read_only = bool(read_only)
        self._active_filter = "open"
        self._items: list = []

        self.setWindowTitle(t("review_title_readonly") if read_only else t("review_title"))
        self.setMinimumSize(760, 540)
        self.setModal(False)
        self._build()
        self._reload()

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

        # ── Filterrij ────────────────────────────────────────────────
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
        root.addLayout(filter_row)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        # ── Lijst ────────────────────────────────────────────────────
        self._list = QListWidget()
        self._list.setSpacing(2)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        self._list.itemActivated.connect(self._on_activate)
        root.addWidget(self._list, 1)

        # ── Statusregel ──────────────────────────────────────────────
        bottom = QHBoxLayout()
        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("secondary")
        bottom.addWidget(self._status_lbl)
        bottom.addStretch()
        hint = QLabel(t("review_hint"))
        hint.setObjectName("secondary")
        bottom.addWidget(hint)
        root.addLayout(bottom)

        self._set_filter("open")

    # ------------------------------------------------------------------
    # Data laden / renderen
    # ------------------------------------------------------------------

    def _reload(self):
        """Herbereken alle actie-objecten uit de huidige data."""
        try:
            self._items = report_generator.enumerate_action_items(self._data)
        except Exception:
            self._items = []
        self._render()

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
                extra += f" — “{ap['reason']}”"
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