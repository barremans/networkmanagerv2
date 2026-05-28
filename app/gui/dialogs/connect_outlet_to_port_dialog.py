# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/connect_outlet_to_port_dialog.py
# Role:    Wandpunt koppelen aan een poort — met zoekfunctie
# Version: 1.0.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie
#                   Wandpunt is bronkant (bekend), gebruiker kiest een poort
#                   Zoeklijst: Site — Ruimte — Rack — Device · Poort (SIDE)
#                   Vrije poorten bovenaan, in-gebruik grijs onderaan
#                   Kabeltype + notitie velden
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
    QVBoxLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from app.helpers.i18n import t

_USER_ROLE   = 256
_IN_USE_ROLE = 257

_CABLE_TYPES = [
    ("utp_cat5e",  "cable_utp_cat5e"),
    ("utp_cat6",   "cable_utp_cat6"),
    ("utp_cat6a",  "cable_utp_cat6a"),
    ("fiber_sm",   "cable_fiber_sm"),
    ("fiber_mm",   "cable_fiber_mm"),
    ("dak",        "cable_dak"),
    ("other",      "cable_other"),
]


class ConnectOutletToPortDialog(QDialog):
    """
    Dialoog om een wandpunt te koppelen aan een poort.
    Wandpunt is reeds bekend (outlet_id + outlet_label).
    De gebruiker kiest een doelpoort via zoeklijst.
    """

    def __init__(self, data: dict, outlet_id: str, outlet_label: str, parent=None):
        super().__init__(parent)
        self._data         = data
        self._outlet_id    = outlet_id
        self._outlet_label = outlet_label
        self._result       = None

        # Verbonden poorten
        self._connected_ports = set()
        for conn in data.get("connections", []):
            if conn.get("from_type") == "port":
                self._connected_ports.add(conn["from_id"])
            if conn.get("to_type") == "port":
                self._connected_ports.add(conn["to_id"])

        self._all_ports: list[dict] = []

        self.setWindowTitle(t("dlg_connect_outlet_to_port_title"))
        self.setMinimumWidth(580)
        self.setMinimumHeight(460)
        self.setModal(True)
        self._build_ui()
        self._populate_ports()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── Wandpunt info ────────────────────────────────────────────
        grp = QGroupBox(t("label_wall_outlet"))
        grp.setFlat(True)
        grp_layout = QHBoxLayout(grp)
        grp_layout.setContentsMargins(6, 4, 6, 4)
        lbl = QLabel(self._outlet_label)
        lbl.setObjectName("device-label")
        grp_layout.addWidget(lbl)
        grp_layout.addStretch()
        root.addWidget(grp)

        # ── Poort zoeklijst ──────────────────────────────────────────
        self._search = QLineEdit()
        self._search.setPlaceholderText(f"🔍  {t('search_placeholder_port')}")
        self._search.textChanged.connect(self._filter_ports)
        root.addWidget(self._search)

        self._list = QListWidget()
        self._list.setMinimumHeight(240)
        root.addWidget(self._list, 1)

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
        self._ddl_cable.setCurrentIndex(1)
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
    # Populeren
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
                        dev    = device_map.get(dev_id)
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
        self._list.clear()
        q      = (text or self._search.text()).strip().lower()
        free   = [p for p in self._all_ports if not p["in_use"]]
        in_use = [p for p in self._all_ports if     p["in_use"]]
        for item_data in free + in_use:
            if q and q not in item_data["label"].lower():
                continue
            suffix = f"  ({t('lbl_already_connected')})" if item_data["in_use"] else ""
            item   = QListWidgetItem(item_data["label"] + suffix)
            if item_data["in_use"]:
                item.setForeground(QColor("#888888"))
            item.setData(_USER_ROLE, item_data["id"])
            item.setData(_IN_USE_ROLE, item_data["in_use"])
            self._list.addItem(item)

    @staticmethod
    def _port_sort_key(p: dict):
        name  = p.get("name", "")
        parts = [int(c) if c.isdigit() else c.lower()
                 for c in re.split(r"(\d+)", name)]
        side_order = 0 if p.get("side") == "front" else (
                     1 if p.get("side") == "back"  else 2)
        return (side_order, parts)

    # ------------------------------------------------------------------
    # Opslaan
    # ------------------------------------------------------------------

    def _on_save(self):
        item = self._list.currentItem()
        if not item or not item.data(_USER_ROLE):
            QMessageBox.warning(self, self.windowTitle(), t("err_no_port_selected"))
            return

        port_id = item.data(_USER_ROLE)
        in_use  = item.data(_IN_USE_ROLE)

        if in_use:
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
            "from_id":    self._outlet_id,
            "from_type":  "wall_outlet",
            "to_id":      port_id,
            "to_type":    "port",
            "cable_type": self._ddl_cable.currentData(),
            "label":      "",
            "notes":      self._notes.text().strip(),
        }
        self.accept()

    def get_result(self) -> dict | None:
        return self._result