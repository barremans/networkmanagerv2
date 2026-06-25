# =============================================================================
# Networkmap_Creator
# File:    app/gui/endpoint_overview_widget.py
# Role:    Eindapparaten overzicht — zoeken en filteren per site
# Version: 1.4.0
# Author:  Barremans
# Changes: 1.4.0 — F8: rechtsklik-menu uitgebreid met "IP kopiëren" / "MAC
#                   kopiëren" (veld-gestuurd, alleen als waarde bestaat). MAC
#                   genormaliseerd via normalize_mac(). Leesactie: werkt ook in
#                   read-only modus.
#          1.0.0 — Initiële versie
#          1.1.0 — MAC-kolom verwijderd
#          1.2.0 — navigate_to_rack geeft nu ook ep_id mee voor poort-highlight
#          1.3.0 — navigate_to_floorplan geeft target_val mee voor wandpunt-selectie
#          1.3.1 — loc_key fallback via rack-ruimte (fix "Open grondplan" uitgeschakeld)
#          1.3.2 — loc_key fix: wandpunt.location_description ipv room.outlet_location_key
#          1.3.3 — target_val fix: outlet_id meesturen voor correcte svg-punt selectie
#                  voor direct verbonden endpoints zonder wandpunt)
#                  Rack-kolom toegevoegd (na Ruimte)
#                  Rechtsklik-menu: "Open rack" en "Open grondplan"
#                  Signal: navigate_to_rack(rack_id), navigate_to_floorplan(site_id, loc_key)
# =============================================================================

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMenu, QApplication,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from app.helpers.i18n import t, get_language
from app.helpers import settings_storage
from app.helpers.formatting import normalize_mac

# Kolom-indices (geen MAC meer)
_COL_NAME   = 0
_COL_TYPE   = 1
_COL_IP     = 2
_COL_SERIAL = 3
_COL_BRAND  = 4
_COL_MODEL  = 5
_COL_OUTLET = 6
_COL_ROOM   = 7
_COL_RACK   = 8
_COLS = 9

_EP_ID_ROLE   = Qt.ItemDataRole.UserRole
_RACK_ID_ROLE    = Qt.ItemDataRole.UserRole + 1
_LOC_KEY_ROLE    = Qt.ItemDataRole.UserRole + 2
_OUTLET_ID_ROLE  = Qt.ItemDataRole.UserRole + 3


