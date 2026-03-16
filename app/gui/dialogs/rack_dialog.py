# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/rack_dialog.py
# Role:    Rack aanmaken en bewerken
# Version: 1.2.0
# Author:  Barremans
# Changes: 1.1.0 — Keuze nummering: 1 bovenaan of 1 onderaan (professioneel)
#          1.2.0 — Uppercase invoer: naam automatisch naar hoofdletters
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QTextEdit, QPushButton,
    QMessageBox, QComboBox
)
from app.helpers.i18n import t
from app.gui.dialogs.device_dialog import _bind_uppercase


class RackDialog(QDialog):
    def __init__(self, parent=None, rack: dict = None, room_id: str = ""):
        super().__init__(parent)
        self._rack    = rack or {}
        self._room_id = room_id
        self._result  = None
        self.setWindowTitle(t("label_rack"))
        self.setMinimumWidth(380)
        self.setModal(True)
        self._build()
        if self._rack:
            self._populate()

    def _build(self):
        layout = QVBoxLayout(self)
        form   = QFormLayout()
        form.setSpacing(8)

        self._name  = QLineEdit()
        _bind_uppercase(self._name)

        self._units = QSpinBox()
        self._units.setRange(1, 48)
        self._units.setValue(12)

        # Nummering keuze — 1.1.0
        self._numbering = QComboBox()
        self._numbering.addItem(t("rack_numbering_top_down"), "top_down")
        self._numbering.addItem(t("rack_numbering_bottom_up"), "bottom_up")

        self._notes = QTextEdit()
        self._notes.setFixedHeight(60)

        form.addRow(t("label_name")           + " *:", self._name)
        form.addRow(t("label_units")          + ":",   self._units)
        form.addRow(t("rack_numbering_label") + ":",   self._numbering)
        form.addRow(t("label_notes")          + ":",   self._notes)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_save   = QPushButton(t("btn_save"))
        btn_cancel = QPushButton(t("btn_cancel"))
        btn_save.clicked.connect(self._on_save)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def _populate(self):
        self._name.setText(self._rack.get("name", ""))
        self._units.setValue(self._rack.get("total_units", 12))
        self._notes.setPlainText(self._rack.get("notes", ""))
        # Nummering instellen
        numbering = self._rack.get("numbering", "top_down")
        idx = self._numbering.findData(numbering)
        if idx >= 0:
            self._numbering.setCurrentIndex(idx)

    def _on_save(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, t("label_rack"), t("label_name") + " is verplicht.")
            return
        self._result = {
            "id":          self._rack.get("id", ""),
            "room_id":     self._room_id or self._rack.get("room_id", ""),
            "name":        name,
            "total_units": self._units.value(),
            "numbering":   self._numbering.currentData(),   # "top_down" | "bottom_up"
            "notes":       self._notes.toPlainText().strip(),
            "slots":       self._rack.get("slots", []),
        }
        self.accept()

    def get_result(self) -> dict | None:
        return self._result