# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/wall_outlet_dialog.py
# Role:    Wandpunt aanmaken en bewerken — incl. eindapparaat beheer
# Version: 1.11.0
# Author:  Barremans
# Changes: 1.11.0 — Locatie en VLAN: QComboBox vervangen door QLineEdit +
#                   QListWidget met real-time zoekfilter
#          1.10.0 — Eindapparaat DDL vervangen door zoekbalk + QListWidget
#                   Zoeken op naam en type, directe selectie via klik
#                   ＋/✏/🗑 knoppen blijven behouden naast zoekbalk
#          1.9.0  — Ruimte DDL: wandpunt verplaatsen naar andere ruimte
#          1.8.0  — Bug fix: duplicate check naam + wandlocatie
#          1.7.0 — F6: sort_id veld toegevoegd — numerieke sorteervolgorde per locatiegroep
#                  Optioneel veld, niet ingevuld = 0 (achteraan bij sortering)
#          1.6.0 — Locatie gewijzigd van vrij tekstveld naar configureerbare keuzelijst
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QTextEdit, QPushButton,
    QMessageBox, QFrame, QLabel, QSpinBox,
    QListWidget, QListWidgetItem, QWidget
)
from PySide6.QtCore import Qt
from app.helpers.i18n import t
from app.services.vlan_service import load_vlans
from app.gui.dialogs.device_dialog import _bind_uppercase
from app.helpers.settings_storage import load_outlet_locations


