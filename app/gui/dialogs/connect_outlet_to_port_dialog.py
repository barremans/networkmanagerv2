# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/connect_outlet_to_port_dialog.py
# Role:    Wandpunt koppelen aan een poort — met zoekfunctie
# Version: 1.4.0
# Author:  Barremans
# Changes: 1.4.0 — Auto-suggestie: wist zoekbalk en herlaadt lijst als vrije poort
#                   niet zichtbaar is in gefilterde resultaten (bv. zoek 'SWALAN'
#                   maar vrije poort is PATCH A2 BACK zonder SWALAN in label)
#                   company_id filter ook correct bij lege company_id
#          1.3.0 — Auto-suggestie uitgebreid: zoekt via patchpanel front↔back
#                   door naar vrije tegenpoort (switch→patch front→patch back vrij)
#                   company_id filter: enkel poorten van zelfde bedrijf
#          1.2.0 — Betere labels: bezette poorten tonen verbonden keten
#                   Auto-suggestie: bezette poort geselecteerd → systeem zoekt
#                   automatisch de vrije koppelpoort en selecteert die
#                   Info-banner toont omleiding aan gebruiker
#          1.1.0 -- F1: get_all_sites() voor v2 JSON
#          1.0.0 — Initiële versie
#                   Wandpunt is bronkant (bekend), gebruiker kiest een poort
#                   Zoeklijst: Site — Ruimte — Rack — Device · Poort (SIDE)
#                   Vrije poorten bovenaan, in-gebruik grijs onderaan
#                   Kabeltype + notitie velden
# =============================================================================

import re

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from app.helpers.i18n import t
from app.helpers.settings_storage import get_all_sites

_USER_ROLE   = 256
_IN_USE_ROLE = 257

_CABLE_TYPES = [
    ("utp_cat5e",  "cable_utp_cat5e"),
    ("utp_cat6",   "cable_utp_cat6"),
    ("utp_cat6a",  "cable_utp_cat6a"),
    ("fiber_sm",   "cable_fiber_sm"),
    ("fiber_mm",   "cable_fiber_mm"),
    ("dak",        "cable_dak"),
    ("other",      "cable_other"),
]


