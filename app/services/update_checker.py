# app/services/update_checker.py  — v1.0.5 (file logging + restore constants + no-cache)
"""
Asynchrone update check bij opstarten.

Ondersteunt version.txt met:
- regel 1: versie (verplicht)
- regel 2: download-URL (optioneel)

Schrijft debug/log naar:
%LOCALAPPDATA%\\Networkmap_Creator\\logs\\update.log

Extra: cache-buster + no-cache headers om proxy/AV caching te omzeilen.
"""

import os
import time
import threading
import urllib.request
import urllib.error
from datetime import datetime

from PySide6.QtCore import QObject, Signal

from app.version import __version__

# ---------------------------------------------------------------------------
# Constanten
# ---------------------------------------------------------------------------

DEFAULT_VERSION_URL = (
    "https://raw.githubusercontent.com/barremans/networkmanagerv2"
    "/main/releases/latest/version.txt"
)

# ⚠️ Belangrijk: wordt elders geïmporteerd (help_window/main_window), dus moet bestaan
GITHUB_RELEASES_URL = "https://github.com/barremans/networkmanagerv2/releases"

REQUEST_TIMEOUT = 5  # seconden


# ---------------------------------------------------------------------------
# Logging naar file (werkt ook in .exe)
# ---------------------------------------------------------------------------

def _log_line(msg: str) -> None:
    try:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        log_dir = os.path.join(base, "Networkmap_Creator", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "update.log")

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{ts} {msg}\n")
    except Exception:
        # logging mag nooit crashen
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_version(v: str) -> tuple[int, ...]:
    """Zet '1.2.10' om naar (1,2,10) zodat vergelijking correct is."""
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except (ValueError, AttributeError):
        return (0,)


def _parse_version_file(text: str) -> tuple[str | None, str | None]:
    """
    Parse version.txt:
    - regel 1: versie (verplicht)
    - regel 2: optionele download-URL

    Return: (version, url)
    """
    if not text:
        return None, None

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None, None

    # strip BOM + eventueel 'v'
    version = lines[0].lstrip("\ufeff").lstrip("vV")
    url = None
    if len(lines) >= 2 and lines[1].startswith(("http://", "https://")):
        url = lines[1]
    return version, url


# ---------------------------------------------------------------------------
# UpdateChecker
# ---------------------------------------------------------------------------

class UpdateChecker(QObject):
    update_available = Signal(str)
    update_available_with_url = Signal(str, object)  # url kan None zijn

    def __init__(self, url: str = "", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._url = url.strip() if url and url.strip() else DEFAULT_VERSION_URL

    def start(self) -> None:
        t = threading.Thread(target=self._run, daemon=True, name="UpdateChecker")
        t.start()

    def _run(self) -> None:
        try:
            remote_version, download_url = self._fetch_remote_info()

            _log_line(f"[update] local={__version__} url={self._url}")
            _log_line(f"[update] remote_ver={remote_version} remote_url={download_url}")

            if remote_version and self._is_newer(remote_version):
                _log_line(f"[update] UPDATE AVAILABLE: remote={remote_version} > local={__version__}")
                self.update_available.emit(remote_version)
                self.update_available_with_url.emit(remote_version, download_url)
            else:
                _log_line(f"[update] no update: remote={remote_version} local={__version__}")

        except Exception as e:
            _log_line(f"[update] failed: {type(e).__name__}: {e}")

    def _fetch_remote_info(self) -> tuple[str | None, str | None]:
        try:
            # Cache-buster query toevoegen (om proxy/AV caching te omzeilen)
            url = self._url
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}t={int(time.time())}"

            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Networkmap-Creator-Updater/1.0",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                },
            )
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
                return _parse_version_file(raw)
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            _log_line(f"[update] fetch failed: {type(e).__name__}: {e}")
            return None, None

    @staticmethod
    def _is_newer(remote: str) -> bool:
        return _parse_version(remote) > _parse_version(__version__)