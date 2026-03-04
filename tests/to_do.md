# Networkmap_Creator — Openstaande werkpunten

## Fase B — Setup + installer
- Creatie applicatie executable voor windows
- Creatie van setup.exe file voor windows van de applicatie.exe + mappen


## Fase C — build + upload to github
-- bat file autoatische build 
  - applicatie.exe -> build setup.exe -> upload naar github



### D — Update check

- [ ] **Update check naar GitHub** — bij opstarten controleren op nieuwere versie
  - URL configureerbaar in settings
  - Indien leeg: standaard URL hardcoded in code
  - Popup bij nieuwe versie: "Versie X.Y beschikbaar — Naar GitHub?"

---
### E — Rapporteren naar GitHub

- [ ] **Bug melden** — knop in help menu, opent GitHub issues met vooringevulde template
- [ ] **Feature aanvragen** — idem

### F — MFA / Active Directory

- [ ] **MFA introduceren**
  - Standaard niet actief — activeren via installer (Inno Setup) of settings
  - Gebruiker moet op niveau 5 bestaan in Active Directory
  - Indien geen rechten → popup + applicatie sluit
  - AD-server hardcoded voor CGK, maar configureerbaar via settings
  - Open vraag: hoe activeren via GitHub builds? Via Inno Setup installer flag?

---



## Layout
- Menu balk (eerste)
  - extra menu 
      -- In/Ex-port(New)
          - Menu Importeren
            -- Importeren van menu "Bestand" naar menu "In/Export" menu
            -- Exoprteren van menu "Bestand" naar menu "In/Export" menu
  - 
 -- Menubalk (tweede)
    - importeren weg, zit al onder eerste menu -> "In/Ex-port" menu
    - exporteren weg, zit al onder eerste menu -> "In/Ex-port" menu





-- BUGS
  - verwijderen device, geen refresh van scherm je moet eens naar een ander object gaan en terug
  -- Wandpunten
    - dubbel icoon
  - wanneer we de optie opslaan hebben, dan "enter" als sneltoets