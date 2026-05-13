# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/connect_port_to_port_dialog.py
# Role:    Poort ↔ Poort verbinding aanmaken (cross-rack / cross-ruimte)
# Version: 1.0.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie
#                  Trapgewijze selectie: Site → Ruimte → Rack → Device → Poort
#                  Alleen vrije poorten tonen als doelpoort
#                  Kabeltype + notitie velden
#                  Zelfde device als bronpoort volledig uitgesloten
# =============================================================================
#
# Gebruik: rechtermuisklik op een poort → "Verbinden met poort..."
# De bronpoort is reeds bekend (port_id). De gebruiker kiest:
#   - Site → Ruimte → Rack → Device → Poort (cascade DDL, alleen vrije poorten)
#   - Kabeltype
#   - Notitie
#
# Data resultaat:
#   {
#     "id":         "conn_xxx",
#     "from_id":    <bron port_id>,
#     "from_type":  "port",
#     "to_id":      <doel port_id>,
#     "to_type":    "port",
#     "cable_type": "utp_cat6",
#     "label":      "",
#     "notes":      ""
#   }
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QComboBox, QTextEdit, QPushButton, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
from app.helpers.i18n import t

_CABLE_TYPES = [
    ("utp_cat5e",  "cable_utp_cat5e"),
    ("utp_cat6",   "cable_utp_cat6"),
    ("utp_cat6a",  "cable_utp_cat6a"),
    ("fiber_sm",   "cable_fiber_sm"),
    ("fiber_mm",   "cable_fiber_mm"),
    ("dak",        "cable_dak"),
    ("other",      "cable_other"),
]


