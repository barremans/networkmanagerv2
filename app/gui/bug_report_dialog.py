# =============================================================================
# Networkmap_Creator
# File:    app/gui/bug_report_dialog.py
# Role:    Bug / Feature melden naar GitHub Issues en Pull Requests
# Version: 1.1.0
# Author:  Barremans
# Changes: 1.1.0 — GitHub token uit app/config/github_config.py (niet hardcoded)
# =============================================================================

import uuid
import base64
from datetime import datetime

import os
import sys

import requests

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QComboBox, QPushButton,
    QMessageBox
)
from PySide6.QtCore import Qt

from app.helpers.i18n import t

# ---------------------------------------------------------------------------
# GitHub configuratie — geladen uit app/config/github_config.py
# Kopieer app/config/github_config.example.py naar github_config.py
# ---------------------------------------------------------------------------
try:
    from app.config.github_config import (
        GITHUB_TOKEN  as _GITHUB_TOKEN,
        GITHUB_OWNER  as _GITHUB_OWNER,
        GITHUB_REPO   as _GITHUB_REPO,
        GITHUB_BRANCH as _GITHUB_BRANCH,
    )
except ImportError:
    _GITHUB_TOKEN  = ""
    _GITHUB_OWNER  = ""
    _GITHUB_REPO   = ""
    _GITHUB_BRANCH = "main"


def _get_verify() -> str | bool:
    """
    Geeft het pad naar cacert.pem terug.
    In een PyInstaller .exe zit certifi gebundeld in _MEIPASS.
    In development wordt het systeem-certifi gebruikt.
    """
    if getattr(sys, "frozen", False):
        # PyInstaller exe — certifi zit in de tijdelijke map
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        pem  = os.path.join(base, "certifi", "cacert.pem")
        if os.path.exists(pem):
            return pem
        # Fallback: naast de exe zelf
        pem2 = os.path.join(os.path.dirname(sys.executable), "certifi", "cacert.pem")
        if os.path.exists(pem2):
            return pem2
    # Development — gebruik certifi normaal
    try:
        import certifi
        return certifi.where()
    except ImportError:
        return True   # vertrouw op het OS


# ---------------------------------------------------------------------------
# GitHub client
# ---------------------------------------------------------------------------

class _GitHubClient:
    def __init__(self):
        self._api   = f"https://api.github.com/repos/{_GITHUB_OWNER}/{_GITHUB_REPO}"
        self._hdrs  = {
            "Authorization": f"token {_GITHUB_TOKEN}",
            "Accept":        "application/vnd.github+json",
        }

    # ── Publieke methode ────────────────────────────────────────────────────

    def submit(self, reporter: str, description: str, report_type: str) -> str:
        """
        Bug   → GitHub Issue  (label: bug)
        Feature → Pull Request (label: enhancement) met bestand in repo
        Geeft de URL terug van het aangemaakte item.
        """
        is_feature  = (report_type == t("report_type_feature"))
        label_gh    = "enhancement" if is_feature else "bug"
        prefix      = "feature" if is_feature else "bug"
        date_str    = datetime.now().strftime("%Y-%m-%d %H:%M")
        short_desc  = description[:60].replace("\n", " ")
        title       = f"{'✨ Feature' if is_feature else '🐞 Bug'}: {short_desc}"
        body        = (
            f"**Type:** {report_type}\n"
            f"**Melder:** {reporter or 'onbekend'}\n"
            f"**Datum:** {date_str}\n\n"
            f"**Beschrijving:**\n\n{description}"
        )

        if is_feature:
            return self._create_pull_request(prefix, title, body, label_gh, reporter, description, date_str)
        else:
            return self._create_issue(title, body, label_gh)

    # ── Privé helpers ───────────────────────────────────────────────────────

    def _create_issue(self, title: str, body: str, label: str) -> str:
        url  = f"{self._api}/issues"
        data = {"title": title, "body": body, "labels": [label]}
        res  = requests.post(url, json=data, headers=self._hdrs, timeout=15, verify=_get_verify())
        res.raise_for_status()
        return res.json().get("html_url", "Issue aangemaakt (geen URL ontvangen).")

    def _create_pull_request(
        self, prefix: str, title: str, body: str,
        label: str, reporter: str, description: str, date_str: str
    ) -> str:
        branch_name = f"{prefix}-{uuid.uuid4().hex[:8]}"
        file_path   = f"{prefix}s/{branch_name}.md"
        content_md  = (
            f"# {title}\n\n"
            f"**Melder:** {reporter or 'onbekend'}  \n"
            f"**Datum:** {date_str}\n\n"
            f"## Beschrijving\n\n{description}\n"
        )
        encoded = base64.b64encode(content_md.encode("utf-8")).decode("utf-8")

        # Branch aanmaken
        sha = self._get_head_sha()
        self._create_branch(branch_name, sha)

        # Bestand committen
        file_url  = f"{self._api}/contents/{file_path}"
        file_data = {
            "message": f"✨ feature-aanvraag: {description[:50]}",
            "content": encoded,
            "branch":  branch_name,
        }
        res = requests.put(file_url, json=file_data, headers=self._hdrs, timeout=15, verify=_get_verify())
        res.raise_for_status()

        # Pull Request aanmaken
        pr_url  = f"{self._api}/pulls"
        pr_data = {
            "title": title,
            "body":  body,
            "head":  branch_name,
            "base":  _GITHUB_BRANCH,
        }
        pr_res = requests.post(pr_url, json=pr_data, headers=self._hdrs, timeout=15, verify=_get_verify())
        pr_res.raise_for_status()
        pr_number = pr_res.json()["number"]

        # Label toevoegen
        lbl_url = f"{self._api}/issues/{pr_number}/labels"
        requests.post(lbl_url, json={"labels": [label]}, headers=self._hdrs, timeout=10, verify=_get_verify())

        return pr_res.json().get("html_url", "Pull Request aangemaakt (geen URL ontvangen).")

    def _get_head_sha(self) -> str:
        url = f"{self._api}/git/ref/heads/{_GITHUB_BRANCH}"
        res = requests.get(url, headers=self._hdrs, timeout=10, verify=_get_verify())
        res.raise_for_status()
        return res.json()["object"]["sha"]

    def _create_branch(self, branch_name: str, sha: str):
        url  = f"{self._api}/git/refs"
        data = {"ref": f"refs/heads/{branch_name}", "sha": sha}
        res  = requests.post(url, json=data, headers=self._hdrs, timeout=10, verify=_get_verify())
        res.raise_for_status()


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

