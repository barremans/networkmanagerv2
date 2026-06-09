# =============================================================================
# Networkmap_Creator
# File:    app/gui/floorplan_view.py
# Role:    Grondplan viewer — basis mockup met rechter zijpaneel
# Version: 1.27.0
# Author:  Barremans
# Changes: 1.27.0 — select_by_target_val: stap 3 volledig uitgewerkt (3a/3b/3c)
#                   3a: wo_id → PP back-poort → directe mapping
#                   3b: PP back → PP front via zelfde device+number, andere side
#                   3c: PP front → switch-poort via connection → mapping
#                   Fix: wandpunt → PP back → PP front → switch → SVG punt ✅
#          1.26.0 — select_by_target_val: stap 3 + 4 toegevoegd
#                   Stap 3: wo_id → verbinding → "port:port_id" in mappings
#                   Stap 4: wo_id → endpoint_id → "ep:ep_id" in mappings
#          1.25.0 — select_by_target_val(target_val): selecteer svg-punt via
#                   omgekeerde mapping-lookup op actuele self._floorplan data.
#                   Gebruikt door main_window na navigatie vanuit eindapparaten-overzicht.
# Changes: 1.24.0 — Site-scope volledig geïmplementeerd via export_all_floorplans_docx
#                   PNG per grondplan exporteren bij site-scope
#                   Tijdelijke PNG-bestanden opruimen na export
#          1.23.0 — PNG grondplan + popup na export
#                   Pagina 1 per grondplan: grondplan-SVG als PDF (apart)
#                   Pagina 2+: gekoppelde punten kaartjes in Word
#                   FloorplanExportDialog: .docx extensie ipv .pdf
#          1.21.0 — G-OPEN-8: Exportknop in toolbar
#          1.20.0 — " SVG Prefix" knop in toolbar
#                   Prefix toevoegen zonder naar Settings te gaan
#                   Herlaadt overlays meteen na toevoegen
#          1.19.0 — Poort-koppeling ondersteuning (port: prefix)
#                   _COLOR_PORT (#ff7043) voor poort overlays
#                   set_port_type() in _OverlayItem
#                   _on_trace_clicked: trace via tracing.trace_from_port()
#                   _resolve_outlet_name: poort-naam tonen
#          1.18.0 — Info tab bewerkbaar
#                   QLineEdit voor naam, QTextEdit voor notities, Opslaan knop
#                   Read-only modus: velden + knop uitgeschakeld
#          1.17.0 — Detail popup: "Bewerken" knop
#          1.16.0 — Checkbox "Toon ongekoppelde punten"
#                   Standaard UIT: ongekoppelde SVG-punten onzichtbaar
#                   Aan: oranje overlays zichtbaar voor koppelen
#          1.15.0 — Fix: endpoint lookup in _on_detail_clicked via outlet["endpoint_id"]
#                   i.p.v. via connections (verkeerde aanpak).
#          1.14.0 — Detail popup: "ℹ Detail tonen" knop in mapping tab
#                   Wandpunt → _OutletDetailDialog uit wall_outlet_view
#                   Eindapparaat → _EndpointDetailDialog uit wall_outlet_view
#                   FloorplanMappingDialog v1.2.0: endpoint tab toegevoegd
#          1.13.0 — Direct endpoint: overlay blauw (#2196f3) voor ep: mappings
#                   _resolve_outlet_name uitgebreid voor endpoints
#                   set_selected_svg_point: ep: prefix herkend
#                   _on_trace_clicked: trace via port voor direct endpoint
#          1.12.0 — G-OPEN-2: Info tab in zijpaneel — naam + notities van het grondplan
#                   _tab_info met _lbl_info_name en _txt_info_notes (readonly)
#                   _refresh_info() aangeroepen vanuit _refresh_sidepanel() en _refresh_from_storage()
#          1.11.0 — G-OPEN-3: rechtsklik op overlay → contextmenu "Koppeling verwijderen"
#                    Alleen zichtbaar bij gekoppeld punt + niet in read-only modus
#          1.10.0 — SVG foreignObject bug opgelost
#                    Draw.io exporteert M-labels als <foreignObject> zonder x/y.
#                    Qt rendert foreignObject als tekst op (0,0) linksboven.
#                    Fix: _load_svg laadt gecleande SVG via temp-bestand
#                    (foreignObjects gestript via floorplan_svg_service.get_cleaned_svg_text)
#          1.9.0 — Vals label fix: overlay alleen aanmaken als positie bekend
#                   Naam + notities tonen in titelbalk
#                   _refresh_from_storage: geen nieuwe overlays voor onbekende punten
#          1.8.0 — Witte achtergrond, overlay alpha, verouderde mappings validatie
#                   _OverlayItem: klikbare cirkel op SVG coördinaten
#                   showEvent: fit-to-screen betrouwbaar bij eerste toon
#                   _refresh_sidepanel bug: "Geen grondplan" tekst vervangen
#                   dubbel venster fix in floorplan_test_window
#          1.4.0 — gesynchroniseerd met nieuwste i18n keys
#                   floorplan_action_fit en floorplan_validation_ok gebruikt
#                   resterende hardcoded UI teksten opgeschoond
#                   contextmenu en validatie volledig op t() afgestemd
#          1.3.0 — resterende UI teksten opgeschoond voor i18n
#                   geen hardcoded 'Fit', 'OK' of fouttitel meer
#                   100% knop als neutrale zoom-reset behouden
#                   status/validatie teksten verder gelijkgetrokken
#          1.2.0 — echte SVG puntdetectie via floorplan_svg_service toegevoegd
#                   vervangt tijdelijke demo-punten waar mogelijk
#                   fallback naar mappings + M1..M8 blijft behouden
#                   validatie werkt nu op gedetecteerde SVG labels
#          1.1.0 — koppeling met FloorplanMappingDialog toegevoegd
#                   mapping direct opslaan/verversen vanuit viewer
#                   read-only respecteren voor map/unmap acties
#                   statuspanelen verfijnd
#          1.0.0 — Initiële versie
#                   SVG basisviewer via QGraphicsView/QGraphicsScene
#                   zoom met muiswiel
#                   basis pan met drag
#                   rechter zijpaneel met tabs
#                   tracing placeholder via bestaande tracing service
#                   i18n via t()
#
# BELANGRIJK:
# Deze view is volledig losstaand en wijzigt GEEN bestaande applicatielogica.
# Ze kan later veilig vanuit MainWindow geopend worden.
# =============================================================================

