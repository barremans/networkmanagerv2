# Networkmap Creator — Openstaande werkpunten v20

## Legende
- 🔴 Bug  |  🟠 Hoge prioriteit  |  🟡 Visueel  |  🔵 Export  |  ⚪ Later  |  🟣 Nieuw  |  ✅ Opgelost  |  ⏸ Hold

---

## Bugs

| ID | Omschrijving | Status |
|---|---|---|
| B2 | Cross-rack poort inkleuring (andere rack niet highlight-baar) | ⏸ Uitgesteld |
| B8 | Cross-side port highlight (front↔back) | ⏸ Op hold |
| T1 | Trace klik op SW9.3 (FRONT): SW10 cross-rack staat iets verkeerd in keten | ⏸ Geaccepteerd |

---

## Security (S)

| ID | Omschrijving | Status |
|---|---|---|
| S4 | MFA/AD uitbreiden (bv. per-gebruiker rechten) | ⚪ Later |
| S6 | Andere manier is nu hardcoded enkel voor CGK AD, ook voor andere firma's kunnen gebruiken. | |

---

## Backup / Sync (B)

| ID | Omschrijving | Status |
|---|---|---|

> **Noot:** Backup pad moet een **submap** zijn, bv. `\\server\share\Bck` — niet de root share zelf. Root share geeft `FileNotFoundError` bij `mkdir()` op Windows UNC.

---

## Grondplannen (G)

| ID | Omschrijving | Status |
|---|---|---|


---

## Wandpunten (W)

| ID | Omschrijving | Status |
|---|---|---|


---

## Direct verbonden apparaten (D)

| ID | Omschrijving | Status |
|---|---|---|


---

## Cross-rack port↔port verbinding (v18)

| ID | Omschrijving | Status |
|---|---|---|


---

## Export / Import (E)

| ID | Omschrijving | Status |
|---|---|---|
| O1 | CSV import | ⏸ Hold |

---

## Functionele verbeteringen (F)

| ID | Omschrijving | Status |
|---|---|---|
|F1 |Menu Im/export, verwijderen van "Exporteer Afbeelding"| Open|
|F2 |Menu Rapporteren, VLAN rapport, filtering toevoegen op VLAN (zelfde logica als wandpunten filtering| Open |



---

## Visuele verbeteringen (V)

| ID | Omschrijving | Status |
|---|---|---|
| V7 | Snelle filter wandpunten op VLAN of locatie | 🟣 Open |
| V8 | Help popup, Sneltoetsen menu - niet over gans de hoogte van de popup, visueel niet mooi

---

## Kwaliteit & betrouwbaarheid (K)

| ID | Omschrijving | Status |
|---|---|---|
| K1 | Export-info bestand in exportmap (`export_info.txt`) | 🟣 Open |
| K3 | Wijzigingslog (append-only, wie/wat/wanneer) | 🟣 Open |
| K4 | Help - Gebruiksaanwijzing volledig maken | Open |

---

## Netwerk (N)

| ID | Omschrijving | Status |
|---|---|---|
| N1 | Ping / bereikbaarheid check vanuit eindapparaat (als IP gekend) | 🟣 Open |

---

## Sneltoetsen

### Algemene regel

- Altijd met underscore werken.
- De eerste letter gebruiken als sneltoets.
- Open vragen:
  - Wat met andere talen?
  - Wat met submenu-keuze?

### Hoofdmenu

| Menu-item | Sneltoets | Underscore |
|---|---|---|
| Im/export | Ctrl + I | `_I` |
| Rapporten | Ctrl + R | `_R` |
| Settings | Ctrl + S | `_S` |
| Grondplannen | Ctrl + G | `_G` |
| Help | Ctrl + H | `_H` |

### Secundair menu

| Menu-item | Sneltoets | Underscore |
|---|---|---|
| Zoeken | Ctrl + Z | `_Z` |
| Wandpunten zoeken | Ctrl + W | `_W` |

---

## Aanbevolen volgorde nieuwe chat

