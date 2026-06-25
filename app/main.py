# =============================================================================
# Networkmap_Creator
# File:    app/main.py
# Role:    Entry point — QApplication, QSS laden, taal instellen, MainWindow
# Version: 1.7.0
# Author:  Barremans
# Changes: 1.7.0 — S6c: security gate faalt niet langer "open".
#                  Oud gedrag (1.6.0): enabled=True maar tenant/client leeg
#                  → stille volledige schrijftoegang. Dat is een lek: een
#                  niet-gemigreerde settings.json gaf iedereen read/write.
#                  Nieuw gedrag:
#                    - enabled=False                → volledige toegang
#                      (bewuste keuze van de beheerder).
#                    - enabled=True + geconfigureerd → normale AD-gate.
#                    - enabled=True + NIET volledig geconfigureerd
#                      (tenant_id of client_id leeg) → GEEN volledige toegang;
#                      offline poweruser login → read-only. Annuleren = geen
#                      toegang.
#          1.6.0 — S6 update-fix: _run_security_gate() controleert eerst of
#                  AD geconfigureerd is (tenant_id + client_id gevuld).
#                  Als niet geconfigureerd → directe toegang, geen popup.
#                  Voorkomt offline login popup na update op bestaande machines.
#          1.5.0 — S6b: get_access_level() ipv has_access()
#                  ipv has_access(). Twee niveaus: admin (read/write) en
#                  readonly. Hardcoded "CGK-APP-L6" referenties verwijderd.
#          D   — update check bij opstarten via UpdateChecker
#          D.1 — update_available_with_url signaal
#          D.2 — download-knop actief via DownloadDialog
#          1.2.3 — versie dynamisch uit version.py (fix statusbalk vs Over)
#          1.3.0 — Azure AD security gate toegevoegd
#          1.4.0 — Globale uppercase filter voor alle QLineEdit velden
#                  Online + CGK-APP-L6 → volledige toegang (read/write)
#                  Online + verkeerde groep → NoAccessDialog + afsluiten
#                  Offline → poweruser login → read-only modus
#                  Elke login wordt gelogd naar security_log.txt
# =============================================================================

import sys
import os
import threading

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
    lang    = settings_storage.get_setting("language", "nl")
    success = i18n.set_language(lang)
    if not success:
        log_warning(f"Onbekende taal '{lang}', teruggevallen op 'nl'.")
        i18n.set_language("nl")
    else:
        log_info(f"Taal ingesteld: {lang}")


# ---------------------------------------------------------------------------
# Update check
# ---------------------------------------------------------------------------

def _start_update_check(window: MainWindow) -> None:
    update_url = settings_storage.get_setting("update_check_url", "")

    def _on_update_available_with_url(version: str, download_url: object) -> None:
        msg = QMessageBox(window)
        msg.setWindowTitle(t("update_available_title"))
        msg.setText(t("update_available_msg").format(version=version))

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
# Security gate — Azure AD
# ---------------------------------------------------------------------------

def _try_azure_login(timeout_sec: int = 60) -> bool:
    """
    Probeert Azure AD login in een aparte thread.
    Geeft False terug bij timeout of fout.
    """
    from app.security.permissions_networkmap import connect_to_azure_ad
    result = {"ok": False}

    def worker():
        try:
            result["ok"] = connect_to_azure_ad()
        except Exception as e:
            print(f"[SECURITY] Azure AD fout: {e}")
            result["ok"] = False

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout=timeout_sec)

    if t.is_alive():
        print("[SECURITY] Azure AD login timeout")
        return False

    return result["ok"]


