# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/connect_to_outlet_dialog.py
# Role:    Poort ↔ Wandpunt verbinding aanmaken
# Version: 1.2.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie
#          1.1.0 — Ruimtestap verwijderd, alle wandpunten van site direct zichtbaar
#          1.2.0 — Fix: locatie key vertaald via get_outlet_location_label()
#                  ipv raw key tonen (bv. containerd_a → Container D (A))
# =============================================================================
#
# Gebruik: rechtermuisklik op een patchpanel-poort → "Verbinden met wandpunt"
# De poort is reeds bekend (port_id). De gebruiker kiest:
#   - Site → Ruimte → Wandpunt (cascade DDL, alleen vrije wandpunten)
#   - Kabeltype
#   - Notitie
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QComboBox, QTextEdit, QPushButton, QMessageBox, QFrame
)
from PySide6.QtCore import Qt
from app.helpers.i18n import t
from app.helpers.settings_storage import get_outlet_location_label
from app.helpers.i18n import get_language

_CABLE_TYPES = [
    ("utp_cat5e",  "cable_utp_cat5e"),
    ("utp_cat6",   "cable_utp_cat6"),
    ("utp_cat6a",  "cable_utp_cat6a"),
    ("fiber_sm",   "cable_fiber_sm"),
    ("fiber_mm",   "cable_fiber_mm"),
    ("dak",        "cable_dak"),
    ("other",      "cable_other"),
]


class ConnectToOutletDialog(QDialog):
    """
    Dialoog om een poort te verbinden met een wandpunt.
    port_id en port_label zijn al bekend — alleen wandpunt kiezen.
    """

    def __init__(self, data: dict, port_id: str, port_label: str, parent=None):
        super().__init__(parent)
        self._data       = data
        self._port_id    = port_id
        self._port_label = port_label
        self._result     = None

        self.setWindowTitle(t("dlg_connect_outlet_title"))
        self.setMinimumWidth(440)
        self.setModal(True)
        self._build()

    # ------------------------------------------------------------------
    # UI opbouw
    # ------------------------------------------------------------------

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Poort info (alleen lezen) ────────────────────────────────
        grp_port = QGroupBox(t("label_port"))
        port_form = QFormLayout(grp_port)
        port_lbl = QLabel(self._port_label)
        port_lbl.setObjectName("device-label")
        port_form.addRow("", port_lbl)
        layout.addWidget(grp_port)

        # ── Wandpunt kiezen ──────────────────────────────────────────
        grp_outlet = QGroupBox(t("label_wall_outlet"))
        outlet_form = QFormLayout(grp_outlet)
        outlet_form.setSpacing(8)

        self._ddl_site   = QComboBox()
        self._ddl_outlet = QComboBox()

        self._ddl_outlet.setEnabled(False)

        # Vul sites
        self._ddl_site.addItem(f"— {t('label_site')} —", "")
        for site in self._data.get("sites", []):
            # Alleen sites tonen die wandpunten hebben
            all_outlets = [wo for r in site.get("rooms", [])
                           for wo in r.get("wall_outlets", [])]
            if all_outlets:
                self._ddl_site.addItem(site["name"], site["id"])

        self._ddl_site.currentIndexChanged.connect(self._on_site_changed)

        outlet_form.addRow(t("label_site")        + ":", self._ddl_site)
        outlet_form.addRow(t("label_wall_outlet") + ":", self._ddl_outlet)
        layout.addWidget(grp_outlet)

        # ── Kabeltype ────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        cable_row = QHBoxLayout()
        cable_row.addWidget(QLabel(t("label_cable_type") + ":"))
        self._ddl_cable = QComboBox()
        for val, key in _CABLE_TYPES:
            self._ddl_cable.addItem(t(key), val)
        self._ddl_cable.setCurrentIndex(1)   # standaard UTP Cat6
        cable_row.addWidget(self._ddl_cable)
        cable_row.addStretch()
        layout.addLayout(cable_row)

        # ── Notitie ──────────────────────────────────────────────────
        notes_form = QFormLayout()
        self._notes = QTextEdit()
        self._notes.setFixedHeight(48)
        self._notes.setPlaceholderText(t("label_notes") + "...")
        notes_form.addRow(t("label_notes") + ":", self._notes)
        layout.addLayout(notes_form)

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
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Cascade handlers
    # ------------------------------------------------------------------

    def _on_site_changed(self):
        site_id = self._ddl_site.currentData()
        self._ddl_outlet.clear()
        self._ddl_outlet.setEnabled(False)

        if not site_id:
            return
        site = next((s for s in self._data["sites"] if s["id"] == site_id), None)
        if not site:
            return

        # Wandpunten die al verbonden zijn
        connected_outlets = set()
        for conn in self._data.get("connections", []):
            if conn.get("from_type") == "wall_outlet":
                connected_outlets.add(conn["from_id"])
            if conn.get("to_type") == "wall_outlet":
                connected_outlets.add(conn["to_id"])

        self._ddl_outlet.addItem(f"— {t('label_wall_outlet')} —", "")

        # Alle ruimtes van de site, elk met hun wandpunten
        for room in site.get("rooms", []):
            outlets = room.get("wall_outlets", [])
            if not outlets:
                continue
            for wo in sorted(outlets, key=lambda w: w.get("name", "")):
                loc_key = wo.get("location_description", "")
                loc_label = get_outlet_location_label(loc_key, get_language()) if loc_key else ""
                # Label: Ruimte — Wandpuntnaam — Locatie (vertaald)
                name_parts = [room["name"], wo["name"]]
                if loc_label:
                    name_parts.append(loc_label)
                label = "  —  ".join(name_parts)

                if wo["id"] in connected_outlets:
                    self._ddl_outlet.addItem(
                        f"⚠  {label}  ({t('err_port_in_use')})", wo["id"]
                    )
                else:
                    self._ddl_outlet.addItem(label, wo["id"])

        self._ddl_outlet.setEnabled(True)

    # ------------------------------------------------------------------
    # Opslaan
    # ------------------------------------------------------------------

    def _on_save(self):
        outlet_id  = self._ddl_outlet.currentData()
        cable_type = self._ddl_cable.currentData()

        if not outlet_id:
            QMessageBox.warning(self, t("dlg_connect_outlet_title"),
                                t("err_no_outlet_selected"))
            return

        # Controleer of dit wandpunt al verbonden is
        for conn in self._data.get("connections", []):
            if (conn.get("from_type") == "wall_outlet" and conn["from_id"] == outlet_id) or \
               (conn.get("to_type")   == "wall_outlet" and conn["to_id"]   == outlet_id):
                reply = QMessageBox.question(
                    self, t("dlg_connect_outlet_title"),
                    t("warn_outlet_already_connected"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
                break

        existing_ids = {c["id"] for c in self._data.get("connections", [])}
        new_id = f"conn{len(existing_ids) + 1}"
        while new_id in existing_ids:
            new_id += "_"

        self._result = {
            "id":         new_id,
            "from_id":    self._port_id,
            "from_type":  "port",
            "to_id":      outlet_id,
            "to_type":    "wall_outlet",
            "cable_type": cable_type,
            "notes":      self._notes.toPlainText().strip(),
        }
        self.accept()

    def get_result(self) -> dict | None:
        return self._result