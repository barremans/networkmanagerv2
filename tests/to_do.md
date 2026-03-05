# Networkmap_Creator — Openstaande werkpunten

## A — Bugs & bijsturing

### Bugs
- [ ] **Device verwijderen**: scherm refresht niet automatisch  
  _Workaround_: eerst naar een ander object navigeren en terug.
- [ ] **Wandpunten**: dubbel icoon zichtbaar

### Bijsturing
- [ ] **Logging**
  - [ ] Logging bijhouden van **wijzigingen/toevoegingen**
  - [ ] Later uitbreiden met **wie** de aanpassingen deed (na fase F)

---

## E — Rapporteren naar GitHub

- [ ] **Bug melden**: knop in Help-menu → opent GitHub Issues met vooringevulde template
- [ ] **Feature aanvragen**: idem

---

## F — MFA / Active Directory

- [ ] **MFA introduceren**
  - [ ] Standaard **niet actief**
  - [ ] Activeerbaar via **installer (Inno Setup)** of via **settings**
  - [ ] Gebruiker moet **niveau 5** bestaan in Active Directory
  - [ ] Indien onvoldoende rechten → **popup** + applicatie **sluit**
  - [ ] AD-server **hardcoded** voor CGK, maar **configureerbaar** via settings
  - [ ] **Open vraag**: activatie via GitHub builds?
    - Optie: Inno Setup installer flag
    - Optie: setting in build/config

---

## G — Uitbreiding

### Layout

#### Menubalk (eerste)
- [ ] Extra menu toevoegen: **In/Ex-port (New)**
  - [ ] **Importeren** verplaatsen van menu **Bestand** → **In/Ex-port**
  - [ ] **Exporteren** verplaatsen van menu **Bestand** → **In/Ex-port**

#### Menubalk (tweede)
- [ ] **Importeren** verwijderen (zit al onder **In/Ex-port**)
- [ ] **Exporteren** verwijderen (zit al onder **In/Ex-port**)