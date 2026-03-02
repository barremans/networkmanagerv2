# =============================================================================
# Networkmap_Creator
# File:    app/gui/search_window.py
# Role:    Zoekvenster popup — live zoeken + navigatie naar resultaat
# Version: 1.2.0
# Author:  Barremans
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QPushButton
)
from PySide6.QtCore import Qt, Signal, QTimer

from app.helpers.i18n import t
from app.services import search_service

# Icoon per resultaattype
_TYPE_ICON = {
    "device":     "💻",
    "port":       "⬡",
    "wall_outlet":"🌐",
    "endpoint":   "🖥",
}


class SearchWindow(QDialog):
    """
    Popup zoekvenster.
    Signaal result_selected(type, id) wanneer gebruiker op resultaat klikt.
    """
    result_selected = Signal(str, str)   # type, id

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self._data  = data
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)   # 200ms debounce
        self._timer.timeout.connect(self._do_search)

        self.setWindowTitle(t("menu_search"))
        self.setMinimumSize(480, 360)
        self.setModal(False)   # niet-modaal zodat boom ook klikbaar blijft
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Zoekveld
        search_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText(t("menu_search") + "...")
        self._input.textChanged.connect(self._on_text_changed)
        self._input.returnPressed.connect(self._do_search)
        search_row.addWidget(self._input)
        btn_close = QPushButton(t("btn_close"))
        btn_close.clicked.connect(self.close)
        search_row.addWidget(btn_close)
        layout.addLayout(search_row)

        # Resultaten label
        self._result_label = QLabel("")
        self._result_label.setObjectName("secondary")
        layout.addWidget(self._result_label)

        # Resultatenlijst
        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._on_item_activated)
        self._list.itemActivated.connect(self._on_item_activated)
        layout.addWidget(self._list)

        # Hint onderaan
        hint = QLabel(t("search_hint"))
        hint.setObjectName("secondary")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        # Focus op zoekveld
        self._input.setFocus()

    def _on_text_changed(self, text: str):
        """Start debounce timer bij elke toetsaanslag."""
        self._timer.start()

    def _do_search(self):
        """Voert de zoekopdracht uit en vult de lijst."""
        query   = self._input.text().strip()
        self._list.clear()

        if not query:
            self._result_label.setText("")
            return

        results = search_service.search(self._data, query)

        if not results:
            self._result_label.setText(t("search_no_results"))
            return

        self._result_label.setText(f"{len(results)} resultaat{'en' if len(results) != 1 else ''}")

        for r in results:
            icon  = _TYPE_ICON.get(r["type"], "•")
            label = f"{icon}  {r['label']}"
            loc   = r.get("location", "")
            if loc:
                label += f"\n     {loc}"

            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, r)
            self._list.addItem(item)

    def _on_item_activated(self, item: QListWidgetItem):
        """Gebruiker klikt op resultaat → signaal naar main_window."""
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self.result_selected.emit(data["type"], data["id"])
            self.close()

    def update_data(self, data: dict):
        """Data verversen als netwerk_data gewijzigd is."""
        self._data = data

    def showEvent(self, event):
        """
        Wordt aangeroepen bij elke opening (show() / raise_()).
        Leegt het zoekveld, wist de resultatenlijst en zet focus op het veld.
        Voldoet aan E2: zoekveld is altijd leeg bij openen via Ctrl+F.
        """
        super().showEvent(event)
        self._timer.stop()
        self._input.clear()
        self._list.clear()
        self._result_label.setText("")
        self._input.setFocus()