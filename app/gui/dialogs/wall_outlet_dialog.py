# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/wall_outlet_dialog.py
# Role:    Wandpunt aanmaken en bewerken — incl. eindapparaat beheer
# Version: 1.7.0
# Author:  Barremans
# Changes: 1.7.0 — F6: sort_id veld toegevoegd — numerieke sorteervolgorde per locatiegroep
#                  Optioneel veld, niet ingevuld = 0 (achteraan bij sortering)
#          1.6.0 — Locatie gewijzigd van vrij tekstveld naar configureerbare keuzelijst
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QTextEdit, QPushButton,
    QMessageBox, QFrame, QLabel, QSpinBox
)
from app.helpers.i18n import t
from app.services.vlan_service import load_vlans
from app.gui.dialogs.device_dialog import _bind_uppercase
from app.helpers.settings_storage import load_outlet_locations


def _build_vlan_ddl(current_vlan=None) -> QComboBox:
    ddl = QComboBox()
    ddl.addItem("— geen VLAN —", None)
    for v in load_vlans():
        label = f"VLAN {v['id']}"
        if v.get("name"):
            label += f"  —  {v['name']}"
        ddl.addItem(label, v["id"])
    if current_vlan is not None:
        for i in range(ddl.count()):
            if ddl.itemData(i) == int(current_vlan):
                ddl.setCurrentIndex(i)
                break
    return ddl


