# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/connect_smart_dialog.py
# Role:    Poort koppelen aan wandpunt, eindapparaat of poort — met zoekfunctie
# Version: 1.2.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie
#                   3 tabs: Wandpunt / Eindapparaat / Poort
#                   Zoekbalk per tab, in-gebruik items grijs maar selecteerbaar
#          1.1.0 — "⊕ Nieuw wandpunt" knop in wandpunt-tab
#                   Aparte in-gebruik tekst per type (wandpunt / eindapparaat / poort)
#                   Vrije wandpunten sorteren vóór in-gebruik wandpunten
#          1.2.0 — Auto-focus op zoekveld bij openen dialoog
#                   Auto-focus op zoekveld bij wisselen van tab
# =============================================================================

import re

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from app.helpers.i18n import t, get_language
from app.helpers.settings_storage import get_outlet_location_label

_USER_ROLE  = 256   # Qt.UserRole  — item id
_IN_USE_ROLE = 257  # bool — al verbonden

_CABLE_TYPES = [
    ("utp_cat5e",  "cable_utp_cat5e"),
    ("utp_cat6",   "cable_utp_cat6"),
    ("utp_cat6a",  "cable_utp_cat6a"),
    ("fiber_sm",   "cable_fiber_sm"),
    ("fiber_mm",   "cable_fiber_mm"),
    ("dak",        "cable_dak"),
    ("other",      "cable_other"),
]

# Tab indices — ook geëxporteerd zodat main_window ze kan gebruiken
_TAB_OUTLET   = 0
_TAB_ENDPOINT = 1
_TAB_PORT     = 2


