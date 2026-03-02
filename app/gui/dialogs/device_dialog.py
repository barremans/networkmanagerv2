# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/device_dialog.py
# Role:    Device aanmaken, bewerken en dupliceren
# Version: 1.0.0
# Author:  Barremans
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QComboBox, QTextEdit,
    QPushButton, QMessageBox, QLabel
)
from app.helpers.i18n import t

# Standaard poortaantallen per device type (handboek sectie 7)
DEVICE_PORT_DEFAULTS = {
    "switch":     {"front": 24, "back": 0},
    "patchpanel": {"front": 24, "back": 24},
    "server":     {"front": 2,  "back": 0},
    "firewall":   {"front": 4,  "back": 0},
    "modem":      {"front": 4,  "back": 0},
    "ups":        {"front": 0,  "back": 0},
}

_DEVICE_TYPES = [
    "switch", "patchpanel", "server", "firewall", "modem", "ups"
]


class DeviceDialog(QDialog):
    """
    Device aanmaken of bewerken.
    Type kiezen via DDL → FRONT/BACK automatisch ingevuld.
    Gebruiker kan FRONT/BACK altijd manueel aanpassen.
    """

    def __init__(self, parent=None, device: dict = None, duplicate: bool = False):
        super().__init__(parent)
        self._device    = device or {}
        self._duplicate = duplicate
        self._result    = None

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
        form = QFormLayout()
        form.setSpacing(8)

        # Naam
        self._name = QLineEdit()
        form.addRow(t("label_name") + " *:", self._name)

        # Type DDL
        self._ddl_type = QComboBox()
        for dt in _DEVICE_TYPES:
            self._ddl_type.addItem(t(f"device_{dt}"), dt)
        self._ddl_type.currentIndexChanged.connect(self._on_type_changed)
        form.addRow(t("label_type") + " *:", self._ddl_type)

        # FRONT poorten
        self._front_ports = QSpinBox()
        self._front_ports.setRange(0, 96)
        form.addRow(t("label_front_ports") + ":", self._front_ports)

        # BACK poorten
        self._back_ports = QSpinBox()
        self._back_ports.setRange(0, 96)
        form.addRow(t("label_back_ports") + ":", self._back_ports)

        form.addRow(QLabel(""))   # lege rij als separator

        # Optionele velden
        self._brand  = QLineEdit()
        self._model  = QLineEdit()
        self._ip     = QLineEdit()
        self._mac    = QLineEdit()
        self._serial = QLineEdit()
        self._notes  = QTextEdit()
        self._notes.setFixedHeight(60)

        form.addRow(t("label_brand")  + ":", self._brand)
        form.addRow(t("label_model")  + ":", self._model)
        form.addRow(t("label_ip")     + ":", self._ip)
        form.addRow(t("label_mac")    + ":", self._mac)
        form.addRow(t("label_serial") + ":", self._serial)
        form.addRow(t("label_notes")  + ":", self._notes)

        layout.addLayout(form)

        # Knoppen
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_save   = QPushButton(t("btn_save"))
        btn_cancel = QPushButton(t("btn_cancel"))
        btn_save.clicked.connect(self._on_save)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

        # Standaard waarden voor eerste type instellen
        self._on_type_changed()

    def _on_type_changed(self):
        """Vult FRONT/BACK automatisch in op basis van gekozen type."""
        dev_type = self._ddl_type.currentData()
        defaults = DEVICE_PORT_DEFAULTS.get(dev_type, {"front": 0, "back": 0})
        self._front_ports.setValue(defaults["front"])
        self._back_ports.setValue(defaults["back"])

    def _populate(self):
        """Vult formulier in met bestaande device data."""
        name = self._device.get("name", "")
        if self._duplicate:
            name += " (kopie)"
        self._name.setText(name)

        dev_type = self._device.get("type", "switch")
        idx = self._ddl_type.findData(dev_type)
        if idx >= 0:
            self._ddl_type.blockSignals(True)
            self._ddl_type.setCurrentIndex(idx)
            self._ddl_type.blockSignals(False)

        self._front_ports.setValue(self._device.get("front_ports", 0))
        self._back_ports.setValue(self._device.get("back_ports", 0))
        self._brand.setText(self._device.get("brand", ""))
        self._model.setText(self._device.get("model", ""))

        # Bij dupliceren: IP, MAC en serial leeg laten (unieke velden)
        if not self._duplicate:
            self._ip.setText(self._device.get("ip", ""))
            self._mac.setText(self._device.get("mac", ""))
            self._serial.setText(self._device.get("serial", ""))

        self._notes.setPlainText(self._device.get("notes", ""))

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
            "mac":         self._mac.text().strip(),
            "serial":      self._serial.text().strip(),
            "notes":       self._notes.toPlainText().strip(),
        }
        self.accept()

    def get_result(self) -> dict | None:
        return self._result