# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/site_dialog.py
# Role:    Site aanmaken en bewerken
# Version: 1.0.0
# Author:  Barremans
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QMessageBox
)
from app.helpers.i18n import t


class SiteDialog(QDialog):
    def __init__(self, parent=None, site: dict = None):
        super().__init__(parent)
        self._site   = site or {}
        self._result = None
        self.setWindowTitle(t("label_site"))
        self.setMinimumWidth(380)
        self.setModal(True)
        self._build()
        if self._site:
            self._populate()

    def _build(self):
        layout = QVBoxLayout(self)
        form   = QFormLayout()
        form.setSpacing(8)

        self._name     = QLineEdit()
        self._location = QLineEdit()
        self._notes    = QTextEdit()
        self._notes.setFixedHeight(60)

        form.addRow(t("label_name")     + " *:", self._name)
        form.addRow(t("label_location") + ":",   self._location)
        form.addRow(t("label_notes")    + ":",   self._notes)
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
        self._name.setText(self._site.get("name", ""))
        self._location.setText(self._site.get("location", ""))
        self._notes.setPlainText(self._site.get("notes", ""))

    def _on_save(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, t("label_site"), t("label_name") + " is verplicht.")
            return
        self._result = {
            "id":       self._site.get("id", ""),
            "name":     name,
            "location": self._location.text().strip(),
            "notes":    self._notes.toPlainText().strip(),
            "rooms":    self._site.get("rooms", []),
        }
        self.accept()

    def get_result(self) -> dict | None:
        return self._result