# =============================================================================
# Networkmap_Creator
# File:    app/services/data_integrity.py
# Role:    Data validatie en automatische reparatie — GEEN Qt imports
# Version: 1.2.0
# Author:  Barremans
# Changes: 1.2.0 — VAL-1 focus_ids: validate_before_save() accepteert optionele
#                  focus_ids set — enkel waarschuwingen tonen waarbij het
#                  bewerkte/nieuwe object betrokken is. Voorkomt dat ongerelateerde
#                  bestaande problemen getoond worden bij aanmaken/bewerken.
# Changes: 1.1.0 — VAL-1: validate_before_save() toegevoegd.
#                  Controles: duplicate IP, duplicate MAC ETH, ongeldig IP-formaat
#                  over alle endpoints en devices. Retourneert lijst van
#                  waarschuwingsstrings (leeg = geen problemen). Geen Qt-imports.
# =============================================================================
#
# Wordt aangeroepen bij elke data-load vanuit MainWindow.
# Repareert stille data-corruptie zonder gebruikersinteractie.
#
# Huidige controles:
#   - Duplicate port IDs (veroorzaakt door snelle _gen_id aanroepen)
#     → elk duplicate ID krijgt een uniek vervangend ID
#     → verbindingen worden bijgewerkt naar de nieuwe IDs
#
# Retourneert altijd een (data, changed, rapport) tuple:
#   data    : (mogelijk gerepareerde) data dict
#   changed : bool — True als er iets gewijzigd is (→ opslaan nodig)
#   rapport : lijst van strings met beschrijving van wat gerepareerd is
# =============================================================================

from collections import Counter
import re
from app.helpers.settings_storage import get_all_sites

# ---------------------------------------------------------------------------
# VAL-1 — Regex voor geldig IPv4-adres
# ---------------------------------------------------------------------------

_IPV4_RE = re.compile(
    r'^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}'
    r'(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$'
)


# ---------------------------------------------------------------------------
# VAL-1 — Validatie vóór opslaan (soft warnings, geen reparatie)
# ---------------------------------------------------------------------------

def validate_before_save(data: dict,
                         focus_ids: set[str] | None = None) -> list[str]:
    """
    VAL-1 — Controleer data op inhoudelijke problemen vóór opslaan.

    Controles (over alle endpoints + devices):
      - Duplicate IP-adressen
      - Duplicate MAC ETH-adressen
      - Ongeldig IPv4-formaat (als IP aanwezig is)

    focus_ids : optionele set van object-IDs (device of endpoint).
      Als opgegeven, worden enkel waarschuwingen getoond waarbij minstens
      één van de focus-objecten betrokken is. Gebruik dit bij aanmaken of
      bewerken van één enkel object zodat de gebruiker geen ongerelateerde
      bestaande problemen te zien krijgt.
      None = volledige dataset (standaard).

    Retourneert een lijst van waarschuwingsstrings.
    Lege lijst = geen problemen gevonden.
    Geen Qt-imports, geen reparatie.
    """
    warnings: list[str] = []

    # Verzamel alle objecten met id + naam + IP + MAC
    objects: list[dict] = []
    for dev in data.get("devices", []):
        objects.append({
            "id":    dev.get("id", ""),
            "label": f"Device '{dev.get('name', dev.get('id', '?'))}'",
            "ip":    (dev.get("ip", "") or "").strip(),
            "mac":   (dev.get("mac_eth", dev.get("mac", "")) or "").strip().upper(),
        })
    for ep in data.get("endpoints", []):
        objects.append({
            "id":    ep.get("id", ""),
            "label": f"Eindapparaat '{ep.get('name', ep.get('id', '?'))}'",
            "ip":    (ep.get("ip", "") or "").strip(),
            "mac":   (ep.get("mac_eth", ep.get("mac", "")) or "").strip().upper(),
        })

    def _focus_match(involved_ids: set[str]) -> bool:
        """True als focus_ids None is (alles tonen) of minstens één match."""
        if focus_ids is None:
            return True
        return bool(focus_ids & involved_ids)

    # — Ongeldig IP-formaat —
    for obj in objects:
        ip = obj["ip"]
        if ip and not _IPV4_RE.match(ip):
            if _focus_match({obj["id"]}):
                warnings.append(f"Ongeldig IP-adres: {ip}  ({obj['label']})")

    # — Duplicate IP —
    ip_counter: dict[str, list[tuple[str, str]]] = {}  # ip → [(id, label)]
    for obj in objects:
        ip = obj["ip"]
        if ip:
            ip_counter.setdefault(ip, []).append((obj["id"], obj["label"]))
    for ip, entries in ip_counter.items():
        if len(entries) > 1:
            involved = {e[0] for e in entries}
            if _focus_match(involved):
                labels = ",  ".join(e[1] for e in entries)
                warnings.append(f"Dubbel IP-adres {ip}: {labels}")

    # — Duplicate MAC ETH —
    mac_counter: dict[str, list[tuple[str, str]]] = {}  # mac → [(id, label)]
    for obj in objects:
        mac = obj["mac"]
        if mac:
            mac_counter.setdefault(mac, []).append((obj["id"], obj["label"]))
    for mac, entries in mac_counter.items():
        if len(entries) > 1:
            involved = {e[0] for e in entries}
            if _focus_match(involved):
                labels = ",  ".join(e[1] for e in entries)
                warnings.append(f"Dubbel MAC-adres {mac}: {labels}")

    return warnings


