# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/connection_dialog.py
# Role:    Verbinding aanmaken via DDL (alternatief voor klik-klik)
# Version: 1.0.0
# Author:  Barremans
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QPushButton, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt

from app.helpers.i18n import t
from app.helpers import settings_storage

# Kabeltype DDL waarden
_CABLE_TYPES = [
    ("utp_cat5e",  "cable_utp_cat5e"),
    ("utp_cat6",   "cable_utp_cat6"),
    ("utp_cat6a",  "cable_utp_cat6a"),
    ("fiber_sm",   "cable_fiber_sm"),
    ("fiber_mm",   "cable_fiber_mm"),
    ("dak",        "cable_dak"),
    ("other",      "cable_other"),
]


class ConnectionDialog(QDialog):
    """
    Dialoogvenster voor het aanmaken van een verbinding via DDL-selectie.
    Cascade DDL: site → ruimte → rack/wandpunten → device → poort (voor poort A en B)
    """

    def __init__(self, data: dict, parent=None,
                 preselect_port_id: str = ""):
        super().__init__(parent)
        self._data = data
        self._preselect_port_id = preselect_port_id
        self._result_connection = None  # gevuld na opslaan

        self.setWindowTitle(t("menu_connect"))
        self.setMinimumWidth(500)
        self.setModal(True)
        self._build()

        if preselect_port_id:
            self._preselect(preselect_port_id)

    # ------------------------------------------------------------------
    # Opbouw
    # ------------------------------------------------------------------

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Poort A ──────────────────────────────────────────────────
        grp_a = QGroupBox(f"{t('label_port')} A")
        self._port_a_widgets = self._build_port_selector(grp_a)
        layout.addWidget(grp_a)

        # ── Poort B ──────────────────────────────────────────────────
        grp_b = QGroupBox(f"{t('label_port')} B")
        self._port_b_widgets = self._build_port_selector(grp_b)
        layout.addWidget(grp_b)

        # ── Kabeltype ────────────────────────────────────────────────
        cable_layout = QHBoxLayout()
        cable_layout.addWidget(QLabel(t("label_cable_type") + ":"))
        self._ddl_cable = QComboBox()
        for val, key in _CABLE_TYPES:
            self._ddl_cable.addItem(t(key), val)
        self._ddl_cable.setCurrentIndex(1)   # standaard UTP Cat6
        cable_layout.addWidget(self._ddl_cable)
        cable_layout.addStretch()
        layout.addLayout(cable_layout)

        # ── Knoppen ──────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_save   = QPushButton(t("btn_save"))
        btn_cancel = QPushButton(t("btn_cancel"))
        btn_save.clicked.connect(self._on_save)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def _build_port_selector(self, group: QGroupBox) -> dict:
        """Bouwt cascade DDL voor één poort. Geeft widget referenties terug."""
        form = QFormLayout(group)
        form.setSpacing(6)

        ddl_site   = QComboBox()
        ddl_room   = QComboBox()
        ddl_device = QComboBox()
        ddl_port   = QComboBox()

        ddl_room.setEnabled(False)
        ddl_device.setEnabled(False)
        ddl_port.setEnabled(False)

        # Vul sites
        for site in self._data.get("sites", []):
            ddl_site.addItem(site["name"], site["id"])
        ddl_site.insertItem(0, "— " + t("label_site") + " —", "")
        ddl_site.setCurrentIndex(0)

        # Cascade signalen
        widgets = {
            "site":   ddl_site,
            "room":   ddl_room,
            "device": ddl_device,
            "port":   ddl_port,
        }
        ddl_site.currentIndexChanged.connect(
            lambda: self._on_site_changed(widgets))
        ddl_room.currentIndexChanged.connect(
            lambda: self._on_room_changed(widgets))
        ddl_device.currentIndexChanged.connect(
            lambda: self._on_device_changed(widgets))

        form.addRow(t("label_site")   + ":", ddl_site)
        form.addRow(t("label_room")   + ":", ddl_room)
        form.addRow(t("label_device") + ":", ddl_device)
        form.addRow(t("label_port")   + ":", ddl_port)

        return widgets

    # ------------------------------------------------------------------
    # Cascade handlers
    # ------------------------------------------------------------------

    def _on_site_changed(self, w: dict):
        site_id = w["site"].currentData()
        w["room"].clear()
        w["device"].clear()
        w["port"].clear()
        w["room"].setEnabled(False)
        w["device"].setEnabled(False)
        w["port"].setEnabled(False)

        if not site_id:
            return
        site = next((s for s in self._data["sites"] if s["id"] == site_id), None)
        if not site:
            return

        w["room"].addItem("— " + t("label_room") + " —", "")
        for room in site.get("rooms", []):
            w["room"].addItem(room["name"], room["id"])
        w["room"].setEnabled(True)

    def _on_room_changed(self, w: dict):
        room_id = w["room"].currentData()
        w["device"].clear()
        w["port"].clear()
        w["device"].setEnabled(False)
        w["port"].setEnabled(False)

        if not room_id:
            return
        room = self._find_room(room_id)
        if not room:
            return

        dev_map = {d["id"]: d for d in self._data.get("devices", [])}

        w["device"].addItem("— " + t("label_device") + " —", "")
        for rack in room.get("racks", []):
            for slot in rack.get("slots", []):
                dev = dev_map.get(slot["device_id"])
                if dev:
                    label = f"{dev['name']}  ({t('device_' + dev['type'])})"
                    w["device"].addItem(label, dev["id"])
        w["device"].setEnabled(True)

    def _on_device_changed(self, w: dict):
        dev_id = w["device"].currentData()
        w["port"].clear()
        w["port"].setEnabled(False)

        if not dev_id:
            return
        dev = next((d for d in self._data.get("devices", []) if d["id"] == dev_id), None)
        if not dev:
            return

        # Beschikbare (vrije) poorten opzoeken
        connected_ports = set()
        for conn in self._data.get("connections", []):
            if conn["from_type"] == "port":
                connected_ports.add(conn["from_id"])
            if conn["to_type"] == "port":
                connected_ports.add(conn["to_id"])

        ports = [p for p in self._data.get("ports", [])
                 if p["device_id"] == dev_id and p["id"] not in connected_ports]

        w["port"].addItem("— " + t("label_port") + " —", "")
        for port in ports:
            side_label = t("label_" + port["side"])
            w["port"].addItem(f"{port['name']}  ({side_label})", port["id"])
        w["port"].setEnabled(True)

    # ------------------------------------------------------------------
    # Opslaan
    # ------------------------------------------------------------------

    def _on_save(self):
        port_a_id  = self._port_a_widgets["port"].currentData()
        port_b_id  = self._port_b_widgets["port"].currentData()
        cable_type = self._ddl_cable.currentData()

        if not port_a_id or not port_b_id:
            QMessageBox.warning(self, t("menu_connect"),
                                t("msg_connect_select_a"))
            return

        if port_a_id == port_b_id:
            QMessageBox.warning(self, t("menu_connect"),
                                t("err_same_port"))
            return

        # Genereer uniek ID
        existing_ids = {c["id"] for c in self._data.get("connections", [])}
        new_id = f"conn{len(existing_ids) + 1}"
        while new_id in existing_ids:
            new_id += "_"

        self._result_connection = {
            "id":         new_id,
            "from_id":    port_a_id,
            "from_type":  "port",
            "to_id":      port_b_id,
            "to_type":    "port",
            "cable_type": cable_type,
            "notes":      "",
        }
        self.accept()

    # ------------------------------------------------------------------
    # Resultaat ophalen
    # ------------------------------------------------------------------

    def get_connection(self) -> dict | None:
        """Geeft de nieuwe verbinding terug na accept(), anders None."""
        return self._result_connection

    # ------------------------------------------------------------------
    # Hulpfuncties
    # ------------------------------------------------------------------

    def _find_room(self, room_id: str) -> dict | None:
        for site in self._data.get("sites", []):
            for room in site.get("rooms", []):
                if room["id"] == room_id:
                    return room
        return None

    def _preselect(self, port_id: str):
        """Preselecteer poort A op basis van een reeds aangeklikte poort."""
        port = next((p for p in self._data.get("ports", [])
                     if p["id"] == port_id), None)
        if not port:
            return
        # Zoek site en room
        for site in self._data.get("sites", []):
            for room in site.get("rooms", []):
                for rack in room.get("racks", []):
                    for slot in rack.get("slots", []):
                        if slot["device_id"] == port["device_id"]:
                            w = self._port_a_widgets
                            # Site selecteren
                            idx = w["site"].findData(site["id"])
                            if idx >= 0:
                                w["site"].setCurrentIndex(idx)
                                # Room selecteren
                                idx = w["room"].findData(room["id"])
                                if idx >= 0:
                                    w["room"].setCurrentIndex(idx)
                                    # Device selecteren
                                    idx = w["device"].findData(port["device_id"])
                                    if idx >= 0:
                                        w["device"].setCurrentIndex(idx)
                                        # Poort selecteren
                                        idx = w["port"].findData(port_id)
                                        if idx >= 0:
                                            w["port"].setCurrentIndex(idx)
                            return