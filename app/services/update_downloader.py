# =============================================================================
# Networkmap_Creator
# File:    app/services/update_downloader.py
# Role:    Fase D — installer downloaden naar Downloads map met voortgang
# Version: 1.0.0
# Author:  Barremans
# =============================================================================

import os
import threading
import urllib.request
import urllib.error

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt


# ---------------------------------------------------------------------------
# Downloader (achtergrondthread)
# ---------------------------------------------------------------------------

class _DownloadWorker(QObject):
    """Voert de download uit in een daemonthread."""

    progress    = Signal(int)          # 0–100
    finished    = Signal(str)          # pad naar gedownload bestand
    failed      = Signal(str)          # foutmelding

    def __init__(self, url: str, dest_path: str, parent=None):
        super().__init__(parent)
        self._url       = url
        self._dest_path = dest_path
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def start(self):
        t = threading.Thread(target=self._run, daemon=True, name="UpdateDownloader")
        t.start()

    def _run(self):
        tmp_path = self._dest_path + ".part"
        try:
            req = urllib.request.Request(
                self._url,
                headers={"User-Agent": "Networkmap-Creator-Updater/1.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 32 * 1024  # 32 KB

                with open(tmp_path, "wb") as f:
                    while not self._cancelled:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = int(downloaded * 100 / total)
                            self.progress.emit(pct)

            if self._cancelled:
                _safe_remove(tmp_path)
                self.failed.emit("Geannuleerd.")
                return

            # Atomisch hernoemen na succesvolle download
            if os.path.exists(self._dest_path):
                os.remove(self._dest_path)
            os.rename(tmp_path, self._dest_path)
            self.progress.emit(100)
            self.finished.emit(self._dest_path)

        except (urllib.error.URLError, OSError, TimeoutError) as e:
            _safe_remove(tmp_path)
            self.failed.emit(str(e))
        except Exception as e:
            _safe_remove(tmp_path)
            self.failed.emit(f"Onverwachte fout: {e}")


def _safe_remove(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Download dialoogvenster
# ---------------------------------------------------------------------------

class DownloadDialog(QDialog):
    """
    Toont een voortgangsbalk tijdens het downloaden van de installer.
    Sluit zichzelf na succesvolle download en start de installer.

    Gebruik::

        dlg = DownloadDialog(url=download_url, version="11.0.3", parent=window)
        dlg.exec()
    """

    def __init__(self, url: str, version: str, parent=None):
        super().__init__(parent)
        self._url     = url
        self._version = version
        self._worker  = None
        self._dest    = _get_download_path(url)

        self.setWindowTitle(f"Update downloaden — v{version}")
        self.setMinimumWidth(420)
        self.setFixedHeight(140)
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint
        )
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 16)

        self._lbl = QLabel(f"Versie {self._version} downloaden...")
        layout.addWidget(self._lbl)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(True)
        layout.addWidget(self._bar)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_cancel = QPushButton("Annuleren")
        self._btn_cancel.setFixedWidth(100)
        self._btn_cancel.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._btn_cancel)
        layout.addLayout(btn_row)

    def showEvent(self, event):
        super().showEvent(event)
        self._start_download()

    def _start_download(self):
        self._worker = _DownloadWorker(self._url, self._dest, parent=self)
        self._worker.progress.connect(self._bar.setValue)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_cancel(self):
        if self._worker:
            self._worker.cancel()
        self.reject()

    def _on_finished(self, path: str):
        self._btn_cancel.setEnabled(False)
        self._lbl.setText(f"✓  Download voltooid!")
        self._bar.setValue(100)

        reply = QMessageBox.question(
            self,
            "Installatie starten",
            f"De installer is gedownload naar:\n{path}\n\nNu installeren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            _launch_installer(path)

        self.accept()

    def _on_failed(self, error: str):
        self._lbl.setText("Download mislukt.")
        QMessageBox.warning(
            self,
            "Download mislukt",
            f"De installer kon niet worden gedownload.\n\n{error}"
        )
        self.reject()


# ---------------------------------------------------------------------------
# Hulpfuncties
# ---------------------------------------------------------------------------

def _get_download_path(url: str) -> str:
    """Geeft het volledige pad naar het doelbestand in de Downloads map."""
    filename = url.split("/")[-1] or "networkmap_setup.exe"
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(downloads, exist_ok=True)
    return os.path.join(downloads, filename)


def _launch_installer(path: str):
    """Start de gedownloade installer via os.startfile (Windows)."""
    try:
        os.startfile(path)
    except Exception as e:
        QMessageBox.warning(
            None,
            "Installer starten mislukt",
            f"Kan de installer niet automatisch starten.\n\nOpen hem handmatig:\n{path}\n\nFout: {e}"
        )