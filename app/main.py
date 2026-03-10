# =============================================================================
# Networkmap_Creator
# File:    app/main.py
# Role:    Entry point — QApplication, QSS laden, taal instellen, MainWindow
# Version: 1.2.3
# Author:  Barremans
# Changes: D   — update check bij opstarten via UpdateChecker
#          D.1 — update_available_with_url signaal
#          D.2 — download-knop actief via DownloadDialog
#          1.2.3 — versie dynamisch uit version.py (fix statusbalk vs Over)
# =============================================================================

import sys
import os

if getattr(sys, 'frozen', False):
    _PROJECT_ROOT = os.path.dirname(sys.executable)
else:
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

from app.helpers import settings_storage
from app.helpers import i18n
from app.helpers.i18n import t
from app.gui.main_window import MainWindow
from app.services.logger import log_info, log_warning, log_error
from app.services.update_checker import UpdateChecker, GITHUB_RELEASES_URL
from app.services.update_downloader import DownloadDialog

try:
    from app import version as _ver
    _APP_VERSION = _ver.__version__
except Exception:
    _APP_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# QSS laden
# ---------------------------------------------------------------------------

def _load_qss(app: QApplication) -> bool:
    qss_path = os.path.join(_PROJECT_ROOT, "css", "main.qss")
    if not os.path.exists(qss_path):
        log_warning(f"QSS bestand niet gevonden: {qss_path}")
        return False
    try:
        with open(qss_path, "r", encoding="utf-8") as f:
            stylesheet = f.read()
        app.setStyleSheet(stylesheet)
        log_info("QSS geladen.")
        print("[INFO] QSS geladen.")
        return True
    except OSError as e:
        log_error(f"QSS laden mislukt", e)
        print(f"[WAARSCHUWING] QSS laden mislukt: {e}")
        return False


# ---------------------------------------------------------------------------
# Taal instellen
# ---------------------------------------------------------------------------

def _init_language():
    lang = settings_storage.get_setting("language", "nl")
    success = i18n.set_language(lang)
    if not success:
        log_warning(f"Onbekende taal '{lang}', teruggevallen op 'nl'.")
        i18n.set_language("nl")
    else:
        log_info(f"Taal ingesteld: {lang}")


# ---------------------------------------------------------------------------
# Update check — Fase D
# ---------------------------------------------------------------------------

def _start_update_check(window: MainWindow) -> None:
    """
    Start de asynchrone update check na het tonen van het hoofdvenster.
    Netwerkfouten worden stil genegeerd — de app wordt nooit geblokkeerd.
    """
    update_url = settings_storage.get_setting("update_check_url", "")

    def _on_update_available_with_url(version: str, download_url: object) -> None:
        """Slot — uitgevoerd in de hoofdthread via Qt QueuedConnection."""
        msg = QMessageBox(window)
        msg.setWindowTitle(t("update_available_title"))
        msg.setText(t("update_available_msg").format(version=version))

        # Download-knop: actief als er een directe URL beschikbaar is
        btn_download = msg.addButton(
            "⬇  Downloaden", QMessageBox.ButtonRole.AcceptRole
        )
        btn_download.setEnabled(bool(download_url))

        msg.addButton(t("update_later"), QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        if msg.clickedButton() is btn_download and download_url:
            dlg = DownloadDialog(url=download_url, version=version, parent=window)
            dlg.exec()
            log_info(f"Download gestart voor versie {version}.")
        else:
            log_info(f"Update: gebruiker kiest 'Later' voor versie {version}.")

    checker = UpdateChecker(url=update_url, parent=window)
    checker.update_available_with_url.connect(_on_update_available_with_url)
    checker.start()
    log_info(f"Update check gestart (url: {checker._url!r}).")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Networkmap Creator")
    app.setApplicationVersion(_APP_VERSION)   # ← dynamisch uit version.py
    app.setOrganizationName("Barremans")

    _init_language()

    qss_ok = _load_qss(app)
    if qss_ok:
        print("[INFO] QSS geladen.")

    window = MainWindow()
    window.show()

    # Update check starten na tonen van het venster — Fase D
    _start_update_check(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()