"""
scripts\validate_project.py

Beschrijving: Valideer project
Applicatie: networkmanager
Versie: 1.0.0
Auteur: Barremans
"""

"""
scripts/validate_project.py
Valideer project structuur
"""

from pathlib import Path

def check_file(path: Path) -> bool:
    exists = path.exists()
    print(f"{'✅' if exists else '❌'} {path.name}")
    return exists

def main():
    print("🔍 Project Validatie\n")
    
    print("📄 Bestanden:")
    all_ok = True
    all_ok &= check_file(Path("../pyproject.toml"))
    all_ok &= check_file(Path("../README.md"))
    all_ok &= check_file(Path("../LICENSE"))
    
    print("\n📁 Folders:")
    all_ok &= check_file(Path("../app"))
    all_ok &= check_file(Path("../tests"))
    all_ok &= check_file(Path("../i18n"))
    
    print("\n" + ("✅ OK" if all_ok else "❌ Problemen gevonden"))

if __name__ == "__main__":
    main()
