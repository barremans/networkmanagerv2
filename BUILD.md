<!--
BUILD.md

Beschrijving: Build documentatie en troubleshooting
Applicatie: networkmanager
Versie: 1.0.0
Auteur: Barremans
-->

# Build Instructies - networkmanager

## 🚀 Quick Start

```bash
venv\Scripts\activate
build.bat
```

## Output

```
dist/networkmanager_1.0.0/
└── networkmanager.exe
```

## Troubleshooting

### Python niet gevonden
```bash
python --version
venv\Scripts\activate
```

### Build faalde
```bash
pip install -r requirements.txt
pip install pyinstaller
build.bat
```

## Meer Info

- [PyInstaller Docs](https://pyinstaller.org)
- Scripts: `scripts/README.md`
