# =============================================================================
# Networkmap_Creator
# File:    app/gui/help_window.py
# Role:    H1 — Help venster: sneltoetsen, gebruiksaanwijzing, versie-info
# Version: 1.2.2
# Author:  Barremans
# Changes: 1.1.0 — donkere kleuren, version.py dynamisch, help_texts.py
#          1.2.0 — D: "Controleer op updates" knop in Over tabblad
#          1.2.1 — D: update_available_with_url signaal
#          1.2.2 — D: download-knop actief via DownloadDialog
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QScrollArea, QFrame, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from app.helpers.i18n import t
from app.helpers.help_texts import SHORTCUTS, get_guide_sections
from app.helpers import settings_storage
from app.services.update_checker import UpdateChecker, GITHUB_RELEASES_URL
from app.services.update_downloader import DownloadDialog

try:
    from app import version as _ver
    _APP_VERSION = _ver.__version__
except Exception:
    _APP_VERSION = "—"

_APP_NAME   = "Networkmap Creator"
_APP_AUTHOR = "Barremans"

_C_HEADING   = "#7eb8f7"
_C_BODY      = "#d0d8e8"
_C_MUTED     = "#8899aa"
_C_ACCENT    = "#4a9eda"
_C_DIVIDER   = "#3a4a5a"
_C_TABLE_HDR = "#1e3a5f"


