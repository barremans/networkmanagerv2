# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/port_dialog.py
# Role:    Poorten beheren per device — naam + VLAN per poort
# Version: 1.1.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie: poortnamen bewerken + VLAN toewijzen
#          1.1.0 — VLAN DDL uit vlan_config ipv vrij tekstveld
#                  Propagatie logica via vlan_service
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QGroupBox, QPushButton,
    QScrollArea, QWidget, QFrame, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt
from app.helpers.i18n import t
from app.services.vlan_service import load_vlans


def _build_vlan_ddl(current_vlan=None) -> QComboBox:
    """Bouw een VLAN DDL gevuld vanuit vlan_config."""
    ddl = QComboBox()
    ddl.addItem("— geen VLAN —", None)
    for v in load_vlans():
        label = f"VLAN {v['id']}"
        if v.get("name"):
            label += f"  —  {v['name']}"
        ddl.addItem(label, v["id"])
    # Selecteer huidig VLAN
    if current_vlan is not None:
        for i in range(ddl.count()):
            if ddl.itemData(i) == int(current_vlan):
                ddl.setCurrentIndex(i)
                break
    return ddl


class PortDialog(QDialog):
    """
    Bewerk poortnamen en wijs VLAN toe per poort via DDL.
    VLAN opties geladen uit vlan_config.json via vlan_service.
    """

    def __init__(self, parent=None, device: dict = None, ports: list = None):
        super().__init__(parent)
        self._device = device or {}
        self._ports  = [dict(p) for p in (ports or [])]
        self._rows   = {}   # port_id → {"name": QLineEdit, "vlan": QComboBox}

        name = self._device.get("name", t("label_device"))
        self.setWindowTitle(f"⬡  {t('label_port')} — {name}")
        self.setMinimumWidth(540)
        self.setMinimumHeight(400)
        self.setModal(True)
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setSpacing(8)
        outer.setContentsMargins(12, 12, 12, 12)

        dev_type = self._device.get("type", "")
        info_lbl = QLabel(
            f"{self._device.get('name', '')}  ·  "
            f"{t(f'device_{dev_type}') if dev_type else ''}"
        )
        info_lbl.setObjectName("secondary")
        outer.addWidget(info_lbl)

        # Info VLAN propagatie
        prop_lbl = QLabel(
            "ℹ  VLAN wijzigingen worden automatisch gepropageerd "
            "naar de volledige trace (patchpaneel, switch, wandpunt)."
        )
        prop_lbl.setObjectName("secondary")
        prop_lbl.setWordWrap(True)
        outer.addWidget(prop_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(8)
        content_layout.setContentsMargins(0, 0, 4, 0)

        front_count = self._device.get("front_ports", 0)
        sfp_count   = self._device.get("sfp_ports", 0)

        copper_ports = [p for p in self._ports
                        if p["side"] == "front" and p.get("number", 0) <= front_count]
        sfp_ports    = [p for p in self._ports
                        if p["side"] == "front" and p.get("number", 0) > front_count]
        back_ports   = [p for p in self._ports if p["side"] == "back"]

        if copper_ports:
            content_layout.addWidget(self._build_section(
                f"⬡  {t('label_front_ports')}  ({len(copper_ports)})",
                sorted(copper_ports, key=lambda p: p["number"])
            ))
        if sfp_ports:
            content_layout.addWidget(self._build_section(
                f"SFP  ({len(sfp_ports)})",
                sorted(sfp_ports, key=lambda p: p["number"])
            ))
        if back_ports:
            content_layout.addWidget(self._build_section(
                f"⬡  {t('label_back_ports')}  ({len(back_ports)})",
                sorted(back_ports, key=lambda p: p["number"])
            ))

        if not (copper_ports or sfp_ports or back_ports):
            empty = QLabel("(geen poorten)")
            empty.setObjectName("secondary")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            content_layout.addWidget(empty)

        content_layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_save   = QPushButton(t("btn_save"))
        btn_cancel = QPushButton(t("btn_cancel"))
        btn_save.clicked.connect(self._on_save)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        outer.addLayout(btn_layout)

    def _build_section(self, title: str, ports: list) -> QGroupBox:
        grp  = QGroupBox(title)
        form = QFormLayout(grp)
        form.setSpacing(5)
        form.setContentsMargins(10, 10, 10, 10)

        # Kolomlabels
        hdr = QHBoxLayout()
        lbl_name = QLabel(t("label_name"))
        lbl_name.setObjectName("secondary")
        lbl_vlan = QLabel("VLAN")
        lbl_vlan.setObjectName("secondary")
        lbl_vlan.setFixedWidth(200)
        hdr.addWidget(lbl_name)
        hdr.addWidget(lbl_vlan)
        form.addRow("", hdr)

        for port in ports:
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.setSpacing(6)

            name_edit = QLineEdit(port.get("name", f"Port {port['number']}"))
            name_edit.setMinimumWidth(140)

            vlan_ddl = _build_vlan_ddl(port.get("vlan"))
            vlan_ddl.setFixedWidth(200)

            row_l.addWidget(name_edit)
            row_l.addWidget(vlan_ddl)

            num_lbl = QLabel(f"#{port['number']}")
            num_lbl.setObjectName("secondary")
            num_lbl.setFixedWidth(32)
            num_lbl.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            form.addRow(num_lbl, row_w)

            self._rows[port["id"]] = {
                "name": name_edit,
                "vlan": vlan_ddl,
            }
        return grp

    def _on_save(self):
        for port in self._ports:
            widgets = self._rows.get(port["id"])
            if widgets:
                port["name"] = widgets["name"].text().strip() or port["name"]
                vlan_val     = widgets["vlan"].currentData()
                if vlan_val is not None:
                    port["vlan"] = int(vlan_val)
                elif "vlan" in port:
                    del port["vlan"]
        self.accept()

    def get_result(self) -> list:
        return self._ports