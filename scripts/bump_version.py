"""
scripts\bump_version.py

Beschrijving: Verhoog versie
Applicatie: networkmanager
Versie: 1.0.0
Auteur: Barremans
"""

"""
scripts/bump_version.py
Verhoog versienummer
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import date

def parse_version(version_str: str) -> tuple:
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", version_str)
    if not match:
        raise ValueError(f"Ongeldige versie: {version_str}")
    return tuple(map(int, match.groups()))

def bump_version(current: str, bump_type: str) -> str:
    major, minor, patch = parse_version(current)
    
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Onbekend type: {bump_type}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bump_type", choices=["major", "minor", "patch"])
    args = parser.parse_args()
    
    version_file = Path("../app/version.py")
    if not version_file.exists():
        print("❌ version.py niet gevonden")
        sys.exit(1)
    
    content = version_file.read_text()
    match = re.search(r'__version__\s*=\s*["\'](\d+\.\d+\.\d+)["\']', content)
    
    if not match:
        print("❌ Versie niet gevonden")
        sys.exit(1)
    
    current_version = match.group(1)
    new_version = bump_version(current_version, args.bump_type)
    
    print(f"🚀 {current_version} → {new_version}")
    
    # Update version.py
    new_content = re.sub(
        r'__version__\s*=\s*["\'][\d.]+["\']',
        f'__version__ = "{new_version}"',
        content
    )
    version_file.write_text(new_content)
    
    print("✅ Versie verhoogd!")

if __name__ == "__main__":
    main()