class HelpWindow(QDialog):
    """H1 — Help venster met 3 tabbladen: Sneltoetsen / Gebruiksaanwijzing / Over."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("help_title"))
        self.setMinimumSize(700, 540)
        self.resize(740, 580)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint
        )
        self._tabs = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.addTab(self._tab_shortcuts(), t("help_tab_shortcuts"))
        self._tabs.addTab(self._tab_guide(),     t("help_tab_guide"))
        self._tabs.addTab(self._tab_version(),   t("help_tab_version"))
        root.addWidget(self._tabs)

        btn_bar = QHBoxLayout()
        btn_bar.setContentsMargins(12, 8, 12, 10)
        btn_bar.addStretch()
        btn_close = QPushButton(t("btn_close"))
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        btn_bar.addWidget(btn_close)
        root.addLayout(btn_bar)

    def set_tab(self, index: int):
        if self._tabs:
            self._tabs.setCurrentIndex(index)

    # ------------------------------------------------------------------
    # Tab 1 — Sneltoetsen
    # ------------------------------------------------------------------

    def _tab_shortcuts(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)

        intro = QLabel(t("help_shortcuts_intro"))
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {_C_MUTED}; font-size: 12px;")
        layout.addWidget(intro)

        tbl = QTableWidget(len(SHORTCUTS), 2)
        tbl.setHorizontalHeaderLabels([t("help_col_shortcut"), t("help_col_action")])
        tbl.horizontalHeader().setStyleSheet(
            f"QHeaderView::section {{"
            f"  background-color: {_C_TABLE_HDR}; color: #ffffff;"
            f"  font-weight: bold; padding: 6px 12px; border: none;}}"
        )
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        tbl.setShowGrid(False)
        tbl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        tbl.setAlternatingRowColors(True)
        tbl.setStyleSheet(
            "QTableWidget { border: none; }"
            f"QTableWidget::item {{ color: {_C_BODY}; padding: 4px 0px; }}"
        )

        mono = QFont("Consolas", 10)
        mono.setBold(True)

        for row, (key, i18n_key) in enumerate(SHORTCUTS):
            key_item = QTableWidgetItem(f"  {key}")
            key_item.setFont(mono)
            key_item.setForeground(QColor(_C_ACCENT))
            desc_item = QTableWidgetItem(f"  {t(i18n_key)}")
            desc_item.setForeground(QColor(_C_BODY))
            tbl.setItem(row, 0, key_item)
            tbl.setItem(row, 1, desc_item)
            tbl.setRowHeight(row, 30)

        layout.addWidget(tbl)
        layout.addStretch()
        return widget

    # ------------------------------------------------------------------
    # Tab 2 — Gebruiksaanwijzing
    # ------------------------------------------------------------------

    def _tab_guide(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(4)

        for section in get_guide_sections():
            lbl_title = QLabel(section["title"])
            f = lbl_title.font()
            f.setBold(True)
            f.setPointSize(f.pointSize() + 1)
            lbl_title.setFont(f)
            lbl_title.setStyleSheet(f"color: {_C_HEADING}; margin-top: 14px; margin-bottom: 2px;")
            layout.addWidget(lbl_title)

            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet(f"color: {_C_DIVIDER}; margin-bottom: 4px;")
            layout.addWidget(line)

            lbl_body = QLabel(section["body"])
            lbl_body.setWordWrap(True)
            lbl_body.setTextFormat(Qt.TextFormat.RichText)
            lbl_body.setStyleSheet(f"color: {_C_BODY}; font-size: 12px; padding: 4px 0px 8px 0px;")
            layout.addWidget(lbl_body)

        layout.addStretch()
        scroll.setWidget(inner)
        return scroll

    # ------------------------------------------------------------------
    # Tab 3 — Over / Versie-info
    # ------------------------------------------------------------------

    def _tab_version(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 28, 24, 20)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        name_lbl = QLabel(_APP_NAME)
        f = name_lbl.font()
        f.setBold(True)
        f.setPointSize(f.pointSize() + 8)
        name_lbl.setFont(f)
        name_lbl.setStyleSheet(f"color: {_C_HEADING}; margin-bottom: 4px;")
        layout.addWidget(name_lbl)

        desc_lbl = QLabel(t("help_app_desc"))
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(f"color: {_C_MUTED}; font-size: 12px; margin-bottom: 18px;")
        layout.addWidget(desc_lbl)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {_C_DIVIDER}; margin-bottom: 14px;")
        layout.addWidget(line)

        rows = [
            (t("help_version_label"), _APP_VERSION),
            (t("help_author_label"),  _APP_AUTHOR),
            (t("help_built_with"),    "Python 3.12  ·  PySide6  ·  python-docx"),
            (t("help_license_label"), t("help_license_value")),
        ]
        for label, value in rows:
            row_w = QWidget()
            h = QHBoxLayout(row_w)
            h.setContentsMargins(0, 4, 0, 4)
            h.setSpacing(0)
            lbl_l = QLabel(label)
            lbl_l.setFixedWidth(150)
            lbl_l.setStyleSheet(f"color: {_C_MUTED}; font-size: 12px;")
            lbl_v = QLabel(value)
            lbl_v.setStyleSheet(f"color: {_C_BODY}; font-size: 12px;")
            lbl_v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            h.addWidget(lbl_l)
            h.addWidget(lbl_v)
            h.addStretch()
            layout.addWidget(row_w)

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet(f"color: {_C_DIVIDER}; margin-top: 18px; margin-bottom: 10px;")
        layout.addWidget(line2)

        update_row = QHBoxLayout()
        update_row.setContentsMargins(0, 0, 0, 0)
        update_row.setSpacing(12)

        self._btn_check_update = QPushButton("🔍  Controleer op updates")
        self._btn_check_update.setFixedWidth(200)
        self._btn_check_update.clicked.connect(self._on_check_update)

        self._lbl_update_status = QLabel("")
        self._lbl_update_status.setStyleSheet(f"color: {_C_MUTED}; font-size: 12px;")

        update_row.addWidget(self._btn_check_update)
        update_row.addWidget(self._lbl_update_status)
        update_row.addStretch()
        layout.addLayout(update_row)

        layout.addStretch()
        return widget

    # ------------------------------------------------------------------
    # Update check — Fase D
    # ------------------------------------------------------------------

    def _on_check_update(self):
        """Handmatige update check vanuit Help → Over."""
        self._btn_check_update.setEnabled(False)
        self._lbl_update_status.setStyleSheet(f"color: {_C_MUTED}; font-size: 12px;")
        self._lbl_update_status.setText("Bezig met controleren...")

        update_url = settings_storage.get_setting("update_check_url", "")
        checker = UpdateChecker(url=update_url, parent=self)
        checker.update_available_with_url.connect(self._on_update_found)

        from PySide6.QtCore import QTimer

        def _re_enable():
            if self._lbl_update_status.text() == "Bezig met controleren...":
                self._lbl_update_status.setStyleSheet(f"color: {_C_MUTED}; font-size: 12px;")
                self._lbl_update_status.setText("✓  Je gebruikt de nieuwste versie.")
            self._btn_check_update.setEnabled(True)

        QTimer.singleShot(6500, _re_enable)
        checker.start()

    def _on_update_found(self, version: str, download_url: object) -> None:
        """Wordt aangeroepen als een nieuwere versie gevonden is."""
        self._btn_check_update.setEnabled(True)
        self._lbl_update_status.setStyleSheet(
            "color: #f0a040; font-size: 12px; font-weight: bold;"
        )
        self._lbl_update_status.setText(f"⬆  Versie {version} beschikbaar!")

        msg = QMessageBox(self)
        msg.setWindowTitle(t("update_available_title"))
        msg.setText(t("update_available_msg").format(version=version))

        btn_download = msg.addButton("⬇  Downloaden", QMessageBox.ButtonRole.AcceptRole)
        btn_download.setEnabled(bool(download_url))

        msg.addButton(t("update_later"), QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        if msg.clickedButton() is btn_download and download_url:
            dlg = DownloadDialog(url=download_url, version=version, parent=self)
            dlg.exec()