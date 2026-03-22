# =============================================================================
# Networkmap_Creator
# File:    app/gui/vlan_manager_window.py
# Role:    VLAN definities beheren — apart venster
# Version: 1.1.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie
#          1.1.0 — IP adres en subnetmasker velden toegevoegd aan VLAN definitie
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QTextEdit, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QFrame,
    QColorDialog, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from app.services.vlan_service import load_vlans, save_vlans
from app.helpers.i18n import t

_DEFAULT_COLOR = "#4a9eda"


class VlanManagerWindow(QDialog):
    """
    Beheervenster voor VLAN definities.
    Lijst links — detail rechts.
    Wijzigingen worden direct opgeslagen via vlan_service.
    """
    vlans_changed = Signal()   # emit na elke wijziging

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔷  VLAN beheer")
        self.setMinimumSize(620, 440)
        self.setModal(True)
        self._vlans    = load_vlans()
        self._selected = None   # index in self._vlans
        self._build()
        self._refresh_list()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build(self):
        outer = QHBoxLayout(self)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── Lijst links ────────────────────────────────────────────────
        left = QFrame()
        left.setObjectName("left_frame")
        left.setFixedWidth(200)
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(8, 8, 8, 8)
        left_l.setSpacing(6)

        lbl = QLabel("VLANs")
        lbl.setObjectName("rack_title")
        left_l.addWidget(lbl)

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.currentRowChanged.connect(self._on_list_select)
        left_l.addWidget(self._list)

        btn_row = QHBoxLayout()
        self._btn_add = QPushButton("＋")
        self._btn_add.setFixedHeight(28)
        self._btn_add.setToolTip("Nieuw VLAN")
        self._btn_add.clicked.connect(self._on_add)
        self._btn_del = QPushButton("🗑")
        self._btn_del.setFixedHeight(28)
        self._btn_del.setToolTip("Verwijder VLAN")
        self._btn_del.clicked.connect(self._on_delete)
        self._btn_del.setEnabled(False)
        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_del)
        left_l.addLayout(btn_row)

        outer.addWidget(left)

        # ── Detail rechts ──────────────────────────────────────────────
        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(16, 16, 16, 16)
        right_l.setSpacing(10)

        self._detail_lbl = QLabel("Selecteer een VLAN of maak een nieuw aan.")
        self._detail_lbl.setObjectName("secondary")
        right_l.addWidget(self._detail_lbl)

        self._form_frame = QFrame()
        form_l = QFormLayout(self._form_frame)
        form_l.setSpacing(8)

        self._fld_id   = QSpinBox()
        self._fld_id.setRange(1, 4094)
        self._fld_id.setFixedWidth(100)

        self._fld_name = QLineEdit()
        self._fld_name.setPlaceholderText("bv. Clients")

        self._fld_ip = QLineEdit()
        self._fld_ip.setPlaceholderText("bv. 192.168.10.1")
        self._fld_ip.setMaxLength(45)  # IPv6 max lengte

        self._fld_subnet = QLineEdit()
        self._fld_subnet.setPlaceholderText("bv. 255.255.255.0  of  /24")
        self._fld_subnet.setMaxLength(45)

        self._fld_desc = QTextEdit()
        self._fld_desc.setFixedHeight(56)
        self._fld_desc.setPlaceholderText("Optionele beschrijving")

        # Kleur
        color_row = QHBoxLayout()
        self._color_preview = QFrame()
        self._color_preview.setFixedSize(24, 24)
        self._color_preview.setStyleSheet(
            f"background-color: {_DEFAULT_COLOR}; border-radius: 4px;"
        )
        self._color_val = _DEFAULT_COLOR
        btn_color = QPushButton("Kies kleur")
        btn_color.setFixedHeight(26)
        btn_color.clicked.connect(self._on_pick_color)
        color_row.addWidget(self._color_preview)
        color_row.addWidget(btn_color)
        color_row.addStretch()

        form_l.addRow("VLAN ID *:",      self._fld_id)
        form_l.addRow("Naam *:",         self._fld_name)
        form_l.addRow("IP adres:",       self._fld_ip)
        form_l.addRow("Subnetmasker:",   self._fld_subnet)
        form_l.addRow("Omschrijving:",   self._fld_desc)
        form_l.addRow("Kleur:",          color_row)

        right_l.addWidget(self._form_frame)
        self._form_frame.setVisible(False)

        save_row = QHBoxLayout()
        save_row.addStretch()
        self._btn_save = QPushButton(t("btn_save"))
        self._btn_save.setEnabled(False)
        self._btn_save.clicked.connect(self._on_save_entry)
        save_row.addWidget(self._btn_save)
        right_l.addLayout(save_row)

        right_l.addStretch()

        # Sluiten
        close_row = QHBoxLayout()
        close_row.addStretch()
        btn_close = QPushButton("Sluiten")
        btn_close.clicked.connect(self.accept)
        close_row.addWidget(btn_close)
        right_l.addLayout(close_row)

        outer.addWidget(right, stretch=1)

    # ------------------------------------------------------------------
    # Lijst
    # ------------------------------------------------------------------

    def _refresh_list(self):
        self._list.blockSignals(True)
        self._list.clear()
        for v in self._vlans:
            color = v.get("color", _DEFAULT_COLOR)
            name  = v.get("name", "")
            label = f"VLAN {v['id']}" + (f"  —  {name}" if name else "")
            item  = QListWidgetItem(label)
            item.setForeground(QColor(color))
            self._list.addItem(item)
        self._list.blockSignals(False)
        if self._selected is not None and self._selected < len(self._vlans):
            self._list.setCurrentRow(self._selected)

    def _on_list_select(self, row: int):
        if row < 0 or row >= len(self._vlans):
            self._selected = None
            self._form_frame.setVisible(False)
            self._btn_save.setEnabled(False)
            self._btn_del.setEnabled(False)
            return
        self._selected = row
        v = self._vlans[row]
        self._fld_id.setValue(v.get("id", 1))
        self._fld_name.setText(v.get("name", ""))
        self._fld_ip.setText(v.get("ip", ""))
        self._fld_subnet.setText(v.get("subnet", ""))
        self._fld_desc.setPlainText(v.get("description", ""))
        color = v.get("color", _DEFAULT_COLOR)
        self._color_val = color
        self._color_preview.setStyleSheet(
            f"background-color: {color}; border-radius: 4px;"
        )
        self._detail_lbl.setText(f"VLAN {v['id']}")
        self._form_frame.setVisible(True)
        self._btn_save.setEnabled(True)
        self._btn_del.setEnabled(True)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def _on_add(self):
        # Zoek eerstvolgende vrije ID
        used = {v["id"] for v in self._vlans}
        new_id = next((i for i in range(1, 4095) if i not in used), 1)
        new_vlan = {"id": new_id, "name": "", "description": "", "color": _DEFAULT_COLOR, "ip": "", "subnet": ""}
        self._vlans.append(new_vlan)
        self._selected = len(self._vlans) - 1
        self._refresh_list()
        self._list.setCurrentRow(self._selected)
        self._fld_name.setFocus()

    def _on_delete(self):
        if self._selected is None:
            return
        v = self._vlans[self._selected]
        reply = QMessageBox.question(
            self, "VLAN verwijderen",
            f"VLAN {v['id']} — {v.get('name', '')} verwijderen?\n\n"
            f"Poorten en wandpunten behouden hun VLAN nummer\n"
            f"maar de definitie (naam, kleur) wordt verwijderd.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._vlans.pop(self._selected)
        self._selected = None
        save_vlans(self._vlans)
        self._refresh_list()
        self._form_frame.setVisible(False)
        self._btn_save.setEnabled(False)
        self._btn_del.setEnabled(False)
        self.vlans_changed.emit()

    def _on_save_entry(self):
        if self._selected is None:
            return
        new_id = self._fld_id.value()
        name   = self._fld_name.text().strip()
        if not name:
            QMessageBox.warning(self, "VLAN", "Naam is verplicht.")
            return

        # Duplicaat ID check
        for i, v in enumerate(self._vlans):
            if v["id"] == new_id and i != self._selected:
                QMessageBox.warning(
                    self, "VLAN",
                    f"VLAN {new_id} bestaat al ({v.get('name', '')})."
                )
                return

        self._vlans[self._selected] = {
            "id":          new_id,
            "name":        name,
            "ip":          self._fld_ip.text().strip(),
            "subnet":      self._fld_subnet.text().strip(),
            "description": self._fld_desc.toPlainText().strip(),
            "color":       self._color_val,
        }
        save_vlans(self._vlans)
        self._refresh_list()
        self.vlans_changed.emit()
        self._detail_lbl.setText(f"✓  VLAN {new_id} opgeslagen.")

    def _on_pick_color(self):
        color = QColorDialog.getColor(
            QColor(self._color_val), self, "Kies VLAN kleur"
        )
        if color.isValid():
            self._color_val = color.name()
            self._color_preview.setStyleSheet(
                f"background-color: {self._color_val}; border-radius: 4px;"
            )