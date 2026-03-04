# =============================================================================
# Networkmap_Creator
# File:    app/gui/dialogs/connection_edit_dialog.py
# Role:    Dialog voor het bewerken van een bestaande verbinding
#          (kabeltype, label, notitie)
# Version: 1.0.0
# Author:  Barremans
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox,
    QPushButton, QFrame
)
from PySide6.QtCore import Qt

from app.helpers.i18n import t

# Kabeltype opties — (interne waarde, i18n sleutel)
_CABLE_TYPES = [
    ("utp_cat5e",  "cable_utp_cat5e"),
    ("utp_cat6",   "cable_utp_cat6"),
    ("utp_cat6a",  "cable_utp_cat6a"),
    ("fiber_sm",   "cable_fiber_sm"),
    ("fiber_mm",   "cable_fiber_mm"),
    ("dak",        "cable_dak"),
    ("other",      "cable_other"),
]


class ConnectionEditDialog(QDialog):
    """
    Dialog voor het bewerken van een verbinding.
    Velden: label (naam), kabeltype, notitie.
    """

    def __init__(self, connection: dict, parent=None):
        super().__init__(parent)
        self._conn   = connection
        self._result = None
        self.setWindowTitle(t("title_edit_connection"))
        self.setMinimumWidth(420)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint
        )
        self._build_ui()
        self._load(connection)

    # ------------------------------------------------------------------
    # UI opbouw
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(12)

        # Van → Naar (alleen-lezen info)
        info_frame = QFrame()
        info_frame.setObjectName("detail_frame")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.setSpacing(2)

        from_label = self._conn.get("_from_label", self._conn.get("from_id", "—"))
        to_label   = self._conn.get("_to_label",   self._conn.get("to_id",   "—"))

        lbl_from = QLabel(f"<b>{t('trace_from')}:</b>  {from_label}")
        lbl_from.setWordWrap(True)
        lbl_to   = QLabel(f"<b>{t('trace_to')}:</b>  {to_label}")
        lbl_to.setWordWrap(True)

        info_layout.addWidget(lbl_from)
        info_layout.addWidget(lbl_to)
        root.addWidget(info_frame)

        # Formulier
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Label / naam
        self._fld_label = QLineEdit()
        self._fld_label.setPlaceholderText(t("conn_label_placeholder"))
        self._fld_label.setMaxLength(80)
        form.addRow(t("label_name") + ":", self._fld_label)

        # Kabeltype
        self._fld_cable = QComboBox()
        for val, i18n_key in _CABLE_TYPES:
            self._fld_cable.addItem(t(i18n_key), userData=val)
        form.addRow(t("label_cable_type") + ":", self._fld_cable)

        # Notitie
        self._fld_notes = QTextEdit()
        self._fld_notes.setPlaceholderText(t("conn_notes_placeholder"))
        self._fld_notes.setFixedHeight(72)
        self._fld_notes.setAcceptRichText(False)
        form.addRow(t("label_notes") + ":", self._fld_notes)

        root.addLayout(form)

        # Knoppen
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton(t("btn_cancel"))
        btn_cancel.setFixedWidth(90)
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton(t("btn_save"))
        btn_save.setFixedWidth(90)
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._on_save)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Data laden / opslaan
    # ------------------------------------------------------------------

    def _load(self, conn: dict):
        """Vul velden met bestaande verbindingsdata."""
        self._fld_label.setText(conn.get("label", ""))

        cable = conn.get("cable_type", "utp_cat6")
        for i in range(self._fld_cable.count()):
            if self._fld_cable.itemData(i) == cable:
                self._fld_cable.setCurrentIndex(i)
                break

        self._fld_notes.setPlainText(conn.get("notes", ""))

    def _on_save(self):
        self._result = {
            "label":      self._fld_label.text().strip(),
            "cable_type": self._fld_cable.currentData(),
            "notes":      self._fld_notes.toPlainText().strip(),
        }
        self.accept()

    def get_result(self) -> dict | None:
        """Geeft de ingevulde velden terug, of None als geannuleerd."""
        return self._result