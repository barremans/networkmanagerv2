# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/endpoint_dialog.py
# Role:    Endpoint aanmaken en bewerken
# Version: 1.2.0
# Author:  Barremans
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QTextEdit, QPushButton, QMessageBox
)
from app.helpers.i18n import t, get_language
from app.helpers import settings_storage


class EndpointDialog(QDialog):
    def __init__(self, parent=None, endpoint: dict = None):
        super().__init__(parent)
        self._endpoint = endpoint or {}
        self._result   = None
        self.setWindowTitle(
            t("title_edit_endpoint") if self._endpoint else t("title_new_endpoint")
        )
        self.setMinimumWidth(380)
        self.setModal(True)
        self._build()
        if self._endpoint:
            self._populate()

    def _build(self):
        layout = QVBoxLayout(self)
        form   = QFormLayout()
        form.setSpacing(8)

        self._name     = QLineEdit()
        self._ddl_type = QComboBox()

        # Types laden uit settings — configureerbaar via Instellingen > Eindapparaten
        lang = get_language()
        for et in settings_storage.load_endpoint_types():
            key   = et.get("key", "")
            label = et.get(f"label_{lang}", et.get("label_nl", key))
            self._ddl_type.addItem(label, key)

        self._ip    = QLineEdit()
        self._mac   = QLineEdit()
        self._brand = QLineEdit()
        self._model = QLineEdit()
        self._notes = QTextEdit()
        self._notes.setFixedHeight(60)

        form.addRow(t("label_name")  + " *:", self._name)
        form.addRow(t("label_type")  + ":",   self._ddl_type)
        form.addRow(t("label_ip")    + ":",   self._ip)
        form.addRow(t("label_mac")   + ":",   self._mac)
        form.addRow(t("label_brand") + ":",   self._brand)
        form.addRow(t("label_model") + ":",   self._model)
        form.addRow(t("label_notes") + ":",   self._notes)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_save   = QPushButton(t("btn_save"))
        btn_cancel = QPushButton(t("btn_cancel"))
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._on_save)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def _populate(self):
        self._name.setText(self._endpoint.get("name", ""))
        key = self._endpoint.get("type", "")
        idx = self._ddl_type.findData(key)
        if idx >= 0:
            self._ddl_type.setCurrentIndex(idx)
        self._ip.setText(self._endpoint.get("ip", ""))
        self._mac.setText(self._endpoint.get("mac", ""))
        self._brand.setText(self._endpoint.get("brand", ""))
        self._model.setText(self._endpoint.get("model", ""))
        self._notes.setPlainText(self._endpoint.get("notes", ""))

    def _on_save(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, t("label_endpoint"), t("err_field_required"))
            return
        self._result = {
            "id":    self._endpoint.get("id", ""),
            "name":  name,
            "type":  self._ddl_type.currentData() or "",
            "ip":    self._ip.text().strip(),
            "mac":   self._mac.text().strip(),
            "brand": self._brand.text().strip(),
            "model": self._model.text().strip(),
            "notes": self._notes.toPlainText().strip(),
        }
        self.accept()

    def get_result(self) -> dict | None:
        return self._result