# =============================================================================
# Networkmap_Creator
# File:    app/gui/wall_outlet_view.py
# Role:    Wandpunten overzicht — per ruimte of per site
# Version: 1.29.0
# Author:  Barremans
# Changes: 1.29.0 — V7: VLAN-filter in titelregel (site-modus).
#                   _VlanPickerDialog: doorzoekbare popup met VLANs die voorkomen
#                   in de huidige selectie (na ruimte-/locatiefilter).
#                   _vlan_filter (int|None) + _btn_vlan in WallOutletView.
#                   _on_vlan_picker_clicked(), _collect_vlans_for_picker().
#                   _collect_site_outlets() filtert op _vlan_filter.
#                   Reset-keten: ruimtewissel → locatie + VLAN reset;
#                   locatiewissel → VLAN reset.
#                   Direct-verbonden sectie verborgen bij actieve VLAN-filter.
#                   4 nieuwe i18n-sleutels (v i18n.py v1.43.0).
# Changes: 1.28.0 — F8: per-veld kopiëren in de detailpopups. _OutletDetailDialog
#                   (Wandpunt + Eindapparaat) en _EndpointDetailDialog tonen nu per
#                   waarde-regel rechtsklik → "Kopiëren". MAC genormaliseerd via
#                   normalize_mac() (AA:BB:CC:DD:EE:FF). Gedeelde helpers
#                   _copyable_value_label() / _show_copy_menu(). Leesactie, ook in
#                   read-only modus. Geen menu op lege "—"-velden.
# Changes: 1.27.3 -- F1: get_all_sites() voor v2 JSON
#          1.27.2 — Bugfix: dubbel 🌐 icoon op locatiefilter knop —
#                   settings_tab_outlet_locations bevat al emoji, strip voor gebruik
#          1.27.1 — Direct verbonden sectie verborgen bij actieve filter
#                   _LocationPickerDialog, _btn_location, _location_filter,
#                   _on_location_picker_clicked()
#                   _collect_site_outlets() filtert ook op _location_filter
#          1.26.0 — Site-modus: QComboBox ruimtefilter vervangen door knop +
#          1.24.0 — outlet_endpoint_edit_requested(str) signaal toegevoegd
#                   "Eindapparaat bewerken" knop opent direct EndpointDialog
#                   (beide knoppen toonden anders "Bewerken")
#          1.23.0 — _OutletDetailDialog: wandpunt-knop = ctx_edit_outlet,
#                   eindapparaat-knop = ctx_edit_endpoint (ipv ctx_edit)
#          1.22.0 — Rechtsklik verbonden wandpunt: "✂ Verbinding verwijderen"
#                   outlet_disconnect_requested signaal + handler in main_window
#          1.21.2 — Fix: QTimer.singleShot(0) voor detail-dialoog callbacks
#                   zodat tweede dialoog pas opent nadat eerste volledig gesloten is
#          1.21.1 — Fix: callback vóór accept() aanroepen
#                   outlet_connect_port_requested signaal
#                   _OutletDetailDialog: "🔌 Koppelen" knop als geen verbinding
#          1.20.0 — Zoekbalk in titelregel: doorzoekt wandpunten én eindapparaten
#                   Zoekt op naam, ruimte, locatie, eindapparaatnaam, IP, serienummer
#                   Lege zoekterm → normale groepsweergave hersteld
#                   _apply_filter() + _build_search_results() methodes toegevoegd
#          1.19.0 — _OutletDetailDialog: "Bewerken" knop toegevoegd
#                   on_edit_clicked callback parameter
#          1.18.1 — Prefix-rij-breuk binnen locatiegroep: A-reeks → rij, B-reeks → nieuwe rij
#                   _name_prefix() helper: leading letters van naam (A21→A, CAM02→CAM)
#                   Debounce timer (150ms) op resizeEvent
#                   refresh() reset _last_col_count
#          1.18.0 — Dynamische kolombreedte via resizeEvent + QGridLayout per groep
#                   refresh() reset _last_col_count zodat col_count herberekend wordt
#                   QTimer import toegevoegd
#          1.18.0 — Dynamische kolombreedte via resizeEvent + QGridLayout per groep
#                   col_count berekend op basis van beschikbare breedte (_CARD_MIN_W=200)
#                   Bij vensterwijziging herlaadt de view automatisch met juist aantal kolommen
#                   setMaximumWidth(280) verwijderd — QGridLayout verdeelt ruimte gelijkmatig
#          1.17.0 — Rechtsklik wandpunt: "Dupliceren" optie
#                   outlet_duplicate_requested signaal toegevoegd
#          1.16.0 — Direct verbonden: groepering per aansluitapparaat
#                   Sortering: device naam (natural sort) → poortnummer (natural sort)
#                   Bv. PATCHPANEL A1 Port 6 → Port 7 → … / nieuwe groep SW10
#          1.15.0 — Bug fix: refresh() lege view na delete
#                   _build() hergebruikt bestaande layout bij refresh
#                   Direct endpoint kaartje: "Verwijderen" in rechtsklik menu
#                   endpoint_delete_requested signaal toegevoegd
#          1.14.0 — setMaximumWidth(280) op kaartjes
#                   addStretch() terug op rijen (vult lege ruimte rechts)
#                   Correcte mix: min 160px, max 280px, stretch absorbeert rest
#          1.13.0 — Responsieve kaartjes: setFixedSize → setMinimumWidth + Expanding policy
#                   Kaartjes vullen nu de volledige beschikbare breedte
#                   col_count verhoogd (max 6 room, max 5 site) voor brede schermen
#                   AlignLeft + addStretch op rijen verwijderd zodat kaartjes uitrekken
#          1.12.0 — Natural sort op wandpuntnaam binnen elke locatiegroep
#                   A2 < A10 < B1 (correct), i.p.v. A10 < A2 (string sort)
#                   sort_id=0 valt terug op natural sort ipv plain string sort
#          1.11.0 — Rechtsklik wandpunt kaartje: "Verwijderen" optie toegevoegd
#                   outlet_delete_requested signaal
#          1.10.0 — Direct modus: filter op rack_id als meegegeven
#                   Constructor accepteert rack_id + rack_name parameters
#                   Titelregel toont rack_name ipv site_name in direct modus
#          1.8.1 — Visuele scheiding voor "Direct verbonden" sectie (HR lijn)
#                  Rechtsklik op endpoint-kaartje: bewerken via outlet_endpoint_edit
#          1.8.0 — Direct endpoint: nieuwe sectie "🖥 Direct verbonden" onderaan
#                  _build_direct_endpoints_section() + _build_endpoint_card()
#                  Toont alle endpoints met een directe port→endpoint verbinding
#          1.7.0 — W1: eindapparaat aanmaken/bewerken vanuit wandpunt
#                  outlet_endpoint_requested signaal + rechtsklik + detail popup knop
#          1.6.0 — F6: sortering binnen locatiegroep op sort_id
#                  Wandpunten zonder sort_id (0) komen achteraan binnen groep
#          1.5.0 — F8: volgorde locatiegroepen gestuurd door load_outlet_locations()
#                  Groepen verschijnen nu in de volgorde zoals ingesteld in settings,
#                  niet meer op volgorde van eerste optreden in de data.
#                  Onbekende/lege locatie blijft altijd laatste (Overig).
#          1.4.0 — V5: wandpunten gegroepeerd per locatie met sectieheader
#                  Binnen elke groep: vaste 4-koloms grid zonder lege gaten
#                  Onbekende/lege locatie → groep "Overig" onderaan
#          1.3.0 — Fix: locatie key vertaald via get_outlet_location_label()
#                  op kaartje en tooltip (was raw key, bv. containerd_a)
# =============================================================================

from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QScrollArea,
    QVBoxLayout, QHBoxLayout, QSizePolicy, QGridLayout,
    QDialog, QMenu, QFormLayout, QTextBrowser,
    QPushButton, QLineEdit, QListWidget, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QCursor
import re

from app.helpers.i18n import t, get_language
from app.helpers.settings_storage import get_outlet_location_label
from app.helpers.settings_storage import get_all_sites, load_outlet_locations, get_all_sites
from app.helpers.formatting import normalize_mac          # F8 — MAC-normalisatie
from app.services import tracing

# 1.18.0 — minimale kaartbreedte voor col_count berekening
_CARD_MIN_W = 200
_CARD_SPACING = 8


def _natural_sort_key(name: str) -> list:
    """
    1.12.0 — Natural sort key: splitst een naam in tekst- en getalsdelen zodat
    A2 < A10 < B1 correct gesorteerd wordt (i.p.v. A10 < A2 bij string sort).
    """
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", name or "")
    ]


def _name_prefix(name: str) -> str:
    """
    1.18.1 — Geeft het leading-letters deel van een naam terug.
    Gebruikt voor rij-breuk bij prefix-wisseling in de grid.
    Voorbeelden: "A21" → "A", "B1" → "B", "CAM02" → "CAM", "W7" → "W"
    Nummers-only of leeg → "__num__" (apart blok onderaan)
    """
    m = re.match(r"^([A-Za-z]+)", name or "")
    return m.group(1).upper() if m else "__num__"


# =============================================================================
# F8 — kopieer-helpers voor de read-only detailpopups
# =============================================================================

def _show_copy_menu(widget: QLabel, pos, value: str):
    """Toont een 'Kopiëren'-menu en plaatst de waarde op het klembord."""
    from PySide6.QtWidgets import QApplication
    menu = QMenu(widget)
    act_copy = menu.addAction(t("ctx_copy"))
    if menu.exec(widget.mapToGlobal(pos)) == act_copy:
        QApplication.clipboard().setText(value)


