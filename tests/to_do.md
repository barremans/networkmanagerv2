# Networkmap Creator — Openstaande werkpunten v5

## Legende
- 🔴 Bug
- 🟠 Functionele verbetering (hoge prioriteit)
- 🟡 Visuele verbetering
- 🔵 Export
- ⚪ Later / security
- 🟣 Nieuw

---

## 1. Bugs

| ID | Omschrijving | Bestand(en) | Status |
|---|---|---|---|
| B2 | Cross-rack poort inkleuring (Qt render timing) | `rack_view.py`, `main_window.py` | ⏸ Uitgesteld |

---

## 2. Functionele verbeteringen

| ID | Omschrijving | Bestand(en) | Status |
|---|---|---|---|
| F5 | Read-only modus — standaard read-only, R/W via settings, indicator in UI | `main_window.py`, `settings_window.py`, `settings_storage.py`, alle dialogs | 🟠 Open |
| F6 | Tracing per device groeperen in wandpuntenview | `wall_outlet_view.py`, `main_window.py` | 🟠 Open |
| F7 | Backup automatisch bij afsluiten | `main_window.py`, `backup_service.py` | ✅ Opgelost (F3/v4) |

---

## 3. Visuele verbeteringen

| ID | Omschrijving | Bestand(en) | Status |
|---|---|---|---|
| V1 | Wandpunt popup dubbel icoon in settings | `settings_window.py` | 🟡 Open |
| V2 | Custom gekleurde devices minder zichtbaar dan type-standaardkleuren | `rack_view.py`, `main.qss` | 🟡 Open |
| V3 | Extra ruimte tussen devices in rack (margin_below, rekening met hoogte) | `rack_view.py`, `place_device_dialog.py` | 🟡 Open |
| V4 | Afbeeldingexport rack te lang en onvoldoende leesbaar | export module | 🟡 Open |

---

## 4. Export

| ID | Omschrijving | Bestand(en) | Status |
|---|---|---|---|
| E1 | Word-export uitbreiden (toestelinfo, detailinfo, VLAN-overzicht) | Word export service | 🔵 Open |
| E2 | Tekstuele rack-export (visueel met pijltjes en symbolen) | nieuw export module | 🔵 Open |
| E3 | Afbeeldingexport rack compacter en leesbaarder | export module | 🔵 Open |

---

## 5. Security — MFA / Active Directory

| ID | Omschrijving | Status |
|---|---|---|
| S1 | MFA introduceren via AD (niveau 5 vereist) | ⚪ Later |
| S1a | Standaard niet actief | ⚪ Later |
| S1b | Activeerbaar via installer (Inno Setup) of settings | ⚪ Later |
| S1c | Bij onvoldoende rechten: popup + applicatie sluiten | ⚪ Later |
| S1d | AD-server hardcoded voor CGK + configureerbaar via settings | ⚪ Later |
| S1e | Open vraag: MFA-activatie koppelen aan GitHub builds (Inno Setup flag of build config) | ⚪ Later |

---

## 6. Overig

| ID | Omschrijving | Status |
|---|---|---|
| O1 | Direct uitlezen uit CSV | 🟣 Nieuw — Open |

---

## 7. SVG Tekeningen (nieuw)

| ID | Omschrijving | Status |
|---|---|---|
| G1 | Grondplan van wandpunten opladen en linken aan ruimte | 🟣 Nieuw — Open |
| G2 | Grondplan kunnen bekijken in de applicatie | 🟣 Nieuw — Open |

---

## Aanbevolen volgorde

1. **F5** — Read-only modus (compact, veel impact)
2. **V1 + V2 + V3** — Visuele fixes (snel resultaat)
3. **F6** — Tracing per device groeperen
4. **E1 + E2 + E3** — Export uitbreiden
5. **G1 + G2** — SVG grondplannen
6. **O1** — CSV import
7. **S1** — MFA/AD (later)
8. **B2** — Cross-rack highlight (als elegantere Qt oplossing gevonden)


- Rack device - bewerken - positie kan niet aangepast worden
- Instellingen menu dubbel, onder "Bestand" en "Settings" menu. Onder "Bestand" mag weg
- Wandpunten:
  - Visiueel groeperen per locatie
- achterkant toestellen met ook ports aan de front, aanklikken front ook port achterzijde gekleurd tonen nu blijft die geelklik front port nu kleurt bv. front van switch op die verbonden is maar niet de back port van de device. bv patchpanel port 1 front aangeklikt - switch port 1 gekleurd alsook port 1 back van de patchpanel
- backup bug, test map lukt, backup maken lukt, maar na een tijdje niet meer. error : Backup mislukt. Controleer het netwerkpad. Geen schrijfrechten op ***maar als ik test doe dan lukt de test.

- backup neemt niet alles mee
  - Eindapparaten, Device Types, Wandpunten locaties die in instellingen zijn bepaald

- Rack verplaatsen van ruimte niet aanwezig

- wandpunten overzicht
  - volgorde van wandpunten locatie kunnen bepalen