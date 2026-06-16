# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/company_dialog.py
# Role:    CRUD-dialoog voor bedrijfsgegevens (F1/F2)
#          Aanmaken en bewerken van een company (naam, adres, BTW, tel, mail, website)
# Version: 1.0.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie (F1/F2)
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLineEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt

from app.helpers.i18n import t


class CompanyDialog(QDialog):
    """
    Dialoog voor het aanmaken of bewerken van een bedrijf.

    Gebruik (nieuw):
        dlg = CompanyDialog(parent=self)
        if dlg.exec() and dlg.get_result():
            company = dlg.get_result()
            company["id"] = self._gen_id("company")
            ...

    Gebruik (bewerken):
        dlg = CompanyDialog(parent=self, company=existing_company)
        if dlg.exec() and dlg.get_result():
            updated = dlg.get_result()
            ...
    """

    def __init__(self, parent=None, company: dict | None = None):
        super().__init__(parent)
        self._company = company or {}
        self._result: dict | None = None

        title_key = "dlg_company_edit_title" if company else "dlg_company_new_title"
        self.setWindowTitle(t(title_key))
        self.setMinimumWidth(420)
        self.setModal(True)
        self._build()
        self._populate()

    # ------------------------------------------------------------------
    # UI opbouw
    # ------------------------------------------------------------------

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Verplichte velden
        grp_main = QGroupBox(t("dlg_company_grp_info"))
        form_main = QFormLayout(grp_main)
        form_main.setLabelAlignment(Qt.AlignRight)
        form_main.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self._fld_name    = QLineEdit()
        self._fld_name.setPlaceholderText(t("dlg_company_ph_name"))
        self._fld_name.setMaxLength(120)
        form_main.addRow(t("dlg_company_lbl_name") + " *", self._fld_name)

        self._fld_address = QLineEdit()
        self._fld_address.setPlaceholderText(t("dlg_company_ph_address"))
        self._fld_address.setMaxLength(200)
        form_main.addRow(t("dlg_company_lbl_address"), self._fld_address)

        layout.addWidget(grp_main)

        # Contactgegevens
        grp_contact = QGroupBox(t("dlg_company_grp_contact"))
        form_contact = QFormLayout(grp_contact)
        form_contact.setLabelAlignment(Qt.AlignRight)
        form_contact.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self._fld_vat     = QLineEdit()
        self._fld_vat.setPlaceholderText(t("dlg_company_ph_vat"))
        self._fld_vat.setMaxLength(30)
        form_contact.addRow(t("dlg_company_lbl_vat"), self._fld_vat)

        self._fld_phone   = QLineEdit()
        self._fld_phone.setPlaceholderText(t("dlg_company_ph_phone"))
        self._fld_phone.setMaxLength(40)
        form_contact.addRow(t("dlg_company_lbl_phone"), self._fld_phone)

        self._fld_email   = QLineEdit()
        self._fld_email.setPlaceholderText(t("dlg_company_ph_email"))
        self._fld_email.setMaxLength(120)
        form_contact.addRow(t("dlg_company_lbl_email"), self._fld_email)

        self._fld_website = QLineEdit()
        self._fld_website.setPlaceholderText(t("dlg_company_ph_website"))
        self._fld_website.setMaxLength(120)
        form_contact.addRow(t("dlg_company_lbl_website"), self._fld_website)

        layout.addWidget(grp_contact)

        # Knoppen
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

    def _populate(self):
        """Vul velden in bij bewerken van een bestaande company."""
        if not self._company:
            return
        self._fld_name.setText(self._company.get("name", ""))
        self._fld_address.setText(self._company.get("address", ""))
        self._fld_vat.setText(self._company.get("vat", ""))
        self._fld_phone.setText(self._company.get("phone", ""))
        self._fld_email.setText(self._company.get("email", ""))
        self._fld_website.setText(self._company.get("website", ""))

    # ------------------------------------------------------------------
    # Acties
    # ------------------------------------------------------------------

    def _on_save(self):
        name = self._fld_name.text().strip()
        if not name:
            QMessageBox.warning(
                self,
                self.windowTitle(),
                t("err_field_required")
            )
            self._fld_name.setFocus()
            return

        self._result = {
            "id":      self._company.get("id", ""),   # behouden bij edit; nieuw id via _gen_id
            "name":    name,
            "address": self._fld_address.text().strip(),
            "vat":     self._fld_vat.text().strip(),
            "phone":   self._fld_phone.text().strip(),
            "email":   self._fld_email.text().strip(),
            "website": self._fld_website.text().strip(),
        }
        # sites[] wordt niet geraakt door dit dialoog — behouden vanuit origineel
        if "sites" in self._company:
            self._result["sites"] = self._company["sites"]

        self.accept()

    # ------------------------------------------------------------------
    # Resultaat ophalen
    # ------------------------------------------------------------------

    def get_result(self) -> dict | None:
        """
        Geeft het ingevulde company-dict terug, of None bij annuleren.
        Bij nieuw: id is leeg string — caller voegt id toe via _gen_id().
        Bij bewerken: id is behouden uit het origineel.
        """
        return self._result