# Networkmap_Creator — Openstaande werkpunten

## A — Bugs & bijsturing


### Bug


## B Features
- Vlan kunnen ingeven en zo indirect naar wandpunt (dus ook zichtbaar zijn bij tracing)


### C Bijsturing
- Menubar
  -- [menubar_inexport]  , dit is visueelniet correct, naam moet im-export of betere benaming.
- Export word document.
  -- uitbreiden met toestel info (detail)
- exporteeren
  -- export bestand, open laatst gebruikte folder
  -- import bestand, open laatst gebruikte folder
  -- export afbeelding, open laatst gebruikte folder
  -- raport word, open laatst gebruikte folder

- afbeelding export
  -- niet duidelijk, te lange afbeelding van het rack.  
  

## D — MFA / Active Directory

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

