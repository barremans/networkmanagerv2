# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/wall_outlet_dialog.py
# Role:    Wandpunt aanmaken en bewerken — incl. eindapparaat beheer
# Version: 1.2.0
# Author:  Barremans
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QTextEdit, QPushButton,
    QMessageBox, QFrame, QLabel
)
from app.helpers.i18n import t


class WallOutletDialog(QDialog):
    """
    Dialog voor wandpunt aanmaken / bewerken.
    Bevat volledige inline eindapparaat-beheer:
      - Nieuw eindapparaat aanmaken
      - Geselecteerd eindapparaat bewerken
      - Geselecteerd eindapparaat verwijderen
    Wijzigingen aan eindapparaten zijn beschikbaar via get_endpoints_result().
    """

    def __init__(self, parent=None, outlet: dict = None,
                 room_id: str = "", endpoints: list = None):
        super().__init__(parent)
        self._outlet         = outlet or {}
        self._room_id        = room_id
        self._endpoints_data = [dict(ep) for ep in (endpoints or [])]
        self._result         = None
        self.setWindowTitle(
            t("title_edit_outlet") if self._outlet else t("title_new_outlet")
        )
        self.setMinimumWidth(420)
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

        # Wandpunt velden
        form = QFormLayout()
        form.setSpacing(8)
        self._name     = QLineEdit()
        self._location = QLineEdit()
        self._notes    = QTextEdit()
        self._notes.setFixedHeight(56)
        form.addRow(t("label_name")     + " *:", self._name)
        form.addRow(t("label_location") + ":",   self._location)
        form.addRow(t("label_notes")    + ":",   self._notes)
        layout.addLayout(form)

        # Scheiding
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # Eindapparaat sectie header
        ep_header = QLabel(t("label_endpoint") + ":")
        layout.addWidget(ep_header)

        # DDL + beheer knoppen
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

        # Scheiding
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep2)

        # Knoppen
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
        """Herbouw de eindapparaat-DDL. Behoudt huidige selectie tenzij select_id opgegeven."""
        from app.helpers import settings_storage
        from app.helpers.i18n import get_language
        lang       = get_language()
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
        self._location.setText(self._outlet.get("location_description", ""))
        self._notes.setPlainText(self._outlet.get("notes", ""))
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
        self._result = {
            "id":                   self._outlet.get("id", ""),
            "room_id":              self._room_id or self._outlet.get("room_id", ""),
            "name":                 name,
            "location_description": self._location.text().strip(),
            "endpoint_id":          self._ddl_ep.currentData() or "",
            "notes":                self._notes.toPlainText().strip(),
        }
        self.accept()

    # ------------------------------------------------------------------
    # Publieke methodes
    # ------------------------------------------------------------------

    def get_result(self) -> dict | None:
        return self._result

    def get_endpoints_result(self) -> list:
        """
        Geeft de gewijzigde lijst van eindapparaten terug.
        main_window moet self._data['endpoints'] synchroniseren na sluiten.
        """
        return self._endpoints_data