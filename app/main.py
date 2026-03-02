# =============================================================================
# Networkmap_Creator
# File:    app/main.py
# Role:    Entry point — QApplication, QSS laden, taal instellen, MainWindow
# Version: 1.1.0
# Author:  Barremans
# =============================================================================

import sys
import os

# Zorg dat de projectroot (één niveau boven app/) op het Python-pad staat
# zodat alle imports zoals 'from app.helpers import ...' werken
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app.helpers import settings_storage
from app.helpers import i18n
from app.gui.main_window import MainWindow
from app.services.logger import log_info, log_warning, log_error, get_logger


# ---------------------------------------------------------------------------
# QSS laden
# ---------------------------------------------------------------------------

def _load_qss(app: QApplication) -> bool:
    """
    Laad css/main.qss en pas toe op de QApplication.
    Geeft True terug bij succes, False als het bestand niet gevonden wordt.
    Geeft een waarschuwing maar crasht NIET — app start gewoon zonder styling.
    """
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
    """
    Laad de taalinstelling uit settings.json en stel i18n in.
    Valt terug op 'nl' bij ontbrekende of ongeldige instelling.
    """
    lang = settings_storage.get_setting("language", "nl")
    success = i18n.set_language(lang)
    if not success:
        log_warning(f"Onbekende taal '{lang}', teruggevallen op 'nl'.")
        i18n.set_language("nl")
    else:
        log_info(f"Taal ingesteld: {lang}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    # High-DPI scaling inschakelen vóór QApplication aanmaken
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Networkmap Creator")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Barremans")

    # Taal instellen vóór het venster opent
    _init_language()

    # QSS laden
    qss_ok = _load_qss(app)
    if qss_ok:
        print("[INFO] QSS geladen.")
    
    # Hoofdvenster aanmaken en tonen
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()