# =============================================================================
# Networkmap_Creator
# File:    app/helpers/i18n.py
# Role:    Meertaligheid — NL/EN vertalingen, t() functie
# Version: 1.9.1
# Author:  Barremans
# Changes: F1 — msg_connect_cancelled
#          F2 — settings_tab_device_types, settings_dt_*, device_* types
#          F3 — settings_group_language, settings_group_datasource,
#               settings_ds_*, err_ds_path_required
#          G1+G2 — menu_export_image, menu_export_pdf, export_col_*, msg_*_exported
#          G3 — menu_export_report, msg_report_exported, msg_report_export_failed
#          H1 — menubar_*, help_*
#          D  — update_check_url, update_available_*, update_goto_github, update_later
#          1.8.0 — settings_tab_outlet_locations, settings_loc_* (wandpunt locaties)
#          1.9.0 — t() fallback voor device_* keys: haalt label op uit settings_storage
#                  als de key niet in TRANSLATIONS staat (custom device types)
#                  Voorkomt [device_cable_management] weergave in rack_view
# =============================================================================

TRANSLATIONS: dict[str, dict[str, str]] = {

    # -------------------------------------------------------------------------
    # Nederlands (standaard)
    # -------------------------------------------------------------------------
    "nl": {
        # App
        "app_title":                "Networkmap Creator",

        # Toolbar / menu
        "menu_new":                 "Nieuw",
        "menu_edit":                "Bewerken",
        "menu_delete":              "Verwijderen",
        "menu_duplicate":           "Dupliceren",
        "menu_search":              "Zoeken",
        "menu_connect":             "Verbinding",
        "menu_import":              "Importeren",
        "menu_export":              "Exporteren",
        "menu_export_image":        "Exporteer afbeelding",          # G2
        "menu_export_pdf":          "Exporteer PDF",                 # G1
        "menu_export_report":       "Rapport (Word)",                # G3
        "menu_settings":            "Instellingen",

        # Menubar — H1
        "menubar_file":             "Bestand",
        "menubar_inexport":         "Im/Export",
        "menubar_help":             "Help",
        "menubar_quit":             "Afsluiten",

        # Help venster — H1
        "help_title":               "Help",
        "help_tab_shortcuts":       "Sneltoetsen",
        "help_tab_guide":           "Gebruiksaanwijzing",
        "help_tab_version":         "Over",
        "help_shortcuts_intro":     "Overzicht van alle sneltoetsen in Networkmap Creator.",
        "help_col_shortcut":        "Sneltoets",
        "help_col_action":          "Actie",
        "help_shortcut_esc":        "Verbindingsmodus annuleren",
        "help_version_label":       "Versie",
        "help_author_label":        "Auteur",
        "help_built_with":          "Gebouwd met",
        "help_license_label":       "Licentie",
        "help_license_value":       "Intern gebruik — CGK",

        # Versie-info beschrijving — H1
        "help_app_desc":            "Netwerk infrastructuur beheer — sites, ruimtes, racks, devices, wandpunten en verbindingen.",

        # Object labels
        "label_site":               "Site",
        "label_room":               "Ruimte",
        "label_rack":               "Rack",
        "label_device":             "Toestel",
        "label_port":               "Poort",
        "label_front":              "Voor",
        "label_back":               "Achter",
        "label_wall_outlet":        "Wandpunt",
        "label_endpoint":           "Eindapparaat",
        "label_cable":              "Kabel",
        "label_connection":         "Verbinding",
        "label_trace":              "Trace",

        # Velden
        "label_name":               "Naam",
        "label_type":               "Type",
        "label_brand":              "Merk",
        "label_model":              "Model",
        "label_ip":                 "IP adres",
        "label_subnet":             "Subnetmasker",
        "label_mac":                "MAC adres",
        "label_serial":             "Serienummer",
        "label_notes":              "Notities",
        "label_floor":              "Verdiep",
        "label_place":              "Plaats",
        "label_place_hint":         "Gebouw, vleugel of zone (optioneel)",
        "label_room_hint":          "Verdiep en Plaats verschijnen in de statusbalk en tooltips.",
        "label_location":           "Locatie",
        "label_units":              "Hoogte (U)",
        "label_u_start":            "Startpositie (U)",
        "label_front_ports":        "Poorten voor",
        "label_back_ports":         "Poorten achter",
        "label_total_units":        "Totale hoogte (U)",
        "label_cable_type":         "Kabeltype",
        "label_endpoint_type":      "Type eindapparaat",
        "label_location_desc":      "Locatiebeschrijving",
        "label_language":           "Taal",
        "label_backup_path":        "Backup map (netwerkpad)",
        "label_backup_enabled":     "Backup inschakelen",
        "label_max_backups":        "Max. backups bewaren",
        "label_rack_unit_height":   "U-hoogte (pixels)",
        "label_rack_unit_width":    "Rack breedte (pixels)",

        # Kabeltype DDL
        "cable_utp_cat5e":          "UTP Cat5e",
        "cable_utp_cat6":           "UTP Cat6",
        "cable_utp_cat6a":          "UTP Cat6a",
        "cable_fiber_sm":           "Glasvezel SM",
        "cable_fiber_mm":           "Glasvezel MM",
        "cable_dak":                "DAK kabel",
        "cable_other":              "Ander",

        # Device type DDL (ingebouwd — ook dynamisch via settings)
        "device_patch_panel":       "Patchpanel",
        "device_switch":            "Switch",
        "device_router":            "Router",
        "device_firewall":          "Firewall",
        "device_server":            "Server",
        "device_kvm":               "KVM-switch",
        "device_ups":               "UPS",
        "device_pdu":               "PDU",
        "device_media_conv":        "Mediaconverter",
        "device_patchpanel":        "Patchpanel",
        "device_modem":             "Modem",
        "device_other":             "Ander",
        "device_cable_management":  "Kabelgoot",
        "device_distribution_plug": "Verdeelstekker",
        "device_fiber":             "Fiber converter",
        "device_nuc1":              "NUC / Mini-PC",
        "device_sonos_server":      "Sonos server",

        # Endpoint type DDL
        "endpoint_pc":              "PC",
        "endpoint_laptop":          "Laptop",
        "endpoint_thin_client":     "Thin Client",
        "endpoint_printer":         "Printer",
        "endpoint_plotter":         "Plotter",
        "endpoint_scanner":         "Scanner",
        "endpoint_all_in_one":      "All-in-one",
        "endpoint_phone":           "IP-telefoon",
        "endpoint_ip_camera":       "IP-camera",
        "endpoint_access_point":    "Access Point",
        "endpoint_nas":             "NAS",
        "endpoint_other":           "Ander",

        # Knoppen
        "btn_save":                 "Opslaan",
        "btn_cancel":               "Annuleren",
        "btn_add":                  "Toevoegen",
        "btn_close":                "Sluiten",
        "btn_browse":               "Bladeren...",
        "btn_new_site":             "Nieuwe site",
        "btn_new_room":             "Nieuwe ruimte",
        "btn_new_rack":             "Nieuw rack",
        "btn_new_device":           "Nieuw toestel",
        "btn_new_outlet":           "Nieuw wandpunt",
        "btn_new_endpoint":         "Nieuw eindapparaat",
        "btn_new_connection":       "Nieuwe verbinding",

        # Statusberichten
        "msg_confirm_delete":       "Bent u zeker dat u dit wilt verwijderen?",
        "msg_confirm_delete_title": "Verwijderen bevestigen",
        "msg_backup_ok":            "Backup succesvol aangemaakt.",
        "msg_backup_fail":          "Backup mislukt. Controleer het netwerkpad.",
        "msg_import_ok":            "Import succesvol.",
        "msg_import_fail":          "Import mislukt. Controleer het bestand.",
        "msg_export_ok":            "Export succesvol.",
        "msg_export_fail":          "Export mislukt.",
        "msg_save_ok":              "Opgeslagen.",
        "msg_save_fail":            "Opslaan mislukt.",
        "msg_invalid_json":         "Ongeldig JSON bestand.",
        "msg_port_in_use":          "Deze poort is al in gebruik.",
        "msg_no_selection":         "Geen selectie gemaakt.",
        "msg_connect_select_a":     "Selecteer eerste poort...",
        "msg_connect_select_b":     "Selecteer tweede poort...",
        "msg_connect_cancel":       "Verbindingsmodus geannuleerd.",
        "msg_connect_cancelled":    "Verbindingsmodus geannuleerd (ESC).",   # F1
        "msg_connect_done":         "Verbinding aangemaakt.",
        "msg_search_no_results":    "Geen resultaten gevonden.",
        "msg_language_restart":     "Taalwijziging wordt direct toegepast.",
        "msg_image_exported":       "Afbeelding opgeslagen",                 # G2
        "msg_image_export_failed":  "Afbeelding opslaan mislukt",            # G2
        "msg_pdf_exported":         "PDF opgeslagen",                        # G1
        "msg_pdf_export_failed":    "PDF opslaan mislukt",                   # G1
        "msg_report_exported":      "Rapport opgeslagen",                    # G3
        "msg_report_export_failed": "Rapport opslaan mislukt",               # G3

        # Titels vensters / dialogs
        "title_settings":           "Instellingen",
        "title_search":             "Zoeken",
        "title_new_site":           "Site aanmaken",
        "title_edit_site":          "Site bewerken",
        "title_new_room":           "Ruimte aanmaken",
        "title_edit_room":          "Ruimte bewerken",
        "title_new_rack":           "Rack aanmaken",
        "title_edit_rack":          "Rack bewerken",
        "title_new_device":         "Toestel aanmaken",
        "title_edit_device":        "Toestel bewerken",
        "title_new_outlet":         "Wandpunt aanmaken",
        "title_edit_outlet":        "Wandpunt bewerken",
        "title_new_endpoint":       "Eindapparaat aanmaken",
        "title_edit_endpoint":      "Eindapparaat bewerken",
        "title_new_connection":     "Verbinding aanmaken",
        "title_wire_detail":        "Verbindingsdetail",
        "title_wall_outlets":       "Wandpunten",

        # Boom (tree view)
        "tree_wall_outlets":        "Wandpunten",
        "tree_no_endpoint":         "(geen eindapparaat)",

        # Trace labels
        "trace_from":               "Van",
        "trace_to":                 "Naar",
        "trace_via":                "Via",
        "trace_cable":              "Kabel",
        "trace_room":               "Ruimte",
        "trace_direction":          "Richting",
        "trace_no_connection":      "Geen verbinding op deze poort.",
        "trace_internal":           "Interne doorverbinding",

        # Import/export
        "import_mode_replace":      "Vervangen",
        "import_mode_merge":        "Samenvoegen",
        "import_mode_label":        "Importmodus",
        "export_filename_prefix":   "networkmap_export",

        # Export renderer — kolommen (G1+G2)
        "export_table_title":       "Aansluitingstabel",
        "export_col_port":          "Poort",
        "export_col_side":          "Zijde",
        "export_col_dest":          "Verbonden met",
        "export_col_outlet":        "Wandpunt",
        "export_col_location":      "Locatie",
        "export_col_trace":         "Trace → Eindpunt",
        "err_no_view_to_export":    "Geen actieve weergave om te exporteren.",

        # Zoeken
        "search_placeholder":       "Zoek op naam, IP, MAC, serienummer...",
        "search_result_device":     "Toestel",
        "search_result_port":       "Poort",
        "search_result_outlet":     "Wandpunt",
        "search_result_endpoint":   "Eindapparaat",

        # Foutmeldingen
        "err_field_required":       "Dit veld is verplicht.",
        "err_outlet_duplicate_name": "Een wandpunt met de naam '{name}' bestaat al in deze ruimte.",
        "err_invalid_number":       "Voer een geldig getal in.",
        "err_path_not_found":       "Pad niet gevonden.",
        "err_file_not_found":       "Bestand niet gevonden.",
        "err_unknown":              "Onbekende fout.",
        "err_same_port":            "Poort A en B zijn dezelfde poort.",
        "err_port_in_use":          "Deze poort is al in gebruik.",
        "err_no_selection":         "Selecteer eerst een object.",
        "err_select_site_for_room": "Selecteer eerst een site om een ruimte toe te voegen.",
        "err_select_room_for_rack": "Selecteer eerst een ruimte om een rack toe te voegen.",
        "err_select_room_for_outlet": "Selecteer eerst een ruimte om een wandpunt toe te voegen.",
        "err_select_for_edit":      "Selecteer een site, ruimte of rack om te bewerken.",
        "err_select_rack_for_device": "Selecteer een rack om een device te bewerken of verwijderen.",
        "err_rack_no_devices":      "Dit rack bevat geen devices.",
        "err_select_outlet":        "Selecteer een individueel wandpunt om te verwijderen.",
        "err_backup_no_path":       "Stel eerst een netwerkpad in.",
        "err_backup_path_required": "Backup is ingeschakeld maar er is geen pad ingesteld.",
        "err_corrupt_data":         "Databestand is corrupt of onleesbaar.",
        "err_save_failed":          "Opslaan mislukt. Controleer de schijfruimte.",
        "err_ds_path_required":     "Netwerkdata is ingeschakeld maar er is geen pad ingesteld.",  # F3

        # Status / info berichten
        "msg_ready":                "Klaar.",
        "msg_connection_deleted":   "Verbinding verwijderd.",
        "msg_device_deleted":       "Toestel verwijderd.",
        "msg_device_updated":       "Toestel bijgewerkt.",
        "msg_rack_deleted":         "Rack verwijderd.",
        "msg_exported_to":          "Geëxporteerd naar:",
        "msg_export_failed":        "Export mislukt.",
        "msg_import_replace_done":  "Import succesvol (vervangen).",
        "msg_import_merge_done":    "Import succesvol — {added} toegevoegd, {skipped} overgeslagen.",
        "msg_path_ok":              "Pad bereikbaar en beschrijfbaar.",
        "msg_language_applied":     "Taalwijziging direct toegepast.",

        # Settings venster — tabbladen
        "settings_tab_general":         "⚙  Algemeen",
        "settings_tab_backup":          "💾  Backup",
        "settings_tab_display":         "🖥  Weergave",
        "settings_tab_endpoints":       "🖥  Eindapparaten",
        "settings_tab_device_types":    "🗄  Device types",      # F2

        # Settings — groepen algemeen
        "settings_group_language":      "Taal",                  # F3
        "settings_group_datasource":    "Databron",              # F3

        # Settings — databron (F3)
        "settings_ds_use_network":      "Netwerkpad gebruiken als databron",
        "settings_ds_hint":             "Als het netwerkpad niet bereikbaar is, wordt automatisch teruggevallen op de lokale data.",
        "settings_ds_browse_title":     "Databron map kiezen",
        "settings_ds_path_ok":          "Pad bereikbaar en beschrijfbaar",
        "settings_ds_path_fail":        "Pad niet bereikbaar of niet beschrijfbaar",
        "settings_ds_active":           "Actieve databron",

        # Settings — backup
        "settings_backup_group":    "Backup",
        "settings_backup_enable":   "Automatische backup inschakelen",
        "settings_backup_path":     "Netwerkpad:",
        "settings_backup_history":  "History bewaren (tijdgestempelde kopieën)",
        "settings_backup_max":      "Maximum aantal backups:",
        "settings_backup_now":      "💾  Nu backup maken",
        "settings_backup_test":     "Test",
        "settings_unit_height":     "Rack unit hoogte:",
        "settings_unit_hint":       "Wijzigingen zijn zichtbaar na herstart.",
        # Settings — standaard exportmap — H1d
        "settings_export_folder":             "Standaard exportmap",
        "settings_export_folder_placeholder": "Kies een map...",
        "settings_export_folder_hint":        "Exportbestanden worden hier standaard opgeslagen. Leeg = elke keer vragen.",
        "settings_export_folder_clear":       "Map wissen",
        "settings_lang_hint":       "De applicatie herlaadt de UI-labels na opslaan.",
        "settings_path_ok_title":   "Pad test",
        "settings_path_fail_title": "Pad test",

        # Settings — eindapparaat-types
        "settings_ep_hint":             "Beheer de lijst van eindapparaat-types. Deze types verschijnen in het eindapparaat-dialoogvenster.",
        "settings_ep_key":              "Interne sleutel",
        "settings_ep_key_hint":         "Alleen kleine letters, cijfers en underscore. Niet wijzigbaar na aanmaken.",
        "settings_ep_key_locked":       "Sleutel kan niet gewijzigd worden (al in gebruik in data).",
        "settings_ep_key_exists":       "Deze sleutel bestaat al.",
        "settings_ep_key_invalid":      "Sleutel mag alleen kleine letters, cijfers en _ bevatten.",
        "settings_ep_label_nl":         "Label NL",
        "settings_ep_label_en":         "Label EN",
        "settings_ep_new_title":        "Nieuw eindapparaat-type",
        "settings_ep_edit_title":       "Eindapparaat-type bewerken",
        "settings_ep_restore":          "Standaard herstellen",
        "settings_ep_restore_confirm":  "Alle eigen types verwijderen en standaardlijst herstellen?",

        # Settings — device types (F2)
        "settings_dt_hint":             "Beheer de types netwerkdevices. De FRONT/BACK waarden zijn de standaard poorttelling bij het aanmaken van een nieuw device.",
        "settings_dt_restore":          "Standaardlijst herstellen",
        "settings_dt_restore_confirm":  "Alle wijzigingen gaan verloren. Doorgaan?",
        "settings_dt_new_title":        "Nieuw device type",
        "settings_dt_edit_title":       "Device type bewerken",
        "settings_dt_front_ports":      "Standaard FRONT poorten",
        "settings_dt_back_ports":       "Standaard BACK poorten",
        "settings_dt_ports_hint":       "Standaardwaarden — worden vooringevuld bij aanmaken nieuw device.",

        # Wire detail
        "wire_delete_btn":          "🗑  Verbinding verwijderen",
        "wire_delete_confirm":      "Verbinding verwijderen?",
        "wire_edit_btn":            "✏  Bewerken",
        "title_edit_connection":    "Verbinding bewerken",
        "conn_label_placeholder":   "Optioneel label of naam...",
        "conn_notes_placeholder":   "Optionele notitie...",
        "msg_connection_updated":   "Verbinding bijgewerkt.",
        "rack_occupancy_tooltip":   "Bezettingsgraad",
        "wire_arrow":               " ──► ",

        # Search
        "search_hint":              "↵ Enter of dubbelklik om naar object te navigeren",
        "search_no_results":        "Geen resultaten.",
        "search_result_count_one":  "1 resultaat",
        "search_result_count":      "{n} resultaten",

        # App info
        "app_version":              "Networkmap Creator v1.0.0",
        "app_ready":                "Klaar.",

        # Bewerken popup (rack context)
        "edit_rack_self":           "🗄  Rack bewerken",
        "edit_device_in_rack":      "💻  Toestel bewerken",
        "delete_rack_self":         "🗄  Rack verwijderen",
        "delete_device_in_rack":    "💻  Toestel verwijderen",
        "delete_rack_confirm":      "Rack verwijderen? Alle devices, poorten en verbindingen worden ook verwijderd.",
        "delete_device_confirm":    "Toestel verwijderen? Alle poorten en verbindingen worden ook verwijderd.",
        "duplicate_choose":         "Toestel kiezen om te dupliceren:",

        # Context menu boom
        "ctx_new_room":             "🚪  Nieuwe ruimte",
        "ctx_new_rack":             "🗄  Nieuw rack",
        "ctx_new_outlet":           "🌐  Nieuw wandpunt",
        "ctx_new_device":           "💻  Nieuw toestel",
        "ctx_edit":                 "✏  Bewerken",
        "ctx_delete":               "🗑  Verwijderen",
        "ctx_edit_device":          "✏  Toestel bewerken",
        "ctx_delete_device":        "🗑  Toestel verwijderen",
        "ctx_edit_outlet":          "✏  Wandpunt bewerken",
        "ctx_delete_outlet":        "🗑  Wandpunt verwijderen",

        # Site wandpunten-overzicht (E3)
        "tree_site_outlets":            "Alle wandpunten",
        "site_outlets_title":           "Wandpunten overzicht",
        "site_outlets_room":            "Ruimte",
        "site_outlets_no_connection":   "Geen verbinding",
        "site_outlets_trace":           "Trace",
        "site_outlets_empty":           "Geen wandpunten gevonden in deze site.",

        # Outlet locator (E3)
        "menu_outlet_locator":          "🌐  Wandpunten zoeken",
        "outlet_filter_placeholder":    "Filter op naam of locatie...",
        "outlet_no_trace":              "Geen verbinding",
        "outlet_locator_choose_room":   "← Kies een ruimte om wandpunten te tonen",
        "outlet_locator_no_outlets":    "Geen wandpunten gevonden in deze ruimte",

        # Poort context menu + verbinding met wandpunt (E3)
        "ctx_connect_to_outlet":        "🌐  Verbinden met wandpunt...",
        "ctx_disconnect_port":          "✂  Verbinding verwijderen",
        "dlg_connect_outlet_title":     "Poort verbinden met wandpunt",
        "err_no_outlet_selected":       "Selecteer eerst een wandpunt.",
        "warn_outlet_already_connected": "Dit wandpunt is al verbonden. Toch doorgaan?",

        # Cross-rack trace (E5)
        "trace_racks":                  "Racks in trace",

        # --- Fase D: update check bij opstarten ---
        "update_check_url":         "Update check URL",
        "update_check_url_hint":    "Leeg = standaard GitHub URL gebruiken.",
        "update_available_title":   "Update beschikbaar",
        "update_available_msg":     "Versie {version} is beschikbaar.\nWil je naar GitHub gaan om te downloaden?",
        "update_goto_github":       "Naar GitHub",
        "update_later":             "Later",
        
        # --- Feature and bug report
        "menubar_report":           "Rapporteren",
        "menu_report_bug":          "🐞 Bug melden...",
        "menu_report_feature":      "✨ Feature aanvragen...",
        "report_dialog_title":      "Bug of Feature melden",
        "report_label_type":        "Type melding:",
        "report_type_bug":          "Bugmelding",
        "report_type_feature":      "Feature-aanvraag",
        "report_type_label":        "Type",
        "report_label_name":        "Je naam:",
        "report_placeholder_name":  "Voornaam Achternaam",
        "report_label_description": "Omschrijving:",
        "report_placeholder_description": "Beschrijf de bug of feature zo duidelijk mogelijk...",
        "report_btn_submit":        "Verzenden",
        "report_btn_sending":       "Bezig met verzenden...",
        "report_preview_title":     "Voorvertoning",
        "report_confirm_send":      "Doorgaan met verzenden?",
        "report_success_title":     "Verzonden",
        "report_success_msg":       "Melding succesvol verzonden:",
        "report_err_no_name":       "Vul je naam in.",
        "report_err_no_description":"Vul een beschrijving in.",
        "report_err_no_connection": "Geen internetverbinding.",
        "report_err_github":        "GitHub fout:",
        "report_err_unknown":       "Onbekende fout:",
        
        # --- Rapporteren menu ---
        "menubar_report":             "Rapporteren",
        "menu_report_bug":            "🐞 Bug melden...",
        "menu_report_feature":        "✨ Feature aanvragen...",
        "menu_report_cases":          "📋 Open cases",

        # --- BugReportDialog ---
        "report_dialog_title":        "Bug of Feature melden",
        "report_label_type":          "Type melding:",
        "report_type_bug":            "Bugmelding",
        "report_type_feature":        "Feature-aanvraag",
        "report_type_label":          "Type",
        "report_label_name":          "Je naam:",
        "report_placeholder_name":    "Voornaam Achternaam",
        "report_label_description":   "Omschrijving:",
        "report_placeholder_description": "Beschrijf de bug of feature zo duidelijk mogelijk...",
        "report_btn_submit":          "Verzenden",
        "report_btn_sending":         "Bezig met verzenden...",
        "report_preview_title":       "Voorvertoning",
        "report_confirm_send":        "Doorgaan met verzenden?",
        "report_success_title":       "Verzonden",
        "report_success_msg":         "Melding succesvol verzonden:",
        "report_err_no_name":         "Vul je naam in.",
        "report_err_no_description":  "Vul een beschrijving in.",
        "report_err_no_connection":   "Geen internetverbinding.",
        "report_err_github":          "GitHub fout:",
        "report_err_unknown":         "Onbekende fout:",

        # --- GithubCasesDialog ---
        "cases_dialog_title":         "Open cases",
        "cases_loading":              "Laden...",
        "cases_loaded":               "Geladen",
        "cases_tab_bugs":             "Bugs",
        "cases_tab_features":         "Features",
        "cases_col_title":            "Titel",
        "cases_col_labels":           "Labels",
        "cases_col_branch":           "Branch",
        "cases_col_date":             "Datum",
        "cases_btn_refresh":          "Vernieuwen",
        "cases_btn_open_browser":     "Openen in browser",
        "cases_no_selection":         "Selecteer eerst een rij.",
        
        # --- rack sortering
        "rack_numbering_label":   "Nummering:",
        "rack_numbering_top_down":  "1 bovenaan (standaard)",
        "rack_numbering_bottom_up": "1 onderaan (professioneel)",
        "label_ports_per_row": "Poorten per rij:",
        "label_sfp_ports": "SFP poorten:",
        "ctx_ports_device": "Poorten beheren",
        # --- VLAN
        "vlan_report_no_vlans":     "Geen VLAN toewijzingen gevonden.",
        "vlan_report_title":        "VLAN rapport",
        "vlan_manager_title":       "VLAN beheer",
        "vlan_conflict_title":      "VLAN conflict",
        "vlan_propagate_confirm":   "Propageer naar hele trace?",

        # --- Wandpunt locaties (settings) — 1.7.0
        "settings_tab_outlet_locations": "🌐  Wandpunt locaties",
        "settings_loc_hint":             "Beheer de lijst van locaties voor wandpunten. Deze opties verschijnen in het wandpunt-dialoogvenster.",
        "settings_loc_restore":          "Standaard herstellen",
        "settings_loc_restore_confirm":  "Alle eigen locaties verwijderen en standaardlijst herstellen?",
        "settings_loc_new_title":        "Nieuwe locatie",
        "settings_loc_edit_title":       "Locatie bewerken",
 
    },

    # -------------------------------------------------------------------------
    # Engels
    # -------------------------------------------------------------------------
    "en": {
        # App
        "app_title":                "Networkmap Creator",

        # Toolbar / menu
        "menu_new":                 "New",
        "menu_edit":                "Edit",
        "menu_delete":              "Delete",
        "menu_duplicate":           "Duplicate",
        "menu_search":              "Search",
        "menu_connect":             "Connection",
        "menu_import":              "Import",
        "menu_export":              "Export",
        "menu_export_image":        "Export image",                  # G2
        "menu_export_pdf":          "Export PDF",                    # G1
        "menu_export_report":       "Report (Word)",                 # G3
        "menu_settings":            "Settings",

        # Menubar — H1
        "menubar_file":             "File",
        "menubar_inexport":         "Im/Export",
        "menubar_help":             "Help",
        "menubar_quit":             "Quit",

        # Help window — H1
        "help_title":               "Help",
        "help_tab_shortcuts":       "Shortcuts",
        "help_tab_guide":           "User Guide",
        "help_tab_version":         "About",
        "help_shortcuts_intro":     "Overview of all keyboard shortcuts in Networkmap Creator.",
        "help_col_shortcut":        "Shortcut",
        "help_col_action":          "Action",
        "help_shortcut_esc":        "Cancel connection mode",
        "help_version_label":       "Version",
        "help_author_label":        "Author",
        "help_built_with":          "Built with",
        "help_license_label":       "License",
        "help_license_value":       "Internal use — CGK",

        # Version info description — H1
        "help_app_desc":            "Network infrastructure management — sites, rooms, racks, devices, wall outlets and connections.",

        # Object labels
        "label_site":               "Site",
        "label_room":               "Room",
        "label_rack":               "Rack",
        "label_device":             "Device",
        "label_port":               "Port",
        "label_front":              "Front",
        "label_back":               "Back",
        "label_wall_outlet":        "Wall Outlet",
        "label_endpoint":           "Endpoint",
        "label_cable":              "Cable",
        "label_connection":         "Connection",
        "label_trace":              "Trace",

        # Velden
        "label_name":               "Name",
        "label_type":               "Type",
        "label_brand":              "Brand",
        "label_model":              "Model",
        "label_ip":                 "IP Address",
        "label_subnet":             "Subnet Mask",
        "label_mac":                "MAC Address",
        "label_serial":             "Serial Number",
        "label_notes":              "Notes",
        "label_floor":              "Floor",
        "label_place":              "Location",
        "label_place_hint":         "Building, wing or zone (optional)",
        "label_room_hint":          "Floor and Location appear in the status bar and tooltips.",
        "label_location":           "Location",
        "label_units":              "Height (U)",
        "label_u_start":            "Start Position (U)",
        "label_front_ports":        "Front Ports",
        "label_back_ports":         "Back Ports",
        "label_total_units":        "Total Height (U)",
        "label_cable_type":         "Cable Type",
        "label_endpoint_type":      "Endpoint Type",
        "label_location_desc":      "Location Description",
        "label_language":           "Language",
        "label_backup_path":        "Backup Folder (network path)",
        "label_backup_enabled":     "Enable Backup",
        "label_max_backups":        "Max. Backups to Keep",
        "label_rack_unit_height":   "Unit Height (pixels)",
        "label_rack_unit_width":    "Rack Width (pixels)",

        # Kabeltype DDL
        "cable_utp_cat5e":          "UTP Cat5e",
        "cable_utp_cat6":           "UTP Cat6",
        "cable_utp_cat6a":          "UTP Cat6a",
        "cable_fiber_sm":           "Fiber SM",
        "cable_fiber_mm":           "Fiber MM",
        "cable_dak":                "DAK Cable",
        "cable_other":              "Other",

        # Device type DDL
        "device_patch_panel":       "Patch Panel",
        "device_switch":            "Switch",
        "device_router":            "Router",
        "device_firewall":          "Firewall",
        "device_server":            "Server",
        "device_kvm":               "KVM Switch",
        "device_ups":               "UPS",
        "device_pdu":               "PDU",
        "device_media_conv":        "Media Converter",
        "device_patchpanel":        "Patch Panel",
        "device_modem":             "Modem",
        "device_other":             "Other",
        "device_cable_management":  "Cable Management",
        "device_distribution_plug": "Distribution Plug",
        "device_fiber":             "Fiber Converter",
        "device_nuc1":              "NUC / Mini-PC",
        "device_sonos_server":      "Sonos Server",

        # Endpoint type DDL
        "endpoint_pc":              "PC",
        "endpoint_laptop":          "Laptop",
        "endpoint_thin_client":     "Thin Client",
        "endpoint_printer":         "Printer",
        "endpoint_plotter":         "Plotter",
        "endpoint_scanner":         "Scanner",
        "endpoint_all_in_one":      "All-in-One",
        "endpoint_phone":           "IP Phone",
        "endpoint_ip_camera":       "IP Camera",
        "endpoint_access_point":    "Access Point",
        "endpoint_nas":             "NAS",
        "endpoint_other":           "Other",

        # Knoppen
        "btn_save":                 "Save",
        "btn_cancel":               "Cancel",
        "btn_add":                  "Add",
        "btn_close":                "Close",
        "btn_browse":               "Browse...",
        "btn_new_site":             "New Site",
        "btn_new_room":             "New Room",
        "btn_new_rack":             "New Rack",
        "btn_new_device":           "New Device",
        "btn_new_outlet":           "New Wall Outlet",
        "btn_new_endpoint":         "New Endpoint",
        "btn_new_connection":       "New Connection",

        # Statusberichten
        "msg_confirm_delete":       "Are you sure you want to delete this?",
        "msg_confirm_delete_title": "Confirm Delete",
        "msg_backup_ok":            "Backup created successfully.",
        "msg_backup_fail":          "Backup failed. Check the network path.",
        "msg_import_ok":            "Import successful.",
        "msg_import_fail":          "Import failed. Check the file.",
        "msg_export_ok":            "Export successful.",
        "msg_export_fail":          "Export failed.",
        "msg_save_ok":              "Saved.",
        "msg_save_fail":            "Save failed.",
        "msg_invalid_json":         "Invalid JSON file.",
        "msg_port_in_use":          "This port is already in use.",
        "msg_no_selection":         "No selection made.",
        "msg_connect_select_a":     "Select first port...",
        "msg_connect_select_b":     "Select second port...",
        "msg_connect_cancel":       "Connection mode cancelled.",
        "msg_connect_cancelled":    "Connection mode cancelled (ESC).",   # F1
        "msg_connect_done":         "Connection created.",
        "msg_search_no_results":    "No results found.",
        "msg_language_restart":     "Language change applied immediately.",
        "msg_image_exported":       "Image saved",                        # G2
        "msg_image_export_failed":  "Failed to save image",               # G2
        "msg_pdf_exported":         "PDF saved",                          # G1
        "msg_pdf_export_failed":    "Failed to save PDF",                 # G1
        "msg_report_exported":      "Report saved",                       # G3
        "msg_report_export_failed": "Failed to save report",              # G3

        # Titels vensters / dialogs
        "title_settings":           "Settings",
        "title_search":             "Search",
        "title_new_site":           "Create Site",
        "title_edit_site":          "Edit Site",
        "title_new_room":           "Create Room",
        "title_edit_room":          "Edit Room",
        "title_new_rack":           "Create Rack",
        "title_edit_rack":          "Edit Rack",
        "title_new_device":         "Create Device",
        "title_edit_device":        "Edit Device",
        "title_new_outlet":         "Create Wall Outlet",
        "title_edit_outlet":        "Edit Wall Outlet",
        "title_new_endpoint":       "Create Endpoint",
        "title_edit_endpoint":      "Edit Endpoint",
        "title_new_connection":     "Create Connection",
        "title_wire_detail":        "Connection Detail",
        "title_wall_outlets":       "Wall Outlets",

        # Boom (tree view)
        "tree_wall_outlets":        "Wall Outlets",
        "tree_no_endpoint":         "(no endpoint)",

        # Trace labels
        "trace_from":               "From",
        "trace_to":                 "To",
        "trace_via":                "Via",
        "trace_cable":              "Cable",
        "trace_room":               "Room",
        "trace_direction":          "Direction",
        "trace_no_connection":      "No connection on this port.",
        "trace_internal":           "Internal cross-connect",

        # Import/export
        "import_mode_replace":      "Replace",
        "import_mode_merge":        "Merge",
        "import_mode_label":        "Import Mode",
        "export_filename_prefix":   "networkmap_export",

        # Export renderer — kolommen (G1+G2)
        "export_table_title":       "Connection table",
        "export_col_port":          "Port",
        "export_col_side":          "Side",
        "export_col_dest":          "Connected to",
        "export_col_outlet":        "Wall outlet",
        "export_col_location":      "Location",
        "export_col_trace":         "Trace → Endpoint",
        "err_no_view_to_export":    "No active view to export.",

        # Zoeken
        "search_placeholder":       "Search by name, IP, MAC, serial...",
        "search_result_device":     "Device",
        "search_result_port":       "Port",
        "search_result_outlet":     "Wall Outlet",
        "search_result_endpoint":   "Endpoint",

        # Foutmeldingen
        "err_field_required":       "This field is required.",
        "err_outlet_duplicate_name": "A wall outlet named '{name}' already exists in this room.",
        "err_invalid_number":       "Please enter a valid number.",
        "err_path_not_found":       "Path not found.",
        "err_file_not_found":       "File not found.",
        "err_unknown":              "Unknown error.",
        "err_same_port":            "Port A and B are the same port.",
        "err_port_in_use":          "This port is already in use.",
        "err_no_selection":         "Please select an object first.",
        "err_select_site_for_room": "Select a site first to add a room.",
        "err_select_room_for_rack": "Select a room first to add a rack.",
        "err_select_room_for_outlet": "Select a room first to add a wall outlet.",
        "err_select_for_edit":      "Select a site, room or rack to edit.",
        "err_select_rack_for_device": "Select a rack to edit or delete a device.",
        "err_rack_no_devices":      "This rack contains no devices.",
        "err_select_outlet":        "Select an individual wall outlet to delete.",
        "err_backup_no_path":       "Please set a network path first.",
        "err_backup_path_required": "Backup is enabled but no path is set.",
        "err_corrupt_data":         "Data file is corrupt or unreadable.",
        "err_save_failed":          "Save failed. Check disk space.",
        "err_ds_path_required":     "Network data is enabled but no path is set.",  # F3

        # Status / info berichten
        "msg_ready":                "Ready.",
        "msg_connection_deleted":   "Connection deleted.",
        "msg_device_deleted":       "Device deleted.",
        "msg_device_updated":       "Device updated.",
        "msg_rack_deleted":         "Rack deleted.",
        "msg_exported_to":          "Exported to:",
        "msg_export_failed":        "Export failed.",
        "msg_import_replace_done":  "Import successful (replaced).",
        "msg_import_merge_done":    "Import successful — {added} added, {skipped} skipped.",
        "msg_path_ok":              "Path is accessible and writable.",
        "msg_language_applied":     "Language change applied immediately.",

        # Settings venster — tabbladen
        "settings_tab_general":         "⚙  General",
        "settings_tab_backup":          "💾  Backup",
        "settings_tab_display":         "🖥  Display",
        "settings_tab_endpoints":       "🖥  Endpoints",
        "settings_tab_device_types":    "🗄  Device Types",     # F2

        # Settings — groepen algemeen
        "settings_group_language":      "Language",             # F3
        "settings_group_datasource":    "Data Source",          # F3

        # Settings — databron (F3)
        "settings_ds_use_network":      "Use network path as data source",
        "settings_ds_hint":             "If the network path is not available, the app automatically falls back to local data.",
        "settings_ds_browse_title":     "Choose data source folder",
        "settings_ds_path_ok":          "Path is accessible and writable",
        "settings_ds_path_fail":        "Path is not accessible or not writable",
        "settings_ds_active":           "Active data source",

        # Settings — backup
        "settings_backup_group":    "Backup",
        "settings_backup_enable":   "Enable automatic backup",
        "settings_backup_path":     "Network path:",
        "settings_backup_history":  "Keep history (timestamped copies)",
        "settings_backup_max":      "Maximum number of backups:",
        "settings_backup_now":      "💾  Backup now",
        "settings_backup_test":     "Test",
        "settings_unit_height":     "Rack unit height:",
        "settings_unit_hint":       "Changes are visible after restart.",
        # Settings — default export folder — H1d
        "settings_export_folder":             "Default Export Folder",
        "settings_export_folder_placeholder": "Choose a folder...",
        "settings_export_folder_hint":        "Export files are saved here by default. Empty = ask every time.",
        "settings_export_folder_clear":       "Clear folder",
        "settings_lang_hint":       "The application reloads UI labels after saving.",
        "settings_path_ok_title":   "Path test",
        "settings_path_fail_title": "Path test",

        # Settings — eindapparaat-types
        "settings_ep_hint":             "Manage the list of endpoint types. These types appear in the endpoint dialog.",
        "settings_ep_key":              "Internal key",
        "settings_ep_key_hint":         "Lowercase letters, digits and underscore only. Cannot be changed after creation.",
        "settings_ep_key_locked":       "Key cannot be changed (already used in data).",
        "settings_ep_key_exists":       "This key already exists.",
        "settings_ep_key_invalid":      "Key may only contain lowercase letters, digits and _.",
        "settings_ep_label_nl":         "Label NL",
        "settings_ep_label_en":         "Label EN",
        "settings_ep_new_title":        "New Endpoint Type",
        "settings_ep_edit_title":       "Edit Endpoint Type",
        "settings_ep_restore":          "Restore Defaults",
        "settings_ep_restore_confirm":  "Delete all custom types and restore the default list?",

        # Settings — device types (F2)
        "settings_dt_hint":             "Manage network device types. The FRONT/BACK values are the default port count when creating a new device.",
        "settings_dt_restore":          "Restore Default List",
        "settings_dt_restore_confirm":  "All changes will be lost. Continue?",
        "settings_dt_new_title":        "New Device Type",
        "settings_dt_edit_title":       "Edit Device Type",
        "settings_dt_front_ports":      "Default FRONT ports",
        "settings_dt_back_ports":       "Default BACK ports",
        "settings_dt_ports_hint":       "Default values — pre-filled when creating a new device.",

        # Wire detail
        "wire_delete_btn":          "🗑  Delete Connection",
        "wire_delete_confirm":      "Delete connection?",
        "wire_edit_btn":            "✏  Edit",
        "title_edit_connection":    "Edit Connection",
        "conn_label_placeholder":   "Optional label or name...",
        "conn_notes_placeholder":   "Optional note...",
        "msg_connection_updated":   "Connection updated.",
        "rack_occupancy_tooltip":   "Occupancy",
        "wire_arrow":               " ──► ",

        # Search
        "search_hint":              "↵ Enter or double-click to navigate to object",
        "search_no_results":        "No results.",
        "search_result_count_one":  "1 result",
        "search_result_count":      "{n} results",

        # App info
        "app_version":              "Networkmap Creator v1.0.0",
        "app_ready":                "Ready.",

        # Bewerken popup (rack context)
        "edit_rack_self":           "🗄  Edit Rack",
        "edit_device_in_rack":      "💻  Edit Device",
        "delete_rack_self":         "🗄  Delete Rack",
        "delete_device_in_rack":    "💻  Delete Device",
        "delete_rack_confirm":      "Delete rack? All devices, ports and connections will also be deleted.",
        "delete_device_confirm":    "Delete device? All ports and connections will also be deleted.",
        "duplicate_choose":         "Choose device to duplicate:",

        # Context menu boom
        "ctx_new_room":             "🚪  New Room",
        "ctx_new_rack":             "🗄  New Rack",
        "ctx_new_outlet":           "🌐  New Wall Outlet",
        "ctx_new_device":           "💻  New Device",
        "ctx_edit":                 "✏  Edit",
        "ctx_delete":               "🗑  Delete",
        "ctx_edit_device":          "✏  Edit Device",
        "ctx_delete_device":        "🗑  Delete Device",
        "ctx_edit_outlet":          "✏  Edit Wall Outlet",
        "ctx_delete_outlet":        "🗑  Delete Wall Outlet",

        # Site wall outlets overview (E3)
        "tree_site_outlets":            "All Wall Outlets",
        "site_outlets_title":           "Wall Outlets Overview",
        "site_outlets_room":            "Room",
        "site_outlets_no_connection":   "No connection",
        "site_outlets_trace":           "Trace",
        "site_outlets_empty":           "No wall outlets found in this site.",

        # Outlet locator (E3)
        "menu_outlet_locator":          "🌐  Find Wall Outlets",
        "outlet_filter_placeholder":    "Filter by name or location...",
        "outlet_no_trace":              "No connection",
        "outlet_locator_choose_room":   "← Choose a room to show wall outlets",
        "outlet_locator_no_outlets":    "No wall outlets found in this room",

        # Port context menu + connect to outlet (E3)
        "ctx_connect_to_outlet":        "🌐  Connect to wall outlet...",
        "ctx_disconnect_port":          "✂  Remove connection",
        "dlg_connect_outlet_title":     "Connect port to wall outlet",
        "err_no_outlet_selected":       "Please select a wall outlet first.",
        "warn_outlet_already_connected": "This wall outlet is already connected. Continue anyway?",

        # Cross-rack trace (E5)
        "trace_racks":                  "Racks in trace",

        # --- Phase D: update check on startup ---
        "update_check_url":         "Update check URL",
        "update_check_url_hint":    "Empty = use default GitHub URL.",
        "update_available_title":   "Update available",
        "update_available_msg":     "Version {version} is available.\nDo you want to go to GitHub to download?",
        "update_goto_github":       "Go to GitHub",
        "update_later":             "Later",
        
        # --- Feature and bug reporting
        "menubar_report":            "Report",
        "menu_report_bug":           "🐞 Report a bug...",
        "menu_report_feature":       "✨ Request a feature...",
        "report_dialog_title":       "Report Bug or Feature",
        "report_label_type":         "Report type:",
        "report_type_bug":           "Bug report",
        "report_type_feature":       "Feature request",
        "report_type_label":         "Type",
        "report_label_name":         "Your name:",
        "report_placeholder_name":   "First Last",
        "report_label_description":  "Description:",
        "report_placeholder_description": "Describe the bug or feature as clearly as possible...",
        "report_btn_submit":         "Submit",
        "report_btn_sending":        "Sending...",
        "report_preview_title":      "Preview",
        "report_confirm_send":       "Proceed with submission?",
        "report_success_title":      "Submitted",
        "report_success_msg":        "Report successfully submitted:",
        "report_err_no_name":        "Please enter your name.",
        "report_err_no_description": "Please enter a description.",
        "report_err_no_connection":  "No internet connection.",
        "report_err_github":         "GitHub error:",
        "report_err_unknown":        "Unknown error:",
        
        # --- Report menu ---
        "menubar_report":             "Report",
        "menu_report_bug":            "🐞 Report a bug...",
        "menu_report_feature":        "✨ Request a feature...",
        "menu_report_cases":          "📋 Open cases",

        # --- BugReportDialog ---
        "report_dialog_title":        "Report Bug or Feature",
        "report_label_type":          "Report type:",
        "report_type_bug":            "Bug report",
        "report_type_feature":        "Feature request",
        "report_type_label":          "Type",
        "report_label_name":          "Your name:",
        "report_placeholder_name":    "First Last",
        "report_label_description":   "Description:",
        "report_placeholder_description": "Describe the bug or feature as clearly as possible...",
        "report_btn_submit":          "Submit",
        "report_btn_sending":         "Sending...",
        "report_preview_title":       "Preview",
        "report_confirm_send":        "Proceed with submission?",
        "report_success_title":       "Submitted",
        "report_success_msg":         "Report successfully submitted:",
        "report_err_no_name":         "Please enter your name.",
        "report_err_no_description":  "Please enter a description.",
        "report_err_no_connection":   "No internet connection.",
        "report_err_github":          "GitHub error:",
        "report_err_unknown":         "Unknown error:",

        # --- GithubCasesDialog ---
        "cases_dialog_title":         "Open cases",
        "cases_loading":              "Loading...",
        "cases_loaded":               "Loaded",
        "cases_tab_bugs":             "Bugs",
        "cases_tab_features":         "Features",
        "cases_col_title":            "Title",
        "cases_col_labels":           "Labels",
        "cases_col_branch":           "Branch",
        "cases_col_date":             "Date",
        "cases_btn_refresh":          "Refresh",
        "cases_btn_open_browser":     "Open in browser",
        "cases_no_selection":         "Select a row first.",
        
        # --- rack sortering
        "rack_numbering_label":   "Numbering:",
        "rack_numbering_top_down":  "1 at top (default)",
        "rack_numbering_bottom_up": "1 at bottom (professional)",
        "label_ports_per_row": "Ports per row:",
        "label_sfp_ports": "SFP ports:",
        "ctx_ports_device": "Manage ports",
        # --- VLAN
        "vlan_report_no_vlans":     "No VLAN assignments found.",
        "vlan_report_title":        "VLAN report",
        "vlan_manager_title":       "VLAN management",
        "vlan_conflict_title":      "VLAN conflict",
        "vlan_propagate_confirm":   "Propagate to entire trace?",

        # --- Wall outlet locations (settings) — 1.7.0
        "settings_tab_outlet_locations": "🌐  Outlet Locations",
        "settings_loc_hint":             "Manage the list of locations for wall outlets. These options appear in the wall outlet dialog.",
        "settings_loc_restore":          "Restore Defaults",
        "settings_loc_restore_confirm":  "Delete all custom locations and restore the default list?",
        "settings_loc_new_title":        "New Location",
        "settings_loc_edit_title":       "Edit Location",

    },
}

