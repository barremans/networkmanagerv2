# =============================================================================
# Networkmap_Creator
# File:    app/gui/github_cases_dialog.py
# Role:    Overzicht open bugs (Issues) en features (Pull Requests) via GitHub
# Version: 1.0.0
# Author:  Barremans
# =============================================================================

import requests
import webbrowser

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton,
    QHeaderView, QAbstractItemView, QTabWidget,
    QWidget, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QBrush

from app.helpers.i18n import t

_GITHUB_OWNER  = "barremans"
_GITHUB_REPO   = "networkmanagerv2"
_GITHUB_TOKEN  = "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"


# ---------------------------------------------------------------------------
# Achtergrond worker — haalt data op zonder UI te blokkeren
# ---------------------------------------------------------------------------

class _FetchWorker(QThread):
    done    = Signal(list, list)   # (issues, pull_requests)
    failed  = Signal(str)

    def run(self):
        hdrs = {
            "Authorization": f"token {_GITHUB_TOKEN}",
            "Accept":        "application/vnd.github+json",
        }
        base = f"https://api.github.com/repos/{_GITHUB_OWNER}/{_GITHUB_REPO}"
        try:
            # Open Issues (excl. pull requests)
            issues_raw = requests.get(
                f"{base}/issues",
                params={"state": "open", "per_page": 100},
                headers=hdrs, timeout=15
            )
            issues_raw.raise_for_status()
            all_items = issues_raw.json()

            issues = [i for i in all_items if "pull_request" not in i]
            pulls  = []

            # Open Pull Requests
            prs_raw = requests.get(
                f"{base}/pulls",
                params={"state": "open", "per_page": 100},
                headers=hdrs, timeout=15
            )
            prs_raw.raise_for_status()
            pulls = prs_raw.json()

            self.done.emit(issues, pulls)

        except requests.exceptions.ConnectionError:
            self.failed.emit(t("report_err_no_connection"))
        except Exception as e:
            self.failed.emit(str(e))


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

class GithubCasesDialog(QDialog):
    """Toont open GitHub Issues (bugs) en Pull Requests (features)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("cases_dialog_title"))
        self.setMinimumSize(780, 480)
        self.resize(900, 540)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._build_ui()
        self._load()

    # ── UI opbouw ───────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Status label
        self._status_label = QLabel(t("cases_loading"))
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setObjectName("secondary")
        layout.addWidget(self._status_label)

        # Tabs
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # Tab: Bugs (Issues)
        self._tab_bugs = QWidget()
        bug_layout = QVBoxLayout(self._tab_bugs)
        bug_layout.setContentsMargins(0, 8, 0, 0)
        self._tbl_bugs = self._make_table(["#", t("cases_col_title"), t("cases_col_labels"), t("cases_col_date")])
        bug_layout.addWidget(self._tbl_bugs)
        self._tabs.addTab(self._tab_bugs, f"🐞  {t('cases_tab_bugs')}")

        # Tab: Features (Pull Requests)
        self._tab_features = QWidget()
        feat_layout = QVBoxLayout(self._tab_features)
        feat_layout.setContentsMargins(0, 8, 0, 0)
        self._tbl_features = self._make_table(["#", t("cases_col_title"), t("cases_col_branch"), t("cases_col_date")])
        feat_layout.addWidget(self._tbl_features)
        self._tabs.addTab(self._tab_features, f"✨  {t('cases_tab_features')}")

        # Knoppen
        btn_layout = QHBoxLayout()
        self._btn_refresh = QPushButton(t("cases_btn_refresh"))
        self._btn_refresh.clicked.connect(self._load)
        self._btn_open = QPushButton(t("cases_btn_open_browser"))
        self._btn_open.clicked.connect(self._open_selected_in_browser)
        btn_close = QPushButton(t("btn_cancel"))
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self._btn_refresh)
        btn_layout.addWidget(self._btn_open)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def _make_table(self, headers: list) -> QTableWidget:
        tbl = QTableWidget()
        tbl.setColumnCount(len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setAlternatingRowColors(True)
        tbl.verticalHeader().setVisible(False)
        hdr = tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        tbl.doubleClicked.connect(self._on_double_click)
        return tbl

    # ── Data laden ──────────────────────────────────────────────────────────

    def _load(self):
        self._status_label.setText(t("cases_loading"))
        self._btn_refresh.setEnabled(False)
        self._tbl_bugs.setRowCount(0)
        self._tbl_features.setRowCount(0)

        self._worker = _FetchWorker()
        self._worker.done.connect(self._on_data)
        self._worker.failed.connect(self._on_error)
        self._worker.start()

    def _on_data(self, issues: list, pulls: list):
        self._btn_refresh.setEnabled(True)

        bug_count  = len(issues)
        feat_count = len(pulls)

        self._tabs.setTabText(0, f"🐞  {t('cases_tab_bugs')} ({bug_count})")
        self._tabs.setTabText(1, f"✨  {t('cases_tab_features')} ({feat_count})")
        self._status_label.setText(
            f"{t('cases_loaded')}: {bug_count} {t('cases_tab_bugs').lower()}, "
            f"{feat_count} {t('cases_tab_features').lower()}"
        )

        # Bugs tabel vullen
        self._tbl_bugs.setRowCount(bug_count)
        for row, issue in enumerate(issues):
            number  = str(issue.get("number", ""))
            title   = issue.get("title", "")
            labels  = ", ".join(l["name"] for l in issue.get("labels", []))
            date    = issue.get("created_at", "")[:10]
            url     = issue.get("html_url", "")

            self._set_row(self._tbl_bugs, row, [number, title, labels, date], url)

        # Features tabel vullen
        self._tbl_features.setRowCount(feat_count)
        for row, pr in enumerate(pulls):
            number  = str(pr.get("number", ""))
            title   = pr.get("title", "")
            branch  = pr.get("head", {}).get("ref", "")
            date    = pr.get("created_at", "")[:10]
            url     = pr.get("html_url", "")

            self._set_row(self._tbl_features, row, [number, title, branch, date], url)

    def _on_error(self, msg: str):
        self._btn_refresh.setEnabled(True)
        self._status_label.setText(f"⚠  {msg}")

    def _set_row(self, tbl: QTableWidget, row: int, values: list, url: str):
        for col, val in enumerate(values):
            item = QTableWidgetItem(val)
            item.setData(Qt.ItemDataRole.UserRole, url)
            item.setToolTip(url)
            tbl.setItem(row, col, item)

    # ── Interactie ──────────────────────────────────────────────────────────

    def _current_url(self) -> str | None:
        tbl = self._tbl_bugs if self._tabs.currentIndex() == 0 else self._tbl_features
        row = tbl.currentRow()
        if row < 0:
            return None
        item = tbl.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _open_selected_in_browser(self):
        url = self._current_url()
        if url:
            webbrowser.open(url)
        else:
            QMessageBox.information(self, t("cases_dialog_title"), t("cases_no_selection"))

    def _on_double_click(self, index):
        tbl = self._tbl_bugs if self._tabs.currentIndex() == 0 else self._tbl_features
        item = tbl.item(index.row(), 0)
        if item:
            url = item.data(Qt.ItemDataRole.UserRole)
            if url:
                webbrowser.open(url)