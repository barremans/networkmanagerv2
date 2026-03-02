"""
scripts\update_toml.py

Beschrijving: Update pyproject.toml
Applicatie: networkmanager
Versie: 1.0.0
Auteur: Barremans
"""

"""
scripts/update_toml.py
Update pyproject.toml automatisch
"""

import argparse
import sys
from pathlib import Path
import shutil

def main():
    parser = argparse.ArgumentParser(description="Update pyproject.toml")
    parser.add_argument("--add-dep", help="Voeg runtime dependency toe")
    parser.add_argument("--add-dev", help="Voeg dev dependency toe")
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    toml_file = project_root / "pyproject.toml"
    
    if not toml_file.exists():
        print(f"❌ {toml_file} niet gevonden")
        sys.exit(1)
    
    try:
        import tomli
        import tomli_w
    except ImportError:
        print("❌ tomli en tomli_w vereist")
        sys.exit(1)
    
    with open(toml_file, "rb") as f:
        data = tomli.load(f)
    
    shutil.copy2(toml_file, toml_file.with_suffix(".toml.bak"))
    
    if args.add_dep:
        if "project" not in data:
            data["project"] = {}
        if "dependencies" not in data["project"]:
            data["project"]["dependencies"] = []
        
        if args.add_dep not in data["project"]["dependencies"]:
            data["project"]["dependencies"].append(args.add_dep)
            print(f"✅ Dependency toegevoegd: {args.add_dep}")
    
    with open(toml_file, "wb") as f:
        tomli_w.dump(data, f)
    
    print("✅ Klaar!")

if __name__ == "__main__":
    main()
