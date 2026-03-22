# =============================================================================
# Networkmap_Creator
# File:    app/gui/main_window.py
# Role:    Hoofdvenster — orkestratie, 3-zone layout, toolbar
# Version: 1.32.3
# Author:  Barremans
# Changes: F1 — ESC annuleert verbindingsmodus
#               Klik op lege poort wist vorige trace + highlight
#          G1+G2 — PNG/JPG + PDF export via QPainter renderer
#          G3 — Word rapport export via python-docx
#          H1 — Help menu (sneltoetsen, gebruiksaanwijzing, versie-info)
#          H1b — Verbinding bewerken (label, kabeltype, notitie)
#          H1c — Rack bezettingsgraad in boom + auto-open na export
#          Taak2 — log_change() aanroepen voor devices en verbindingen
#          1.25.0 — data_integrity.validate_and_repair() na laden
#                   _gen_id: random suffix + ports opgenomen in ID-check
#          1.26.0 — Menubar: In/Ex-port menu (nieuw)
#          1.27.0 — Rapporteren menu (bug report + GitHub cases)
#                   Refresh fix: boom hertekent na toevoegen device
#                   Import/Export verplaatst van Bestand → In/Ex-port
#          1.32.2 — Fix PortDialog: nieuwe poorten (id="") worden nu aangemaakt
#                   in self._data via _gen_id("p") ipv stilzwijgend genegeerd
#                   VLAN propagatie werkt ook correct voor nieuw aangemaakte poorten
#                   Toolbar opgeschoond: import/export knoppen verwijderd
#          1.32.3 — Fix: locatie key vertaald via get_outlet_location_label()
#                   in boom tooltip (was raw key, bv. containerd_a)
#          1.28.0 — Versie dynamisch uit version.py (fix statusbalk vs Over)
#          1.29.0 — Dubbelklik device → info popup; PortDialog; VLAN rapport zijpaneel
#          1.30.0 — VLAN beheer knop + automatische propagatie na opslaan poort/wandpunt
#          1.31.0 — Settings menu in menubar (Instellingen + VLAN beheer)
#          1.31.2 — Rapporteren volgorde aangepast; Im/Export namen + divider
#                   VLAN rapport onder Rapporteren; linkerpaneel knoppen verwijderd
#                   Instellingen uit toolbar; Im/Export shortcuts opgeschoond
#          1.32.0 — Uppercase weergave: site/room/rack/device/wandpunt namen in boom
#          1.32.1 — outlet_edit_requested gekoppeld in room- en site-modus wandpuntview
# =============================================================================

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QFrame, QSplitter,
    QVBoxLayout, QHBoxLayout, QToolBar, QLabel,
    QSizePolicy, QStatusBar, QTreeWidget, QTreeWidgetItem,
    QPushButton
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QKeySequence, QColor, QBrush

from app.helpers import settings_storage
from app.helpers.settings_storage import get_last_folder, set_last_folder
from app.helpers.i18n import t
from app.gui.rack_view import RackView, _rack_occupancy, _occupancy_color
from app.gui.wall_outlet_view import WallOutletView
from app.gui.outlet_locator_view import OutletLocatorView
from app.gui.wire_detail_view import WireDetailView
from app.gui.search_window import SearchWindow
from app.gui.settings_window import SettingsWindow
from app.gui.help_window import HelpWindow
from app.gui.dialogs.connection_dialog import ConnectionDialog
from app.gui.dialogs.connection_edit_dialog import ConnectionEditDialog
from app.gui.dialogs.connect_to_outlet_dialog import ConnectToOutletDialog
from app.gui.dialogs.site_dialog import SiteDialog
from app.gui.dialogs.room_dialog import RoomDialog
from app.gui.dialogs.rack_dialog import RackDialog
from app.gui.dialogs.device_dialog import DeviceDialog
from app.gui.dialogs.place_device_dialog import PlaceDeviceDialog
from app.gui.dialogs.wall_outlet_dialog import WallOutletDialog
from app.gui.dialogs.endpoint_dialog import EndpointDialog
from app.services import tracing
from app.services import search_service
from app.services import import_export_service
from app.services import backup_service
from app.services.logger import log_info, log_warning, log_error
from app.services import export_renderer
from app.services import report_generator
from app.gui.bug_report_dialog import BugReportDialog
from app.gui.dialogs.device_info_dialog import DeviceInfoDialog
from app.gui.dialogs.port_dialog import PortDialog
from app.services import vlan_service
from app.gui.dialogs.vlan_propagation_dialog import VlanPropagationDialog
from app.gui.github_cases_dialog import GithubCasesDialog
from app.services.changelog_service import (   # Taak2
    log_change,
    ENTITY_DEVICE, ENTITY_CONNECTION,
    ACTION_ADD, ACTION_EDIT, ACTION_DELETE
)

try:
    from app import version as _ver
    _APP_VERSION = _ver.__version__
except Exception:
    _APP_VERSION = "—"

