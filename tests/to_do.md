# Networkmap Creator — Openstaande werkpunten v5

# Networkmap Creator — Openstaande werkpunten v8

## Legende
- 🔴 Bug
- 🟠 Functionele verbetering (hoge prioriteit)
- 🟡 Visuele verbetering
- 🔵 Export
- ⚪ Later / security
- 🟣 Nieuw
- ✅ Opgelost
- ⏸ Op hold

---

## 1. Bugs

| ID | Omschrijving | Bestand(en) | Status |
|---|---|---|---|
| B2 | Cross-rack poort inkleuring (Qt render timing) | `rack_view.py`, `main_window.py` | ⏸ Uitgesteld |
| B6 | Rack device bewerken — positie niet aanpasbaar | `place_device_dialog.py`, `main_window.py` | ✅ Opgelost |
| B7 | Instellingen menu dubbel | `main_window.py` | ✅ Opgelost |
| B8 | Cross-side port highlight (front↔back patchpanel) | `tracing.py`, `rack_view.py`, `main_window.py` | ⏸ Op hold |
| B9 | Backup mislukt na verloop van tijd | `backup_service.py` | ✅ Opgelost |
| B10 | Backup neemt settings niet mee (endpoint types, device types, outlet locations) | `backup_service.py`, `settings_storage.py` | 🔴 Open — volgende stap |

---

## 2. Functionele verbeteringen

| ID | Omschrijving | Bestand(en) | Status |
|---|---|---|---|
| F5 | Read-only modus | meerdere | ✅ Opgelost |
| F6 | Tracing per device groeperen in wandpuntenview | `wall_outlet_view.py` | 🟠 Open |
| F7 | Rack verplaatsen naar andere ruimte | `main_window.py`, `rack_dialog.py` | 🟠 Open |
| F8 | Volgorde wandpunt locaties bepalen in overzicht | `wall_outlet_view.py` | 🟠 Open |

---

## 3. Visuele verbeteringen

| ID | Omschrijving | Bestand(en) | Status |
|---|---|---|---|
| V1 | Wandpunt popup dubbel icoon in settings | `settings_window.py` | 🟡 Open |
| V2 | Custom gekleurde devices minder zichtbaar | `rack_view.py`, `main.qss` | 🟡 Open |
| V3 | Extra ruimte tussen devices in rack | `rack_view.py`, `place_device_dialog.py` | 🟡 Open |
| V4 | Afbeeldingexport rack te lang | export module | 🟡 Open |
| V5 | Wandpunten visueel groeperen per locatie | `wall_outlet_view.py` | ✅ Opgelost v1.4.0 |

---

## 4. Export

| ID | Omschrijving | Status |
|---|---|---|
| E1 | Word-export uitbreiden | 🔵 Open |
| E2 | Tekstuele rack-export | 🔵 Open |
| E3 | Afbeeldingexport rack compacter | 🔵 Open |

---

## 5. Security

| ID | Omschrijving | Status |
|---|---|---|
| S1 | MFA via AD | ⚪ Later |

---

## 6. Overig

| ID | Omschrijving | Status |
|---|---|---|
| O1 | CSV import | 🟣 Open |

---

## 7. SVG Tekeningen

| ID | Omschrijving | Status |
|---|---|---|
| G1 | Grondplan opladen + linken aan ruimte | 🟣 Open |
| G2 | Grondplan bekijken in applicatie | 🟣 Open |

---

## Aanbevolen volgorde

1. **B10** — Backup settings mee nemen *(volgende stap)*
2. **F7** — Rack verplaatsen naar andere ruimte
3. **F8** — Volgorde wandpunt locaties
4. **V1 + V2 + V3** — Visuele fixes
5. **F6** — Tracing per device groeperen
6. **E1 + E2 + E3** — Export
7. **G1 + G2** — SVG grondplannen
8. **O1** — CSV import
9. **S1** — MFA/AD
10. **B8** — Cross-side highlight herbekijken
11. **B2** — Cross-rack highlight

# Bugs - Extra
1. bestaande grondplan kunnen wissen
2. wandpunt eindapparaat kunnen aan maken zonder dat je een nieuw wandpunt moet maken
3. wandpunt locaties aan een site kunnen koppelen om zo DDL keuzes te beperken