import os
import tempfile

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QAction, QPainter, QBrush, QColor, QPen, QFont
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QGraphicsEllipseItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.helpers import settings_storage
from app.helpers.i18n import t
from app.services import floorplan_service
from app.services import floorplan_svg_service
from app.services import tracing
from app.gui.dialogs.floorplan_mapping_dialog import FloorplanMappingDialog


_OVERLAY_R        = 7
_COLOR_MAPPED     = QColor("#4caf7d")   # groen — wandpunt
_COLOR_UNMAPPED   = QColor("#f0a030")   # amber — ongekoppeld
_COLOR_SELECTED   = QColor("#e040fb")   # paars — geselecteerd
_COLOR_ENDPOINT   = QColor("#2196f3")   # blauw — direct endpoint
_COLOR_PORT       = QColor("#ff7043")   # oranje-rood — poort koppeling
_PEN_WIDTH        = 2.5


class _OverlayItem(QGraphicsEllipseItem):
    """
    Klikbare overlay op SVG coördinaat voor een wandpuntlabel.

    Ontwerp:
    - Transparante fill, gekleurde rand — SVG tekst blijft leesbaar
    - Label rechtsonder de cirkel op donkere achtergrond
    - Geen hover-scale (voorkomt verschuiving andere cirkels)
    - Cursor verandert naar hand bij hover
    """

    def __init__(self, label: str, x: float, y: float, callback, unmap_callback=None, parent=None):
        r = _OVERLAY_R
        super().__init__(x - r, y - r, r * 2, r * 2, parent)
        self._label          = label
        self._callback       = callback
        self._unmap_callback = unmap_callback  # G-OPEN-3: rechtsklik verwijderen
        self._mapped         = False
        self._selected       = False

        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setZValue(10)
        self.setToolTip(label)

        # Label ONDER de cirkel — verborgen, tooltip volstaat
        self._txt = QGraphicsSimpleTextItem(label, self)
        font = QFont()
        font.setPointSize(6)
        font.setBold(True)
        self._txt.setFont(font)
        self._txt.setZValue(12)
        self._txt.setVisible(False)   # 1.16.0 — label niet tonen, tooltip volstaat

        self._update_style()

    def set_mapped(self, mapped: bool):
        self._mapped = mapped
        self._update_style()

    def set_endpoint_type(self, is_endpoint: bool):
        """1.13.0 — Markeer overlay als direct endpoint (blauw)."""
        self._is_endpoint = is_endpoint
        self._update_style()

    def set_port_type(self, is_port: bool):
        """1.19.0 — Markeer overlay als poort-koppeling (oranje-rood)."""
        self._is_port = is_port
        self._update_style()

    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()

    def _update_style(self):
        is_ep   = getattr(self, "_is_endpoint", False)
        is_port = getattr(self, "_is_port", False)
        color = _COLOR_SELECTED if self._selected else (
            _COLOR_PORT     if (self._mapped and is_port) else (
            _COLOR_ENDPOINT if (self._mapped and is_ep) else (
                _COLOR_MAPPED if self._mapped else _COLOR_UNMAPPED
            ))
        )
        fill = QColor(color)
        fill.setAlpha(160)
        self.setBrush(QBrush(fill))
        self.setPen(QPen(color, _PEN_WIDTH))
        self._txt.setBrush(QBrush(color.lighter(150)))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._callback(self._label)
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            # G-OPEN-3: contextmenu alleen voor gekoppelde punten
            if self._mapped and self._unmap_callback:
                self._unmap_callback(self._label)
            event.accept()
        else:
            super().mousePressEvent(event)

    def hoverEnterEvent(self, event):
        # Geen schaalverandering — alleen pen dikker
        pen = self.pen()
        pen.setWidthF(_PEN_WIDTH * 2)
        self.setPen(pen)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        pen = self.pen()
        pen.setWidthF(_PEN_WIDTH)
        self.setPen(pen)
        super().hoverLeaveEvent(event)


