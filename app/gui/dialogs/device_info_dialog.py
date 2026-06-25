# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/device_info_dialog.py
# Role:    Readonly device info popup — dubbelklik op device in rack_view
# Version: 1.3.0
# Author:  Barremans
# Changes: 1.3.0 — F7: poortrijen (front/back/SFP) alleen tonen als het device
#                   ze heeft (type-afhankelijke zichtbaarheid, geen "0"-rijen).
#                   F8: per veld kopiëren via rechtsklik ("Kopiëren"); MAC wordt
#                   genormaliseerd (AA:BB:CC:DD:EE:FF). Locatiebanner en VLAN-
#                   waarden eveneens kopieerbaar.
#          1.2.0 — slot parameter toegevoegd: toont U-positie in locatie banner
#                   "🗄 Rack 01  ·  U35  ·  🚪 SERVERRUIMTE  ·  📍 CGK Gullegem"
#          1.1.0 — Subnetmasker toegevoegd aan info popup (na IP adres)
#          1.0.0 — Initiële versie
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QGroupBox, QPushButton, QFrame, QScrollArea, QWidget,
    QApplication, QMenu
)
from PySide6.QtCore import Qt
from app.helpers.i18n import t
from app.helpers.formatting import normalize_mac


def _val(v) -> str:
    """Geeft '—' terug als waarde leeg/None is."""
    if v is None:
        return "—"
    s = str(v).strip()
    return s if s else "—"