class WallOutletDialog(QDialog):
    """
    Dialog voor wandpunt aanmaken / bewerken.
    Bevat volledige inline eindapparaat-beheer + VLAN toewijzing.
    """

    def __init__(self, parent=None, outlet: dict = None,
                 room_id: str = "", endpoints: list = None,
                 existing_outlets: list = None, data: dict = None):
        super().__init__(parent)
        self._outlet           = outlet or {}
        self._room_id          = room_id
        self._data             = data or {}
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

        # Ruimte DDL (1.9.0)
        # Zichtbaar bij bewerken (verplaatsen) + bij nieuw zonder room_id
        self._ddl_room = QComboBox()
        self._ddl_room.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._ddl_room.setMinimumWidth(300)
        self._show_room_ddl = bool(self._outlet) or not self._room_id
        if self._show_room_ddl:
            self._ddl_room.addItem("-- " + t("label_room") + " --", "")
            for _site in self._data.get("sites", []):
                for _room in _site.get("rooms", []):
                    lbl = f"{_site['name']}  /  {_room['name']}"
                    self._ddl_room.addItem(lbl, _room["id"])

        # Locatie — zoekbaar (v1.11.0)
        loc_widget = QWidget()
        loc_layout = QVBoxLayout(loc_widget)
        loc_layout.setContentsMargins(0, 0, 0, 0)
        loc_layout.setSpacing(3)

        self._search_location = QLineEdit()
        self._search_location.setPlaceholderText(
            f"🔍  {t('search_placeholder_outlet_location')}"
        )
        self._search_location.setClearButtonEnabled(True)
        self._search_location.textChanged.connect(self._filter_locations)
        loc_layout.addWidget(self._search_location)

        self._list_location = QListWidget()
        self._list_location.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list_location.setFixedHeight(110)
        loc_layout.addWidget(self._list_location)

        # Vul locatielijst
        from app.helpers.i18n import get_language
        lang = get_language()
        none_item = QListWidgetItem("— " + t("label_location") + " —")
        none_item.setData(Qt.ItemDataRole.UserRole, "")
        self._list_location.addItem(none_item)
        for loc in load_outlet_locations():
            label = loc.get(f"label_{lang}", loc.get("label_nl", loc["key"]))
            item  = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, loc["key"])
            self._list_location.addItem(item)
        self._list_location.setCurrentRow(0)

        self._notes    = QTextEdit()
        self._notes.setFixedHeight(56)

        # Sorteervolgorde — numeriek, optioneel (0 = niet ingesteld → achteraan)
        self._sort_id = QSpinBox()
        self._sort_id.setRange(0, 9999)
        self._sort_id.setSpecialValueText("—")   # 0 toont als "—"
        self._sort_id.setToolTip("Sorteervolgorde binnen locatiegroep (0 = achteraan)")

        # VLAN — zoekbaar (v1.11.0)
        vlan_widget = QWidget()
        vlan_layout = QVBoxLayout(vlan_widget)
        vlan_layout.setContentsMargins(0, 0, 0, 0)
        vlan_layout.setSpacing(3)

        self._search_vlan = QLineEdit()
        self._search_vlan.setPlaceholderText("🔍  VLAN...")
        self._search_vlan.setClearButtonEnabled(True)
        self._search_vlan.textChanged.connect(self._filter_vlans)
        vlan_layout.addWidget(self._search_vlan)

        self._list_vlan = QListWidget()
        self._list_vlan.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list_vlan.setFixedHeight(110)
        vlan_layout.addWidget(self._list_vlan)

        # Vul VLAN lijst
        none_vlan = QListWidgetItem("— geen VLAN —")
        none_vlan.setData(Qt.ItemDataRole.UserRole, None)
        self._list_vlan.addItem(none_vlan)
        for v in load_vlans():
            label = f"VLAN {v['id']}"
            if v.get("name"):
                label += f"  —  {v['name']}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, v["id"])
            self._list_vlan.addItem(item)
        self._list_vlan.setCurrentRow(0)

        if self._show_room_ddl:
            form.addRow(t("label_room") + " *:", self._ddl_room)
        form.addRow(t("label_name")     + " *:", self._name)
        form.addRow(t("label_location") + ":",   loc_widget)
        form.addRow("VLAN:",                     vlan_widget)
        form.addRow("Volgorde:",                 self._sort_id)
        form.addRow(t("label_notes")    + ":",   self._notes)
        layout.addLayout(form)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        ep_header = QLabel(t("label_endpoint") + ":")
        layout.addWidget(ep_header)

        # 1.10.0 — Zoekbalk + knoppen op één rij
        ep_search_row = QHBoxLayout()
        self._ep_search = QLineEdit()
        self._ep_search.setPlaceholderText(f"🔍  {t('search_placeholder_endpoint')}")
        self._ep_search.textChanged.connect(self._filter_ep_list)
        ep_search_row.addWidget(self._ep_search, 1)

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

        ep_search_row.addWidget(self._btn_ep_new)
        ep_search_row.addWidget(self._btn_ep_edit)
        ep_search_row.addWidget(self._btn_ep_del)
        layout.addLayout(ep_search_row)

        # 1.10.0 — Lijst (vervangt DDL)
        self._list_ep = QListWidget()
        self._list_ep.setFixedHeight(130)
        self._list_ep.currentItemChanged.connect(self._on_ep_selection_changed)
        layout.addWidget(self._list_ep)

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

    # ------------------------------------------------------------------
    # Eindapparaat lijst beheer (1.10.0)
    # ------------------------------------------------------------------

    _EP_ID_ROLE = 256  # Qt.UserRole

    def _refresh_ddl(self, select_id: str = None):
        """1.10.0 — Herbouw de eindapparaat-lijst en selecteer select_id indien opgegeven."""
        from app.helpers import settings_storage
        from app.helpers.i18n import get_language
        lang        = get_language()
        ep_type_map = {
            et.get("key", ""): et.get(f"label_{lang}", et.get("label_nl", ""))
            for et in settings_storage.load_endpoint_types()
        }
        # Bewaar huidige selectie als select_id niet opgegeven
        current_id = select_id if select_id is not None else self._get_selected_ep_id()

        # Herstel zoekterm leeg zodat alle items zichtbaar zijn na CRUD
        self._ep_search.blockSignals(True)
        self._ep_search.clear()
        self._ep_search.blockSignals(False)

        self._ep_type_map = ep_type_map
        self._filter_ep_list("", select_id=current_id)

    def _filter_ep_list(self, text: str = "", select_id: str = None):
        """Filter de eindapparaat-lijst op zoekterm."""
        from app.helpers import settings_storage
        from app.helpers.i18n import get_language
        if not hasattr(self, "_ep_type_map"):
            lang = get_language()
            self._ep_type_map = {
                et.get("key", ""): et.get(f"label_{lang}", et.get("label_nl", ""))
                for et in settings_storage.load_endpoint_types()
            }

        q          = text.strip().lower()
        current_id = select_id if select_id is not None else self._get_selected_ep_id()

        self._list_ep.blockSignals(True)
        self._list_ep.clear()

        # Lege keuze — bovenaan
        none_item = QListWidgetItem(f"— {t('label_endpoint')} —")
        none_item.setData(self._EP_ID_ROLE, "")
        self._list_ep.addItem(none_item)

        for ep in sorted(self._endpoints_data, key=lambda e: e.get("name", "").lower()):
            name    = ep.get("name", ep.get("id", "?"))
            ep_type = ep.get("type", "")
            label   = f"{name}  ({self._ep_type_map[ep_type]})" if ep_type in self._ep_type_map else name
            if q and q not in label.lower():
                continue
            item = QListWidgetItem(label)
            item.setData(self._EP_ID_ROLE, ep.get("id", ""))
            self._list_ep.addItem(item)

        self._list_ep.blockSignals(False)

        # Herstel selectie
        self._select_ep_by_id(current_id or "")
        self._update_ep_buttons()

    def _get_selected_ep_id(self) -> str:
        item = self._list_ep.currentItem()
        if item:
            return item.data(self._EP_ID_ROLE) or ""
        return ""

    def _select_ep_by_id(self, ep_id: str):
        for i in range(self._list_ep.count()):
            if self._list_ep.item(i).data(self._EP_ID_ROLE) == ep_id:
                self._list_ep.setCurrentRow(i)
                return
        # Fallback: selecteer lege keuze
        if self._list_ep.count() > 0:
            self._list_ep.setCurrentRow(0)

    def _update_ep_buttons(self):
        has = bool(self._get_selected_ep_id())
        self._btn_ep_edit.setEnabled(has)
        self._btn_ep_del.setEnabled(has)

    def _on_ep_selection_changed(self, current, previous):
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
        ep_id = self._get_selected_ep_id()
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
        ep_id = self._get_selected_ep_id()
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
    # Zoekfilters locatie + VLAN — v1.11.0
    # ------------------------------------------------------------------

    def _filter_locations(self, text: str):
        needle = text.strip().lower()
        first  = None
        for i in range(self._list_location.count()):
            item  = self._list_location.item(i)
            match = (not needle) or (needle in item.text().lower())
            item.setHidden(not match)
            if match and first is None:
                first = i
        if first is not None:
            self._list_location.setCurrentRow(first)

    def _filter_vlans(self, text: str):
        needle = text.strip().lower()
        first  = None
        for i in range(self._list_vlan.count()):
            item  = self._list_vlan.item(i)
            match = (not needle) or (needle in item.text().lower())
            item.setHidden(not match)
            if match and first is None:
                first = i
        if first is not None:
            self._list_vlan.setCurrentRow(first)

    def _current_location_key(self) -> str:
        item = self._list_location.currentItem()
        if item and not item.isHidden():
            return item.data(Qt.ItemDataRole.UserRole) or ""
        return ""

    def _current_vlan_value(self):
        item = self._list_vlan.currentItem()
        if item and not item.isHidden():
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    # ------------------------------------------------------------------
    # Invullen bij bewerken
    # ------------------------------------------------------------------

    def _populate(self):
        self._name.setText(self._outlet.get("name", ""))

        # Ruimte DDL instellen (1.9.0)
        if self._show_room_ddl and self._room_id:
            idx = self._ddl_room.findData(self._room_id)
            if idx >= 0:
                self._ddl_room.setCurrentIndex(idx)

        # Locatie lijst instellen
        loc_key = self._outlet.get("location_description", "")
        for i in range(self._list_location.count()):
            if self._list_location.item(i).data(Qt.ItemDataRole.UserRole) == loc_key:
                self._list_location.setCurrentRow(i)
                break
        self._notes.setPlainText(self._outlet.get("notes", ""))
        self._sort_id.setValue(int(self._outlet.get("sort_id", 0)))

        # VLAN lijst instellen
        current_vlan = self._outlet.get("vlan")
        if current_vlan is not None:
            for i in range(self._list_vlan.count()):
                if self._list_vlan.item(i).data(Qt.ItemDataRole.UserRole) == int(current_vlan):
                    self._list_vlan.setCurrentRow(i)
                    break

        ep_id = self._outlet.get("endpoint_id", "")
        self._refresh_ddl(select_id=ep_id if ep_id else "")
        self._update_ep_buttons()

    # ------------------------------------------------------------------
    # Opslaan
    # ------------------------------------------------------------------

    def _on_save(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, t("label_wall_outlet"), t("err_field_required"))
            return

        # Ruimte bepalen (1.9.0): DDL of vaste room_id
        if self._show_room_ddl:
            effective_room_id = self._ddl_room.currentData() or ""
            if not effective_room_id:
                QMessageBox.warning(self, t("label_wall_outlet"), t("err_field_required"))
                self._ddl_room.setFocus()
                return
        else:
            effective_room_id = self._room_id

        current_id  = self._outlet.get("id", "")
        new_loc_key = self._current_location_key()
        # Duplicate check: gebruik data van de effectieve doelruimte (1.9.0)
        if self._data and effective_room_id:
            check_room = next(
                (r for s in self._data.get("sites", [])
                 for r in s.get("rooms", []) if r["id"] == effective_room_id),
                None
            )
            check_outlets = check_room.get("wall_outlets", []) if check_room else []
        else:
            check_outlets = self._existing_outlets
        duplicate   = next(
            (wo for wo in check_outlets
             if wo.get("name", "").strip().lower() == name.lower()
             and (wo.get("location_description", "") or "") == new_loc_key
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

        vlan_val = self._current_vlan_value()

        self._result = {
            "id":                   self._outlet.get("id", ""),
            "room_id":              effective_room_id,
            "name":                 name,
            "location_description": self._current_location_key(),
            "endpoint_id":          self._get_selected_ep_id() or "",
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
        return self._current_vlan_value()

    def get_endpoints_result(self) -> list:
        return self._endpoints_data