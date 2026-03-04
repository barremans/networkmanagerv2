# =============================================================================
# Networkmap_Creator
# File:    app/helpers/help_texts.py
# Role:    H1 — Vertaalde teksten voor het Help venster (los van i18n.py)
# Version: 1.0.0
# Author:  Barremans
# =============================================================================

from app.helpers.i18n import get_language

# ---------------------------------------------------------------------------
# Sneltoetsen — (sneltoets, vertaalsleutel voor omschrijving)
# De omschrijving wordt via i18n.t() opgehaald zodat die mee wisselt met taal.
# ---------------------------------------------------------------------------

SHORTCUTS = [
    ("Ctrl+N",       "menu_new"),
    ("Ctrl+F",       "menu_search"),
    ("Ctrl+W",       "menu_outlet_locator"),
    ("Ctrl+Shift+E", "menu_export_image"),
    ("Ctrl+Shift+R", "menu_export_report"),
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
            "Start met het aanmaken van een <b>Site</b> via de knop <b>Nieuw</b> "
            "of het contextmenu (rechtermuisklik) in de boom links.<br><br>"
            "Voeg vervolgens <b>Ruimtes</b> toe aan de site, <b>Racks</b> aan de ruimtes "
            "en <b>Devices</b> aan de racks."
        ),
    },
    {
        "title": "Boomstructuur (links)",
        "body": (
            "De boom toont de volledige hiërarchie:<br>"
            "<b>Sites → Ruimtes → Racks + Wandpunten</b><br><br>"
            "Klik op een item om het te tonen in het middengebied.<br>"
            "<b>Rechtermuisklik</b> op een item opent een contextmenu met beschikbare acties."
        ),
    },
    {
        "title": "Rack beheer",
        "body": (
            "Klik op een rack in de boom om het te openen. "
            "Elke U-positie toont het geplaatste device.<br><br>"
            "Klik op een <b>poort</b> om de volledige verbindingstrace te zien onderaan het venster.<br>"
            "Gebruik de knop <b>Verbinding</b> in de toolbar om twee poorten met elkaar te verbinden."
        ),
    },
    {
        "title": "Verbindingen aanmaken",
        "body": (
            "1. Activeer de verbindingsmodus via de knop <b>Verbinding</b> in de toolbar.<br>"
            "2. Klik op de eerste poort (poort A) — de poort wordt gemarkeerd.<br>"
            "3. Klik op de tweede poort (poort B) — de verbinding wordt aangemaakt.<br><br>"
            "Druk <b>ESC</b> om de verbindingsmodus te annuleren.<br>"
            "Via <b>rechtermuisklik op een poort</b> kan je ook verbinden met een wandpunt."
        ),
    },
    {
        "title": "Wandpunten",
        "body": (
            "Wandpunten zijn fysieke aansluitpunten in een ruimte (muurcontact, netwerkaansluiting).<br><br>"
            "Voeg ze toe via het contextmenu op een ruimte of via <b>Nieuw → Wandpunt</b>.<br>"
            "Gebruik <b>Ctrl+W</b> of de toolbar-knop <b>Wandpunten zoeken</b> "
            "voor een overzicht per ruimte met tracemogelijkheid."
        ),
    },
    {
        "title": "Exporteren",
        "body": (
            "<b>Afbeelding (Ctrl+Shift+E)</b><br>"
            "Exporteert de actieve rackweergave of wandpuntentabel als PNG of JPEG.<br><br>"
            "<b>Rapport (Ctrl+Shift+R)</b><br>"
            "Genereert een volledig Word-rapport (.docx) van de volledige infrastructuur "
            "met alle sites, ruimtes, racks, devices, poorten en wandpunten.<br><br>"
            "<b>JSON export</b><br>"
            "Exporteert alle data als JSON-bestand voor backup of overdracht naar een andere installatie."
        ),
    },
    {
        "title": "Backup & instellingen",
        "body": (
            "Via <b>Bestand → Instellingen</b> kan je:<br>"
            "· Automatische backup instellen naar een netwerkpad<br>"
            "· De taal van de applicatie wijzigen (NL / EN)<br>"
            "· De databron instellen (lokaal of netwerkpad)<br>"
            "· Device types en eindapparaat-types beheren<br><br>"
            "De backup wordt automatisch aangemaakt bij elke opslag als het netwerkpad bereikbaar is."
        ),
    },
    {
        "title": "Zoeken",
        "body": (
            "Via <b>Ctrl+F</b> of de zoekknop in de toolbar open je het zoekvenster.<br><br>"
            "Je kan zoeken op <b>naam, IP-adres, MAC-adres en serienummer</b> "
            "van devices, poorten, wandpunten en eindapparaten.<br>"
            "Dubbelklik op een resultaat om er direct naartoe te navigeren."
        ),
    },
]