class _FloorplanGraphicsView(QGraphicsView):
    """
    Interne graphics view voor SVG weergave.
    Basisfunctionaliteit:
    - zoom via muiswiel
    - pan via hand drag
    """

    point_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        # Witte achtergrond — SVG tekeningen zijn ontworpen op witte achtergrond
        self.setBackgroundBrush(QBrush(QColor("#ffffff")))

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.scale(1.15, 1.15)
        else:
            self.scale(1 / 1.15, 1 / 1.15)

    def mouseDoubleClickEvent(self, event):
        """
        Placeholder voor latere echte SVG-elementselectie.
        Voor nu resetten we de view op dubbelklik.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.resetTransform()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class FloorplanView(QWidget):
    """
    Basis groundplan viewer.

    Verwacht:
        floorplan: dict uit floorplan_service
        data: volledige network_data structuur
    """

    request_map_point = Signal(str, str)   # floorplan_id, svg_point
    trace_requested = Signal(str)          # outlet_id

    def __init__(self, floorplan: dict, data: dict, parent=None):
        super().__init__(parent)

        self._floorplan = floorplan
        self._data = data or {}

        self._selected_svg_point: str | None = None
        self._selected_outlet_id: str | None = None
        self._detected_svg_points: list[str] = []
        self._overlay_items: dict[str, _OverlayItem] = {}
        self._fit_done = False

        self._scene = QGraphicsScene(self)
        self._svg_item: QGraphicsSvgItem | None = None

        self._build_ui()
        self._load_svg()
        self._refresh_from_storage()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # --------------------------------------------------------------
        # Linkerzijde: viewer
        # --------------------------------------------------------------
        viewer_wrap = QWidget()
        viewer_layout = QVBoxLayout(viewer_wrap)
        viewer_layout.setContentsMargins(12, 12, 6, 12)
        viewer_layout.setSpacing(6)

        # Titel: naam + locatie indien beschikbaar
        name = self._floorplan.get("name", "") or ""
        loc  = self._floorplan.get("outlet_location_key", "") or ""
        title_txt = name if name else (loc if loc else t("title_floorplan_view"))
        self._title_label = QLabel(title_txt)
        self._title_label.setObjectName("secondary")
        viewer_layout.addWidget(self._title_label)

        self._graphics_view = _FloorplanGraphicsView(self)
        self._graphics_view.setScene(self._scene)
        viewer_layout.addWidget(self._graphics_view, 1)

        viewer_btn_row = QHBoxLayout()
        viewer_btn_row.setContentsMargins(0, 0, 0, 0)
        viewer_btn_row.setSpacing(6)

        self._btn_reset_zoom = QPushButton("100%")
        self._btn_reset_zoom.clicked.connect(self._on_reset_zoom)

        self._btn_fit = QPushButton(t("floorplan_action_fit"))
        self._btn_fit.clicked.connect(self._on_fit)

        # 1.16.0 — Toggle ongekoppelde SVG-punten (standaard verborgen)
        self._chk_show_unmapped = QCheckBox("Toon ongekoppelde punten")
        self._chk_show_unmapped.setChecked(False)
        self._chk_show_unmapped.setToolTip(
            "Oranje punten tonen voor SVG-locaties die nog niet aan een wandpunt gekoppeld zijn"
        )
        self._chk_show_unmapped.toggled.connect(self._on_toggle_unmapped)

        viewer_btn_row.addWidget(self._btn_reset_zoom)
        viewer_btn_row.addWidget(self._btn_fit)
        viewer_btn_row.addSpacing(12)
        viewer_btn_row.addWidget(self._chk_show_unmapped)
        viewer_btn_row.addSpacing(12)

        # 1.20.0 — Snel prefix toevoegen zonder naar Settings te gaan
        self._btn_add_prefix = QPushButton("+ SVG Prefix")
        self._btn_add_prefix.setToolTip(
            "Voeg een nieuw SVG-label prefix toe (bv. SW, CAM) zodat die punten "
            "herkend worden op het grondplan"
        )
        self._btn_add_prefix.clicked.connect(self._on_add_prefix)
        viewer_btn_row.addWidget(self._btn_add_prefix)

        # 1.21.0 — Exportknop grondplan PNG/PDF (G-OPEN-8)
        self._btn_export = QPushButton("⬇  " + t("fp_export_btn_export"))
        self._btn_export.setToolTip(t("fp_export_btn_tip"))
        self._btn_export.clicked.connect(self._on_export_clicked)
        viewer_btn_row.addWidget(self._btn_export)

        viewer_btn_row.addStretch(1)

        viewer_layout.addLayout(viewer_btn_row)

        # --------------------------------------------------------------
        # Rechterzijde: tabs
        # --------------------------------------------------------------
        side_wrap = QWidget()
        side_layout = QVBoxLayout(side_wrap)
        side_layout.setContentsMargins(6, 12, 12, 12)
        side_layout.setSpacing(6)

        self._tabs = QTabWidget()

        # Tab 1: selectie
        self._tab_selection = QWidget()
        sel_layout = QVBoxLayout(self._tab_selection)
        sel_layout.setContentsMargins(8, 8, 8, 8)
        sel_layout.setSpacing(8)

        self._lbl_selected_point = QLabel("-")
        self._lbl_selected_outlet = QLabel("-")

        sel_layout.addWidget(QLabel(f"{t('floorplan_mapping_svg_point')}:"))
        sel_layout.addWidget(self._lbl_selected_point)
        sel_layout.addSpacing(8)
        sel_layout.addWidget(QLabel(f"{t('floorplan_mapping_outlet')}:"))
        sel_layout.addWidget(self._lbl_selected_outlet)
        sel_layout.addStretch(1)

        # Tab 2: koppelingen
        self._tab_mapping = QWidget()
        map_layout = QVBoxLayout(self._tab_mapping)
        map_layout.setContentsMargins(8, 8, 8, 8)
        map_layout.setSpacing(8)

        self._mapping_info = QTextEdit()
        self._mapping_info.setReadOnly(True)
        self._mapping_info.setMinimumHeight(120)

        self._btn_map = QPushButton(t("floorplan_mapping_assign"))
        self._btn_map.clicked.connect(self._on_map_clicked)

        self._btn_unmap = QPushButton(t("floorplan_mapping_remove"))
        self._btn_unmap.clicked.connect(self._on_unmap_clicked)

        # 1.14.0 — Detail popup voor gekoppeld object (wandpunt of endpoint)
        self._btn_detail = QPushButton("ℹ  " + t("label_detail"))
        self._btn_detail.clicked.connect(self._on_detail_clicked)
        self._btn_detail.setEnabled(False)

        map_layout.addWidget(self._mapping_info)
        map_layout.addWidget(self._btn_map)
        map_layout.addWidget(self._btn_unmap)
        map_layout.addWidget(self._btn_detail)
        map_layout.addStretch(1)

        # Tab 3: trace
        self._tab_trace = QWidget()
        trace_layout = QVBoxLayout(self._tab_trace)
        trace_layout.setContentsMargins(8, 8, 8, 8)
        trace_layout.setSpacing(8)

        self._trace_info = QTextEdit()
        self._trace_info.setReadOnly(True)

        self._btn_trace = QPushButton(t("label_trace"))
        self._btn_trace.clicked.connect(self._on_trace_clicked)

        trace_layout.addWidget(self._trace_info)
        trace_layout.addWidget(self._btn_trace)

        # Tab 4: validatie
        self._tab_validation = QWidget()
        val_layout = QVBoxLayout(self._tab_validation)
        val_layout.setContentsMargins(8, 8, 8, 8)
        val_layout.setSpacing(8)

        self._validation_list = QListWidget()
        val_layout.addWidget(self._validation_list)

        # Tab 5: info (G-OPEN-2)
        self._tab_info = QWidget()
        info_layout = QVBoxLayout(self._tab_info)
        info_layout.setContentsMargins(8, 8, 8, 8)
        info_layout.setSpacing(8)

        form_info = QFormLayout()
        form_info.setSpacing(6)

        # 1.18.0 — Naam bewerkbaar
        from PySide6.QtWidgets import QLineEdit
        self._edit_info_name = QLineEdit()
        self._edit_info_name.setPlaceholderText("(optioneel)")

        self._txt_info_notes = QTextEdit()
        self._txt_info_notes.setMinimumHeight(80)
        self._txt_info_notes.setPlaceholderText("(optioneel)")

        form_info.addRow(f"{t('label_name')}:", self._edit_info_name)
        form_info.addRow(f"{t('label_notes')}:", self._txt_info_notes)
        info_layout.addLayout(form_info)

        # Opslaan knop
        info_btn_row = QHBoxLayout()
        info_btn_row.addStretch()
        self._btn_info_save = QPushButton(t("btn_save"))
        self._btn_info_save.clicked.connect(self._on_info_save)
        info_btn_row.addWidget(self._btn_info_save)
        info_layout.addLayout(info_btn_row)
        info_layout.addStretch()

        self._tabs.addTab(self._tab_selection,  t("floorplan_tab_selection"))
        self._tabs.addTab(self._tab_mapping,    t("floorplan_tab_mapping"))
        self._tabs.addTab(self._tab_trace,      t("floorplan_tab_trace"))
        self._tabs.addTab(self._tab_validation, t("floorplan_tab_validation"))
        self._tabs.addTab(self._tab_info,       t("floorplan_tab_info"))

        side_layout.addWidget(self._tabs, 1)

        splitter.addWidget(viewer_wrap)
        splitter.addWidget(side_wrap)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([900, 320])

        root.addWidget(splitter)

        self._graphics_view.customContextMenuRequested.connect(self._on_view_context_menu)

    # ------------------------------------------------------------------
    # SVG laden
    # ------------------------------------------------------------------

    def _load_svg(self):
        self._scene.clear()
        self._svg_item = None
        self._detected_svg_points = []
        self._overlay_items = {}
        self._fit_done = False
        self._svg_temp_file = None  # bewaar referentie zodat temp-bestand niet te vroeg verwijderd wordt

        svg_path = floorplan_service.get_svg_path(self._floorplan)

        if not svg_path.exists():
            self._scene.addText(t("floorplan_validation_missing_svg"))
            self._refresh_validation()
            return

        # Strip <foreignObject> elementen vóór rendering.
        # Draw.io exporteert M-labels als <foreignObject width="100%" height="100%">
        # zonder x/y positie. Qt rendert deze als tekst op (0,0) linksboven.
        # De <switch> bevat ook een <image> fallback — die wordt correct gebruikt
        # nadat foreignObject verwijderd is.
        cleaned_svg = floorplan_svg_service.get_cleaned_svg_text(svg_path)
        if cleaned_svg:
            tmp = tempfile.NamedTemporaryFile(
                suffix=".svg", delete=False, mode="w", encoding="utf-8"
            )
            tmp.write(cleaned_svg)
            tmp.flush()
            tmp.close()
            self._svg_temp_file = tmp.name
            render_path = tmp.name
        else:
            render_path = str(svg_path)

        self._svg_item = QGraphicsSvgItem(render_path)
        self._scene.addItem(self._svg_item)
        self._scene.setSceneRect(self._svg_item.boundingRect())

        self._detected_svg_points = floorplan_svg_service.detect_point_labels(svg_path)

        # Overlays plaatsen op gedetecteerde posities
        positions = floorplan_svg_service.detect_point_positions(svg_path)
        mappings  = self._floorplan.get("mappings", {})
        show_unmapped = self._chk_show_unmapped.isChecked()
        for label, (x, y) in positions.items():
            overlay = _OverlayItem(
                label=label, x=x, y=y,
                callback=self._on_overlay_clicked,
                unmap_callback=self._on_overlay_unmap,
            )
            mapped_val = mappings.get(label, "")
            overlay.set_mapped(bool(mapped_val))
            overlay.set_endpoint_type(mapped_val.startswith("ep:"))
            overlay.set_port_type(mapped_val.startswith("port:"))
            # 1.16.0 — ongekoppelde punten standaard verborgen
            if not mapped_val:
                overlay.setVisible(show_unmapped)
            self._scene.addItem(overlay)
            self._overlay_items[label] = overlay

        self._refresh_validation()

    def showEvent(self, event):
        """Fit SVG to screen bij eerste toon — betrouwbaarder dan in _load_svg."""
        super().showEvent(event)
        if not self._fit_done and self._svg_item is not None:
            self._on_fit()
            self._fit_done = True

    def closeEvent(self, event):
        """Ruim temp-bestand op bij sluiten van de view."""
        super().closeEvent(event)
        self._cleanup_temp_svg()

    def _cleanup_temp_svg(self):
        """Verwijder het tijdelijk gecleande SVG bestand indien aanwezig."""
        tmp = getattr(self, "_svg_temp_file", None)
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            self._svg_temp_file = None

    def _on_overlay_clicked(self, label: str):
        """Overlay aangeklikt — selecteer punt en switch naar mapping tab."""
        self.set_selected_svg_point(label)
        self._tabs.setCurrentWidget(self._tab_mapping)

    def _on_overlay_unmap(self, label: str):
        """
        G-OPEN-3: rechtsklik op gekoppelde overlay → koppeling direct verwijderen.
        Alleen actief als niet in read-only modus.
        """
        if settings_storage.get_read_only_mode():
            return
        floorplan_service.remove_mapping(self._floorplan["id"], label)
        if self._selected_svg_point == label:
            self._selected_outlet_id = None
        self._refresh_from_storage()
        if self._selected_svg_point == label:
            self._refresh_sidepanel()

    # ------------------------------------------------------------------
    # Publieke API
    # ------------------------------------------------------------------

    def set_selected_svg_point(self, svg_point: str | None):
        # Deselecteer vorige overlay
        if self._selected_svg_point and self._selected_svg_point in self._overlay_items:
            self._overlay_items[self._selected_svg_point].set_selected(False)

        self._selected_svg_point = svg_point
        self._selected_outlet_id = None

        if svg_point:
            mapped_val = floorplan_service.get_mapping(
                self._floorplan["id"], svg_point,
            )
            # Bewaar de volledige mapping waarde — ep:, port: of wandpunt ID
            self._selected_outlet_id = mapped_val or None
            if svg_point in self._overlay_items:
                self._overlay_items[svg_point].set_selected(True)

        self._refresh_sidepanel()

    def select_by_target_val(self, target_val: str) -> bool:
        """
        1.27.0 — Selecteer het svg-punt dat gekoppeld is aan target_val.
        target_val: outlet_id OF "ep:ep_id".

        Zoekstrategie (in volgorde):
        1. Directe match op target_val in mappings
        2. "ep:ep_id" → wandpunt met dat endpoint_id → outlet_id in mappings
        3. wo_id → volledige poort-keten:
           3a. wo → PP back-poort → directe mapping (port:back_id)
           3b. PP back → PP front via zelfde device+number, andere side → mapping
           3c. PP front → switch-poort via connection → mapping (port:switch_id)
        4. wo_id → endpoint_id → "ep:ep_id" in mappings
        """
        if not target_val:
            return False
        mappings = self._floorplan.get("mappings", {})

        # Stap 1: directe match
        svg_point = next((k for k, v in mappings.items() if v == target_val), None)

        # Stap 2: "ep:ep_id" → zoek via gekoppeld wandpunt outlet_id
        if not svg_point and target_val.startswith("ep:"):
            ep_id = target_val[3:]
            for site in self._data.get("sites", []):
                for room in site.get("rooms", []):
                    for wo in room.get("wall_outlets", []):
                        if wo.get("endpoint_id") == ep_id:
                            outlet_id = wo.get("id", "")
                            svg_point = next(
                                (k for k, v in mappings.items() if v == outlet_id),
                                None,
                            )
                            break
                    if svg_point:
                        break
                if svg_point:
                    break

        # Stap 3: wo_id → volledige poort-keten → mapping
        if not svg_point and target_val and not target_val.startswith(("ep:", "port:")):
            port_id = None
            for conn in self._data.get("connections", []):
                ft = conn.get("from_type", "")
                fid = conn.get("from_id", "")
                tt = conn.get("to_type", "")
                tid = conn.get("to_id", "")
                if ft == "wall_outlet" and fid == target_val and tt == "port":
                    port_id = tid
                    break
                if tt == "wall_outlet" and tid == target_val and ft == "port":
                    port_id = fid
                    break

            if port_id:
                # 3a — directe mapping op de gevonden poort
                port_key = f"port:{port_id}"
                svg_point = next(
                    (k for k, v in mappings.items() if v == port_key), None
                )

                # 3b — PP back → PP front via zelfde device+number, andere side
                if not svg_point:
                    port_map     = {p["id"]: p for p in self._data.get("ports", [])}
                    back_port    = port_map.get(port_id, {})
                    dev_id       = back_port.get("device_id", "")
                    number       = back_port.get("number")
                    side         = back_port.get("side", "")
                    partner_side = "front" if side == "back" else "back"
                    partner_port_id = next(
                        (p["id"] for p in self._data.get("ports", [])
                         if p.get("device_id") == dev_id
                         and p.get("number") == number
                         and p.get("side") == partner_side),
                        None,
                    )
                    if partner_port_id:
                        partner_key = f"port:{partner_port_id}"
                        svg_point = next(
                            (k for k, v in mappings.items() if v == partner_key), None
                        )

                        # 3c — PP front → switch-poort via connection
                        if not svg_point:
                            switch_port_id = None
                            for conn in self._data.get("connections", []):
                                ft = conn.get("from_type", "")
                                fid = conn.get("from_id", "")
                                tt = conn.get("to_type", "")
                                tid = conn.get("to_id", "")
                                if ft == "port" and fid == partner_port_id and tt == "port":
                                    switch_port_id = tid
                                    break
                                if tt == "port" and tid == partner_port_id and ft == "port":
                                    switch_port_id = fid
                                    break
                            if switch_port_id:
                                switch_key = f"port:{switch_port_id}"
                                svg_point = next(
                                    (k for k, v in mappings.items() if v == switch_key),
                                    None,
                                )

        # Stap 4: wo_id → endpoint_id → "ep:ep_id" in mappings
        if not svg_point and target_val and not target_val.startswith(("ep:", "port:")):
            for site in self._data.get("sites", []):
                for room in site.get("rooms", []):
                    for wo in room.get("wall_outlets", []):
                        if wo.get("id") == target_val:
                            ep_id = wo.get("endpoint_id", "")
                            if ep_id:
                                ep_key = f"ep:{ep_id}"
                                svg_point = next(
                                    (k for k, v in mappings.items() if v == ep_key),
                                    None,
                                )
                            break
                    if svg_point:
                        break
                if svg_point:
                    break

        if svg_point:
            self.set_selected_svg_point(svg_point)
            return True
        return False

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _on_toggle_unmapped(self, checked: bool):
        """1.16.0 — Toon/verberg ongekoppelde SVG-punten (oranje overlays)."""
        for overlay in self._overlay_items.values():
            if not overlay._mapped:
                overlay.setVisible(checked)

    def _on_add_prefix(self):
        """
        1.20.0 — Voeg snel een nieuw SVG-label prefix toe vanuit de grondplan view.
        Toont een invoerdialoog, slaat op via settings_storage en herlaadt de overlays.
        """
        from PySide6.QtWidgets import QInputDialog
        from app.helpers.settings_storage import (
            load_outlet_label_prefixes,
            save_outlet_label_prefixes,
        )

        prefix, ok = QInputDialog.getText(
            self,
            "SVG Prefix toevoegen",
            "Prefix (bv. M, WAP, D, SW, CAM):",
        )
        if not ok or not prefix.strip():
            return

        prefix = prefix.strip().upper()
        prefixes = load_outlet_label_prefixes()
        if prefix in prefixes:
            QMessageBox.information(
                self,
                "SVG Prefix",
                f'Prefix "{prefix}" bestaat al.'
            )
            return

        prefixes.append(prefix)
        save_outlet_label_prefixes(prefixes)

        # Herlaad overlays zodat nieuw prefix meteen herkend wordt
        self._load_svg()

    def _on_export_clicked(self):
        """
        1.22.0 — G-OPEN-8: exporteer grondplan.
        Pagina 1 (grondplan SVG): PDF via export_renderer.render_floorplan_image()
        Pagina 2+ (gekoppelde punten): Word-document via floorplan_docx_renderer
        """
        from app.gui.dialogs.floorplan_export_dialog import FloorplanExportDialog
        from app.services import export_renderer, floorplan_docx_renderer

        site_id = self._floorplan.get("site_id", "")
        site    = next(
            (s for s in self._data.get("sites", []) if s["id"] == site_id),
            {"id": site_id, "name": ""},
        )

        dlg = FloorplanExportDialog(
            floorplan=self._floorplan,
            site=site,
            parent=self,
        )
        if not dlg.exec():
            return

        if not dlg.filepath:
            return

        filepath = dlg.filepath  # .docx pad
        import os as _os

        if dlg.scope == "site":
            # ── Alle grondplannen van de site exporteren ───────────────
            from app.services import floorplan_service as _fps
            floorplans = _fps.get_floorplans_for_site(site_id)

            # PNG per grondplan exporteren
            png_paths = {}
            for fp in floorplans:
                fp_id   = fp.get("id", "")
                png_tmp = filepath.replace(".docx", f"_{fp_id}.png")
                ok_png, _ = export_renderer.render_floorplan_image(
                    floorplan=fp, site=site, data=self._data, filepath=png_tmp,
                )
                if ok_png and _os.path.exists(png_tmp):
                    png_paths[fp_id] = png_tmp

            ok, err = floorplan_docx_renderer.export_all_floorplans_docx(
                floorplans=floorplans,
                site=site,
                data=self._data,
                filepath=filepath,
                png_paths=png_paths,
            )

            # Tijdelijke PNG's opruimen
            for png_tmp in png_paths.values():
                try: _os.unlink(png_tmp)
                except OSError: pass

        else:
            # ── Huidig grondplan exporteren ───────────────────────────
            png_tmp = filepath.replace(".docx", "_grondplan.png")
            ok_png, _ = export_renderer.render_floorplan_image(
                floorplan=self._floorplan,
                site=site,
                data=self._data,
                filepath=png_tmp,
            )
            png_path = png_tmp if ok_png and _os.path.exists(png_tmp) else None

            ok, err = floorplan_docx_renderer.export_floorplan_docx(
                floorplan=self._floorplan,
                site=site,
                data=self._data,
                filepath=filepath,
                png_path=png_path,
            )

            # Tijdelijke PNG opruimen
            if png_path:
                try: _os.unlink(png_path)
                except OSError: pass

        if not ok:
            QMessageBox.warning(self, t("title_floorplan_view"),
                                f"{t('msg_export_failed')}\n{err}")
            return

        # ── Popup: document openen? ───────────────────────────────────
        reply = QMessageBox.question(
            self,
            t("title_floorplan_view"),
            f"{t('msg_pdf_exported')}\n{filepath}\n\nDocument nu openen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            import subprocess, sys
            try:
                if sys.platform == "win32":
                    _os.startfile(filepath)
                elif sys.platform == "darwin":
                    subprocess.run(["open", filepath])
                else:
                    subprocess.run(["xdg-open", filepath])
            except Exception:
                pass

    def _on_reset_zoom(self):
        self._graphics_view.resetTransform()

    def _on_fit(self):
        if self._svg_item is None:
            return
        self._graphics_view.fitInView(
            self._svg_item.boundingRect(),
            Qt.AspectRatioMode.KeepAspectRatio
        )

    def _on_map_clicked(self):
        """
        Open de mapping dialoog voor het geselecteerde SVG punt.
        """
        if settings_storage.get_read_only_mode():
            return

        if not self._selected_svg_point:
            QMessageBox.warning(self, t("title_floorplan_view"), t("err_no_selection"))
            return

        dlg = FloorplanMappingDialog(
            parent=self,
            data=self._data,
            floorplan=self._floorplan,
            svg_point=self._selected_svg_point,
        )

        if dlg.exec():
            result = dlg.get_result()
            if result:
                self._refresh_from_storage()
                self.set_selected_svg_point(self._selected_svg_point)
                self.request_map_point.emit(
                    self._floorplan["id"],
                    self._selected_svg_point,
                )

    def _on_unmap_clicked(self):
        if settings_storage.get_read_only_mode():
            return

        if not self._selected_svg_point:
            QMessageBox.warning(self, t("title_floorplan_view"), t("err_no_selection"))
            return

        floorplan_service.remove_mapping(
            self._floorplan["id"],
            self._selected_svg_point,
        )
        self._selected_outlet_id = None
        self._refresh_from_storage()
        self._refresh_sidepanel()

    def _on_detail_clicked(self):
        """
        1.14.0 — Toon detail popup voor het gekoppelde object:
        - Wandpunt    → _OutletDetailDialog
        - Eindapparaat → _EndpointDetailDialog
        - Poort (port:) → DeviceInfoDialog voor het device van de poort
        """
        if not self._selected_outlet_id:
            return

        from app.gui.wall_outlet_view import _OutletDetailDialog, _EndpointDetailDialog

        sel = self._selected_outlet_id

        # ── Poort-koppeling (port: prefix) ────────────────────────────
        if sel.startswith("port:"):
            port_id = sel[5:]
            port = next((p for p in self._data.get("ports", [])
                         if p["id"] == port_id), None)
            if not port:
                return
            dev = next((d for d in self._data.get("devices", [])
                        if d["id"] == port.get("device_id", "")), None)
            if not dev:
                return
            # Zoek rack/room/site/slot voor dit device
            rack = room = site = slot_found = None
            for s in self._data.get("sites", []):
                for r in s.get("rooms", []):
                    for ra in r.get("racks", []):
                        for sl in ra.get("slots", []):
                            if sl.get("device_id") == dev["id"]:
                                rack, room, site, slot_found = ra, r, s, sl
            from app.gui.dialogs.device_info_dialog import DeviceInfoDialog
            dlg = DeviceInfoDialog(
                parent=self, device=dev, data=self._data,
                rack=rack or {}, room=room or {}, site=site or {},
                slot=slot_found or {}
            )
            dlg.exec()
            return

        # ── Eindapparaat (ep: prefix) ──────────────────────────────────
        if sel.startswith("ep:"):
            ep_id = sel[3:]
            ep = next((e for e in self._data.get("endpoints", [])
                       if e["id"] == ep_id), None)
            if not ep:
                return
            conn = next(
                (c for c in self._data.get("connections", [])
                 if (c.get("to_type") == "endpoint" and c["to_id"] == ep_id) or
                    (c.get("from_type") == "endpoint" and c["from_id"] == ep_id)),
                None
            )
            port = None
            dev  = None
            if conn:
                port_id = (conn["from_id"] if conn.get("to_type") == "endpoint"
                           else conn["to_id"])
                port = next((p for p in self._data.get("ports", [])
                             if p["id"] == port_id), None)
                if port:
                    dev = next((d for d in self._data.get("devices", [])
                                if d["id"] == port.get("device_id", "")), None)
            dlg = _EndpointDetailDialog(
                ep=ep, port=port, dev=dev, data=self._data, parent=self
            )
            dlg.exec()
            return

        # ── Wandpunt ──────────────────────────────────────────────────
        outlet_id = sel
        outlet = next(
            (wo for s in self._data.get("sites", [])
             for r in s.get("rooms", [])
             for wo in r.get("wall_outlets", [])
             if wo["id"] == outlet_id),
            None
        )
        if not outlet:
            return
        ep_id    = outlet.get("endpoint_id", "")
        endpoint = next(
            (e for e in self._data.get("endpoints", [])
             if e["id"] == ep_id), None
        ) if ep_id else None

        def _do_edit():
            room_id = next(
                (r["id"] for s in self._data.get("sites", [])
                 for r in s.get("rooms", [])
                 if any(wo["id"] == outlet_id
                        for wo in r.get("wall_outlets", []))),
                ""
            )
            mw = self.window()
            if hasattr(mw, "_edit_wall_outlet"):
                mw._edit_wall_outlet({"id": outlet_id, "room_id": room_id})

        dlg = _OutletDetailDialog(
            outlet=outlet, endpoint=endpoint, data=self._data,
            parent=self, on_edit_clicked=_do_edit,
        )
        dlg.exec()

    def _on_trace_clicked(self):
        if not self._selected_outlet_id:
            self._trace_info.setPlainText(t("trace_no_connection"))
            return

        sel = self._selected_outlet_id

        if sel.startswith("port:"):
            # 1.19.0 — Poort-koppeling: trace direct via poort ID
            port_id = sel[5:]
            steps = tracing.trace_from_port(self._data, port_id)
        elif sel.startswith("ep:"):
            # Direct endpoint: trace via de verbonden poort
            ep_id = sel[3:]
            conn = next(
                (c for c in self._data.get("connections", [])
                 if (c.get("to_type") == "endpoint" and c["to_id"] == ep_id) or
                    (c.get("from_type") == "endpoint" and c["from_id"] == ep_id)),
                None
            )
            if conn:
                port_id = conn["from_id"] if conn.get("to_type") == "endpoint" else conn["to_id"]
                steps = tracing.trace_from_port(self._data, port_id)
            else:
                steps = []
        else:
            steps = tracing.trace_from_wall_outlet(self._data, sel)

        if not steps:
            self._trace_info.setPlainText(t("trace_no_connection"))
            return

        lines = []
        for step in steps:
            label      = step.get("label", "?")
            obj_type   = step.get("obj_type", "")
            cable_type = step.get("cable_type", "")
            if cable_type:
                lines.append(f"[{obj_type}] {label}  ({cable_type})")
            else:
                lines.append(f"[{obj_type}] {label}")

        self._trace_info.setPlainText("\n".join(lines))
        # trace_requested enkel voor wandpunten (niet ep: of port:)
        if not sel.startswith("ep:") and not sel.startswith("port:"):
            self.trace_requested.emit(sel)

    def _on_view_context_menu(self, pos):
        menu = QMenu(self)

        act_fit = QAction(t("floorplan_action_fit"), self)
        act_fit.triggered.connect(self._on_fit)
        menu.addAction(act_fit)

        act_reset = QAction("100%", self)
        act_reset.triggered.connect(self._on_reset_zoom)
        menu.addAction(act_reset)

        menu.addSeparator()

        svg_points = self._get_available_svg_points()
        if svg_points:
            for point in svg_points[:20]:
                act = QAction(point, self)
                act.triggered.connect(
                    lambda checked=False, p=point: self.set_selected_svg_point(p)
                )
                menu.addAction(act)

        menu.exec(self._graphics_view.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh_from_storage(self):
        """
        Laad de meest recente floorplan-data opnieuw in vanuit storage.
        Zo blijven mappings synchroon na dialoog-acties.
        Overlay kleuren bijwerken — geen nieuwe overlays aanmaken voor
        verouderde mappings zonder bekende SVG-positie (vals label fix).
        """
        latest = floorplan_service.get_floorplan(self._floorplan.get("id", ""))
        if latest:
            self._floorplan = latest

        # Overlay kleuren bijwerken — ALLEEN voor bekende posities
        mappings = self._floorplan.get("mappings", {})
        show_unmapped = self._chk_show_unmapped.isChecked()
        for label, overlay in self._overlay_items.items():
            mapped_val = mappings.get(label, "")
            overlay.set_mapped(bool(mapped_val))
            overlay.set_endpoint_type(mapped_val.startswith("ep:"))
            overlay.set_port_type(mapped_val.startswith("port:"))
            overlay.set_selected(label == self._selected_svg_point)
            # 1.16.0 — zichtbaarheid bijhouden na koppelen/ontkoppelen
            if not mapped_val:
                overlay.setVisible(show_unmapped)
            else:
                overlay.setVisible(True)

        # Naam bijwerken indien aanwezig
        name = self._floorplan.get("name", "") or ""
        loc  = self._floorplan.get("outlet_location_key", "") or ""
        title_txt = name if name else (loc if loc else t("title_floorplan_view"))
        self._title_label.setText(title_txt)

        self._refresh_validation()
        self._refresh_sidepanel()
        self._apply_read_only_mode()

    def _refresh_sidepanel(self):
        point_txt  = self._selected_svg_point or "-"
        outlet_txt = self._resolve_outlet_name(self._selected_outlet_id) or "-"

        self._lbl_selected_point.setText(point_txt)
        self._lbl_selected_outlet.setText(outlet_txt)

        if self._selected_svg_point:
            mapping_lines = [
                f"{t('floorplan_mapping_svg_point')}: {self._selected_svg_point}",
                f"{t('floorplan_mapping_outlet')}: {outlet_txt}",
            ]
        else:
            # Fix: geen "Geen grondplan gevonden" maar lege prompt
            mapping_lines = [t("floorplan_mapping_svg_point") + ": -"]

        self._mapping_info.setPlainText("\n".join(mapping_lines))

        if self._selected_outlet_id:
            self._trace_info.setPlainText(f"{t('label_wall_outlet')}: {outlet_txt}")
            self._btn_detail.setEnabled(True)
        else:
            self._trace_info.setPlainText(t("trace_no_connection"))
            self._btn_detail.setEnabled(False)

        self._refresh_info()

    def _refresh_info(self):
        """G-OPEN-2 — Naam en notities van het huidige grondplan tonen in de Info tab."""
        if not self._floorplan:
            self._edit_info_name.setText("")
            self._txt_info_notes.setPlainText("")
            return

        name  = self._floorplan.get("name", "") or ""
        notes = self._floorplan.get("description", "") or ""

        self._edit_info_name.setText(name)
        self._txt_info_notes.setPlainText(notes)

    def _on_info_save(self):
        """1.18.0 — Naam en notities van het grondplan opslaan."""
        if not self._floorplan:
            return
        if settings_storage.get_read_only_mode():
            return
        fp_id = self._floorplan.get("id", "")
        name  = self._edit_info_name.text().strip()
        notes = self._txt_info_notes.toPlainText().strip()
        # update_floorplan_meta slaat naam alleen op als niet leeg
        # description altijd opslaan (ook leeg = wissen)
        from app.services import floorplan_service as _fps
        data = _fps.load_floorplans()
        for fp in data.get("floorplans", []):
            if fp.get("id") == fp_id:
                fp["name"] = name
                fp["description"] = notes
                break
        _fps.save_floorplans(data)
        self._refresh_from_storage()

    def _refresh_validation(self):
        self._validation_list.clear()

        svg_path = floorplan_service.get_svg_path(self._floorplan)
        if not svg_path.exists():
            self._validation_list.addItem(
                QListWidgetItem(t("floorplan_validation_missing_svg"))
            )

        svg_points  = set(self._detected_svg_points)
        mappings    = self._floorplan.get("mappings", {})

        # Verouderde mappings: punten in data maar niet (meer) in SVG
        stale = [p for p in mappings if p not in svg_points]
        if stale:
            item = QListWidgetItem(
                f"⚠ Verouderde koppelingen (niet in SVG): {', '.join(stale)}"
            )
            item.setForeground(QColor("#f0a030"))
            self._validation_list.addItem(item)

        unmapped = [p for p in svg_points if p not in mappings]
        if unmapped:
            self._validation_list.addItem(
                QListWidgetItem(
                    f"{t('floorplan_validation_unmapped')}: {', '.join(unmapped[:10])}"
                )
            )

        reverse: dict[str, list[str]] = {}
        for svg_point, outlet_id in mappings.items():
            reverse.setdefault(outlet_id, []).append(svg_point)

        duplicates = [
            f"{outlet_id}: {', '.join(points)}"
            for outlet_id, points in reverse.items()
            if len(points) > 1
        ]
        if duplicates:
            self._validation_list.addItem(
                QListWidgetItem(
                    f"{t('floorplan_validation_duplicate')}: "
                    + " | ".join(duplicates[:10])
                )
            )

        if self._validation_list.count() == 0:
            self._validation_list.addItem(
                QListWidgetItem(t("floorplan_validation_ok"))
            )

    def _apply_read_only_mode(self):
        read_only = settings_storage.get_read_only_mode()
        self._btn_map.setEnabled(not read_only)
        self._btn_unmap.setEnabled(not read_only)
        # Detail knop is altijd beschikbaar (ook read-only) als er een koppeling is
        # 1.18.0 — Info tab: velden en opslaan knop in read-only uitschakelen
        self._edit_info_name.setReadOnly(read_only)
        self._txt_info_notes.setReadOnly(read_only)
        self._btn_info_save.setEnabled(not read_only)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_outlet_name(self, outlet_id: str | None) -> str | None:
        if not outlet_id:
            return None

        # Poort-koppeling (1.19.0)
        if outlet_id.startswith("port:"):
            port_id = outlet_id[5:]
            port = next((p for p in self._data.get("ports", [])
                         if p.get("id") == port_id), None)
            if port:
                dev = next((d for d in self._data.get("devices", [])
                            if d["id"] == port.get("device_id", "")), None)
                dev_name = dev.get("name", "") if dev else ""
                port_name = port.get("name", port_id)
                side = port.get("side", "")
                side_lbl = f" ({side.upper()})" if side else ""
                return f"🔌  {dev_name} — {port_name}{side_lbl}" if dev_name else f"🔌  {port_name}{side_lbl}"
            return port_id

        # Direct endpoint
        if outlet_id.startswith("ep:"):
            ep_id = outlet_id[3:]
            ep = next((e for e in self._data.get("endpoints", [])
                       if e["id"] == ep_id), None)
            return f"🖥  {ep.get('name', ep_id)}" if ep else ep_id

        # Wandpunt
        for site in self._data.get("sites", []):
            for room in site.get("rooms", []):
                for outlet in room.get("wall_outlets", []):
                    if outlet.get("id") == outlet_id:
                        return outlet.get("name", outlet_id)

        return outlet_id

    def _get_available_svg_points(self) -> list[str]:
        """
        Geef de bruikbare SVG punten terug.
        Combineert gedetecteerde labels met eventueel al opgeslagen mappings.
        """
        points = set(self._detected_svg_points)
        points.update(self._floorplan.get("mappings", {}).keys())
        return sorted(points)