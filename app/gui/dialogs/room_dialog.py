# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/room_dialog.py
# Role:    Ruimte aanmaken en bewerken
# Version: 1.0.0
# Author:  Barremans
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QMessageBox
)
from app.helpers.i18n import t


class RoomDialog(QDialog):
    def __init__(self, parent=None, room: dict = None, site_id: str = ""):
        super().__init__(parent)
        self._room    = room or {}
        self._site_id = site_id
        self._result  = None
        self.setWindowTitle(t("label_room"))
        self.setMinimumWidth(380)
        self.setModal(True)
        self._build()
        if self._room:
            self._populate()

    def _build(self):
        layout = QVBoxLayout(self)
        form   = QFormLayout()
        form.setSpacing(8)

        self._name  = QLineEdit()
        self._floor = QLineEdit()
        self._notes = QTextEdit()
        self._notes.setFixedHeight(60)

        form.addRow(t("label_name")  + " *:", self._name)
        form.addRow(t("label_floor") + ":",   self._floor)
        form.addRow(t("label_notes") + ":",   self._notes)
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
        self._name.setText(self._room.get("name", ""))
        self._floor.setText(self._room.get("floor", ""))
        self._notes.setPlainText(self._room.get("notes", ""))

    def _on_save(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, t("label_room"), t("label_name") + " is verplicht.")
            return
        self._result = {
            "id":           self._room.get("id", ""),
            "site_id":      self._site_id or self._room.get("site_id", ""),
            "name":         name,
            "floor":        self._floor.text().strip(),
            "notes":        self._notes.toPlainText().strip(),
            "racks":        self._room.get("racks", []),
            "wall_outlets": self._room.get("wall_outlets", []),
        }
        self.accept()

    def get_result(self) -> dict | None:
        return self._result