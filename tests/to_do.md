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
| S1 | Azure AD login — CGK-APP-L6 vereist | ✅ v16 |
| S2 | Offline poweruser login → read-only modus | ✅ v16 |
| S3 | Security logging naar security_log.txt | ✅ v16 |
| S4 | MFA/AD uitbreiden (bv. per-gebruiker rechten) | ⚪ Later |

---

## Backup / Sync (B)

| ID | Omschrijving | Status |
|---|---|---|
| B-BACKUP | Backup live omgeving via Intune | ✅ backup_service 1.4.6 |
| B-NEW-1 | `floorplans.json` meenemen in backup | ✅ backup_service 1.4.6 |
| B-NEW-2 | SVG bestanden map (`floorplans/`) meenemen in backup | ✅ backup_service 1.4.6 |
| B-UNC-1 | Backup schrijft niet naar UNC (OSError) | ✅ v17 |
| B-UNC-2 | Restore WinError 5 op UNC | ✅ v17 |
| B-CLOSE-1 | Backup gevraagd bij read-only modus | ✅ v17 |
| B-CLOSE-2 | Backup gevraagd als niks gewijzigd | ✅ v17 |
| B-SYNC-1 | Vals pull bij opstart (mtime mismatch) | ✅ v17 |
| B-SYNC-2 | Pull van leeg netwerkbestand | ✅ v17 |
| R-1 | Backup herstellen vanuit history naar lokale data | ✅ v17 |

> **Noot:** Backup pad moet een **submap** zijn, bv. `\\server\share\Bck` — niet de root share zelf. Root share geeft `FileNotFoundError` bij `mkdir()` op Windows UNC.

---

## Grondplannen (G)

| ID | Omschrijving | Status |
|---|---|---|
| G1-G11 | SVG grondplan module volledig werkend | ✅ |
| G-OPEN-1 | M8 verwijderen uit bestaande floorplans.json | ⏸ Hold |  DONE
| G-OPEN-2 | Notities + naam tonen in Info tab zijpaneel FloorplanView | ✅ floorplan_view 1.12.0 |
| G-OPEN-3 | Koppeling verwijderen via rechtsklik overlay | ✅ floorplan_view 1.11.0 |
| G-OPEN-4 | SVG label preview bij importeren in FloorplanDialog | ⏸ Hold |
| G-OPEN-5 | SVG vervangen/updaten voor bestaand grondplan | ✅ floorplan_service 1.5.0 |
| G-OPEN-6 | Verouderde mappings automatisch opkuisen bij SVG update | ✅ floorplan_service 1.5.0 |
| G-OPEN-7 | Bulk koppeling SVG punten ↔ wandpunten via tabel | ⏸ Hold |
| G-OPEN-8 | Grondplan exporteren als PNG/PDF met overlays | 🔵 Open |
| G-OPEN-9 | Grondplan meenemen in Word export | 🔵 Open |
| G-SVG-BUG | foreignObject tekst linksboven (draw.io SVG) | ⏸ Workaround: gebruik Plain SVG export |  DONE
| G-SVG-FIX | light-dark() zwarte vlakken + label prefixen | ✅ floorplan_svg_service 1.6.0 |

**SVG werkwijze:**
1. Teken in draw.io
2. Open in Inkscape → id's toewijzen aan wandpunt elementen
3. Exporteer als **Plain SVG** (File → Save As → Plain SVG)
4. Importeer in app → labels worden automatisch gedetecteerd

---

## Wandpunten (W)