class ConnectSmartDialog(QDialog):
    """
    Universele koppeldialoog voor poorten.

    Bronpoort is reeds bekend (port_id + port_label).
    De gebruiker kiest het doel via tabs met zoekfunctie:
      - Tab 0: Wandpunt  (+ knop om nieuw wandpunt aan te maken)
      - Tab 1: Eindapparaat
      - Tab 2: Poort (cross-rack / cross-ruimte)
    """

    def __init__(
        self,
        data: dict,
        port_id: str,
        port_label: str,
        initial_tab: int = _TAB_OUTLET,
        parent=None,
    ):
        super().__init__(parent)
        self._data       = data
        self._port_id    = port_id
        self._port_label = port_label
        self._result     = None

        # Bronpoort context bepalen
        self._src_site_id   = ""
        self._src_device_id = ""
        src_port = next((p for p in data.get("ports", []) if p["id"] == port_id), None)
        if src_port:
            self._src_device_id = src_port.get("device_id", "")
            for site in data.get("sites", []):
                for room in site.get("rooms", []):
                    for rack in room.get("racks", []):
                        for slot in rack.get("slots", []):
                            if slot.get("device_id") == self._src_device_id:
                                self._src_site_id = site["id"]

        # Verbonden sets opbouwen
        self._connected_outlets = set()
        self._connected_ports   = set()
        self._connected_eps     = set()
        for conn in data.get("connections", []):
            ft, fid = conn.get("from_type", ""), conn.get("from_id", "")
            tt, tid = conn.get("to_type",   ""), conn.get("to_id",   "")
            if ft == "wall_outlet": self._connected_outlets.add(fid)
            if tt == "wall_outlet": self._connected_outlets.add(tid)
            if ft == "port":        self._connected_ports.add(fid)
            if tt == "port":        self._connected_ports.add(tid)
            if ft == "endpoint":    self._connected_eps.add(fid)
            if tt == "endpoint":    self._connected_eps.add(tid)

        # Interne lijsten voor filter
        self._all_outlets:   list[dict] = []
        self._all_endpoints: list[dict] = []
        self._all_ports:     list[dict] = []

        self.setWindowTitle(t("dlg_connect_smart_title"))
        self.setMinimumWidth(580)
        self.setMinimumHeight(500)
        self.setModal(True)

        self._build_ui()
        self._populate_outlets()
        self._populate_endpoints()
        self._populate_ports()
        self._tabs.setCurrentIndex(initial_tab)

    # ------------------------------------------------------------------
    # UI opbouw
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── Bronpoort info ───────────────────────────────────────────
        grp_src = QGroupBox(t("label_port"))
        grp_src.setFlat(True)
        src_layout = QHBoxLayout(grp_src)
        src_layout.setContentsMargins(6, 4, 6, 4)
        lbl_port = QLabel(self._port_label)
        lbl_port.setObjectName("device-label")
        src_layout.addWidget(lbl_port)
        src_layout.addStretch()
        root.addWidget(grp_src)

        # ── Tabs ─────────────────────────────────────────────────────
        self._tabs = QTabWidget()

        # ── Tab 0: Wandpunt ──────────────────────────────────────────
        tab_outlet = QWidget()
        ol = QVBoxLayout(tab_outlet)
        ol.setContentsMargins(8, 8, 8, 4)
        ol.setSpacing(6)

        # Zoekbalk + Nieuw-knop op één rij
        search_row = QHBoxLayout()
        self._search_outlet = QLineEdit()
        self._search_outlet.setPlaceholderText(
            f"🔍  {t('search_placeholder_outlet')}"
        )
        self._search_outlet.textChanged.connect(self._filter_outlets)
        self._btn_new_outlet = QPushButton("⊕  " + t("btn_new_outlet"))
        self._btn_new_outlet.setToolTip(t("btn_new_outlet"))
        self._btn_new_outlet.clicked.connect(self._on_new_outlet)
        search_row.addWidget(self._search_outlet, 1)
        search_row.addWidget(self._btn_new_outlet)

        self._list_outlet = QListWidget()
        self._list_outlet.setMinimumHeight(200)
        ol.addLayout(search_row)
        ol.addWidget(self._list_outlet)
        self._tabs.addTab(tab_outlet, t("label_wall_outlet"))

        # ── Tab 1: Eindapparaat ──────────────────────────────────────
        tab_ep = QWidget()
        el = QVBoxLayout(tab_ep)
        el.setContentsMargins(8, 8, 8, 4)
        el.setSpacing(6)
        self._search_endpoint = QLineEdit()
        self._search_endpoint.setPlaceholderText(
            f"🔍  {t('search_placeholder_endpoint')}"
        )
        self._search_endpoint.textChanged.connect(self._filter_endpoints)
        self._list_endpoint = QListWidget()
        self._list_endpoint.setMinimumHeight(200)
        el.addWidget(self._search_endpoint)
        el.addWidget(self._list_endpoint)
        self._tabs.addTab(tab_ep, t("label_endpoint"))

        # ── Tab 2: Poort ─────────────────────────────────────────────
        tab_port = QWidget()
        pl = QVBoxLayout(tab_port)
        pl.setContentsMargins(8, 8, 8, 4)
        pl.setSpacing(6)
        self._search_port = QLineEdit()
        self._search_port.setPlaceholderText(
            f"🔍  {t('search_placeholder_port')}"
        )
        self._search_port.textChanged.connect(self._filter_ports)
        self._list_port = QListWidget()
        self._list_port.setMinimumHeight(200)
        pl.addWidget(self._search_port)
        pl.addWidget(self._list_port)
        self._tabs.addTab(tab_port, t("label_port"))

        root.addWidget(self._tabs, 1)

        # 1.2.0 — Focus op zoekveld bij tab-wissel
        self._tabs.currentChanged.connect(self._focus_search)

        # ── Scheidingslijn ───────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        # ── Kabeltype ────────────────────────────────────────────────
        cable_row = QHBoxLayout()
        cable_row.addWidget(QLabel(t("label_cable_type") + ":"))
        self._ddl_cable = QComboBox()
        for val, key in _CABLE_TYPES:
            self._ddl_cable.addItem(t(key), val)
        self._ddl_cable.setCurrentIndex(1)  # standaard UTP Cat6
        cable_row.addWidget(self._ddl_cable)
        cable_row.addStretch()
        root.addLayout(cable_row)

        # ── Notitie ──────────────────────────────────────────────────
        notes_row = QHBoxLayout()
        notes_row.addWidget(QLabel(t("label_notes") + ":"))
        self._notes = QLineEdit()
        self._notes.setPlaceholderText(t("label_notes") + "...")
        notes_row.addWidget(self._notes, 1)
        root.addLayout(notes_row)

        # ── Knoppen ──────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(t("btn_cancel"))
        btn_save   = QPushButton(t("btn_save"))
        btn_save.setDefault(True)
        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Focus helpers — 1.2.0
    # ------------------------------------------------------------------

    def showEvent(self, event):
        """Auto-focus op het zoekveld van de initieel actieve tab."""
        super().showEvent(event)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._focus_search)

    def _focus_search(self):
        """Geef focus aan het zoekveld van de huidige tab."""
        idx = self._tabs.currentIndex()
        if idx == _TAB_OUTLET:
            self._search_outlet.setFocus()
        elif idx == _TAB_ENDPOINT:
            self._search_endpoint.setFocus()
        else:
            self._search_port.setFocus()

    # ------------------------------------------------------------------
    # Populeren — Wandpunten
    # ------------------------------------------------------------------

    def _populate_outlets(self):
        self._all_outlets = []
        lang = get_language()

        for site in self._data.get("sites", []):
            site_name = site.get("name", "?")
            for room in site.get("rooms", []):
                room_name = room.get("name", "?")
                for wo in room.get("wall_outlets", []):
                    loc_key   = wo.get("location_description", "")
                    loc_label = (
                        get_outlet_location_label(loc_key, lang)
                        if loc_key else ""
                    )
                    parts = [site_name, room_name, wo.get("name", wo["id"])]
                    if loc_label:
                        parts.append(loc_label)
                    label  = "  —  ".join(parts)
                    in_use = wo["id"] in self._connected_outlets
                    self._all_outlets.append({
                        "label":  label,
                        "id":     wo["id"],
                        "in_use": in_use,
                    })

        # Vrije wandpunten eerst, dan in-gebruik — binnen elke groep alfabetisch
        self._all_outlets.sort(key=lambda x: (x["in_use"], x["label"].lower()))
        self._filter_outlets()

    def _filter_outlets(self, text: str = ""):
        self._list_outlet.clear()
        q = (text if text != "" else self._search_outlet.text()).strip().lower()
        for item_data in self._all_outlets:
            if q and q not in item_data["label"].lower():
                continue
            suffix = f"  ({t('lbl_already_connected')})" if item_data["in_use"] else ""
            item = self._make_list_item(
                item_data["label"] + suffix,
                item_data["id"],
                item_data["in_use"],
            )
            self._list_outlet.addItem(item)

    # ------------------------------------------------------------------
    # Populeren — Eindapparaten
    # ------------------------------------------------------------------

    def _populate_endpoints(self):
        self._all_endpoints = []
        from app.helpers import settings_storage
        lang        = get_language()
        ep_type_map = {
            et.get("key", ""): et.get(f"label_{lang}", et.get("label_nl", ""))
            for et in settings_storage.load_endpoint_types()
        }

        for ep in sorted(
            self._data.get("endpoints", []),
            key=lambda e: e.get("name", "").lower()
        ):
            ep_id    = ep.get("id", "")
            ep_name  = ep.get("name", ep_id or "?")
            ep_type  = ep.get("type", "")
            type_lbl = ep_type_map.get(ep_type, ep_type)
            loc      = ep.get("location", "")
            ip       = ep.get("ip", "")

            parts = [ep_name]
            if type_lbl:
                parts.append(type_lbl)
            if loc:
                parts.append(loc)
            if ip:
                parts.append(ip)
            label  = "  —  ".join(parts)
            in_use = ep_id in self._connected_eps
            self._all_endpoints.append({
                "label":  label,
                "id":     ep_id,
                "in_use": in_use,
            })

        self._all_endpoints.sort(key=lambda x: (x["in_use"], x["label"].lower()))
        self._filter_endpoints()

    def _filter_endpoints(self, text: str = ""):
        self._list_endpoint.clear()
        q = (text if text != "" else self._search_endpoint.text()).strip().lower()
        for item_data in self._all_endpoints:
            if q and q not in item_data["label"].lower():
                continue
            suffix = f"  ({t('lbl_already_connected')})" if item_data["in_use"] else ""
            item = self._make_list_item(
                item_data["label"] + suffix,
                item_data["id"],
                item_data["in_use"],
            )
            self._list_endpoint.addItem(item)

    # ------------------------------------------------------------------
    # Populeren — Poorten
    # ------------------------------------------------------------------

    def _populate_ports(self):
        self._all_ports = []
        device_map = {d["id"]: d for d in self._data.get("devices", [])}

        for site in self._data.get("sites", []):
            site_name = site.get("name", "?")
            for room in site.get("rooms", []):
                room_name = room.get("name", "?")
                for rack in room.get("racks", []):
                    rack_name = rack.get("name", "?")
                    for slot in rack.get("slots", []):
                        dev_id = slot.get("device_id", "")
                        if dev_id == self._src_device_id:
                            continue  # eigen device uitsluiten
                        dev = device_map.get(dev_id)
                        if not dev:
                            continue
                        dev_name  = dev.get("name", dev_id)
                        dev_type  = t(f"device_{dev.get('type', 'other')}")
                        dev_label = (
                            f"{site_name}  —  {room_name}  —  "
                            f"{rack_name}  —  {dev_name}  ({dev_type})"
                        )
                        ports = [
                            p for p in self._data.get("ports", [])
                            if p.get("device_id") == dev_id
                        ]
                        for port in sorted(ports, key=self._port_sort_key):
                            pid      = port.get("id", "")
                            pname    = port.get("name", pid)
                            side     = port.get("side", "")
                            side_lbl = (
                                t("label_front") if side == "front"
                                else t("label_back") if side == "back"
                                else side.upper()
                            )
                            label  = f"{dev_label}  ·  {pname}  ({side_lbl})"
                            in_use = pid in self._connected_ports
                            self._all_ports.append({
                                "label":  label,
                                "id":     pid,
                                "in_use": in_use,
                            })

        self._filter_ports()

    def _filter_ports(self, text: str = ""):
        self._list_port.clear()
        q = (text if text != "" else self._search_port.text()).strip().lower()
        free   = [p for p in self._all_ports if not p["in_use"]]
        in_use = [p for p in self._all_ports if     p["in_use"]]
        for item_data in free + in_use:
            if q and q not in item_data["label"].lower():
                continue
            suffix = f"  ({t('lbl_already_connected')})" if item_data["in_use"] else ""
            item = self._make_list_item(
                item_data["label"] + suffix,
                item_data["id"],
                item_data["in_use"],
            )
            self._list_port.addItem(item)

    # ------------------------------------------------------------------
    # Nieuw wandpunt aanmaken vanuit de dialoog
    # ------------------------------------------------------------------

    def _on_new_outlet(self):
        """
        Open WallOutletDialog om een nieuw wandpunt aan te maken.
        Na opslaan wordt het direct geselecteerd in de lijst.
        """
        from app.gui.dialogs.wall_outlet_dialog import WallOutletDialog
        import time

        # Bepaal standaard ruimte op basis van huidige site (eerste ruimte)
        default_room_id = ""
        for site in self._data.get("sites", []):
            for room in site.get("rooms", []):
                if room.get("wall_outlets") is not None:
                    default_room_id = room.get("id", "")
                    break
            if default_room_id:
                break

        # Verzamel alle bestaande eindapparaten
        endpoints = list(self._data.get("endpoints", []))

        dlg = WallOutletDialog(
            parent=self,
            outlet=None,
            room_id=default_room_id,
            endpoints=endpoints,
            existing_outlets=[],
            data=self._data,
        )
        if not dlg.exec():
            return

        result   = dlg.get_result()
        new_eps  = dlg.get_endpoints_result()
        if not result:
            return

        # Genereer ID indien nog leeg
        if not result.get("id"):
            result["id"] = f"wo_{int(time.time() * 1000) % 100_000_000}"

        # Bepaal effectieve ruimte
        effective_room_id = result.get("room_id") or default_room_id
        if not effective_room_id:
            return

        # Voeg wandpunt toe aan de ruimte in self._data
        for site in self._data.get("sites", []):
            for room in site.get("rooms", []):
                if room["id"] == effective_room_id:
                    room.setdefault("wall_outlets", []).append(result)
                    break

        # Verwerk nieuwe/gewijzigde eindapparaten
        existing_ep_ids = {ep["id"] for ep in self._data.get("endpoints", [])}
        for ep in new_eps:
            if ep.get("id") and ep["id"] not in existing_ep_ids:
                self._data.setdefault("endpoints", []).append(ep)

        # Herlaad lijst en selecteer het nieuwe wandpunt
        in_use_before = len(self._connected_outlets)
        self._populate_outlets()

        # Selecteer het nieuwe item
        for i in range(self._list_outlet.count()):
            item = self._list_outlet.item(i)
            if item and item.data(_USER_ROLE) == result["id"]:
                self._list_outlet.setCurrentRow(i)
                self._list_outlet.scrollToItem(item)
                break

    # ------------------------------------------------------------------
    # Helper — lijst item opbouwen
    # ------------------------------------------------------------------

    def _make_list_item(self, label: str, item_id: str, in_use: bool) -> QListWidgetItem:
        item = QListWidgetItem(label)
        if in_use:
            item.setForeground(QColor("#888888"))
        item.setData(_USER_ROLE, item_id)
        item.setData(_IN_USE_ROLE, in_use)
        return item

    @staticmethod
    def _port_sort_key(p: dict):
        name  = p.get("name", "")
        parts = [
            int(c) if c.isdigit() else c.lower()
            for c in re.split(r"(\d+)", name)
        ]
        side_order = 0 if p.get("side") == "front" else (
                     1 if p.get("side") == "back"  else 2)
        return (side_order, parts)

    # ------------------------------------------------------------------
    # Opslaan
    # ------------------------------------------------------------------

    def _on_save(self):
        tab_idx = self._tabs.currentIndex()

        if tab_idx == _TAB_OUTLET:
            item = self._list_outlet.currentItem()
            if not item or not item.data(_USER_ROLE):
                QMessageBox.warning(self, self.windowTitle(), t("err_no_outlet_selected"))
                return
            to_id   = item.data(_USER_ROLE)
            to_type = "wall_outlet"
            if item.data(_IN_USE_ROLE):
                reply = QMessageBox.question(
                    self, self.windowTitle(),
                    t("warn_outlet_already_connected"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

        elif tab_idx == _TAB_ENDPOINT:
            item = self._list_endpoint.currentItem()
            if not item or not item.data(_USER_ROLE):
                QMessageBox.warning(self, self.windowTitle(), t("err_no_endpoint_selected"))
                return
            to_id   = item.data(_USER_ROLE)
            to_type = "endpoint"
            if item.data(_IN_USE_ROLE):
                reply = QMessageBox.question(
                    self, self.windowTitle(),
                    t("warn_endpoint_already_connected"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

        else:  # _TAB_PORT
            item = self._list_port.currentItem()
            if not item or not item.data(_USER_ROLE):
                QMessageBox.warning(self, self.windowTitle(), t("err_no_port_selected"))
                return
            to_id   = item.data(_USER_ROLE)
            to_type = "port"
            if item.data(_IN_USE_ROLE):
                reply = QMessageBox.question(
                    self, self.windowTitle(),
                    t("warn_port_already_connected"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

        existing_ids = {c["id"] for c in self._data.get("connections", [])}
        new_id = f"conn{len(existing_ids) + 1}"
        while new_id in existing_ids:
            new_id += "_"

        self._result = {
            "id":         new_id,
            "from_id":    self._port_id,
            "from_type":  "port",
            "to_id":      to_id,
            "to_type":    to_type,
            "cable_type": self._ddl_cable.currentData(),
            "label":      "",
            "notes":      self._notes.text().strip(),
        }
        self.accept()

    def get_result(self) -> dict | None:
        return self._result