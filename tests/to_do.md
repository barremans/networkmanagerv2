# Networkmap_Creator — Openstaande werkpunten

## 1. Bugs

- **Manuele backup werkt niet**
  - Foutmelding:
    - `Backup mislukt. Controleer het netwerkpad.`
    - `Geen schrijfrechten op: //wsqlvsOI/Cutrite/Networkmapping`

- **Netwerkdata wordt niet automatisch ververst**
  - Wanneer twee machines met dezelfde netwerkmap werken, zijn wijzigingen van machine 1 niet zichtbaar op machine 2.
  - Er ontbreekt een automatische refresh wanneer de brondata nieuwer is.

- **Synchronisatie lokaal ↔ netwerk ontbreekt**
  - De applicatie moet controleren of het lokale bestand en het netwerkbestand gelijk lopen.
  - Er moet altijd een lokaal bestand beschikbaar zijn, ook wanneer men met netwerkdata werkt, zodat offline werken mogelijk blijft.
  - Indien lokaal nieuwer is dan netwerk: netwerk updaten.
  - Indien netwerk nieuwer is dan lokaal: lokaal updaten.

- **Uitlijning van verbindingen op switches klopt niet**
  - Bij het maken van een verbinding op een switch wordt de poort visueel verbreed.
  - Daardoor verschuift de lijn t.o.v. andere lijnen.
  - Dit is vooral een probleem bij devices met meerdere lijnen.

- **VLAN-overzicht in export niet correct**
  - Het veld **“Via poort”** is leeg, terwijl er wel een koppeling is met bijvoorbeeld `Patchpanel A port 20`.

- **Tracing-volgorde bij rack tracing is omgekeerd**
  - Huidige weergave:
    - `Patchpanel A - Port 20 (Back) => A20 (VLAN 100) => Airtame Xperience`
  - Gewenste weergave:
    - `Airtame Xperience => A20 (VLAN 100) => Patchpanel A - Port 20 (Back)`

---

## 2. Functionele verbeteringen

### 2.1 Settings

- **Wandpunt**
  - pop-up icon
    - dubbel icoon

- **Databron**
  - Ondersteuning verbeteren voor werken met:
    - lokale databron
    - netwerkdatabron
    - automatische vergelijking en synchronisatie tussen beide

- **Backup**
  - Automatisch backup laten uitvoeren bij het afsluiten van de applicatie.

### 2.2 Toegangsmodus

- De applicatie moet standaard in **read-only** openen.
- Via **settings** moet bewerken expliciet kunnen worden ingeschakeld.
- De huidige modus moet duidelijk zichtbaar zijn in de applicatie:
  - `"read"`
  - `"R/W"`

### 2.3 Wandpunten

### 2.4 Tracing en overzicht

- Het huidige overzicht groepeert reeds per:
  - site
  - ruimte
- Dit uitbreiden zodat ook gegroepeerd kan worden per device:
  - bijvoorbeeld `Patchpanel A` → bijhorende wandpunten

---

## 3. Visuele verbeteringen

- Devices in een rack een **kleur** kunnen geven.
- Device laten **oplichten bij hover**.
  - Dit maakt het duidelijker wanneer verbindingen worden gelegd.

- Mogelijk extra **ruimte tussen devices in een rack** voorzien.
  - Rekening houden met de hoogte van het device.

- I18n.py bijsturen
  - benaming niet kompleet, Kabelgoot staat er [device_cable_management]

- **Afbeelding export**
  - De huidige rack-afbeelding is te lang en onvoldoende duidelijk.
  - Export compacter en leesbaarder maken.

---

## 4. Export

### 4.1 Word-export

- Export uitbreiden met:
  - toestelinfo
  - detailinformatie
  - VLAN-overzicht

### 4.2 Afbeeldingexport

- Rackweergave duidelijker exporteren.
- Vermijden dat de afbeelding te lang en moeilijk leesbaar wordt.

---

## 5. Security — MFA / Active Directory

- [ ] **MFA introduceren**
  - [ ] Standaard **niet actief**
  - [ ] Activeerbaar via:
    - [ ] **installer (Inno Setup)**
    - [ ] **settings**
  - [ ] Gebruiker moet **niveau 5** hebben in Active Directory
  - [ ] Indien onvoldoende rechten:
    - [ ] popup tonen
    - [ ] applicatie sluiten
  - [ ] AD-server standaard **hardcoded voor CGK**
  - [ ] AD-server ook **configureerbaar via settings**

### Open vraag

- [ ] Hoe MFA-activatie koppelen aan GitHub builds?
  - [ ] Optie 1: via **Inno Setup installer flag**
  - [ ] Optie 2: via **setting in build/config**

---

## 6. Overig

- Direct uitlezen.