| ID | Omschrijving | Status |
|---|---|---|
| W1 | Eindapparaat aanmaken vanuit wandpunt | ✅ |
| W2 | Wandpunt locaties koppelen aan site | ⏸ Op hold |
| W-DUP | Duplicate check was naam+ruimte → nu naam+wandlocatie | ✅ v19 |
| W-MOVE | Wandpunt verplaatsen naar andere ruimte via DDL in bewerk-dialoog | ✅ v19 |
| W-NEW-ANYWHERE | Nieuw wandpunt aanmaken zonder ruimte te kennen (DDL in dialoog) | ✅ v19 |
| W-DELETE | Wandpunt verwijderen via rechtsklik op kaartje | ✅ v20 |
| W-SORT | Natural sort op wandpuntnaam (A2 < A10 < B1) | ✅ v20 |
| W-RESPONSIVE | Responsieve kaartjes (min 160px / max 280px) | ✅ v20 |
| W-OPEN-1 | Verdere bijsturingen wandpunten + wandpuntlocaties | 🟣 Open |

---

## Direct verbonden apparaten (D)

| ID | Omschrijving | Status |
|---|---|---|
| D-FILTER | Direct verbonden view gefilterd op geselecteerde rack | ✅ v19 |
| D-TITLE | Titelregel toont rack naam ipv site naam | ✅ v19 |

---

## Cross-rack port↔port verbinding (v18)

| ID | Omschrijving | Status |
|---|---|---|
| — | `connect_port_to_port_dialog.py` v1.0.0 | ✅ v18 |
| — | Cross-rack verbinding aanmaken via rechtsklik vrije poort | ✅ v18 |

---

## Export / Import (E)

| ID | Omschrijving | Status |
|---|---|---|
| E1-E3 | Export uitbreiden | 🔵 Open |
| E4 | VLAN-rapport als Markdown export | 🟣 Open |
| O1 | CSV import | ⏸ Hold |

---

## Functionele verbeteringen (F)

| ID | Omschrijving | Status |
|---|---|---|
| F5 | Read-only modus | ✅ |
| F6 | Sort_id per wandpunt | ✅ |
| F7 | Rack verplaatsen | ✅ |
| F8 | Volgorde wandpunt locaties | ✅ |
| F9 | Zoekfunctie uitbreiden (VLAN-nr, IP, eindapparaat-type) | 🟣 Open |
| F10 | IP-adres per eindapparaat registreren | ✅ v17 |
| F11 | Duplicate detectie wandpuntnamen per locatie | ✅ v19 |

---

## Visuele verbeteringen (V)

| ID | Omschrijving | Status |
|---|---|---|
| V1 | Wandpunt popup dubbel icoon | ✅ |
| V2 | Custom gekleurde devices tekstzichtbaarheid | ⏸ Op hold |
| V3 | Extra ruimte tussen devices in rack | ✅ |
| V5 | Wandpunten groeperen per locatie | ✅ |
| V6 | Rack bezettingsgraad in boom (bv. `Rack A [18/24]`) | 🟣 Open |
| V7 | Snelle filter wandpunten op VLAN of locatie | 🟣 Open |

---

## Kwaliteit & betrouwbaarheid (K)

| ID | Omschrijving | Status |
|---|---|---|
| K1 | Export-info bestand in exportmap (`export_info.txt`) | 🟣 Open |
| K2 | Automatische datamigatie bij versie-upgrade | 🟣 Open |
| K3 | Wijzigingslog (append-only, wie/wat/wanneer) | 🟣 Open |

---

## Netwerk (N)

| ID | Omschrijving | Status |
|---|---|---|
| N1 | Ping / bereikbaarheid check vanuit eindapparaat (als IP gekend) | 🟣 Open |

---

## Aanbevolen volgorde nieuwe chat

1. **W-OPEN-1** — Verdere bijsturingen wandpunten + wandpuntlocaties
2. **G-OPEN-8/9** — Grondplan exporteren als PNG/PDF + meenemen in Word
3. **E4** — VLAN-rapport als Markdown export
4. **V6** — Rack bezettingsgraad in boom
5. **F9** — Zoekfunctie uitbreiden (VLAN-nr, IP, eindapparaat-type)
6. **E1-E3** — Export verder uitbreiden
7. **V7** — Snelle filter wandpunten
8. **K1/K2/K3** — Kwaliteit & betrouwbaarheid
9. **N1** — Ping/bereikbaarheid check