class ConnectPortToPortDialog(QDialog):
    """
    Dialoog om een poort te verbinden met een andere poort (cross-rack / cross-ruimte).
    port_id en port_label zijn al bekend — alleen doelpoort kiezen.
    """

    def __init__(self, data: dict, port_id: str, port_label: str,
                 current_site_id: str = "", current_room_id: str = "",
                 current_rack_id: str = "", parent=None):
        super().__init__(parent)
        self._data            = data
        self._port_id         = port_id
        self._port_label      = port_label
        self._current_site_id = current_site_id
        self._current_room_id = current_room_id
        self._current_rack_id = current_rack_id
        self._result          = None

        # Bepaal device_id van de bronpoort — doeldevice mag nooit hetzelfde zijn
        src_port = next(
            (p for p in data.get("ports", []) if p["id"] == port_id), None
        )
        self._src_device_id = src_port["device_id"] if src_port else ""

        self.setWindowTitle(t("dlg_connect_port_title"))
        self.setMinimumWidth(480)
        self.setModal(True)
        self._build()

    # ------------------------------------------------------------------
    # UI opbouw
    # ------------------------------------------------------------------

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Bronpoort info (alleen lezen) ────────────────────────────
        grp_src = QGroupBox(t("label_port"))
        src_form = QFormLayout(grp_src)
        src_lbl = QLabel(self._port_label)
        src_lbl.setObjectName("device-label")
        src_form.addRow("", src_lbl)
        layout.addWidget(grp_src)

        # ── Doelpoort kiezen — cascade DDL ───────────────────────────
        grp_target = QGroupBox(t("label_target_port"))
        target_form = QFormLayout(grp_target)
        target_form.setSpacing(8)

        self._ddl_site   = QComboBox()
        self._ddl_room   = QComboBox()
        self._ddl_rack   = QComboBox()
        self._ddl_device = QComboBox()
        self._ddl_port   = QComboBox()

        self._ddl_room.setEnabled(False)
        self._ddl_rack.setEnabled(False)
        self._ddl_device.setEnabled(False)
        self._ddl_port.setEnabled(False)

        # Vul sites
        self._ddl_site.addItem(f"— {t('label_site')} —", "")
        for site in self._data.get("sites", []):
            self._ddl_site.addItem(site["name"], site["id"])

        # Vooraf huidige site selecteren indien beschikbaar
        if self._current_site_id:
            idx = self._ddl_site.findData(self._current_site_id)
            if idx >= 0:
                self._ddl_site.setCurrentIndex(idx)

        self._ddl_site.currentIndexChanged.connect(self._on_site_changed)
        self._ddl_room.currentIndexChanged.connect(self._on_room_changed)
        self._ddl_rack.currentIndexChanged.connect(self._on_rack_changed)
        self._ddl_device.currentIndexChanged.connect(self._on_device_changed)

        target_form.addRow(t("label_site")   + ":", self._ddl_site)
        target_form.addRow(t("label_room")   + ":", self._ddl_room)
        target_form.addRow(t("label_rack")   + ":", self._ddl_rack)
        target_form.addRow(t("label_device") + ":", self._ddl_device)
        target_form.addRow(t("label_target_port") + ":", self._ddl_port)
        layout.addWidget(grp_target)

        # ── Kabeltype ────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        cable_row = QHBoxLayout()
        cable_row.addWidget(QLabel(t("label_cable_type") + ":"))
        self._ddl_cable = QComboBox()
        for val, key in _CABLE_TYPES:
            self._ddl_cable.addItem(t(key), val)
        self._ddl_cable.setCurrentIndex(1)  # standaard UTP Cat6
        cable_row.addWidget(self._ddl_cable)
        cable_row.addStretch()
        layout.addLayout(cable_row)

        # ── Notitie ──────────────────────────────────────────────────
        notes_form = QFormLayout()
        self._notes = QTextEdit()
        self._notes.setFixedHeight(48)
        self._notes.setPlaceholderText(t("label_notes") + "...")
        notes_form.addRow(t("label_notes") + ":", self._notes)
        layout.addLayout(notes_form)

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
        layout.addLayout(btn_row)

        # Initieel vullen als site al geselecteerd is
        if self._current_site_id:
            self._on_site_changed()

    # ------------------------------------------------------------------
    # Cascade handlers
    # ------------------------------------------------------------------

    def _on_site_changed(self):
        site_id = self._ddl_site.currentData()
        self._ddl_room.clear()
        self._ddl_rack.clear()
        self._ddl_device.clear()
        self._ddl_port.clear()
        self._ddl_room.setEnabled(False)
        self._ddl_rack.setEnabled(False)
        self._ddl_device.setEnabled(False)
        self._ddl_port.setEnabled(False)

        if not site_id:
            return
        site = next((s for s in self._data["sites"] if s["id"] == site_id), None)
        if not site:
            return

        self._ddl_room.addItem(f"— {t('label_room')} —", "")
        for room in site.get("rooms", []):
            if room.get("racks"):
                self._ddl_room.addItem(room["name"], room["id"])

        self._ddl_room.setEnabled(True)

        # Vooraf huidige ruimte selecteren
        if self._current_site_id == site_id and self._current_room_id:
            idx = self._ddl_room.findData(self._current_room_id)
            if idx >= 0:
                self._ddl_room.setCurrentIndex(idx)

    def _on_room_changed(self):
        site_id = self._ddl_site.currentData()
        room_id = self._ddl_room.currentData()
        self._ddl_rack.clear()
        self._ddl_device.clear()
        self._ddl_port.clear()
        self._ddl_rack.setEnabled(False)
        self._ddl_device.setEnabled(False)
        self._ddl_port.setEnabled(False)

        if not site_id or not room_id:
            return
        site = next((s for s in self._data["sites"] if s["id"] == site_id), None)
        if not site:
            return
        room = next((r for r in site.get("rooms", []) if r["id"] == room_id), None)
        if not room:
            return

        self._ddl_rack.addItem(f"— {t('label_rack')} —", "")
        for rack in room.get("racks", []):
            self._ddl_rack.addItem(rack["name"], rack["id"])

        self._ddl_rack.setEnabled(True)

        # Vooraf huidige rack selecteren
        if self._current_room_id == room_id and self._current_rack_id:
            idx = self._ddl_rack.findData(self._current_rack_id)
            if idx >= 0:
                self._ddl_rack.setCurrentIndex(idx)

    def _on_rack_changed(self):
        site_id = self._ddl_site.currentData()
        room_id = self._ddl_room.currentData()
        rack_id = self._ddl_rack.currentData()
        self._ddl_device.clear()
        self._ddl_port.clear()
        self._ddl_device.setEnabled(False)
        self._ddl_port.setEnabled(False)

        if not rack_id:
            return

        site = next((s for s in self._data["sites"] if s["id"] == site_id), None)
        if not site:
            return
        room = next((r for r in site.get("rooms", []) if r["id"] == room_id), None)
        if not room:
            return
        rack = next((r for r in room.get("racks", []) if r["id"] == rack_id), None)
        if not rack:
            return

        dev_map = {d["id"]: d for d in self._data.get("devices", [])}

        self._ddl_device.addItem(f"— {t('label_device')} —", "")
        for slot in rack.get("slots", []):
            dev = dev_map.get(slot.get("device_id", ""))
            if not dev:
                continue
            # Brondevice uitsluiten — je kan niet verbinden met jezelf
            if dev["id"] == self._src_device_id:
                continue
            # Alleen devices met poorten tonen
            has_ports = any(
                p for p in self._data.get("ports", [])
                if p.get("device_id") == dev["id"]
            )
            if has_ports:
                dev_type = t(f"device_{dev.get('type', 'other')}")
                self._ddl_device.addItem(
                    f"{dev['name']}  ({dev_type})", dev["id"]
                )

        self._ddl_device.setEnabled(True)

    def _on_device_changed(self):
        device_id = self._ddl_device.currentData()
        self._ddl_port.clear()
        self._ddl_port.setEnabled(False)

        if not device_id:
            return

        # Verbonden poorten ophalen
        connected_ports = set()
        for conn in self._data.get("connections", []):
            if conn.get("from_type") == "port":
                connected_ports.add(conn["from_id"])
            if conn.get("to_type") == "port":
                connected_ports.add(conn["to_id"])

        self._ddl_port.addItem(f"— {t('label_target_port')} —", "")

        ports = [
            p for p in self._data.get("ports", [])
            if p.get("device_id") == device_id
        ]
        # Sorteer: vrije poorten eerst, dan side (front < back), dan nummer
        ports.sort(key=lambda p: (
            p["id"] in connected_ports,
            0 if p.get("side") == "front" else 1,
            p.get("number", 0)
        ))

        for port in ports:
            side_label = t("label_front") if port.get("side") == "front" else t("label_back")
            port_name  = port.get("name", f"Port {port.get('number', '?')}")
            label      = f"{port_name}  ({side_label})"
            is_used    = port["id"] in connected_ports

            if is_used:
                self._ddl_port.addItem(
                    f"⚠  {label}  ({t('err_port_in_use')})", port["id"]
                )
            else:
                self._ddl_port.addItem(label, port["id"])

        self._ddl_port.setEnabled(True)

    # ------------------------------------------------------------------
    # Opslaan
    # ------------------------------------------------------------------

    def _on_save(self):
        target_port_id = self._ddl_port.currentData()
        cable_type     = self._ddl_cable.currentData()

        if not target_port_id:
            QMessageBox.warning(self, t("dlg_connect_port_title"),
                                t("err_no_port_selected"))
            return

        # Waarschuwing als doelpoort al verbonden is
        connected_ports = set()
        for conn in self._data.get("connections", []):
            if conn.get("from_type") == "port":
                connected_ports.add(conn["from_id"])
            if conn.get("to_type") == "port":
                connected_ports.add(conn["to_id"])

        if target_port_id in connected_ports:
            reply = QMessageBox.question(
                self, t("dlg_connect_port_title"),
                t("warn_port_already_connected"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
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
            "to_id":      target_port_id,
            "to_type":    "port",
            "cable_type": cable_type,
            "label":      "",
            "notes":      self._notes.toPlainText().strip(),
        }
        self.accept()

    def get_result(self) -> dict | None:
        return self._result