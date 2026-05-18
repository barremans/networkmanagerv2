# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/floorplan_mapping_dialog.py
# Role:    Dialoog — SVG punt koppelen aan wandpunt of eindapparaat
# Version: 1.2.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie
#          1.1.0 — bugfix: wandpunten nu ophalen op site-niveau i.p.v. enkel
#                           floorplan room_id
#                   combo toont nu "RUIMTE — WANDPUNT"
#                   bestaande mapping wordt vooraf geselecteerd
#          1.2.0 — Eindapparaat koppeling: type-keuze via tabs
#                   Tab 1: Wandpunt (bestaand gedrag ongewijzigd)
#                   Tab 2: Eindapparaat (nieuw)
#                   Bestaande ep:-mapping wordt correct voorgeselecteerd
#                   Opslaat als "ep:ep_xxx" prefix voor eindapparaten
# =============================================================================

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.helpers import settings_storage
from app.helpers.i18n import t
from app.services import floorplan_service


class FloorplanMappingDialog(QDialog):
    """
    Koppel één SVG punt aan één bestaand wandpunt of eindapparaat.

    Type-keuze via tabs:
    - Tab 1: Wandpunt  (bestaand gedrag)
    - Tab 2: Eindapparaat (nieuw v1.2.0)

    Resultaat opgeslagen als:
    - Wandpunt:     "outlet_xxx"
    - Eindapparaat: "ep:ep_xxx"
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
        self._populate_endpoints()
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

        # SVG punt label
        form_top = QFormLayout()
        form_top.setContentsMargins(0, 0, 0, 0)
        form_top.setSpacing(8)
        self._lbl_svg_point = QLabel(self._svg_point or "-")
        form_top.addRow(f"{t('floorplan_mapping_svg_point')}:", self._lbl_svg_point)
        root.addLayout(form_top)

        # Tabs: wandpunt / eindapparaat
        self._tabs = QTabWidget()

        # Tab 1 — Wandpunt
        tab_outlet = QWidget()
        outlet_layout = QFormLayout(tab_outlet)
        outlet_layout.setContentsMargins(8, 8, 8, 8)
        outlet_layout.setSpacing(8)
        self._cmb_outlet = QComboBox()
        outlet_layout.addRow(f"{t('floorplan_mapping_outlet')}:", self._cmb_outlet)
        self._tabs.addTab(tab_outlet, t("label_wall_outlet"))

        # Tab 2 — Eindapparaat
        tab_ep = QWidget()
        ep_layout = QFormLayout(tab_ep)
        ep_layout.setContentsMargins(8, 8, 8, 8)
        ep_layout.setSpacing(8)
        self._cmb_endpoint = QComboBox()
        ep_layout.addRow(f"{t('label_endpoint')}:", self._cmb_endpoint)
        self._tabs.addTab(tab_ep, t("label_endpoint"))

        root.addWidget(self._tabs)

        # Knoppen
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
    # Populeren
    # ------------------------------------------------------------------

    def _populate_outlets(self):
        """Alle wandpunten binnen de site, met label 'RUIMTE — WANDPUNT'."""
        self._cmb_outlet.clear()
        self._cmb_outlet.addItem(f"— {t('label_wall_outlet')} —", "")

        site_id = self._floorplan.get("site_id")
        if not site_id:
            return

        for site in self._data.get("sites", []):
            if site.get("id") != site_id:
                continue
            for room in site.get("rooms", []):
                room_name = room.get("name", "?")
                for outlet in room.get("wall_outlets", []):
                    outlet_id   = outlet.get("id")
                    outlet_name = outlet.get("name", outlet_id or "?")
                    self._cmb_outlet.addItem(
                        f"{room_name} — {outlet_name}", outlet_id
                    )
            break

    def _populate_endpoints(self):
        """Alle eindapparaten gesorteerd op naam, met locatie als hint."""
        self._cmb_endpoint.clear()
        self._cmb_endpoint.addItem(f"— {t('label_endpoint')} —", "")

        endpoints = sorted(
            self._data.get("endpoints", []),
            key=lambda e: e.get("name", "")
        )
        for ep in endpoints:
            ep_id   = ep.get("id")
            ep_name = ep.get("name", ep_id or "?")
            loc     = ep.get("location", "")
            label   = f"{ep_name}  —  {loc}" if loc else ep_name
            self._cmb_endpoint.addItem(label, ep_id)

    def _apply_current_mapping_selection(self):
        """Vooraf selecteren op basis van bestaande mapping."""
        floorplan_id = self._floorplan.get("id")
        if not floorplan_id or not self._svg_point:
            return

        mapped_val = floorplan_service.get_mapping(floorplan_id, self._svg_point)
        if not mapped_val:
            return

        if mapped_val.startswith("ep:"):
            # Endpoint → tab 2 activeren
            ep_id = mapped_val[3:]
            for i in range(self._cmb_endpoint.count()):
                if self._cmb_endpoint.itemData(i) == ep_id:
                    self._cmb_endpoint.setCurrentIndex(i)
                    break
            self._tabs.setCurrentIndex(1)
        else:
            # Wandpunt → tab 1
            for i in range(self._cmb_outlet.count()):
                if self._cmb_outlet.itemData(i) == mapped_val:
                    self._cmb_outlet.setCurrentIndex(i)
                    break
            self._tabs.setCurrentIndex(0)

    def _apply_read_only_mode(self):
        read_only = settings_storage.get_read_only_mode()
        if read_only:
            self._btn_save.setEnabled(False)
            self._cmb_outlet.setEnabled(False)
            self._cmb_endpoint.setEnabled(False)

    # ------------------------------------------------------------------
    # Opslaan
    # ------------------------------------------------------------------

    def _on_save(self):
        if settings_storage.get_read_only_mode():
            self.reject()
            return

        floorplan_id = self._floorplan.get("id")
        if not floorplan_id or not self._svg_point:
            QMessageBox.warning(self, self.windowTitle(), t("err_no_selection"))
            return

        tab_idx = self._tabs.currentIndex()

        if tab_idx == 0:
            # Wandpunt
            outlet_id = self._cmb_outlet.currentData()
            if not outlet_id:
                QMessageBox.warning(self, self.windowTitle(), t("err_no_selection"))
                return
            mapping_val = outlet_id
        else:
            # Eindapparaat
            ep_id = self._cmb_endpoint.currentData()
            if not ep_id:
                QMessageBox.warning(self, self.windowTitle(), t("err_no_selection"))
                return
            mapping_val = f"ep:{ep_id}"

        floorplan_service.set_mapping(
            floorplan_id=floorplan_id,
            svg_point=self._svg_point,
            outlet_id=mapping_val,
        )

        self._result = {
            "floorplan_id": floorplan_id,
            "svg_point":    self._svg_point,
            "mapping_val":  mapping_val,
        }
        self.accept()

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def get_result(self) -> dict | None:
        return self._result