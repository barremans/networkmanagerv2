# =============================================================================
# Networkmap_Creator
# File:    app/gui/unused_outlet_overview_widget.py
# Role:    Wandpunten overzicht per site — status per wandpunt tonen:
#          actief zonder device (security risico), actief met device (normaal),
#          niet verbonden (inactief). Volledige switch-trace via tracing service.
# Version: 1.2.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie
#                  Kolommen: Naam, Ruimte, Verbonden met, Poort, Type verbinding, Status
#                  Zoekbalk + statusfilter (alles / actief zonder device / niet verbonden)
#                  Rechtsklik: Wandpunt bewerken / Open rack / Open grondplan
#                  Signalen: outlet_changed, navigate_to_rack, navigate_to_floorplan
#          1.1.0 — Volledige switch-trace via tracing.trace_from_port()
#                  Nieuwe kolommen: Switch, Switch Poort, Rack
#                  navigate_to_rack geeft nu switch_port_id mee voor highlight
#                  _SWITCH_PORT_ID_ROLE toegevoegd op naam-cel
#          1.2.0 — Standaard filter op "Actief — geen device"
#                  Nieuwe status: "Actief — met device" (active_with_device)
#                  Widget laadt nu ALLE wandpunten van de site (ook met endpoint_id)
#                  Status constanten uitgebreid: _STATUS_ACTIVE_NO_DEV,
#                  _STATUS_ACTIVE_WITH_DEV, _STATUS_INACTIVE
#                  Teltekst in header toont beide actieve categorieën apart
# =============================================================================

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMenu,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from app.helpers.i18n import t
from app.helpers import settings_storage
from app.services import tracing

# Kolom-indices
_COL_NAME        = 0   # Wandpunt naam
_COL_ROOM        = 1   # Ruimte
_COL_CONNECTED   = 2   # Verbonden met (patchpanel of direct switch)
_COL_PORT        = 3   # Poortnaam (patchpanel back-poort of switch-poort)
_COL_CONN_TYPE   = 4   # Type verbinding (Direct switch / Via patchpanel)
_COL_SWITCH      = 5   # Switch naam (eindpunt van trace)
_COL_SWITCH_PORT = 6   # Switch poortnaam
_COL_RACK        = 7   # Rack naam van de switch
_COL_STATUS      = 8   # Status label
_COLS = 9

# Data roles op naam-cel
_WO_ID_ROLE          = Qt.ItemDataRole.UserRole
_RACK_ID_ROLE        = Qt.ItemDataRole.UserRole + 1
_LOC_KEY_ROLE        = Qt.ItemDataRole.UserRole + 2
_STATUS_ROLE         = Qt.ItemDataRole.UserRole + 3
_SWITCH_PORT_ID_ROLE = Qt.ItemDataRole.UserRole + 4   # voor rack highlight (1.1.0)

# Status constanten (1.2.0 — uitgebreid)
_STATUS_ACTIVE_NO_DEV   = "active_no_device"    # 🟠 Actief, geen eindapparaat → risico
_STATUS_ACTIVE_WITH_DEV = "active_with_device"  # 🟢 Actief, met eindapparaat → normaal
_STATUS_INACTIVE        = "inactive"            # 🔴 Niet verbonden met netwerk


def _t(key: str, fallback: str) -> str:
    """t() met inline fallback als sleutel nog niet in i18n staat."""
    val = t(key)
    return fallback if val == f"[{key}]" else val


