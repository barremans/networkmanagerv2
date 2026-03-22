# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/device_dialog.py
# Role:    Device aanmaken, bewerken en dupliceren
# Version: 1.4.1
# Author:  Barremans
# Changes: 1.1.0 — Device types geladen uit settings_storage (configureerbaar)
#                  ipv hardcoded lijst
#          1.2.0 — Positie (U-start) en hoogte aanpasbaar bij bewerken
#                  Extra ports_per_row opties: 3, 4
#          1.3.0 — Uppercase invoer: alle tekstvelden automatisch naar hoofdletters
#          1.4.0 — Subnetmasker veld toegevoegd (direct na IP adres)
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QComboBox, QTextEdit,
    QPushButton, QMessageBox, QLabel, QGroupBox
)
from app.helpers.i18n import t
from app.helpers.settings_storage import load_device_types, get_device_type_defaults

# Standaard poortaantallen per device type — fallback als type niet in settings staat
DEVICE_PORT_DEFAULTS = {
    "switch":       {"front": 24, "back": 0},
    "patch_panel":  {"front": 24, "back": 24},
    "patchpanel":   {"front": 24, "back": 24},
    "server":       {"front": 2,  "back": 0},
    "firewall":     {"front": 4,  "back": 0},
    "router":       {"front": 4,  "back": 0},
    "modem":        {"front": 4,  "back": 0},
    "kvm":          {"front": 8,  "back": 0},
    "ups":          {"front": 0,  "back": 0},
    "pdu":          {"front": 0,  "back": 0},
    "media_conv":   {"front": 2,  "back": 0},
    "other":        {"front": 0,  "back": 0},
}


def _load_device_type_list():
    try:
        return load_device_types()
    except Exception:
        return [
            {"key": k, "label_nl": k, "label_en": k,
             "front_ports": DEVICE_PORT_DEFAULTS.get(k, {}).get("front", 0),
             "back_ports":  DEVICE_PORT_DEFAULTS.get(k, {}).get("back",  0)}
            for k in DEVICE_PORT_DEFAULTS
        ]


def _bind_uppercase(line_edit):
    """Koppelt automatische uppercase conversie aan een QLineEdit."""
    def _to_upper(text):
        if text != text.upper():
            cursor = line_edit.cursorPosition()
            line_edit.blockSignals(True)
            line_edit.setText(text.upper())
            line_edit.blockSignals(False)
            line_edit.setCursorPosition(cursor)
    line_edit.textChanged.connect(_to_upper)


