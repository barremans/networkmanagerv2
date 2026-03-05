# =============================================================================
# Networkmap_Creator
# File:    app/gui/settings_window.py
# Role:    Instellingen venster — taal, backup, weergave, eindapparaat-types,
#          device-types, netwerkdata locatie
# Version: 1.6.0
# Author:  Barremans
# Changes: F2 — Tabblad "Device types" met CRUD + standaard FRONT/BACK
#          F3 — Sectie "Databron" in Algemeen tabblad
#          H1d — Standaard exportmap in Weergave tabblad
#          D  — Update check URL veld in Algemeen tabblad
# =============================================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QLineEdit, QSpinBox, QCheckBox,
    QComboBox, QPushButton, QFileDialog, QMessageBox,
    QTabWidget, QWidget, QListWidget, QListWidgetItem,
    QFrame
)
from PySide6.QtCore import Qt, Signal

from app.helpers.i18n import t
from app.helpers import settings_storage, i18n
from app.services import backup_service


class SettingsWindow(QDialog):
    """
    Instellingen venster met tabbladen:
      - Algemeen      : taal + databron (F3) + update check URL (D)
      - Backup        : netwerkpad, history, max backups
      - Weergave      : rack unit hoogte + standaard exportmap (H1d)
      - Eindapparaten : types beheren
      - Device types  : types beheren incl. standaard FRONT/BACK (F2)
    """
    language_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings  = settings_storage.load_settings()
        self._ep_types  = list(settings_storage.load_endpoint_types())
        self._dev_types = list(settings_storage.load_device_types())
        self.setWindowTitle(t("menu_settings"))
        self.setMinimumWidth(500)
        self.setMinimumHeight(460)
        self.setModal(True)
        self._build()
        self._load()

    # ------------------------------------------------------------------
    # Opbouw
    # ------------------------------------------------------------------

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        tabs = QTabWidget()
        tabs.addTab(self._build_general_tab(),    t("settings_tab_general"))
        tabs.addTab(self._build_backup_tab(),     t("settings_tab_backup"))
        tabs.addTab(self._build_display_tab(),    t("settings_tab_display"))
        tabs.addTab(self._build_endpoint_tab(),   t("settings_tab_endpoints"))
        tabs.addTab(self._build_devicetype_tab(), t("settings_tab_device_types"))
        layout.addWidget(tabs)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(t("btn_cancel"))
        btn_save   = QPushButton(t("btn_save"))
        btn_save.setDefault(True)
        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Tabblad: Algemeen
    # ------------------------------------------------------------------

    def _build_general_tab(self) -> QWidget:
        tab    = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # --- Taal ---
        grp_lang   = QGroupBox(t("settings_group_language"))
        form_lang  = QFormLayout(grp_lang)
        form_lang.setSpacing(8)
        self._ddl_lang = QComboBox()
        self._ddl_lang.addItem("Nederlands", "nl")
        self._ddl_lang.addItem("English",    "en")
        form_lang.addRow("Taal / Language:", self._ddl_lang)
        hint_lang = QLabel(t("settings_lang_hint"))
        hint_lang.setObjectName("secondary")
        form_lang.addRow("", hint_lang)
        layout.addWidget(grp_lang)

        # --- Databron (F3) ---
        grp_data  = QGroupBox(t("settings_group_datasource"))
        form_data = QVBoxLayout(grp_data)
        form_data.setSpacing(8)

        self._chk_use_network = QCheckBox(t("settings_ds_use_network"))
        form_data.addWidget(self._chk_use_network)

        path_row = QHBoxLayout()
        self._txt_ds_path   = QLineEdit()
        self._txt_ds_path.setPlaceholderText(r"\\server\share\networkmap  of  Z:\data")
        self._btn_ds_browse = QPushButton("📂")
        self._btn_ds_browse.setFixedWidth(32)
        self._btn_ds_browse.setToolTip(t("btn_browse"))
        self._btn_ds_test   = QPushButton(t("settings_backup_test"))
        self._btn_ds_test.setFixedWidth(48)
        path_row.addWidget(self._txt_ds_path)
        path_row.addWidget(self._btn_ds_browse)
        path_row.addWidget(self._btn_ds_test)
        form_data.addLayout(path_row)

        self._lbl_ds_status = QLabel("")
        self._lbl_ds_status.setObjectName("secondary")
        form_data.addWidget(self._lbl_ds_status)

        hint_ds = QLabel(t("settings_ds_hint"))
        hint_ds.setObjectName("secondary")
        hint_ds.setWordWrap(True)
        form_data.addWidget(hint_ds)

        layout.addWidget(grp_data)

        # --- Update check URL (D) ---
        grp_update = QGroupBox(t("update_check_url"))
        form_update = QFormLayout(grp_update)
        form_update.setSpacing(8)

        self._txt_update_url = QLineEdit()
        self._txt_update_url.setPlaceholderText(t("update_check_url_hint"))
        self._txt_update_url.setMinimumWidth(360)
        form_update.addRow(t("update_check_url") + ":", self._txt_update_url)

        hint_update = QLabel(t("update_check_url_hint"))
        hint_update.setObjectName("secondary")
        hint_update.setWordWrap(True)
        form_update.addRow("", hint_update)

        layout.addWidget(grp_update)

        layout.addStretch()

        self._chk_use_network.toggled.connect(self._on_ds_toggled)
        self._btn_ds_browse.clicked.connect(self._on_ds_browse)
        self._btn_ds_test.clicked.connect(self._on_ds_test)

        return tab

    # ------------------------------------------------------------------
    # Tabblad: Backup
    # ------------------------------------------------------------------

    def _build_backup_tab(self) -> QWidget:
        tab    = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        grp_enable = QGroupBox(t("settings_backup_group"))
        grp_layout = QFormLayout(grp_enable)
        grp_layout.setSpacing(8)

        self._chk_backup = QCheckBox(t("settings_backup_enable"))
        grp_layout.addRow("", self._chk_backup)

        path_row = QHBoxLayout()
        self._txt_path   = QLineEdit()
        self._txt_path.setPlaceholderText(r"\\server\share\backup  of  C:\backup")
        self._btn_browse = QPushButton("📂")
        self._btn_browse.setFixedWidth(32)
        self._btn_browse.setToolTip(t("btn_browse"))
        self._btn_test   = QPushButton(t("settings_backup_test"))
        self._btn_test.setFixedWidth(48)
        path_row.addWidget(self._txt_path)
        path_row.addWidget(self._btn_browse)
        path_row.addWidget(self._btn_test)
        grp_layout.addRow(t("settings_backup_path"), path_row)

        self._chk_history = QCheckBox(t("settings_backup_history"))
        grp_layout.addRow("", self._chk_history)

        self._spn_max = QSpinBox()
        self._spn_max.setRange(1, 100)
        self._spn_max.setValue(10)
        self._spn_max.setSuffix(" backups")
        grp_layout.addRow(t("settings_backup_max"), self._spn_max)

        layout.addWidget(grp_enable)

        self._btn_backup_now = QPushButton(t("settings_backup_now"))
        layout.addWidget(self._btn_backup_now)
        layout.addStretch()

        self._btn_browse.clicked.connect(self._on_browse_path)
        self._btn_test.clicked.connect(self._on_test_path)
        self._btn_backup_now.clicked.connect(self._on_backup_now)
        self._chk_backup.toggled.connect(self._on_backup_toggled)

        return tab

    # ------------------------------------------------------------------
    # Tabblad: Weergave  [H1d — exportmap toegevoegd]
    # ------------------------------------------------------------------

    def _build_display_tab(self) -> QWidget:
        tab  = QWidget()
        form = QFormLayout(tab)
        form.setSpacing(10)
        form.setContentsMargins(12, 12, 12, 12)

        # Rack unit hoogte
        self._spn_unit_h = QSpinBox()
        self._spn_unit_h.setRange(20, 60)
        self._spn_unit_h.setValue(30)
        self._spn_unit_h.setSuffix(" px")
        form.addRow(t("settings_unit_height"), self._spn_unit_h)
        hint = QLabel(t("settings_unit_hint"))
        hint.setObjectName("secondary")
        form.addRow("", hint)

        # Scheidingslijn
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        form.addRow(sep)

        # Standaard exportmap  [H1d]
        export_row = QHBoxLayout()
        self._txt_export_folder = QLineEdit()
        self._txt_export_folder.setPlaceholderText(
            t("settings_export_folder_placeholder")
        )
        self._btn_export_browse = QPushButton("📂")
        self._btn_export_browse.setFixedWidth(32)
        self._btn_export_browse.setToolTip(t("btn_browse"))
        self._btn_export_browse.clicked.connect(self._on_export_folder_browse)
        self._btn_export_clear = QPushButton("✕")
        self._btn_export_clear.setFixedWidth(28)
        self._btn_export_clear.setToolTip(t("settings_export_folder_clear"))
        self._btn_export_clear.clicked.connect(
            lambda: self._txt_export_folder.clear()
        )
        export_row.addWidget(self._txt_export_folder)
        export_row.addWidget(self._btn_export_browse)
        export_row.addWidget(self._btn_export_clear)
        form.addRow(t("settings_export_folder") + ":", export_row)

        hint_export = QLabel(t("settings_export_folder_hint"))
        hint_export.setObjectName("secondary")
        hint_export.setWordWrap(True)
        form.addRow("", hint_export)

        return tab

    # ------------------------------------------------------------------
    # Tabblad: Eindapparaten
    # ------------------------------------------------------------------

    def _build_endpoint_tab(self) -> QWidget:
        tab    = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        hint = QLabel(t("settings_ep_hint"))
        hint.setObjectName("secondary")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        list_row = QHBoxLayout()
        self._ep_list = QListWidget()
        self._ep_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._ep_list.currentRowChanged.connect(self._on_ep_row_changed)
        list_row.addWidget(self._ep_list, stretch=1)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(4)
        btn_col.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._btn_ep_add  = QPushButton("＋  " + t("btn_add"))
        self._btn_ep_edit = QPushButton("✏  " + t("ctx_edit"))
        self._btn_ep_del  = QPushButton("🗑  " + t("ctx_delete"))
        self._btn_ep_up   = QPushButton("▲")
        self._btn_ep_down = QPushButton("▼")
        for btn in (self._btn_ep_add, self._btn_ep_edit, self._btn_ep_del,
                    self._btn_ep_up, self._btn_ep_down):
            btn.setMinimumWidth(110)
            btn_col.addWidget(btn)
        self._btn_ep_add.clicked.connect(self._on_ep_add)
        self._btn_ep_edit.clicked.connect(self._on_ep_edit)
        self._btn_ep_del.clicked.connect(self._on_ep_delete)
        self._btn_ep_up.clicked.connect(self._on_ep_move_up)
        self._btn_ep_down.clicked.connect(self._on_ep_move_down)
        list_row.addLayout(btn_col)
        layout.addLayout(list_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        restore_row = QHBoxLayout()
        restore_row.addStretch()
        self._btn_ep_restore = QPushButton("↺  " + t("settings_ep_restore"))
        self._btn_ep_restore.clicked.connect(self._on_ep_restore)
        restore_row.addWidget(self._btn_ep_restore)
        layout.addLayout(restore_row)
        return tab

    # ------------------------------------------------------------------
    # Tabblad: Device types — F2
    # ------------------------------------------------------------------

    def _build_devicetype_tab(self) -> QWidget:
        tab    = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        hint = QLabel(t("settings_dt_hint"))
        hint.setObjectName("secondary")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        list_row = QHBoxLayout()
        self._dt_list = QListWidget()
        self._dt_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._dt_list.currentRowChanged.connect(self._on_dt_row_changed)
        list_row.addWidget(self._dt_list, stretch=1)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(4)
        btn_col.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._btn_dt_add  = QPushButton("＋  " + t("btn_add"))
        self._btn_dt_edit = QPushButton("✏  " + t("ctx_edit"))
        self._btn_dt_del  = QPushButton("🗑  " + t("ctx_delete"))
        self._btn_dt_up   = QPushButton("▲")
        self._btn_dt_down = QPushButton("▼")
        for btn in (self._btn_dt_add, self._btn_dt_edit, self._btn_dt_del,
                    self._btn_dt_up, self._btn_dt_down):
            btn.setMinimumWidth(110)
            btn_col.addWidget(btn)
        self._btn_dt_add.clicked.connect(self._on_dt_add)
        self._btn_dt_edit.clicked.connect(self._on_dt_edit)
        self._btn_dt_del.clicked.connect(self._on_dt_delete)
        self._btn_dt_up.clicked.connect(self._on_dt_move_up)
        self._btn_dt_down.clicked.connect(self._on_dt_move_down)
        list_row.addLayout(btn_col)
        layout.addLayout(list_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        restore_row = QHBoxLayout()
        restore_row.addStretch()
        self._btn_dt_restore = QPushButton("↺  " + t("settings_dt_restore"))
        self._btn_dt_restore.clicked.connect(self._on_dt_restore)
        restore_row.addWidget(self._btn_dt_restore)
        layout.addLayout(restore_row)
        return tab

    # ------------------------------------------------------------------
    # Laden
    # ------------------------------------------------------------------

    def _load(self):
        # Taal
        lang = self._settings.get("language", "nl")
        idx  = self._ddl_lang.findData(lang)
        if idx >= 0:
            self._ddl_lang.setCurrentIndex(idx)

        # Databron (F3)
        nd_cfg = self._settings.get("network_data", {})
        self._chk_use_network.blockSignals(True)
        self._chk_use_network.setChecked(nd_cfg.get("use_network_path", False))
        self._chk_use_network.blockSignals(False)
        self._txt_ds_path.setText(nd_cfg.get("network_path", ""))
        self._on_ds_toggled(nd_cfg.get("use_network_path", False))
        self._update_ds_status_label()

        # Update check URL (D)
        self._txt_update_url.setText(self._settings.get("update_check_url", ""))

        # Backup
        backup = self._settings.get("backup", {})
        self._chk_backup.blockSignals(True)
        self._chk_backup.setChecked(backup.get("enabled", False))
        self._chk_backup.blockSignals(False)
        self._txt_path.setText(backup.get("network_path", ""))
        self._chk_history.setChecked(backup.get("keep_history", True))
        self._spn_max.setValue(backup.get("max_backups", 10))
        self._on_backup_toggled(backup.get("enabled", False))

        # Weergave + exportmap  [H1d]
        ui = self._settings.get("ui", {})
        self._spn_unit_h.setValue(ui.get("rack_unit_height", 30))
        self._txt_export_folder.setText(ui.get("export_folder", ""))

        # Eindapparaten
        self._refresh_ep_list()
        self._on_ep_row_changed(-1)

        # Device types
        self._refresh_dt_list()
        self._on_dt_row_changed(-1)

    def _update_ds_status_label(self):
        label, is_net = settings_storage.get_network_data_source_label()
        if is_net:
            self._lbl_ds_status.setText(f"✓  {t('settings_ds_active')}: {label}")
        elif "fallback" in label.lower():
            self._lbl_ds_status.setText(f"⚠  {label}")
        else:
            self._lbl_ds_status.setText(f"📁  {t('settings_ds_active')}: {label}")

    def _refresh_ep_list(self, select_idx: int = -1):
        lang = self._ddl_lang.currentData() or "nl"
        self._ep_list.clear()
        for et in self._ep_types:
            label = et.get(f"label_{lang}", et.get("label_nl", et.get("key", "?")))
            item  = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, et)
            self._ep_list.addItem(item)
        if select_idx >= 0 and select_idx < self._ep_list.count():
            self._ep_list.setCurrentRow(select_idx)
        self._on_ep_row_changed(self._ep_list.currentRow())

    def _refresh_dt_list(self, select_idx: int = -1):
        lang = self._ddl_lang.currentData() or "nl"
        self._dt_list.clear()
        for dt in self._dev_types:
            label = dt.get(f"label_{lang}", dt.get("label_nl", dt.get("key", "?")))
            fp    = dt.get("front_ports", 0)
            bp    = dt.get("back_ports",  0)
            item  = QListWidgetItem(f"{label}  (F:{fp}  B:{bp})")
            item.setData(Qt.ItemDataRole.UserRole, dt)
            self._dt_list.addItem(item)
        if select_idx >= 0 and select_idx < self._dt_list.count():
            self._dt_list.setCurrentRow(select_idx)
        self._on_dt_row_changed(self._dt_list.currentRow())

    def _on_ep_row_changed(self, row: int):
        has = row >= 0
        self._btn_ep_edit.setEnabled(has)
        self._btn_ep_del.setEnabled(has)
        self._btn_ep_up.setEnabled(has and row > 0)
        self._btn_ep_down.setEnabled(has and row < self._ep_list.count() - 1)

    def _on_dt_row_changed(self, row: int):
        has = row >= 0
        self._btn_dt_edit.setEnabled(has)
        self._btn_dt_del.setEnabled(has)
        self._btn_dt_up.setEnabled(has and row > 0)
        self._btn_dt_down.setEnabled(has and row < self._dt_list.count() - 1)

    # ------------------------------------------------------------------
    # Exportmap browse handler — H1d
    # ------------------------------------------------------------------

    def _on_export_folder_browse(self):
        folder = QFileDialog.getExistingDirectory(
            self, t("settings_export_folder"),
            self._txt_export_folder.text() or ""
        )
        if folder:
            self._txt_export_folder.setText(folder)

    # ------------------------------------------------------------------
    # Databron handlers — F3
    # ------------------------------------------------------------------

    def _on_ds_toggled(self, checked: bool):
        self._txt_ds_path.setEnabled(checked)
        self._btn_ds_browse.setEnabled(checked)
        self._btn_ds_test.setEnabled(checked)

    def _on_ds_browse(self):
        folder = QFileDialog.getExistingDirectory(
            self, t("settings_ds_browse_title"),
            self._txt_ds_path.text() or ""
        )
        if folder:
            self._txt_ds_path.setText(folder)

    def _on_ds_test(self):
        path = self._txt_ds_path.text().strip()
        if not path:
            QMessageBox.warning(self, t("settings_group_datasource"),
                                t("err_backup_no_path"))
            return
        ok = settings_storage.is_network_path_available(path)
        if ok:
            QMessageBox.information(
                self, t("settings_path_ok_title"),
                f"✓  {t('settings_ds_path_ok')}\n{path}"
            )
        else:
            QMessageBox.warning(
                self, t("settings_path_ok_title"),
                f"⚠  {t('settings_ds_path_fail')}\n{path}"
            )

    # ------------------------------------------------------------------
    # Eindapparaat CRUD
    # ------------------------------------------------------------------

    def _on_ep_add(self):
        dlg = _EndpointTypeDialog(parent=self)
        if dlg.exec():
            et = dlg.get_result()
            if et:
                keys = {e.get("key", "") for e in self._ep_types}
                if et["key"] in keys:
                    QMessageBox.warning(self, t("settings_tab_endpoints"),
                                        t("settings_ep_key_exists"))
                    return
                self._ep_types.append(et)
                self._refresh_ep_list(len(self._ep_types) - 1)

    def _on_ep_edit(self):
        row = self._ep_list.currentRow()
        if row < 0:
            return
        dlg = _EndpointTypeDialog(parent=self, ep_type=self._ep_types[row])
        if dlg.exec():
            result = dlg.get_result()
            if result:
                self._ep_types[row] = result
                self._refresh_ep_list(row)

    def _on_ep_delete(self):
        row = self._ep_list.currentRow()
        if row < 0:
            return
        et    = self._ep_types[row]
        name  = et.get("label_nl", et.get("key", "?"))
        reply = QMessageBox.question(
            self, t("menu_delete"),
            f"{t('msg_confirm_delete')}\n\n{name}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._ep_types.pop(row)
        self._refresh_ep_list(max(0, row - 1))

    def _on_ep_move_up(self):
        row = self._ep_list.currentRow()
        if row <= 0:
            return
        self._ep_types[row], self._ep_types[row - 1] = \
            self._ep_types[row - 1], self._ep_types[row]
        self._refresh_ep_list(row - 1)

    def _on_ep_move_down(self):
        row = self._ep_list.currentRow()
        if row < 0 or row >= len(self._ep_types) - 1:
            return
        self._ep_types[row], self._ep_types[row + 1] = \
            self._ep_types[row + 1], self._ep_types[row]
        self._refresh_ep_list(row + 1)

    def _on_ep_restore(self):
        reply = QMessageBox.question(
            self, t("settings_tab_endpoints"),
            t("settings_ep_restore_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        from app.helpers.settings_storage import _DEFAULT_ENDPOINT_TYPES
        self._ep_types = list(_DEFAULT_ENDPOINT_TYPES)
        self._refresh_ep_list(0)

    # ------------------------------------------------------------------
    # Device type CRUD — F2
    # ------------------------------------------------------------------

    def _on_dt_add(self):
        dlg = _DeviceTypeDialog(parent=self)
        if dlg.exec():
            dt = dlg.get_result()
            if dt:
                keys = {d.get("key", "") for d in self._dev_types}
                if dt["key"] in keys:
                    QMessageBox.warning(self, t("settings_tab_device_types"),
                                        t("settings_ep_key_exists"))
                    return
                self._dev_types.append(dt)
                self._refresh_dt_list(len(self._dev_types) - 1)

    def _on_dt_edit(self):
        row = self._dt_list.currentRow()
        if row < 0:
            return
        dlg = _DeviceTypeDialog(parent=self, dev_type=self._dev_types[row])
        if dlg.exec():
            result = dlg.get_result()
            if result:
                self._dev_types[row] = result
                self._refresh_dt_list(row)

    def _on_dt_delete(self):
        row = self._dt_list.currentRow()
        if row < 0:
            return
        dt    = self._dev_types[row]
        name  = dt.get("label_nl", dt.get("key", "?"))
        reply = QMessageBox.question(
            self, t("menu_delete"),
            f"{t('msg_confirm_delete')}\n\n{name}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._dev_types.pop(row)
        self._refresh_dt_list(max(0, row - 1))

    def _on_dt_move_up(self):
        row = self._dt_list.currentRow()
        if row <= 0:
            return
        self._dev_types[row], self._dev_types[row - 1] = \
            self._dev_types[row - 1], self._dev_types[row]
        self._refresh_dt_list(row - 1)

    def _on_dt_move_down(self):
        row = self._dt_list.currentRow()
        if row < 0 or row >= len(self._dev_types) - 1:
            return
        self._dev_types[row], self._dev_types[row + 1] = \
            self._dev_types[row + 1], self._dev_types[row]
        self._refresh_dt_list(row + 1)

    def _on_dt_restore(self):
        reply = QMessageBox.question(
            self, t("settings_tab_device_types"),
            t("settings_dt_restore_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        from app.helpers.settings_storage import _DEFAULT_DEVICE_TYPES
        self._dev_types = list(_DEFAULT_DEVICE_TYPES)
        self._refresh_dt_list(0)

    # ------------------------------------------------------------------
    # Backup handlers
    # ------------------------------------------------------------------

    def _on_backup_toggled(self, checked: bool):
        self._txt_path.setEnabled(checked)
        self._chk_history.setEnabled(checked)
        self._spn_max.setEnabled(checked)

    def _on_browse_path(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Backup map kiezen", self._txt_path.text() or ""
        )
        if folder:
            self._txt_path.setText(folder)

    def _on_test_path(self):
        path = self._txt_path.text().strip()
        ok, err = backup_service.test_path(path)
        if ok:
            QMessageBox.information(self, t("settings_path_ok_title"),
                                    f"✓  Pad bereikbaar en beschrijfbaar:\n{path}")
        else:
            QMessageBox.warning(self, t("settings_path_ok_title"),
                                f"⚠  Pad niet bereikbaar:\n{err}")

    def _on_backup_now(self):
        path = self._txt_path.text().strip()
        if not path:
            QMessageBox.warning(self, t("settings_backup_group"),
                                t("err_backup_no_path"))
            return
        config = {
            "enabled":      True,
            "network_path": path,
            "keep_history": self._chk_history.isChecked(),
            "max_backups":  self._spn_max.value(),
        }
        source = settings_storage.get_network_data_path()
        ok, err = backup_service.create_backup(source, config)
        if ok:
            QMessageBox.information(self, t("settings_backup_group"),
                                    f"✓  {t('msg_backup_ok')}\n{path}")
        else:
            QMessageBox.warning(self, t("settings_backup_group"),
                                f"⚠  {t('msg_backup_fail')}\n{err}")

    # ------------------------------------------------------------------
    # Opslaan
    # ------------------------------------------------------------------

    def _on_save(self):
        new_lang = self._ddl_lang.currentData()
        old_lang = self._settings.get("language", "nl")
        lang_changed = new_lang != old_lang

        backup_enabled = self._chk_backup.isChecked()
        network_path   = self._txt_path.text().strip()

        if backup_enabled and not network_path:
            QMessageBox.warning(self, t("menu_settings"),
                                t("err_backup_path_required"))
            return

        use_net = self._chk_use_network.isChecked()
        ds_path = self._txt_ds_path.text().strip()
        if use_net and not ds_path:
            QMessageBox.warning(self, t("menu_settings"),
                                t("err_ds_path_required"))
            return

        settings_storage.save_setting("language", new_lang)
        settings_storage.save_setting("update_check_url",           # D
                                      self._txt_update_url.text().strip())
        settings_storage.save_setting("backup", {
            "enabled":      backup_enabled,
            "network_path": network_path,
            "keep_history": self._chk_history.isChecked(),
            "max_backups":  self._spn_max.value(),
        })
        settings_storage.save_setting("ui", {
            "theme":            "dark",
            "rack_unit_height": self._spn_unit_h.value(),
            "rack_unit_width":  400,
            "export_folder":    self._txt_export_folder.text().strip(),  # H1d
        })
        settings_storage.save_setting("network_data", {
            "use_network_path": use_net,
            "network_path":     ds_path,
        })
        settings_storage.save_endpoint_types(self._ep_types)
        settings_storage.save_device_types(self._dev_types)

        if lang_changed:
            i18n.set_language(new_lang)
            self.language_changed.emit()

        self.accept()


# ---------------------------------------------------------------------------
# Hulp-dialog: eindapparaat-type
# ---------------------------------------------------------------------------

class _EndpointTypeDialog(QDialog):
    def __init__(self, parent=None, ep_type: dict = None):
        super().__init__(parent)
        self._ep_type = ep_type
        self._result  = None
        self.setWindowTitle(
            t("settings_ep_edit_title") if ep_type else t("settings_ep_new_title")
        )
        self.setMinimumWidth(340)
        self.setModal(True)
        self._build()
        if self._ep_type:
            self._populate()

    def _build(self):
        layout = QVBoxLayout(self)
        form   = QFormLayout()
        form.setSpacing(8)
        self._key      = QLineEdit()
        self._key.setPlaceholderText("bijv. thin_client")
        self._label_nl = QLineEdit()
        self._label_en = QLineEdit()
        is_new = self._ep_type is None
        self._key.setEnabled(is_new)
        if not is_new:
            self._key.setToolTip(t("settings_ep_key_locked"))
        form.addRow(t("settings_ep_key")      + ":", self._key)
        form.addRow(t("settings_ep_label_nl") + ":", self._label_nl)
        form.addRow(t("settings_ep_label_en") + ":", self._label_en)
        hint = QLabel(t("settings_ep_key_hint"))
        hint.setObjectName("secondary")
        hint.setWordWrap(True)
        form.addRow("", hint)
        layout.addLayout(form)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(t("btn_cancel"))
        btn_save   = QPushButton(t("btn_save"))
        btn_save.setDefault(True)
        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def _populate(self):
        self._key.setText(self._ep_type.get("key", ""))
        self._label_nl.setText(self._ep_type.get("label_nl", ""))
        self._label_en.setText(self._ep_type.get("label_en", ""))

    def _on_save(self):
        import re
        key    = self._key.text().strip().lower().replace(" ", "_")
        lbl_nl = self._label_nl.text().strip()
        lbl_en = self._label_en.text().strip()
        if not key:
            QMessageBox.warning(self, "", t("settings_ep_key") + " " + t("err_field_required"))
            return
        if not re.match(r'^[a-z0-9_]+$', key):
            QMessageBox.warning(self, "", t("settings_ep_key_invalid"))
            return
        if not lbl_nl:
            QMessageBox.warning(self, "", t("settings_ep_label_nl") + " " + t("err_field_required"))
            return
        if not lbl_en:
            lbl_en = lbl_nl
        self._result = {"key": key, "label_nl": lbl_nl, "label_en": lbl_en}
        self.accept()

    def get_result(self) -> dict | None:
        return self._result


# ---------------------------------------------------------------------------
# Hulp-dialog: device-type — F2
# ---------------------------------------------------------------------------

class _DeviceTypeDialog(QDialog):
    def __init__(self, parent=None, dev_type: dict = None):
        super().__init__(parent)
        self._dev_type = dev_type
        self._result   = None
        self.setWindowTitle(
            t("settings_dt_edit_title") if dev_type else t("settings_dt_new_title")
        )
        self.setMinimumWidth(360)
        self.setModal(True)
        self._build()
        if self._dev_type:
            self._populate()

    def _build(self):
        layout = QVBoxLayout(self)
        form   = QFormLayout()
        form.setSpacing(8)
        self._key      = QLineEdit()
        self._key.setPlaceholderText("bijv. patch_panel")
        self._label_nl = QLineEdit()
        self._label_en = QLineEdit()
        self._front_ports = QSpinBox()
        self._front_ports.setRange(0, 96)
        self._front_ports.setSuffix("  poorten")
        self._back_ports = QSpinBox()
        self._back_ports.setRange(0, 96)
        self._back_ports.setSuffix("  poorten")
        is_new = self._dev_type is None
        self._key.setEnabled(is_new)
        if not is_new:
            self._key.setToolTip(t("settings_ep_key_locked"))
        form.addRow(t("settings_ep_key")        + ":", self._key)
        form.addRow(t("settings_ep_label_nl")   + ":", self._label_nl)
        form.addRow(t("settings_ep_label_en")   + ":", self._label_en)
        form.addRow(t("settings_dt_front_ports") + ":", self._front_ports)
        form.addRow(t("settings_dt_back_ports")  + ":", self._back_ports)
        hint = QLabel(t("settings_dt_ports_hint"))
        hint.setObjectName("secondary")
        hint.setWordWrap(True)
        form.addRow("", hint)
        layout.addLayout(form)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(t("btn_cancel"))
        btn_save   = QPushButton(t("btn_save"))
        btn_save.setDefault(True)
        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def _populate(self):
        self._key.setText(self._dev_type.get("key", ""))
        self._label_nl.setText(self._dev_type.get("label_nl", ""))
        self._label_en.setText(self._dev_type.get("label_en", ""))
        self._front_ports.setValue(self._dev_type.get("front_ports", 0))
        self._back_ports.setValue(self._dev_type.get("back_ports", 0))

    def _on_save(self):
        import re
        key    = self._key.text().strip().lower().replace(" ", "_")
        lbl_nl = self._label_nl.text().strip()
        lbl_en = self._label_en.text().strip()
        if not key:
            QMessageBox.warning(self, "", t("settings_ep_key") + " " + t("err_field_required"))
            return
        if not re.match(r'^[a-z0-9_]+$', key):
            QMessageBox.warning(self, "", t("settings_ep_key_invalid"))
            return
        if not lbl_nl:
            QMessageBox.warning(self, "", t("settings_ep_label_nl") + " " + t("err_field_required"))
            return
        if not lbl_en:
            lbl_en = lbl_nl
        self._result = {
            "key":         key,
            "label_nl":    lbl_nl,
            "label_en":    lbl_en,
            "front_ports": self._front_ports.value(),
            "back_ports":  self._back_ports.value(),
        }
        self.accept()

    def get_result(self) -> dict | None:
        return self._result