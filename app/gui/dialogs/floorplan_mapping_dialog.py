# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/floorplan_mapping_dialog.py
# Role:    Dialoog — SVG punt koppelen aan bestaand wandpunt
# Version: 1.1.0
# Author:  Barremans
# Changes: 1.1.0 — bugfix: wandpunten nu ophalen op site-niveau i.p.v. enkel
#                           floorplan room_id
#                   combo toont nu "RUIMTE — WANDPUNT"
#                   bestaande mapping wordt vooraf geselecteerd
#                   correcte ruimte van het wandpunt wordt dus gebruikt
#          1.0.0 — Initiële versie
#                   kiest wandpunt binnen site/ruimte context
#                   toont SVG punt
#                   slaat koppeling op via floorplan_service
#                   read-only compatibel
#                   i18n via t()
# =============================================================================

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.helpers import settings_storage
from app.helpers.i18n import t
from app.services import floorplan_service


class FloorplanMappingDialog(QDialog):
    """
    Koppel één SVG punt aan één bestaand wandpunt.

    Belangrijk:
    - Een floorplan hangt aan een site + room
    - Maar een wandpunt moet correct getoond worden met zijn EIGEN ruimte
    - Daarom worden alle wandpunten binnen de site opgelijst, met label:
        "RUIMTE — WANDPUNT"
    """

    def __init__(
        self,
        parent=None,
        data: dict | None = None,
        floorplan: dict | None = None,
        svg_point: str = "",
    ):
        super().__init__(parent)

        self._data = data or {}
        self._floorplan = floorplan or {}
        self._svg_point = svg_point
        self._result: dict | None = None

        self._build_ui()
        self._populate_outlets()
        self._apply_current_mapping_selection()
        self._apply_read_only_mode()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.setWindowTitle(t("floorplan_mapping_title"))
        self.setModal(True)
        self.setMinimumWidth(520)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)

        self._lbl_svg_point = QLabel(self._svg_point or "-")
        form.addRow(f"{t('floorplan_mapping_svg_point')}:", self._lbl_svg_point)

        self._cmb_outlet = QComboBox()
        form.addRow(f"{t('floorplan_mapping_outlet')}:", self._cmb_outlet)

        root.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self._btn_save = QPushButton(t("floorplan_mapping_assign"))
        self._btn_save.clicked.connect(self._on_save)

        self._btn_cancel = QPushButton(t("btn_cancel"))
        self._btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(self._btn_save)
        btn_row.addWidget(self._btn_cancel)

        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------

    def _populate_outlets(self):
        """
        Bugfix:
        Niet beperken tot floorplan.room_id.
        We tonen alle wandpunten binnen de site, met hun echte ruimte.
        """
        self._cmb_outlet.clear()

        site_id = self._floorplan.get("site_id")
        if not site_id:
            return

        for site in self._data.get("sites", []):
            if site.get("id") != site_id:
                continue

            for room in site.get("rooms", []):
                room_name = room.get("name", "?")

                for outlet in room.get("wall_outlets", []):
                    outlet_id = outlet.get("id")
                    outlet_name = outlet.get("name", outlet_id or "?")

                    label = f"{room_name} — {outlet_name}"
                    self._cmb_outlet.addItem(label, outlet_id)

            break

    def _apply_current_mapping_selection(self):
        """
        Selecteer bestaande mapping vooraf als die al bestaat.
        """
        floorplan_id = self._floorplan.get("id")
        if not floorplan_id or not self._svg_point:
            return

        mapped_outlet_id = floorplan_service.get_mapping(floorplan_id, self._svg_point)
        if not mapped_outlet_id:
            return

        for i in range(self._cmb_outlet.count()):
            if self._cmb_outlet.itemData(i) == mapped_outlet_id:
                self._cmb_outlet.setCurrentIndex(i)
                return

    def _apply_read_only_mode(self):
        read_only = settings_storage.get_read_only_mode()
        if read_only:
            self._btn_save.setEnabled(False)
            self._cmb_outlet.setEnabled(False)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _on_save(self):
        if settings_storage.get_read_only_mode():
            self.reject()
            return

        floorplan_id = self._floorplan.get("id")
        outlet_id = self._cmb_outlet.currentData()

        if not floorplan_id or not self._svg_point or not outlet_id:
            QMessageBox.warning(self, self.windowTitle(), t("err_no_selection"))
            return

        floorplan_service.set_mapping(
            floorplan_id=floorplan_id,
            svg_point=self._svg_point,
            outlet_id=outlet_id,
        )

        self._result = {
            "floorplan_id": floorplan_id,
            "svg_point": self._svg_point,
            "outlet_id": outlet_id,
        }
        self.accept()

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def get_result(self) -> dict | None:
        return self._result