class DeviceDialog(QDialog):
    """
    Device aanmaken of bewerken.
    Bij bewerken ook U-positie en hoogte aanpasbaar.
    """

    def __init__(self, parent=None, device: dict = None, duplicate: bool = False,
                 rack: dict = None):
        """
        rack: optioneel — als meegegeven worden U-positie en hoogte getoond.
        """
        super().__init__(parent)
        self._device       = device or {}
        self._duplicate    = duplicate
        self._rack         = rack or {}
        self._result       = None
        self._device_types = _load_device_type_list()

        title = t("label_device")
        if duplicate:
            title += f" — {t('menu_duplicate')}"
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        self.setModal(True)
        self._build()
        if self._device:
            self._populate()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Device sectie ─────────────────────────────────────────────
        grp_dev = QGroupBox(t("label_device"))
        form = QFormLayout(grp_dev)
        form.setSpacing(8)

        self._name = QLineEdit()
        form.addRow(t("label_name") + " *:", self._name)
        _bind_uppercase(self._name)

        self._ddl_type = QComboBox()
        lang = t("_lang") if t("_lang") in ("nl", "en") else "nl"
        for dt in self._device_types:
            label = dt.get(f"label_{lang}", dt.get("label_nl", dt["key"]))
            self._ddl_type.addItem(label, dt["key"])
        self._ddl_type.currentIndexChanged.connect(self._on_type_changed)
        form.addRow(t("label_type") + " *:", self._ddl_type)

        self._front_ports = QSpinBox()
        self._front_ports.setRange(0, 96)
        form.addRow(t("label_front_ports") + ":", self._front_ports)

        self._back_ports = QSpinBox()
        self._back_ports.setRange(0, 96)
        form.addRow(t("label_back_ports") + ":", self._back_ports)

        # Poorten per rij — opties uitgebreid met 3 en 4
        self._ports_per_row = QComboBox()
        self._ports_per_row.addItem("12  (standaard)", 12)
        self._ports_per_row.addItem("24  (1 rij)",     24)
        self._ports_per_row.addItem("3",                3)
        self._ports_per_row.addItem("4",                4)
        self._ports_per_row.addItem("6",                6)
        self._ports_per_row.addItem("8",                8)
        self._ports_per_row.addItem("16",              16)
        form.addRow(t("label_ports_per_row") + ":", self._ports_per_row)

        self._sfp_ports = QSpinBox()
        self._sfp_ports.setRange(0, 32)
        self._sfp_ports.setToolTip("Aantal SFP uplink poorten (laatste X front poorten)")
        form.addRow(t("label_sfp_ports") + ":", self._sfp_ports)

        form.addRow(QLabel(""))

        self._brand  = QLineEdit()
        self._model  = QLineEdit()
        self._ip     = QLineEdit()
        self._subnet = QLineEdit()
        self._subnet.setPlaceholderText("bv. 255.255.255.0  of  /24")
        self._mac    = QLineEdit()
        self._serial = QLineEdit()
        self._notes  = QTextEdit()
        self._notes.setFixedHeight(60)

        for field in (self._brand, self._model,
                      self._ip, self._mac, self._serial):
            _bind_uppercase(field)

        form.addRow(t("label_brand")  + ":", self._brand)
        form.addRow(t("label_model")  + ":", self._model)
        form.addRow(t("label_ip")     + ":", self._ip)
        form.addRow(t("label_subnet") + ":", self._subnet)
        form.addRow(t("label_mac")    + ":", self._mac)
        form.addRow(t("label_serial") + ":", self._serial)
        form.addRow(t("label_notes")  + ":", self._notes)
        layout.addWidget(grp_dev)

        # ── Rack positie sectie — alleen bij bewerken met rack context ─
        self._grp_slot = None
        self._u_start  = None
        self._height   = None

        if self._rack and self._device:
            total_u = self._rack.get("total_units", 42)
            self._grp_slot = QGroupBox(
                f"{t('label_rack')} — {self._rack.get('name', '')}"
            )
            slot_form = QFormLayout(self._grp_slot)
            slot_form.setSpacing(8)

            self._u_start = QSpinBox()
            self._u_start.setRange(1, total_u)

            self._height = QSpinBox()
            self._height.setRange(1, total_u)

            slot_form.addRow(t("label_u_start") + ":", self._u_start)
            slot_form.addRow(t("label_units")   + ":", self._height)
            layout.addWidget(self._grp_slot)

        # ── Knoppen ───────────────────────────────────────────────────
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

    def _on_type_changed(self):
        dev_type = self._ddl_type.currentData()
        for dt in self._device_types:
            if dt["key"] == dev_type:
                self._front_ports.setValue(dt.get("front_ports", 0))
                self._back_ports.setValue(dt.get("back_ports",  0))
                self._sfp_ports.setValue(dt.get("sfp_ports", 0))
                return
        defaults = DEVICE_PORT_DEFAULTS.get(dev_type, {"front": 0, "back": 0})
        self._front_ports.setValue(defaults["front"])
        self._back_ports.setValue(defaults["back"])
        self._sfp_ports.setValue(0)

    def _populate(self):
        name = self._device.get("name", "")
        if self._duplicate:
            name += " (kopie)"
        self._name.setText(name)

        dev_type = self._device.get("type", "")
        idx = self._ddl_type.findData(dev_type)
        if idx >= 0:
            self._ddl_type.blockSignals(True)
            self._ddl_type.setCurrentIndex(idx)
            self._ddl_type.blockSignals(False)

        self._front_ports.setValue(self._device.get("front_ports", 0))
        self._back_ports.setValue(self._device.get("back_ports", 0))
        self._sfp_ports.setValue(self._device.get("sfp_ports", 0))

        ppr = self._device.get("ports_per_row", 12)
        idx = self._ports_per_row.findData(ppr)
        if idx >= 0:
            self._ports_per_row.setCurrentIndex(idx)

        self._brand.setText(self._device.get("brand", ""))
        self._model.setText(self._device.get("model", ""))

        if not self._duplicate:
            self._ip.setText(self._device.get("ip", ""))
            self._subnet.setText(self._device.get("subnet", ""))
            self._mac.setText(self._device.get("mac", ""))
            self._serial.setText(self._device.get("serial", ""))

        self._notes.setPlainText(self._device.get("notes", ""))

        # U-positie + hoogte invullen vanuit slot
        if self._u_start and self._height and self._rack:
            slot = self._find_slot()
            if slot:
                u_raw  = slot.get("u_start", 1)
                height = slot.get("height", 1)
                # Omzetten naar display waarde
                numbering = self._rack.get("numbering", "top_down")
                total_u   = self._rack.get("total_units", 42)
                if numbering == "bottom_up":
                    display_u = total_u - u_raw + 1
                else:
                    display_u = u_raw
                self._u_start.setValue(display_u)
                self._height.setValue(height)

    def _find_slot(self) -> dict | None:
        """Zoek het slot van dit device in de rack."""
        dev_id = self._device.get("id", "")
        for slot in self._rack.get("slots", []):
            if slot.get("device_id") == dev_id:
                return slot
        return None

    def _on_save(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, t("label_device"), t("label_name") + " is verplicht.")
            return

        self._result = {
            "id":          self._device.get("id", "") if not self._duplicate else "",
            "name":        name,
            "type":        self._ddl_type.currentData(),
            "front_ports": self._front_ports.value(),
            "back_ports":  self._back_ports.value(),
            "brand":       self._brand.text().strip(),
            "model":       self._model.text().strip(),
            "ip":          self._ip.text().strip(),
            "subnet":      self._subnet.text().strip(),
            "mac":         self._mac.text().strip(),
            "serial":      self._serial.text().strip(),
            "notes":         self._notes.toPlainText().strip(),
            "ports_per_row": self._ports_per_row.currentData(),
            "sfp_ports":     self._sfp_ports.value(),
        }

        # Slot update bij bewerken
        if self._u_start and self._height and self._rack:
            display_u = self._u_start.value()
            height    = self._height.value()
            total_u   = self._rack.get("total_units", 42)
            numbering = self._rack.get("numbering", "top_down")

            if numbering == "bottom_up":
                u_internal = total_u - display_u + 1
                u_top      = u_internal - height + 1
                if u_top < 1 or u_internal > total_u:
                    QMessageBox.warning(self, t("label_device"),
                                        f"Device past niet in rack "
                                        f"(U{display_u}+{height}U > {total_u}U).")
                    return
                u_start = u_top
            else:
                u_start = display_u
                if u_start + height - 1 > total_u:
                    QMessageBox.warning(self, t("label_device"),
                                        f"Device past niet in rack "
                                        f"(U{display_u}+{height}U > {total_u}U).")
                    return

            self._result["_slot_update"] = {
                "u_start": u_start,
                "height":  height,
            }

        self.accept()

    def get_result(self) -> dict | None:
        return self._result