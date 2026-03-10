# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/vlan_propagation_dialog.py
# Role:    Waarschuwing bij VLAN conflict tijdens propagatie
# Version: 1.0.0
# Author:  Barremans
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from app.services.vlan_service import vlan_label


class VlanPropagationDialog(QDialog):
    """
    Toont conflicten bij VLAN propagatie en vraagt bevestiging.

    Retourneert:
        QDialog.Accepted → overschrijf conflicten
        QDialog.Rejected → annuleer
    """

    def __init__(self, parent=None, new_vlan: int = 0,
                 port_conflicts: list = None,
                 outlet_conflicts: list = None):
        super().__init__(parent)
        self._new_vlan        = new_vlan
        self._port_conflicts  = port_conflicts  or []
        self._outlet_conflicts = outlet_conflicts or []
        self.setWindowTitle("⚠  VLAN conflict")
        self.setMinimumWidth(460)
        self.setModal(True)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header
        hdr = QLabel(
            f"Je wijst <b>{vlan_label(self._new_vlan)}</b> toe aan een trace<br>"
            f"maar de volgende objecten hebben al een ander VLAN:"
        )
        hdr.setTextFormat(Qt.TextFormat.RichText)
        hdr.setWordWrap(True)
        layout.addWidget(hdr)

        # Conflicten tonen
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(200)
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setSpacing(4)
        cl.setContentsMargins(8, 8, 8, 8)

        all_conflicts = (
            [(c, "poort")   for c in self._port_conflicts] +
            [(c, "wandpunt") for c in self._outlet_conflicts]
        )
        for c, ctype in all_conflicts:
            row = QLabel(
                f"• <b>{c['name']}</b>  ({ctype})  "
                f"—  huidig: <span style='color:#e09a2a;'>"
                f"{vlan_label(c['current_vlan'])}</span>"
                f"  →  <span style='color:#4caf7d;'>"
                f"{vlan_label(self._new_vlan)}</span>"
            )
            row.setTextFormat(Qt.TextFormat.RichText)
            row.setWordWrap(True)
            cl.addWidget(row)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Vraag
        vraag = QLabel("Wil je deze objecten <b>overschrijven</b> met het nieuwe VLAN?")
        vraag.setTextFormat(Qt.TextFormat.RichText)
        vraag.setWordWrap(True)
        layout.addWidget(vraag)

        # Knoppen
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Annuleren")
        btn_ok     = QPushButton(f"Ja, overschrijven met VLAN {self._new_vlan}")
        btn_ok.setDefault(True)
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)