# ---------------------------------------------------------------------------
# Actieve taal — wordt ingesteld via set_language()
# ---------------------------------------------------------------------------

_active_language: str = "nl"


def set_language(lang: str) -> bool:
    global _active_language
    if lang in TRANSLATIONS:
        _active_language = lang
        return True
    return False


def get_language() -> str:
    return _active_language


def get_available_languages() -> list[str]:
    return list(TRANSLATIONS.keys())


def t(key: str) -> str:
    """
    Geeft de vertaling terug voor de opgegeven sleutel in de actieve taal.
    Valt terug op NL als de sleutel niet bestaat in de actieve taal.

    Extra fallback voor 'device_*' sleutels:
    Als de key niet in TRANSLATIONS staat (bv. een custom device type zoals
    'device_cable_management'), wordt het label opgehaald uit settings_storage.
    Zo worden custom device types altijd correct weergegeven zonder dat ze
    handmatig in i18n.py toegevoegd moeten worden.
    """
    result = TRANSLATIONS[_active_language].get(key)
    if result is not None:
        return result
    result = TRANSLATIONS["nl"].get(key)
    if result is not None:
        return result

    # Fallback voor custom device types: zoek label in settings_storage
    if key.startswith("device_"):
        dev_type_key = key[len("device_"):]  # bv. "cable_management"
        try:
            from app.helpers.settings_storage import load_device_types
            lang_field = f"label_{_active_language}"
            for dt in load_device_types():
                if dt.get("key") == dev_type_key:
                    label = dt.get(lang_field) or dt.get("label_nl") or dt.get("key", dev_type_key)
                    return label
        except Exception:
            pass
        # Laatste fallback: key zonder prefix, underscores als spaties, title case
        return dev_type_key.replace("_", " ").title()

    return f"[{key}]"