# ---------------------------------------------------------------------------
# Hulpfuncties
# ---------------------------------------------------------------------------

def _all_existing_ids(data: dict) -> set:
    """Verzamel alle bestaande IDs in de data — voor uniciteitscheck."""
    ids = set()
    for site in get_all_sites(data):
        ids.add(site.get("id", ""))
        for room in site.get("rooms", []):
            ids.add(room.get("id", ""))
            for rack in room.get("racks", []):
                ids.add(rack.get("id", ""))
                for slot in rack.get("slots", []):
                    ids.add(slot.get("id", ""))
            for wo in room.get("wall_outlets", []):
                ids.add(wo.get("id", ""))
    for d in data.get("devices", []):
        ids.add(d.get("id", ""))
    for p in data.get("ports", []):
        ids.add(p.get("id", ""))
    for e in data.get("endpoints", []):
        ids.add(e.get("id", ""))
    for c in data.get("connections", []):
        ids.add(c.get("id", ""))
    ids.discard("")
    return ids


def _new_unique_id(base: str, used: set) -> str:
    """Genereer een uniek ID op basis van een basisnaam."""
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}_{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


# ---------------------------------------------------------------------------
# Controle: duplicate port IDs
# ---------------------------------------------------------------------------

def _fix_duplicate_port_ids(data: dict) -> tuple[dict, bool, list[str]]:
    """
    Detecteer en repareer duplicate port IDs.

    Aanpak:
    - Poorten met een uniek ID blijven ongewijzigd.
    - Bij duplicaten: de EERSTE poort met dat ID behoudt het originele ID.
    - Alle volgende poorten met hetzelfde ID krijgen een nieuw uniek ID.
    - Verbindingen worden bijgewerkt: ze verwijzen naar de eerste poort
      met het originele ID (de bedoelde poort bij aanmaken van de verbinding).

    Retourneert (data, changed, rapport_regels).
    """
    ports       = data.get("ports", [])
    connections = data.get("connections", [])

    # Tel voorkomens per ID
    id_counts = Counter(p["id"] for p in ports)
    duplicates = {pid for pid, cnt in id_counts.items() if cnt > 1}

    if not duplicates:
        return data, False, []

    rapport = []
    rapport.append(
        f"Duplicate port IDs gevonden: {len(duplicates)} — automatisch gerepareerd."
    )

    # Verzamel alle bestaande IDs voor uniciteitscheck
    used_ids = _all_existing_ids(data)

    # Verwerk poorten: eerste occurrence behoudt ID, rest krijgt nieuw ID
    seen_ids: set[str] = set()
    port_id_remap: dict[str, str] = {}  # old_id_of_duplicate → new_id (alleen voor de eerste)

    for port in ports:
        old_id = port["id"]
        if old_id not in duplicates:
            seen_ids.add(old_id)
            continue

        if old_id not in seen_ids:
            # Eerste occurrence — behoudt origineel ID
            seen_ids.add(old_id)
            port_id_remap[old_id] = old_id
        else:
            # Latere occurrence — krijgt nieuw uniek ID
            base = f"p_{port['device_id'].replace('dev_', '')}_{port['side'][0]}{port['number']}"
            new_id = _new_unique_id(base, used_ids)
            rapport.append(
                f"  Port {old_id} ({port['device_id']} {port['side']} #{port['number']}) "
                f"→ {new_id}"
            )
            port["id"] = new_id

    # Verbindingen hoeven NIET bijgewerkt te worden:
    # de eerste occurrence behoudt het originele ID waar de verbinding naar verwijst.

    data["ports"] = ports
    return data, True, rapport


# ---------------------------------------------------------------------------
# Hoofd validatie functie — aanroepen na elke data-load
# ---------------------------------------------------------------------------

def validate_and_repair(data: dict) -> tuple[dict, bool, list[str]]:
    """
    Voer alle data-integriteitscontroles uit op de geladen data.

    Parameters:
        data : de volledige network_data dict

    Retourneert:
        (data, changed, rapport)
        - data    : gerepareerde data (of origineel als niets gewijzigd)
        - changed : True als er iets gerepareerd is → MainWindow moet opslaan
        - rapport : lijst van strings voor logging
    """
    changed_total = False
    rapport_total = []

    # Controle 1: duplicate port IDs
    data, changed, rapport = _fix_duplicate_port_ids(data)
    if changed:
        changed_total = True
        rapport_total.extend(rapport)

    # Toekomstige controles hier toevoegen:
    # data, changed, rapport = _fix_orphaned_connections(data)
    # data, changed, rapport = _fix_missing_port_numbers(data)

    return data, changed_total, rapport_total