def _copyable_value_label(text: str, copy_value: str = None) -> QLabel:
    """
    Waarde-label dat selecteerbaar is en — als de kopieerwaarde gevuld is —
    via rechtsklik een 'Kopiëren'-menu toont. Geen menu op lege '—'-waarde.
    Leesactie: ook beschikbaar in read-only modus.
    """
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

    cv = (copy_value if copy_value is not None else text)
    cv = (cv or "").strip()
    if cv and cv != "—":
        lbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        lbl.customContextMenuRequested.connect(
            lambda pos, w=lbl, v=cv: _show_copy_menu(w, pos, v)
        )
    return lbl


# =============================================================================
# _RoomPickerDialog — v1.26.0
# Popup dialoog om een ruimte te kiezen met zoekbalk.
# Zelfde patroon als FloorplanPickerDialog in main_window.py.
# =============================================================================

class _RoomPickerDialog(QDialog):
    """
    Dialoog om een ruimte te kiezen uit een doorzoekbare lijst.

    Parameters
    ----------
    rooms  : list[dict]  — ruimte-dicts met 'id' en 'name'
    parent : QWidget
    """

    def __init__(self, rooms: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("label_room"))
        self.setModal(True)
        self.setMinimumWidth(320)
        self.setMinimumHeight(300)

        self._rooms = rooms          # [{"id": ..., "name": ...}, ...]
        self._selected_id   = ""
        self._selected_name = ""

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Zoekbalk
        self._search = QLineEdit()
        self._search.setPlaceholderText(f"🔍  {t('search_placeholder_outlet_location')}")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter)
        layout.addWidget(self._search)

        # Lijst
        self._list = QListWidget()
        self._list.addItem(f"— {t('label_room')} —")
        self._list.item(0).setData(Qt.ItemDataRole.UserRole, "")
        for room in rooms:
            from PySide6.QtWidgets import QListWidgetItem
            item = QListWidgetItem(room.get("name", "?"))
            item.setData(Qt.ItemDataRole.UserRole, room.get("id", ""))
            self._list.addItem(item)
        layout.addWidget(self._list)

        # "Geen resultaten" label
        self._lbl_empty = QLabel(t("lbl_no_outlet_location_match"))
        self._lbl_empty.setObjectName("secondary")
        self._lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_empty.setVisible(False)
        layout.addWidget(self._lbl_empty)

        # Knoppen
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(self._buttons)

        self._list.setCurrentRow(0)
        self._search.textChanged.connect(self._filter)
        self._list.itemDoubleClicked.connect(self._on_double_click)
        self._buttons.accepted.connect(self._on_ok)
        self._buttons.rejected.connect(self.reject)

    def _filter(self, text: str):
        needle  = text.strip().lower()
        visible = 0
        first   = None
        for i in range(self._list.count()):
            item  = self._list.item(i)
            match = (not needle) or (needle in item.text().lower())
            item.setHidden(not match)
            if match:
                visible += 1
                if first is None:
                    first = i
        self._lbl_empty.setVisible(visible == 0)
        if first is not None:
            self._list.setCurrentRow(first)

    def _on_double_click(self, item):
        self._selected_id   = item.data(Qt.ItemDataRole.UserRole) or ""
        self._selected_name = item.text()
        self.accept()

    def _on_ok(self):
        item = self._list.currentItem()
        if item and not item.isHidden():
            self._selected_id   = item.data(Qt.ItemDataRole.UserRole) or ""
            self._selected_name = item.text()
        self.accept()

    def selected_id(self) -> str:
        return self._selected_id

    def selected_name(self) -> str:
        return self._selected_name


# =============================================================================
# _LocationPickerDialog — v1.27.0
# Popup dialoog om een wandpunt locatie te kiezen met zoekbalk.
# Gevuld met locaties die effectief voorkomen in de huidige outlet-set.
# =============================================================================

class _LocationPickerDialog(QDialog):
    """
    Dialoog om een wandpunt locatie te kiezen uit een doorzoekbare lijst.

    Parameters
    ----------
    locations : list[tuple[str, str]]  — (loc_key, loc_label) tuples
    parent    : QWidget
    """

    def __init__(self, locations: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("settings_tab_outlet_locations"))
        self.setModal(True)
        self.setMinimumWidth(320)
        self.setMinimumHeight(300)

        self._selected_key   = ""
        self._selected_label = ""

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText(f"🔍  {t('search_placeholder_outlet_location')}")
        self._search.setClearButtonEnabled(True)
        layout.addWidget(self._search)

        self._list = QListWidget()
        # Eerste item = "alle locaties"
        from PySide6.QtWidgets import QListWidgetItem
        all_item = QListWidgetItem(f"— {t('settings_tab_outlet_locations').strip()} —")
        all_item.setData(Qt.ItemDataRole.UserRole, ("", ""))
        self._list.addItem(all_item)
        for key, label in locations:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, (key, label))
            self._list.addItem(item)
        layout.addWidget(self._list)

        self._lbl_empty = QLabel(t("lbl_no_outlet_location_match"))
        self._lbl_empty.setObjectName("secondary")
        self._lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_empty.setVisible(False)
        layout.addWidget(self._lbl_empty)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(self._buttons)

        self._list.setCurrentRow(0)
        self._search.textChanged.connect(self._filter)
        self._list.itemDoubleClicked.connect(self._on_double_click)
        self._buttons.accepted.connect(self._on_ok)
        self._buttons.rejected.connect(self.reject)

    def _filter(self, text: str):
        needle  = text.strip().lower()
        visible = 0
        first   = None
        for i in range(self._list.count()):
            item  = self._list.item(i)
            match = (not needle) or (needle in item.text().lower())
            item.setHidden(not match)
            if match:
                visible += 1
                if first is None:
                    first = i
        self._lbl_empty.setVisible(visible == 0)
        if first is not None:
            self._list.setCurrentRow(first)

    def _on_double_click(self, item):
        key, label = item.data(Qt.ItemDataRole.UserRole)
        self._selected_key, self._selected_label = key, label
        self.accept()

    def _on_ok(self):
        item = self._list.currentItem()
        if item and not item.isHidden():
            key, label = item.data(Qt.ItemDataRole.UserRole)
            self._selected_key, self._selected_label = key, label
        self.accept()

    def selected_key(self) -> str:
        return self._selected_key

    def selected_label(self) -> str:
        return self._selected_label


# =============================================================================
# _VlanPickerDialog — V7
# Popup om een VLAN te kiezen uit de VLANs die effectief voorkomen in de
# huidige selectie (na ruimte- en locatiefilter).
# =============================================================================

class _VlanPickerDialog(QDialog):
    """
    V7 — Doorzoekbare VLAN-keuzepopup.

    Parameters
    ----------
    vlans  : list[tuple[int, str]]  — (vlan_id, vlan_label) tuples,
             alleen VLANs die voorkomen in de huidige wandpuntenselectie.
    parent : QWidget
    """

    def __init__(self, vlans: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("vlan_filter_picker_title"))
        self.setModal(True)
        self.setMinimumWidth(320)
        self.setMinimumHeight(300)

        self._selected_id    = None   # int | None
        self._selected_label = ""

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText(f"🔍  {t('vlan_filter_btn')}...")
        self._search.setClearButtonEnabled(True)
        layout.addWidget(self._search)

        self._list = QListWidget()
        from PySide6.QtWidgets import QListWidgetItem
        # Eerste item = "alle VLANs" (reset)
        all_item = QListWidgetItem(t("vlan_filter_all"))
        all_item.setData(Qt.ItemDataRole.UserRole, (None, ""))
        self._list.addItem(all_item)
        for vlan_id, vlan_lbl in vlans:
            item = QListWidgetItem(vlan_lbl)
            item.setData(Qt.ItemDataRole.UserRole, (vlan_id, vlan_lbl))
            self._list.addItem(item)
        layout.addWidget(self._list)

        self._lbl_empty = QLabel(t("vlan_filter_no_vlans"))
        self._lbl_empty.setObjectName("secondary")
        self._lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_empty.setVisible(False)
        layout.addWidget(self._lbl_empty)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(self._buttons)

        self._list.setCurrentRow(0)
        self._search.textChanged.connect(self._filter)
        self._list.itemDoubleClicked.connect(self._on_double_click)
        self._buttons.accepted.connect(self._on_ok)
        self._buttons.rejected.connect(self.reject)

    def _filter(self, text: str):
        needle  = text.strip().lower()
        visible = 0
        first   = None
        for i in range(self._list.count()):
            item  = self._list.item(i)
            # "Alle VLANs" item altijd zichtbaar
            if i == 0:
                item.setHidden(False)
                visible += 1
                first = 0
                continue
            match = (not needle) or (needle in item.text().lower())
            item.setHidden(not match)
            if match:
                visible += 1
                if first is None:
                    first = i
        self._lbl_empty.setVisible(visible == 0)
        if first is not None:
            self._list.setCurrentRow(first)

    def _on_double_click(self, item):
        vlan_id, vlan_lbl = item.data(Qt.ItemDataRole.UserRole)
        self._selected_id    = vlan_id
        self._selected_label = vlan_lbl
        self.accept()

    def _on_ok(self):
        item = self._list.currentItem()
        if item and not item.isHidden():
            vlan_id, vlan_lbl = item.data(Qt.ItemDataRole.UserRole)
            self._selected_id    = vlan_id
            self._selected_label = vlan_lbl
        self.accept()

    def selected_id(self) -> int | None:
        return self._selected_id

    def selected_label(self) -> str:
        return self._selected_label


