# Networkmap_Creator — Openstaande werkpunten

> Bijgewerkt na implementatie Fase A t/m E (volledig stabiel).
> Opgeloste punten zijn verwijderd. Nieuw opgeloste punten staan onder "Opgelost".

---

## Fase F — Correcties & configuratie

### F3 — Lokale vs netwerkdata

- [ ] **Keuze of network_data.json lokaal of op netwerkmap staat**
  - Instelling in settings venster (backend klaar, UI ontbreekt nog)
  - Fallback naar lokaal als netwerkpad niet bereikbaar

### F4 — Update check

- [ ] **Update check naar GitHub** — bij opstarten controleren op nieuwere versie
  - URL configureerbaar in settings
  - Indien leeg: standaard URL hardcoded in code
  - Popup bij nieuwe versie: "Versie X.Y beschikbaar — Naar GitHub?"

---

## Fase G — Export & printing

### G1 — PDF export

- [ ] **PDF export van het netwerk**
  - Volledig per geselecteerde site
  - Per ruimte
  - Per rack

### G2 — Afbeelding export

- [ ] **JPG/PNG export** — schermafbeelding van rack_view of wall_outlet_view

---

## Fase H — Afronden & beveiliging

### H1 — Help menu

- [ ] **Help menu toevoegen**
  - Sneltoetsen overzicht
  - Versie-info
  - Gebruiksaanwijzing

### H2 — Rapporteren naar GitHub

- [ ] **Bug melden** — knop in help menu, opent GitHub issues met vooringevulde template
- [ ] **Feature aanvragen** — idem

### H3 — MFA / Active Directory

- [ ] **MFA introduceren**
  - Standaard niet actief — activeren via installer (Inno Setup) of settings
  - Gebruiker moet op niveau 5 bestaan in Active Directory
  - Indien geen rechten → popup + applicatie sluit
  - AD-server hardcoded voor CGK, maar configureerbaar via settings
  - Open vraag: hoe activeren via GitHub builds? Via Inno Setup installer flag?

---

## Ontbrekend — nog niet ingepland

- [ ] **Verbinding bewerken** — kabeltype en notitie aanpassen na aanmaken (nu alleen verwijderen mogelijk)
- [ ] **Duplicaat-check wandpunten** — naam uniek per ruimte verplichten
- [ ] **Rack bezettingsgraad** — visuele indicator hoeveel U vrij/bezet per rack

---
