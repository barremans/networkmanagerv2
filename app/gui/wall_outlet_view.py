# =============================================================================
# Networkmap_Creator
# File:    app/gui/wall_outlet_view.py
# Role:    Wandpunten overzicht — per ruimte of per site
# Version: 1.22.0
# Author:  Barremans
# Changes: 1.22.0 — Rechtsklik verbonden wandpunt: "✂ Verbinding verwijderen"
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
    QPushButton, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QCursor
import re

from app.helpers.i18n import t, get_language
from app.helpers.settings_storage import get_outlet_location_label, load_outlet_locations
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
        else:
            self._search_bar = None

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
        """Verzamel alle (room, outlet) tuples voor de huidige site."""
        result = []
        for site in self._data.get("sites", []):
            if site["id"] == self._site["id"]:
                for room in site.get("rooms", []):
                    for wo in room.get("wall_outlets", []):
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
            for site in self._data.get("sites", []):
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

        dlg = _OutletDetailDialog(
            outlet, ep, self._data, parent=self,
            on_endpoint_clicked=_emit_ep,
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

        form_outlet.addRow(t("label_name")     + ":", QLabel(self._outlet.get("name", "—")))
        form_outlet.addRow(t("label_location") + ":", QLabel(loc_lbl))
        form_outlet.addRow("VLAN:",                   QLabel(vlan_str))
        form_outlet.addRow(t("label_notes")    + ":", QLabel(notes))
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
                else:
                    val = self._endpoint.get(key, "") or "—"
                form_ep.addRow(lbl + ":", QLabel(val))
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
        # 1.19.0 — Bewerken knop (wandpunt)
        if self._on_edit_clicked:
            btn_edit = QPushButton("✏  " + t("ctx_edit"))
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
        # W1: knop eindapparaat toevoegen/bewerken
        if self._on_endpoint_clicked:
            ep_label = t("ctx_edit") if self._endpoint else t("btn_new_endpoint")
            btn_ep = QPushButton(f"🖥  {ep_label}")
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

        def _row(label: str, value: str):
            lbl = QLabel(f"<b>{label}</b>")
            lbl.setFixedWidth(110)
            val = QLabel(value or "—")
            val.setWordWrap(True)
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
            root.addLayout(_row("MAC adres:",    ep.get("mac", "")))
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
                for _site in self._data.get("sites", []):
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