class WallOutletView(QWidget):
    """
    Toont wandpunten als klikbare kaartjes.

    Modi:
      room  — alle wandpunten van één ruimte  (standaard, bestaand gedrag)
      site  — alle wandpunten van alle ruimtes in één site (E3 nieuw)

    Elk kaartje toont:
      - Naam + locatiebeschrijving
      - Ruimtenaam (alleen in site-modus)
      - Eindapparaat indien gekoppeld
      - Korte trace-samenvatting: wandpunt → ... → switch/eindpunt


    Signaal:
      outlet_clicked(outlet_id)  — klik op een wandpunt
    """

    outlet_clicked = Signal(str)
    outlet_edit_requested = Signal(str)       # rechtsklik → bewerken
    outlet_delete_requested = Signal(str)     # 1.11.0: rechtsklik → verwijderen
    outlet_duplicate_requested = Signal(str)  # 1.17.0: rechtsklik → dupliceren (ruimte+locatie)
    outlet_endpoint_requested = Signal(str)   # W1: eindapparaat toevoegen/bewerken
    outlet_endpoint_edit_requested = Signal(str)  # 1.24.0: eindapparaat direct bewerken (outlet_id)
    outlet_connect_port_requested = Signal(str)  # 1.21.0: koppelen aan poort
    outlet_disconnect_requested = Signal(str)    # 1.22.0: verbinding verwijderen
    endpoint_edit_requested = Signal(str)     # 1.8.1: rechtsklik endpoint-kaartje → bewerken
    endpoint_delete_requested = Signal(str)   # 1.15.0: rechtsklik endpoint-kaartje → verwijderen
    endpoint_double_clicked  = Signal(str)    # 1.9.0: dubbelklik endpoint-kaartje → detail popup

    # ------------------------------------------------------------------
    # Constructor — room- of site-modus
    # ------------------------------------------------------------------

    def __init__(self, room_or_site, context, data: dict,
                 mode: str = "room", parent=None,
                 rack_id: str = "", rack_name: str = ""):
        """
        room_or_site : room dict (mode='room') of site dict (mode='site')
        context      : site dict (mode='room') of genegeerd (mode='site')
        data         : volledig network_data dict
        mode         : 'room' | 'site' | 'direct'
        rack_id      : filter direct-modus op één rack (optioneel)
        rack_name    : weergavenaam van de rack voor de titelregel
        """
        super().__init__(parent)
        self._mode      = mode
        self._rack_id   = rack_id    # v1.10.0 — filter voor direct modus
        self._rack_name = rack_name  # v1.10.0 — titelregel
        if mode == "site" or mode == "direct":
            self._site = room_or_site
            self._room = None
        else:
            self._room = room_or_site
            self._site = context
        self._data           = data
        self._outlet_widgets = {}
        self._selected_id    = None
        self._last_col_count = 0   # 1.18.0 — voor resize rebuild detectie
        self._search_text    = ""  # 1.20.0 — actieve zoekterm
        self._room_filter        = ""  # 1.25.0 — ruimtefilter (site-modus only)
        self._location_filter    = ""  # 1.27.0 — wandpunt locatiefilter (site-modus only)
        self._vlan_filter: int | None = None  # V7 — VLAN-filter (site-modus only)
        # 1.18.0 — debounce timer: rebuild pas na 150ms stilstand resize
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._on_resize_settled)
        self._build()

    # ------------------------------------------------------------------
    # 1.18.0 — Dynamische kolombreedte op basis van beschikbare breedte
    # ------------------------------------------------------------------

    def _col_count(self) -> int:
        """Berekent optimaal aantal kolommen op basis van huidige breedte."""
        w = self.width() or 800
        cols = max(1, (w + _CARD_SPACING) // (_CARD_MIN_W + _CARD_SPACING))
        return cols

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start(150)   # debounce 150ms

    def _on_resize_settled(self):
        """Wordt aangeroepen na 150ms stilstand — rebuild als col_count gewijzigd."""
        new_cols = self._col_count()
        if new_cols != self._last_col_count:
            self._last_col_count = new_cols
            layout = self.layout()
            if layout:
                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
            self._outlet_widgets.clear()
            self._selected_id = None
            self._build()

    # ------------------------------------------------------------------
    # Opbouw
    # ------------------------------------------------------------------

    def _build(self):
        # 1.15.0 — gebruik bestaande layout als die al bestaat (voor refresh)
        if self.layout() is None:
            outer = QVBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(0)
        else:
            outer = self.layout()

        # Titelregel
        title_bar = QFrame()
        title_bar.setObjectName("rack_frame")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(8, 4, 8, 4)

        if self._mode == "site":
            title_text = (
                f"🌐  {t('site_outlets_title')}  —  {self._site['name']}"
            )
            all_outlets = self._collect_site_outlets()
        elif self._mode == "direct":
            context_name = self._rack_name if self._rack_name else self._site['name']
            title_text = (
                f"🖥  {t('wall_outlet_group_direct')}  —  {context_name}"
            )
            all_outlets = []
        else:
            title_text = (
                f"🌐  {t('title_wall_outlets')}  —  "
                f"{self._room['name']}  —  {self._site['name']}"
            )
            all_outlets = [
                (self._room, wo)
                for wo in self._room.get("wall_outlets", [])
            ]

        title_lbl = QLabel(title_text)
        title_lbl.setObjectName("rack_title")
        if self._mode == "direct":
            count_lbl = QLabel("")
        else:
            count_lbl = QLabel(
                f"{len(all_outlets)}  {t('tree_wall_outlets').lower()}"
            )
        count_lbl.setObjectName("secondary")
        count_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        title_layout.addWidget(title_lbl)
        title_layout.addStretch()

        # 1.20.0 — Zoekbalk (alleen in site- en room-modus, niet in direct-modus)
        if self._mode in ("site", "room"):
            self._search_bar = QLineEdit()
            self._search_bar.setPlaceholderText(f"🔍  {t('search_placeholder_outlets')}")
            self._search_bar.setMaximumWidth(280)
            self._search_bar.setFixedHeight(26)
            self._search_bar.setText(self._search_text)
            self._search_bar.textChanged.connect(self._on_search_changed)
            title_layout.addWidget(self._search_bar)
            title_layout.addSpacing(8)

            # 1.26.0 — Ruimte-knop opent _RoomPickerDialog (site-modus only)
            if self._mode == "site":
                room_label = t("label_room")
                if self._room_filter:
                    room = next(
                        (r for r in self._site.get("rooms", [])
                         if r.get("id") == self._room_filter), None
                    )
                    room_label = room.get("name", t("label_room")) if room else t("label_room")
                self._btn_room = QPushButton(f"🚪  {room_label}")
                self._btn_room.setFixedHeight(26)
                self._btn_room.setMinimumWidth(160)
                self._btn_room.clicked.connect(self._on_room_picker_clicked)
                title_layout.addWidget(self._btn_room)
                title_layout.addSpacing(4)

                # 1.27.0 — Wandpunt locatiefilter knop
                # settings_tab_outlet_locations bevat al een 🌐 emoji — niet herhalen
                _raw_loc_label = t("settings_tab_outlet_locations").strip()
                _loc_btn_label = _raw_loc_label.lstrip("🌐 ").strip() \
                    if _raw_loc_label.startswith("🌐") else _raw_loc_label
                if self._location_filter:
                    _loc_btn_label = get_outlet_location_label(
                        self._location_filter, get_language()
                    ) or self._location_filter
                self._btn_location = QPushButton(f"🌐  {_loc_btn_label}")
                self._btn_location.setFixedHeight(26)
                self._btn_location.setMinimumWidth(160)
                self._btn_location.clicked.connect(self._on_location_picker_clicked)
                title_layout.addWidget(self._btn_location)
                title_layout.addSpacing(4)

                # V7 — VLAN-filter knop
                _vlan_btn_label = t("vlan_filter_btn")
                if self._vlan_filter is not None:
                    from app.services.vlan_service import vlan_label as _vlan_label
                    _vlan_btn_label = _vlan_label(self._vlan_filter)
                self._btn_vlan = QPushButton(f"🔀  {_vlan_btn_label}")
                self._btn_vlan.setFixedHeight(26)
                self._btn_vlan.setMinimumWidth(120)
                self._btn_vlan.clicked.connect(self._on_vlan_picker_clicked)
                title_layout.addWidget(self._btn_vlan)
                title_layout.addSpacing(8)
            else:
                self._btn_room     = None
                self._btn_location = None
                self._btn_vlan     = None
        else:
            self._search_bar   = None
            self._btn_room     = None
            self._btn_location = None
            self._btn_vlan     = None

        title_layout.addWidget(count_lbl)
        outer.addWidget(title_bar)

        # Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(12, 12, 12, 12)
        body_layout.setSpacing(16)
        body_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        ep_map = {e["id"]: e for e in self._data.get("endpoints", [])}

        if self._mode == "direct":
            # Geen wandpunten tonen — alleen direct verbonden sectie
            pass
        elif self._search_text.strip():
            # 1.20.0 — Zoekresultaten: platte lijst zonder groepsheaders
            self._build_search_results(body_layout, all_outlets, ep_map)
        elif not all_outlets:
            empty_lbl = QLabel(
                t("site_outlets_empty") if self._mode == "site"
                else t("tree_no_endpoint")
            )
            empty_lbl.setObjectName("secondary")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            body_layout.addWidget(empty_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        else:
            # V5 — groeperen per locatie (location_description)
            # 1.18.0 — QGridLayout per groep: kolommen dynamisch op breedte
            # 1.18.1 — Binnen elke locatiegroep: nieuwe grid-rij per naam-prefix (A, B, C…)
            col_count = self._col_count()
            groups = self._group_by_location(all_outlets)

            for loc_key, loc_label, outlets_in_group in groups:
                header = self._build_group_header(loc_label, len(outlets_in_group))
                body_layout.addWidget(header)

                grid_widget = QWidget()
                grid = QGridLayout(grid_widget)
                grid.setContentsMargins(0, 0, 0, 0)
                grid.setSpacing(_CARD_SPACING)
                for col in range(col_count):
                    grid.setColumnStretch(col, 1)
                body_layout.addWidget(grid_widget)

                # Groepeer per prefix (leading letters) voor automatische rij-breuk
                # A21,A22,A23 → prefix "A" → eigen blok rijen
                # B1,B2 → prefix "B" → volgende blok rijen, enz.
                grid_row   = 0
                grid_col   = 0
                cur_prefix = None

                for room, outlet in outlets_in_group:
                    name   = outlet.get("name", "")
                    prefix = _name_prefix(name)

                    # Prefix gewisseld → nieuwe rij starten
                    if prefix != cur_prefix:
                        if cur_prefix is not None and grid_col > 0:
                            grid_row += 1   # sluit vorige prefix-rij af
                        grid_col   = 0
                        cur_prefix = prefix

                    endpoint = ep_map.get(outlet.get("endpoint_id", ""))
                    trace    = tracing.trace_from_wall_outlet(self._data, outlet["id"])
                    card     = self._build_outlet_card(
                        outlet, endpoint, trace,
                        room_name=room["name"] if self._mode == "site" else None
                    )
                    grid.addWidget(card, grid_row, grid_col)
                    grid_col += 1
                    if grid_col >= col_count:
                        grid_col = 0
                        grid_row += 1

        # 1.8.0 — Direct verbonden endpoints sectie
        # 1.27.0 — Verborgen bij actieve locatie- of ruimtefilter (niet relevant)
        # V7     — ook verborgen bij actieve VLAN-filter
        if self._mode != "site" or (not self._room_filter and not self._location_filter and self._vlan_filter is None):
            self._build_direct_endpoints_section(body_layout)

        body_layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------
    # 1.20.0 — Zoeken over wandpunten en eindapparaten
    # ------------------------------------------------------------------

    def _on_search_changed(self, text: str):
        """Zoekterm gewijzigd — bewaar en rebuild scroll-inhoud."""
        self._search_text = text
        # Rebuild enkel de scroll-inhoud, niet de hele view
        layout = self.layout()
        if not layout:
            return
        # Verwijder alles behalve de titelregel (index 0)
        while layout.count() > 1:
            item = layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self._outlet_widgets.clear()

        # Rebuild scroll + body
        ep_map      = {e["id"]: e for e in self._data.get("endpoints", [])}
        all_outlets = self._collect_site_outlets() if self._mode == "site" \
                      else [(self._room, wo) for wo in self._room.get("wall_outlets", [])]

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body        = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(12, 12, 12, 12)
        body_layout.setSpacing(16)
        body_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        if text.strip():
            self._build_search_results(body_layout, all_outlets, ep_map)
        elif not all_outlets:
            empty_lbl = QLabel(
                t("site_outlets_empty") if self._mode == "site"
                else t("tree_no_endpoint")
            )
            empty_lbl.setObjectName("secondary")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            body_layout.addWidget(empty_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        else:
            col_count = self._col_count()
            groups    = self._group_by_location(all_outlets)
            for loc_key, loc_label, outlets_in_group in groups:
                header = self._build_group_header(loc_label, len(outlets_in_group))
                body_layout.addWidget(header)
                grid_widget = QWidget()
                grid = QGridLayout(grid_widget)
                grid.setContentsMargins(0, 0, 0, 0)
                grid.setSpacing(_CARD_SPACING)
                for col in range(col_count):
                    grid.setColumnStretch(col, 1)
                body_layout.addWidget(grid_widget)
                grid_row, grid_col, cur_prefix = 0, 0, None
                for room, outlet in outlets_in_group:
                    prefix = _name_prefix(outlet.get("name", ""))
                    if prefix != cur_prefix:
                        if cur_prefix is not None and grid_col > 0:
                            grid_row += 1
                        grid_col, cur_prefix = 0, prefix
                    endpoint = ep_map.get(outlet.get("endpoint_id", ""))
                    trace    = tracing.trace_from_wall_outlet(self._data, outlet["id"])
                    card     = self._build_outlet_card(
                        outlet, endpoint, trace,
                        room_name=room["name"] if self._mode == "site" else None
                    )
                    grid.addWidget(card, grid_row, grid_col)
                    grid_col += 1
                    if grid_col >= col_count:
                        grid_col, grid_row = 0, grid_row + 1

        # 1.27.0 — Verborgen bij actieve locatie- of ruimtefilter
        # V7     — ook verborgen bij actieve VLAN-filter
        if self._mode != "site" or (not self._room_filter and not self._location_filter and self._vlan_filter is None):
            self._build_direct_endpoints_section(body_layout)
        body_layout.addStretch()
        scroll.setWidget(body)
        layout.addWidget(scroll)

    def _on_room_picker_clicked(self):
        """1.26.0 — Ruimte-knop geklikt — open _RoomPickerDialog."""
        rooms = self._site.get("rooms", [])
        dlg   = _RoomPickerDialog(rooms, parent=self)
        if not dlg.exec():
            return
        self._room_filter = dlg.selected_id()
        if self._btn_room:
            label = dlg.selected_name() if self._room_filter else t("label_room")
            self._btn_room.setText(f"🚪  {label}")
        # Locatiefilter resetten: bij nieuwe ruimte kan de locatie niet meer geldig zijn
        self._location_filter = ""
        if self._btn_location:
            _raw = t("settings_tab_outlet_locations").strip()
            _lbl = _raw.lstrip("🌐 ").strip() if _raw.startswith("🌐") else _raw
            self._btn_location.setText(f"🌐  {_lbl}")
        # V7 — VLAN-filter ook resetten
        self._vlan_filter = None
        if self._btn_vlan:
            self._btn_vlan.setText(f"🔀  {t('vlan_filter_btn')}")
        if self._search_bar and self._search_text:
            self._search_bar.blockSignals(True)
            self._search_bar.clear()
            self._search_bar.blockSignals(False)
            self._search_text = ""
        self._rebuild_scroll()

    def _on_location_picker_clicked(self):
        """1.27.0 — Locatiefilter knop — open _LocationPickerDialog."""
        lang = get_language()
        all_for_loc = self._collect_site_outlets_unfiltered_location()
        seen_keys: dict[str, str] = {}
        for _room, wo in all_for_loc:
            key = wo.get("location_description", "").strip()
            if key and key not in seen_keys:
                seen_keys[key] = get_outlet_location_label(key, lang) or key

        defined_keys = [loc["key"] for loc in load_outlet_locations()]
        ordered = [(k, seen_keys[k]) for k in defined_keys if k in seen_keys]
        known = set(defined_keys)
        for k, lbl in seen_keys.items():
            if k not in known:
                ordered.append((k, lbl))

        dlg = _LocationPickerDialog(ordered, parent=self)
        if not dlg.exec():
            return

        self._location_filter = dlg.selected_key()
        if self._btn_location:
            if self._location_filter:
                lbl = dlg.selected_label()
            else:
                _raw = t("settings_tab_outlet_locations").strip()
                lbl  = _raw.lstrip("🌐 ").strip() if _raw.startswith("🌐") else _raw
            self._btn_location.setText(f"🌐  {lbl}")

        # V7 — VLAN-filter resetten: bij nieuwe locatie kan VLAN-keuze ongeldig zijn
        self._vlan_filter = None
        if self._btn_vlan:
            self._btn_vlan.setText(f"🔀  {t('vlan_filter_btn')}")

        if self._search_bar and self._search_text:
            self._search_bar.blockSignals(True)
            self._search_bar.clear()
            self._search_bar.blockSignals(False)
            self._search_text = ""

        self._rebuild_scroll()

    def _collect_site_outlets_unfiltered_location(self) -> list[tuple[dict, dict]]:
        """Outlets gefilterd op ruimte, NIET op locatie — voor de locatiepicker."""
        result = []
        for site in get_all_sites(self._data):
            if site["id"] == self._site["id"]:
                for room in site.get("rooms", []):
                    if self._room_filter and room.get("id") != self._room_filter:
                        continue
                    for wo in room.get("wall_outlets", []):
                        result.append((room, wo))
        return result

    def _collect_vlans_for_picker(self) -> list[tuple[int, str]]:
        """
        V7 — Verzamel alle unieke VLANs die voorkomen in de huidige selectie
        (na ruimte- en locatiefilter, NIET na VLAN-filter zelf).
        Geeft gesorteerde lijst van (vlan_id, vlan_label) tuples terug.
        """
        from app.services.vlan_service import vlan_label as _vlan_label
        outlets = self._collect_site_outlets_unfiltered_location()
        # Als locatiefilter actief: gebruik de gefilterde set op locatie maar niet op VLAN
        if self._location_filter:
            outlets = [
                (room, wo) for room, wo in outlets
                if wo.get("location_description", "").strip() == self._location_filter
            ]
        seen: dict[int, str] = {}
        for _room, wo in outlets:
            vlan_raw = wo.get("vlan")
            if vlan_raw not in (None, ""):
                try:
                    vid = int(vlan_raw)
                    if vid not in seen:
                        seen[vid] = _vlan_label(vid)
                except (ValueError, TypeError):
                    pass
        return sorted(seen.items())  # gesorteerd op vlan_id

    def _on_vlan_picker_clicked(self):
        """V7 — VLAN-filter knop geklikt — open _VlanPickerDialog."""
        vlans = self._collect_vlans_for_picker()
        dlg   = _VlanPickerDialog(vlans, parent=self)
        if not dlg.exec():
            return
        self._vlan_filter = dlg.selected_id()  # None = alle VLANs
        if self._btn_vlan:
            if self._vlan_filter is not None:
                self._btn_vlan.setText(f"🔀  {dlg.selected_label()}")
            else:
                self._btn_vlan.setText(f"🔀  {t('vlan_filter_btn')}")
        if self._search_bar and self._search_text:
            self._search_bar.blockSignals(True)
            self._search_bar.clear()
            self._search_bar.blockSignals(False)
            self._search_text = ""
        self._rebuild_scroll()

    def _rebuild_scroll(self):
        """1.27.0 — Gemeenschappelijke scroll-rebuild na filter- of zoekaanpassing."""
        layout = self.layout()
        if not layout:
            return
        while layout.count() > 1:
            item = layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self._outlet_widgets.clear()

        ep_map      = {e["id"]: e for e in self._data.get("endpoints", [])}
        all_outlets = self._collect_site_outlets()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body        = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(12, 12, 12, 12)
        body_layout.setSpacing(16)
        body_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        if self._search_text.strip():
            self._build_search_results(body_layout, all_outlets, ep_map)
        elif not all_outlets:
            empty_lbl = QLabel(t("site_outlets_empty"))
            empty_lbl.setObjectName("secondary")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            body_layout.addWidget(empty_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        else:
            col_count = self._col_count()
            groups    = self._group_by_location(all_outlets)
            for loc_key, loc_label, outlets_in_group in groups:
                header = self._build_group_header(loc_label, len(outlets_in_group))
                body_layout.addWidget(header)
                grid_widget = QWidget()
                grid = QGridLayout(grid_widget)
                grid.setContentsMargins(0, 0, 0, 0)
                grid.setSpacing(_CARD_SPACING)
                for col in range(col_count):
                    grid.setColumnStretch(col, 1)
                body_layout.addWidget(grid_widget)
                grid_row, grid_col, cur_prefix = 0, 0, None
                for room, outlet in outlets_in_group:
                    prefix = _name_prefix(outlet.get("name", ""))
                    if prefix != cur_prefix:
                        if cur_prefix is not None and grid_col > 0:
                            grid_row += 1
                        grid_col, cur_prefix = 0, prefix
                    endpoint = ep_map.get(outlet.get("endpoint_id", ""))
                    trace    = tracing.trace_from_wall_outlet(self._data, outlet["id"])
                    card     = self._build_outlet_card(
                        outlet, endpoint, trace,
                        room_name=room["name"] if self._mode == "site" else None
                    )
                    grid.addWidget(card, grid_row, grid_col)
                    grid_col += 1
                    if grid_col >= col_count:
                        grid_col, grid_row = 0, grid_row + 1

        # 1.27.0 — Verborgen bij actieve locatie- of ruimtefilter
        # V7     — ook verborgen bij actieve VLAN-filter
        if self._mode != "site" or (not self._room_filter and not self._location_filter and self._vlan_filter is None):
            self._build_direct_endpoints_section(body_layout)
        body_layout.addStretch()
        scroll.setWidget(body)
        layout.addWidget(scroll)

    def _build_search_results(
        self,
        body_layout: QVBoxLayout,
        all_outlets: list[tuple[dict, dict]],
        ep_map: dict,
    ):
        """
        1.20.0 — Bouw gefilterde resultatenweergave.
        Zoekt in: wandpuntnaam, ruimtenaam, locatielabel, eindapparaatnaam,
                  eindapparaat IP, eindapparaat serienummer, eindapparaat model.
        Wandpunten en eindapparaten worden samen getoond, gesorteerd op naam.
        """
        q    = self._search_text.strip().lower()
        lang = get_language()

        # ── Wandpunten zoeken ────────────────────────────────────────
        matched_outlets: list[tuple[dict, dict]] = []
        for room, outlet in all_outlets:
            ep      = ep_map.get(outlet.get("endpoint_id", ""))
            loc_key = outlet.get("location_description", "")
            loc_lbl = get_outlet_location_label(loc_key, lang) if loc_key else ""
            haystack = " ".join(filter(None, [
                outlet.get("name", ""),
                room.get("name", ""),
                loc_lbl,
                ep.get("name", "")    if ep else "",
                ep.get("ip", "")      if ep else "",
                ep.get("serial", "")  if ep else "",
                ep.get("model", "")   if ep else "",
                ep.get("brand", "")   if ep else "",
            ])).lower()
            if q in haystack:
                matched_outlets.append((room, outlet))

        # ── Direct verbonden eindapparaten zoeken ────────────────────
        direct_conns = [
            c for c in self._data.get("connections", [])
            if c.get("to_type") == "endpoint" or c.get("from_type") == "endpoint"
        ]
        port_map = {p["id"]: p for p in self._data.get("ports", [])}
        dev_map  = {d["id"]: d for d in self._data.get("devices", [])}

        # Scope: alleen devices van de huidige site/ruimte
        if self._mode == "room":
            allowed_device_ids = {
                slot.get("device_id")
                for rack in self._room.get("racks", [])
                for slot in rack.get("slots", [])
                if slot.get("device_id")
            }
        else:
            allowed_device_ids = {
                slot.get("device_id")
                for room in self._site.get("rooms", [])
                for rack in room.get("racks", [])
                for slot in rack.get("slots", [])
                if slot.get("device_id")
            }

        matched_direct: list[tuple] = []
        seen_ep_ids = set()
        for conn in direct_conns:
            ep_id   = conn["to_id"]   if conn.get("to_type")   == "endpoint" else conn["from_id"]
            port_id = conn["from_id"] if conn.get("to_type")   == "endpoint" else conn["to_id"]
            if ep_id in seen_ep_ids:
                continue
            ep   = ep_map.get(ep_id)
            port = port_map.get(port_id)
            dev  = dev_map.get(port["device_id"]) if port else None
            if allowed_device_ids and (not port or port.get("device_id") not in allowed_device_ids):
                continue
            if not ep:
                continue
            haystack = " ".join(filter(None, [
                ep.get("name", ""),
                ep.get("ip", ""),
                ep.get("serial", ""),
                ep.get("model", ""),
                ep.get("brand", ""),
                ep.get("location", ""),
                dev.get("name", "") if dev else "",
            ])).lower()
            if q in haystack:
                matched_direct.append((ep, port, dev))
                seen_ep_ids.add(ep_id)

        total = len(matched_outlets) + len(matched_direct)

        # ── Resultaten header ────────────────────────────────────────
        hdr = self._build_group_header(
            f"🔍  {t('search_results')}  \"{self._search_text}\"", total
        )
        body_layout.addWidget(hdr)

        if total == 0:
            empty_lbl = QLabel(t("search_no_results"))
            empty_lbl.setObjectName("secondary")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            body_layout.addWidget(empty_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
            return

        col_count = self._col_count()

        # ── Wandpunten resultaten ────────────────────────────────────
        if matched_outlets:
            matched_outlets.sort(key=lambda x: _natural_sort_key(x[1].get("name", "")))
            grid_widget = QWidget()
            grid = QGridLayout(grid_widget)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(_CARD_SPACING)
            for col in range(col_count):
                grid.setColumnStretch(col, 1)
            body_layout.addWidget(grid_widget)
            for idx, (room, outlet) in enumerate(matched_outlets):
                row, col = divmod(idx, col_count)
                endpoint = ep_map.get(outlet.get("endpoint_id", ""))
                trace    = tracing.trace_from_wall_outlet(self._data, outlet["id"])
                card     = self._build_outlet_card(
                    outlet, endpoint, trace,
                    room_name=room["name"]   # altijd ruimtenaam tonen in zoekresultaten
                )
                grid.addWidget(card, row, col)

        # ── Direct verbonden eindapparaten resultaten ────────────────
        if matched_direct:
            if matched_outlets:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet("color: rgba(255,255,255,0.10); margin: 4px 0;")
                body_layout.addWidget(sep)

            ep_hdr = self._build_group_header(
                f"🖥  {t('wall_outlet_group_direct')}", len(matched_direct)
            )
            body_layout.addWidget(ep_hdr)

            grid_widget = QWidget()
            grid = QGridLayout(grid_widget)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(_CARD_SPACING)
            for col in range(col_count):
                grid.setColumnStretch(col, 1)
            body_layout.addWidget(grid_widget)
            for idx, (ep, port, dev) in enumerate(matched_direct):
                row, col = divmod(idx, col_count)
                card = self._build_endpoint_card(ep, port, dev)
                grid.addWidget(card, row, col)

    def _group_by_location(
        self, outlets: list[tuple[dict, dict]]
    ) -> list[tuple[str, str, list]]:
        """
        F8 — Groepeer (room, outlet) tuples per location_description.
        Volgorde wordt bepaald door load_outlet_locations() uit settings,
        zodat de gebruiker de volgorde kan instellen via Instellingen.
        Lege/onbekende locatie komt altijd als laatste groep ('Overig').

        Retourneert: lijst van (loc_key, loc_label, [(room, outlet), ...])
        """
        lang = get_language()
        groups  : dict[str, list] = {}
        labels  : dict[str, str]  = {}
        fallback_key = "__overig__"

        for room, outlet in outlets:
            key = outlet.get("location_description", "").strip()
            if not key:
                key = fallback_key
                label = "Overig"
            else:
                label = get_outlet_location_label(key, lang) or key

            if key not in groups:
                groups[key] = []
                labels[key] = label
            groups[key].append((room, outlet))

        # Volgorde: gedefinieerde locaties in settings-volgorde, daarna Overig
        defined_keys = [loc["key"] for loc in load_outlet_locations()]
        order = [k for k in defined_keys if k in groups]

        # Onbekende keys (niet in settings) tussengevoegd voor Overig
        known = set(defined_keys) | {fallback_key}
        for k in groups:
            if k not in known:
                order.append(k)

        if fallback_key in groups:
            order.append(fallback_key)

        # F6/1.12.0 — sorteren binnen elke groep:
        #   primair: sort_id (0 = niet ingesteld → achteraan)
        #   secundair: natural sort op naam (A2 < A10 < B1)
        def _sort_key(item):
            _, outlet = item
            sid = int(outlet.get("sort_id", 0) or 0)
            return (sid == 0, sid, _natural_sort_key(outlet.get("name", "")))

        return [(k, labels[k], sorted(groups[k], key=_sort_key)) for k in order]

    def _build_group_header(self, label: str, count: int) -> QFrame:
        """V5 — Sectieheader boven elke locatiegroep."""
        frame = QFrame()
        frame.setObjectName("outlet_group_header")
        frame.setStyleSheet(
            "QFrame#outlet_group_header {"
            "  background-color: rgba(255,255,255,0.05);"
            "  border-left: 3px solid #56B4E9;"
            "  border-radius: 2px;"
            "  padding: 2px 6px;"
            "}"
        )
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        lbl = QLabel(f"📍  {label}")
        lbl.setObjectName("rack_title")
        lbl.setStyleSheet("font-size: 12px; font-weight: bold;")

        cnt = QLabel(f"{count}  {t('tree_wall_outlets').lower()}")
        cnt.setObjectName("secondary")
        cnt.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(lbl)
        layout.addStretch()
        layout.addWidget(cnt)
        return frame

    def _collect_site_outlets(self) -> list[tuple[dict, dict]]:
        """Verzamel alle (room, outlet) tuples voor de huidige site.
        1.25.0 — filtert op _room_filter indien ingesteld.
        1.27.0 — filtert ook op _location_filter indien ingesteld.
        V7     — filtert ook op _vlan_filter indien ingesteld."""
        result = []
        for site in get_all_sites(self._data):
            if site["id"] == self._site["id"]:
                for room in site.get("rooms", []):
                    if self._room_filter and room.get("id") != self._room_filter:
                        continue
                    for wo in room.get("wall_outlets", []):
                        if self._location_filter:
                            wo_loc = wo.get("location_description", "").strip()
                            if wo_loc != self._location_filter:
                                continue
                        if self._vlan_filter is not None:
                            try:
                                wo_vlan = int(wo.get("vlan") or 0)
                            except (ValueError, TypeError):
                                wo_vlan = 0
                            if wo_vlan != self._vlan_filter:
                                continue
                        result.append((room, wo))
        return result

    # ------------------------------------------------------------------
    # Wandpunt kaartje
    # ------------------------------------------------------------------

    def _build_outlet_card(self, outlet: dict, endpoint,
                            trace: list, room_name: str | None) -> QFrame:
        card = QFrame()
        card.setObjectName("wall-outlet")
        # 1.13.0 — Responsief: minimumbreedte i.p.v. vaste breedte
        # Hoogte vast (inhoud past altijd), breedte rekt mee met beschikbare ruimte
        card.setMinimumWidth(160)
        card.setMinimumHeight(120 if room_name else 90)
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        card.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        card.setToolTip(get_outlet_location_label(
            outlet.get("location_description", ""), get_language()
        ))

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        # Naam
        name_lbl = QLabel(outlet.get("name", ""))
        name_lbl.setObjectName("outlet-label")
        layout.addWidget(name_lbl)

        # Ruimtenaam (alleen site-modus)
        if room_name:
            room_lbl = QLabel(f"🚪  {room_name}")
            room_lbl.setObjectName("secondary")
            layout.addWidget(room_lbl)

        # Locatiebeschrijving
        loc_key = outlet.get("location_description", "")
        loc     = get_outlet_location_label(loc_key, get_language()) if loc_key else ""
        if loc:
            loc_lbl = QLabel(loc)
            loc_lbl.setObjectName("secondary")
            loc_lbl.setWordWrap(True)
            layout.addWidget(loc_lbl)

        layout.addStretch()

        # Trace samenvatting
        trace_summary = self._build_trace_summary(trace)
        trace_lbl = QLabel(trace_summary)
        trace_lbl.setObjectName("secondary")
        trace_lbl.setWordWrap(True)
        layout.addWidget(trace_lbl)

        # Klik events
        outlet_id = outlet["id"]
        self._outlet_widgets[outlet_id] = card

        card.mousePressEvent = lambda e, oid=outlet_id, c=card: \
            self._on_outlet_clicked(oid, c, e)
        card.mouseDoubleClickEvent = lambda e, oid=outlet_id, o=outlet: \
            self._on_outlet_double_clicked(oid, o)
        card.contextMenuEvent = lambda e, oid=outlet_id: \
            self._on_outlet_context_menu(oid, e)

        return card

    def _build_trace_summary(self, trace: list) -> str:
        """
        Bouw een korte trace-samenvatting voor op het kaartje.
        Toont: Eindapparaat → ... → Switch/eindpunt
        Maximaal 2 stappen zichtbaar.
        """
        if not trace:
            return f"○  {t('site_outlets_no_connection')}"

        # Zoek het eerste en laatste zinvolle label
        labels = [s["label"] for s in trace if s.get("label")]
        if not labels:
            return f"○  {t('site_outlets_no_connection')}"

        # Zoek de eindbestemming (laatste poort of endpoint)
        last_port = next(
            (s for s in reversed(trace) if s["obj_type"] == "port"),
            None
        )
        first_ep = next(
            (s for s in trace if s["obj_type"] == "endpoint"),
            None
        )

        if last_port and first_ep:
            return f"🖥  {first_ep['label']}\n⬡  {last_port['label']}"
        elif last_port:
            return f"⬡  {last_port['label']}"
        elif first_ep:
            return f"🖥  {first_ep['label']}"
        else:
            return f"○  {t('site_outlets_no_connection')}"

    # ------------------------------------------------------------------
    # Direct verbonden endpoints sectie (1.8.0)
    # ------------------------------------------------------------------

    def _build_direct_endpoints_section(self, body_layout: QVBoxLayout):
        """
        1.8.0 — Toont alle endpoints die rechtstreeks verbonden zijn aan een
        switch-poort (port → endpoint, zonder wandpunt).
        Sectie wordt alleen getoond als er minstens één zulke verbinding bestaat.
        """
        # Verzamel alle directe port→endpoint verbindingen
        direct_conns = [
            c for c in self._data.get("connections", [])
            if c.get("to_type") == "endpoint" or c.get("from_type") == "endpoint"
        ]
        if not direct_conns:
            return

        ep_map   = {e["id"]: e for e in self._data.get("endpoints", [])}
        port_map = {p["id"]: p for p in self._data.get("ports", [])}
        dev_map  = {d["id"]: d for d in self._data.get("devices", [])}

        # Bepaal welke device_ids relevant zijn voor de huidige modus
        if self._mode == "room":
            # Alleen devices in de racks van deze ruimte
            allowed_device_ids = {
                slot.get("device_id")
                for rack in self._room.get("racks", [])
                for slot in rack.get("slots", [])
                if slot.get("device_id")
            }
        elif self._mode == "direct" and self._rack_id:
            # v1.10.0 — Filter op specifieke rack
            allowed_device_ids = set()
            for site in get_all_sites(self._data):
                for room in site.get("rooms", []):
                    for rack in room.get("racks", []):
                        if rack["id"] == self._rack_id:
                            for slot in rack.get("slots", []):
                                if slot.get("device_id"):
                                    allowed_device_ids.add(slot["device_id"])
        elif self._mode in ("site", "direct"):
            # Alle devices in alle ruimtes van deze site
            allowed_device_ids = {
                slot.get("device_id")
                for room in self._site.get("rooms", [])
                for rack in room.get("racks", [])
                for slot in rack.get("slots", [])
                if slot.get("device_id")
            }
        else:
            allowed_device_ids = None  # geen filter

        # Bouw lijst van (endpoint, port, device) tuples
        items = []
        for conn in direct_conns:
            if conn.get("to_type") == "endpoint":
                ep_id   = conn["to_id"]
                port_id = conn["from_id"]
            else:
                ep_id   = conn["from_id"]
                port_id = conn["to_id"]
            ep   = ep_map.get(ep_id)
            port = port_map.get(port_id)
            dev  = dev_map.get(port["device_id"]) if port else None
            # Filter op ruimte/site
            if allowed_device_ids is not None:
                if not port or port.get("device_id") not in allowed_device_ids:
                    continue
            if ep:
                items.append((ep, port, dev))

        if not items:
            return

        # Visuele scheiding boven de sectie — alleen in room/site modus
        if self._mode != "direct":
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setStyleSheet("color: rgba(255,255,255,0.15); margin: 8px 0;")
            body_layout.addWidget(separator)

        # Sectieheader — weglaten in direct modus (titel staat al in de title bar)
        if self._mode != "direct":
            header = QFrame()
            header.setObjectName("outlet_group_header")
            header.setStyleSheet(
                "QFrame#outlet_group_header {"
                "  background-color: rgba(255,255,255,0.05);"
                "  border-left: 3px solid #2196f3;"
                "  border-radius: 2px;"
                "  padding: 2px 6px;"
                "}"
            )
            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(8, 4, 8, 4)
            header_layout.setSpacing(8)
            hdr_lbl = QLabel(t("wall_outlet_group_direct"))
            hdr_lbl.setObjectName("rack_title")
            hdr_lbl.setStyleSheet("font-size: 12px; font-weight: bold;")
            cnt_lbl = QLabel(f"{len(items)}")
            cnt_lbl.setObjectName("secondary")
            cnt_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            header_layout.addWidget(hdr_lbl)
            header_layout.addStretch()
            header_layout.addWidget(cnt_lbl)
            body_layout.addWidget(header)

        # 1.16.0 — Groeperen per aansluitapparaat, gesorteerd op device naam + poortnummer
        # Sortering: device naam (natural sort) → poortnummer (natural sort)
        def _port_sort_key(item):
            _, port, dev = item
            dev_name  = dev.get("name", "") if dev else ""
            port_name = port.get("name", "") if port else ""
            return (_natural_sort_key(dev_name), _natural_sort_key(port_name))

        items.sort(key=_port_sort_key)

        # Groepeer per device_id
        from collections import OrderedDict
        groups: OrderedDict[str, list] = OrderedDict()
        for item in items:
            _, port, dev = item
            dev_id = dev.get("id", "") if dev else "__no_device__"
            if dev_id not in groups:
                groups[dev_id] = []
            groups[dev_id].append(item)

        for dev_id, grp_items in groups.items():
            # Subheader per device
            _, _, dev = grp_items[0]
            dev_name = dev.get("name", t("label_unknown")) if dev else t("label_unknown")
            sub = QFrame()
            sub.setObjectName("outlet_group_header")
            sub.setStyleSheet(
                "QFrame#outlet_group_header {"
                "  background-color: rgba(255,255,255,0.05);"
                "  border-left: 3px solid #2196f3;"
                "  border-radius: 2px;"
                "}"
            )
            sub_layout = QHBoxLayout(sub)
            sub_layout.setContentsMargins(8, 4, 8, 4)
            sub_layout.setSpacing(8)
            sub_lbl = QLabel(f"⬡  {dev_name}")
            sub_lbl.setObjectName("rack_title")
            sub_lbl.setStyleSheet("font-size: 11px; font-weight: bold;")
            cnt_lbl = QLabel(str(len(grp_items)))
            cnt_lbl.setObjectName("secondary")
            cnt_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            sub_layout.addWidget(sub_lbl)
            sub_layout.addStretch()
            sub_layout.addWidget(cnt_lbl)
            body_layout.addWidget(sub)

            # 1.18.0 — QGridLayout per device groep
            col_count = self._col_count()

            grid_widget = QWidget()
            grid = QGridLayout(grid_widget)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(_CARD_SPACING)
            for col in range(col_count):
                grid.setColumnStretch(col, 1)
            body_layout.addWidget(grid_widget)

            for idx, (ep, port, dev_item) in enumerate(grp_items):
                row, col = divmod(idx, col_count)
                card = self._build_endpoint_card(ep, port, dev_item)
                grid.addWidget(card, row, col)

    def _build_endpoint_card(self, ep: dict, port: dict | None,
                              dev: dict | None) -> QFrame:
        """
        1.8.0 — Kaartje voor een direct verbonden endpoint.
        1.8.1 — Rechtsklik opent contextmenu met Bewerken.
        """
        card = QFrame()
        card.setObjectName("wall-outlet")
        # 1.13.0 — Responsief: minimumbreedte i.p.v. vaste breedte
        card.setMinimumWidth(160)
        card.setMinimumHeight(90)
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        card.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        # Naam
        name_lbl = QLabel(f"🖥  {ep.get('name', '?')}")
        name_lbl.setObjectName("outlet-label")
        layout.addWidget(name_lbl)

        # Locatie (optioneel)
        loc = ep.get("location", "")
        if loc:
            loc_lbl = QLabel(loc)
            loc_lbl.setObjectName("secondary")
            loc_lbl.setWordWrap(True)
            layout.addWidget(loc_lbl)

        layout.addStretch()

        # Verbonden poort
        if port and dev:
            port_lbl = QLabel(
                f"⬡  {dev.get('name', '?')} — {port.get('name', '?')}"
                f" ({port.get('side', '').upper()})"
            )
        elif port:
            port_lbl = QLabel(f"⬡  {port.get('name', '?')}")
        else:
            port_lbl = QLabel(f"○  {t('site_outlets_no_connection')}")
        port_lbl.setObjectName("secondary")
        port_lbl.setWordWrap(True)
        layout.addWidget(port_lbl)

        # Rechtsklik — contextmenu Bewerken + Verwijderen (1.15.0)
        ep_id = ep["id"]
        def _on_context(event, eid=ep_id):
            menu = QMenu(self)
            act_edit = menu.addAction("✏  " + t("ctx_edit"))
            menu.addSeparator()
            act_del  = menu.addAction("🗑  " + t("ctx_delete"))
            action = menu.exec(QCursor.pos())
            if action == act_edit:
                self.endpoint_edit_requested.emit(eid)
            elif action == act_del:
                self.endpoint_delete_requested.emit(eid)
        card.contextMenuEvent = _on_context

        # 1.9.0 — Dubbelklik opent detail popup + emit signal
        def _on_ep_double_click(event, eid=ep_id, _ep=ep, _port=port, _dev=dev):
            self.endpoint_double_clicked.emit(eid)
            dlg = _EndpointDetailDialog(_ep, _port, _dev, self._data, parent=self)
            dlg.exec()
        card.mouseDoubleClickEvent = _on_ep_double_click

        return card

    # ------------------------------------------------------------------
    # Klik handler
    # ------------------------------------------------------------------

    def _on_outlet_clicked(self, outlet_id: str, card: QFrame, event=None):
        if self._selected_id and self._selected_id in self._outlet_widgets:
            prev = self._outlet_widgets[self._selected_id]
            prev.setObjectName("wall-outlet")
            prev.setStyle(prev.style())
        self._selected_id = outlet_id
        card.setObjectName("wall-outlet-selected")
        card.setStyle(card.style())
        self.outlet_clicked.emit(outlet_id)

    def _on_outlet_double_clicked(self, outlet_id: str, outlet: dict):
        """Dubbelklik — toon detail popup met alle wandpunt + eindapparaat info."""
        from PySide6.QtCore import QTimer
        ep_map  = {e["id"]: e for e in self._data.get("endpoints", [])}
        ep      = ep_map.get(outlet.get("endpoint_id", ""))

        # 1.21.1 — callbacks via QTimer.singleShot zodat detail-dialoog
        # volledig gesloten is vóór de volgende dialoog opent
        def _emit_edit():
            QTimer.singleShot(0, lambda: self.outlet_edit_requested.emit(outlet_id))

        def _emit_connect():
            QTimer.singleShot(0, lambda: self.outlet_connect_port_requested.emit(outlet_id))

        def _emit_ep():
            QTimer.singleShot(0, lambda: self.outlet_endpoint_requested.emit(outlet_id))

        def _emit_ep_edit():
            # 1.24.0 — direct EndpointDialog openen voor gekoppeld eindapparaat
            QTimer.singleShot(0, lambda: self.outlet_endpoint_edit_requested.emit(outlet_id))

        dlg = _OutletDetailDialog(
            outlet, ep, self._data, parent=self,
            on_endpoint_clicked=_emit_ep_edit if ep else _emit_ep,
            on_edit_clicked=_emit_edit,
            on_connect_clicked=_emit_connect,
        )
        dlg.exec()

    def _on_outlet_context_menu(self, outlet_id: str, event):
        """Rechtsklik — contextmenu met Bewerken, Eindapparaat, Dupliceren en Verwijderen."""
        is_connected = any(
            c for c in self._data.get("connections", [])
            if c.get("from_id") == outlet_id or c.get("to_id") == outlet_id
        )
        menu = QMenu(self)
        act_edit    = menu.addAction("✏  " + t("ctx_edit"))
        act_ep      = menu.addAction("🖥  " + t("btn_new_endpoint"))
        # Koppelen (vrij) of loskoppelen (verbonden)
        act_connect    = None
        act_disconnect = None
        if not is_connected:
            act_connect = menu.addAction("🔌  " + t("ctx_connect_outlet_to_port"))
        else:
            act_disconnect = menu.addAction("✂  " + t("ctx_disconnect_port"))
        act_dup  = menu.addAction("⧉  " + t("ctx_duplicate"))
        menu.addSeparator()
        act_del  = menu.addAction("🗑  " + t("ctx_delete"))
        action   = menu.exec(QCursor.pos())
        if action == act_edit:
            self.outlet_edit_requested.emit(outlet_id)
        elif action == act_ep:
            self.outlet_endpoint_requested.emit(outlet_id)
        elif act_connect and action == act_connect:
            self.outlet_connect_port_requested.emit(outlet_id)
        elif act_disconnect and action == act_disconnect:
            self.outlet_disconnect_requested.emit(outlet_id)
        elif action == act_dup:
            self.outlet_duplicate_requested.emit(outlet_id)
        elif action == act_del:
            self.outlet_delete_requested.emit(outlet_id)

    # ------------------------------------------------------------------
    # Data verversen
    # ------------------------------------------------------------------

    def refresh(self, data: dict):
        self._data = data
        self._last_col_count = 0   # 1.18.0 — forceer col_count herberekening
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._outlet_widgets.clear()
        self._selected_id = None
        self._build()
        # 1.20.0 — herstel zoekterm na refresh
        if self._search_text and self._search_bar:
            self._search_bar.setText(self._search_text)

# ---------------------------------------------------------------------------
# Detail popup — dubbelklik op wandpunt kaartje
# ---------------------------------------------------------------------------

class _OutletDetailDialog(QDialog):
    """
    Toont alle velden van een wandpunt + gekoppeld eindapparaat in een
    read-only popup. Verschijnt bij dubbelklik op een wandpunt kaartje.
    """

    def __init__(self, outlet: dict, endpoint, data: dict, parent=None,
                 on_endpoint_clicked=None, on_edit_clicked=None,
                 on_connect_clicked=None):
        super().__init__(parent)
        self._outlet              = outlet
        self._endpoint            = endpoint
        self._data                = data
        self._on_endpoint_clicked = on_endpoint_clicked
        self._on_edit_clicked     = on_edit_clicked   # 1.19.0 — bewerken callback
        self._on_connect_clicked  = on_connect_clicked  # 1.21.0 — koppelen aan poort
        self.setWindowTitle(outlet.get('name', ''))
        self.setMinimumWidth(400)
        self.setModal(True)
        self._build()

    def _build(self):
        from PySide6.QtWidgets import QPushButton, QGroupBox, QHBoxLayout
        from app.helpers.i18n import t
        from app.helpers.settings_storage import (
            load_outlet_locations, get_outlet_location_label
        )
        from app.helpers.i18n import get_language
        from app.services import tracing

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Wandpunt info ──────────────────────────────────────────────
        grp_outlet = QGroupBox(t("label_wall_outlet"))
        form_outlet = QFormLayout(grp_outlet)
        form_outlet.setSpacing(6)

        lang     = get_language()
        loc_key  = self._outlet.get("location_description", "")
        loc_lbl  = get_outlet_location_label(loc_key, lang) if loc_key else "—"

        vlan_val = self._outlet.get("vlan")
        if vlan_val is not None:
            from app.services.vlan_service import load_vlans
            vlan_str = f"VLAN {vlan_val}"
            for v in load_vlans():
                if v.get("id") == int(vlan_val):
                    vlan_str += f"  —  {v['name']}" if v.get("name") else ""
                    break
        else:
            vlan_str = "—"

        notes = self._outlet.get("notes", "") or "—"

        form_outlet.addRow(t("label_name")     + ":", _copyable_value_label(self._outlet.get("name", "—")))
        form_outlet.addRow(t("label_location") + ":", _copyable_value_label(loc_lbl))
        form_outlet.addRow("VLAN:",                   _copyable_value_label(vlan_str))
        form_outlet.addRow(t("label_notes")    + ":", _copyable_value_label(notes))
        layout.addWidget(grp_outlet)

        # ── Eindapparaat info ──────────────────────────────────────────
        grp_ep = QGroupBox(t("label_endpoint"))
        form_ep = QFormLayout(grp_ep)
        form_ep.setSpacing(6)

        if self._endpoint:
            from app.helpers.settings_storage import get_endpoint_type_label
            ep_type_lbl = get_endpoint_type_label(
                self._endpoint.get("type", ""), lang
            )
            for lbl, key in [
                (t("label_name"),   "name"),
                (t("label_type"),   None),
                (t("label_ip"),     "ip"),
                (t("label_mac"),    "mac"),
                (t("label_serial"), "serial"),
                (t("label_brand"),  "brand"),
                (t("label_model"),  "model"),
                (t("label_notes"),  "notes"),
            ]:
                if key is None:
                    val = ep_type_lbl
                    copy_val = None
                else:
                    val = self._endpoint.get(key, "") or "—"
                    copy_val = normalize_mac(val) if key == "mac" else None
                form_ep.addRow(lbl + ":", _copyable_value_label(val, copy_val))
        else:
            form_ep.addRow("", QLabel("— " + t("tree_no_endpoint") + " —"))

        layout.addWidget(grp_ep)

        # ── Trace samenvatting ─────────────────────────────────────────
        trace = tracing.trace_from_wall_outlet(self._data, self._outlet["id"])
        if trace:
            grp_trace = QGroupBox("Trace")
            trace_layout = QVBoxLayout(grp_trace)
            for step in trace:
                lbl = step.get("label", "")
                if lbl:
                    trace_layout.addWidget(QLabel(f"  →  {lbl}"))
            layout.addWidget(grp_trace)

        # ── Sluitknop ──────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        # 1.19.0 — Bewerken knop (wandpunt); 1.23.0 — ctx_edit_outlet ipv ctx_edit
        if self._on_edit_clicked:
            btn_edit = QPushButton(t("ctx_edit_outlet"))
            btn_edit.clicked.connect(self._on_edit_btn_clicked)
            btn_row.addWidget(btn_edit)
        # 1.21.0 — Koppelen aan poort (alleen als nog geen verbinding)
        if self._on_connect_clicked:
            is_connected = any(
                c for c in self._data.get("connections", [])
                if c.get("from_id") == self._outlet["id"]
                or c.get("to_id")   == self._outlet["id"]
            )
            if not is_connected:
                btn_connect = QPushButton("🔌  " + t("ctx_connect_outlet_to_port"))
                btn_connect.clicked.connect(self._on_connect_btn_clicked)
                btn_row.addWidget(btn_connect)
        # W1: knop eindapparaat toevoegen — alleen als nog geen eindapparaat (1.24.0: bewerken verwijderd)
        if self._on_endpoint_clicked and not self._endpoint:
            btn_ep = QPushButton("🖥  " + t("btn_new_endpoint"))
            btn_ep.clicked.connect(self._on_ep_btn_clicked)
            btn_row.addWidget(btn_ep)
        btn_row.addStretch()
        btn_close = QPushButton(t("btn_cancel"))
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _on_edit_btn_clicked(self):
        """1.19.0 — Sluit popup en open wandpunt bewerk-dialoog."""
        if self._on_edit_clicked:
            self._on_edit_clicked()
        self.accept()

    def _on_connect_btn_clicked(self):
        """1.21.0 — Sluit popup en open poort-koppel dialoog."""
        if self._on_connect_clicked:
            self._on_connect_clicked()
        self.accept()

    def _on_ep_btn_clicked(self):
        """Sluit de popup en roep de endpoint callback aan."""
        if self._on_endpoint_clicked:
            self._on_endpoint_clicked()
        self.accept()

# ---------------------------------------------------------------------------
# Detail popup — dubbelklik op direct endpoint kaartje (1.9.0)
# ---------------------------------------------------------------------------

class _EndpointDetailDialog(QDialog):
    """
    1.9.0 — Toont alle velden van een direct verbonden endpoint in een
    read-only popup. Verschijnt bij dubbelklik op een endpoint kaartje.
    """

    def __init__(self, ep: dict, port: dict | None, dev: dict | None,
                 data: dict, parent=None):
        super().__init__(parent)
        self._ep   = ep
        self._port = port
        self._dev  = dev
        self._data = data
        self._build_ui()

    def _build_ui(self):
        ep = self._ep
        self.setWindowTitle(ep.get("name", "Eindapparaat"))
        self.setModal(True)
        self.setMinimumWidth(380)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        def _section(title: str):
            lbl = QLabel(title)
            lbl.setObjectName("group-label")
            lbl.setStyleSheet("font-weight: bold; margin-top: 4px;")
            return lbl

        def _row(label: str, value: str, copy_value: str = None):
            lbl = QLabel(f"<b>{label}</b>")
            lbl.setFixedWidth(110)
            val = _copyable_value_label(value or "—", copy_value)
            row = QHBoxLayout()
            row.addWidget(lbl)
            row.addWidget(val, 1)
            return row

        # Endpoint sectie
        root.addWidget(_section(t("label_endpoint")))
        root.addLayout(_row(t("label_name"),     ep.get("name", "")))
        from app.helpers.settings_storage import get_endpoint_type_label as _get_ep_type
        from app.helpers.i18n import get_language as _get_lang
        ep_type_display = _get_ep_type(ep.get("type", ""), _get_lang()) or ep.get("type", "")
        root.addLayout(_row(t("label_type"), ep_type_display))
        root.addLayout(_row(t("endpoint_location"), ep.get("location", "")))
        if ep.get("ip"):
            root.addLayout(_row("IP adres:",     ep.get("ip", "")))
        if ep.get("mac"):
            root.addLayout(_row("MAC adres:",    ep.get("mac", ""),
                                normalize_mac(ep.get("mac", ""))))
        if ep.get("serial"):
            root.addLayout(_row("Serienummer:",  ep.get("serial", "")))
        if ep.get("brand") or ep.get("model"):
            root.addLayout(_row("Merk / Model:", f"{ep.get('brand','')} {ep.get('model','')}".strip()))
        if ep.get("notes"):
            root.addLayout(_row(t("label_notes"), ep.get("notes", "")))

        # Verbonden poort sectie
        if self._port:
            root.addWidget(_section(t("label_port")))
            # Zoek rack + ruimte voor deze poort
            port_lbl = ""
            rack_room_lbl = ""
            if self._dev:
                dev_id = self._dev.get("id", "")
                for _site in get_all_sites(self._data):
                    for _room in _site.get("rooms", []):
                        for _rack in _room.get("racks", []):
                            for _slot in _rack.get("slots", []):
                                if _slot.get("device_id") == dev_id:
                                    rack_room_lbl = f"{_room.get('name','?')} — {_rack.get('name','?')}"
                port_lbl = (
                    f"{self._dev.get('name','?')} — "
                    f"{self._port.get('name','?')} ({self._port.get('side','').upper()})"
                )
            else:
                port_lbl = f"{self._port.get('name','?')} ({self._port.get('side','').upper()})"
            if rack_room_lbl:
                root.addLayout(_row(t("label_location"), rack_room_lbl))
            root.addLayout(_row(t("label_connected_port"), port_lbl))
            if self._port.get("vlan"):
                from app.services.vlan_service import vlan_label
                root.addLayout(_row("VLAN:", vlan_label(self._port.get("vlan"), self._data)))

        # Trace sectie
        from app.services import tracing
        ep_id = ep.get("id", "")
        # Zoek poort-id voor trace
        port_id = self._port.get("id") if self._port else None
        if port_id:
            steps = tracing.trace_from_port(self._data, port_id)
            if steps:
                root.addWidget(_section("Trace"))
                for step in steps:
                    lbl = QLabel(f"  →  {step.get('label', '')}")
                    lbl.setObjectName("secondary")
                    root.addWidget(lbl)

        root.addStretch()

        # Sluit knop
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton(t("btn_cancel"))
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        root.addLayout(btn_row)