class BugReportDialog(QDialog):
    """Dialog voor het melden van bugs en feature-aanvragen via GitHub."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("report_dialog_title"))
        self.setMinimumSize(460, 400)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._build_ui()

    # ── UI opbouw ───────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Type
        layout.addWidget(QLabel(t("report_label_type")))
        self._type_select = QComboBox()
        self._type_select.addItems([
            t("report_type_bug"),
            t("report_type_feature"),
        ])
        layout.addWidget(self._type_select)

        # Naam
        layout.addWidget(QLabel(t("report_label_name")))
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText(t("report_placeholder_name"))
        layout.addWidget(self._name_input)

        # Beschrijving
        layout.addWidget(QLabel(t("report_label_description")))
        self._desc_input = QTextEdit()
        self._desc_input.setPlaceholderText(t("report_placeholder_description"))
        self._desc_input.setMinimumHeight(140)
        layout.addWidget(self._desc_input)

        # Knoppen
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._btn_cancel = QPushButton(t("btn_cancel"))
        self._btn_cancel.clicked.connect(self.reject)
        self._btn_submit = QPushButton(t("report_btn_submit"))
        self._btn_submit.setDefault(True)
        self._btn_submit.clicked.connect(self._on_submit)
        btn_layout.addWidget(self._btn_cancel)
        btn_layout.addWidget(self._btn_submit)
        layout.addLayout(btn_layout)

    # ── Verzenden ───────────────────────────────────────────────────────────

    def _on_submit(self):
        reporter    = self._name_input.text().strip()
        description = self._desc_input.toPlainText().strip()
        report_type = self._type_select.currentText()

        if not reporter:
            QMessageBox.warning(self, t("report_dialog_title"), t("report_err_no_name"))
            return
        if not description:
            QMessageBox.warning(self, t("report_dialog_title"), t("report_err_no_description"))
            return

        # Preview
        preview = (
            f"{t('report_type_label')}: {report_type}\n"
            f"{t('report_label_name')}: {reporter}\n\n"
            f"{t('report_label_description')}:\n{description[:200]}"
            f"{'…' if len(description) > 200 else ''}\n\n"
            f"{t('report_confirm_send')}"
        )
        reply = QMessageBox.question(
            self, t("report_preview_title"), preview,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._btn_submit.setEnabled(False)
        self._btn_submit.setText(t("report_btn_sending"))

        try:
            gh  = _GitHubClient()
            url = gh.submit(reporter, description, report_type)
            QMessageBox.information(
                self, t("report_success_title"),
                f"{t('report_success_msg')}\n\n{url}"
            )
            self.accept()
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(
                self, t("report_dialog_title"),
                t("report_err_no_connection")
            )
        except requests.exceptions.HTTPError as e:
            QMessageBox.critical(
                self, t("report_dialog_title"),
                f"{t('report_err_github')}\n\n{e}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, t("report_dialog_title"),
                f"{t('report_err_unknown')}\n\n{e}"
            )
        finally:
            self._btn_submit.setEnabled(True)
            self._btn_submit.setText(t("report_btn_submit"))