# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/place_device_dialog.py
# Role:    Device aanmaken + plaatsen in rack (U-positie kiezen)
# Version: 1.7.0
# Author:  Barremans
# Changes: 1.1.0 — Device types geladen uit settings_storage (configureerbaar)
#                  ipv import van hardcoded _DEVICE_TYPES uit device_dialog
#          1.2.0 — Fix: U-positie omzetting voor bottom_up nummering
#          1.3.0 — Poorten per rij keuze voor alle device types
#          1.4.0 — SFP poorten veld
#          1.5.0 — S/N en MAC velden toegevoegd (pariteit met device_dialog)
#          1.6.0 — Fix: grenzenvalidatie bij bottom_up nummering
#                  (u_start > total_u ipv u_start + height - 1 > total_u)
#          1.7.0 — Extra ports_per_row opties: 3 en 4
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QComboBox, QTextEdit,
    QPushButton, QGroupBox, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
from app.helpers.i18n import t
from app.helpers.settings_storage import load_device_types
from app.gui.dialogs.device_dialog import DEVICE_PORT_DEFAULTS


class PlaceDeviceDialog(QDialog):
    """
    Combineert device aanmaken + U-positie kiezen in één venster.
    Device types worden geladen uit settings_storage — volledig configureerbaar.
    """

    def __init__(self, parent=None, rack: dict = None, data: dict = None):
        super().__init__(parent)
        self._rack         = rack or {}
        self._data         = data or {}
        self._result       = None
        self._device_types = self._load_types()

        self.setWindowTitle(f"{t('label_device')} — {rack.get('name', '')} toevoegen")
        self.setMinimumWidth(480)
        self.setModal(True)
        self._build()

    def _load_types(self) -> list:
        try:
            return load_device_types()
        except Exception:
            return []

    def _display_to_internal(self, display_u: int) -> int:
        numbering = self._rack.get("numbering", "top_down")
        if numbering == "bottom_up":
            total_u = self._rack.get("total_units", 12)
            return total_u - display_u + 1
        return display_u

    def _internal_to_display(self, internal_u: int) -> int:
        numbering = self._rack.get("numbering", "top_down")
        if numbering == "bottom_up":
            total_u = self._rack.get("total_units", 12)
            return total_u - internal_u + 1
        return internal_u

    # ------------------------------------------------------------------
    # Opbouw
    # ------------------------------------------------------------------

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        grp_dev = QGroupBox(t("label_device"))
        form    = QFormLayout(grp_dev)
        form.setSpacing(6)

        self._name = QLineEdit()

        self._ddl_type = QComboBox()
        lang = "nl"
        for dt in self._device_types:
            label = dt.get(f"label_{lang}", dt.get("label_nl", dt["key"]))
            self._ddl_type.addItem(label, dt["key"])
        self._ddl_type.currentIndexChanged.connect(self._on_type_changed)

        self._front_ports = QSpinBox()
        self._front_ports.setRange(0, 96)
        self._back_ports  = QSpinBox()
        self._back_ports.setRange(0, 96)

        # Poorten per rij — uitgebreid met 3 en 4
        self._ports_per_row = QComboBox()
        self._ports_per_row.addItem("12  (standaard)", 12)
        self._ports_per_row.addItem("24  (1 rij)",     24)
        self._ports_per_row.addItem("3",                3)
        self._ports_per_row.addItem("4",                4)
        self._ports_per_row.addItem("6",                6)
        self._ports_per_row.addItem("8",                8)
        self._ports_per_row.addItem("16",              16)

        self._sfp_ports = QSpinBox()
        self._sfp_ports.setRange(0, 32)
        self._sfp_ports.setToolTip("Aantal SFP uplink poorten (laatste X front poorten)")

        self._brand  = QLineEdit()
        self._model  = QLineEdit()
        self._ip     = QLineEdit()
        self._mac    = QLineEdit()
        self._serial = QLineEdit()
        self._notes  = QTextEdit()
        self._notes.setFixedHeight(48)

        form.addRow(t("label_name")          + " *:", self._name)
        form.addRow(t("label_type")          + " *:", self._ddl_type)
        form.addRow(t("label_front_ports")   + ":",   self._front_ports)
        form.addRow(t("label_back_ports")    + ":",   self._back_ports)
        form.addRow(t("label_sfp_ports")     + ":",   self._sfp_ports)
        form.addRow(t("label_ports_per_row") + ":",   self._ports_per_row)
        form.addRow(t("label_brand")         + ":",   self._brand)
        form.addRow(t("label_model")         + ":",   self._model)
        form.addRow(t("label_ip")            + ":",   self._ip)
        form.addRow(t("label_mac")           + ":",   self._mac)
        form.addRow(t("label_serial")        + ":",   self._serial)
        form.addRow(t("label_notes")         + ":",   self._notes)
        layout.addWidget(grp_dev)

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

        occupied = self._occupied_units()
        if occupied:
            occ_str = ", ".join(str(u) for u in sorted(occupied))
            occ_lbl = QLabel(f"Bezet: U{occ_str}")
            occ_lbl.setObjectName("secondary")
            slot_form.addRow("", occ_lbl)

        slot_form.addRow("U-positie *:", self._u_start)
        slot_form.addRow(t("label_units") + ":", self._height)
        layout.addWidget(grp_slot)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_save   = QPushButton(t("btn_save"))
        btn_cancel = QPushButton(t("btn_cancel"))
        btn_save.clicked.connect(self._on_save)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

        self._on_type_changed()

    # ------------------------------------------------------------------
    # Type DDL handler
    # ------------------------------------------------------------------

    def _on_type_changed(self):
        dev_type = self._ddl_type.currentData()
        front, back, sfp = 0, 0, 0
        for dt in self._device_types:
            if dt["key"] == dev_type:
                front = dt.get("front_ports", 0)
                back  = dt.get("back_ports",  0)
                sfp   = dt.get("sfp_ports",   0)
                break
        else:
            defaults = DEVICE_PORT_DEFAULTS.get(dev_type, {"front": 0, "back": 0})
            front = defaults["front"]
            back  = defaults["back"]
        self._front_ports.setValue(front)
        self._back_ports.setValue(back)
        self._sfp_ports.setValue(sfp)
        total = max(front, back)
        default_ppr = 24 if total > 12 else 12
        idx = self._ports_per_row.findData(default_ppr)
        if idx >= 0:
            self._ports_per_row.setCurrentIndex(idx)

    # ------------------------------------------------------------------
    # Opslaan
    # ------------------------------------------------------------------

    def _on_save(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, t("label_device"),
                                t("label_name") + " is verplicht.")
            return

        display_u = self._u_start.value()
        height    = self._height.value()
        total_u   = self._rack.get("total_units", 12)
        numbering = self._rack.get("numbering", "top_down")

        u_start = self._display_to_internal(display_u)

        if numbering == "bottom_up":
            u_top = u_start - height + 1
        else:
            u_top = u_start

        if u_top < 1 or u_start > total_u:
            QMessageBox.warning(self, t("label_device"),
                                f"Device past niet in rack "
                                f"(U{display_u}+{height}U > {total_u}U).")
            return

        if numbering == "bottom_up":
            u_start = u_top

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
                "id":            "",
                "name":          name,
                "type":          self._ddl_type.currentData(),
                "front_ports":   self._front_ports.value(),
                "back_ports":    self._back_ports.value(),
                "brand":         self._brand.text().strip(),
                "model":         self._model.text().strip(),
                "ip":            self._ip.text().strip(),
                "mac":           self._mac.text().strip(),
                "serial":        self._serial.text().strip(),
                "notes":         self._notes.toPlainText().strip(),
                "ports_per_row": self._ports_per_row.currentData(),
                "sfp_ports":     self._sfp_ports.value(),
            },
            "slot": {
                "id":      "",
                "u_start": u_start,
                "height":  height,
            }
        }
        self.accept()

    def get_result(self) -> dict | None:
        return self._result

    def _occupied_units(self) -> set:
        occupied = set()
        for slot in self._rack.get("slots", []):
            height = slot.get("height", 1)
            u      = slot.get("u_start", 1)
            for i in range(height):
                occupied.add(u + i)
        return occupied

    def _next_free_u(self) -> int:
        occupied  = self._occupied_units()
        total_u   = self._rack.get("total_units", 12)
        numbering = self._rack.get("numbering", "top_down")
        if numbering == "bottom_up":
            for u in range(total_u, 0, -1):
                if u not in occupied:
                    return self._internal_to_display(u)
        else:
            for u in range(1, total_u + 1):
                if u not in occupied:
                    return u
        return 1