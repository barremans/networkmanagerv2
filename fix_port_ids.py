"""
Fix duplicate port IDs in network_data.json.
Elke poort krijgt een uniek gegenereerd ID.
Verbindingen worden bijgewerkt naar de nieuwe IDs.
"""
import json
import time

# ── Inladen ────────────────────────────────────────────────────────────────
with open("data/network_data.json", encoding="utf-8") as f:
    data = json.load(f)

ports       = data.get("ports", [])
connections = data.get("connections", [])

# ── Detecteer duplicaten ────────────────────────────────────────────────────
from collections import Counter
id_counts = Counter(p["id"] for p in ports)
duplicates = {pid for pid, cnt in id_counts.items() if cnt > 1}
print(f"Gevonden {len(duplicates)} duplicate port ID(s): {duplicates}")

# ── Genereer nieuwe unieke IDs ──────────────────────────────────────────────
used_ids = set(p["id"] for p in ports)

def new_id(device_id: str, side: str, number: int) -> str:
    """Genereer een uniek poort-ID op basis van device + side + nummer."""
    dev_short = device_id.replace("dev_", "")
    candidate = f"p_{dev_short}_{side[0]}{number}"
    suffix = 0
    base = candidate
    while candidate in used_ids:
        suffix += 1
        candidate = f"{base}_{suffix}"
    used_ids.add(candidate)
    return candidate

# ── Bouw mapping old_id → new_id per poort-object ──────────────────────────
# Poorten met een uniek ID behouden hun ID.
# Poorten met een duplicaat ID krijgen een nieuw ID op basis van device+side+number.

port_id_map = {}  # (port_index) → new_id

for i, port in enumerate(ports):
    old_id = port["id"]
    if old_id not in duplicates:
        port_id_map[i] = old_id  # ongewijzigd
    else:
        port_id_map[i] = new_id(
            port["device_id"], port["side"], port["number"]
        )

# ── Pas verbindingen aan ────────────────────────────────────────────────────
# Verbindingen verwijzen naar port IDs. We moeten weten welke SPECIFIEKE poort
# bedoeld wordt. Omdat de originele verbindingen gemaakt zijn op basis van
# de eerste poort met dat ID, mappen we elke duplicate ID naar de EERSTE
# poort met dat ID die de originele betekenis had.

# Bouw: old_duplicate_id → index van eerste poort met dat ID
first_occurrence = {}
for i, port in enumerate(ports):
    if port["id"] not in first_occurrence:
        first_occurrence[port["id"]] = i

# Verbindingen updaten: vervang duplicate IDs door het nieuwe ID van de
# eerste poort met dat ID (de bedoelde poort bij het aanmaken van de verbinding)
for conn in connections:
    if conn.get("from_type") == "port" and conn["from_id"] in duplicates:
        idx = first_occurrence[conn["from_id"]]
        conn["from_id"] = port_id_map[idx]
        print(f"  Verbinding {conn['id']}: from_id bijgewerkt → {conn['from_id']}")

    if conn.get("to_type") == "port" and conn["to_id"] in duplicates:
        idx = first_occurrence[conn["to_id"]]
        conn["to_id"] = port_id_map[idx]
        print(f"  Verbinding {conn['id']}: to_id bijgewerkt → {conn['to_id']}")

# ── Pas poort IDs aan ──────────────────────────────────────────────────────
for i, port in enumerate(ports):
    port["id"] = port_id_map[i]

# ── Verifieer: geen duplicaten meer ────────────────────────────────────────
final_ids = [p["id"] for p in ports]
final_counts = Counter(final_ids)
remaining = {pid for pid, cnt in final_counts.items() if cnt > 1}
if remaining:
    print(f"⚠  Nog steeds duplicaten: {remaining}")
else:
    print(f"✓  Alle {len(ports)} poorten hebben nu een uniek ID.")

# ── Opslaan ────────────────────────────────────────────────────────────────
data["ports"]       = ports
data["connections"] = connections

with open("data/network_data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("✓  data/network_data.json opgeslagen.")