class EndpointOverviewWidget(QWidget):
    """
    Overzichtstabel van alle eindapparaten van een site.
    Zoekbalk + type-filter. Dubbelklik → EndpointDialog.
    Rechtsklik → Open rack / Open grondplan.
    """

    endpoint_changed      = Signal()           # na opslaan
    navigate_to_rack      = Signal(str, str)   # rack_id, ep_id
    navigate_to_floorplan = Signal(str, str, str)  # site_id, loc_key, target_val (ep:id of outlet_id)

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

        # Zoek + filter
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        self._search = QLineEdit()
        self._search.setPlaceholderText(f"🔍  {t('search_placeholder_endpoint')}")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self._search, 1)
        self._ddl_type = QComboBox()
        self._ddl_type.setMinimumWidth(160)
        self._ddl_type.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self._ddl_type)
        root.addLayout(filter_row)

        # Tabel
        self._table = QTableWidget(0, _COLS)
        self._table.setHorizontalHeaderLabels([
            t("label_name"),
            t("label_type"),
            t("label_ip"),
            t("label_serial"),
            t("label_brand"),
            t("label_model"),
            t("label_wall_outlet"),
            t("label_room"),
            t("label_rack"),
        ])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hdr.setStretchLastSection(True)
        self._table.setColumnWidth(_COL_NAME,   160)
        self._table.setColumnWidth(_COL_TYPE,   110)
        self._table.setColumnWidth(_COL_IP,     115)
        self._table.setColumnWidth(_COL_SERIAL, 120)
        self._table.setColumnWidth(_COL_BRAND,   80)
        self._table.setColumnWidth(_COL_MODEL,  180)
        self._table.setColumnWidth(_COL_OUTLET,  80)
        self._table.setColumnWidth(_COL_ROOM,   140)

        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSortingEnabled(True)
        self._table.doubleClicked.connect(self._on_double_click)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)
        root.addWidget(self._table, 1)

    # ------------------------------------------------------------------
    # Data vullen
    # ------------------------------------------------------------------

    def _populate(self):
        lang = get_language()

        # Type-labels
        ep_types = settings_storage.load_endpoint_types()
        self._type_label_map: dict[str, str] = {}
        for et in ep_types:
            key   = et.get("key", "")
            label = et.get(f"label_{lang}", et.get("label_nl", key))
            self._type_label_map[key] = label

        # Rack-lookup: device_id → (rack, room)
        device_to_rack: dict[str, tuple] = {}
        for room in self._site.get("rooms", []):
            for rack in room.get("racks", []):
                for slot in rack.get("slots", []):
                    dev_id = slot.get("device_id", "")
                    if dev_id:
                        device_to_rack[dev_id] = (rack, room)

        # Poort → (rack, room) via device
        port_to_rack: dict[str, tuple] = {}
        for p in self._data.get("ports", []):
            info = device_to_rack.get(p.get("device_id", ""))
            if info:
                port_to_rack[p["id"]] = info

        # Wandpunt-info per endpoint_id
        outlet_map: dict[str, dict] = {}
        for room in self._site.get("rooms", []):
            for wo in room.get("wall_outlets", []):
                ep_id = wo.get("endpoint_id", "")
                if ep_id:
                    # loc_key = location_description van het wandpunt zelf
                    # (dit is de outlet_location_key die aan een floorplan gekoppeld is)
                    loc_key = wo.get("location_description", "") \
                              or room.get("outlet_location_key", "")
                    outlet_map[ep_id] = {
                        "outlet_name": wo.get("name", ""),
                        "room_name":   room.get("name", ""),
                        "loc_key":     loc_key,
                        "outlet_id":   wo.get("id", ""),
                    }

        # Endpoints die tot deze site behoren
        site_ep_ids: set[str] = set(outlet_map.keys())
        site_port_ids = set(port_to_rack.keys())
        ep_to_rack: dict[str, tuple] = {}

        for conn in self._data.get("connections", []):
            ft, fid = conn.get("from_type", ""), conn.get("from_id", "")
            tt, tid = conn.get("to_type",   ""), conn.get("to_id",   "")
            if ft == "endpoint" and tid in site_port_ids:
                site_ep_ids.add(fid)
                ep_to_rack[fid] = port_to_rack[tid]
            if tt == "endpoint" and fid in site_port_ids:
                site_ep_ids.add(tid)
                ep_to_rack[tid] = port_to_rack[fid]

        # Rack via wandpunt-verbinding
        for ep_id, wo_info in outlet_map.items():
            if ep_id not in ep_to_rack:
                # Zoek verbinding van dit wandpunt naar een poort
                wo_id = next(
                    (wo["id"]
                     for room in self._site.get("rooms", [])
                     for wo in room.get("wall_outlets", [])
                     if wo.get("endpoint_id") == ep_id),
                    None,
                )
                if wo_id:
                    for conn in self._data.get("connections", []):
                        pid = None
                        if conn.get("from_type") == "wall_outlet" and conn.get("from_id") == wo_id:
                            pid = conn.get("to_id") if conn.get("to_type") == "port" else None
                        elif conn.get("to_type") == "wall_outlet" and conn.get("to_id") == wo_id:
                            pid = conn.get("from_id") if conn.get("from_type") == "port" else None
                        if pid and pid in port_to_rack:
                            ep_to_rack[ep_id] = port_to_rack[pid]
                            break

        self._all_rows = []
        for ep in self._data.get("endpoints", []):
            ep_id = ep.get("id", "")
            if ep_id not in site_ep_ids:
                continue
            type_key   = ep.get("type", "")
            type_label = self._type_label_map.get(type_key, type_key)
            wo_info    = outlet_map.get(ep_id, {})
            rack_info  = ep_to_rack.get(ep_id)
            rack_name  = rack_info[0].get("name", "") if rack_info else ""
            rack_id    = rack_info[0].get("id",   "") if rack_info else ""
            loc_key    = wo_info.get("loc_key", "")
            # Fallback: loc_key via ruimte van het rack (voor direct verbonden endpoints)
            if not loc_key and rack_info:
                rack_room = rack_info[1]   # (rack, room) tuple
                loc_key = rack_room.get("outlet_location_key", "")

            self._all_rows.append({
                "id":          ep_id,
                "name":        ep.get("name", ""),
                "type_key":    type_key,
                "type_label":  type_label,
                "ip":          ep.get("ip", ""),
                "serial":      ep.get("serial", ""),
                "brand":       ep.get("brand", ""),
                "model":       ep.get("model", ""),
                "outlet_name": wo_info.get("outlet_name", ""),
                "room_name":   wo_info.get("room_name", ""),
                "rack_name":   rack_name,
                "rack_id":     rack_id,
                "loc_key":     loc_key,
                "outlet_id":   wo_info.get("outlet_id", ""),
                "_search": " ".join([
                    ep.get("name",   ""),
                    type_label,
                    ep.get("ip",     ""),
                    ep.get("serial", ""),
                    ep.get("brand",  ""),
                    ep.get("model",  ""),
                    wo_info.get("outlet_name", ""),
                    wo_info.get("room_name",   ""),
                    rack_name,
                ]).lower(),
            })

        self._all_rows.sort(key=lambda r: r["name"].lower())

        # Type-DDL
        self._ddl_type.blockSignals(True)
        self._ddl_type.clear()
        self._ddl_type.addItem(f"— {t('label_type')} —", "")
        seen: set[str] = set()
        for row in self._all_rows:
            tk = row["type_key"]
            if tk and tk not in seen:
                seen.add(tk)
                self._ddl_type.addItem(row["type_label"], tk)
        self._ddl_type.blockSignals(False)

        site_name = self._site.get("name", "")
        title_key = t("tree_endpoints")
        title_lbl = title_key if title_key != "tree_endpoints" else "Eindapparaten"
        self._lbl_title.setText(f"🖥  {title_lbl}  —  {site_name}")

        self._apply_filter()

    # ------------------------------------------------------------------
    # Filter
    # ------------------------------------------------------------------

    def _apply_filter(self):
        q        = self._search.text().strip().lower()
        type_key = self._ddl_type.currentData() or ""

        filtered = [
            r for r in self._all_rows
            if (not q or q in r["_search"])
            and (not type_key or r["type_key"] == type_key)
        ]

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(filtered))

        for row_idx, row in enumerate(filtered):
            def _item(val: str) -> QTableWidgetItem:
                it = QTableWidgetItem(val)
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                return it

            self._table.setItem(row_idx, _COL_NAME,   _item(row["name"]))
            self._table.setItem(row_idx, _COL_TYPE,   _item(row["type_label"]))
            self._table.setItem(row_idx, _COL_IP,     _item(row["ip"]))
            self._table.setItem(row_idx, _COL_SERIAL, _item(row["serial"]))
            self._table.setItem(row_idx, _COL_BRAND,  _item(row["brand"]))
            self._table.setItem(row_idx, _COL_MODEL,  _item(row["model"]))
            self._table.setItem(row_idx, _COL_OUTLET, _item(row["outlet_name"]))
            self._table.setItem(row_idx, _COL_ROOM,   _item(row["room_name"]))
            self._table.setItem(row_idx, _COL_RACK,   _item(row["rack_name"]))

            # Extra data op naam-cel
            name_item = self._table.item(row_idx, _COL_NAME)
            name_item.setData(_EP_ID_ROLE,      row["id"])
            name_item.setData(_RACK_ID_ROLE,    row["rack_id"])
            name_item.setData(_LOC_KEY_ROLE,    row["loc_key"])
            name_item.setData(_OUTLET_ID_ROLE,  row["outlet_id"])

        self._table.setSortingEnabled(True)
        total = len(self._all_rows)
        shown = len(filtered)
        self._lbl_count.setText(
            f"{shown} / {total}" if shown != total else str(total)
        )

    # ------------------------------------------------------------------
    # Interactie
    # ------------------------------------------------------------------

    def _row_data(self, row: int):
        item = self._table.item(row, _COL_NAME)
        if not item:
            return None, None, None, None
        return (
            item.data(_EP_ID_ROLE),
            item.data(_RACK_ID_ROLE),
            item.data(_LOC_KEY_ROLE),
            item.data(_OUTLET_ID_ROLE) or "",
        )

    def _on_double_click(self, index):
        self._open_edit(index.row())

    def _on_context_menu(self, pos):
        row = self._table.rowAt(pos.y())
        if row < 0:
            return
        ep_id, rack_id, loc_key, outlet_id = self._row_data(row)

        # Endpoint-object opzoeken voor IP/MAC (veld-gestuurd menu)
        ep = next(
            (e for e in self._data.get("endpoints", []) if e.get("id") == ep_id),
            None,
        ) or {}
        ip_val  = (ep.get("ip", "")  or "").strip()
        mac_val = (ep.get("mac", "") or "").strip()

        menu = QMenu(self)
        act_edit     = menu.addAction("✏  " + t("ctx_edit"))

        # F8 — kopieeracties (leesactie: ook in read-only modus)
        act_copy_ip = act_copy_mac = None
        if ip_val or mac_val:
            menu.addSeparator()
            if ip_val:
                act_copy_ip = menu.addAction(t("ctx_copy_ip"))
            if mac_val:
                act_copy_mac = menu.addAction(t("ctx_copy_mac"))

        menu.addSeparator()
        act_rack     = menu.addAction("🗄  " + (
            t("ctx_open_rack") if t("ctx_open_rack") != "ctx_open_rack"
            else "Open rack"
        ))
        act_floorplan = menu.addAction("🗺  " + (
            t("ctx_open_floorplan") if t("ctx_open_floorplan") != "ctx_open_floorplan"
            else "Open grondplan"
        ))

        # Uitschakelen als info ontbreekt
        act_rack.setEnabled(bool(rack_id))
        act_floorplan.setEnabled(bool(loc_key))

        action = menu.exec(QCursor.pos())
        if action is None:
            return
        if action == act_edit:
            self._open_edit(row)
        elif act_copy_ip is not None and action == act_copy_ip:
            QApplication.clipboard().setText(ip_val)
        elif act_copy_mac is not None and action == act_copy_mac:
            QApplication.clipboard().setText(normalize_mac(mac_val))
        elif action == act_rack and rack_id:
            self.navigate_to_rack.emit(rack_id, ep_id or "")
        elif action == act_floorplan and loc_key:
            # target_val: outlet_id heeft voorkeur (wandpunt-mapping),
            # anders "ep:ep_id" (directe endpoint-mapping)
            target_val = outlet_id if outlet_id else (f"ep:{ep_id}" if ep_id else "")
            self.navigate_to_floorplan.emit(self._site["id"], loc_key, target_val)

    def _open_edit(self, row: int):
        if settings_storage.get_read_only_mode():
            return
        ep_id, _, _, _ = self._row_data(row)
        if not ep_id:
            return
        ep = next(
            (e for e in self._data.get("endpoints", []) if e["id"] == ep_id),
            None,
        )
        if not ep:
            return
        from app.gui.dialogs.endpoint_dialog import EndpointDialog
        dlg = EndpointDialog(parent=self, endpoint=ep)
        if dlg.exec() and dlg.get_result():
            result = dlg.get_result()
            result["id"] = ep_id
            for i, e in enumerate(self._data.get("endpoints", [])):
                if e["id"] == ep_id:
                    self._data["endpoints"][i] = result
                    break
            self._populate()
            self.endpoint_changed.emit()

    # ------------------------------------------------------------------
    # Publiek
    # ------------------------------------------------------------------

    def refresh(self, data: dict):
        self._data = data
        self._populate()