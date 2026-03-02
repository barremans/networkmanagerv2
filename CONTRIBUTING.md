<!--
CONTRIBUTING.md

Beschrijving: Contributie richtlijnen
Applicatie: networkmanager
Versie: 1.0.0
Auteur: Barremans
-->

# Bijdragen aan networkmanager

Bedankt voor je interesse!

## Development Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -e ".[dev]"
```

## Code Style

- Black voor formatting
- Flake8 voor linting
- MyPy voor type checking

## Tests

```bash
pytest
```

## i18n

Bij nieuwe UI teksten:
1. Gebruik `t("key.name")`
2. Voeg toe aan alle locale bestanden
3. Test in meerdere talen