class DeviceInfoDialog(QDialog):
    """
    Readonly popup met alle velden van een device.
    Geopend via rechtsklik "Detail tonen" in het zoekvenster.
    """

    def __init__(self, parent=None, device: dict = None, data: dict = None,
                 rack: dict = None, room: dict = None, site: dict = None,
                 slot: dict = None):
        super().__init__(parent)
        self._device = device or {}
        self._data   = data   or {}
        self._rack   = rack   or {}
        self._room   = room   or {}
        self._site   = site   or {}
        self._slot   = slot   or {}

        self.setWindowTitle(f"ℹ  {self._device.get('name', t('label_device'))}")
        self.setMinimumWidth(460)
        self.setModal(True)
        self._build()

    # ------------------------------------------------------------------
    # Klembord-helpers (F8 — per veld kopiëren)
    # ------------------------------------------------------------------

    def _copy_to_clipboard(self, value: str):
        value = (value or "").strip()
        if value:
            QApplication.clipboard().setText(value)

    def _make_value_label(self, text: str, copy_value: str = None) -> QLabel:
        """
        Waarde-label dat selecteerbaar is en — als copy_value gevuld is —
        via rechtsklik een "Kopiëren"-menu toont.
        """
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        cv = (copy_value if copy_value is not None else text)
        cv = (cv or "").strip()
        if cv and cv != "—":
            lbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            lbl.customContextMenuRequested.connect(
                lambda pos, w=lbl, v=cv: self._show_value_menu(w, pos, v)
            )
        return lbl

    def _show_value_menu(self, widget: QLabel, pos, value: str):
        menu = QMenu(widget)
        act_copy = menu.addAction(t("ctx_copy"))
        if menu.exec(widget.mapToGlobal(pos)) == act_copy:
            self._copy_to_clipboard(value)

    # ------------------------------------------------------------------
    # Opbouw
    # ------------------------------------------------------------------

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setSpacing(10)
        outer.setContentsMargins(12, 12, 12, 12)

        # ── Locatie banner ─────────────────────────────────────────────
        loc_frame = QFrame()
        loc_frame.setObjectName("rack_frame")
        loc_l = QHBoxLayout(loc_frame)
        loc_l.setContentsMargins(10, 6, 10, 6)

        # U-positie uit slot
        u_start = self._slot.get("u_start", "")
        height  = self._slot.get("height", 1)
        if u_start != "":
            try:
                u_start = int(u_start)
                height  = int(height) if height else 1
                if height > 1:
                    u_str = f"U{u_start}–U{u_start + height - 1}  ({height}U)"
                else:
                    u_str = f"U{u_start}"
            except (ValueError, TypeError):
                u_str = f"U{u_start}"
            u_part = f"  ·  {u_str}"
        else:
            u_part = ""

        rack_lbl = QLabel(
            f"🗄  {self._rack.get('name', '—')}{u_part}  ·  "
            f"🚪  {self._room.get('name', '—')}  ·  "
            f"📍  {self._site.get('name', '—')}"
        )
        rack_lbl.setObjectName("secondary")

        # F8 — locatie kopiëren (platte tekst: site · ruimte · rack[ · U..])
        loc_parts = [p for p in (
            self._site.get("name", ""),
            self._room.get("name", ""),
            self._rack.get("name", ""),
            (u_str if u_start != "" else ""),
        ) if p]
        loc_copy = " · ".join(loc_parts)
        if loc_copy:
            rack_lbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            rack_lbl.customContextMenuRequested.connect(
                lambda pos, w=rack_lbl, v=loc_copy: self._show_value_menu(w, pos, v)
            )

        loc_l.addWidget(rack_lbl)
        outer.addWidget(loc_frame)

        # ── Device info ────────────────────────────────────────────────
        grp = QGroupBox(t("label_device"))
        form = QFormLayout(grp)
        form.setSpacing(8)
        form.setContentsMargins(12, 12, 12, 12)

        dev_type   = self._device.get("type", "")
        type_label = t(f"device_{dev_type}") if dev_type else "—"

        # Poortaantallen — voor type-afhankelijke zichtbaarheid (F7)
        def _as_int(v):
            try:
                return int(v)
            except (ValueError, TypeError):
                return 0
        front_n = _as_int(self._device.get("front_ports", 0))
        back_n  = _as_int(self._device.get("back_ports", 0))
        sfp_n   = _as_int(self._device.get("sfp_ports", 0))

        mac_raw  = self._device.get("mac", "")
        mac_copy = normalize_mac(mac_raw) if str(mac_raw).strip() else None

        # (label, weergavewaarde, altijd tonen, kopieerwaarde)
        rows = [
            (t("label_name"),   _val(self._device.get("name")),   True,  None),
            (t("label_type"),   type_label,                       True,  None),
            (t("label_brand"),  _val(self._device.get("brand")),  False, None),
            (t("label_model"),  _val(self._device.get("model")),  False, None),
            (t("label_ip"),     _val(self._device.get("ip")),     False, None),
            (t("label_subnet"), _val(self._device.get("subnet")), False, None),
            (t("label_mac"),    _val(mac_raw),                    False, mac_copy),
            (t("label_serial"), _val(self._device.get("serial")), False, None),
        ]

        # Poortrijen alleen tonen wanneer het device poorten heeft (F7)
        if front_n:
            rows.append((t("label_front_ports"), str(front_n), True, None))
        if back_n:
            rows.append((t("label_back_ports"), str(back_n), True, None))
        if sfp_n:
            rows.append((t("label_sfp_ports"), str(sfp_n), True, None))

        notes = self._device.get("notes", "").strip()
        if notes:
            rows.append((t("label_notes"), notes, True, None))

        for label, value, always_show, copy_value in rows:
            if not always_show and value == "—":
                continue
            lbl = QLabel(label + ":")
            lbl.setObjectName("secondary")
            val_lbl = self._make_value_label(value, copy_value)
            form.addRow(lbl, val_lbl)

        outer.addWidget(grp)

        # ── Poorten met VLAN ──────────────────────────────────────────
        ports = [p for p in self._data.get("ports", [])
                 if p["device_id"] == self._device.get("id")]
        vlan_ports = [p for p in ports if p.get("vlan")]

        if vlan_ports:
            grp_vlan = QGroupBox("VLAN")
            vlan_form = QFormLayout(grp_vlan)
            vlan_form.setSpacing(6)
            vlan_form.setContentsMargins(12, 12, 12, 12)

            for p in sorted(vlan_ports, key=lambda x: (x["side"], x["number"])):
                side = "VOOR" if p["side"] == "front" else "ACHTER"
                lbl = QLabel(f"{p['name']}  ({side}):")
                lbl.setObjectName("secondary")
                vlan_lbl = self._make_value_label(
                    f"VLAN {p['vlan']}", str(p["vlan"])
                )
                vlan_form.addRow(lbl, vlan_lbl)

            outer.addWidget(grp_vlan)

        # ── Sluiten knop ───────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("Sluiten")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        outer.addLayout(btn_layout)