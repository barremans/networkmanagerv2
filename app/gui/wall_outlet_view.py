# =============================================================================
# Networkmap_Creator
# File:    app/gui/wall_outlet_view.py
# Role:    Wandpunten overzicht — per ruimte of per site
# Version: 1.3.0
# Author:  Barremans
# Changes: 1.3.0 — Fix: locatie key vertaald via get_outlet_location_label()
#                  op kaartje en tooltip (was raw key, bv. containerd_a)
# Author:  Barremans
# Changes: 1.2.0 — Dubbelklik op kaartje toont detail popup (alle velden + eindapparaat)
#                  Rechtsklik op kaartje toont contextmenu met 'Bewerken'
# =============================================================================

from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QScrollArea,
    QVBoxLayout, QHBoxLayout, QGridLayout, QSizePolicy,
    QDialog, QMenu, QFormLayout, QTextBrowser
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from app.helpers.i18n import t, get_language
from app.helpers.settings_storage import get_outlet_location_label
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
    outlet_edit_requested = Signal(str)   # rechtsklik / dubbelklik → bewerken

    # ------------------------------------------------------------------
    # Constructor — room- of site-modus
    # ------------------------------------------------------------------

    def __init__(self, room_or_site, context, data: dict,
                 mode: str = "room", parent=None):
        """
        room_or_site : room dict (mode='room') of site dict (mode='site')
        context      : site dict (mode='room') of genegeerd (mode='site')
        data         : volledig network_data dict
        mode         : 'room' | 'site'
        """
        super().__init__(parent)
        self._mode = mode
        if mode == "site":
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
        body_layout.setSpacing(8)
        body_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        ep_map = {e["id"]: e for e in self._data.get("endpoints", [])}

        if not all_outlets:
            empty_lbl = QLabel(
                t("site_outlets_empty") if self._mode == "site"
                else t("tree_no_endpoint")
            )
            empty_lbl.setObjectName("secondary")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            body_layout.addWidget(empty_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        else:
            col_count = 3 if self._mode == "site" else 4
            grid = QGridLayout()
            grid.setSpacing(8)
            for idx, (room, outlet) in enumerate(all_outlets):
                endpoint = ep_map.get(outlet.get("endpoint_id", ""))
                trace    = tracing.trace_from_wall_outlet(self._data, outlet["id"])
                card     = self._build_outlet_card(
                    outlet, endpoint, trace,
                    room_name=room["name"] if self._mode == "site" else None
                )
                grid.addWidget(card, idx // col_count, idx % col_count)

            # Opvullen lege cellen
            remainder = len(all_outlets) % col_count
            if remainder:
                for i in range(col_count - remainder):
                    spacer = QWidget()
                    spacer.setSizePolicy(
                        QSizePolicy.Policy.Expanding,
                        QSizePolicy.Policy.Preferred
                    )
                    grid.addWidget(
                        spacer,
                        len(all_outlets) // col_count,
                        remainder + i
                    )
            body_layout.addLayout(grid)

        body_layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)

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
        dlg     = _OutletDetailDialog(outlet, ep, self._data, parent=self)
        dlg.exec()

    def _on_outlet_context_menu(self, outlet_id: str, event):
        """Rechtsklik — contextmenu met Bewerken optie."""
        menu = QMenu(self)
        act_edit = menu.addAction("✏  " + "Bewerken")
        action   = menu.exec(QCursor.pos())
        if action == act_edit:
            self.outlet_edit_requested.emit(outlet_id)

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

    def __init__(self, outlet: dict, endpoint, data: dict, parent=None):
        super().__init__(parent)
        self._outlet   = outlet
        self._endpoint = endpoint
        self._data     = data
        self.setWindowTitle(f"📍  {outlet.get('name', '')}")
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
        btn_row.addStretch()
        btn_close = QPushButton(t("btn_cancel"))
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)