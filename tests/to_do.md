# Networkmap Creator — Openstaande werkpunten v13

## Legende
- 🔴 Bug  |  🟠 Hoge prioriteit  |  🟡 Visueel  |  🔵 Export  |  ⚪ Later  |  🟣 Nieuw  |  ✅ Opgelost  |  ⏸ Hold

---

## Bugs

| ID | Omschrijving | Status |
|---|---|---|
| B2 | Cross-rack poort inkleuring | ⏸ Uitgesteld |
| B8 | Cross-side port highlight (front↔back) | ⏸ Op hold |
| B-BACKUP | Backup live omgeving via Intune | ✅ backup_service 1.4.6 |

---

## Grondplannen (G)

| ID | Omschrijving | Status |
|---|---|---|
| G1-G11 | SVG grondplan module volledig werkend | ✅ |
| G-OPEN-1 | M8 verwijderen uit bestaande floorplans.json | ⏸ Hold |
| G-OPEN-2 | Notities + naam tonen in Info tab zijpaneel FloorplanView | ✅ floorplan_view 1.12.0 |
| G-OPEN-3 | Koppeling verwijderen via rechtsklik overlay | ✅ floorplan_view 1.11.0 |
| G-OPEN-4 | SVG label preview bij importeren in FloorplanDialog | ⏸ Hold |
| G-OPEN-5 | SVG vervangen/updaten voor bestaand grondplan | ✅ floorplan_service 1.5.0 |
| G-OPEN-6 | Verouderde mappings automatisch opkuisen bij SVG update | ✅ floorplan_service 1.5.0 |
| G-OPEN-7 | Bulk koppeling SVG punten ↔ wandpunten via tabel | ⏸ Hold |
| G-OPEN-8 | Grondplan exporteren als PNG/PDF met overlays | 🔵 Open |
| G-OPEN-9 | Grondplan meenemen in Word export | 🔵 Open |
| G-SVG-BUG | foreignObject tekst linksboven (draw.io SVG) | ⏸ Workaround: gebruik Plain SVG export |
| G-SVG-FIX | light-dark() zwarte vlakken + label prefixen | ✅ floorplan_svg_service 1.6.0 |

**SVG werkwijze:**
1. Teken in draw.io
2. Open in Inkscape → id's toewijzen aan wandpunt elementen
3. Exporteer als **Plain SVG** (File → Save As → Plain SVG)
4. Importeer in app → labels worden automatisch gedetecteerd

---

## Backup verbeteringen (B-NEW)

| ID | Omschrijving | Status |
|---|---|---|
| B-NEW-1 | `floorplans.json` meenemen in backup | ✅ backup_service 1.4.6 |
| B-NEW-2 | SVG bestanden map (`floorplans/`) meenemen in backup | ✅ backup_service 1.4.6 |

**Belangrijke noot:**
- Backup pad moet een **submap** zijn, bv. `\\server\share\Bck` — niet de root share zelf
- Root share geeft `FileNotFoundError` bij `mkdir()` op Windows UNC

---

## Restore (nieuw)

| ID | Omschrijving | Status |
|---|---|---|
| R-1 | Backup herstellen vanuit history naar lokale data | 🟠 Open — volgende chat |

---

## Functionele verbeteringen (F)

| ID | Omschrijving | Status |
|---|---|---|
| F5 | Read-only modus | ✅ |
| F6 | Sort_id per wandpunt | ✅ |
| F7 | Rack verplaatsen | ✅ |
| F8 | Volgorde wandpunt locaties | ✅ |

---

## Visuele verbeteringen (V)

| ID | Omschrijving | Status |
|---|---|---|
| V1 | Wandpunt popup dubbel icoon | ✅ |
| V2 | Custom gekleurde devices tekstzichtbaarheid | ⏸ Op hold |
| V3 | Extra ruimte tussen devices in rack | ✅ |
| V5 | Wandpunten groeperen per locatie | ✅ |

---

## Wandpunten (W)

| ID | Omschrijving | Status |
|---|---|---|
| W1 | Eindapparaat aanmaken vanuit wandpunt | ✅ |
| W2 | Wandpunt locaties koppelen aan site | ⏸ Op hold |

---

## Export / Import / Overig

| ID | Omschrijving | Status |
|---|---|---|
| E1-E3 | Export uitbreiden | 🔵 Open |
| O1 | CSV import | ⏸ Hold |
| S1 | MFA/AD | ⚪ Later |

---

## Aanbevolen volgorde nieuwe chat

1. **R-1** — Backup restore functionaliteit
2. **E1-E3** — Export uitbreiden
3. **G-OPEN-8/9** — Grondplan exporteren als PNG/PDF + Word
4. **V2** — Custom device kleur tekstzichtbaarheid (on hold)
5. **B2/B8** — Cross-rack/cross-side highlight (on hold)
