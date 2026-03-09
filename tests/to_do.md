# Networkmap_Creator — Openstaande werkpunten

## A — Bugs & bijsturing

### Bug
- nieuw toestel (via instellingen -Device) toegevoegd
  -- nieuw device toevoegen aan Rack => device staat niet in de lijst van keuzes
  -- bij nader inzien zijn niet alle types beschikbaar (waarschijnlijk hardcoded?).
- visueele bug
  - toevoegen nieuw toestel => geen refresh, ik moet naar ander object en dan terug naar het eerste object (in dit geval rack 1)


### Bijsturing
- Rack nummering
  -- keuze hoogste  rij boven of onder
  -- bestaande volgorde aanpassen bij aanpassen rackrij volgorde
- patchpanel aantal poorten 
  - patchpanel is altijd 2 rijen
    -- keuze 1 of 2 rijen.
- Switch
  -- switch keuze 1 of 2 rijen (nu 28 en wordt 3 rijen, 24 wordt 2 rijen, dus aanpassen breedte)

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

