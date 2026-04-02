# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/floorplan_manage_dialog.py
# Role:    Dialoog — grondplan beheren (naam, site, locatie, verwijderen)
# Version: 1.2.0
# Author:  Barremans
# Changes: 1.2.0 — G-OPEN-5/6: knop "SVG vervangen" naast SVG label
#                  roept floorplan_service.replace_svg() aan
#                  toont melding met verwijderde verouderde koppelingen
#                  floorplan_changed signaal wordt ook na SVG-wissel geëmit
#          1.1.0 — floorplan_changed signaal toegevoegd
#                  wordt geëmit direct na opslaan zodat FloorplanView live kan verversen
#          1.0.1 — Fix: currentRowChanged → itemSelectionChanged (PySide6 API)
#          1.0.0 — Initiële versie
#                   Tabel met alle geldige grondplannen
#                   Bewerken: naam, beschrijving, site, wandpunt locatie
#                   Verwijderen met bevestiging
#                   Read-only compatibel
# =============================================================================

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QComboBox,
    QVBoxLayout,
    QWidget,
)

from app.helpers import settings_storage
from app.helpers.i18n import get_language, t
from app.services import floorplan_service


class FloorplanManageDialog(QDialog):
    """
    Beheerdialoog voor grondplannen.

    Links: tabel met alle grondplannen
    Rechts: bewerkformulier voor geselecteerd grondplan
    """

    floorplan_changed = Signal(str)  # floorplan_id — emitted na elke opslag

    def __init__(self, parent=None, data: dict | None = None):
        super().__init__(parent)
        self._data       = data or {}
        self._floorplans : list[dict] = []
        self._selected_fp: dict | None = None
        self._changed    = False

        self.setWindowTitle(t("menu_floorplan_manage"))
        self.setModal(True)
        self.setMinimumSize(860, 480)
        self.resize(980, 560)

        self._build_ui()
        self._load_data()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ── Links: tabel ─────────────────────────────────────────────
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.setSpacing(6)

        lbl = QLabel(t("menu_floorplan_manage"))
        lbl.setObjectName("secondary")
        left_layout.addWidget(lbl)

        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels([
            t("label_name"),
            t("label_site"),
            t("settings_tab_outlet_locations"),
        ])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self._table, 1)

        # Verwijder knop onder de tabel
        self._btn_delete = QPushButton("🗑  " + t("msg_floorplan_deleted").replace(".", ""))
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_delete.setEnabled(False)
        left_layout.addWidget(self._btn_delete)

        splitter.addWidget(left)

        # ── Rechts: bewerkformulier ───────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.setSpacing(6)

        lbl2 = QLabel(t("label_rack"))  # hergebruik "Bewerken" concept
        lbl2.setObjectName("secondary")
        lbl2.setText("Bewerken")
        right_layout.addWidget(lbl2)

        form = QFormLayout()
        form.setSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)

        # Naam
        self._edit_name = QLineEdit()
        self._edit_name.setPlaceholderText("(optioneel)")
        form.addRow(t("label_name") + ":", self._edit_name)

        # Beschrijving
        self._edit_desc = QTextEdit()
        self._edit_desc.setFixedHeight(60)
        self._edit_desc.setPlaceholderText("(optioneel)")
        form.addRow(t("label_notes") + ":", self._edit_desc)

        # Site
        self._cmb_site = QComboBox()
        self._cmb_site.currentIndexChanged.connect(self._on_site_changed)
        form.addRow(t("label_floorplan_site") + ":", self._cmb_site)

        # Wandpunt locatie
        self._cmb_location = QComboBox()
        form.addRow(t("settings_tab_outlet_locations") + ":", self._cmb_location)

        # SVG bestand (readonly info) + vervang knop
        svg_row = QHBoxLayout()
        svg_row.setContentsMargins(0, 0, 0, 0)
        svg_row.setSpacing(6)
        self._lbl_svg = QLabel("-")
        self._lbl_svg.setObjectName("secondary")
        self._btn_replace_svg = QPushButton("📂 " + t("btn_browse"))
        self._btn_replace_svg.setFixedWidth(90)
        self._btn_replace_svg.clicked.connect(self._on_replace_svg)
        self._btn_replace_svg.setEnabled(False)
        svg_row.addWidget(self._lbl_svg, 1)
        svg_row.addWidget(self._btn_replace_svg)

        svg_widget = QWidget()
        svg_widget.setLayout(svg_row)
        form.addRow(t("label_floorplan_svg") + ":", svg_widget)

        right_layout.addLayout(form)
        right_layout.addStretch(1)

        # Opslaan knop
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self._btn_save = QPushButton(t("btn_save"))
        self._btn_save.clicked.connect(self._on_save)
        self._btn_save.setEnabled(False)
        btn_row.addWidget(self._btn_save)
        right_layout.addLayout(btn_row)

        splitter.addWidget(right)
        splitter.setSizes([560, 380])
        root.addWidget(splitter, 1)

        # Sluitknop onderaan
        close_row = QHBoxLayout()
        close_row.addStretch(1)
        btn_close = QPushButton(t("btn_cancel"))
        btn_close.clicked.connect(self.accept)
        close_row.addWidget(btn_close)
        root.addLayout(close_row)

        self._set_form_enabled(False)
        self._apply_read_only()

    # ------------------------------------------------------------------
    # Data laden
    # ------------------------------------------------------------------

    def _load_data(self):
        """Laad alle grondplannen in de tabel."""
        all_fp = floorplan_service.load_floorplans().get("floorplans", [])
        # Toon alle, ook zonder locatie — beheer moet ze kunnen fixen
        self._floorplans = all_fp

        lang = get_language()
        locs = settings_storage.load_outlet_locations()
        self._loc_labels = {
            loc["key"]: loc.get(f"label_{lang}") or loc.get("label_nl") or loc["key"]
            for loc in locs
        }
        self._locs = locs

        # Sites voor DDL
        self._sites = self._data.get("sites", [])

        self._refresh_table()

    def _refresh_table(self):
        self._table.setRowCount(0)
        lang = get_language()

        for fp in self._floorplans:
            row = self._table.rowCount()
            self._table.insertRow(row)

            name    = fp.get("name", "") or fp.get("svg_file", fp.get("id", ""))
            site    = self._find_site_name(fp.get("site_id"))
            loc_key = fp.get("outlet_location_key", "")
            loc     = self._loc_labels.get(loc_key, loc_key or "⚠ geen locatie")

            item_name = QTableWidgetItem(name)
            item_name.setData(Qt.ItemDataRole.UserRole, fp.get("id"))
            if not loc_key:
                # Markeer records zonder locatie
                for item in [item_name]:
                    item.setForeground(Qt.GlobalColor.red)

            self._table.setItem(row, 0, item_name)
            self._table.setItem(row, 1, QTableWidgetItem(site))
            self._table.setItem(row, 2, QTableWidgetItem(loc))

        if self._table.rowCount() > 0:
            self._table.selectRow(0)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _on_selection_changed(self):
        row = self._table.currentRow()
        if row < 0 or row >= len(self._floorplans):
            self._selected_fp = None
            self._set_form_enabled(False)
            self._btn_delete.setEnabled(False)
            return

        fp_id = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self._selected_fp = next(
            (f for f in self._floorplans if f.get("id") == fp_id), None
        )
        if self._selected_fp:
            self._populate_form(self._selected_fp)
            self._set_form_enabled(True)
            self._btn_delete.setEnabled(
                not settings_storage.get_read_only_mode()
            )

    def _on_replace_svg(self):
        """G-OPEN-5/6 — Vervang SVG bestand van geselecteerd grondplan."""
        if not self._selected_fp or settings_storage.get_read_only_mode():
            return

        from PySide6.QtWidgets import QFileDialog
        last_folder = settings_storage.get_last_folder("floorplan_svg") or ""
        path, _ = QFileDialog.getOpenFileName(
            self, t("label_floorplan_svg"), last_folder, "SVG (*.svg)"
        )
        if not path:
            return

        from pathlib import Path as _Path
        settings_storage.set_last_folder("floorplan_svg", str(_Path(path).parent))

        from app.services import floorplan_service
        fp_id = self._selected_fp.get("id", "")
        ok, err, removed = floorplan_service.replace_svg(fp_id, path)

        if not ok:
            QMessageBox.warning(self, self.windowTitle(), f"SVG vervangen mislukt:\n{err}")
            return

        # Toon resultaat
        msg = t("msg_backup_ok") if hasattr(self, "_dummy") else "SVG vervangen."
        if removed:
            msg = f"SVG vervangen.\n\n⚠ {len(removed)} verouderde koppeling(en) verwijderd:\n{', '.join(removed)}"
        else:
            msg = "SVG vervangen. Alle bestaande koppelingen zijn nog geldig."

        QMessageBox.information(self, self.windowTitle(), msg)

        self._changed = True
        self.floorplan_changed.emit(fp_id)
        self._load_data()

        # Herselect hetzelfde grondplan
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == fp_id:
                self._table.selectRow(row)
                break

    def _on_site_changed(self, idx: int):
        """Bij site wissel: herlaad wandpunt locaties DDL."""
        self._populate_location_ddl()

    def _on_save(self):
        if not self._selected_fp:
            return
        if settings_storage.get_read_only_mode():
            return

        fp_id    = self._selected_fp.get("id", "")
        name     = self._edit_name.text().strip()
        desc     = self._edit_desc.toPlainText().strip()
        site_id  = self._cmb_site.currentData() or ""
        loc_key  = self._cmb_location.currentData() or ""

        if not site_id or not loc_key:
            QMessageBox.warning(self, self.windowTitle(),
                                t("err_select_site_for_room"))
            return

        # Controleer of site+locatie al bezet is door een ANDER grondplan
        existing = floorplan_service.get_floorplan_for_location(site_id, loc_key)
        if existing and existing.get("id") != fp_id:
            QMessageBox.warning(self, self.windowTitle(),
                                t("msg_floorplan_exists"))
            return

        floorplan_service.update_floorplan_meta(
            floorplan_id        = fp_id,
            name                = name,
            description         = desc,
            site_id             = site_id,
            outlet_location_key = loc_key,
        )
        self._changed = True
        self.floorplan_changed.emit(fp_id)

        # Herlaad tabel
        self._load_data()
        self.statusBar().showMessage(t("btn_save") + " ✓", 3000) if hasattr(self, "statusBar") else None

    def _on_delete(self):
        if not self._selected_fp:
            return
        if settings_storage.get_read_only_mode():
            return

        fp = self._selected_fp
        name = fp.get("name", "") or fp.get("svg_file", fp.get("id", ""))
        reply = QMessageBox.question(
            self,
            "Grondplan verwijderen",
            f"'{name}' verwijderen?\n\nDit verwijdert ook het SVG bestand en alle koppelingen.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        floorplan_service.delete_floorplan(fp.get("id", ""))
        self._changed = True
        self._selected_fp = None
        self._load_data()
        self._set_form_enabled(False)

    # ------------------------------------------------------------------
    # Form helpers
    # ------------------------------------------------------------------

    def _populate_form(self, fp: dict):
        self._edit_name.setText(fp.get("name", ""))
        self._edit_desc.setPlainText(fp.get("description", ""))
        self._lbl_svg.setText(fp.get("svg_file", "-"))

        # Sites DDL
        self._cmb_site.blockSignals(True)
        self._cmb_site.clear()
        for site in self._sites:
            self._cmb_site.addItem(site.get("name", "?"), site.get("id"))
        idx = self._cmb_site.findData(fp.get("site_id", ""))
        if idx >= 0:
            self._cmb_site.setCurrentIndex(idx)
        self._cmb_site.blockSignals(False)

        self._populate_location_ddl(preselect=fp.get("outlet_location_key", ""))

    def _populate_location_ddl(self, preselect: str = ""):
        self._cmb_location.clear()
        lang = get_language()
        for loc in self._locs:
            key   = loc.get("key", "")
            label = loc.get(f"label_{lang}") or loc.get("label_nl") or key
            self._cmb_location.addItem(label, key)
        if preselect:
            idx = self._cmb_location.findData(preselect)
            if idx >= 0:
                self._cmb_location.setCurrentIndex(idx)

    def _set_form_enabled(self, enabled: bool):
        for w in [self._edit_name, self._edit_desc,
                  self._cmb_site, self._cmb_location,
                  self._btn_save, self._btn_replace_svg]:
            w.setEnabled(enabled)
        if not enabled:
            self._edit_name.clear()
            self._edit_desc.clear()
            self._lbl_svg.setText("-")
            self._cmb_site.clear()
            self._cmb_location.clear()

    def _apply_read_only(self):
        if settings_storage.get_read_only_mode():
            self._btn_save.setEnabled(False)
            self._btn_delete.setEnabled(False)
            self._btn_replace_svg.setEnabled(False)
            self._edit_name.setReadOnly(True)
            self._edit_desc.setReadOnly(True)
            self._cmb_site.setEnabled(False)
            self._cmb_location.setEnabled(False)

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def has_changes(self) -> bool:
        """True als er wijzigingen zijn die de aanroeper moet verwerken."""
        return self._changed

    # ------------------------------------------------------------------
    # Data lookup
    # ------------------------------------------------------------------

    def _find_site_name(self, site_id: str | None) -> str:
        if not site_id:
            return "-"
        for site in self._sites:
            if site.get("id") == site_id:
                return site.get("name", site_id)
        return site_id