def _run_security_gate() -> tuple[bool, bool]:
    """
    Voert de volledige security check uit.

    Returns:
        (toegang_verleend, read_only)
        - (True,  False) → AD uitgeschakeld OF online admin → volledige toegang
        - (True,  True)  → online readonly-groep, offline poweruser, of
                           AD ingeschakeld-maar-niet-geconfigureerd → read-only
        - (False, False) → geen toegang, app mag niet starten

    Beleid (S6c):
        AD bewust uitgeschakeld (enabled=False) is een expliciete keuze van de
        beheerder en geeft volledige toegang. AD ingeschakeld maar niet
        geconfigureerd (tenant_id/client_id leeg) geeft NOOIT stil volledige
        toegang — dat is een lek. In dat geval volgt offline poweruser login
        met read-only als hoogst haalbare niveau.
    """
    from app.security.permissions_networkmap import get_access_level, get_cached_user
    from app.security.offline_auth import log_ad_login, log_app_start, log_offline_login
    from app.gui.dialogs.no_access_dialog import NoAccessDialog
    from app.gui.dialogs.offline_login_dialog import OfflineLoginDialog
    from app.helpers.settings_storage import get_azure_ad_config

    # --- Configuratiecheck vóór elke netwerkpoging ---
    cfg = get_azure_ad_config()
    ad_enabled  = cfg.get("enabled", True)
    tenant_id   = cfg.get("tenant_id", "").strip()
    client_id   = cfg.get("client_id", "").strip()

    # 1) AD bewust uitgeschakeld door de beheerder → volledige toegang.
    if not ad_enabled:
        log_app_start("onbekend (AD uitgeschakeld)", mode="readwrite")
        print("[SECURITY] AD uitgeschakeld in settings — volledige toegang.")
        return True, False

    # 2) AD ingeschakeld maar NIET volledig geconfigureerd.
    #    Geen stille volledige toegang meer (was het lek in 1.6.0).
    #    Veilige fallback: offline poweruser login → read-only.
    if not tenant_id or not client_id:
        print("[SECURITY] AD ingeschakeld maar niet geconfigureerd "
              "(tenant_id/client_id leeg) — offline login vereist.")
        log_offline_login(
            "AD ingeschakeld zonder configuratie",
            success=False,
            reason="tenant_id/client_id ontbreken in settings",
        )
        dlg = OfflineLoginDialog()
        if dlg.exec() == OfflineLoginDialog.DialogCode.Accepted:
            username = dlg.get_username()
            log_app_start(username, mode="readonly")
            print(f"[SECURITY] Offline read-only toegang voor '{username}' "
                  f"(AD niet geconfigureerd).")
            return True, True
        print("[SECURITY] Offline login geannuleerd — geen toegang.")
        return False, False

    # 3) AD ingeschakeld én geconfigureerd → normale gate.
    print("[SECURITY] Azure AD login starten...")
    ad_ok = _try_azure_login(timeout_sec=60)

    if ad_ok:
        user  = get_cached_user() or {}
        name  = user.get("displayName", "")
        upn   = user.get("userPrincipalName", "")
        level = get_access_level()   # "admin" | "readonly" | "none"

        if level == "admin":
            log_ad_login(name, upn, success=True)
            log_app_start(f"{name} <{upn}>", mode="readwrite")
            print(f"[SECURITY] Toegang verleend (admin) voor {name}.")
            return True, False

        elif level == "readonly":
            log_ad_login(name, upn, success=True)
            log_app_start(f"{name} <{upn}>", mode="readonly")
            print(f"[SECURITY] Read-only toegang verleend voor {name}.")
            return True, True

        else:  # "none"
            log_ad_login(name, upn, success=False,
                         reason="niet in een toegestane AD-groep")
            print(f"[SECURITY] Toegang geweigerd voor {name} ({upn}).")
            dlg = NoAccessDialog(reason=f"Ingelogd als: {name} ({upn})")
            dlg.exec()
            return False, False

    else:
        # Azure AD niet bereikbaar — offline poweruser login
        print("[SECURITY] Azure AD niet bereikbaar — offline login.")
        dlg = OfflineLoginDialog()
        if dlg.exec() == OfflineLoginDialog.DialogCode.Accepted:
            username = dlg.get_username()
            log_app_start(username, mode="readonly")
            print(f"[SECURITY] Offline toegang verleend voor '{username}' (read-only).")
            return True, True
        else:
            print("[SECURITY] Offline login geannuleerd of mislukt.")
            return False, False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Networkmap Creator")
    app.setApplicationVersion(_APP_VERSION)
    app.setOrganizationName("Barremans")

    # 1.4.0 — Globale uppercase filter voor alle QLineEdit velden
    from app.helpers.uppercase_filter import UpperCaseFilter
    _uc_filter = UpperCaseFilter(app)
    app.installEventFilter(_uc_filter)

    _init_language()

    qss_ok = _load_qss(app)
    if qss_ok:
        print("[INFO] QSS geladen.")

    # --- Security gate ---
    toegang, read_only = _run_security_gate()
    if not toegang:
        sys.exit(0)

    # --- Read-only modus instellen (readonly AD-groep of offline login) ---
    if read_only:
        settings_storage.set_read_only_mode(True)
        print("[SECURITY] Read-only modus actief.")

    # --- Hoofdvenster starten ---
    window = MainWindow()
    window.show()

    _start_update_check(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()