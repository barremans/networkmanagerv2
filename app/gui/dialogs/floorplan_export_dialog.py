# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/floorplan_export_dialog.py
# Role:    Dialoog — scopekeuze voor grondplan PDF export
# Version: 1.5.0
# Author:  Barremans
# Changes: 1.5.0 — Bestandsnaam op basis van scope:
#                   huidig grondplan → fp_name_site_name_gekoppeld.docx
#                   alle grondplannen → ALL_site_name_gekoppeld.docx
#          1.4.0 — Exporteert naar .docx (Word) ipv .pdf
#                   Bestandsdialoog filter gewijzigd naar Word-documenten
#          1.3.0 — Expliciete QRadioButton stylesheet: indicator altijd zichtbaar
#                   geselecteerde indicator wit, niet-geselecteerde transparant
#          1.2.0 — QButtonGroup terug toegevoegd
#          1.1.0 — Vereenvoudigd: enkel PDF
#          1.0.0 — G-OPEN-8: initiële versie
# =============================================================================

from pathlib import Path

from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from app.helpers import settings_storage
from app.helpers.i18n import t


class FloorplanExportDialog(QDialog):
    """
    Dialoog voor grondplan PDF export (G-OPEN-8).

    Na accept() zijn beschikbaar:
        .scope   : "current" | "site"
        .filepath: str — volledig pad inclusief .pdf extensie
    """

    def __init__(self, floorplan: dict, site: dict, parent=None):
        super().__init__(parent)
        self._floorplan = floorplan or {}
        self._site      = site or {}

        self.scope    = "current"
        self.filepath = ""

        self.setWindowTitle(t("fp_export_dialog_title"))
        self.setMinimumWidth(420)
        self.setModal(True)

        self._build()

    # ------------------------------------------------------------------
    # UI opbouw
    # ------------------------------------------------------------------

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        hint = QLabel(t("fp_export_hint"))
        hint.setObjectName("secondary")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # --- Bereik ---
        grp = QGroupBox(t("fp_export_scope_group"))
        grp_layout = QVBoxLayout(grp)
        grp_layout.setSpacing(8)

        self._btn_current = QRadioButton(t("fp_export_scope_current"))
        self._btn_site    = QRadioButton(t("fp_export_scope_site"))
        self._btn_current.setChecked(True)

        # QButtonGroup voor correcte exclusiviteit en indicator-state
        self._grp_scope = QButtonGroup(self)
        self._grp_scope.addButton(self._btn_current, 0)
        self._grp_scope.addButton(self._btn_site,    1)

        site_name = self._site.get("name", "")
        if site_name:
            self._btn_site.setText(
                f"{t('fp_export_scope_site')}  ({site_name})"
            )

        # Expliciete indicator-styling zodat de cirkel zichtbaar is in elk thema
        _rb_style = """
            QRadioButton { spacing: 8px; }
            QRadioButton::indicator {
                width: 16px; height: 16px;
                border-radius: 8px;
                border: 2px solid #888888;
                background: transparent;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #ffffff;
                background: #ffffff;
            }
            QRadioButton::indicator:hover {
                border: 2px solid #cccccc;
            }
        """
        self._btn_current.setStyleSheet(_rb_style)
        self._btn_site.setStyleSheet(_rb_style)

        grp_layout.addWidget(self._btn_current)
        grp_layout.addWidget(self._btn_site)
        layout.addWidget(grp)

        layout.addStretch()

        # --- Scheidingslijn ---
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # --- Knoppen ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton(t("btn_cancel"))
        btn_cancel.clicked.connect(self.reject)

        btn_export = QPushButton(t("fp_export_btn_export"))
        btn_export.setDefault(True)
        btn_export.clicked.connect(self._on_export)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_export)
        layout.addLayout(btn_row)

        # Signals direct per radiobutton (betrouwbaarder dan QButtonGroup)
        self._btn_current.toggled.connect(self._update_ui)
        self._btn_site.toggled.connect(self._update_ui)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _update_ui(self, _checked=None):
        pass  # uitbreidbaar bij toekomstige opties

    def _on_export(self):
        self.scope = "current" if self._btn_current.isChecked() else "site"

        last_folder  = settings_storage.get_last_folder("fp_export") or ""
        site_name = self._site.get("name", "") or ""
        if self.scope == "site":
            # Alle grondplannen van de site → ALL_sitenaam
            base_name = f"ALL_{site_name}".replace(" ", "_").strip("_")
        else:
            # Huidig grondplan → grondplaannaam_sitenaam
            fp_name   = self._floorplan.get("name", "") or self._floorplan.get("outlet_location_key", "") or "grondplan"
            base_name = f"{fp_name}_{site_name}".replace(" ", "_").strip("_")
        default_name = f"{base_name}_gekoppeld.docx"
        start_path   = f"{last_folder}/{default_name}" if last_folder else default_name

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            t("fp_export_dialog_title"),
            start_path,
            "Word document (*.docx)",
        )

        if not filepath:
            return

        if not filepath.lower().endswith(".docx"):
            filepath += ".docx"

        settings_storage.set_last_folder("fp_export", str(Path(filepath).parent))

        self.filepath = filepath
        self.accept()