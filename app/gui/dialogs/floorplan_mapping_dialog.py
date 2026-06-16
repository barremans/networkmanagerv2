# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/floorplan_mapping_dialog.py
# Role:    Dialoog — SVG punt koppelen aan wandpunt, eindapparaat of poort
# Version: 1.7.1
# Author:  Barremans
# Changes: 1.7.1 -- F1: get_all_sites() voor v2 JSON
#          1.7.0 — Auto-focus op zoekveld bij openen en bij wisselen van tab:
#                   showEvent + _focus_search + currentChanged gekoppeld
#          1.6.0 — _populate_port_devices: filter op device-definitie
#                   _port_sort_key: front poorten eerst (was back eerst)
#                   back_ports=0 → back poorten niet tonen
#                   front+sfp max → overbodige front poorten niet tonen
#                   Voorkomt orphan-poorten in koppellijst bij switch zonder back
#          1.5.0 — Wandpunt label toont nu ook locatie:
#                   "SERVERRUIMTE — D23 — OB REFTER (G)"
#                   zodat gelijknamige wandpunten onderscheidbaar zijn
#          1.4.0 — Zoekbalk per tab: QLineEdit + QListWidget ipv QComboBox
#                   Filter bij typen, selectie via klik in lijst
#                   Poort tab: device + poort in één regel, direct doorzoekbaar
#          1.3.0 — Poort koppeling: Tab 3 "Poort"
#          1.2.0 — Eindapparaat koppeling: type-keuze via tabs
# =============================================================================

import re

