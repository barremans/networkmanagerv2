# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/rack_export_dialog.py
# Role:    Scopekeuze + exportopties dialog voor MD rack-export (E2)
# Version: 2.1.0
# Author:  Barremans
# Changes: 2.1.0 — Tracing-only checkbox toegevoegd
#                  _update_tracing_mode: schakelt andere opties uit
#          2.0.2 — setMaximumHeight(640) om scherm-overflow te vermijden
#          2.0.1 — QSS radiobutton fluo-geel
#          2.0.0 — Exportopties toegevoegd: vrije poorten, patchpanels,
#                  switches, aandachtspunten, controlelog
#                  Detailniveau: kort / technisch / volledig
#                  options-property beschikbaar na accept()
#          1.0.1 — Bugfix: radiobutton signals direct gekoppeld
#          1.0.0 — E2: initiële versie
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QComboBox, QRadioButton,
    QButtonGroup, QPushButton, QFrame, QWidget, QCheckBox,
)
from PySide6.QtCore import Qt

from app.helpers.i18n import t


_RADIO_QSS = """
QRadioButton {
    spacing: 8px;
    padding: 2px 4px;
    border-radius: 4px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid #666666;
    background-color: transparent;
}
QRadioButton::indicator:checked {
    border: 2px solid #D4FF00;
    background-color: #D4FF00;
}
QRadioButton:checked {
    color: #D4FF00;
    font-weight: bold;
}
"""


class RackExportDialog(QDialog):
    """
    Dialog voor scopekeuze en exportopties bij Markdown rack-export.

    Na accept() zijn beschikbaar:
        .scope    : "all" | "site" | "rack"
        .site_id  : str (alleen bij scope=="site")
        .rack_id  : str (alleen bij scope=="rack")
        .options  : dict met exportopties voor rack_export_md.export_md()
    """

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self._data   = data
        self.scope   = "all"
        self.site_id = ""
        self.rack_id = ""
        self.options: dict = {}

        self.setWindowTitle(t("rack_export_dialog_title"))
        self.setMinimumWidth(460)
        self.setMaximumHeight(640)
        self.setModal(True)
        self.setStyleSheet(_RADIO_QSS)
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

        # --- Detailniveau ---
        grp_level = QGroupBox("Detailniveau")
        level_layout = QHBoxLayout(grp_level)
        level_layout.setSpacing(16)
        self._btn_short    = QRadioButton("Kort")
        self._btn_tech     = QRadioButton("Technisch")
        self._btn_full     = QRadioButton("Volledig")
        self._btn_tech.setChecked(True)
        self._grp_level = QButtonGroup(self)
        self._grp_level.addButton(self._btn_short, 0)
        self._grp_level.addButton(self._btn_tech,  1)
        self._grp_level.addButton(self._btn_full,  2)
        level_layout.addWidget(self._btn_short)
        level_layout.addWidget(self._btn_tech)
        level_layout.addWidget(self._btn_full)
        level_layout.addStretch()
        layout.addWidget(grp_level)

        # --- Exportopties ---
        grp_opts = QGroupBox("Exportopties")
        opts_layout = QVBoxLayout(grp_opts)
        opts_layout.setSpacing(6)

        self._chk_tracing_only = QCheckBox("📋 Tracing-only (rackfiche voor aan het rack)")
        self._chk_tracing_only.setChecked(False)
        self._chk_tracing_only.setToolTip(
            "Compacte export met alleen U-layout, aandachtspunten en volledige\n"
            "switchpoort-tracing. Ideaal om uitgedrukt bij het rack te leggen.\n"
            "Patchpanelmatrix, wandpunttabel en controlelog worden weggelaten."
        )
        opts_layout.addWidget(self._chk_tracing_only)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        opts_layout.addWidget(sep2)

        self._chk_free_ports   = QCheckBox("Vrije poorten tonen")
        self._chk_switches     = QCheckBox("Switchpoortdetails tonen")
        self._chk_patchpanels  = QCheckBox("Patchpaneldetails tonen")
        self._chk_attention    = QCheckBox("Aandachtspunten tonen")
        self._chk_control_log  = QCheckBox("Controlelog toevoegen")

        self._chk_free_ports.setChecked(True)
        self._chk_switches.setChecked(True)
        self._chk_patchpanels.setChecked(True)
        self._chk_attention.setChecked(True)
        self._chk_control_log.setChecked(True)

        for chk in (self._chk_free_ports, self._chk_switches,
                    self._chk_patchpanels, self._chk_attention,
                    self._chk_control_log):
            opts_layout.addWidget(chk)

        # Tracing-only schakelt andere opties uit
        self._chk_tracing_only.toggled.connect(self._update_tracing_mode)
        layout.addWidget(grp_opts)

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

        # Signals
        self._btn_all.toggled.connect(self._update_ui)
        self._btn_site.toggled.connect(self._update_ui)
        self._btn_rack.toggled.connect(self._update_ui)
        self._btn_short.toggled.connect(self._update_options_ui)
        self._btn_tech.toggled.connect(self._update_options_ui)
        self._btn_full.toggled.connect(self._update_options_ui)

    def _populate_racks(self):
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
        self._site_row.setVisible(self._btn_site.isChecked())
        self._rack_row.setVisible(self._btn_rack.isChecked())
        self.adjustSize()

    def _update_options_ui(self, _checked=None):
        """Bij 'Kort' zijn switch- en patchpaneldetails niet relevant."""
        is_short    = self._btn_short.isChecked()
        is_tracing  = self._chk_tracing_only.isChecked()
        self._chk_switches.setEnabled(not is_short and not is_tracing)
        self._chk_patchpanels.setEnabled(not is_short and not is_tracing)
        self._chk_free_ports.setEnabled(not is_short and not is_tracing)
        self._chk_attention.setEnabled(not is_tracing)
        self._chk_control_log.setEnabled(not is_tracing)
        self.adjustSize()

    def _update_tracing_mode(self, checked: bool):
        """Tracing-only: schakel andere opties uit en zet detailniveau op volledig."""
        self._chk_switches.setEnabled(not checked)
        self._chk_patchpanels.setEnabled(not checked)
        self._chk_free_ports.setEnabled(not checked)
        self._chk_attention.setEnabled(not checked)
        self._chk_control_log.setEnabled(not checked)
        self._btn_level_group = getattr(self, "_grp_level", None)
        if self._btn_level_group:
            for btn in [self._btn_short, self._btn_tech, self._btn_full]:
                btn.setEnabled(not checked)
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

        if self._btn_short.isChecked():
            level = "short"
        elif self._btn_full.isChecked():
            level = "full"
        else:
            level = "technical"

        self.options = {
            "include_free_ports":       self._chk_free_ports.isChecked(),
            "include_switches":         self._chk_switches.isChecked(),
            "include_patchpanels":      self._chk_patchpanels.isChecked(),
            "include_attention_points": self._chk_attention.isChecked(),
            "include_control_log":      self._chk_control_log.isChecked(),
            "detail_level":             level,
            "tracing_only":             self._chk_tracing_only.isChecked(),
        }
        self.accept()