# =============================================================================
# Networkmap_Creator
# File:    app/gui/changelog_viewer_dialog.py
# Role:    Read-only venster voor de wijzigingslog (K3).
#          Toont entries nieuwste eerst in een tabel; exporteer-knop kopieert
#          het actieve changelog.jsonl naar een door de gebruiker gekozen pad.
# Version: 1.0.1
# Author:  Barremans
# Changes: 1.0.1 — K3-fix: details getoond als tooltip (ℹ) op omschrijving.
#          1.0.0 — K3: initiële versie.
# =============================================================================

import shutil

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog,
)
from PySide6.QtCore import Qt

from app.helpers.i18n import t
from app.services import changelog_service

_ACTION_KEYS = {
    "create":  "changelog_action_create",
    "update":  "changelog_action_update",
    "delete":  "changelog_action_delete",
    "approve": "changelog_action_approve",
    "reopen":  "changelog_action_reopen",
}


class ChangelogViewerDialog(QDialog):
    """
    Niet-modaal venster dat de wijzigingslog toont (K3).
    Aanroepen vanuit Help-menu.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("changelog_title"))
        self.setMinimumSize(820, 520)
        self.setModal(False)
        self._build()
        self._load()

    # ------------------------------------------------------------------
    # UI opbouw
    # ------------------------------------------------------------------

    def _build(self):
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(10, 10, 10, 10)

        # ── Titel + sluitknop ────────────────────────────────────────
        top = QHBoxLayout()
        lbl = QLabel("📜  " + t("changelog_title"))
        f = lbl.font(); f.setPointSize(f.pointSize() + 2); f.setBold(True)
        lbl.setFont(f)
        top.addWidget(lbl)
        top.addStretch()
        btn_export = QPushButton(t("changelog_btn_export"))
        btn_export.setFixedWidth(110)
        btn_export.clicked.connect(self._on_export)
        top.addWidget(btn_export)
        btn_close = QPushButton(t("changelog_btn_close"))
        btn_close.setFixedWidth(90)
        btn_close.clicked.connect(self.close)
        top.addWidget(btn_close)
        root.addLayout(top)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        # ── Tabel ────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels([
            t("changelog_col_ts"),
            t("changelog_col_action"),
            t("changelog_col_type"),
            t("changelog_col_label"),
            t("changelog_col_user"),
        ])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(self._table, 1)

        # ── Statusregel ──────────────────────────────────────────────
        self._status = QLabel("")
        self._status.setObjectName("secondary")
        root.addWidget(self._status)

    # ------------------------------------------------------------------
    # Data laden
    # ------------------------------------------------------------------

    def _load(self):
        entries = changelog_service.load_entries()
        self._table.setRowCount(0)

        if not entries:
            self._status.setText(t("changelog_empty"))
            return

        self._table.setRowCount(len(entries))
        for row, e in enumerate(entries):
            action_key = _ACTION_KEYS.get(e.get("action", ""), "")
            action_lbl = t(action_key) if action_key else e.get("action", "")

            self._table.setItem(row, 0, self._cell(e.get("ts", "")[:19].replace("T", "  ")))
            self._table.setItem(row, 1, self._cell(action_lbl))
            self._table.setItem(row, 2, self._cell(e.get("entity_type", "")))
            label_cell = self._cell(e.get("label", ""))
            extra = e.get("extra")
            if extra:
                tooltip_lines = []
                for k, v in extra.items():
                    if isinstance(v, dict) and "van" in v and "naar" in v:
                        tooltip_lines.append(f"{k}:  {v['van']}  →  {v['naar']}")
                    else:
                        tooltip_lines.append(f"{k}: {v}")
                if tooltip_lines:
                    label_cell.setToolTip("\n".join(tooltip_lines))
                    label_cell.setText(e.get("label", "") + "  ℹ")
            self._table.setItem(row, 3, label_cell)
            self._table.setItem(row, 4, self._cell(e.get("user", "")))

        self._status.setText(f"{len(entries)} entries")

    @staticmethod
    def _cell(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        return item

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _on_export(self):
        src = changelog_service.get_changelog_path()
        dest, _ = QFileDialog.getSaveFileName(
            self, t("changelog_btn_export"), "changelog.jsonl",
            t("changelog_export_filter")
        )
        if not dest:
            return
        try:
            shutil.copy2(src, dest)
            self._status.setText(f"✓  {t('changelog_export_ok')} {dest}")
        except Exception as e:
            self._status.setText(f"⚠  {t('changelog_export_fail')}: {e}")

    # ------------------------------------------------------------------
    # Externe verversing (optioneel — aanroepen na nieuwe log-entry)
    # ------------------------------------------------------------------

    def refresh(self):
        self._load()