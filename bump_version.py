# bump_version.py
#
# Beschrijving: Verhoog de versie in app/version.py
# Gebruik:      python bump_version.py [patch|minor|major]
# Standaard:    patch
# Applicatie:   Networkmap_Creator
# Auteur:       Barremans

import re
import sys
from pathlib import Path

VERSION_FILE = Path("app/version.py")


def read_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*["\']([0-9]+\.[0-9]+\.[0-9]+)["\']', text)
    if not match:
        print(f"❌ Geen __version__ gevonden in {path}")
        sys.exit(1)
    return match.group(1)


def bump(version: str, part: str) -> str:
    major, minor, patch = map(int, version.split("."))
    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1
    else:
        print(f"❌ Ongeldig part '{part}'. Gebruik: patch, minor of major.")
        sys.exit(1)
    return f"{major}.{minor}.{patch}"


def write_version(path: Path, new_version: str):
    text = path.read_text(encoding="utf-8")
    updated = re.sub(
        r'(__version__\s*=\s*["\'])[0-9]+\.[0-9]+\.[0-9]+(["\'])',
        rf'\g<1>{new_version}\g<2>',
        text,
    )
    path.write_text(updated, encoding="utf-8")


def main():
    part = sys.argv[1].lower() if len(sys.argv) > 1 else "patch"

    if not VERSION_FILE.exists():
        print(f"❌ Bestand niet gevonden: {VERSION_FILE}")
        sys.exit(1)

    old_version = read_version(VERSION_FILE)
    new_version = bump(old_version, part)
    write_version(VERSION_FILE, new_version)

    print(f"✅ Versie verhoogd: {old_version} → {new_version}  ({VERSION_FILE})")


if __name__ == "__main__":
    main()