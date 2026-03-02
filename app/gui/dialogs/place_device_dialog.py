# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/place_device_dialog.py
# Role:    Device aanmaken + plaatsen in rack (U-positie kiezen)
# Version: 1.0.0
# Author:  Barremans
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QComboBox, QTextEdit,
    QPushButton, QGroupBox, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
from app.helpers.i18n import t
from app.gui.dialogs.device_dialog import DEVICE_PORT_DEFAULTS, _DEVICE_TYPES


class PlaceDeviceDialog(QDialog):
    """
    Combineert device aanmaken + U-positie kiezen in één venster.

    Toont een visuele U-kaart van de rack zodat de gebruiker
    een vrij slot kan kiezen.

    Resultaat via get_result():
      {
        "device": { ...device velden... },
        "slot": { "u_start": int, "height": int }
      }
    """

    def __init__(self, parent=None, rack: dict = None, data: dict = None):
        super().__init__(parent)
        self._rack   = rack or {}
        self._data   = data or {}
        self._result = None

        self.setWindowTitle(f"{t('label_device')} — {rack.get('name', '')} toevoegen")
        self.setMinimumWidth(480)
        self.setModal(True)
        self._build()

    # ------------------------------------------------------------------
    # Opbouw
    # ------------------------------------------------------------------

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Device velden ────────────────────────────────────────────
        grp_dev = QGroupBox(t("label_device"))
        form    = QFormLayout(grp_dev)
        form.setSpacing(6)

        self._name = QLineEdit()
        self._ddl_type = QComboBox()
        for dt in _DEVICE_TYPES:
            self._ddl_type.addItem(t(f"device_{dt}"), dt)
        self._ddl_type.currentIndexChanged.connect(self._on_type_changed)

        self._front_ports = QSpinBox()
        self._front_ports.setRange(0, 96)
        self._back_ports  = QSpinBox()
        self._back_ports.setRange(0, 96)
        self._brand  = QLineEdit()
        self._model  = QLineEdit()
        self._ip     = QLineEdit()
        self._notes  = QTextEdit()
        self._notes.setFixedHeight(48)

        form.addRow(t("label_name")        + " *:", self._name)
        form.addRow(t("label_type")        + " *:", self._ddl_type)
        form.addRow(t("label_front_ports") + ":",   self._front_ports)
        form.addRow(t("label_back_ports")  + ":",   self._back_ports)
        form.addRow(t("label_brand")       + ":",   self._brand)
        form.addRow(t("label_model")       + ":",   self._model)
        form.addRow(t("label_ip")          + ":",   self._ip)
        form.addRow(t("label_notes")       + ":",   self._notes)
        layout.addWidget(grp_dev)

        # ── Rack plaatsing ───────────────────────────────────────────
        grp_slot = QGroupBox(f"{t('label_rack')} — {self._rack.get('name', '')}")
        slot_form = QFormLayout(grp_slot)
        slot_form.setSpacing(6)

        total_u = self._rack.get("total_units", 12)

        self._u_start = QSpinBox()
        self._u_start.setRange(1, total_u)
        self._u_start.setValue(self._next_free_u())

        self._height = QSpinBox()
        self._height.setRange(1, total_u)
        self._height.setValue(1)

        # Bezette U-posities tonen
        occupied = self._occupied_units()
        if occupied:
            occ_str = ", ".join(str(u) for u in sorted(occupied))
            occ_lbl = QLabel(f"Bezet: U{occ_str}")
            occ_lbl.setObjectName("secondary")
            slot_form.addRow("", occ_lbl)

        slot_form.addRow("U-positie *:", self._u_start)
        slot_form.addRow(t("label_units") + ":", self._height)
        layout.addWidget(grp_slot)

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

        # Standaard poortwaarden instellen
        self._on_type_changed()

    # ------------------------------------------------------------------
    # Type DDL handler
    # ------------------------------------------------------------------

    def _on_type_changed(self):
        dev_type = self._ddl_type.currentData()
        defaults = DEVICE_PORT_DEFAULTS.get(dev_type, {"front": 0, "back": 0})
        self._front_ports.setValue(defaults["front"])
        self._back_ports.setValue(defaults["back"])

    # ------------------------------------------------------------------
    # Opslaan
    # ------------------------------------------------------------------

    def _on_save(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, t("label_device"),
                                t("label_name") + " is verplicht.")
            return

        u_start = self._u_start.value()
        height  = self._height.value()
        total_u = self._rack.get("total_units", 12)

        # Past het device in de rack?
        if u_start + height - 1 > total_u:
            QMessageBox.warning(self, t("label_device"),
                                f"Device past niet in rack "
                                f"(U{u_start}+{height}U > {total_u}U).")
            return

        # Conflict check
        occupied = self._occupied_units()
        needed   = set(range(u_start, u_start + height))
        conflict = needed & occupied
        if conflict:
            QMessageBox.warning(self, t("label_device"),
                                f"U-positie(s) al bezet: "
                                f"{', '.join('U'+str(u) for u in sorted(conflict))}")
            return

        self._result = {
            "device": {
                "id":          "",   # wordt ingevuld door main_window
                "name":        name,
                "type":        self._ddl_type.currentData(),
                "front_ports": self._front_ports.value(),
                "back_ports":  self._back_ports.value(),
                "brand":       self._brand.text().strip(),
                "model":       self._model.text().strip(),
                "ip":          self._ip.text().strip(),
                "mac":         "",
                "serial":      "",
                "notes":       self._notes.toPlainText().strip(),
            },
            "slot": {
                "id":       "",   # wordt ingevuld door main_window
                "u_start":  u_start,
                "height":   height,
            }
        }
        self.accept()

    # ------------------------------------------------------------------
    # Resultaat
    # ------------------------------------------------------------------

    def get_result(self) -> dict | None:
        return self._result

    # ------------------------------------------------------------------
    # Hulpfuncties
    # ------------------------------------------------------------------

    def _occupied_units(self) -> set:
        """Geeft set van bezette U-posities in dit rack."""
        occupied = set()
        dev_map  = {d["id"]: d for d in self._data.get("devices", [])}
        for slot in self._rack.get("slots", []):
            dev    = dev_map.get(slot.get("device_id", ""))
            height = slot.get("height", 1)
            u      = slot.get("u_start", 1)
            for i in range(height):
                occupied.add(u + i)
        return occupied

    def _next_free_u(self) -> int:
        """Geeft de eerste vrije U-positie terug."""
        occupied = self._occupied_units()
        total_u  = self._rack.get("total_units", 12)
        for u in range(1, total_u + 1):
            if u not in occupied:
                return u
        return 1