class WallOutletDialog(QDialog):
    """
    Dialog voor wandpunt aanmaken / bewerken.
    Bevat volledige inline eindapparaat-beheer + VLAN toewijzing.
    """

    def __init__(self, parent=None, outlet: dict = None,
                 room_id: str = "", endpoints: list = None,
                 existing_outlets: list = None):
        super().__init__(parent)
        self._outlet           = outlet or {}
        self._room_id          = room_id
        self._endpoints_data   = [dict(ep) for ep in (endpoints or [])]
        self._existing_outlets = existing_outlets or []
        self._result           = None
        self.setWindowTitle(
            t("title_edit_outlet") if self._outlet else t("title_new_outlet")
        )
        self.setMinimumWidth(440)
        self.setModal(True)
        self._build()
        if self._outlet:
            self._populate()

    # ------------------------------------------------------------------
    # UI bouwen
    # ------------------------------------------------------------------

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)
        self._name     = QLineEdit()
        _bind_uppercase(self._name)

        # Locatie — keuzelijst uit settings (configureerbaar)
        self._ddl_location = QComboBox()
        self._ddl_location.addItem("— " + t("label_location") + " —", "")
        for loc in load_outlet_locations():
            from app.helpers.i18n import get_language
            lang  = get_language()
            label = loc.get(f"label_{lang}", loc.get("label_nl", loc["key"]))
            self._ddl_location.addItem(label, loc["key"])

        self._notes    = QTextEdit()
        self._notes.setFixedHeight(56)

        # Sorteervolgorde — numeriek, optioneel (0 = niet ingesteld → achteraan)
        self._sort_id = QSpinBox()
        self._sort_id.setRange(0, 9999)
        self._sort_id.setSpecialValueText("—")   # 0 toont als "—"
        self._sort_id.setToolTip("Sorteervolgorde binnen locatiegroep (0 = achteraan)")

        # VLAN DDL
        self._ddl_vlan = _build_vlan_ddl()

        form.addRow(t("label_name")     + " *:", self._name)
        form.addRow(t("label_location") + ":",   self._ddl_location)
        form.addRow("VLAN:",                     self._ddl_vlan)
        form.addRow("Volgorde:",                 self._sort_id)
        form.addRow(t("label_notes")    + ":",   self._notes)
        layout.addLayout(form)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        ep_header = QLabel(t("label_endpoint") + ":")
        layout.addWidget(ep_header)

        ep_row = QHBoxLayout()
        self._ddl_ep = QComboBox()
        self._ddl_ep.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._ddl_ep.setMinimumWidth(180)
        self._ddl_ep.currentIndexChanged.connect(self._on_ep_selection_changed)
        ep_row.addWidget(self._ddl_ep, stretch=1)

        self._btn_ep_new  = QPushButton("＋")
        self._btn_ep_new.setFixedWidth(34)
        self._btn_ep_new.setToolTip(t("btn_new_endpoint"))
        self._btn_ep_new.clicked.connect(self._on_new_endpoint)

        self._btn_ep_edit = QPushButton("✏")
        self._btn_ep_edit.setFixedWidth(34)
        self._btn_ep_edit.setToolTip(t("ctx_edit"))
        self._btn_ep_edit.clicked.connect(self._on_edit_endpoint)

        self._btn_ep_del  = QPushButton("🗑")
        self._btn_ep_del.setFixedWidth(34)
        self._btn_ep_del.setToolTip(t("ctx_delete"))
        self._btn_ep_del.clicked.connect(self._on_delete_endpoint)

        ep_row.addWidget(self._btn_ep_new)
        ep_row.addWidget(self._btn_ep_edit)
        ep_row.addWidget(self._btn_ep_del)
        layout.addLayout(ep_row)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep2)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton(t("btn_cancel"))
        btn_save   = QPushButton(t("btn_save"))
        btn_save.setDefault(True)
        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

        self._refresh_ddl()
        self._update_ep_buttons()

    # ------------------------------------------------------------------
    # DDL eindapparaten
    # ------------------------------------------------------------------

    def _refresh_ddl(self, select_id: str = None):
        from app.helpers import settings_storage
        from app.helpers.i18n import get_language
        lang        = get_language()
        ep_type_map = {
            et.get("key", ""): et.get(f"label_{lang}", et.get("label_nl", ""))
            for et in settings_storage.load_endpoint_types()
        }
        current_id = select_id if select_id is not None else (self._ddl_ep.currentData() or "")
        self._ddl_ep.blockSignals(True)
        self._ddl_ep.clear()
        self._ddl_ep.addItem(f"— {t('label_endpoint')} —", "")
        for ep in self._endpoints_data:
            name    = ep.get("name", ep.get("id", "?"))
            ep_type = ep.get("type", "")
            label   = f"{name}  ({ep_type_map[ep_type]})" if ep_type in ep_type_map else name
            self._ddl_ep.addItem(label, ep.get("id", ""))
        self._ddl_ep.blockSignals(False)
        idx = self._ddl_ep.findData(current_id) if current_id else 0
        self._ddl_ep.setCurrentIndex(max(0, idx))
        self._update_ep_buttons()

    def _update_ep_buttons(self):
        has = bool(self._ddl_ep.currentData())
        self._btn_ep_edit.setEnabled(has)
        self._btn_ep_del.setEnabled(has)

    def _on_ep_selection_changed(self, _):
        self._update_ep_buttons()

    # ------------------------------------------------------------------
    # Eindapparaat CRUD
    # ------------------------------------------------------------------

    def _on_new_endpoint(self):
        from app.gui.dialogs.endpoint_dialog import EndpointDialog
        import time
        dlg = EndpointDialog(parent=self)
        if dlg.exec() and dlg.get_result():
            ep = dlg.get_result()
            if not ep.get("id"):
                ep["id"] = f"ep_{int(time.time() * 1000) % 1_000_000}"
            self._endpoints_data.append(ep)
            self._refresh_ddl(select_id=ep["id"])

    def _on_edit_endpoint(self):
        from app.gui.dialogs.endpoint_dialog import EndpointDialog
        ep_id = self._ddl_ep.currentData()
        if not ep_id:
            return
        ep = next((e for e in self._endpoints_data if e.get("id") == ep_id), None)
        if not ep:
            return
        dlg = EndpointDialog(parent=self, endpoint=ep)
        if dlg.exec() and dlg.get_result():
            ep.update(dlg.get_result())
            self._refresh_ddl(select_id=ep_id)

    def _on_delete_endpoint(self):
        ep_id = self._ddl_ep.currentData()
        if not ep_id:
            return
        ep = next((e for e in self._endpoints_data if e.get("id") == ep_id), None)
        if not ep:
            return
        reply = QMessageBox.question(
            self, t("menu_delete"),
            f"{t('msg_confirm_delete')}\n\n{ep.get('name', ep_id)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._endpoints_data = [e for e in self._endpoints_data if e.get("id") != ep_id]
        self._refresh_ddl(select_id="")

    # ------------------------------------------------------------------
    # Invullen bij bewerken
    # ------------------------------------------------------------------

    def _populate(self):
        self._name.setText(self._outlet.get("name", ""))

        # Locatie DDL instellen
        loc_key = self._outlet.get("location_description", "")
        idx = self._ddl_location.findData(loc_key)
        if idx >= 0:
            self._ddl_location.setCurrentIndex(idx)
        self._notes.setPlainText(self._outlet.get("notes", ""))
        self._sort_id.setValue(int(self._outlet.get("sort_id", 0)))

        # VLAN
        current_vlan = self._outlet.get("vlan")
        if current_vlan is not None:
            for i in range(self._ddl_vlan.count()):
                if self._ddl_vlan.itemData(i) == int(current_vlan):
                    self._ddl_vlan.setCurrentIndex(i)
                    break

        ep_id = self._outlet.get("endpoint_id", "")
        if ep_id:
            idx = self._ddl_ep.findData(ep_id)
            if idx >= 0:
                self._ddl_ep.setCurrentIndex(idx)
        self._update_ep_buttons()

    # ------------------------------------------------------------------
    # Opslaan
    # ------------------------------------------------------------------

    def _on_save(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, t("label_wall_outlet"), t("err_field_required"))
            return

        current_id = self._outlet.get("id", "")
        duplicate  = next(
            (wo for wo in self._existing_outlets
             if wo.get("name", "").strip().lower() == name.lower()
             and wo.get("id", "") != current_id),
            None
        )
        if duplicate:
            QMessageBox.warning(
                self, t("label_wall_outlet"),
                t("err_outlet_duplicate_name").replace("{name}", name),
            )
            self._name.setFocus()
            self._name.selectAll()
            return

        vlan_val = self._ddl_vlan.currentData()

        self._result = {
            "id":                   self._outlet.get("id", ""),
            "room_id":              self._room_id or self._outlet.get("room_id", ""),
            "name":                 name,
            "location_description": self._ddl_location.currentData() or "",
            "endpoint_id":          self._ddl_ep.currentData() or "",
            "notes":                self._notes.toPlainText().strip(),
            "sort_id":              self._sort_id.value(),
        }
        if vlan_val is not None:
            self._result["vlan"] = int(vlan_val)

        self.accept()

    # ------------------------------------------------------------------
    # Publieke methodes
    # ------------------------------------------------------------------

    def get_result(self) -> dict | None:
        return self._result

    def get_vlan(self) -> int | None:
        """Geeft het geselecteerde VLAN ID terug (of None)."""
        return self._ddl_vlan.currentData()

    def get_endpoints_result(self) -> list:
        return self._endpoints_data