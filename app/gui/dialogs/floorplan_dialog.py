# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/floorplan_dialog.py
# Role:    Dialoog — nieuw grondplan koppelen aan site en wandpunt locatie
# Version: 1.4.0
# Author:  Barremans
# Changes: 1.4.0 — bugfix: keuze gewijzigd van rooms naar Wandpunt locaties
#                   gebruikt settings_storage.load_outlet_locations()
#                   slaat outlet_location_key op i.p.v. room_id
#                   bestaande floorplan-check nu op site + locatie
#          1.3.0 — SVG detectie- en waarschuwingsteksten volledig via i18n t()
#                   geen hardcoded NL tekst meer in de dialoog
#          1.2.0 — SVG validatie via floorplan_svg_service toegevoegd
#                   waarschuwing indien geen detecteerbare puntlabels gevonden
#                   extra info in dialoog over aantal gedetecteerde punten
#          1.1.0 — gebruikt floorplan_svg last-folder key uit settings_storage
#                   sluit aan op floorplan_service v1.1.0
#                   kleine validatieverfijningen en veiligere preselectie
#          1.0.0 — Initiële versie
# =============================================================================

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.helpers import settings_storage
from app.helpers.i18n import t
from app.services import floorplan_service
from app.services import floorplan_svg_service


class FloorplanDialog(QDialog):
    """
    Dialoog voor het toevoegen van een nieuw grondplan.

    Nieuwe koppeling:
        site_id + outlet_location_key
    """

    def __init__(
        self,
        parent=None,
        data: dict | None = None,
        preselected_site_id: str | None = None,
        preselected_location_key: str | None = None,
    ):
        super().__init__(parent)

        self._data = data or {}
        self._result: dict | None = None

        self._preselected_site_id = preselected_site_id
        self._preselected_location_key = preselected_location_key

        self._detected_points: list[str] = []

        self._build_ui()
        self._populate_sites()
        self._populate_outlet_locations()
        self._apply_preselection()
        self._apply_read_only_mode()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.setWindowTitle(t("title_floorplan_new"))
        self.setModal(True)
        self.setMinimumWidth(560)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        info_lbl = QLabel(t("menu_floorplan_new"))
        info_lbl.setObjectName("secondary")
        root.addWidget(info_lbl)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)

        # SVG bestand
        svg_row = QHBoxLayout()
        svg_row.setContentsMargins(0, 0, 0, 0)
        svg_row.setSpacing(6)

        self._edit_svg = QLineEdit()
        self._edit_svg.setPlaceholderText(t("label_floorplan_svg"))
        self._edit_svg.setReadOnly(True)

        self._btn_browse = QPushButton(t("btn_browse"))
        self._btn_browse.clicked.connect(self._browse_svg)

        svg_row.addWidget(self._edit_svg, 1)
        svg_row.addWidget(self._btn_browse)

        form.addRow(f"{t('label_floorplan_svg')}:", self._wrap_layout(svg_row))

        # Detectie-info
        self._lbl_detect_info = QLabel(t("msg_floorplan_detected_zero"))
        self._lbl_detect_info.setObjectName("secondary")
        form.addRow("", self._lbl_detect_info)

        # Site
        self._cmb_site = QComboBox()
        form.addRow(f"{t('label_floorplan_site')}:", self._cmb_site)

        # Wandpunt locaties
        self._cmb_location = QComboBox()
        form.addRow(f"{t('settings_tab_outlet_locations')}:", self._cmb_location)

        root.addLayout(form)

        # Knoppen
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self._btn_save = QPushButton(t("btn_save"))
        self._btn_save.clicked.connect(self._on_save)

        self._btn_cancel = QPushButton(t("btn_cancel"))
        self._btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(self._btn_save)
        btn_row.addWidget(self._btn_cancel)

        root.addLayout(btn_row)

    def _wrap_layout(self, layout) -> QWidget:
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    # ------------------------------------------------------------------
    # Init data
    # ------------------------------------------------------------------

    def _populate_sites(self):
        self._cmb_site.clear()

        for site in self._data.get("sites", []):
            site_name = site.get("name", "?")
            site_id = site.get("id")
            self._cmb_site.addItem(site_name, site_id)

    def _populate_outlet_locations(self):
        self._cmb_location.clear()

        language = settings_storage.load_settings().get("language", "nl")
        for loc in settings_storage.load_outlet_locations():
            key = loc.get("key", "")
            label = loc.get(f"label_{language}") or loc.get("label_nl") or key
            self._cmb_location.addItem(label, key)

    def _apply_preselection(self):
        if self._preselected_site_id:
            idx = self._find_combo_index_by_data(self._cmb_site, self._preselected_site_id)
            if idx >= 0:
                self._cmb_site.setCurrentIndex(idx)

        if self._preselected_location_key:
            idx = self._find_combo_index_by_data(self._cmb_location, self._preselected_location_key)
            if idx >= 0:
                self._cmb_location.setCurrentIndex(idx)

    def _apply_read_only_mode(self):
        read_only = settings_storage.get_read_only_mode()
        if read_only:
            self._btn_browse.setEnabled(False)
            self._btn_save.setEnabled(False)
            self._cmb_site.setEnabled(False)
            self._cmb_location.setEnabled(False)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _browse_svg(self):
        last_folder = settings_storage.get_last_folder("floorplan_svg") or ""

        path, _ = QFileDialog.getOpenFileName(
            self,
            t("label_floorplan_svg"),
            last_folder,
            "SVG (*.svg)"
        )

        if not path:
            return

        self._edit_svg.setText(path)
        settings_storage.set_last_folder("floorplan_svg", str(Path(path).parent))
        self._analyze_svg(path)

    def _on_save(self):
        if settings_storage.get_read_only_mode():
            self.reject()
            return

        svg_path = self._edit_svg.text().strip()
        site_id = self._current_site_id()
        outlet_location_key = self._current_location_key()

        if not svg_path:
            self._show_error(t("err_file_not_found"))
            return

        svg_file = Path(svg_path)
        if not svg_file.exists() or not svg_file.is_file():
            self._show_error(t("err_file_not_found"))
            return

        if svg_file.suffix.lower() != ".svg":
            self._show_error(t("err_file_not_found"))
            return

        if not site_id:
            self._show_error(t("err_select_site_for_room"))
            return

        if not outlet_location_key:
            self._show_error(t("err_no_selection"))
            return

        existing = floorplan_service.get_floorplan_for_location(
            site_id=site_id,
            outlet_location_key=outlet_location_key,
        )
        if existing:
            self._show_error(t("msg_floorplan_exists"))
            return

        if not self._detected_points:
            self._analyze_svg(svg_path, show_warning=False)

        created = floorplan_service.create_floorplan(
            site_id=site_id,
            outlet_location_key=outlet_location_key,
            svg_source=svg_path,
        )

        self._result = created
        self.accept()

    # ------------------------------------------------------------------
    # SVG analyse
    # ------------------------------------------------------------------

    def _analyze_svg(self, svg_path: str, show_warning: bool = True):
        self._detected_points = floorplan_svg_service.detect_point_labels(svg_path)

        if self._detected_points:
            preview = ", ".join(self._detected_points[:8])
            extra = ""
            if len(self._detected_points) > 8:
                extra = " ..."
            self._lbl_detect_info.setText(
                t("msg_floorplan_detected_points").format(
                    count=len(self._detected_points),
                    preview=preview,
                    extra=extra,
                )
            )
        else:
            self._lbl_detect_info.setText(t("msg_floorplan_detected_zero"))

            if show_warning:
                QMessageBox.information(
                    self,
                    self.windowTitle(),
                    t("msg_floorplan_no_points_warning"),
                )

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def get_result(self) -> dict | None:
        return self._result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _current_site_id(self) -> str | None:
        return self._cmb_site.currentData()

    def _current_location_key(self) -> str | None:
        return self._cmb_location.currentData()

    def _find_combo_index_by_data(self, combo: QComboBox, value: str) -> int:
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                return i
        return -1

    def _show_error(self, message: str):
        QMessageBox.warning(self, self.windowTitle(), message)