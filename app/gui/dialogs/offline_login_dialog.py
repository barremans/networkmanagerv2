# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/offline_login_dialog.py
# Role:    Poweruser login wanneer Azure AD niet bereikbaar is
# Version: 1.0.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie
#                  Naam + wachtwoord
#                  Bij succes: app start in read-only modus
#                  3 pogingen — daarna sluiten
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel,
    QLineEdit, QPushButton, QHBoxLayout, QMessageBox,
)
from PySide6.QtCore import Qt

from app.security.offline_auth import check_poweruser_password, log_offline_login

_MAX_ATTEMPTS = 3


class OfflineLoginDialog(QDialog):
    """
    Getoond wanneer Azure AD niet bereikbaar is.
    Poweruser kan inloggen met naam + wachtwoord.
    Bij succes: app start in read-only modus.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Offline toegang — Networkmap Creator")
        self.setFixedSize(420, 260)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self._attempts  = 0
        self._username  = ""

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel("🔒  Offline toegang")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        info = QLabel(
            "Azure AD is niet bereikbaar.\n"
            "Log in als poweruser om door te gaan in read-only modus."
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setWordWrap(True)
        info.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(info)

        layout.addSpacing(6)

        form = QFormLayout()
        form.setSpacing(8)

        self._txt_name = QLineEdit()
        self._txt_name.setPlaceholderText("Uw naam (voor logging)")
        form.addRow("Naam:", self._txt_name)

        self._txt_password = QLineEdit()
        self._txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._txt_password.setPlaceholderText("Wachtwoord")
        self._txt_password.returnPressed.connect(self._on_login)
        form.addRow("Wachtwoord:", self._txt_password)

        layout.addLayout(form)
        layout.addSpacing(4)

        self._lbl_error = QLabel("")
        self._lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_error.setStyleSheet("color: #e05050;")
        layout.addWidget(self._lbl_error)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._btn_login = QPushButton("Inloggen")
        self._btn_login.setFixedWidth(110)
        self._btn_login.clicked.connect(self._on_login)
        btn_row.addWidget(self._btn_login)

        btn_cancel = QPushButton("Annuleren")
        btn_cancel.setFixedWidth(110)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _on_login(self):
        name     = self._txt_name.text().strip()
        password = self._txt_password.text()

        if not name:
            self._lbl_error.setText("Vul uw naam in.")
            return

        if not password:
            self._lbl_error.setText("Vul het wachtwoord in.")
            return

        self._attempts += 1

        if check_poweruser_password(password):
            log_offline_login(name, success=True, reason="correct wachtwoord")
            self._username = name
            self.accept()
        else:
            remaining = _MAX_ATTEMPTS - self._attempts
            log_offline_login(name, success=False, reason="fout wachtwoord")

            if remaining <= 0:
                log_offline_login(name, success=False, reason="max pogingen bereikt")
                QMessageBox.critical(
                    self,
                    "Toegang geweigerd",
                    "Te veel mislukte pogingen. De applicatie wordt gesloten.",
                )
                self.reject()
            else:
                self._lbl_error.setText(
                    f"Ongeldig wachtwoord. Nog {remaining} poging(en)."
                )
                self._txt_password.clear()
                self._txt_password.setFocus()

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def get_username(self) -> str:
        """Geeft de ingevoerde naam terug na succesvolle login."""
        return self._username