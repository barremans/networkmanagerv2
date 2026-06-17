# Networkmap Creator — Openstaande werkpunten v21

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
| S6 | AD-koppeling hardcoded voor CGK — uitbreiden naar andere firma's | ⚪ Later |

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

## Cross-rack port↔port verbinding

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
| F2 | Menu Rapporteren → VLAN rapport: filtering op VLAN toevoegen (zelfde logica als wandpunten filtering) | 🟣 Open |
| F3 | settings, toevoegen primair bedrijf - kijkt naar lijst van bedrijven, primair opent standaard bij opstarten alle gekoppelde sites, zodat alle racks zichtbaar zijn | open |
---

## Visuele verbeteringen (V)

| ID | Omschrijving | Status |
|---|---|---|
| V7 | Snelle filter wandpunten op VLAN of locatie | 🟣 Open |

---

## Kwaliteit & betrouwbaarheid (K)

| ID | Omschrijving | Status |
|---|---|---|
| K1 | Export-info bestand in exportmap (`export_info.txt`) | 🟣 Open |
| K3 | Wijzigingslog (append-only, wie/wat/wanneer) | 🟣 Open |
| K4 | Help → Gebruiksaanwijzing volledig maken | 🟣 Open |---

## Netwerk (N)

| ID | Omschrijving | Status |
|---|---|---|
| N1 | Ping / bereikbaarheid check vanuit eindapparaat (als IP gekend) | 🟣 Open |

---

## Sneltoetsen

### Algemene regel



### Hoofdmenu

| Menu-item | Sneltoets | Underscore |
|---|---|---|


### Secundair menu

| Menu-item | Sneltoets | Underscore |
|---|---|---|


---

## Aanbevolen volgorde nieuwe chat
