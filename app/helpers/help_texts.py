# =============================================================================
# Networkmap_Creator
# File:    app/helpers/help_texts.py
# Role:    H1 — Vertaalde teksten voor het Help venster (los van i18n.py)
# Version: 1.2.0
# Author:  Barremans
# Changes: 1.2.0 — Gebruiksaanwijzing volledig herzien (K4):
#                  · Aan de slag: "knop Nieuw" vervangen door contextmenu-verwijzing
#                  · Rack beheer: toolbar-knop "Verbinding" verwijderd (niet meer aanwezig)
#                  · Verbindingen: herschreven naar poort-contextmenu + Smart Connect
#                  · Wandpunten: filters beschreven (zoekbalk, ruimte, locatie) + Ctrl+E
#                  · Exporteren: "JSON export" → "Exporteren Data" via Im/Export (Ctrl+I)
#                  · Backup & instellingen: menupad gecorrigeerd naar Ctrl+S / Instellingen
#          1.1.0 — Sneltoetsen bijgewerkt: nieuwe Ctrl+N/E/I/R/S/G/H en
#                  Ctrl+Shift+R; verouderde Ctrl+W/Ctrl+Shift+E verwijderd
#                  Guide-teksten aangepast aan huidige sneltoetsen
# =============================================================================

from app.helpers.i18n import get_language

# ---------------------------------------------------------------------------
# Sneltoetsen — (sneltoets, vertaalsleutel voor omschrijving)
# ---------------------------------------------------------------------------

SHORTCUTS = [
    # Navigatie / zoeken
    ("Ctrl+F",       "menu_search"),
    ("Ctrl+B",       "menu_floorplan_view"),
    # Aanmaken
    ("Ctrl+N",       "help_shortcut_new_outlet"),
    ("Ctrl+E",       "help_shortcut_new_endpoint"),
    # Menu openen
    ("Ctrl+I",       "menubar_inexport"),
    ("Ctrl+R",       "menubar_report"),
    ("Ctrl+S",       "menu_settings"),
    ("Ctrl+G",       "menu_floorplan"),
    ("Ctrl+H",       "menubar_help"),
    # Export
    ("Ctrl+Shift+R", "menu_export_report"),
    # Algemeen
    ("Delete",       "menu_delete"),
    ("ESC",          "help_shortcut_esc"),
    ("F1",           "help_title"),
]

# ---------------------------------------------------------------------------
# Gebruiksaanwijzing secties — per taal
# Elke sectie: {"title": str, "body": str (HTML toegestaan)}
# ---------------------------------------------------------------------------

