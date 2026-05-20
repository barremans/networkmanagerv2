# =============================================================================
# Networkmap_Creator
# File:    app/gui/wall_outlet_view.py
# Role:    Wandpunten overzicht — per ruimte of per site
# Version: 1.10.0
# Author:  Barremans
# Changes: 1.10.0 — Direct modus: filter op rack_id als meegegeven
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
    QVBoxLayout, QHBoxLayout, QSizePolicy,
    QDialog, QMenu, QFormLayout, QTextBrowser,
    QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from app.helpers.i18n import t, get_language
from app.helpers.settings_storage import get_outlet_location_label, load_outlet_locations
from app.services import tracing


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
    outlet_endpoint_requested = Signal(str)   # W1: eindapparaat toevoegen/bewerken
    endpoint_edit_requested = Signal(str)     # 1.8.1: rechtsklik endpoint-kaartje → bewerken
    endpoint_double_clicked  = Signal(str)     # 1.9.0: dubbelklik endpoint-kaartje → detail popup

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
        self._build()

    # ------------------------------------------------------------------
    # Opbouw
    # ------------------------------------------------------------------

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

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
            col_count = 3 if self._mode == "site" else 4
            groups = self._group_by_location(all_outlets)

            for loc_key, loc_label, outlets_in_group in groups:
                # Sectieheader
                header = self._build_group_header(loc_label, len(outlets_in_group))
                body_layout.addWidget(header)

                # Kaartjes in vaste rijen van col_count — geen QGridLayout
                # (QGridLayout geeft inconsistente kolombreedte bij herlaad)
                row_widget = None
                row_layout = None
                for idx, (room, outlet) in enumerate(outlets_in_group):
                    if idx % col_count == 0:
                        row_widget = QWidget()
                        row_layout = QHBoxLayout(row_widget)
                        row_layout.setContentsMargins(0, 0, 0, 0)
                        row_layout.setSpacing(8)
                        row_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
                        body_layout.addWidget(row_widget)

                    endpoint = ep_map.get(outlet.get("endpoint_id", ""))
                    trace    = tracing.trace_from_wall_outlet(self._data, outlet["id"])
                    card     = self._build_outlet_card(
                        outlet, endpoint, trace,
                        room_name=room["name"] if self._mode == "site" else None
                    )
                    row_layout.addWidget(card)

                # Opvullen laatste rij met stretch zodat kaartjes links blijven
                if row_layout is not None:
                    row_layout.addStretch()

        # 1.8.0 — Direct verbonden endpoints sectie
        self._build_direct_endpoints_section(body_layout)

        body_layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)

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

        # F6 — sorteren binnen elke groep op sort_id ascending
        # sort_id=0 (niet ingesteld) komt achteraan via (sort_id==0, sort_id, naam)
        def _sort_key(item):
            _, outlet = item
            sid = int(outlet.get("sort_id", 0) or 0)
            return (sid == 0, sid, outlet.get("name", "").lower())

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
        # Site-modus: iets breder voor ruimtenaam + trace
        card.setFixedSize(200 if room_name else 160, 120 if room_name else 90)
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

        # Kaartjes in rijen van 4
        col_count = 3 if self._mode == "site" else 4
        row_widget = None
        row_layout = None
        for idx, (ep, port, dev) in enumerate(items):
            if idx % col_count == 0:
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(8)
                row_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
                body_layout.addWidget(row_widget)
            card = self._build_endpoint_card(ep, port, dev)
            row_layout.addWidget(card)
        if row_layout is not None:
            row_layout.addStretch()

    def _build_endpoint_card(self, ep: dict, port: dict | None,
                              dev: dict | None) -> QFrame:
        """
        1.8.0 — Kaartje voor een direct verbonden endpoint.
        1.8.1 — Rechtsklik opent contextmenu met Bewerken.
        """
        card = QFrame()
        card.setObjectName("wall-outlet")
        card.setFixedSize(160, 90)
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

        # Rechtsklik — contextmenu Bewerken
        ep_id = ep["id"]
        def _on_context(event, eid=ep_id):
            menu = QMenu(self)
            act_edit = menu.addAction("✏  " + t("ctx_edit"))
            action = menu.exec(QCursor.pos())
            if action == act_edit:
                self.endpoint_edit_requested.emit(eid)
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
        ep_map  = {e["id"]: e for e in self._data.get("endpoints", [])}
        ep      = ep_map.get(outlet.get("endpoint_id", ""))
        dlg     = _OutletDetailDialog(
            outlet, ep, self._data, parent=self,
            on_endpoint_clicked=lambda: self.outlet_endpoint_requested.emit(outlet_id),
        )
        dlg.exec()

    def _on_outlet_context_menu(self, outlet_id: str, event):
        """Rechtsklik — contextmenu met Bewerken en Eindapparaat opties."""
        menu = QMenu(self)
        act_edit = menu.addAction("✏  " + t("ctx_edit"))
        act_ep   = menu.addAction("🖥  " + t("btn_new_endpoint"))
        action   = menu.exec(QCursor.pos())
        if action == act_edit:
            self.outlet_edit_requested.emit(outlet_id)
        elif action == act_ep:
            self.outlet_endpoint_requested.emit(outlet_id)

    # ------------------------------------------------------------------
    # Data verversen
    # ------------------------------------------------------------------

    def refresh(self, data: dict):
        self._data = data
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._outlet_widgets.clear()
        self._selected_id = None
        self._build()

# ---------------------------------------------------------------------------
# Detail popup — dubbelklik op wandpunt kaartje
# ---------------------------------------------------------------------------

class _OutletDetailDialog(QDialog):
    """
    Toont alle velden van een wandpunt + gekoppeld eindapparaat in een
    read-only popup. Verschijnt bij dubbelklik op een wandpunt kaartje.
    """

    def __init__(self, outlet: dict, endpoint, data: dict, parent=None,
                 on_endpoint_clicked=None):
        super().__init__(parent)
        self._outlet              = outlet
        self._endpoint            = endpoint
        self._data                = data
        self._on_endpoint_clicked = on_endpoint_clicked
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

    def _on_ep_btn_clicked(self):
        """Sluit de popup en roep de endpoint callback aan."""
        self.accept()
        if self._on_endpoint_clicked:
            self._on_endpoint_clicked()

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