class ConnectOutletToPortDialog(QDialog):
    """
    Dialoog om een wandpunt te koppelen aan een poort.
    Wandpunt is reeds bekend (outlet_id + outlet_label).
    De gebruiker kiest een doelpoort via zoeklijst.
    """

    def __init__(self, data: dict, outlet_id: str, outlet_label: str,
                 company_id: str = "", parent=None):
        super().__init__(parent)
        self._data         = data
        self._outlet_id    = outlet_id
        self._outlet_label = outlet_label
        self._result       = None

        # company_id filter: bepaal site-IDs van dit bedrijf
        self._company_site_ids: set[str] = set()
        if company_id:
            for company in data.get("companies", []):
                if company["id"] == company_id:
                    for site in company.get("sites", []):
                        self._company_site_ids.add(site["id"])
                    break

        # Verbonden poorten + keten-map voor betere labels
        self._connected_ports = set()
        # port_id → label van de poort waarmee verbonden (voor keten-weergave)
        self._port_chain_label: dict[str, str] = {}
        port_map  = {p["id"]: p for p in data.get("ports", [])}
        device_map_init = {d["id"]: d for d in data.get("devices", [])}
        for conn in data.get("connections", []):
            ft = conn.get("from_type", "")
            tt = conn.get("to_type",   "")
            fid = conn.get("from_id", "")
            tid = conn.get("to_id",   "")
            if ft == "port": self._connected_ports.add(fid)
            if tt == "port": self._connected_ports.add(tid)
            # keten-label: poort A → naam poort B
            if ft == "port" and tt == "port":
                self._port_chain_label[fid] = self._make_port_label(tid, port_map, device_map_init)
                self._port_chain_label[tid] = self._make_port_label(fid, port_map, device_map_init)
            elif ft == "port" and tt == "wall_outlet":
                wo = self._find_outlet(tid, data)
                if wo: self._port_chain_label[fid] = f"🌐 {wo.get('name', tid)}"
            elif tt == "port" and ft == "wall_outlet":
                wo = self._find_outlet(fid, data)
                if wo: self._port_chain_label[tid] = f"🌐 {wo.get('name', fid)}"

        self._all_ports: list[dict] = []

        self.setWindowTitle(t("dlg_connect_outlet_to_port_title"))
        self.setMinimumWidth(580)
        self.setMinimumHeight(460)
        self.setModal(True)
        self._build_ui()
        self._populate_ports()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── Wandpunt info ────────────────────────────────────────────
        grp = QGroupBox(t("label_wall_outlet"))
        grp.setFlat(True)
        grp_layout = QHBoxLayout(grp)
        grp_layout.setContentsMargins(6, 4, 6, 4)
        lbl = QLabel(self._outlet_label)
        lbl.setObjectName("device-label")
        grp_layout.addWidget(lbl)
        grp_layout.addStretch()
        root.addWidget(grp)

        # ── Poort zoeklijst ──────────────────────────────────────────
        self._search = QLineEdit()
        self._search.setPlaceholderText(f"🔍  {t('search_placeholder_port')}")
        self._search.textChanged.connect(self._filter_ports)
        root.addWidget(self._search)

        self._list = QListWidget()
        self._list.setMinimumHeight(200)
        self._list.currentItemChanged.connect(self._on_item_changed)
        root.addWidget(self._list, 1)

        # Info-banner voor auto-suggestie (verborgen tot nodig)
        self._banner = QLabel("")
        self._banner.setObjectName("info_banner")
        self._banner.setStyleSheet(
            "QLabel { background: #1a3a5c; color: #7ecfff; "
            "border: 1px solid #4a7aaa; border-radius: 4px; "
            "padding: 6px 10px; font-size: 12px; }"
        )
        self._banner.setWordWrap(True)
        self._banner.hide()
        root.addWidget(self._banner)

        # ── Scheidingslijn ───────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        # ── Kabeltype ────────────────────────────────────────────────
        cable_row = QHBoxLayout()
        cable_row.addWidget(QLabel(t("label_cable_type") + ":"))
        self._ddl_cable = QComboBox()
        for val, key in _CABLE_TYPES:
            self._ddl_cable.addItem(t(key), val)
        self._ddl_cable.setCurrentIndex(1)
        cable_row.addWidget(self._ddl_cable)
        cable_row.addStretch()
        root.addLayout(cable_row)

        # ── Notitie ──────────────────────────────────────────────────
        notes_row = QHBoxLayout()
        notes_row.addWidget(QLabel(t("label_notes") + ":"))
        self._notes = QLineEdit()
        self._notes.setPlaceholderText(t("label_notes") + "...")
        notes_row.addWidget(self._notes, 1)
        root.addLayout(notes_row)

        # ── Knoppen ──────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(t("btn_cancel"))
        btn_save   = QPushButton(t("btn_save"))
        btn_save.setDefault(True)
        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Populeren
    # ------------------------------------------------------------------

    def _populate_ports(self):
        self._all_ports = []
        device_map = {d["id"]: d for d in self._data.get("devices", [])}

        for site in get_all_sites(self._data):
            # company filter: sla sites van andere bedrijven over
            if self._company_site_ids and site["id"] not in self._company_site_ids:
                continue
            site_name = site.get("name", "?")
            for room in site.get("rooms", []):
                room_name = room.get("name", "?")
                for rack in room.get("racks", []):
                    rack_name = rack.get("name", "?")
                    for slot in rack.get("slots", []):
                        dev_id = slot.get("device_id", "")
                        dev    = device_map.get(dev_id)
                        if not dev:
                            continue
                        dev_name  = dev.get("name", dev_id)
                        dev_type  = t(f"device_{dev.get('type', 'other')}")
                        dev_label = (
                            f"{site_name}  —  {room_name}  —  "
                            f"{rack_name}  —  {dev_name}  ({dev_type})"
                        )
                        ports = [
                            p for p in self._data.get("ports", [])
                            if p.get("device_id") == dev_id
                        ]
                        for port in sorted(ports, key=self._port_sort_key):
                            pid      = port.get("id", "")
                            pname    = port.get("name", pid)
                            side     = port.get("side", "")
                            side_lbl = (
                                t("label_front") if side == "front"
                                else t("label_back") if side == "back"
                                else side.upper()
                            )
                            label  = f"{dev_label}  ·  {pname}  ({side_lbl})"
                            in_use = pid in self._connected_ports
                            # 1.2.0 — keten-label: toon verbonden poort bij in-gebruik items
                            chain = self._port_chain_label.get(pid, "")
                            if in_use and chain:
                                label = f"{label}  →  {chain}"
                            self._all_ports.append({
                                "label":  label,
                                "id":     pid,
                                "in_use": in_use,
                                "chain":  chain,
                            })

        self._filter_ports()

    def _filter_ports(self, text: str = ""):
        self._list.clear()
        q      = (text or self._search.text()).strip().lower()
        free   = [p for p in self._all_ports if not p["in_use"]]
        in_use = [p for p in self._all_ports if     p["in_use"]]
        for item_data in free + in_use:
            if q and q not in item_data["label"].lower():
                continue
            suffix = f"  ({t('lbl_already_connected')})" if item_data["in_use"] else ""
            item   = QListWidgetItem(item_data["label"] + suffix)
            if item_data["in_use"]:
                item.setForeground(QColor("#888888"))
            item.setData(_USER_ROLE, item_data["id"])
            item.setData(_IN_USE_ROLE, item_data["in_use"])
            self._list.addItem(item)

    @staticmethod
    def _port_sort_key(p: dict):
        name  = p.get("name", "")
        parts = [int(c) if c.isdigit() else c.lower()
                 for c in re.split(r"(\d+)", name)]
        side_order = 0 if p.get("side") == "front" else (
                     1 if p.get("side") == "back"  else 2)
        return (side_order, parts)

    # ------------------------------------------------------------------
    # Auto-suggestie bij selectie van bezette poort
    # ------------------------------------------------------------------

    def _on_item_changed(self, current, previous):
        """1.3.0 — Uitgebreide auto-suggestie.
        Stap 1: bezette poort A is verbonden met poort B.
          Als B vrij → selecteer B.
          Als B ook bezet → stap 2.
        Stap 2: zoek de tegenovergestelde side (front↔back) van B
          op hetzelfde device en poortnummer.
          Als die vrij → selecteer die (patchpanel doorverbinding).
          Zo werkt: switch→patch front (bezet) → auto naar patch back (vrij).
        """
        self._banner.hide()
        if not current:
            return
        in_use = current.data(_IN_USE_ROLE)
        if not in_use:
            return

        port_id = current.data(_USER_ROLE)
        chain_label = self._port_chain_label.get(port_id, "")

        # Stap 1: zoek directe partner (poort waarmee verbonden)
        partner_id = ""
        for conn in self._data.get("connections", []):
            ft, fid = conn.get("from_type", ""), conn.get("from_id", "")
            tt, tid = conn.get("to_type",   ""), conn.get("to_id",   "")
            if ft == "port" and tt == "port":
                if fid == port_id: partner_id = tid; break
                if tid == port_id: partner_id = fid; break

        if not partner_id:
            if chain_label:
                self._banner.setText(f"ℹ️  Verbonden met: {chain_label}")
                self._banner.show()
            return

        # Is de directe partner vrij?
        if partner_id not in self._connected_ports:
            self._select_port_in_list(partner_id, chain_label)
            return

        # Stap 2: partner is ook bezet.
        # Zoek de tegenovergestelde side van de partner op hetzelfde device.
        # Gebruik geval: switch→patch FRONT (bezet) → zoek patch BACK (zelfde nr, zelfde device)
        port_map  = {p["id"]: p for p in self._data.get("ports", [])}
        partner_p = port_map.get(partner_id)
        opposite_id = ""
        opposite_label = ""
        if partner_p:
            partner_dev_id  = partner_p.get("device_id", "")
            partner_number  = partner_p.get("number", -1)
            partner_side    = partner_p.get("side", "")
            opposite_side   = "back" if partner_side == "front" else "front"
            # Zoek poort op zelfde device, zelfde nummer, tegenovergestelde side
            for p in self._data.get("ports", []):
                if (p.get("device_id") == partner_dev_id
                        and p.get("number") == partner_number
                        and p.get("side") == opposite_side
                        and p["id"] != partner_id):
                    opposite_id = p["id"]
                    opposite_label = self._make_port_label(
                        opposite_id, port_map,
                        {d["id"]: d for d in self._data.get("devices", [])}
                    )
                    break

        if opposite_id and opposite_id not in self._connected_ports:
            # Tegenovergestelde side is vrij → selecteer automatisch
            self._select_port_in_list(opposite_id, opposite_label)
        else:
            # Geen vrije poort gevonden — toon info
            msg = f"ℹ️  Verbonden met: {chain_label}"
            if opposite_id:
                msg += f"  —  tegenpoort ({opposite_label}) is ook in gebruik."
            self._banner.setText(msg)
            self._banner.show()

    def _select_port_in_list(self, port_id: str, label: str):
        """Zoek port_id in de lijst, selecteer en scroll ernaar, toon banner.
        1.4.0: als poort niet zichtbaar is door actieve zoekterm
        (bv. 'SWALAN' maar vrije poort is PATCH A2 BACK)
        wis dan de zoekbalk zodat alle poorten zichtbaar worden,
        en selecteer dan de juiste poort.
        """
        # Eerste poging: zoek in huidige gefilterde lijst
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item and item.data(_USER_ROLE) == port_id:
                self._list.blockSignals(True)
                self._list.setCurrentRow(i)
                self._list.scrollToItem(item)
                self._list.blockSignals(False)
                self._banner.setText(
                    f"🔀  Automatisch omgeleid naar vrije koppelpoort: {label}"
                )
                self._banner.show()
                return

        # Poort niet zichtbaar door zoekfilter — wis zoekbalk en herlaad
        self._search.blockSignals(True)
        self._search.clear()
        self._search.blockSignals(False)
        self._filter_ports("")  # herlaad volledige lijst

        # Tweede poging: zoek opnieuw in volledige lijst
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item and item.data(_USER_ROLE) == port_id:
                self._list.blockSignals(True)
                self._list.setCurrentRow(i)
                self._list.scrollToItem(item)
                self._list.blockSignals(False)
                self._banner.setText(
                    f"🔀  Automatisch omgeleid naar vrije koppelpoort: {label}"
                    f"  (zoekfilter gewist)"
                )
                self._banner.show()
                return

        # Poort echt niet beschikbaar (andere company of niet in data)
        self._banner.setText(
            f"ℹ️  Vrije koppelpoort ({label}) niet beschikbaar in de lijst."
        )
        self._banner.show()

    # ------------------------------------------------------------------
    # Opslaan
    # ------------------------------------------------------------------

    def _on_save(self):
        item = self._list.currentItem()
        if not item or not item.data(_USER_ROLE):
            QMessageBox.warning(self, self.windowTitle(), t("err_no_port_selected"))
            return

        port_id = item.data(_USER_ROLE)
        in_use  = item.data(_IN_USE_ROLE)

        if in_use:
            reply = QMessageBox.question(
                self, self.windowTitle(),
                t("warn_port_already_connected"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        existing_ids = {c["id"] for c in self._data.get("connections", [])}
        new_id = f"conn{len(existing_ids) + 1}"
        while new_id in existing_ids:
            new_id += "_"

        self._result = {
            "id":         new_id,
            "from_id":    self._outlet_id,
            "from_type":  "wall_outlet",
            "to_id":      port_id,
            "to_type":    "port",
            "cable_type": self._ddl_cable.currentData(),
            "label":      "",
            "notes":      self._notes.text().strip(),
        }
        self.accept()

    def get_result(self) -> dict | None:
        return self._result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_port_label(port_id: str, port_map: dict, device_map: dict) -> str:
        """Geeft een leesbaar label terug voor een poort: 'Device — Poort (SIDE)'."""
        port = port_map.get(port_id)
        if not port:
            return port_id
        dev = device_map.get(port.get("device_id", ""), {})
        dev_name  = dev.get("name", "?")
        port_name = port.get("name", port_id)
        side      = port.get("side", "")
        side_lbl  = (
            t("label_front") if side == "front"
            else t("label_back") if side == "back"
            else side.upper()
        )
        return f"{dev_name}  —  {port_name}  ({side_lbl})"

    @staticmethod
    def _find_outlet(outlet_id: str, data: dict) -> dict | None:
        """Zoek een wandpunt op via ID."""
        for site in get_all_sites(data):
            for room in site.get("rooms", []):
                for wo in room.get("wall_outlets", []):
                    if wo["id"] == outlet_id:
                        return wo
        return None