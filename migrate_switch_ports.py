"""
migrate_switch_ports.py
Eenmalig migratiescript: hernoemt poortnamen van switches naar correcte nummering.
Werkt op zowel dev-omgeving als geinstalleerde versie.
"""

import json
import shutil
import os
import sys
from datetime import datetime


def find_data_file() -> str:
    """Zoek het network_data.json bestand op alle mogelijke locaties."""

    # 1. Probeer via settings_storage (dev omgeving met venv)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from app.helpers import settings_storage
        path = settings_storage.get_network_data_path()
        if os.path.exists(path):
            print(f"OK Data gevonden via settings_storage: {path}")
            return path
    except Exception:
        pass

    # 2. Standaard APPDATA locaties (geinstalleerde versie)
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        candidates = [
            os.path.join(appdata, "Networkmap_Creator", "data", "network_data.json"),
            os.path.join(appdata, "Networkmap_Creator", "network_data.json"),
        ]
        for path in candidates:
            if os.path.exists(path):
                print(f"OK Data gevonden via APPDATA: {path}")
                return path

    # 3. Dev data map
    dev_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "network_data.json")
    if os.path.exists(dev_path):
        print(f"OK Data gevonden in dev map: {dev_path}")
        return dev_path

    # 4. Vraag handmatig
    print("\nData bestand niet automatisch gevonden.")
    print("Mogelijke locaties:")
    if appdata:
        print(f"  - {os.path.join(appdata, 'Networkmap_Creator', 'data', 'network_data.json')}")
    print(f"  - {dev_path}")
    path = input("\nGeef het volledige pad naar network_data.json: ").strip().strip('"')
    if os.path.exists(path):
        return path

    print(f"FOUT: bestand niet gevonden op: {path}")
    sys.exit(1)


def migrate(data: dict) -> tuple[dict, int]:
    dev_map = {d["id"]: d for d in data.get("devices", [])}
    count   = 0

    for port in data.get("ports", []):
        dev = dev_map.get(port.get("device_id", ""))
        if not dev:
            continue
        if dev.get("type") != "switch":
            continue

        front_ports   = dev.get("front_ports", 0)
        ports_per_row = dev.get("ports_per_row", 12)
        sfp_count     = dev.get("sfp_ports", 0)

        if front_ports <= ports_per_row:
            continue

        num  = port.get("number", 0)
        side = port.get("side", "")

        if side == "front" and sfp_count > 0 and num > front_ports:
            continue

        new_name = f"Port {num}"
        old_name = port.get("name", "")

        if old_name != new_name:
            port["name"] = new_name
            count += 1
            print(f"  [{dev['name']}] {side} port {num}: '{old_name}' -> '{new_name}'")

    return data, count


def main():
    print("=" * 60)
    print("  Networkmap Creator - Switch poort migratie")
    print("=" * 60)
    print()

    data_file = find_data_file()

    ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = data_file + f".backup_{ts}"
    shutil.copy2(data_file, backup)
    print(f"OK Backup gemaakt: {backup}\n")

    with open(data_file, encoding="utf-8") as f:
        data = json.load(f)

    switches = [
        d for d in data.get("devices", [])
        if d.get("type") == "switch"
        and d.get("front_ports", 0) > d.get("ports_per_row", 12)
    ]
    if switches:
        print(f"Switches met 2+ rijen gevonden ({len(switches)}):")
        for sw in switches:
            print(f"  - {sw['name']}  ({sw['front_ports']} poorten, "
                  f"{sw.get('ports_per_row', 12)} per rij)")
        print()
    else:
        print("Geen switches met 2+ rijen gevonden - niets te doen.")
        return

    print("Poortnamen controleren en aanpassen...\n")
    data, count = migrate(data)

    if count == 0:
        print("OK Alle poortnamen zijn al correct - geen wijzigingen nodig.")
    else:
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\nOK {count} poortnamen aangepast en opgeslagen naar:")
        print(f"  {data_file}")

    print("\nKlaar.")


if __name__ == "__main__":
    main()