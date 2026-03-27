# =============================================================================
# Networkmap_Creator
# File:    app/gui/floorplan_view.py
# Role:    Grondplan viewer — basis mockup met rechter zijpaneel
# Version: 1.8.0
# Author:  Barremans
# Changes: 1.8.0 — Witte achtergrond voor SVG viewer (ongeacht app thema)
#                   Overlays: voller (alpha 160, rand 2.5px) voor donker thema
#                   Validatie: waarschuwing voor verouderde mappings (niet in SVG)
#          1.7.0 — Fallback M1..M8 verwijderd, kleuren donker thema
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

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QAction, QPainter, QBrush, QColor, QPen, QFont
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtWidgets import (
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


_OVERLAY_R      = 7
_COLOR_MAPPED   = QColor("#4caf7d")   # groen
_COLOR_UNMAPPED = QColor("#f0a030")   # amber
_COLOR_SELECTED = QColor("#e040fb")   # paars
_PEN_WIDTH      = 2.5


class _OverlayItem(QGraphicsEllipseItem):
    """
    Klikbare overlay op SVG coördinaat voor een wandpuntlabel.

    Ontwerp:
    - Transparante fill, gekleurde rand — SVG tekst blijft leesbaar
    - Label rechtsonder de cirkel op donkere achtergrond
    - Geen hover-scale (voorkomt verschuiving andere cirkels)
    - Cursor verandert naar hand bij hover
    """

    def __init__(self, label: str, x: float, y: float, callback, parent=None):
        r = _OVERLAY_R
        super().__init__(x - r, y - r, r * 2, r * 2, parent)
        self._label    = label
        self._callback = callback
        self._mapped   = False
        self._selected = False

        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setZValue(10)
        self.setToolTip(label)

        # Label ONDER de cirkel, donkere tekst op lichte achtergrond
        self._txt = QGraphicsSimpleTextItem(label, self)
        font = QFont()
        font.setPointSize(6)
        font.setBold(True)
        self._txt.setFont(font)
        self._txt.setZValue(12)

        # Positioneer label gecentreerd onder de cirkel
        txt_w = self._txt.boundingRect().width()
        self._txt.setPos(-txt_w / 2, r + 1)

        self._update_style()

    def set_mapped(self, mapped: bool):
        self._mapped = mapped
        self._update_style()

    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()

    def _update_style(self):
        color = _COLOR_SELECTED if self._selected else (
            _COLOR_MAPPED if self._mapped else _COLOR_UNMAPPED
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

        self._title_label = QLabel(t("title_floorplan_view"))
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

        viewer_btn_row.addWidget(self._btn_reset_zoom)
        viewer_btn_row.addWidget(self._btn_fit)
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

        map_layout.addWidget(self._mapping_info)
        map_layout.addWidget(self._btn_map)
        map_layout.addWidget(self._btn_unmap)
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

        self._tabs.addTab(self._tab_selection, t("floorplan_tab_selection"))
        self._tabs.addTab(self._tab_mapping, t("floorplan_tab_mapping"))
        self._tabs.addTab(self._tab_trace, t("floorplan_tab_trace"))
        self._tabs.addTab(self._tab_validation, t("floorplan_tab_validation"))

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

        svg_path = floorplan_service.get_svg_path(self._floorplan)

        if not svg_path.exists():
            self._scene.addText(t("floorplan_validation_missing_svg"))
            self._refresh_validation()
            return

        self._svg_item = QGraphicsSvgItem(str(svg_path))
        self._scene.addItem(self._svg_item)
        self._scene.setSceneRect(self._svg_item.boundingRect())

        self._detected_svg_points = floorplan_svg_service.detect_point_labels(svg_path)

        # Overlays plaatsen op gedetecteerde posities
        positions = floorplan_svg_service.detect_point_positions(svg_path)
        mappings  = self._floorplan.get("mappings", {})
        for label, (x, y) in positions.items():
            overlay = _OverlayItem(
                label=label, x=x, y=y,
                callback=self._on_overlay_clicked,
            )
            overlay.set_mapped(label in mappings)
            self._scene.addItem(overlay)
            self._overlay_items[label] = overlay

        self._refresh_validation()

    def showEvent(self, event):
        """Fit SVG to screen bij eerste toon — betrouwbaarder dan in _load_svg."""
        super().showEvent(event)
        if not self._fit_done and self._svg_item is not None:
            self._on_fit()
            self._fit_done = True

    def _on_overlay_clicked(self, label: str):
        """Overlay aangeklikt — selecteer punt en switch naar mapping tab."""
        self.set_selected_svg_point(label)
        self._tabs.setCurrentWidget(self._tab_mapping)

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
            self._selected_outlet_id = floorplan_service.get_mapping(
                self._floorplan["id"], svg_point,
            )
            if svg_point in self._overlay_items:
                self._overlay_items[svg_point].set_selected(True)

        self._refresh_sidepanel()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

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

    def _on_trace_clicked(self):
        if not self._selected_outlet_id:
            self._trace_info.setPlainText(t("trace_no_connection"))
            return

        steps = tracing.trace_from_wall_outlet(self._data, self._selected_outlet_id)

        if not steps:
            self._trace_info.setPlainText(t("trace_no_connection"))
            return

        lines = []
        for step in steps:
            label = step.get("label", "?")
            obj_type = step.get("obj_type", "")
            cable_type = step.get("cable_type", "")
            if cable_type:
                lines.append(f"[{obj_type}] {label}  ({cable_type})")
            else:
                lines.append(f"[{obj_type}] {label}")

        self._trace_info.setPlainText("\n".join(lines))
        self.trace_requested.emit(self._selected_outlet_id)

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
        """
        latest = floorplan_service.get_floorplan(self._floorplan.get("id", ""))
        if latest:
            self._floorplan = latest

        # Overlay kleuren bijwerken
        mappings = self._floorplan.get("mappings", {})
        for label, overlay in self._overlay_items.items():
            overlay.set_mapped(label in mappings)
            overlay.set_selected(label == self._selected_svg_point)

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
        else:
            self._trace_info.setPlainText(t("trace_no_connection"))

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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_outlet_name(self, outlet_id: str | None) -> str | None:
        if not outlet_id:
            return None

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