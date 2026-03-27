# =============================================================================
# Networkmap_Creator
# File:    app/gui/floorplan_test_window.py
# Role:    Losse testhost voor floorplan dialog en viewer
# Version: 1.6.0
# Author:  Barremans
# Changes: 1.6.0 — Beheer knop toegevoegd → FloorplanManageDialog
#                   Verwijder knop verwijderd (zit nu in beheerdialoog)
#          1.5.0 — Filter ongeldige grondplannen, knop "Bekijk" weg
#          1.3.0 — Dubbel venster bug, outlet_location_key, DDL
#
# Starten via: python -m app.gui.floorplan_test_window
# =============================================================================

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.helpers import settings_storage
from app.helpers.i18n import get_language, set_language, t
from app.gui.dialogs.floorplan_dialog import FloorplanDialog
from app.gui.dialogs.floorplan_manage_dialog import FloorplanManageDialog
from app.gui.floorplan_view import FloorplanView
from app.services import floorplan_service


class FloorplanTestWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self._data = settings_storage.load_network_data()
        self._current_view = None
        self._valid_floorplans: list[dict] = []   # alleen geldige (met locatie)

        self._setup_window()
        self._build_ui()
        self._reload_floorplan_list()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_window(self):
        self.setWindowTitle(f"{t('title_floorplan_view')} — Test")
        self.resize(1280, 820)
        self.setMinimumSize(1000, 700)

    def _build_ui(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        # Nieuw grondplan
        self._btn_new = QPushButton(t("menu_floorplan_new"))
        self._btn_new.clicked.connect(self._on_new_floorplan)

        # DDL — alleen geldige grondplannen
        self._cmb_floorplans = QComboBox()
        self._cmb_floorplans.setMinimumWidth(320)
        self._cmb_floorplans.currentIndexChanged.connect(self._on_floorplan_selected)

        # Beheer knop
        self._btn_manage = QPushButton("⚙  " + t("menu_floorplan_manage"))
        self._btn_manage.setToolTip(t("menu_floorplan_manage"))
        self._btn_manage.clicked.connect(self._on_manage_floorplans)

        self._lbl_info = QLabel("-")
        self._lbl_info.setObjectName("secondary")

        top_row.addWidget(self._btn_new)
        top_row.addWidget(self._cmb_floorplans)
        top_row.addWidget(self._btn_manage)
        top_row.addStretch(1)

        layout.addLayout(top_row)
        layout.addWidget(self._lbl_info)

        # Centrale host
        self._host = QWidget()
        self._host_layout = QVBoxLayout(self._host)
        self._host_layout.setContentsMargins(0, 0, 0, 0)
        self._host_layout.setSpacing(0)

        self._placeholder = QLabel(t("msg_floorplan_not_found"))
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setObjectName("secondary")
        self._host_layout.addWidget(self._placeholder)

        layout.addWidget(self._host, 1)
        self.setCentralWidget(root)
        self._apply_read_only_mode()

    # ------------------------------------------------------------------
    # Floorplan lijst
    # ------------------------------------------------------------------

    def _reload_floorplan_list(self):
        """
        Laad grondplannen — verberg records zonder outlet_location_key.
        """
        all_fp = floorplan_service.load_floorplans().get("floorplans", [])

        # Filter: alleen grondplannen met geldige locatie + bestaand SVG bestand
        self._valid_floorplans = [
            fp for fp in all_fp
            if fp.get("outlet_location_key", "").strip()
            and floorplan_service.svg_exists(fp)
        ]

        self._cmb_floorplans.blockSignals(True)
        self._cmb_floorplans.clear()

        if not self._valid_floorplans:
            self._cmb_floorplans.addItem(t("msg_floorplan_not_found"), None)
            self._cmb_floorplans.setEnabled(False)
            self._clear_host()
            self._show_placeholder()
        else:
            self._cmb_floorplans.setEnabled(True)
            lang = get_language()
            locs = settings_storage.load_outlet_locations()
            loc_labels = {
                loc["key"]: loc.get(f"label_{lang}") or loc.get("label_nl") or loc["key"]
                for loc in locs
            }
            for fp in self._valid_floorplans:
                site_name = self._find_site_name(fp.get("site_id"))
                loc_key   = fp.get("outlet_location_key", "")
                loc_label = loc_labels.get(loc_key, loc_key)
                self._cmb_floorplans.addItem(f"{site_name}  —  {loc_label}", fp.get("id"))

        self._cmb_floorplans.blockSignals(False)

        # Automatisch laatste tonen
        if self._valid_floorplans:
            self._open_floorplan(self._valid_floorplans[-1])

    def _on_floorplan_selected(self, idx: int):
        """DDL gewijzigd — direct openen."""
        if idx < 0 or idx >= len(self._valid_floorplans):
            self._update_info_label(None)
            return
        fp_id = self._cmb_floorplans.itemData(idx)
        fp = next((f for f in self._valid_floorplans if f.get("id") == fp_id), None)
        if fp:
            self._open_floorplan(fp)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_new_floorplan(self):
        if settings_storage.get_read_only_mode():
            return
        dlg = FloorplanDialog(parent=self, data=self._data)
        if dlg.exec():
            result = dlg.get_result()
            if not result:
                return
            self._reload_floorplan_list()
            # Selecteer nieuw grondplan in DDL
            for i in range(self._cmb_floorplans.count()):
                if self._cmb_floorplans.itemData(i) == result.get("id"):
                    self._cmb_floorplans.setCurrentIndex(i)
                    break
            self.statusBar().showMessage(t("msg_floorplan_created"), 4000)

    def _on_manage_floorplans(self):
        """Open beheerdialoog — verwijderen, site/locatie/naam wijzigen."""
        dlg = FloorplanManageDialog(parent=self, data=self._data)
        dlg.exec()
        if dlg.has_changes():
            # Bewaar huidig geselecteerde fp_id om na reload te herselecteren
            current_id = None
            idx = self._cmb_floorplans.currentIndex()
            if idx >= 0:
                current_id = self._cmb_floorplans.itemData(idx)
            self._reload_floorplan_list()
            # Herselecteer indien nog aanwezig
            if current_id:
                for i in range(self._cmb_floorplans.count()):
                    if self._cmb_floorplans.itemData(i) == current_id:
                        self._cmb_floorplans.setCurrentIndex(i)
                        break

    # ------------------------------------------------------------------
    # View host
    # ------------------------------------------------------------------

    def _open_floorplan(self, floorplan: dict):
        self._clear_host()
        view = FloorplanView(floorplan=floorplan, data=self._data, parent=self._host)
        self._host_layout.addWidget(view)
        self._current_view = view
        self._update_info_label(floorplan)

    def _clear_host(self):
        while self._host_layout.count():
            item = self._host_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self._current_view = None

    def _show_placeholder(self):
        lbl = QLabel(t("msg_floorplan_not_found"))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setObjectName("secondary")
        self._host_layout.addWidget(lbl)

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------

    def _apply_read_only_mode(self):
        read_only = settings_storage.get_read_only_mode()
        self._btn_new.setEnabled(not read_only)

    def _update_info_label(self, floorplan: dict | None = None):
        if not floorplan:
            self._lbl_info.setText("-")
            return
        site_name = self._find_site_name(floorplan.get("site_id"))
        loc_key   = floorplan.get("outlet_location_key", "-")
        lang      = get_language()
        loc_label = loc_key
        for loc in settings_storage.load_outlet_locations():
            if loc.get("key") == loc_key:
                loc_label = loc.get(f"label_{lang}") or loc.get("label_nl") or loc_key
                break
        svg_name = floorplan.get("svg_file", "-")
        self._lbl_info.setText(
            f"{t('label_site')}: {site_name}  ·  "
            f"{t('settings_tab_outlet_locations')}: {loc_label}  ·  "
            f"{t('label_floorplan_svg')}: {svg_name}"
        )

    # ------------------------------------------------------------------
    # Data lookup
    # ------------------------------------------------------------------

    def _find_site_name(self, site_id: str | None) -> str:
        if not site_id:
            return "-"
        for site in self._data.get("sites", []):
            if site.get("id") == site_id:
                return site.get("name", site_id)
        return site_id


def run():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    try:
        lang = settings_storage.load_settings().get("language", "nl")
        set_language(lang)
    except Exception:
        set_language("nl")
    window = FloorplanTestWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()