_GUIDE_NL = [
    {
        "title": "Aan de slag",
        "body": (
            "De hiërarchie in Networkmap Creator is:<br>"
            "<b>Sites → Ruimtes → Racks → Devices → Poorten</b><br>"
            "en parallel: <b>Ruimtes → Wandpunten → Eindapparaten</b><br><br>"
            "Maak een <b>Site</b> aan via <b>rechtermuisklik</b> in de lege boom links "
            "en kies <i>Nieuwe site</i>.<br>"
            "Voeg daarna <b>Ruimtes</b> toe aan de site, <b>Racks</b> aan de ruimtes "
            "en <b>Devices</b> aan de racks — telkens via het contextmenu op het bovenliggende item.<br><br>"
            "De data wordt automatisch opgeslagen in het ingestelde JSON-bestand. "
            "Gebruik <b>Ctrl+I</b> (Im/Export) voor handmatige export of import."
        ),
    },
    {
        "title": "Boomstructuur (links)",
        "body": (
            "De boom toont de volledige hiërarchie:<br>"
            "<b>Sites → Ruimtes → Racks + Wandpunten</b><br><br>"
            "Klik op een item om het te tonen in het middengebied.<br>"
            "<b>Rechtermuisklik</b> op een item opent een contextmenu met beschikbare acties:<br><br>"
            "· <b>Site</b>: bewerken, nieuwe ruimte, verwijderen<br>"
            "· <b>Ruimte</b>: bewerken, nieuw rack, nieuw wandpunt, verwijderen<br>"
            "· <b>Rack</b>: bewerken, nieuw device, verwijderen<br>"
            "· <b>Wandpunten (groep)</b>: nieuw wandpunt, bekijk grondplan<br>"
            "· <b>Wandpunt</b>: bewerken, verwijderen"
        ),
    },
    {
        "title": "Rack beheer",
        "body": (
            "Klik op een <b>rack</b> in de boom om het te openen in het middengebied.<br>"
            "Elke U-positie toont het geplaatste device met zijn poorten.<br><br>"
            "Klik op een <b>poort</b> om de volledige verbindingstrace te zien in het zijpaneel rechtsonder.<br><br>"
            "<b>Rechtermuisklik op een device</b> biedt:<br>"
            "· Poorten beheren<br>"
            "· Toestel bewerken<br>"
            "· Dupliceren<br>"
            "· Toestel verwijderen<br><br>"
            "<b>Rechtermuisklik op een poort</b> biedt koppelacties — zie sectie <i>Verbindingen aanmaken</i>."
        ),
    },
    {
        "title": "Verbindingen aanmaken",
        "body": (
            "Verbindingen worden aangemaakt via <b>rechtermuisklik op een poort</b> in de rackweergave.<br><br>"
            "Beschikbare acties:<br>"
            "· <b>Koppelen aan wandpunt</b> — verbindt de poort met een fysiek wandpunt in een ruimte<br>"
            "· <b>Koppelen aan eindapparaat</b> — verbindt de poort direct met een eindapparaat<br>"
            "· <b>Verbinding verplaatsen</b> — wijzigt de bestemming van een bestaande verbinding<br>"
            "· <b>Verbinding verwijderen</b> — verbreekt de koppeling<br><br>"
            "Voor complexe koppelingen (wandpunt → eindapparaat) gebruik je het <b>Smart Connect</b> dialoog, "
            "bereikbaar via de poort-contextmenu.<br><br>"
            "Druk <b>ESC</b> om een lopende koppelactie te annuleren."
        ),
    },
    {
        "title": "Wandpunten",
        "body": (
            "Wandpunten zijn fysieke aansluitpunten in een ruimte (muurcontact, netwerkaansluiting).<br><br>"
            "<b>Aanmaken:</b><br>"
            "· Via het contextmenu op een <b>ruimte</b> in de boom: <i>Nieuw wandpunt</i><br>"
            "· Via sneltoets <b>Ctrl+N</b> (globaal nieuw wandpunt)<br><br>"
            "<b>Eindapparaat koppelen:</b><br>"
            "· Via het contextmenu op een poort in de rackweergave<br>"
            "· Of via sneltoets <b>Ctrl+E</b> (nieuw eindapparaat globaal aanmaken)<br><br>"
            "<b>Overzicht en filters (wandpunten view):</b><br>"
            "Klik op een ruimte in de boom om het wandpuntenoverzicht te openen. "
            "Bovenaan vind je drie filters:<br>"
            "· <b>Zoekbalk</b> — zoekt op naam, locatie, eindapparaat, IP, serienummer<br>"
            "· <b>🚪 Ruimte</b> — filtert op ruimte (zoekbaar popup)<br>"
            "· <b>🌐 Locatie</b> — filtert op locatieomschrijving (zoekbaar popup)<br><br>"
            "Gebruik <b>Ctrl+B</b> of de toolbar voor het visuele grondplanoverzicht."
        ),
    },
    {
        "title": "Exporteren",
        "body": (
            "Alle exportfuncties zijn bereikbaar via het menu <b>Rapporteren (Ctrl+R)</b>.<br><br>"
            "<b>Word rapport (Ctrl+Shift+R)</b><br>"
            "Genereert een volledig Word-rapport (.docx) van de infrastructuur: "
            "alle sites, ruimtes, racks, devices, poorten, wandpunten en eindapparaten. "
            "Het rapport bevat ook VLAN-overzichten en een actieplan voor openstaande dataproblemen.<br><br>"
            "<b>Rack export Markdown</b><br>"
            "Exporteert een technisch rack-overzicht als Markdown-bestand (.md), "
            "inclusief poorttracing, wandpunten en aandachtspunten per rack.<br><br>"
            "<b>VLAN rapport</b><br>"
            "Toont een overzicht van alle VLANs met gekoppelde poorten en eindapparaten.<br><br>"
            "<b>Exporteren / Importeren Data (Ctrl+I)</b><br>"
            "Exporteert alle data als JSON-bestand voor backup of overdracht. "
            "Importeren laadt een eerder geëxporteerd bestand terug in."
        ),
    },
    {
        "title": "Backup & instellingen",
        "body": (
            "Open de instellingen via het menu <b>Instellingen (Ctrl+S)</b>.<br><br>"
            "Beschikbare opties:<br>"
            "· <b>Taal</b> — schakel tussen NL en EN<br>"
            "· <b>Databron</b> — stel het pad in naar het JSON-databestand (lokaal of netwerk)<br>"
            "· <b>Backup</b> — stel een netwerkpad in voor automatische backup bij elke opslag<br>"
            "· <b>Device types</b> — beheer de lijst van beschikbare toesteltypen<br>"
            "· <b>Eindapparaat types</b> — beheer de lijst van eindapparaattypes<br><br>"
            "De backup wordt automatisch aangemaakt bij elke opslag als het ingestelde pad bereikbaar is. "
            "Gebruik <b>Ctrl+I</b> (Im/Export) voor een handmatige JSON-export als extra backup."
        ),
    },
    {
        "title": "Zoeken",
        "body": (
            "Gebruik <b>Ctrl+F</b> of de zoekknop in de toolbar om de globale zoekbalk te openen.<br><br>"
            "Je kan zoeken op:<br>"
            "· <b>Naam</b> — van devices, wandpunten, eindapparaten<br>"
            "· <b>IP-adres</b> — van devices of eindapparaten<br>"
            "· <b>MAC-adres</b> — van eindapparaten<br>"
            "· <b>Serienummer</b> — van devices of eindapparaten<br><br>"
            "Dubbelklik op een resultaat om er direct naartoe te navigeren in de boom en het middengebied.<br><br>"
            "Voor gefilterd zoeken binnen het wandpuntenoverzicht (op ruimte of locatie): "
            "zie sectie <i>Wandpunten</i>."
        ),
    },
]