_COL              = 0
_TYPE_SITE        = "site"
_TYPE_ROOM        = "room"
_TYPE_RACK        = "rack"
_TYPE_OUTLETS     = "outlets"
_TYPE_OUTLET      = "outlet"       # individueel wandpunt in boom
_TYPE_SITE_OUTLETS = "site_outlets" # alle wandpunten van een site (E3)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self._data     = settings_storage.load_network_data()
        self._settings = settings_storage.load_settings()

        # Automatische data-integriteitscontrole bij elke start — v1.25.0
        from app.services.data_integrity import validate_and_repair
        self._data, _repaired, _rapport = validate_and_repair(self._data)
        if _repaired:
            settings_storage.save_network_data(self._data)
            for regel in _rapport:
                log_info(f"[data_integrity] {regel}")

        self._current_view    = None
        self._connect_mode    = False
        self._connect_port_a  = None   # eerste geselecteerde poort ID
        self._outlet_locator_view = None  # persistent view, hergebruikt (E3)
        self._setup_window()
        self._build_menubar()
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self._attach_new_menu()   # dropdown op Nieuw knop
        self._populate_tree()

    # ------------------------------------------------------------------
    # Venster
    # ------------------------------------------------------------------

    def _setup_window(self):
        self.setWindowTitle(t("app_title"))
        self.setMinimumSize(1100, 680)
        self.resize(1280, 800)

    # ------------------------------------------------------------------
    # Menubar — H1
    # ------------------------------------------------------------------

    def _build_menubar(self):
        mb = self.menuBar()

        # ── Bestand menu ─────────────────────────────────────────────
        self._menu_file = mb.addMenu(t("menubar_file"))

        act_settings = self._menu_file.addAction(t("menu_settings"))
        act_settings.triggered.connect(self._on_settings)

        self._menu_file.addSeparator()

        act_quit = self._menu_file.addAction(t("menubar_quit"))
        act_quit.setShortcut("Alt+F4")
        act_quit.triggered.connect(self.close)

        # ── In/Ex-port menu ──────────────────────────────────────────
        self._menu_inex = mb.addMenu(t("menubar_inexport"))

        act_import = self._menu_inex.addAction("Importeren Data")
        act_import.triggered.connect(self._on_import)

        act_export = self._menu_inex.addAction("Exporteren Data")
        act_export.triggered.connect(self._on_export)

        self._menu_inex.addSeparator()

        act_export_image = self._menu_inex.addAction(t("menu_export_image"))
        act_export_image.triggered.connect(self._on_export_image)

        # ── Rapporteren menu ─────────────────────────────────────────
        self._menu_report = mb.addMenu(t("menubar_report"))

        act_word_report = self._menu_report.addAction(t("menu_export_report"))
        act_word_report.triggered.connect(self._on_export_report)

        self._menu_report.addSeparator()

        act_vlan_report_mb = self._menu_report.addAction("🔷  VLAN rapport")
        act_vlan_report_mb.triggered.connect(self._on_vlan_report)

        self._menu_report.addSeparator()

        act_bug = self._menu_report.addAction(t("menu_report_bug"))
        act_bug.triggered.connect(self._on_report_bug)

        act_feature = self._menu_report.addAction(t("menu_report_feature"))
        act_feature.triggered.connect(self._on_report_feature)

        act_cases = self._menu_report.addAction(t("menu_report_cases"))
        act_cases.triggered.connect(self._on_show_cases)

        # ── Settings menu ────────────────────────────────────────────
        self._menu_settings_mb = mb.addMenu("Settings")

        act_settings_mb = self._menu_settings_mb.addAction(t("menu_settings"))
        act_settings_mb.triggered.connect(self._on_settings)

        self._menu_settings_mb.addSeparator()

        act_vlan_mgr_mb = self._menu_settings_mb.addAction("⚙  VLAN beheer")
        act_vlan_mgr_mb.triggered.connect(self._on_vlan_manager)

        # ── Help menu ────────────────────────────────────────────────
        self._menu_help = mb.addMenu(t("menubar_help"))

        act_help = self._menu_help.addAction(t("help_title"))
        act_help.setShortcut("F1")
        act_help.triggered.connect(self._on_help)

        self._menu_help.addSeparator()

        act_about = self._menu_help.addAction(t("help_tab_version"))
        act_about.triggered.connect(self._on_about)

    def _build_toolbar(self):
        tb = QToolBar()
        tb.setMovable(False)
        tb.setIconSize(QSize(16, 16))
        tb.setObjectName("main_toolbar")

        self._act_new       = QAction(t("menu_new"),       self)
        self._act_new.setShortcut(QKeySequence.StandardKey.New)
        self._act_new.setEnabled(True)
        self._act_new.triggered.connect(self._on_new)
        # Sla toolbar referentie op voor menu koppeling na build
        self._tb = tb
        tb.addAction(self._act_new)

        self._act_edit      = QAction(t("menu_edit"),      self)
        self._act_edit.setEnabled(True)
        self._act_edit.triggered.connect(self._on_edit)
        tb.addAction(self._act_edit)

        self._act_delete    = QAction(t("menu_delete"),    self)
        self._act_delete.setShortcut(QKeySequence.StandardKey.Delete)
        self._act_delete.setEnabled(True)
        self._act_delete.triggered.connect(self._on_delete)
        tb.addAction(self._act_delete)

        self._act_duplicate = QAction(t("menu_duplicate"), self)
        self._act_duplicate.setEnabled(True)
        self._act_duplicate.triggered.connect(self._on_duplicate)
        tb.addAction(self._act_duplicate)

        tb.addSeparator()

        self._act_search    = QAction(t("menu_search"),    self)
        self._act_search.setShortcut(QKeySequence.StandardKey.Find)
        self._act_search.setEnabled(True)
        self._act_search.triggered.connect(self._on_search)
        tb.addAction(self._act_search)

        self._act_outlet_locator = QAction(t("menu_outlet_locator"), self)
        self._act_outlet_locator.setShortcut("Ctrl+W")
        self._act_outlet_locator.setEnabled(True)
        self._act_outlet_locator.triggered.connect(self._on_outlet_locator)
        tb.addAction(self._act_outlet_locator)

        self._act_connect   = QAction(t("menu_connect"),   self)
        self._act_connect.setCheckable(True)
        self._act_connect.setEnabled(True)
        self._act_connect.triggered.connect(self._on_connect_mode_toggled)
        tb.addAction(self._act_connect)

        tb.addSeparator()

        self._act_settings  = QAction(t("menu_settings"),  self)
        self._act_settings.setEnabled(True)
        self._act_settings.triggered.connect(self._on_settings)

        # QActions voor In/Ex-port — alleen in menu, niet in toolbar
        self._act_import    = QAction(t("menu_import"),    self)
        self._act_import.setEnabled(True)
        self._act_import.triggered.connect(self._on_import)

        self._act_export    = QAction(t("menu_export"),    self)
        self._act_export.setEnabled(True)
        self._act_export.triggered.connect(self._on_export)

        self._act_export_image = QAction(t("menu_export_image"), self)
        self._act_export_image.setShortcut("Ctrl+Shift+E")
        self._act_export_image.setEnabled(True)
        self._act_export_image.triggered.connect(self._on_export_image)

        self._act_export_pdf = QAction(t("menu_export_pdf"), self)
        self._act_export_pdf.setShortcut("Ctrl+Shift+P")
        self._act_export_pdf.setEnabled(True)
        self._act_export_pdf.triggered.connect(self._on_export_pdf)

        self._act_export_report = QAction(t("menu_export_report"), self)
        self._act_export_report.setShortcut("Ctrl+Shift+R")
        self._act_export_report.setEnabled(True)
        self._act_export_report.triggered.connect(self._on_export_report)

        self.addToolBar(tb)

    # ------------------------------------------------------------------
    # Centrale layout — 3 zones
    # ------------------------------------------------------------------

    def _build_central(self):
        root        = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        v_splitter = QSplitter(Qt.Orientation.Vertical)
        v_splitter.setChildrenCollapsible(False)

        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        h_splitter.setChildrenCollapsible(False)

        # Linker frame
        self._left_frame = QFrame()
        self._left_frame.setObjectName("left_frame")
        self._left_frame.setMinimumWidth(200)
        self._left_frame.setMaximumWidth(380)
        left_layout = QVBoxLayout(self._left_frame)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setColumnCount(1)
        self._tree.setIndentation(16)
        self._tree.setAnimated(True)
        self._tree.itemClicked.connect(self._on_tree_item_clicked)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        left_layout.addWidget(self._tree)



        # Midden frame
        self._mid_frame = QFrame()
        self._mid_frame.setObjectName("mid_frame")
        self._mid_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self._mid_layout = QVBoxLayout(self._mid_frame)
        self._mid_layout.setContentsMargins(12, 12, 12, 12)
        self._mid_layout.setSpacing(4)

        self._mid_placeholder = QLabel(t("label_rack") + " / " + t("title_wall_outlets"))
        self._mid_placeholder.setObjectName("secondary")
        self._mid_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._mid_layout.addWidget(
            self._mid_placeholder, alignment=Qt.AlignmentFlag.AlignCenter
        )

        h_splitter.addWidget(self._left_frame)
        h_splitter.addWidget(self._mid_frame)
        h_splitter.setStretchFactor(0, 0)
        h_splitter.setStretchFactor(1, 1)
        h_splitter.setSizes([240, 900])

        # Detail frame — WireDetailView
        self._detail_frame = QFrame()
        self._detail_frame.setObjectName("detail_frame")
        self._detail_frame.setMinimumHeight(80)
        self._detail_frame.setMaximumHeight(160)
        detail_outer = QVBoxLayout(self._detail_frame)
        detail_outer.setContentsMargins(0, 0, 0, 0)
        detail_outer.setSpacing(0)

        self._wire_detail = WireDetailView(parent=self._detail_frame)
        self._wire_detail.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._wire_detail.delete_connection.connect(self._on_delete_connection)
        self._wire_detail.edit_connection.connect(self._on_edit_connection)
        self._wire_detail.navigate_to_rack.connect(self._on_navigate_to_rack)
        detail_outer.addWidget(self._wire_detail)

        v_splitter.addWidget(h_splitter)
        v_splitter.addWidget(self._detail_frame)
        v_splitter.setStretchFactor(0, 1)
        v_splitter.setStretchFactor(1, 0)
        v_splitter.setSizes([620, 100])

        root_layout.addWidget(v_splitter)
        self.setCentralWidget(root)

    # ------------------------------------------------------------------
    # Statusbalk
    # ------------------------------------------------------------------

    def _build_statusbar(self):
        sb = QStatusBar()
        sb.setObjectName("status_bar")
        version_label = QLabel(f"Networkmap Creator v{_APP_VERSION}")
        version_label.setObjectName("secondary")
        sb.addPermanentWidget(version_label)
        self.setStatusBar(sb)
        self.set_status(t("app_ready"))

    # ------------------------------------------------------------------
    # Toetsenbord — F1
    # ------------------------------------------------------------------

    def keyPressEvent(self, event):
        """ESC annuleert verbindingsmodus. F1 opent Help."""
        if event.key() == Qt.Key.Key_Escape and self._connect_mode:
            self._on_connect_mode_toggled(False)
            self._act_connect.setChecked(False)
            self.set_status(t("msg_connect_cancelled"))
            event.accept()
            return
        if event.key() == Qt.Key.Key_F1:
            self._on_help()
            event.accept()
            return
        super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Boomstructuur
    # ------------------------------------------------------------------

    def _populate_tree(self):
        """Herbouw de volledige boom. Bewaart uitgelapte state van bestaande items."""
        expanded = set()
        for i in range(self._tree.topLevelItemCount()):
            site_item = self._tree.topLevelItem(i)
            site_data = site_item.data(_COL, Qt.ItemDataRole.UserRole)
            if site_item.isExpanded() and site_data:
                expanded.add(site_data.get("id", ""))
            for j in range(site_item.childCount()):
                room_item = site_item.child(j)
                room_data = room_item.data(_COL, Qt.ItemDataRole.UserRole)
                if room_item.isExpanded() and room_data:
                    expanded.add(room_data.get("id", ""))

        self._tree.clear()
        sites = self._data.get("sites", [])

        for idx, site in enumerate(sites):
            site_item = QTreeWidgetItem([f"📍  {site['name'].upper()}"])
            site_item.setData(_COL, Qt.ItemDataRole.UserRole, {
                "type": _TYPE_SITE,
                "id":   site["id"],
            })
            site_item.setToolTip(_COL, site.get("location", ""))

            for room in site.get("rooms", []):
                room_item = QTreeWidgetItem([f"🚪  {room['name'].upper()}"])
                room_item.setData(_COL, Qt.ItemDataRole.UserRole, {
                    "type":    _TYPE_ROOM,
                    "id":      room["id"],
                    "site_id": site["id"],
                })
                room_item.setToolTip(_COL, self._room_tooltip(room, site))

                for rack in room.get("racks", []):
                    used, total = _rack_occupancy(rack)
                    pct   = (used / total * 100) if total else 0
                    color = _occupancy_color(used, total)
                    rack_item = QTreeWidgetItem([f"🗄  {rack['name'].upper()}"])
                    rack_item.setData(_COL, Qt.ItemDataRole.UserRole, {
                        "type":    _TYPE_RACK,
                        "id":      rack["id"],
                        "room_id": room["id"],
                        "site_id": site["id"],
                    })
                    rack_item.setToolTip(_COL,
                        f"{rack['total_units']}U  ·  {used}/{total}U bezet ({pct:.0f}%)  ·  "
                        f"{self._room_status_label(room, site)}")
                    rack_item.setForeground(_COL, QBrush(QColor(color)))
                    room_item.addChild(rack_item)

                outlets      = room.get("wall_outlets", [])
                outlets_item = QTreeWidgetItem([
                    f"🌐  {t('tree_wall_outlets')}  ({len(outlets)})" if outlets
                    else f"🌐  {t('tree_wall_outlets')}"
                ])
                outlets_item.setData(_COL, Qt.ItemDataRole.UserRole, {
                    "type":    _TYPE_OUTLETS,
                    "room_id": room["id"],
                    "site_id": site["id"],
                })
                for wo in outlets:
                    wo_item = QTreeWidgetItem([f"   {wo.get('name', wo['id']).upper()}"])
                    wo_item.setData(_COL, Qt.ItemDataRole.UserRole, {
                        "type":    _TYPE_OUTLET,
                        "id":      wo["id"],
                        "room_id": room["id"],
                        "site_id": site["id"],
                    })
                    loc_key   = wo.get("location_description", "")
                    loc_label = settings_storage.get_outlet_location_label(
                        loc_key, self._settings.get("language", "nl")
                    ) if loc_key else ""
                    wo_item.setToolTip(_COL, loc_label)
                    outlets_item.addChild(wo_item)
                room_item.addChild(outlets_item)
                site_item.addChild(room_item)

            all_site_outlets = [
                wo for room in site.get("rooms", [])
                for wo in room.get("wall_outlets", [])
            ]
            site_outlets_item = QTreeWidgetItem([
                f"🌐  {t('tree_site_outlets')}  ({len(all_site_outlets)})"
                if all_site_outlets
                else f"🌐  {t('tree_site_outlets')}"
            ])
            site_outlets_item.setData(_COL, Qt.ItemDataRole.UserRole, {
                "type":    _TYPE_SITE_OUTLETS,
                "id":      site["id"],
                "site_id": site["id"],
            })
            site_outlets_item.setToolTip(_COL,
                f"{len(all_site_outlets)} wandpunten in {len(site.get('rooms', []))} ruimtes")
            site_item.addChild(site_outlets_item)

            self._tree.addTopLevelItem(site_item)

            if site["id"] in expanded:
                site_item.setExpanded(True)
                for j in range(site_item.childCount()):
                    child = site_item.child(j)
                    child_data = child.data(_COL, Qt.ItemDataRole.UserRole)
                    if child_data and child_data.get("id", "") in expanded:
                        child.setExpanded(True)
            elif idx == 0:
                site_item.setExpanded(True)

    # ------------------------------------------------------------------
    # Klik handler
    # ------------------------------------------------------------------

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(_COL, Qt.ItemDataRole.UserRole)
        if not data:
            return
        item_type = data.get("type")

        if item_type == _TYPE_RACK:
            rack = self._find_rack(data["id"])
            room = self._find_room(data["room_id"])
            site = self._find_site(data["site_id"])
            if rack and room and site:
                self.set_status(
                    f"{t('label_rack')}: {rack['name']}  ·  "
                    f"{t('label_room')}: {room['name']}  ·  "
                    f"{t('label_site')}: {site['name']}"
                )
                self._show_rack_view(rack, room, site)

        elif item_type == _TYPE_SITE_OUTLETS:
            site = self._find_site(data["site_id"])
            if site:
                all_outlets = [
                    wo for room in site.get("rooms", [])
                    for wo in room.get("wall_outlets", [])
                ]
                self.set_status(
                    f"🌐  {t('tree_site_outlets')}  —  {site['name']}  "
                    f"({len(all_outlets)} {t('tree_wall_outlets').lower()})"
                )
                self._show_site_outlets_view(site)

        elif item_type == _TYPE_OUTLETS:
            room = self._find_room(data["room_id"])
            site = self._find_site(data["site_id"])
            if room and site:
                outlets = room.get("wall_outlets", [])
                self.set_status(
                    f"{t('label_wall_outlet')} — "
                    f"{room['name']}  ·  {site['name']}  "
                    f"({len(outlets)} {t('tree_wall_outlets').lower()})"
                )
                self._show_wall_outlet_view(room, site)

        elif item_type == _TYPE_OUTLET:
            room = self._find_room(data["room_id"])
            site = self._find_site(data["site_id"])
            if room and site:
                self._show_wall_outlet_view(room, site)
                steps = tracing.trace_from_wall_outlet(self._data, data["id"])
                wo = next((w for w in room.get("wall_outlets", [])
                           if w["id"] == data["id"]), None)
                if wo:
                    self.set_status(
                        f"{t('label_wall_outlet')}: {wo['name']}  ·  "
                        f"{room['name']}  ·  {site['name']}"
                    )
                    self._wire_detail.set_trace(steps, wo.get("name", ""), data=self._data)

        elif item_type == _TYPE_ROOM:
            room = self._find_room(data["id"])
            site = self._find_site(data["site_id"])
            if room and site:
                self.set_status(
                    f"{t('label_room')}: {room['name']}  ·  "
                    f"{t('label_site')}: {site['name']}"
                )
                if isinstance(self._current_view, OutletLocatorView):
                    self._current_view.set_room(data["id"])
                elif not room.get("racks") and room.get("wall_outlets"):
                    self._show_outlet_locator(room_id=data["id"])
                    self.set_status(
                        f"🌐  {room['name']}  ·  {site['name']}  —  "
                        f"{len(room['wall_outlets'])} {t('tree_wall_outlets').lower()}"
                    )

        elif item_type == _TYPE_SITE:
            site = self._find_site(data["id"])
            if site:
                self.set_status(
                    f"{t('label_site')}: {site['name']}  ·  "
                    f"{site.get('location', '')}"
                )

    def _on_tree_context_menu(self, pos):
        """Rechtermuisklik op boom — toont context menu op basis van item type."""
        from PySide6.QtWidgets import QMenu
        item = self._tree.itemAt(pos)
        if not item:
            menu = QMenu(self)
            menu.addAction(f"📍  {t('label_site')}", self._new_site)
            menu.exec(self._tree.viewport().mapToGlobal(pos))
            return

        data      = item.data(_COL, Qt.ItemDataRole.UserRole)
        if not data:
            return
        item_type = data.get("type")
        self._tree.setCurrentItem(item)
        menu = QMenu(self)

        if item_type == _TYPE_SITE:
            menu.addAction(t("ctx_edit"),       lambda: self._on_edit())
            menu.addSeparator()
            menu.addAction(t("ctx_new_room"),   lambda: self._new_room(data["id"]))
            menu.addSeparator()
            menu.addAction(t("ctx_delete"),     lambda: self._on_delete())

        elif item_type == _TYPE_ROOM:
            menu.addAction(t("ctx_edit"),       lambda: self._on_edit())
            menu.addSeparator()
            menu.addAction(t("ctx_new_rack"),   lambda: self._new_rack(data["id"]))
            menu.addAction(t("ctx_new_outlet"),
                           lambda: self._new_wall_outlet(data["id"]))
            menu.addSeparator()
            menu.addAction(t("ctx_delete"),     lambda: self._on_delete())

        elif item_type == _TYPE_RACK:
            menu.addAction(t("ctx_edit"),
                           lambda: self._edit_rack_direct(data))
            menu.addSeparator()
            menu.addAction(t("ctx_new_device"),
                           lambda: self._new_device_in_rack(data["id"]))
            menu.addSeparator()
            menu.addAction(t("ctx_delete"),
                           lambda: self._delete_rack_direct(data))

        elif item_type == _TYPE_OUTLETS:
            menu.addAction(t("ctx_new_outlet"),
                           lambda: self._new_wall_outlet(data["room_id"]))

        elif item_type == _TYPE_OUTLET:
            menu.addAction(t("ctx_edit_outlet"),
                           lambda: self._edit_wall_outlet(data))
            menu.addSeparator()
            menu.addAction(t("ctx_delete_outlet"),
                           lambda: self._delete_wall_outlet(data))

        if not menu.isEmpty():
            menu.exec(self._tree.viewport().mapToGlobal(pos))

    def _edit_wall_outlet(self, data: dict):
        """Wandpunt bewerken via context menu."""
        room = self._find_room(data["room_id"])
        if not room:
            return
        wo = next((w for w in room.get("wall_outlets", [])
                   if w["id"] == data["id"]), None)
        if not wo:
            return
        endpoints = self._data.get("endpoints", [])
        dlg = WallOutletDialog(parent=self, room_id=data["room_id"],
                               endpoints=endpoints, outlet=wo,
                               existing_outlets=room.get("wall_outlets", []))
        if dlg.exec() and dlg.get_result():
            self._data["endpoints"] = dlg.get_endpoints_result()
            wo.update(dlg.get_result())
            self._save_and_backup()
            self._populate_tree()
            self.set_status(f"✓  {t('label_wall_outlet')} '{wo['name']}' bijgewerkt.")

    def _on_outlet_edit_requested(self, outlet_id: str):
        """Rechtsklik 'Bewerken' vanuit WallOutletView kaartje."""
        # Zoek het wandpunt en de bijhorende ruimte op in de data
        for site in self._data.get("sites", []):
            for room in site.get("rooms", []):
                for wo in room.get("wall_outlets", []):
                    if wo["id"] == outlet_id:
                        self._edit_wall_outlet({
                            "id":      outlet_id,
                            "room_id": room["id"],
                        })
                        return

    def _delete_wall_outlet(self, data: dict):
        """Wandpunt verwijderen via context menu."""
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, t("menu_delete"), t("msg_confirm_delete"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        room = self._find_room(data["room_id"])
        if room:
            room["wall_outlets"] = [
                wo for wo in room.get("wall_outlets", []) if wo["id"] != data["id"]
            ]
            self._data["connections"] = [
                c for c in self._data.get("connections", [])
                if not (c.get("from_id") == data["id"] or c.get("to_id") == data["id"])
            ]
            self._save_and_backup()
            self._populate_tree()
            self.set_status(f"✓  {t('label_wall_outlet')} verwijderd.")

    def _on_device_context_menu(self, device_id: str, action: str):
        """Dispatcher voor device context menu acties vanuit rack_view."""
        rack_data = None
        for site in self._data.get("sites", []):
            for room in site.get("rooms", []):
                for rack in room.get("racks", []):
                    for slot in rack.get("slots", []):
                        if slot.get("device_id") == device_id:
                            rack_data = {
                                "type":    _TYPE_RACK,
                                "id":      rack["id"],
                                "room_id": room["id"],
                                "site_id": site["id"],
                            }
                            break

        device = next((d for d in self._data.get("devices", [])
                       if d["id"] == device_id), None)
        if not device:
            return

        if action == "edit":
            dlg = DeviceDialog(parent=self, device=device)
            if dlg.exec() and dlg.get_result():
                device.update(dlg.get_result())
                # Genereer ontbrekende SFP poorten
                new_front = device.get("front_ports", 0)
                new_sfp   = device.get("sfp_ports",   0)
                existing_nums = {
                    p["number"] for p in self._data.get("ports", [])
                    if p["device_id"] == device["id"] and p["side"] == "front"
                }
                for i in range(1, new_sfp + 1):
                    sfp_num = new_front + i
                    if sfp_num not in existing_nums:
                        self._data.setdefault("ports", []).append({
                            "id":        self._gen_id("p"),
                            "device_id": device["id"],
                            "name":      f"SFP {i}",
                            "side":      "front",
                            "number":    sfp_num,
                        })
                self._save_and_backup()
                # Taak2 — log device bewerken
                log_change(
                    action=ACTION_EDIT,
                    entity=ENTITY_DEVICE,
                    entity_id=device["id"],
                    label=f"{device['type']} — {device['name']}"
                )
                if isinstance(self._current_view, RackView):
                    self._current_view.refresh(self._data)
                self.set_status(f"✓  {t('msg_device_updated')}: {device['name']}.")

        elif action == "ports":
            ports = [p for p in self._data.get("ports", [])
                     if p["device_id"] == device_id]
            dlg = PortDialog(parent=self, device=device, ports=ports)
            if dlg.exec():
                updated  = dlg.get_result()
                port_map = {p["id"]: p for p in self._data.get("ports", [])}
                for up in updated:
                    if up.get("id"):
                        # Bestaande poort — gewoon updaten
                        if up["id"] in port_map:
                            port_map[up["id"]].update(up)
                    else:
                        # Nieuwe poort (aangemaakt door port_dialog._ensure_all_ports)
                        # — genereer id en voeg toe aan data
                        new_port = dict(up)
                        new_port["id"] = self._gen_id("p")
                        self._data.setdefault("ports", []).append(new_port)
                # Propageer VLAN voor elke poort die een VLAN heeft
                for up in updated:
                    pid = up.get("id") or next(
                        (p["id"] for p in self._data.get("ports", [])
                         if p["device_id"] == up.get("device_id")
                         and p["side"] == up.get("side")
                         and p["number"] == up.get("number")), None
                    )
                    if pid and up.get("vlan"):
                        self._propagate_vlan_after_save(pid, "port", up["vlan"])
                self._save_and_backup()
                if isinstance(self._current_view, __import__(
                        "app.gui.rack_view", fromlist=["RackView"]).RackView):
                    self._current_view.refresh(self._data)
                self.set_status(f"✓  Poorten bijgewerkt: {device['name']}")

        elif action == "delete":
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.warning(
                self, t("menu_delete"),
                t("delete_device_confirm"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            # Taak2 — log device verwijderen (vóór de verwijdering)
            log_change(
                action=ACTION_DELETE,
                entity=ENTITY_DEVICE,
                entity_id=device_id,
                label=f"{device['type']} — {device['name']}"
            )
            port_ids = {p["id"] for p in self._data.get("ports", [])
                        if p["device_id"] == device_id}
            self._data["ports"] = [
                p for p in self._data.get("ports", []) if p["device_id"] != device_id
            ]
            self._data["connections"] = [
                c for c in self._data.get("connections", [])
                if c.get("from_id") not in port_ids and c.get("to_id") not in port_ids
            ]
            if rack_data:
                rack = self._find_rack(rack_data["id"])
                if rack:
                    rack["slots"] = [
                        s for s in rack.get("slots", []) if s.get("device_id") != device_id
                    ]
            self._data["devices"] = [
                d for d in self._data.get("devices", []) if d["id"] != device_id
            ]
            self._save_and_backup()
            if isinstance(self._current_view, RackView):
                self._current_view.refresh(self._data)
            self._wire_detail.clear()
            self.set_status(f"✓  {t('msg_device_deleted')}: {device['name']}.")

    def _show_wall_outlet_view(self, room: dict, site: dict):
        """Verwijder huidige midden-inhoud en toon WallOutletView (ruimte-modus)."""
        while self._mid_layout.count():
            item = self._mid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        outlet_view = WallOutletView(room, site, self._data,
                                     mode="room", parent=self._mid_frame)
        outlet_view.outlet_clicked.connect(self._on_outlet_clicked)
        outlet_view.outlet_edit_requested.connect(self._on_outlet_edit_requested)
        self._mid_layout.addWidget(outlet_view)
        self._current_view = outlet_view

    def _show_site_outlets_view(self, site: dict):
        """Toon WallOutletView in site-modus — alle wandpunten van de site."""
        while self._mid_layout.count():
            item = self._mid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        outlet_view = WallOutletView(site, None, self._data,
                                     mode="site", parent=self._mid_frame)
        outlet_view.outlet_clicked.connect(self._on_outlet_clicked)
        outlet_view.outlet_edit_requested.connect(self._on_outlet_edit_requested)
        self._mid_layout.addWidget(outlet_view)
        self._current_view = outlet_view

    def _on_outlet_clicked(self, outlet_id: str):
        """Wandpunt aangeklikt — bereken trace en toon in wire_detail."""
        room_outlets = [
            wo for s in self._data.get("sites", [])
            for r in s.get("rooms", [])
            for wo in r.get("wall_outlets", [])
        ]
        outlet = next((wo for wo in room_outlets if wo["id"] == outlet_id), None)
        if outlet:
            ep_id  = outlet.get("endpoint_id")
            ep     = next((e for e in self._data.get("endpoints", [])
                           if e["id"] == ep_id), None) if ep_id else None
            status = f"{t('label_wall_outlet')}: {outlet['name']}"
            if ep:
                status += f"  ·  {t('label_endpoint')}: {ep['name']}"
            self.set_status(status)

            steps = tracing.trace_from_wall_outlet(self._data, outlet_id)
            self._wire_detail.set_trace(steps, outlet.get("name", outlet_id), data=self._data)

    def _show_rack_view(self, rack: dict, room: dict, site: dict):
        """Verwijder huidige midden-inhoud en toon RackView."""
        while self._mid_layout.count():
            item = self._mid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        rack_view = RackView(rack, room, site, self._data, parent=self._mid_frame)
        rack_view.port_clicked.connect(self._on_port_clicked)
        rack_view.port_selected_for_connect.connect(self._on_port_selected_for_connect)
        rack_view.device_context_menu.connect(self._on_device_context_menu)
        rack_view.port_context_menu.connect(self._on_port_context_menu)
        rack_view.device_double_clicked.connect(self._on_device_double_clicked)
        self._mid_layout.addWidget(rack_view)
        self._current_view = rack_view

        if self._connect_mode:
            rack_view.set_connect_mode(True)

    # ------------------------------------------------------------------
    # Verbindingsmodus
    # ------------------------------------------------------------------

    def _on_connect_mode_toggled(self, checked: bool):
        """Toolbar Verbinding knop aan/uit."""
        self._connect_mode   = checked
        self._connect_port_a = None
        self._wire_detail.clear()

        if isinstance(self._current_view, RackView):
            self._current_view.set_connect_mode(checked)

        self.set_status(t("msg_connect_select_a") if checked else "Klaar.")

    def _on_port_selected_for_connect(self, port_id: str):
        """Verbindingsmodus: eerste en tweede poortselectie."""
        if self._connect_port_a is None:
            self._connect_port_a = port_id
            port = next((p for p in self._data.get("ports", [])
                         if p["id"] == port_id), None)
            dev  = next((d for d in self._data.get("devices", [])
                         if d["id"] == port["device_id"]), None) if port else None
            label = f"{dev['name']} — {port['name']}" if port and dev else port_id
            self.set_status(
                f"{t('msg_connect_select_a')}  ✓ {label}  →  {t('msg_connect_select_b')}"
            )
        else:
            port_a_id = self._connect_port_a
            port_b_id = port_id
            self._connect_port_a = None

            if port_a_id == port_b_id:
                self.set_status(t("err_same_port"))
                return

            if tracing.port_has_conflict(self._data, port_a_id):
                self.set_status(f"⚠  {t('err_port_in_use')}: poort A")
                return
            if tracing.port_has_conflict(self._data, port_b_id):
                self.set_status(f"⚠  {t('err_port_in_use')}: poort B")
                return

            existing = {c["id"] for c in self._data.get("connections", [])}
            new_id   = f"conn{len(existing) + 1}"
            while new_id in existing:
                new_id += "_"

            self._data.setdefault("connections", []).append({
                "id":         new_id,
                "from_id":    port_a_id,
                "from_type":  "port",
                "to_id":      port_b_id,
                "to_type":    "port",
                "cable_type": "utp_cat6",
                "notes":      "",
            })
            self._save_and_backup()
            # Taak2 — log verbinding aanmaken via klik-klik
            log_change(
                action=ACTION_ADD,
                entity=ENTITY_CONNECTION,
                entity_id=new_id,
                label=f"{port_a_id} → {port_b_id}",
                details={"cable_type": "utp_cat6"}
            )

            self._connect_mode = False
            self._act_connect.setChecked(False)
            if isinstance(self._current_view, RackView):
                self._current_view.set_connect_mode(False)
                self._current_view.refresh(self._data)

            self.set_status(
                f"✓  {t('label_connection')} aangemaakt  ({t('label_cable_type')}: UTP Cat6)"
            )

    def _on_port_clicked(self, port_id: str, device_id: str, side: str):
        """Poort aangeklikt — bereken trace, toon wire_detail en highlight alle trace-poorten."""
        port = next((p for p in self._data.get("ports", []) if p["id"] == port_id), None)
        dev  = next((d for d in self._data.get("devices", []) if d["id"] == device_id), None)
        if not port or not dev:
            return

        self.set_status(
            f"{t('label_port')}: {port.get('name', port_id)}  ·  "
            f"{t('label_device')}: {dev.get('name', device_id)}  ·  "
            f"{t('label_' + side)}"
        )

        conn_id = ""
        for c in self._data.get("connections", []):
            if c.get("from_id") == port_id or c.get("to_id") == port_id:
                conn_id = c.get("id", "")
                break

        # F1 — lege poort: geen verbinding → trace wissen en stoppen
        if not conn_id:
            self._wire_detail.clear()
            if isinstance(self._current_view, RackView):
                self._current_view.clear_trace_highlight()
            return

        steps  = tracing.trace_from_port(self._data, port_id)
        origin = f"{dev.get('name', '')} — {port.get('name', '')} ({side.upper()})"

        self._wire_detail.set_trace(steps, origin, conn_id=conn_id, data=self._data)

        if isinstance(self._current_view, RackView):
            trace_port_ids = [
                s["obj_id"] for s in steps if s["obj_type"] == "port"
            ]
            self._current_view.highlight_trace(trace_port_ids)

    def _on_delete_connection(self, conn_id: str):
        """Verbinding verwijderen na bevestiging — getriggerd vanuit wire_detail_view."""
        from PySide6.QtWidgets import QMessageBox
        conn = next((c for c in self._data.get("connections", [])
                     if c.get("id") == conn_id), None)
        if not conn:
            return
        reply = QMessageBox.warning(
            self, t("menu_delete"),
            t("wire_delete_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        # Taak2 — log verbinding verwijderen (vóór de verwijdering)
        log_change(
            action=ACTION_DELETE,
            entity=ENTITY_CONNECTION,
            entity_id=conn_id,
            label=conn.get("label") or f"{conn.get('from_id', '')} → {conn.get('to_id', '')}"
        )
        self._data["connections"] = [
            c for c in self._data.get("connections", []) if c.get("id") != conn_id
        ]
        self._save_and_backup()
        self._wire_detail.clear()
        if isinstance(self._current_view, RackView):
            self._current_view.refresh(self._data)
        self.set_status(f"✓  {t('msg_connection_deleted')}")

    def _on_edit_connection(self, conn_id: str):
        """Verbinding bewerken — getriggerd vanuit wire_detail_view."""
        conn = next(
            (c for c in self._data.get("connections", []) if c.get("id") == conn_id),
            None
        )
        if not conn:
            return

        conn_with_labels = dict(conn)
        conn_with_labels["_from_label"] = self._resolve_port_label(
            conn.get("from_id", ""), conn.get("from_type", "port")
        )
        conn_with_labels["_to_label"] = self._resolve_port_label(
            conn.get("to_id", ""), conn.get("to_type", "port")
        )

        dlg = ConnectionEditDialog(conn_with_labels, parent=self)
        if dlg.exec() != ConnectionEditDialog.DialogCode.Accepted:
            return

        result = dlg.get_result()
        if result is None:
            return

        old_cable = conn.get("cable_type", "")
        old_label = conn.get("label", "")

        conn["label"]      = result["label"]
        conn["cable_type"] = result["cable_type"]
        conn["notes"]      = result["notes"]

        self._save_and_backup()
        log_change(
            action=ACTION_EDIT,
            entity=ENTITY_CONNECTION,
            entity_id=conn["id"],
            label=conn.get("label") or f"{conn.get('from_id', '')} → {conn.get('to_id', '')}",
            details={
                "from": {"cable_type": old_cable, "label": old_label},
                "to":   {"cable_type": result["cable_type"], "label": result["label"]}
            }
        )

        self._wire_detail.refresh_info(self._data)
        self.set_status(f"✓  {t('msg_connection_updated')}")

    def _resolve_port_label(self, obj_id: str, obj_type: str) -> str:
        """Zet een poort- of wandpunt-ID om naar een leesbaar label."""
        if obj_type in ("port", ""):
            port = next(
                (p for p in self._data.get("ports", []) if p.get("id") == obj_id),
                None
            )
            if port:
                dev = next(
                    (d for d in self._data.get("devices", [])
                     if d.get("id") == port.get("device_id")), None
                )
                dev_name = dev["name"] if dev else "?"
                return f"{dev_name}  /  {port.get('name', obj_id)}"
        if obj_type == "wall_outlet":
            wo = next(
                (w for w in self._data.get("wall_outlets", [])
                 if w.get("id") == obj_id), None
            )
            if wo:
                return f"🌐  {wo.get('name', obj_id)}"
        return obj_id

    def _on_navigate_to_rack(self, rack_id: str, port_ids: list):
        """E5 — Cross-rack navigatie vanuit wire_detail."""
        for site in self._data.get("sites", []):
            for room in site.get("rooms", []):
                for rack in room.get("racks", []):
                    if rack["id"] == rack_id:
                        self._show_rack_view(rack, room, site)
                        self._select_tree_item_by_id(rack_id, "rack")
                        self.set_status(
                            f"🗄  {rack['name']}  ·  {room['name']}  ·  {site['name']}"
                        )
                        if isinstance(self._current_view, RackView):
                            self._current_view.highlight_trace(port_ids)
                        return

    def _on_port_context_menu(self, port_id: str, global_pos):
        """Rechtermuisklik op een poort — toon context menu."""
        from PySide6.QtWidgets import QMenu
        port = next((p for p in self._data.get("ports", [])
                     if p["id"] == port_id), None)
        dev  = next((d for d in self._data.get("devices", [])
                     if d["id"] == port["device_id"]), None) if port else None
        if not port or not dev:
            return

        is_connected = any(
            c for c in self._data.get("connections", [])
            if c.get("from_id") == port_id or c.get("to_id") == port_id
        )

        port_label = f"{dev.get('name', '')} — {port.get('name', '')} ({port.get('side','').upper()})"

        menu = QMenu(self)
        act_outlet = menu.addAction(t("ctx_connect_to_outlet"))

        act_disconnect = None
        if is_connected:
            menu.addSeparator()
            act_disconnect = menu.addAction(t("ctx_disconnect_port"))

        chosen = menu.exec(global_pos)
        if chosen is None:
            return

        if chosen == act_outlet:
            dlg = ConnectToOutletDialog(
                self._data, port_id, port_label, parent=self
            )
            if dlg.exec() and dlg.get_result():
                conn = dlg.get_result()
                self._data.setdefault("connections", []).append(conn)
                self._save_and_backup()
                outlet = next(
                    (wo for s in self._data.get("sites", [])
                     for r in s.get("rooms", [])
                     for wo in r.get("wall_outlets", [])
                     if wo["id"] == conn["to_id"]),
                    None
                )
                outlet_name = outlet["name"] if outlet else conn["to_id"]
                log_change(
                    action=ACTION_ADD,
                    entity=ENTITY_CONNECTION,
                    entity_id=conn["id"],
                    label=f"{port_label} → 🌐 {outlet_name}",
                    details={"cable_type": conn["cable_type"]}
                )
                if isinstance(self._current_view, RackView):
                    self._current_view.refresh(self._data)
                steps = tracing.trace_from_port(self._data, port_id)
                self._wire_detail.set_trace(steps, port_label, data=self._data)
                self.set_status(f"✓  {port_label}  ►  🌐  {outlet_name}")

        elif chosen == act_disconnect:
            conn = next(
                (c for c in self._data.get("connections", [])
                 if c.get("from_id") == port_id or c.get("to_id") == port_id),
                None
            )
            if conn:
                self._on_delete_connection(conn["id"])

    # ------------------------------------------------------------------
    # Data opzoeken
    # ------------------------------------------------------------------

    def _find_site(self, site_id: str) -> dict | None:
        for s in self._data.get("sites", []):
            if s["id"] == site_id:
                return s
        return None

    def _find_room(self, room_id: str) -> dict | None:
        for s in self._data.get("sites", []):
            for r in s.get("rooms", []):
                if r["id"] == room_id:
                    return r
        return None

    def _find_rack(self, rack_id: str) -> dict | None:
        for s in self._data.get("sites", []):
            for r in s.get("rooms", []):
                for rack in r.get("racks", []):
                    if rack["id"] == rack_id:
                        return rack
        return None

    def _room_tooltip(self, room: dict, site: dict) -> str:
        parts = []
        floor = room.get("floor", "")
        place = room.get("place", "")
        if floor:
            parts.append(f"{t('label_floor')}: {floor}")
        if place:
            parts.append(f"{t('label_place')}: {place}")
        parts.append(f"{t('label_site')}: {site.get('name', '')}")
        n_racks   = len(room.get("racks", []))
        n_outlets = len(room.get("wall_outlets", []))
        if n_racks:
            parts.append(f"{n_racks} {t('label_rack').lower()}{'s' if n_racks != 1 else ''}")
        if n_outlets:
            parts.append(f"{n_outlets} {t('tree_wall_outlets').lower()}")
        return "  ·  ".join(parts)

    def _room_status_label(self, room: dict, site: dict) -> str:
        parts = [room.get("name", "")]
        floor = room.get("floor", "")
        place = room.get("place", "")
        if floor:
            parts.append(f"+{floor}")
        if place:
            parts.append(place)
        parts.append(site.get("name", ""))
        return "  ·  ".join(parts)

    # ------------------------------------------------------------------
    # CRUD — Nieuw / Bewerken / Verwijderen / Dupliceren
    # ------------------------------------------------------------------

    def _selected_tree_data(self) -> dict | None:
        item = self._tree.currentItem()
        if not item:
            return None
        return item.data(0, Qt.ItemDataRole.UserRole)

    def _on_new(self):
        from PySide6.QtWidgets import QMenu
        data      = self._selected_tree_data()
        item_type = data.get("type") if data else None

        menu = QMenu(self)
        act_site   = menu.addAction(f"📍  {t('label_site')}")
        act_room   = menu.addAction(f"🚪  {t('label_room')}")
        act_rack   = menu.addAction(f"🗄  {t('label_rack')}")
        act_device = menu.addAction(f"💻  {t('label_device')}")
        act_outlet = menu.addAction(f"🌐  {t('label_wall_outlet')}")

        has_site   = item_type in (_TYPE_SITE, _TYPE_ROOM, _TYPE_RACK, _TYPE_OUTLETS, _TYPE_OUTLET)
        has_room   = item_type in (_TYPE_ROOM, _TYPE_RACK, _TYPE_OUTLETS, _TYPE_OUTLET)
        has_rack   = item_type == _TYPE_RACK
        act_room.setEnabled(has_site)
        act_rack.setEnabled(has_room)
        act_device.setEnabled(has_rack)
        act_outlet.setEnabled(has_room)

        chosen = menu.exec(self.cursor().pos())

        if chosen == act_site:
            self._new_site()
        elif chosen == act_room and has_site:
            site_id = data["id"] if item_type == _TYPE_SITE else data["site_id"]
            self._new_room(site_id)
        elif chosen == act_rack and has_room:
            room_id = data["id"] if item_type == _TYPE_ROOM else data["room_id"]
            self._new_rack(room_id)
        elif chosen == act_device and has_rack:
            self._new_device_in_rack(data["id"])
        elif chosen == act_outlet and has_room:
            room_id = data["id"] if item_type == _TYPE_ROOM else data["room_id"]
            self._new_wall_outlet(room_id)

    def _attach_new_menu(self):
        from PySide6.QtWidgets import QMenu, QToolButton
        menu = QMenu(self)
        menu.addAction(f"📍  {t('label_site')}",       self._new_site)
        menu.addAction(f"🚪  {t('label_room')}",       self._new_room_from_menu)
        menu.addAction(f"🗄  {t('label_rack')}",       self._new_rack_from_menu)
        menu.addAction(f"🌐  {t('label_wall_outlet')}", self._new_outlet_from_menu)
        tb_widget = self._tb.widgetForAction(self._act_new)
        if isinstance(tb_widget, QToolButton):
            tb_widget.setMenu(menu)
            tb_widget.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)

    def _new_room_from_menu(self):
        data      = self._selected_tree_data()
        item_type = data.get("type") if data else None
        if item_type == _TYPE_SITE:
            self._new_room(data["id"])
        elif item_type in (_TYPE_ROOM, _TYPE_RACK, _TYPE_OUTLETS):
            site_id = data.get("site_id", "")
            if site_id:
                self._new_room(site_id)
        else:
            self.set_status(t("err_select_site_for_room"))

    def _new_rack_from_menu(self):
        data      = self._selected_tree_data()
        item_type = data.get("type") if data else None
        if item_type == _TYPE_ROOM:
            self._new_rack(data["id"])
        elif item_type in (_TYPE_RACK, _TYPE_OUTLETS):
            self._new_rack(data["room_id"])
        else:
            self.set_status(t("err_select_room_for_rack"))

    def _new_outlet_from_menu(self):
        data      = self._selected_tree_data()
        item_type = data.get("type") if data else None
        if item_type == _TYPE_ROOM:
            self._new_wall_outlet(data["id"])
        elif item_type in (_TYPE_RACK, _TYPE_OUTLETS):
            self._new_wall_outlet(data["room_id"])
        else:
            self.set_status(t("err_select_room_for_outlet"))

    def _on_new_site_explicit(self):
        self._new_site()

    def _new_site(self):
        dlg = SiteDialog(parent=self)
        if dlg.exec() and dlg.get_result():
            obj = dlg.get_result()
            obj["id"] = self._gen_id("site")
            self._data.setdefault("sites", []).append(obj)
            self._save_and_backup()
            self._populate_tree()
            self.set_status(f"✓  {t('label_site')} '{obj['name']}' aangemaakt.")

    def _new_room(self, site_id: str):
        dlg = RoomDialog(parent=self, site_id=site_id)
        if dlg.exec() and dlg.get_result():
            obj = dlg.get_result()
            obj["id"] = self._gen_id("room")
            site = self._find_site(site_id)
            if site:
                site.setdefault("rooms", []).append(obj)
                self._save_and_backup()
                self._populate_tree()
                self.set_status(f"✓  {t('label_room')} '{obj['name']}' aangemaakt.")

    def _new_rack(self, room_id: str):
        dlg = RackDialog(parent=self, room_id=room_id)
        if dlg.exec() and dlg.get_result():
            obj = dlg.get_result()
            obj["id"] = self._gen_id("rack")
            room = self._find_room(room_id)
            if room:
                room.setdefault("racks", []).append(obj)
                self._save_and_backup()
                self._populate_tree()
                self.set_status(f"✓  {t('label_rack')} '{obj['name']}' aangemaakt.")

    def _new_wall_outlet(self, room_id: str):
        endpoints = self._data.get("endpoints", [])
        room      = self._find_room(room_id)
        existing  = room.get("wall_outlets", []) if room else []
        dlg = WallOutletDialog(parent=self, room_id=room_id,
                               endpoints=endpoints, existing_outlets=existing)
        if dlg.exec() and dlg.get_result():
            self._data["endpoints"] = dlg.get_endpoints_result()
            obj = dlg.get_result()
            obj["id"] = self._gen_id("wo")
            room = self._find_room(room_id)
            if room:
                room.setdefault("wall_outlets", []).append(obj)
                vlan_val = dlg.get_vlan()
                if vlan_val and obj.get("id"):
                    self._propagate_vlan_after_save(obj["id"], "wall_outlet", vlan_val)
                self._save_and_backup()
                self._populate_tree()
                self.set_status(f"✓  {t('label_wall_outlet')} '{obj['name']}' aangemaakt.")

    def _on_edit(self):
        data = self._selected_tree_data()
        if not data:
            self.set_status(t("err_no_selection"))
            return
        item_type = data.get("type")

        if item_type == _TYPE_SITE:
            site = self._find_site(data["id"])
            if not site:
                return
            dlg = SiteDialog(parent=self, site=site)
            if dlg.exec() and dlg.get_result():
                site.update(dlg.get_result())
                self._save_and_backup()
                self._populate_tree()
                self._select_tree_item_by_id(data["id"])
                self.set_status(f"✓  {t('label_site')} '{site['name']}' bijgewerkt.")

        elif item_type == _TYPE_ROOM:
            room = self._find_room(data["id"])
            if not room:
                return
            dlg = RoomDialog(parent=self, room=room, site_id=data["site_id"])
            if dlg.exec() and dlg.get_result():
                room.update(dlg.get_result())
                self._save_and_backup()
                self._populate_tree()
                self._select_tree_item_by_id(data["id"])
                self.set_status(f"✓  {t('label_room')} '{room['name']}' bijgewerkt.")

        elif item_type == _TYPE_RACK:
            from PySide6.QtWidgets import QMenu
            menu = QMenu(self)
            menu.addAction(t('edit_rack_self'),
                           lambda: self._edit_rack_direct(data))
            menu.addAction(t('edit_device_in_rack'),
                           self._on_edit_device)
            menu.exec(self.cursor().pos())

        else:
            self.set_status(t("err_select_for_edit"))

    def _edit_rack_direct(self, data: dict):
        rack = self._find_rack(data["id"])
        if not rack:
            return
        dlg = RackDialog(parent=self, rack=rack, room_id=data["room_id"])
        if dlg.exec() and dlg.get_result():
            rack.update(dlg.get_result())
            self._save_and_backup()
            self._populate_tree()
            self._select_tree_item_by_id(data["id"])
            if isinstance(self._current_view, RackView):
                room = self._find_room(data["room_id"])
                site = self._find_site(data["site_id"])
                if room and site:
                    self._show_rack_view(rack, room, site)
            self.set_status(f"✓  {t('label_rack')} '{rack['name']}' bijgewerkt.")

    def _on_delete(self):
        from PySide6.QtWidgets import QMessageBox
        data = self._selected_tree_data()
        if not data:
            self.set_status(t("err_no_selection"))
            return

        reply = QMessageBox.question(
            self, t("menu_delete"), t("msg_confirm_delete"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        item_type = data.get("type")

        if item_type == _TYPE_SITE:
            self._data["sites"] = [
                s for s in self._data.get("sites", []) if s["id"] != data["id"]
            ]
            self._save_and_backup()
            self._populate_tree()
            self.set_status(f"✓  {t('label_site')} verwijderd.")

        elif item_type == _TYPE_ROOM:
            site = self._find_site(data["site_id"])
            if site:
                site["rooms"] = [r for r in site.get("rooms", []) if r["id"] != data["id"]]
                self._save_and_backup()
                self._populate_tree()
                self.set_status(f"✓  {t('label_room')} verwijderd.")

        elif item_type == _TYPE_RACK:
            from PySide6.QtWidgets import QMenu
            menu = QMenu(self)
            menu.addAction(t('delete_rack_self'),
                           lambda: self._delete_rack_direct(data))
            menu.addAction(t('delete_device_in_rack'),
                           self._on_delete_device)
            menu.exec(self.cursor().pos())
            return

        elif item_type == _TYPE_OUTLET:
            room = self._find_room(data["room_id"])
            if room:
                room["wall_outlets"] = [
                    wo for wo in room.get("wall_outlets", []) if wo["id"] != data["id"]
                ]
                self._data["connections"] = [
                    c for c in self._data.get("connections", [])
                    if not (c.get("from_id") == data["id"] or c.get("to_id") == data["id"])
                ]
                self._save_and_backup()
                self._populate_tree()
                self.set_status(f"✓  {t('label_wall_outlet')} verwijderd.")

        elif item_type == _TYPE_OUTLETS:
            self.set_status(t("err_select_outlet"))

    def _on_edit_device(self):
        data = self._selected_tree_data()
        if not data or data.get("type") != _TYPE_RACK:
            self.set_status(t("err_select_rack_for_device"))
            return
        rack = self._find_rack(data["id"])
        if not rack or not rack.get("slots"):
            self.set_status(t("err_rack_no_devices"))
            return

        dev_map   = {d["id"]: d for d in self._data.get("devices", [])}
        dev_names = []
        dev_ids   = []
        for slot in rack.get("slots", []):
            dev = dev_map.get(slot.get("device_id", ""))
            if dev:
                dev_names.append(f"{dev['name']}  ({t('device_' + dev['type'])})")
                dev_ids.append(dev["id"])

        if not dev_names:
            self.set_status(t("err_rack_no_devices"))
            return

        from PySide6.QtWidgets import QInputDialog
        chosen, ok = QInputDialog.getItem(
            self, t("menu_edit"), f"{t('label_device')} kiezen:",
            dev_names, 0, False
        )
        if not ok:
            return

        dev_id = dev_ids[dev_names.index(chosen)]
        device = dev_map[dev_id]

        dlg = DeviceDialog(parent=self, device=device)
        if dlg.exec() and dlg.get_result():
            device.update(dlg.get_result())
            new_front = device.get("front_ports", 0)
            new_sfp   = device.get("sfp_ports",   0)

            existing_nums = {
                p["number"] for p in self._data.get("ports", [])
                if p["device_id"] == device["id"] and p["side"] == "front"
            }
            for i in range(1, new_sfp + 1):
                sfp_num = new_front + i
                if sfp_num not in existing_nums:
                    self._data.setdefault("ports", []).append({
                        "id":        self._gen_id("p"),
                        "device_id": device["id"],
                        "name":      f"SFP {i}",
                        "side":      "front",
                        "number":    sfp_num,
                    })

            self._save_and_backup()
            log_change(
                action=ACTION_EDIT,
                entity=ENTITY_DEVICE,
                entity_id=device["id"],
                label=f"{device['type']} — {device['name']}"
            )
            if isinstance(self._current_view, RackView):
                self._current_view.refresh(self._data)
            self.set_status(f"✓  {t('msg_device_updated')}: {device['name']}.")

    def _on_delete_device(self):
        from PySide6.QtWidgets import QInputDialog, QMessageBox
        data = self._selected_tree_data()
        if not data or data.get("type") != _TYPE_RACK:
            self.set_status(t("err_select_rack_for_device"))
            return
        rack = self._find_rack(data["id"])
        if not rack or not rack.get("slots"):
            self.set_status(t("err_rack_no_devices"))
            return

        dev_map   = {d["id"]: d for d in self._data.get("devices", [])}
        dev_names = []
        dev_ids   = []
        for slot in rack.get("slots", []):
            dev = dev_map.get(slot.get("device_id", ""))
            if dev:
                dev_names.append(f"{dev['name']}  ({t('device_' + dev['type'])})")
                dev_ids.append(dev["id"])

        if not dev_names:
            self.set_status(t("err_rack_no_devices"))
            return

        chosen, ok = QInputDialog.getItem(
            self, t("menu_delete"), f"{t('label_device')} kiezen:",
            dev_names, 0, False
        )
        if not ok:
            return

        dev_id = dev_ids[dev_names.index(chosen)]
        device = dev_map[dev_id]

        reply = QMessageBox.warning(
            self, t("menu_delete"),
            t('delete_device_confirm'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        log_change(
            action=ACTION_DELETE,
            entity=ENTITY_DEVICE,
            entity_id=dev_id,
            label=f"{device['type']} — {device['name']}"
        )
        port_ids = {p["id"] for p in self._data.get("ports", [])
                    if p["device_id"] == dev_id}
        self._data["ports"] = [
            p for p in self._data.get("ports", []) if p["device_id"] != dev_id
        ]
        self._data["connections"] = [
            c for c in self._data.get("connections", [])
            if c.get("from_id") not in port_ids and c.get("to_id") not in port_ids
        ]
        rack["slots"] = [
            s for s in rack.get("slots", []) if s.get("device_id") != dev_id
        ]
        self._data["devices"] = [
            d for d in self._data.get("devices", []) if d["id"] != dev_id
        ]

        self._save_and_backup()
        if isinstance(self._current_view, RackView):
            self._current_view.refresh(self._data)
        self._wire_detail.clear()
        self.set_status(f"✓  {t('msg_device_deleted')}: {device['name']}.")

    def _delete_rack_direct(self, data: dict):
        from PySide6.QtWidgets import QMessageBox
        rack = self._find_rack(data["id"])
        if not rack:
            return
        reply = QMessageBox.warning(
            self, t("menu_delete"),
            t('delete_rack_confirm'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        room = self._find_room(data["room_id"])
        if room:
            room["racks"] = [r for r in room.get("racks", []) if r["id"] != data["id"]]
            self._save_and_backup()
            self._populate_tree()
            self.set_status(f"✓  {t('msg_rack_deleted')}: {rack['name']}.")

    def _new_device_in_rack(self, rack_id: str):
        rack = self._find_rack(rack_id)
        if not rack:
            return
        dlg = PlaceDeviceDialog(parent=self, rack=rack, data=self._data)
        if dlg.exec() and dlg.get_result():
            result = dlg.get_result()
            device = result["device"]
            slot   = result["slot"]

            device["id"] = self._gen_id("dev")
            slot["id"]   = self._gen_id("slot")
            slot["rack_id"]   = rack_id
            slot["device_id"] = device["id"]

            self._data.setdefault("devices", []).append(device)
            self._generate_ports(device)
            rack.setdefault("slots", []).append(slot)

            self._save_and_backup()
            log_change(
                action=ACTION_ADD,
                entity=ENTITY_DEVICE,
                entity_id=device["id"],
                label=f"{device['type']} — {device['name']} ({rack['name']})"
            )

            if isinstance(self._current_view, RackView):
                self._current_view.refresh(self._data)
            self._populate_tree()

            self.set_status(f"✓  {t('label_device')} '{device['name']}' toegevoegd aan {rack['name']}.")

    def _generate_ports(self, device: dict):
        dev_id      = device["id"]
        front_count = device.get("front_ports", 0)
        back_count  = device.get("back_ports",  0)
        sfp_count   = device.get("sfp_ports",   0)

        for i in range(1, front_count + 1):
            self._data.setdefault("ports", []).append({
                "id":        self._gen_id("p"),
                "device_id": dev_id,
                "name":      f"Port {i}",
                "side":      "front",
                "number":    i,
            })

        for i in range(1, sfp_count + 1):
            sfp_num = front_count + i
            self._data.setdefault("ports", []).append({
                "id":        self._gen_id("p"),
                "device_id": dev_id,
                "name":      f"SFP {i}",
                "side":      "front",
                "number":    sfp_num,
            })

        for i in range(1, back_count + 1):
            self._data.setdefault("ports", []).append({
                "id":        self._gen_id("p"),
                "device_id": dev_id,
                "name":      f"Port {i}",
                "side":      "back",
                "number":    i,
            })

    def _on_duplicate(self):
        data = self._selected_tree_data()
        if not data or data.get("type") != _TYPE_RACK:
            self.set_status("Selecteer een rack en gebruik Dupliceren via het rack zelf. (Klik eerst op een rack)")
            return

        rack = self._find_rack(data["id"])
        if not rack or not rack.get("slots"):
            self.set_status(t("err_rack_no_devices"))
            return

        from PySide6.QtWidgets import QInputDialog
        dev_map   = {d["id"]: d for d in self._data.get("devices", [])}
        dev_names = []
        dev_ids   = []
        for slot in rack.get("slots", []):
            dev = dev_map.get(slot.get("device_id", ""))
            if dev:
                dev_names.append(f"{dev['name']}  ({t('device_' + dev['type'])})")
                dev_ids.append(dev["id"])

        if not dev_names:
            self.set_status("Geen devices gevonden in dit rack.")
            return

        chosen, ok = QInputDialog.getItem(
            self, t("menu_duplicate"), t("label_device") + ":",
            dev_names, 0, False
        )
        if not ok:
            return

        idx    = dev_names.index(chosen)
        src_id = dev_ids[idx]
        src    = dev_map[src_id]

        new_dev = {
            "id":          self._gen_id("dev"),
            "name":        src["name"] + " (kopie)",
            "type":        src["type"],
            "front_ports": src.get("front_ports", 0),
            "back_ports":  src.get("back_ports",  0),
            "brand":       src.get("brand",  ""),
            "model":       src.get("model",  ""),
            "ip":          "",
            "mac":         "",
            "serial":      "",
            "notes":       src.get("notes",  ""),
        }
        self._data.setdefault("devices", []).append(new_dev)
        self._generate_ports(new_dev)

        dlg = PlaceDeviceDialog(parent=self, rack=rack, data=self._data)
        dlg._name.setText(new_dev["name"])
        dlg._ddl_type.setCurrentIndex(
            dlg._ddl_type.findData(new_dev["type"])
        )
        dlg._front_ports.setValue(new_dev["front_ports"])
        dlg._back_ports.setValue(new_dev["back_ports"])

        if dlg.exec() and dlg.get_result():
            result = dlg.get_result()
            slot   = result["slot"]
            slot["id"]        = self._gen_id("slot")
            slot["rack_id"]   = rack["id"]
            slot["device_id"] = new_dev["id"]
            rack.setdefault("slots", []).append(slot)
            self._save_and_backup()
            log_change(
                action=ACTION_ADD,
                entity=ENTITY_DEVICE,
                entity_id=new_dev["id"],
                label=f"{new_dev['type']} — {new_dev['name']} ({rack['name']})",
                details={"duplicated_from": src_id}
            )
            if isinstance(self._current_view, RackView):
                self._current_view.refresh(self._data)
            self.set_status(f"✓  '{new_dev['name']}' gedupliceerd.")
        else:
            self._data["devices"] = [
                d for d in self._data["devices"] if d["id"] != new_dev["id"]
            ]
            self._data["ports"] = [
                p for p in self._data.get("ports", []) if p["device_id"] != new_dev["id"]
            ]

    # ------------------------------------------------------------------
    # Help — H1
    # ------------------------------------------------------------------

    def _on_device_double_clicked(self, device_id: str):
        """Dubbelklik op device — toon readonly info popup."""
        device = next((d for d in self._data.get("devices", [])
                       if d["id"] == device_id), None)
        if not device:
            return
        rack = room = site = None
        for s in self._data.get("sites", []):
            for r in s.get("rooms", []):
                for ra in r.get("racks", []):
                    for slot in ra.get("slots", []):
                        if slot.get("device_id") == device_id:
                            rack, room, site = ra, r, s
        dlg = DeviceInfoDialog(
            parent=self, device=device, data=self._data,
            rack=rack or {}, room=room or {}, site=site or {}
        )
        dlg.exec()

    def _on_vlan_report(self):
        """VLAN rapport knop — toon VlanReportView in midden paneel."""
        self._show_vlan_report()
        self.set_status("🔷  VLAN rapport")

    def _show_vlan_report(self):
        from app.gui.vlan_report_view import VlanReportView
        while self._mid_layout.count():
            item = self._mid_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        view = VlanReportView(self._data, parent=self._mid_frame)
        self._mid_layout.addWidget(view)
        self._current_view = view

    def _on_vlan_manager(self):
        from app.gui.vlan_manager_window import VlanManagerWindow
        dlg = VlanManagerWindow(parent=self)
        dlg.exec()
        # Herlaad VLAN rapport als dat zichtbaar is
        if self._current_view and hasattr(self._current_view, "refresh"):
            try:
                from app.gui.vlan_report_view import VlanReportView
                if isinstance(self._current_view, VlanReportView):
                    self._current_view.refresh(self._data)
            except Exception:
                pass

    def _propagate_vlan_after_save(self, start_id: str, start_type: str, vlan_id: int | None):
        """
        Propageer VLAN naar de volledige trace na opslaan van een poort of wandpunt.
        Toont waarschuwingsdialog bij conflicten.
        """
        if vlan_id is None:
            return

        trace = vlan_service.collect_trace_objects(self._data, start_id, start_type)
        port_ids   = trace["port_ids"]
        outlet_ids = trace["outlet_ids"]

        conflicts = vlan_service.propagate_vlan(
            self._data, port_ids, outlet_ids, vlan_id
        )

        has_conflicts = (conflicts["port_conflicts"] or conflicts["outlet_conflicts"])

        if has_conflicts:
            dlg = VlanPropagationDialog(
                parent=self,
                new_vlan=vlan_id,
                port_conflicts=conflicts["port_conflicts"],
                outlet_conflicts=conflicts["outlet_conflicts"],
            )
            if dlg.exec() != VlanPropagationDialog.DialogCode.Accepted:
                return   # gebruiker geannuleerd — geen propagatie

        vlan_service.apply_vlan(self._data, port_ids, outlet_ids, vlan_id)
        self._save_and_backup()

        if isinstance(self._current_view, __import__(
                "app.gui.rack_view", fromlist=["RackView"]).RackView):
            self._current_view.refresh(self._data)

    def _on_report_bug(self):
        dlg = BugReportDialog(parent=self)
        dlg._type_select.setCurrentIndex(0)
        dlg.exec()

    def _on_report_feature(self):
        dlg = BugReportDialog(parent=self)
        dlg._type_select.setCurrentIndex(1)
        dlg.exec()

    def _on_show_cases(self):
        dlg = GithubCasesDialog(parent=self)
        dlg.exec()

    def _on_help(self):
        dlg = HelpWindow(parent=self)
        dlg.exec()

    def _on_about(self):
        dlg = HelpWindow(parent=self)
        dlg.set_tab(2)
        dlg.exec()

    # ------------------------------------------------------------------
    # Instellingen
    # ------------------------------------------------------------------

    def _on_settings(self):
        dlg = SettingsWindow(parent=self)
        dlg.language_changed.connect(self.reload_ui_labels)
        dlg.exec()

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def _on_export(self):
        from PySide6.QtWidgets import QFileDialog
        import os
        suggested = import_export_service.suggested_filename()
        last = get_last_folder("export_json")
        if last:
            suggested = os.path.join(last, os.path.basename(suggested))
        filepath, _ = QFileDialog.getSaveFileName(
            self, t("menu_export"), suggested,
            "JSON bestanden (*.json)"
        )
        if not filepath:
            return
        try:
            ok = import_export_service.export_to_file(self._data, filepath)
            if ok:
                set_last_folder("export_json", os.path.dirname(filepath))
                log_info(f"Export naar: {filepath}")
                self.set_status(f"✓  {t('msg_exported_to')} {filepath}")
            else:
                log_warning(f"Export mislukt: {filepath}")
                self.set_status(f"⚠  {t('msg_export_failed')}")
        except Exception as e:
            log_error("Export fout", e)
            self.set_status(f"⚠  {t('msg_export_failed')}")

    def _on_export_image(self):
        if not self._current_view:
            self.set_status(t("err_no_view_to_export"))
            return

        import datetime
        datum = datetime.date.today().strftime("%Y%m%d")
        suggested, export_fn = self._resolve_export_context(datum, "png")
        if not export_fn:
            return

        from PySide6.QtWidgets import QFileDialog
        import os
        start_dir = get_last_folder("export_image") or self._export_folder()
        if start_dir:
            suggested = os.path.join(start_dir, os.path.basename(suggested))
        filepath, _ = QFileDialog.getSaveFileName(
            self, t("menu_export_image"), suggested,
            "PNG afbeelding (*.png);;JPEG afbeelding (*.jpg *.jpeg)"
        )
        if not filepath:
            return

        ok, err = export_fn(filepath)
        if ok:
            set_last_folder("export_image", os.path.dirname(filepath))
            log_info(f"Afbeelding geëxporteerd: {filepath}")
            self.set_status(f"✓  {t('msg_image_exported')}: {filepath}")
            import os; os.startfile(filepath)
        else:
            log_warning(f"Afbeelding export mislukt: {err}")
            self.set_status(f"⚠  {t('msg_image_export_failed')}: {err}")

    def _on_export_pdf(self):
        if not self._current_view:
            self.set_status(t("err_no_view_to_export"))
            return

        import datetime
        datum = datetime.date.today().strftime("%Y%m%d")
        suggested, export_fn = self._resolve_export_context(datum, "pdf")
        if not export_fn:
            return

        from PySide6.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getSaveFileName(
            self, t("menu_export_pdf"), suggested,
            "PDF document (*.pdf)"
        )
        if not filepath:
            return

        ok, err = export_fn(filepath)
        if ok:
            log_info(f"PDF geëxporteerd: {filepath}")
            self.set_status(f"✓  {t('msg_pdf_exported')}: {filepath}")
        else:
            log_warning(f"PDF export mislukt: {err}")
            self.set_status(f"⚠  {t('msg_pdf_export_failed')}: {err}")

    def _on_export_report(self):
        import datetime
        from PySide6.QtWidgets import QFileDialog

        datum     = datetime.date.today().strftime("%Y%m%d")
        suggested = f"networkmap_rapport_{datum}.docx"

        import os
        start_dir = get_last_folder("export_report") or self._export_folder()
        if start_dir:
            suggested = os.path.join(start_dir, suggested)
        filepath, _ = QFileDialog.getSaveFileName(
            self, t("menu_export_report"), suggested,
            "Word document (*.docx)"
        )
        if not filepath:
            return

        ok, err = report_generator.render_report_docx(self._data, filepath)
        if ok:
            set_last_folder("export_report", os.path.dirname(filepath))
            log_info(f"Rapport geëxporteerd: {filepath}")
            self.set_status(f"✓  {t('msg_report_exported')}: {filepath}")
            import os; os.startfile(filepath)
        else:
            log_warning(f"Rapport export mislukt: {err}")
            self.set_status(f"⚠  {t('msg_report_export_failed')}: {err}")

    def _resolve_export_context(self, datum: str, ext: str):
        if isinstance(self._current_view, RackView):
            rack = self._current_view._rack
            room = self._current_view._room
            site = self._current_view._site
            name = rack.get("name", "rack").replace(" ", "_")
            suggested = f"rack_{name}_{datum}.{ext}"
            if ext == "pdf":
                fn = lambda fp: export_renderer.render_rack_pdf(rack, room, site, self._data, fp)
            else:
                fn = lambda fp: export_renderer.render_rack_image(rack, room, site, self._data, fp)
            return suggested, fn

        elif isinstance(self._current_view, WallOutletView):
            mode = self._current_view._mode
            if mode == "site":
                obj  = self._current_view._site
                name = obj.get("name", "site").replace(" ", "_")
                suggested = f"wandpunten_site_{name}_{datum}.{ext}"
            else:
                obj  = self._current_view._room
                name = obj.get("name", "ruimte").replace(" ", "_")
                suggested = f"wandpunten_{name}_{datum}.{ext}"
            if ext == "pdf":
                fn = lambda fp: export_renderer.render_outlets_pdf(obj, self._data, mode, fp)
            else:
                fn = lambda fp: export_renderer.render_outlets_image(obj, self._data, mode, fp)
            return suggested, fn

        else:
            self.set_status(t("err_no_view_to_export"))
            return None, None

    def _export_folder(self) -> str:
        return self._settings.get("ui", {}).get("export_folder", "")

    def _on_import(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox, QInputDialog
        import os
        last = get_last_folder("import_json")
        filepath, _ = QFileDialog.getOpenFileName(
            self, t("menu_import"), last,
            "JSON bestanden (*.json)"
        )
        if not filepath:
            return
        set_last_folder("import_json", os.path.dirname(filepath))

        modus, ok = QInputDialog.getItem(
            self, t("menu_import"),
            t("import_mode_label") + ":",
            [f"{t('import_mode_merge')} — nieuwe objecten toevoegen",
             f"{t('import_mode_replace')}  — huidige data overschrijven"],
            0, False
        )
        if not ok:
            return

        try:
            from app.services.data_integrity import validate_and_repair
            if t("import_mode_replace") in modus:
                reply = QMessageBox.warning(
                    self, t("menu_import"),
                    t("msg_confirm_delete"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
                data, err = import_export_service.import_replace(filepath)
                if data is None:
                    log_warning(f"Import replace mislukt: {err}")
                    self.set_status(f"⚠  {t('msg_import_fail')}: {err}")
                    return
                self._data = data
                self._data, _repaired, _rapport = validate_and_repair(self._data)
                if _repaired:
                    for regel in _rapport:
                        log_info(f"[data_integrity] {regel}")
                self._save_and_backup()
                self._populate_tree()
                log_info(f"Import replace: {filepath}")
                self.set_status(f"✓  {t('msg_import_replace_done')}")
            else:
                data, err, stats = import_export_service.import_merge(
                    filepath, self._data
                )
                if data is None:
                    log_warning(f"Import merge mislukt: {err}")
                    self.set_status(f"⚠  {t('msg_import_fail')}: {err}")
                    return
                self._data = data
                self._data, _repaired, _rapport = validate_and_repair(self._data)
                if _repaired:
                    for regel in _rapport:
                        log_info(f"[data_integrity] {regel}")
                self._save_and_backup()
                self._populate_tree()
                log_info(f"Import merge: {filepath} — {stats}")
                self.set_status(
                    t("msg_import_merge_done").format(
                        added=stats["added"], skipped=stats["skipped"]
                    )
                )
        except Exception as e:
            log_error("Import fout", e)
            self.set_status(f"⚠  {t('msg_import_fail')}")

    # ------------------------------------------------------------------
    # Zoeken
    # ------------------------------------------------------------------

    def _on_search(self):
        if not hasattr(self, "_search_win") or not self._search_win:
            self._search_win = SearchWindow(self._data, parent=self)
            self._search_win.result_selected.connect(self._on_search_result)
        else:
            self._search_win.update_data(self._data)
        self._search_win.show()
        self._search_win.raise_()
        self._search_win.activateWindow()

    def _on_outlet_locator(self):
        self._show_outlet_locator(room_id=None)
        self.set_status(f"🌐  {t('menu_outlet_locator')}")

    def _show_outlet_locator(self, room_id: str = None):
        if isinstance(self._current_view, OutletLocatorView):
            if room_id:
                self._current_view.set_room(room_id)
            self._current_view.refresh(self._data)
            return

        while self._mid_layout.count():
            item = self._mid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        view = OutletLocatorView(self._data, parent=self._mid_frame)
        view.outlet_selected.connect(self._on_locator_outlet_selected)
        view.room_navigate_requested.connect(self._on_locator_room_navigate)
        self._mid_layout.addWidget(view)
        self._current_view = view

        if room_id:
            view.set_room(room_id)

    def _on_locator_outlet_selected(self, outlet_id: str, steps: list):
        outlet = next(
            (wo for site in self._data.get("sites", [])
             for room in site.get("rooms", [])
             for wo in room.get("wall_outlets", [])
             if wo["id"] == outlet_id),
            None
        )
        if outlet:
            self._wire_detail.set_trace(steps, outlet.get("name", outlet_id), data=self._data)
            ep_id = outlet.get("endpoint_id")
            ep    = next((e for e in self._data.get("endpoints", [])
                          if e["id"] == ep_id), None) if ep_id else None
            status = f"🌐  {outlet['name']}"
            if ep:
                status += f"  ·  💻  {ep['name']}"
            last_port = next(
                (s for s in reversed(steps) if s["obj_type"] == "port"), None)
            if last_port:
                status += f"  ►  ⬡  {last_port['label']}"
            self.set_status(status)

    def _on_locator_room_navigate(self, room_id: str):
        self._select_tree_item_by_id(room_id, "room")

    def _on_search_result(self, result_type: str, result_id: str):
        if result_type == "rack":
            for site in self._data.get("sites", []):
                for room in site.get("rooms", []):
                    for rack in room.get("racks", []):
                        if rack["id"] == result_id:
                            self._navigate_to_rack(rack, room, site)
                            self.set_status(
                                f"🔍  {t('label_rack')}: {rack['name']} — "
                                f"{room['name']} — {site['name']}"
                            )
                            return

        elif result_type == "site":
            for i in range(self._tree.topLevelItemCount()):
                item = self._tree.topLevelItem(i)
                d = item.data(_COL, Qt.ItemDataRole.UserRole)
                if d and d.get("id") == result_id:
                    self._tree.setCurrentItem(item)
                    item.setExpanded(True)
                    site = self._find_site(result_id)
                    self.set_status(f"🔍  {t('label_site')}: {site['name']}")
                    return

        elif result_type == "room":
            for site in self._data.get("sites", []):
                for room in site.get("rooms", []):
                    if room["id"] == result_id:
                        self._select_tree_item_by_id(result_id)
                        self.set_status(
                            f"🔍  {t('label_room')}: {room['name']} — {site['name']}"
                        )
                        return

        elif result_type in ("device", "port"):
            dev_id = result_id
            if result_type == "port":
                port = next((p for p in self._data.get("ports", [])
                             if p["id"] == result_id), None)
                dev_id = port["device_id"] if port else None
            if not dev_id:
                return
            for site in self._data.get("sites", []):
                for room in site.get("rooms", []):
                    for rack in room.get("racks", []):
                        for slot in rack.get("slots", []):
                            if slot.get("device_id") == dev_id:
                                self._navigate_to_rack(rack, room, site)
                                dev = next((d for d in self._data.get("devices", [])
                                            if d["id"] == dev_id), None)
                                self.set_status(
                                    f"🔍  {t('label_device')}: "
                                    f"{dev['name'] if dev else dev_id} — "
                                    f"{rack['name']} — {site['name']}"
                                )
                                return

        elif result_type == "wall_outlet":
            for site in self._data.get("sites", []):
                for room in site.get("rooms", []):
                    for wo in room.get("wall_outlets", []):
                        if wo["id"] == result_id:
                            self._show_wall_outlet_view(room, site)
                            self.set_status(
                                f"🔍  {t('label_wall_outlet')}: "
                                f"{wo.get('name', '')} — {room['name']} — {site['name']}"
                            )
                            return

        elif result_type == "endpoint":
            for site in self._data.get("sites", []):
                for room in site.get("rooms", []):
                    for wo in room.get("wall_outlets", []):
                        if wo.get("endpoint_id") == result_id:
                            self._show_wall_outlet_view(room, site)
                            ep = next((e for e in self._data.get("endpoints", [])
                                       if e["id"] == result_id), None)
                            self.set_status(
                                f"🔍  {t('label_endpoint')}: "
                                f"{ep['name'] if ep else result_id} — "
                                f"{wo.get('name', '')} — {room['name']}"
                            )
                            return

    def _select_tree_item_by_id(self, obj_id: str, obj_type: str = None):
        def _search(item: QTreeWidgetItem) -> bool:
            d = item.data(_COL, Qt.ItemDataRole.UserRole)
            if d and d.get("id") == obj_id:
                if obj_type is None or d.get("type") == obj_type:
                    self._tree.setCurrentItem(item)
                    parent = item.parent()
                    while parent:
                        parent.setExpanded(True)
                        parent = parent.parent()
                    return True
            for i in range(item.childCount()):
                if _search(item.child(i)):
                    return True
            return False

        for i in range(self._tree.topLevelItemCount()):
            if _search(self._tree.topLevelItem(i)):
                return

    def _navigate_to_rack(self, rack: dict, room: dict, site: dict):
        self._show_rack_view(rack, room, site)
        for i in range(self._tree.topLevelItemCount()):
            site_item = self._tree.topLevelItem(i)
            site_data = site_item.data(_COL, Qt.ItemDataRole.UserRole)
            if site_data and site_data.get("id") == site["id"]:
                site_item.setExpanded(True)
                for j in range(site_item.childCount()):
                    room_item = site_item.child(j)
                    room_data = room_item.data(_COL, Qt.ItemDataRole.UserRole)
                    if room_data and room_data.get("id") == room["id"]:
                        room_item.setExpanded(True)
                        for k in range(room_item.childCount()):
                            rack_item = room_item.child(k)
                            rack_data = rack_item.data(_COL, Qt.ItemDataRole.UserRole)
                            if rack_data and rack_data.get("id") == rack["id"]:
                                self._tree.setCurrentItem(rack_item)
                                return

    # ------------------------------------------------------------------
    # Opslaan + Backup
    # ------------------------------------------------------------------

    def _save_and_backup(self):
        try:
            settings_storage.save_network_data(self._data)
            log_info("network_data opgeslagen")
        except Exception as e:
            log_error("Opslaan mislukt", e)
            self.set_status(f"⚠  {t('err_save_failed')}")
            return

        try:
            settings   = settings_storage.load_settings()
            backup_cfg = settings.get("backup", {})

            if not backup_cfg.get("enabled", False):
                return
            network_path = backup_cfg.get("network_path", "").strip()
            if not network_path:
                return

            source = settings_storage.get_network_data_path()
            ok, err = backup_service.create_backup(source, backup_cfg)
            if ok:
                log_info(f"Backup aangemaakt naar: {network_path}")
            else:
                log_warning(f"Backup mislukt: {err}")
                self.set_status(f"⚠  {t('msg_backup_fail')}: {err}")
        except Exception as e:
            log_error("Backup fout", e)

    # ------------------------------------------------------------------
    # ID generator — v1.25.0
    # ------------------------------------------------------------------

    def _gen_id(self, prefix: str) -> str:
        import time, random
        base = f"{prefix}_{int(time.time() * 1000) % 1_000_000}_{random.randint(100, 999)}"
        all_ids = set()
        for site in self._data.get("sites", []):
            all_ids.add(site["id"])
            for room in site.get("rooms", []):
                all_ids.add(room["id"])
                for rack in room.get("racks", []):
                    all_ids.add(rack["id"])
                for wo in room.get("wall_outlets", []):
                    all_ids.add(wo["id"])
        for d in self._data.get("devices", []):
            all_ids.add(d["id"])
        for p in self._data.get("ports", []):
            all_ids.add(p["id"])
        while base in all_ids:
            base = f"{prefix}_{int(time.time() * 1000) % 1_000_000}_{random.randint(100, 999)}"
        return base

    # ------------------------------------------------------------------
    # Publieke methodes
    # ------------------------------------------------------------------

    def set_status(self, message: str):
        self.statusBar().showMessage(message)

    def reload_ui_labels(self):
        self.setWindowTitle(t("app_title"))
        self._menu_file.setTitle(t("menubar_file"))
        self._menu_inex.setTitle(t("menubar_inexport"))
        self._menu_report.setTitle(t("menubar_report"))
        self._menu_settings_mb.setTitle("Settings")
        self._menu_help.setTitle(t("menubar_help"))
        self._act_new.setText(t("menu_new"))
        self._act_edit.setText(t("menu_edit"))
        self._act_delete.setText(t("menu_delete"))
        self._act_duplicate.setText(t("menu_duplicate"))
        self._act_search.setText(t("menu_search"))
        self._act_connect.setText(t("menu_connect"))
        self._act_import.setText(t("menu_import"))
        self._act_export.setText(t("menu_export"))
        self._act_export_image.setText(t("menu_export_image"))
        self._act_export_pdf.setText(t("menu_export_pdf"))
        self._act_export_report.setText(t("menu_export_report"))
        self._act_settings.setText(t("menu_settings"))
        self._populate_tree()

    def refresh_tree(self):
        self._data = settings_storage.load_network_data()
        self._populate_tree()