# =============================================================================
# Networkmap_Creator
# File:    app/gui/vlan_report_view.py
# Role:    Zijpaneel VLAN rapport — alle poorten per VLAN, over sites/racks
# Version: 1.6.0
# Author:  Barremans
# Changes: 1.6.0 -- F1: get_all_sites() voor v2 JSON
#          1.5.0 — F2: VLAN selector vervangen door QLineEdit + QListWidget
#                  met real-time zoekfilter
#          1.4.0 — Direct endpoint: conn_label herkent to_type=="endpoint"
#                  _add_vlan_direct_endpoints() toegevoegd
#          1.3.0 — B4: VLAN type-mismatch fix
# =============================================================================

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt
from app.helpers.i18n import t
from app.services.vlan_service import load_vlans, vlan_label
from app.helpers.settings_storage import get_all_sites


def _vlan_eq(port_vlan, vlan_num: int) -> bool:
    """B4 — Vergelijk VLAN waarden type-onafhankelijk (str of int in JSON)."""
    if port_vlan is None:
        return False
    try:
        return int(port_vlan) == vlan_num
    except (ValueError, TypeError):
        return False


class VlanReportView(QWidget):
    """
    Toont een tekstueel VLAN rapport in het midden paneel.
    Kies een VLAN → overzicht van alle poorten + wandpunten van dat VLAN,
    gegroepeerd per site → rack → device.
    """

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self._data = data
        self._build()

    def _collect_vlans(self) -> list[int]:
        """Verzamel alle unieke VLAN nummers in de data — poorten + wandpunten."""
        vlans = set()
        for p in self._data.get("ports", []):
            v = p.get("vlan")
            if v:
                vlans.add(int(v))
        for s in get_all_sites(self._data):
            for r in s.get("rooms", []):
                for wo in r.get("wall_outlets", []):
                    v = wo.get("vlan")
                    if v:
                        vlans.add(int(v))
        return sorted(vlans)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Titel
        title = QLabel("🔷  VLAN rapport")
        title.setObjectName("rack_title")
        layout.addWidget(title)

        vlans = self._collect_vlans()

        # Scroll area altijd aanmaken (ook als leeg) zodat refresh() werkt
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll = scroll

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setSpacing(6)
        self._content_layout.setContentsMargins(0, 0, 4, 0)
        scroll.setWidget(self._content)

        if not vlans:
            empty = QLabel(t("vlan_report_no_vlans")
                           if t("vlan_report_no_vlans") != "vlan_report_no_vlans"
                           else "Geen VLAN toewijzingen gevonden.")
            empty.setObjectName("secondary")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._content_layout.addWidget(empty)
            self._content_layout.addStretch()
            layout.addWidget(scroll)
            return

        # VLAN selector — zoekbaar (v1.5.0)
        sel_row = QHBoxLayout()
        sel_lbl = QLabel("VLAN:")
        sel_row.addWidget(sel_lbl)

        vlan_widget = QWidget()
        vlan_vl = QVBoxLayout(vlan_widget)
        vlan_vl.setContentsMargins(0, 0, 0, 0)
        vlan_vl.setSpacing(3)

        self._search_vlan = QLineEdit()
        self._search_vlan.setPlaceholderText("🔍  VLAN zoeken...")
        self._search_vlan.setClearButtonEnabled(True)
        self._search_vlan.textChanged.connect(self._filter_vlan_list)
        vlan_vl.addWidget(self._search_vlan)

        self._list_vlan = QListWidget()
        self._list_vlan.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list_vlan.setFixedHeight(110)
        self._list_vlan.currentRowChanged.connect(self._on_vlan_selection_changed)

        all_item = QListWidgetItem("— alle —")
        all_item.setData(Qt.ItemDataRole.UserRole, None)
        self._list_vlan.addItem(all_item)
        for v in vlans:
            item = QListWidgetItem(vlan_label(v))
            item.setData(Qt.ItemDataRole.UserRole, v)
            self._list_vlan.addItem(item)
        self._list_vlan.setCurrentRow(0)
        vlan_vl.addWidget(self._list_vlan)

        sel_row.addWidget(vlan_widget, 1)
        sel_row.addStretch()
        layout.addLayout(sel_row)

        layout.addWidget(scroll)

        self._refresh_report()

    def _filter_vlan_list(self, text: str):
        """Real-time filter op VLAN lijst."""
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

    def _on_vlan_selection_changed(self, _row: int):
        self._refresh_report()

    def _current_vlan(self):
        """Geeft het geselecteerde VLAN terug (int of None voor 'alle')."""
        item = self._list_vlan.currentItem()
        if item and not item.isHidden():
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _refresh_report(self):
        # Leeg content
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        selected_vlan = self._current_vlan()
        vlans_to_show = (
            [selected_vlan] if selected_vlan is not None
            else self._collect_vlans()
        )

        # Index opbouwen
        dev_map  = {d["id"]: d for d in self._data.get("devices", [])}
        port_map = {}
        for p in self._data.get("ports", []):
            port_map.setdefault(p["device_id"], []).append(p)

        for vlan_num in vlans_to_show:
            self._add_vlan_section(vlan_num, dev_map, port_map)

        self._content_layout.addStretch()

    def _add_vlan_section(self, vlan_num: int, dev_map: dict, port_map: dict):
        """Voeg één VLAN sectie toe aan het rapport."""

        # Verzamel alle poorten van dit VLAN
        vlan_ports = [
            p for p in self._data.get("ports", [])
            if _vlan_eq(p.get("vlan"), vlan_num)
        ]
        # Wandpunten met dit VLAN verzamelen
        vlan_outlets = []
        for s in get_all_sites(self._data):
            for r in s.get("rooms", []):
                for wo in r.get("wall_outlets", []):
                    if _vlan_eq(wo.get("vlan"), vlan_num):
                        vlan_outlets.append({
                            "wo": wo,
                            "room": r.get("name", "?"),
                            "site": s.get("name", "?"),
                        })

        if not vlan_ports and not vlan_outlets:
            return

        # VLAN header
        vlan_frame = QFrame()
        vlan_frame.setObjectName("rack_frame")
        vlan_hl = QHBoxLayout(vlan_frame)
        vlan_hl.setContentsMargins(10, 6, 10, 6)
        from app.services.vlan_service import vlan_label as _vl
        vlan_title = QLabel(_vl(vlan_num))
        from app.services.vlan_service import get_vlan_by_id as _gvb
        _vdef = _gvb(vlan_num)
        _vcolor = _vdef.get("color", "#4a9eda") if _vdef else "#4a9eda"
        vlan_title.setObjectName("rack_title")
        vlan_title.setStyleSheet(f"color: {_vcolor};")

        # IP / subnet tonen indien ingevuld
        _vip     = _vdef.get("ip", "")     if _vdef else ""
        _vsubnet = _vdef.get("subnet", "") if _vdef else ""
        ip_parts = [x for x in [_vip, _vsubnet] if x]
        ip_lbl   = QLabel("  /  ".join(ip_parts)) if ip_parts else None
        if ip_lbl:
            ip_lbl.setObjectName("secondary")

        count_lbl = QLabel(f"{len(vlan_ports)} poort{'en' if len(vlan_ports) != 1 else ''}")
        count_lbl.setObjectName("secondary")
        vlan_hl.addWidget(vlan_title)
        if ip_lbl:
            vlan_hl.addSpacing(12)
            vlan_hl.addWidget(ip_lbl)
        vlan_hl.addStretch()
        vlan_hl.addWidget(count_lbl)
        self._content_layout.addWidget(vlan_frame)

        # Groepeer per site → rack → device
        # Bouw lookup: device_id → (site, rack, device)
        device_location = {}
        for site in get_all_sites(self._data):
            for room in site.get("rooms", []):
                for rack in room.get("racks", []):
                    for slot in rack.get("slots", []):
                        dev_id = slot.get("device_id")
                        if dev_id:
                            device_location[dev_id] = (site, room, rack)

        # Groepeer poorten per locatie
        from collections import defaultdict
        grouped = defaultdict(list)
        for p in vlan_ports:
            loc = device_location.get(p["device_id"])
            if loc:
                site, room, rack = loc
                key = (site["id"], room["id"], rack["id"], p["device_id"])
                grouped[key].append(p)

        # Render per groep
        current_site_id = None
        current_rack_id = None

        # Sorteer op site → room → rack → device
        sorted_keys = sorted(grouped.keys())

        for key in sorted_keys:
            site_id, room_id, rack_id, dev_id = key
            ports_in_group = grouped[key]

            site  = next((s for s in get_all_sites(self._data) if s["id"] == site_id), None)
            room  = next((r for s in get_all_sites(self._data)
                          for r in s.get("rooms", []) if r["id"] == room_id), None)
            rack  = next((ra for s in get_all_sites(self._data)
                          for r in s.get("rooms", [])
                          for ra in r.get("racks", []) if ra["id"] == rack_id), None)
            dev   = dev_map.get(dev_id)

            if not all([site, room, rack, dev]):
                continue

            # Site label (eenmalig per site)
            if site_id != current_site_id:
                site_lbl = QLabel(f"📍  {site['name']}")
                site_lbl.setStyleSheet(
                    "font-weight: bold; font-size: 12px; padding: 4px 0 2px 0;"
                )
                self._content_layout.addWidget(site_lbl)
                current_site_id = site_id
                current_rack_id = None

            # Rack label (eenmalig per rack)
            if rack_id != current_rack_id:
                rack_lbl = QLabel(f"  🗄  {rack['name']}  ·  🚪  {room['name']}")
                rack_lbl.setObjectName("secondary")
                self._content_layout.addWidget(rack_lbl)
                current_rack_id = rack_id

            # Device + poorten
            dev_frame = QFrame()
            dev_frame.setObjectName("rack_unit_empty")
            dev_vl = QVBoxLayout(dev_frame)
            dev_vl.setContentsMargins(16, 4, 8, 4)
            dev_vl.setSpacing(2)

            dev_type  = dev.get("type", "")
            dev_title = QLabel(
                f"💻  {dev['name']}  "
                f"<span style='color:#888; font-size:10px;'>"
                f"[{t(f'device_{dev_type}') if dev_type else dev_type}]</span>"
            )
            dev_title.setTextFormat(Qt.TextFormat.RichText)
            dev_vl.addWidget(dev_title)

            for p in sorted(ports_in_group, key=lambda x: (x["side"], x["number"])):
                side_str = "VOOR" if p["side"] == "front" else "ACHTER"
                # Verbonden met?
                conn = next(
                    (c for c in self._data.get("connections", [])
                     if c.get("from_id") == p["id"] or c.get("to_id") == p["id"]),
                    None
                )
                conn_label = ""
                if conn:
                    other_id   = conn["to_id"]   if conn["from_id"] == p["id"] else conn["from_id"]
                    other_type = conn["to_type"]  if conn["from_id"] == p["id"] else conn["from_type"]
                    if other_type == "port":
                        op = next((x for x in self._data.get("ports", [])
                                   if x["id"] == other_id), None)
                        od = dev_map.get(op["device_id"]) if op else None
                        if op and od:
                            conn_label = f"  →  {od['name']} / {op['name']}"
                    elif other_type == "wall_outlet":
                        for s2 in get_all_sites(self._data):
                            for r2 in s2.get("rooms", []):
                                for wo in r2.get("wall_outlets", []):
                                    if wo["id"] == other_id:
                                        conn_label = f"  →  🌐 {wo['name']} ({r2['name']})"
                    elif other_type == "endpoint":
                        ep = next((e for e in self._data.get("endpoints", [])
                                   if e["id"] == other_id), None)
                        if ep:
                            conn_label = f"  →  🖥 {ep['name']}"

                port_lbl = QLabel(
                    f"    ⬡  {p['name']}  ({side_str})"
                    f"<span style='color:#4caf7d; font-weight:bold;'>"
                    f"  VLAN {p['vlan']}</span>"
                    f"<span style='color:#888;'>{conn_label}</span>"
                )
                port_lbl.setTextFormat(Qt.TextFormat.RichText)
                dev_vl.addWidget(port_lbl)

            self._content_layout.addWidget(dev_frame)

        # Wandpunten met dit VLAN (indirect via verbonden poort)
        self._add_vlan_outlets(vlan_num, dev_map)
        # 1.4.0 — Direct verbonden endpoints via VLAN poort
        self._add_vlan_direct_endpoints(vlan_num)

    def _add_vlan_outlets(self, vlan_num: int, dev_map: dict):
        """
        Voeg wandpunten toe die indirect dit VLAN hebben
        (verbonden met een poort van VLAN X).
        """
        vlan_port_ids = {
            p["id"] for p in self._data.get("ports", [])
            if _vlan_eq(p.get("vlan"), vlan_num)
        }

        outlet_conns = []
        for conn in self._data.get("connections", []):
            from_is_vlan = (conn.get("from_type") == "port"
                            and conn.get("from_id") in vlan_port_ids)
            to_is_vlan   = (conn.get("to_type") == "port"
                            and conn.get("to_id") in vlan_port_ids)

            if from_is_vlan and conn.get("to_type") == "wall_outlet":
                outlet_conns.append((conn["to_id"], conn["from_id"]))
            elif to_is_vlan and conn.get("from_type") == "wall_outlet":
                outlet_conns.append((conn["from_id"], conn["to_id"]))

        # Ook wandpunten met DIRECT VLAN toewijzing tonen
        direct_outlets = []
        direct_ids = {oc[0] for oc in outlet_conns}  # al via trace gevonden
        for s in get_all_sites(self._data):
            for r in s.get("rooms", []):
                for wo in r.get("wall_outlets", []):
                    if (_vlan_eq(wo.get("vlan"), vlan_num)
                            and wo["id"] not in direct_ids):
                        ep_id = wo.get("endpoint_id", "")
                        ep = next((e for e in self._data.get("endpoints", [])
                                   if e.get("id") == ep_id), None)
                        direct_outlets.append({
                            "wo": wo,
                            "room": r.get("name", "?"),
                            "site": s.get("name", "?"),
                            "ep":   ep,
                        })

        if direct_outlets:
            sep_d = QLabel("  🌐  Wandpunten (direct VLAN):")
            sep_d.setObjectName("secondary")
            self._content_layout.addWidget(sep_d)
            for entry in direct_outlets:
                wo = entry["wo"]
                ep_name = entry["ep"].get("name", "") if entry["ep"] else ""
                wo_lbl = QLabel(
                    f"    🌐  <b>{wo.get('name', wo['id'])}</b>"
                    f"<span style='color:#888; font-size:10px;'>"
                    f"  ({entry['room']}, {entry['site']})"
                    + (f"  —  {ep_name}" if ep_name else "")
                    + f"</span>"
                )
                wo_lbl.setTextFormat(Qt.TextFormat.RichText)
                self._content_layout.addWidget(wo_lbl)

        if not outlet_conns:
            return

        sep = QLabel("  🌐  Wandpunten via dit VLAN:")
        sep.setObjectName("secondary")
        self._content_layout.addWidget(sep)

        for outlet_id, port_id in outlet_conns:
            wo = room_name = site_name = None
            for s in get_all_sites(self._data):
                for r in s.get("rooms", []):
                    for w in r.get("wall_outlets", []):
                        if w["id"] == outlet_id:
                            wo        = w
                            room_name = r["name"]
                            site_name = s["name"]
            if not wo:
                continue

            port = next((p for p in self._data.get("ports", [])
                         if p["id"] == port_id), None)
            dev  = dev_map.get(port["device_id"]) if port else None
            port_label = (f"{dev['name']} / {port['name']}"
                          if port and dev else port_id)

            wo_lbl = QLabel(
                f"    🌐  {wo.get('name', outlet_id)}"
                f"<span style='color:#888; font-size:10px;'>"
                f"  ({room_name}, {site_name})"
                f"  via {port_label}"
                f"</span>"
            )
            wo_lbl.setTextFormat(Qt.TextFormat.RichText)
            self._content_layout.addWidget(wo_lbl)

    def _add_vlan_direct_endpoints(self, vlan_num: int):
        """
        1.4.0 — Toon direct verbonden endpoints waarvan de poort dit VLAN heeft.
        """
        vlan_port_ids = {
            p["id"] for p in self._data.get("ports", [])
            if _vlan_eq(p.get("vlan"), vlan_num)
        }
        ep_map = {e["id"]: e for e in self._data.get("endpoints", [])}

        items = []
        for conn in self._data.get("connections", []):
            if conn.get("to_type") == "endpoint":
                port_id = conn["from_id"]
                ep_id   = conn["to_id"]
            elif conn.get("from_type") == "endpoint":
                port_id = conn["to_id"]
                ep_id   = conn["from_id"]
            else:
                continue
            if port_id not in vlan_port_ids:
                continue
            ep = ep_map.get(ep_id)
            if ep:
                items.append(ep)

        if not items:
            return

        sep = QLabel("  🖥  Direct verbonden (VLAN):")
        sep.setObjectName("secondary")
        self._content_layout.addWidget(sep)

        for ep in items:
            lbl = QLabel(
                f"    🖥  <b>{ep.get('name', ep['id'])}</b>"
                f"<span style='color:#888; font-size:10px;'>"
                f"  {ep.get('location', '')}"
                f"</span>"
            )
            lbl.setTextFormat(Qt.TextFormat.RichText)
            self._content_layout.addWidget(lbl)

    def refresh(self, data: dict):
        self._data = data
        self._refresh_report()