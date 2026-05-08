# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/move_connection_dialog.py
# Role:    Dialoog — verbinding verplaatsen naar een andere vrije poort
# Version: 1.2.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie
#          1.1.0 — UX verbetering: scope filter (zelfde rack / ruimte / site)
#          1.2.0 — Sortering DDL: zelfde device eerst, dan zelfde type, dan rest
#                  Standaard: zelfde rack
#                  Nooit poorten van andere site
#                  Teller toont beschikbare poorten per scope
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QPushButton, QMessageBox,
)
from PySide6.QtCore import Qt

from app.helpers.i18n import t

_SCOPE_RACK = "rack"
_SCOPE_ROOM = "room"
_SCOPE_SITE = "site"


class MoveConnectionDialog(QDialog):
    """
    Verplaats een bestaande verbinding naar een andere vrije poort.
    De verbinding zelf blijft intact. Alleen de poort-kant wordt vervangen.

    Scope filter (3 knoppen):
    - Zelfde rack  (standaard)
    - Zelfde ruimte
    - Hele site
    Nooit poorten van een andere site.
    """

    def __init__(
        self,
        parent=None,
        data: dict | None = None,
        connection: dict | None = None,
        port_id: str = "",
    ):
        super().__init__(parent)

        self._data       = data or {}
        self._connection = connection or {}
        self._port_id    = port_id
        self._result_port_id: str | None = None
        self._scope = _SCOPE_RACK

        self._current_site_id, self._current_room_id, self._current_rack_id = \
            self._find_port_context(port_id)

        # Device en type van de huidige poort (voor sortering)
        _cur_port = next((p for p in self._data.get("ports", []) if p["id"] == port_id), {})
        self._current_dev_id   = _cur_port.get("device_id", "")
        _cur_dev = next((d for d in self._data.get("devices", [])
                         if d["id"] == self._current_dev_id), {})
        self._current_dev_type = _cur_dev.get("type", "")

        self._build_ui()
        self._populate_ports()

    # ------------------------------------------------------------------
    # Context opzoeken
    # ------------------------------------------------------------------

    def _find_port_context(self, port_id: str) -> tuple[str, str, str]:
        port  = next((p for p in self._data.get("ports", []) if p["id"] == port_id), None)
        if not port:
            return "", "", ""
        dev_id = port.get("device_id", "")
        for site in self._data.get("sites", []):
            for room in site.get("rooms", []):
                for rack in room.get("racks", []):
                    for slot in rack.get("slots", []):
                        if slot.get("device_id") == dev_id:
                            return site["id"], room["id"], rack["id"]
        return "", "", ""

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.setWindowTitle(t("ctx_move_port_connection"))
        self.setModal(True)
        self.setMinimumWidth(560)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # Samenvatting huidige verbinding
        info = QLabel(self._build_connection_summary())
        info.setWordWrap(True)
        info.setObjectName("secondary")
        root.addWidget(info)

        # Scope knoppen
        scope_row = QHBoxLayout()
        scope_row.setSpacing(6)
        lbl = QLabel(t("move_conn_scope") + ":")
        lbl.setFixedWidth(80)
        scope_row.addWidget(lbl)

        self._btn_rack = QPushButton(t("move_conn_scope_rack"))
        self._btn_rack.setCheckable(True)
        self._btn_rack.setChecked(True)
        self._btn_rack.clicked.connect(lambda: self._set_scope(_SCOPE_RACK))

        self._btn_room = QPushButton(t("move_conn_scope_room"))
        self._btn_room.setCheckable(True)
        self._btn_room.clicked.connect(lambda: self._set_scope(_SCOPE_ROOM))

        self._btn_site = QPushButton(t("move_conn_scope_site"))
        self._btn_site.setCheckable(True)
        self._btn_site.clicked.connect(lambda: self._set_scope(_SCOPE_SITE))

        self._scope_btns = [self._btn_rack, self._btn_room, self._btn_site]
        for btn in self._scope_btns:
            btn.setFixedHeight(26)
            scope_row.addWidget(btn)

        scope_row.addStretch()
        root.addLayout(scope_row)

        # Poort dropdown + teller
        form = QFormLayout()
        form.setSpacing(8)

        self._cmb_port  = QComboBox()
        self._cmb_port.setMinimumWidth(380)
        self._lbl_count = QLabel("")
        self._lbl_count.setObjectName("secondary")

        port_row = QHBoxLayout()
        port_row.addWidget(self._cmb_port)
        port_row.addWidget(self._lbl_count)
        form.addRow(f"{t('move_conn_new_port')}:", port_row)
        root.addLayout(form)

        # OK / Annuleren
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._btn_ok = QPushButton(t("btn_save"))
        self._btn_ok.setDefault(True)
        self._btn_ok.clicked.connect(self._on_ok)
        btn_row.addWidget(self._btn_ok)

        btn_cancel = QPushButton(t("btn_cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        root.addLayout(btn_row)

    def _build_connection_summary(self) -> str:
        ports = {p["id"]: p for p in self._data.get("ports", [])}
        devs  = {d["id"]: d for d in self._data.get("devices", [])}
        conn  = self._connection

        def _lbl(pid):
            p = ports.get(pid, {})
            d = devs.get(p.get("device_id", ""), {})
            return f"{d.get('name','?')} \u2014 {p.get('name','?')} ({p.get('side','').upper()})"

        from_lbl = _lbl(conn.get("from_id", ""))
        to_type  = conn.get("to_type", "port")
        if to_type == "endpoint":
            ep = next((e for e in self._data.get("endpoints", [])
                       if e["id"] == conn.get("to_id")), None)
            to_lbl = f"\U0001f5a5 {ep.get('name', conn.get('to_id','?'))}" if ep else conn.get("to_id","?")
        else:
            to_lbl = _lbl(conn.get("to_id", ""))

        current_lbl = _lbl(self._port_id)
        cable = conn.get("cable_type", "")
        return (
            f"Huidige poort:  {current_lbl}\n"
            f"Verbinding:  {from_lbl}  \u2192  {to_lbl}"
            + (f"  [{cable}]" if cable else "")
        )

    # ------------------------------------------------------------------
    # Scope
    # ------------------------------------------------------------------

    def _set_scope(self, scope: str):
        self._scope = scope
        for btn, s in zip(self._scope_btns, [_SCOPE_RACK, _SCOPE_ROOM, _SCOPE_SITE]):
            btn.setChecked(s == scope)
        self._populate_ports()

    # ------------------------------------------------------------------
    # Populate
    # ------------------------------------------------------------------

    def _populate_ports(self):
        self._cmb_port.clear()

        # Gebruikte poorten — huidige verbinding telt niet mee
        used_port_ids = set()
        for conn in self._data.get("connections", []):
            if conn["id"] == self._connection.get("id"):
                continue
            used_port_ids.add(conn.get("from_id", ""))
            used_port_ids.add(conn.get("to_id", ""))

        dev_map   = {d["id"]: d for d in self._data.get("devices", [])}
        ports_map = {}  # dev_id -> [(port, rack_name)]

        for site in self._data.get("sites", []):
            if site["id"] != self._current_site_id:
                continue

            for room in site.get("rooms", []):
                if self._scope in (_SCOPE_RACK, _SCOPE_ROOM):
                    if room["id"] != self._current_room_id:
                        continue

                for rack in room.get("racks", []):
                    if self._scope == _SCOPE_RACK:
                        if rack["id"] != self._current_rack_id:
                            continue

                    rack_name = rack.get("name", "?")

                    for slot in rack.get("slots", []):
                        dev_id = slot.get("device_id")
                        if not dev_id:
                            continue
                        free_ports = [
                            p for p in self._data.get("ports", [])
                            if p.get("device_id") == dev_id
                            and p["id"] not in used_port_ids
                            and p["id"] != self._port_id
                        ]
                        if free_ports:
                            if dev_id not in ports_map:
                                ports_map[dev_id] = []
                            for port in free_ports:
                                ports_map[dev_id].append((port, rack_name))

        # Sortering: 0) zelfde device  1) zelfde type  2) rest
        def _sort_key(dev_id):
            if dev_id == self._current_dev_id:
                return 0
            dev = dev_map.get(dev_id, {})
            if dev.get("type", "") == self._current_dev_type:
                return 1
            return 2

        sorted_dev_ids = sorted(ports_map.keys(), key=_sort_key)

        count      = 0
        last_group = -1
        for dev_id in sorted_dev_ids:
            dev      = dev_map.get(dev_id, {})
            dev_name = dev.get("name", "?")
            group    = _sort_key(dev_id)

            # Scheidingslijn tussen groepen
            if last_group >= 0 and group != last_group:
                self._cmb_port.insertSeparator(self._cmb_port.count())
            last_group = group

            for port, rack_name in ports_map[dev_id]:
                if self._scope == _SCOPE_RACK:
                    label = f"{dev_name}  —  {port.get('name','?')} ({port.get('side','').upper()})"
                else:
                    label = f"{rack_name}  /  {dev_name}  —  {port.get('name','?')} ({port.get('side','').upper()})"
                self._cmb_port.addItem(label, port["id"])
                count += 1

        if count == 0:
            hint = ""
            if self._scope == _SCOPE_RACK:
                hint = f"  —  {t('move_conn_try_room')}"
            elif self._scope == _SCOPE_ROOM:
                hint = f"  —  {t('move_conn_try_site')}"
            self._cmb_port.addItem(t("move_conn_no_free_ports") + hint, "")
            self._btn_ok.setEnabled(False)
            self._lbl_count.setText("")
        else:
            self._btn_ok.setEnabled(True)
            self._lbl_count.setText(f"({count})")

    def _on_ok(self):
        new_port_id = self._cmb_port.currentData()
        if not new_port_id:
            QMessageBox.warning(self, self.windowTitle(), t("err_no_selection"))
            return
        self._result_port_id = new_port_id
        self.accept()

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def get_result_port_id(self) -> str | None:
        return self._result_port_id