_GUIDE_EN = [
    {
        "title": "Getting started",
        "body": (
            "Start by creating a <b>Site</b> using the <b>New</b> button "
            "or the context menu (right-click) in the tree on the left.<br><br>"
            "Then add <b>Rooms</b> to the site, <b>Racks</b> to the rooms, "
            "and <b>Devices</b> to the racks."
        ),
    },
    {
        "title": "Tree structure (left panel)",
        "body": (
            "The tree shows the full hierarchy:<br>"
            "<b>Sites → Rooms → Racks + Wall Outlets</b><br><br>"
            "Click an item to display it in the centre area.<br>"
            "<b>Right-click</b> an item to open a context menu with available actions."
        ),
    },
    {
        "title": "Rack management",
        "body": (
            "Click a rack in the tree to open it. "
            "Each U-position shows the installed device.<br><br>"
            "Click a <b>port</b> to see the full connection trace at the bottom of the window.<br>"
            "Use the <b>Connection</b> button in the toolbar to link two ports together."
        ),
    },
    {
        "title": "Creating connections",
        "body": (
            "1. Activate connection mode using the <b>Connection</b> button in the toolbar.<br>"
            "2. Click the first port (port A) — the port is highlighted.<br>"
            "3. Click the second port (port B) — the connection is created.<br><br>"
            "Press <b>ESC</b> to cancel connection mode.<br>"
            "<b>Right-click a port</b> to connect it to a wall outlet instead."
        ),
    },
    {
        "title": "Wall outlets",
        "body": (
            "Wall outlets are physical connection points in a room (wall socket, network port).<br><br>"
            "Add them via the context menu on a room or via <b>New → Wall Outlet</b>.<br>"
            "Use <b>Ctrl+W</b> or the <b>Find Wall Outlets</b> toolbar button "
            "for a room overview with trace functionality."
        ),
    },
    {
        "title": "Exporting",
        "body": (
            "<b>Image (Ctrl+Shift+E)</b><br>"
            "Exports the active rack view or outlet table as PNG or JPEG.<br><br>"
            "<b>Report (Ctrl+Shift+R)</b><br>"
            "Generates a full Word report (.docx) of the entire infrastructure "
            "including all sites, rooms, racks, devices, ports and wall outlets.<br><br>"
            "<b>JSON export</b><br>"
            "Exports all data as a JSON file for backup or transfer to another installation."
        ),
    },
    {
        "title": "Backup & settings",
        "body": (
            "Via <b>File → Settings</b> you can:<br>"
            "· Configure automatic backup to a network path<br>"
            "· Change the application language (NL / EN)<br>"
            "· Set the data source (local or network path)<br>"
            "· Manage device types and endpoint types<br><br>"
            "Backup is created automatically on every save when the network path is reachable."
        ),
    },
    {
        "title": "Search",
        "body": (
            "Use <b>Ctrl+F</b> or the search button in the toolbar to open the search window.<br><br>"
            "You can search by <b>name, IP address, MAC address and serial number</b> "
            "of devices, ports, wall outlets and endpoints.<br>"
            "Double-click a result to navigate directly to it."
        ),
    },
]


def get_guide_sections() -> list[dict]:
    """Geeft de gebruiksaanwijzing secties terug voor de actieve taal."""
    lang = get_language()
    return _GUIDE_EN if lang == "en" else _GUIDE_NL