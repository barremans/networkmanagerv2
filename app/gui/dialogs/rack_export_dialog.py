# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/rack_export_dialog.py
# Role:    Scopekeuze dialog voor MD rack-export (E2)
# Version: 1.0.1
# Author:  Barremans
# Changes: 1.0.0 — E2: initiële versie
#          1.0.1 — Bugfix: radiobutton signals direct gekoppeld (idClicked
#                  onbetrouwbaar in PySide6); QFrame site/rack rows correct
#                  aangemaakt; _update_ui() aangeroepen bij initialisatie
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QComboBox, QRadioButton,
    QButtonGroup, QPushButton, QFrame, QWidget,
)
from PySide6.QtCore import Qt

from app.helpers.i18n import t


class RackExportDialog(QDialog):
    """
    Dialog voor scopekeuze bij Markdown rack-export.

    Na accept() zijn beschikbaar:
        .scope    : "all" | "site" | "rack"
        .site_id  : str (alleen bij scope=="site")
        .rack_id  : str (alleen bij scope=="rack")
    """

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self._data   = data
        self.scope   = "all"
        self.site_id = ""
        self.rack_id = ""

        self.setWindowTitle(t("rack_export_dialog_title"))
        self.setMinimumWidth(420)
        self.setModal(True)
        self._build()
        self._update_ui()

    # ------------------------------------------------------------------
    # UI opbouw
    # ------------------------------------------------------------------

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        hint = QLabel(t("rack_export_hint"))
        hint.setObjectName("secondary")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # --- Scope keuze ---
        grp = QGroupBox(t("rack_export_scope_group"))
        grp_layout = QVBoxLayout(grp)
        grp_layout.setSpacing(8)

        self._btn_all  = QRadioButton(t("rack_export_scope_all"))
        self._btn_site = QRadioButton(t("rack_export_scope_site"))
        self._btn_rack = QRadioButton(t("rack_export_scope_rack"))
        self._btn_all.setChecked(True)

        # QButtonGroup puur voor exclusiviteit — signals direct per knop
        self._grp_btns = QButtonGroup(self)
        self._grp_btns.addButton(self._btn_all,  0)
        self._grp_btns.addButton(self._btn_site, 1)
        self._grp_btns.addButton(self._btn_rack, 2)

        grp_layout.addWidget(self._btn_all)
        grp_layout.addWidget(self._btn_site)
        grp_layout.addWidget(self._btn_rack)
        layout.addWidget(grp)

        # --- Site dropdown ---
        self._site_row = QWidget()
        site_form = QFormLayout(self._site_row)
        site_form.setContentsMargins(0, 4, 0, 0)
        self._ddl_site = QComboBox()
        for site in self._data.get("sites", []):
            self._ddl_site.addItem(site.get("name", "?"), userData=site["id"])
        site_form.addRow(t("rack_export_select_site") + ":", self._ddl_site)
        layout.addWidget(self._site_row)

        # --- Rack dropdown ---
        self._rack_row = QWidget()
        rack_form = QFormLayout(self._rack_row)
        rack_form.setContentsMargins(0, 4, 0, 0)
        self._ddl_rack = QComboBox()
        self._populate_racks()
        rack_form.addRow(t("rack_export_select_rack") + ":", self._ddl_rack)
        layout.addWidget(self._rack_row)

        layout.addStretch()

        # --- Knoppen ---
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(t("btn_cancel"))
        btn_export = QPushButton(t("rack_export_btn_export"))
        btn_export.setDefault(True)
        btn_cancel.clicked.connect(self.reject)
        btn_export.clicked.connect(self._on_export)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_export)
        layout.addLayout(btn_row)

        # Signals — direct per radiobutton (betrouwbaarder dan idClicked)
        self._btn_all.toggled.connect(self._update_ui)
        self._btn_site.toggled.connect(self._update_ui)
        self._btn_rack.toggled.connect(self._update_ui)

    def _populate_racks(self):
        """Vul de rack-dropdown met alle racks over alle sites."""
        self._ddl_rack.clear()
        for site in self._data.get("sites", []):
            for room in site.get("rooms", []):
                for rack in room.get("racks", []):
                    label = (f"{site.get('name','?')}  \u203a  "
                             f"{room.get('name','?')}  \u203a  "
                             f"{rack.get('name','?')}")
                    self._ddl_rack.addItem(label, userData=rack["id"])

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _update_ui(self, _checked=None):
        """Toon alleen de relevante dropdown op basis van geselecteerde scope."""
        self._site_row.setVisible(self._btn_site.isChecked())
        self._rack_row.setVisible(self._btn_rack.isChecked())
        self.adjustSize()

    def _on_export(self):
        if self._btn_all.isChecked():
            self.scope = "all"
        elif self._btn_site.isChecked():
            self.scope   = "site"
            self.site_id = self._ddl_site.currentData() or ""
        else:
            self.scope   = "rack"
            self.rack_id = self._ddl_rack.currentData() or ""
        self.accept()