from PySide6.QtWidgets import (
    QDialog,
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

from app.helpers import settings_storage
from app.helpers.i18n import t, get_language
from app.helpers.settings_storage import get_outlet_location_label
from app.helpers.settings_storage import get_all_sites
from app.services import floorplan_service

_USER_ROLE = 256   # Qt.UserRole


class FloorplanMappingDialog(QDialog):
    """
    Koppel één SVG punt aan één bestaand wandpunt, eindapparaat of poort.

    Type-keuze via tabs met zoekfilter:
    - Tab 1: Wandpunt
    - Tab 2: Eindapparaat
    - Tab 3: Poort

    Resultaat opgeslagen als:
    - Wandpunt:     "outlet_xxx"
    - Eindapparaat: "ep:ep_xxx"
    - Poort:        "port:port_xxx"
    """

    def __init__(
        self,
        parent=None,
        data: dict | None = None,
        floorplan: dict | None = None,
        svg_point: str = "",
    ):
        super().__init__(parent)

        self._data = data or {}
        self._floorplan = floorplan or {}
        self._svg_point = svg_point
        self._result: dict | None = None

        # Interne lijsten voor filter
        self._all_outlets:   list[tuple[str, str]] = []
        self._all_endpoints: list[tuple[str, str]] = []
        self._all_ports:     list[tuple[str, str]] = []

        self._build_ui()
        self._populate_outlets()
        self._populate_endpoints()
        self._populate_port_devices()
        self._apply_current_mapping_selection()
        self._apply_read_only_mode()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.setWindowTitle(t("floorplan_mapping_title"))
        self.setModal(True)
        self.setMinimumWidth(560)
        self.setMinimumHeight(380)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # SVG punt label
        from PySide6.QtWidgets import QFormLayout
        form_top = QFormLayout()
        form_top.setContentsMargins(0, 0, 0, 0)
        form_top.setSpacing(8)
        self._lbl_svg_point = QLabel(self._svg_point or "-")
        form_top.addRow(f"{t('floorplan_mapping_svg_point')}:", self._lbl_svg_point)
        root.addLayout(form_top)

        # Tabs
        self._tabs = QTabWidget()

        # Tab 1 — Wandpunt
        tab_outlet = QWidget()
        ol = QVBoxLayout(tab_outlet)
        ol.setContentsMargins(8, 8, 8, 8)
        ol.setSpacing(6)
        self._search_outlet = QLineEdit()
        self._search_outlet.setPlaceholderText("🔍  Zoek ruimte of wandpunt...")
        self._search_outlet.textChanged.connect(self._filter_outlets)
        self._list_outlet = QListWidget()
        self._list_outlet.setMinimumHeight(180)
        ol.addWidget(self._search_outlet)
        ol.addWidget(self._list_outlet)
        self._tabs.addTab(tab_outlet, t("label_wall_outlet"))

        # Tab 2 — Eindapparaat
        tab_ep = QWidget()
        el = QVBoxLayout(tab_ep)
        el.setContentsMargins(8, 8, 8, 8)
        el.setSpacing(6)
        self._search_endpoint = QLineEdit()
        self._search_endpoint.setPlaceholderText("🔍  Zoek eindapparaat...")
        self._search_endpoint.textChanged.connect(self._filter_endpoints)
        self._list_endpoint = QListWidget()
        self._list_endpoint.setMinimumHeight(180)
        el.addWidget(self._search_endpoint)
        el.addWidget(self._list_endpoint)
        self._tabs.addTab(tab_ep, t("label_endpoint"))

        # Tab 3 — Poort
        tab_port = QWidget()
        pl = QVBoxLayout(tab_port)
        pl.setContentsMargins(8, 8, 8, 8)
        pl.setSpacing(6)
        self._search_port = QLineEdit()
        self._search_port.setPlaceholderText("🔍  Zoek device of poort...")
        self._search_port.textChanged.connect(self._filter_ports)
        self._list_port = QListWidget()
        self._list_port.setMinimumHeight(180)
        pl.addWidget(self._search_port)
        pl.addWidget(self._list_port)
        self._tabs.addTab(tab_port, t("label_port"))

        root.addWidget(self._tabs)
        self._tabs.currentChanged.connect(self._focus_search)

        # Knoppen
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self._btn_save = QPushButton(t("floorplan_mapping_assign"))
        self._btn_save.clicked.connect(self._on_save)
        self._btn_cancel = QPushButton(t("btn_cancel"))
        self._btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_save)
        btn_row.addWidget(self._btn_cancel)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Focus
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._focus_search)

    def _focus_search(self):
        idx = self._tabs.currentIndex()
        if idx == 0:
            self._search_outlet.setFocus()
        elif idx == 1:
            self._search_endpoint.setFocus()
        else:
            self._search_port.setFocus()

    # ------------------------------------------------------------------
    # Populeren
    # ------------------------------------------------------------------

    def _populate_outlets(self):
        self._all_outlets = []
        site_id = self._floorplan.get("site_id")
        lang = get_language()
        if site_id:
            for site in get_all_sites(self._data):
                if site.get("id") != site_id:
                    continue
                for room in site.get("rooms", []):
                    room_name = room.get("name", "?")
                    for outlet in room.get("wall_outlets", []):
                        loc_key   = outlet.get("location_description", "")
                        loc_label = (
                            get_outlet_location_label(loc_key, lang)
                            if loc_key else ""
                        )
                        # 1.5.0 — locatie toevoegen zodat gelijknamige wandpunten
                        # onderscheidbaar zijn: "SERVERRUIMTE — D23 — OB REFTER (G)"
                        parts = [room_name, outlet.get("name", outlet.get("id", "?"))]
                        if loc_label:
                            parts.append(loc_label)
                        label = "  —  ".join(parts)
                        self._all_outlets.append((label, outlet.get("id", "")))
                break
        self._all_outlets.sort(key=lambda x: x[0].lower())
        self._filter_outlets("")

    def _filter_outlets(self, text: str = ""):
        self._list_outlet.clear()
        q = text.strip().lower()
        for label, oid in self._all_outlets:
            if not q or q in label.lower():
                item = QListWidgetItem(label)
                item.setData(_USER_ROLE, oid)
                self._list_outlet.addItem(item)

    def _populate_endpoints(self):
        self._all_endpoints = []
        for ep in sorted(self._data.get("endpoints", []), key=lambda e: e.get("name", "").lower()):
            ep_id   = ep.get("id", "")
            ep_name = ep.get("name", ep_id or "?")
            loc     = ep.get("location", "")
            label   = f"{ep_name}  —  {loc}" if loc else ep_name
            self._all_endpoints.append((label, ep_id))
        self._filter_endpoints("")

    def _filter_endpoints(self, text: str = ""):
        self._list_endpoint.clear()
        q = text.strip().lower()
        for label, ep_id in self._all_endpoints:
            if not q or q in label.lower():
                item = QListWidgetItem(label)
                item.setData(_USER_ROLE, ep_id)
                self._list_endpoint.addItem(item)

    def _populate_port_devices(self):
        """1.4.0 — Bouw volledige poort-lijst: device + poort in één doorzoekbare regel."""
        self._all_ports = []
        site_id = self._floorplan.get("site_id")
        if site_id:
            device_map = {d["id"]: d for d in self._data.get("devices", [])}
            for site in get_all_sites(self._data):
                if site.get("id") != site_id:
                    continue
                for room in site.get("rooms", []):
                    for rack in room.get("racks", []):
                        for slot in rack.get("slots", []):
                            dev_id = slot.get("device_id", "")
                            dev = device_map.get(dev_id)
                            if not dev:
                                continue
                            dev_label = f"{room['name']} / {rack['name']} — {dev['name']}"
                            ports = [p for p in self._data.get("ports", [])
                                     if p.get("device_id") == dev_id]
                            for port in sorted(ports, key=self._port_sort_key):
                                pid      = port.get("id", "")
                                pname    = port.get("name", pid)
                                side     = port.get("side", "")
                                side_lbl = f" ({side.upper()})" if side else ""
                                label    = f"{dev_label}  ·  {pname}{side_lbl}"
                                self._all_ports.append((label, pid))
                break
        self._filter_ports("")

    def _filter_ports(self, text: str = ""):
        self._list_port.clear()
        q = text.strip().lower()
        for label, pid in self._all_ports:
            if not q or q in label.lower():
                item = QListWidgetItem(label)
                item.setData(_USER_ROLE, pid)
                self._list_port.addItem(item)

    @staticmethod
    def _port_sort_key(p: dict):
        name  = p.get("name", "")
        parts = [int(c) if c.isdigit() else c.lower()
                 for c in re.split(r'(\d+)', name)]
        side_order = 0 if p.get("side", "") == "front" else (
                     1 if p.get("side", "") == "back" else 2)
        return (parts, side_order)

    # ------------------------------------------------------------------
    # Voorselectie & read-only
    # ------------------------------------------------------------------

    def _select_list_item_by_data(self, list_widget: QListWidget, value: str):
        for i in range(list_widget.count()):
            if list_widget.item(i).data(_USER_ROLE) == value:
                list_widget.setCurrentRow(i)
                list_widget.scrollToItem(list_widget.currentItem())
                return

    def _apply_current_mapping_selection(self):
        floorplan_id = self._floorplan.get("id")
        if not floorplan_id or not self._svg_point:
            return

        mapped_val = floorplan_service.get_mapping(floorplan_id, self._svg_point)
        if not mapped_val:
            return

        if mapped_val.startswith("port:"):
            port_id = mapped_val[5:]
            self._select_list_item_by_data(self._list_port, port_id)
            self._tabs.setCurrentIndex(2)
        elif mapped_val.startswith("ep:"):
            ep_id = mapped_val[3:]
            self._select_list_item_by_data(self._list_endpoint, ep_id)
            self._tabs.setCurrentIndex(1)
        else:
            self._select_list_item_by_data(self._list_outlet, mapped_val)
            self._tabs.setCurrentIndex(0)

    def _apply_read_only_mode(self):
        read_only = settings_storage.get_read_only_mode()
        if read_only:
            self._btn_save.setEnabled(False)
            for w in (self._search_outlet, self._list_outlet,
                      self._search_endpoint, self._list_endpoint,
                      self._search_port, self._list_port):
                w.setEnabled(False)

    # ------------------------------------------------------------------
    # Opslaan
    # ------------------------------------------------------------------

    def _on_save(self):
        if settings_storage.get_read_only_mode():
            self.reject()
            return

        floorplan_id = self._floorplan.get("id")
        if not floorplan_id or not self._svg_point:
            QMessageBox.warning(self, self.windowTitle(), t("err_no_selection"))
            return

        tab_idx = self._tabs.currentIndex()

        if tab_idx == 0:
            item = self._list_outlet.currentItem()
            if not item or not item.data(_USER_ROLE):
                QMessageBox.warning(self, self.windowTitle(), t("err_no_selection"))
                return
            mapping_val = item.data(_USER_ROLE)
        elif tab_idx == 1:
            item = self._list_endpoint.currentItem()
            if not item or not item.data(_USER_ROLE):
                QMessageBox.warning(self, self.windowTitle(), t("err_no_selection"))
                return
            mapping_val = f"ep:{item.data(_USER_ROLE)}"
        else:
            item = self._list_port.currentItem()
            if not item or not item.data(_USER_ROLE):
                QMessageBox.warning(self, self.windowTitle(), t("err_no_selection"))
                return
            mapping_val = f"port:{item.data(_USER_ROLE)}"

        floorplan_service.set_mapping(
            floorplan_id=floorplan_id,
            svg_point=self._svg_point,
            outlet_id=mapping_val,
        )

        self._result = {
            "floorplan_id": floorplan_id,
            "svg_point":    self._svg_point,
            "mapping_val":  mapping_val,
        }
        self.accept()

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def get_result(self) -> dict | None:
        return self._result