_GUIDE_EN = [
    {
        "title": "Getting started",
        "body": (
            "The hierarchy in Networkmap Creator is:<br>"
            "<b>Sites → Rooms → Racks → Devices → Ports</b><br>"
            "and in parallel: <b>Rooms → Wall Outlets → Endpoints</b><br><br>"
            "Create a <b>Site</b> by <b>right-clicking</b> in the empty tree on the left "
            "and selecting <i>New site</i>.<br>"
            "Then add <b>Rooms</b> to the site, <b>Racks</b> to the rooms, "
            "and <b>Devices</b> to the racks — always via the context menu on the parent item.<br><br>"
            "Data is saved automatically to the configured JSON file. "
            "Use <b>Ctrl+I</b> (Im/Export) for manual export or import."
        ),
    },
    {
        "title": "Tree structure (left panel)",
        "body": (
            "The tree shows the full hierarchy:<br>"
            "<b>Sites → Rooms → Racks + Wall Outlets</b><br><br>"
            "Click an item to display it in the centre area.<br>"
            "<b>Right-click</b> an item to open a context menu with available actions:<br><br>"
            "· <b>Site</b>: edit, new room, delete<br>"
            "· <b>Room</b>: edit, new rack, new wall outlet, delete<br>"
            "· <b>Rack</b>: edit, new device, delete<br>"
            "· <b>Wall Outlets (group)</b>: new wall outlet, view floorplan<br>"
            "· <b>Wall Outlet</b>: edit, delete"
        ),
    },
    {
        "title": "Rack management",
        "body": (
            "Click a <b>rack</b> in the tree to open it in the centre area.<br>"
            "Each U-position shows the installed device with its ports.<br><br>"
            "Click a <b>port</b> to see the full connection trace in the side panel at the bottom right.<br><br>"
            "<b>Right-click a device</b> offers:<br>"
            "· Manage ports<br>"
            "· Edit device<br>"
            "· Duplicate<br>"
            "· Delete device<br><br>"
            "<b>Right-click a port</b> offers linking actions — see section <i>Creating connections</i>."
        ),
    },
    {
        "title": "Creating connections",
        "body": (
            "Connections are created by <b>right-clicking a port</b> in the rack view.<br><br>"
            "Available actions:<br>"
            "· <b>Link to wall outlet</b> — connects the port to a physical wall outlet in a room<br>"
            "· <b>Link to endpoint</b> — connects the port directly to an endpoint<br>"
            "· <b>Move connection</b> — changes the destination of an existing connection<br>"
            "· <b>Remove connection</b> — disconnects the link<br><br>"
            "For complex links (wall outlet → endpoint) use the <b>Smart Connect</b> dialog, "
            "accessible from the port context menu.<br><br>"
            "Press <b>ESC</b> to cancel an ongoing link action."
        ),
    },
    {
        "title": "Wall outlets",
        "body": (
            "Wall outlets are physical connection points in a room (wall socket, network port).<br><br>"
            "<b>Creating:</b><br>"
            "· Via the context menu on a <b>room</b> in the tree: <i>New wall outlet</i><br>"
            "· Via shortcut <b>Ctrl+N</b> (global new wall outlet)<br><br>"
            "<b>Linking an endpoint:</b><br>"
            "· Via the context menu on a port in the rack view<br>"
            "· Or via shortcut <b>Ctrl+E</b> (create new endpoint globally)<br><br>"
            "<b>Overview and filters (wall outlets view):</b><br>"
            "Click a room in the tree to open the wall outlet overview. "
            "Three filters are available at the top:<br>"
            "· <b>Search bar</b> — searches by name, location, endpoint, IP, serial number<br>"
            "· <b>🚪 Room</b> — filters by room (searchable popup)<br>"
            "· <b>🌐 Location</b> — filters by location description (searchable popup)<br><br>"
            "Use <b>Ctrl+B</b> or the toolbar for the visual floorplan overview."
        ),
    },
    {
        "title": "Exporting",
        "body": (
            "All export functions are accessible via the <b>Report menu (Ctrl+R)</b>.<br><br>"
            "<b>Word report (Ctrl+Shift+R)</b><br>"
            "Generates a full Word report (.docx) of the infrastructure: "
            "all sites, rooms, racks, devices, ports, wall outlets and endpoints. "
            "The report includes VLAN overviews and an action plan for outstanding data issues.<br><br>"
            "<b>Rack export Markdown</b><br>"
            "Exports a technical rack overview as a Markdown file (.md), "
            "including port tracing, wall outlets and attention points per rack.<br><br>"
            "<b>VLAN report</b><br>"
            "Displays an overview of all VLANs with linked ports and endpoints.<br><br>"
            "<b>Export / Import Data (Ctrl+I)</b><br>"
            "Exports all data as a JSON file for backup or transfer. "
            "Import loads a previously exported file."
        ),
    },
    {
        "title": "Backup & settings",
        "body": (
            "Open settings via the <b>Settings menu (Ctrl+S)</b>.<br><br>"
            "Available options:<br>"
            "· <b>Language</b> — switch between NL and EN<br>"
            "· <b>Data source</b> — set the path to the JSON data file (local or network)<br>"
            "· <b>Backup</b> — set a network path for automatic backup on every save<br>"
            "· <b>Device types</b> — manage the list of available device types<br>"
            "· <b>Endpoint types</b> — manage the list of endpoint types<br><br>"
            "Backup is created automatically on every save when the configured path is reachable. "
            "Use <b>Ctrl+I</b> (Im/Export) for a manual JSON export as an additional backup."
        ),
    },
    {
        "title": "Search",
        "body": (
            "Use <b>Ctrl+F</b> or the search button in the toolbar to open the global search bar.<br><br>"
            "You can search by:<br>"
            "· <b>Name</b> — of devices, wall outlets, endpoints<br>"
            "· <b>IP address</b> — of devices or endpoints<br>"
            "· <b>MAC address</b> — of endpoints<br>"
            "· <b>Serial number</b> — of devices or endpoints<br><br>"
            "Double-click a result to navigate directly to it in the tree and centre area.<br><br>"
            "For filtered searching within the wall outlet overview (by room or location): "
            "see section <i>Wall outlets</i>."
        ),
    },
]


def get_guide_sections() -> list[dict]:
    """Geeft de gebruiksaanwijzing secties terug voor de actieve taal."""
    lang = get_language()
    return _GUIDE_EN if lang == "en" else _GUIDE_NL