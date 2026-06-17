# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/no_access_dialog.py
# Role:    Venster getoond bij geen AD-toegang
# Version: 1.2.0
# Author:  Barremans
# Changes: 1.2.0 — S6b: twee groepen tonen in foutmelding (admin + readonly)
#          1.1.0 — S6: groepsnaam dynamisch uit settings
#          1.0.0 — Initiële versie
# =============================================================================

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from app.helpers.settings_storage import get_azure_ad_config


class NoAccessDialog(QDialog):
    """
    Wordt getoond wanneer de gebruiker niet in de vereiste AD-groep zit.
    Groepsnaam wordt dynamisch gelezen uit Settings → Azure AD.
    App sluit na OK.
    """

    def __init__(self, parent=None, reason: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Geen toegang — Networkmap Creator")
        self.setFixedSize(480, 220)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        cfg            = get_azure_ad_config()
        group_admin    = cfg.get("group_admin",    "") or "—"
        group_readonly = cfg.get("group_readonly", "")

        groepen_tekst = f"Admin-groep: {group_admin}"
        if group_readonly:
            groepen_tekst += f"\nRead-only groep: {group_readonly}"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("🚫  Geen toegang")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        msg = QLabel(
            "U bent niet gemachtigd om Networkmap Creator te gebruiken.\n"
            f"{groepen_tekst}"
        )
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True)
        layout.addWidget(msg)

        if reason:
            hint = QLabel(reason)
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint.setWordWrap(True)
            hint.setStyleSheet("color: #888; font-size: 11px;")
            layout.addWidget(hint)

        layout.addStretch()

        btn = QPushButton("Sluiten")
        btn.setFixedWidth(120)
        btn.clicked.connect(self.reject)

        btn_row_layout = QVBoxLayout()
        btn_row_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_row_layout.addWidget(btn)
        layout.addLayout(btn_row_layout)