class UnusedOutletOverviewWidget(QWidget):
    """
    Overzichtstabel van ALLE wandpunten van een site, gesorteerd op status.

    Drie categorieën:
      🟠 Actief — geen device  : verbonden met netwerk, geen eindapparaat → RISICO
      🟢 Actief — met device   : verbonden met netwerk + eindapparaat → normaal
      🔴 Niet verbonden        : wandpunt bestaat maar heeft geen netwerkkoppeling

    Standaard gefilterd op 🟠 (de gevaarlijke categorie).
    Volledige switch-trace getoond (patchpanel → switch naam/poort/rack).
    Rechtsklik → bewerken / open rack (met poort-highlight) / open grondplan.
    """

    outlet_changed        = Signal()                # na opslaan wandpunt
    navigate_to_rack      = Signal(str, str)        # rack_id, switch_port_id (voor highlight)
    navigate_to_floorplan = Signal(str, str, str)   # site_id, loc_key, target_val

    def __init__(self, site: dict, data: dict, parent=None):
        super().__init__(parent)
        self._site = site
        self._data = data
        self._all_rows: list[dict] = []

        self._build_ui()
        self._populate()

    # ------------------------------------------------------------------
    # UI opbouw
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(8)

        # Titelregel
        title_row = QHBoxLayout()
        self._lbl_title = QLabel()
        self._lbl_title.setObjectName("section-title")
        title_row.addWidget(self._lbl_title)
        title_row.addStretch()
        self._lbl_count = QLabel()
        self._lbl_count.setObjectName("secondary")
        title_row.addWidget(self._lbl_count)
        root.addLayout(title_row)

        # Zoek + statusfilter
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        self._search = QLineEdit()
        self._search.setPlaceholderText(
            f"🔍  {_t('search_placeholder_unused_outlet', 'Zoek naam, ruimte of verbonden toestel...')}"
        )
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self._search, 1)

        self._ddl_status = QComboBox()
        self._ddl_status.setMinimumWidth(240)
        self._ddl_status.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self._ddl_status)
        root.addLayout(filter_row)

        # Tabel
        self._table = QTableWidget(0, _COLS)
        self._table.setHorizontalHeaderLabels([
            _t("label_wall_outlet",        "Wandpunt"),
            _t("label_room",               "Ruimte"),
            _t("label_unused_connected_to","Verbonden met"),
            _t("label_port",               "Poort"),
            _t("label_conn_type",          "Type verbinding"),
            _t("label_switch",             "Switch"),
            _t("label_switch_port",        "Switch poort"),
            _t("label_rack",               "Rack"),
            _t("label_status",             "Status"),
        ])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hdr.setStretchLastSection(True)
        self._table.setColumnWidth(_COL_NAME,        100)
        self._table.setColumnWidth(_COL_ROOM,        160)
        self._table.setColumnWidth(_COL_CONNECTED,   160)
        self._table.setColumnWidth(_COL_PORT,        100)
        self._table.setColumnWidth(_COL_CONN_TYPE,   140)
        self._table.setColumnWidth(_COL_SWITCH,      160)
        self._table.setColumnWidth(_COL_SWITCH_PORT, 100)
        self._table.setColumnWidth(_COL_RACK,        100)

        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSortingEnabled(True)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)
        root.addWidget(self._table, 1)

    # ------------------------------------------------------------------
    # Data vullen
    # ------------------------------------------------------------------

    def _populate(self):
        """
        Bouw de volledige rijen-lijst voor ALLE wandpunten van de site.

        Stap 1: helpers opbouwen (device_map, port_map, device_to_rack,
                outlet_connections).
        Stap 2: itereer over alle wandpunten.
        Stap 3: bepaal status (active_no_device / active_with_device / inactive).
        Stap 4: voor actieve wandpunten → volledige trace via
                tracing.trace_from_port() om switch + switch-poort + rack te vinden.
        Stap 5: DDL vullen, standaard op _STATUS_ACTIVE_NO_DEV.
        """
        # --- helpers ---
        device_map: dict[str, dict] = {
            d["id"]: d for d in self._data.get("devices", [])
        }
        port_map: dict[str, dict] = {
            p["id"]: p for p in self._data.get("ports", [])
        }

        # rack-info per device_id — alleen devices in DEZE site
        device_to_rack: dict[str, tuple] = {}
        for room in self._site.get("rooms", []):
            for rack in room.get("racks", []):
                for slot in rack.get("slots", []):
                    dev_id = slot.get("device_id", "")
                    if dev_id:
                        device_to_rack[dev_id] = (rack, room)

        # verbindingen geïndexeerd op outlet-id
        outlet_connections: dict[str, list[dict]] = {}
        for conn in self._data.get("connections", []):
            ft  = conn.get("from_type", "")
            fid = conn.get("from_id",   "")
            tt  = conn.get("to_type",   "")
            tid = conn.get("to_id",     "")
            if ft == "wall_outlet":
                outlet_connections.setdefault(fid, []).append(
                    {"partner_id": tid, "partner_type": tt}
                )
            if tt == "wall_outlet":
                outlet_connections.setdefault(tid, []).append(
                    {"partner_id": fid, "partner_type": ft}
                )

        self._all_rows = []

        for room in self._site.get("rooms", []):
            room_name    = room.get("name", "")
            loc_key_room = room.get("outlet_location_key", "")

            for wo in room.get("wall_outlets", []):
                wo_id      = wo.get("id", "")
                wo_name    = wo.get("name", "")
                has_ep     = bool(wo.get("endpoint_id", ""))
                loc_key    = wo.get("location_description", "") or loc_key_room
                conns      = outlet_connections.get(wo_id, [])

                if not conns:
                    # 🔴 Niet verbonden — wandpunt bestaat maar geen netwerkkoppeling
                    # Alleen wandpunten ZONDER device tonen hier (met device = normaal niet-verbonden)
                    if not has_ep:
                        self._all_rows.append(self._build_row(
                            wo_id=wo_id, wo_name=wo_name, room_name=room_name,
                            loc_key=loc_key, connected_to="", port_name="",
                            conn_type="", switch_name="", switch_port_name="",
                            rack_name="", status=_STATUS_INACTIVE,
                            rack_id="", switch_port_id="",
                        ))
                    continue

                # Wandpunt heeft een verbinding — verwerk (normaal max 1)
                for c in conns:
                    partner_id   = c["partner_id"]
                    partner_type = c["partner_type"]

                    connected_to     = ""
                    port_name        = ""
                    conn_type        = ""
                    switch_name      = ""
                    switch_port_name = ""
                    rack_name        = ""
                    rack_id          = ""
                    switch_port_id   = ""

                    if partner_type == "port":
                        port    = port_map.get(partner_id, {})
                        dev_id  = port.get("device_id", "")
                        device  = device_map.get(dev_id, {})
                        port_name    = port.get("name", partner_id)
                        connected_to = device.get("name", dev_id)

                        # Type verbinding bepalen op basis van device type
                        dev_type = device.get("type", "").lower()
                        if "switch" in dev_type:
                            conn_type      = _t("conn_type_direct_switch", "Direct switch")
                            switch_name    = connected_to
                            switch_port_name = port_name
                            rack_info      = device_to_rack.get(dev_id)
                            rack_id        = rack_info[0].get("id",   "") if rack_info else ""
                            rack_name      = rack_info[0].get("name", "") if rack_info else ""
                            switch_port_id = partner_id
                        elif "patch" in dev_type:
                            conn_type = _t("conn_type_via_patchpanel", "Via patchpanel")
                            # Volledige trace om de switch te vinden
                            switch_name, switch_port_name, rack_name, rack_id, switch_port_id = \
                                self._resolve_switch_via_trace(partner_id, device_to_rack,
                                                               device_map, port_map)
                        else:
                            conn_type = _t("conn_type_via_device", "Via toestel")
                            switch_name, switch_port_name, rack_name, rack_id, switch_port_id = \
                                self._resolve_switch_via_trace(partner_id, device_to_rack,
                                                               device_map, port_map)

                    # Status bepalen
                    if has_ep:
                        status = _STATUS_ACTIVE_WITH_DEV
                    else:
                        status = _STATUS_ACTIVE_NO_DEV

                    self._all_rows.append(self._build_row(
                        wo_id=wo_id, wo_name=wo_name, room_name=room_name,
                        loc_key=loc_key, connected_to=connected_to,
                        port_name=port_name, conn_type=conn_type,
                        switch_name=switch_name, switch_port_name=switch_port_name,
                        rack_name=rack_name, status=status,
                        rack_id=rack_id, switch_port_id=switch_port_id,
                    ))

        # Sortering: eerst 🟠, dan 🟢, dan 🔴 — daarna room + naam
        _order = {
            _STATUS_ACTIVE_NO_DEV:   0,
            _STATUS_ACTIVE_WITH_DEV: 1,
            _STATUS_INACTIVE:        2,
        }
        self._all_rows.sort(key=lambda r: (
            _order.get(r["status"], 9),
            r["room_name"].lower(),
            r["wo_name"].lower(),
        ))

        # DDL opbouwen
        self._ddl_status.blockSignals(True)
        self._ddl_status.clear()
        self._ddl_status.addItem(
            f"— {_t('label_status', 'Status')} —", ""
        )
        self._ddl_status.addItem(
            _t("status_active_no_device",   "🟠  Actief — geen device"),
            _STATUS_ACTIVE_NO_DEV,
        )
        self._ddl_status.addItem(
            _t("status_active_with_device", "🟢  Actief — met device"),
            _STATUS_ACTIVE_WITH_DEV,
        )
        self._ddl_status.addItem(
            _t("status_not_connected",      "🔴  Niet verbonden"),
            _STATUS_INACTIVE,
        )
        # Standaard selecteren op "Actief — geen device" (1.2.0)
        self._ddl_status.setCurrentIndex(1)
        self._ddl_status.blockSignals(False)

        site_name = self._site.get("name", "")
        title_lbl = _t("tree_unused_outlets", "Ongebruikte wandpunten")
        self._lbl_title.setText(f"🔌  {title_lbl}  —  {site_name}")

        self._apply_filter()

    def _resolve_switch_via_trace(
        self,
        start_port_id: str,
        device_to_rack: dict,
        device_map: dict,
        port_map: dict,
    ) -> tuple[str, str, str, str, str]:
        """
        Volg de trace vanuit start_port_id (bv. patchpanel back-poort) en
        geef (switch_name, switch_port_name, rack_name, rack_id, switch_port_id)
        terug van de switch aan het einde van de keten.
        Geeft 5 lege strings terug als geen switch gevonden.
        """
        try:
            steps = tracing.trace_from_port(self._data, start_port_id)
        except Exception:
            return "", "", "", "", ""

        # Zoek de laatste poort-stap waarvan het device een switch is
        for step in reversed(steps):
            if step.get("obj_type") != "port":
                continue
            port = port_map.get(step["obj_id"], {})
            dev_id = port.get("device_id", "")
            device = device_map.get(dev_id, {})
            if "switch" in device.get("type", "").lower():
                rack_info = device_to_rack.get(dev_id)
                rack_id   = rack_info[0].get("id",   "") if rack_info else ""
                rack_name = rack_info[0].get("name", "") if rack_info else ""
                return (
                    device.get("name", ""),
                    port.get("name", ""),
                    rack_name,
                    rack_id,
                    step["obj_id"],
                )

        return "", "", "", "", ""

    def _build_row(self, *, wo_id, wo_name, room_name, loc_key,
                   connected_to, port_name, conn_type,
                   switch_name, switch_port_name, rack_name,
                   status, rack_id, switch_port_id) -> dict:
        """Stel één rij-dict samen inclusief zoekstring."""
        status_map = {
            _STATUS_ACTIVE_NO_DEV:   _t("status_active_no_device",   "🟠  Actief — geen device"),
            _STATUS_ACTIVE_WITH_DEV: _t("status_active_with_device", "🟢  Actief — met device"),
            _STATUS_INACTIVE:        _t("status_not_connected",      "🔴  Niet verbonden"),
        }
        status_label = status_map.get(status, status)

        return {
            "wo_id":            wo_id,
            "wo_name":          wo_name,
            "room_name":        room_name,
            "loc_key":          loc_key,
            "connected_to":     connected_to,
            "port_name":        port_name,
            "conn_type":        conn_type,
            "switch_name":      switch_name,
            "switch_port_name": switch_port_name,
            "rack_name":        rack_name,
            "status":           status,
            "status_label":     status_label,
            "rack_id":          rack_id,
            "switch_port_id":   switch_port_id,
            "_search": " ".join([
                wo_name, room_name, connected_to, port_name,
                conn_type, switch_name, switch_port_name, rack_name,
                status_label,
            ]).lower(),
        }

    # ------------------------------------------------------------------
    # Filter
    # ------------------------------------------------------------------

    def _apply_filter(self):
        q      = self._search.text().strip().lower()
        status = self._ddl_status.currentData() or ""

        filtered = [
            r for r in self._all_rows
            if (not q or q in r["_search"])
            and (not status or r["status"] == status)
        ]

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(filtered))

        for row_idx, row in enumerate(filtered):
            def _item(val: str) -> QTableWidgetItem:
                it = QTableWidgetItem(val)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                return it

            self._table.setItem(row_idx, _COL_NAME,        _item(row["wo_name"]))
            self._table.setItem(row_idx, _COL_ROOM,        _item(row["room_name"]))
            self._table.setItem(row_idx, _COL_CONNECTED,   _item(row["connected_to"]))
            self._table.setItem(row_idx, _COL_PORT,        _item(row["port_name"]))
            self._table.setItem(row_idx, _COL_CONN_TYPE,   _item(row["conn_type"]))
            self._table.setItem(row_idx, _COL_SWITCH,      _item(row["switch_name"]))
            self._table.setItem(row_idx, _COL_SWITCH_PORT, _item(row["switch_port_name"]))
            self._table.setItem(row_idx, _COL_RACK,        _item(row["rack_name"]))
            self._table.setItem(row_idx, _COL_STATUS,      _item(row["status_label"]))

            # Extra data op naam-cel
            name_item = self._table.item(row_idx, _COL_NAME)
            name_item.setData(_WO_ID_ROLE,          row["wo_id"])
            name_item.setData(_RACK_ID_ROLE,        row["rack_id"])
            name_item.setData(_LOC_KEY_ROLE,        row["loc_key"])
            name_item.setData(_STATUS_ROLE,         row["status"])
            name_item.setData(_SWITCH_PORT_ID_ROLE, row["switch_port_id"])

        self._table.setSortingEnabled(True)

        total        = len(self._all_rows)
        shown        = len(filtered)
        n_no_dev     = sum(1 for r in self._all_rows if r["status"] == _STATUS_ACTIVE_NO_DEV)
        n_with_dev   = sum(1 for r in self._all_rows if r["status"] == _STATUS_ACTIVE_WITH_DEV)
        n_inactive   = sum(1 for r in self._all_rows if r["status"] == _STATUS_INACTIVE)

        count_txt = (
            f"{shown} / {total}  "
            f"(🟠 {n_no_dev}  🟢 {n_with_dev}  🔴 {n_inactive})"
            if shown != total
            else f"{total}  (🟠 {n_no_dev}  🟢 {n_with_dev}  🔴 {n_inactive})"
        )
        self._lbl_count.setText(count_txt)

    # ------------------------------------------------------------------
    # Interactie
    # ------------------------------------------------------------------

    def _row_data(self, row: int):
        """Geeft (wo_id, rack_id, loc_key, status, switch_port_id) terug."""
        item = self._table.item(row, _COL_NAME)
        if not item:
            return None, None, None, None, None
        return (
            item.data(_WO_ID_ROLE),
            item.data(_RACK_ID_ROLE),
            item.data(_LOC_KEY_ROLE),
            item.data(_STATUS_ROLE),
            item.data(_SWITCH_PORT_ID_ROLE) or "",
        )

    def _on_context_menu(self, pos):
        row = self._table.rowAt(pos.y())
        if row < 0:
            return
        wo_id, rack_id, loc_key, status, switch_port_id = self._row_data(row)

        menu = QMenu(self)
        act_edit = menu.addAction(
            "✏  " + _t("ctx_edit_outlet", "Wandpunt bewerken")
        )
        menu.addSeparator()
        act_rack = menu.addAction(
            "🗄  " + _t("ctx_open_rack", "Open rack")
        )
        act_floorplan = menu.addAction(
            "🗺  " + _t("ctx_open_floorplan", "Open grondplan")
        )

        act_rack.setEnabled(bool(rack_id))
        act_floorplan.setEnabled(bool(loc_key))

        action = menu.exec(QCursor.pos())
        if action == act_edit:
            self._open_edit(row)
        elif action == act_rack and rack_id:
            # switch_port_id meesturen voor poort-highlight in rack (1.1.0)
            self.navigate_to_rack.emit(rack_id, switch_port_id)
        elif action == act_floorplan and loc_key:
            # target_val = outlet_id voor directe wandpunt-mapping in floorplan
            self.navigate_to_floorplan.emit(self._site["id"], loc_key, wo_id)

    def _open_edit(self, row: int):
        if settings_storage.get_read_only_mode():
            return
        wo_id, _, _, _, _ = self._row_data(row)
        if not wo_id:
            return

        # Wandpunt + ruimte opzoeken
        wo       = None
        room_ref = None
        for room in self._site.get("rooms", []):
            for w in room.get("wall_outlets", []):
                if w["id"] == wo_id:
                    wo       = w
                    room_ref = room
                    break
            if wo:
                break
        if not wo:
            return

        from app.gui.dialogs.wall_outlet_dialog import WallOutletDialog
        dlg = WallOutletDialog(
            parent=self,
            outlet=wo,
            room=room_ref,
            site=self._site,
        )
        if dlg.exec() and dlg.get_result():
            result        = dlg.get_result()
            result["id"]  = wo_id
            for r in self._site.get("rooms", []):
                for i, w in enumerate(r.get("wall_outlets", [])):
                    if w["id"] == wo_id:
                        r["wall_outlets"][i] = result
                        break
            self._populate()
            self.outlet_changed.emit()

    # ------------------------------------------------------------------
    # Publiek
    # ------------------------------------------------------------------

    def refresh(self, data: dict):
        self._data = data
        self._populate()