"""
scripts\generate_requirements.py

Beschrijving: Genereer requirements.txt
Applicatie: networkmanager
Versie: 1.0.0
Auteur: Barremans
"""

"""
scripts/generate_requirements.py
Genereer requirements.txt
"""

import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()
    
    try:
        import tomli
    except ImportError:
        print("❌ tomli vereist")
        return
    
    toml_file = Path("../pyproject.toml")
    with open(toml_file, "rb") as f:
        data = tomli.load(f)
    
    requirements = []
    
    if "project" in data and "dependencies" in data["project"]:
        requirements.extend(data["project"]["dependencies"])
    
    if args.dev:
        if "project" in data and "optional-dependencies" in data["project"]:
            if "dev" in data["project"]["optional-dependencies"]:
                requirements.extend(data["project"]["optional-dependencies"]["dev"])
    
    output_file = Path("../requirements.txt")
    with open(output_file, "w") as f:
        f.write("# Gegenereerd uit pyproject.toml\n\n")
        for req in requirements:
            f.write(f"{req}\n")
    
    print(f"✅ {len(requirements)} dependencies → requirements.txt")

if __name__ == "__main__":
    main()
