# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/no_access_dialog.py
# Role:    Venster getoond bij geen AD-toegang
# Version: 1.0.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie
# =============================================================================

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt


class NoAccessDialog(QDialog):
    """
    Wordt getoond wanneer de gebruiker niet in CGK-APP-L6 zit.
    App sluit na OK.
    """

    def __init__(self, parent=None, reason: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Geen toegang — Networkmap Creator")
        self.setFixedSize(480, 220)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("🚫  Geen toegang")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        msg = QLabel(
            "U bent niet gemachtigd om Networkmap Creator te gebruiken.\n"
            "Vereiste groep: CGK-APP-L6"
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