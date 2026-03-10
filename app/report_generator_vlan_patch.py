# =============================================================================
# Networkmap_Creator — PATCH SCRIPT
# Toepassen: python3 report_generator_vlan_patch.py
# Past report_generator.py v1.0.0 → v1.1.0 aan
# Voegt VLAN overzicht sectie toe aan Word export
# =============================================================================
import sys, os

TARGET = "services/report_generator.py"
if not os.path.exists(TARGET):
    print(f"FOUT: {TARGET} niet gevonden. Voer dit script uit vanuit de project root.")
    sys.exit(1)

with open(TARGET, encoding="utf-8") as f:
    src = f.read()

if "# Version: 1.1.0" in src:
    print("Patch al toegepast (v1.1.0 aanwezig). Geen wijzigingen.")
    sys.exit(0)

# ── 1. Versie ────────────────────────────────────────────────────────────────
src = src.replace("# Version: 1.0.0", "# Version: 1.1.0", 1)

# ── 2. Aanroep in _build_docx vóór doc.save ──────────────────────────────────
OLD_SAVE = "    # ── Opslaan ──────────────────────────────────────────────────────────────\n    doc.save(filepath)"
NEW_SAVE = """    # ── VLAN rapport ─────────────────────────────────────────────────────────
    _build_vlan_section(doc, data, idx)

    # ── Opslaan ──────────────────────────────────────────────────────────────
    doc.save(filepath)"""
if OLD_SAVE not in src:
    print("FOUT: ankerpunt '# ── Opslaan' niet gevonden. Controleer de broncode.")
    sys.exit(1)
src = src.replace(OLD_SAVE, NEW_SAVE, 1)

# ── 3. Nieuwe functie _build_vlan_section ────────────────────────────────────
OLD_TEST = "# ---------------------------------------------------------------------------\n# Standalone test\n# ---------------------------------------------------------------------------"
VLAN_FUNC = '''# ---------------------------------------------------------------------------
# VLAN sectie — v1.1.0
# ---------------------------------------------------------------------------

def _build_vlan_section(doc, data: dict, idx: dict):
    """Voeg VLAN overzicht toe aan het Word rapport."""
    vlan_map = {}
    for p in data.get("ports", []):
        v = p.get("vlan")
        if v:
            vlan_map.setdefault(int(v), []).append(p)

    if not vlan_map:
        return

    _spacer(doc, 16)
    _heading_para(doc, "\U0001f537  VLAN overzicht", level=1)
    _para(doc, f"  Totaal: {len(vlan_map)} VLAN(s) geconfigureerd",
          size_pt=9, color_hex=_C_MUTED, space_after=6)

    device_location = {}
    for site in data.get("sites", []):
        for room in site.get("rooms", []):
            for rack in room.get("racks", []):
                for slot in rack.get("slots", []):
                    dev_id = slot.get("device_id")
                    if dev_id:
                        device_location[dev_id] = (site, room, rack)

    for vlan_num in sorted(vlan_map.keys()):
        ports = vlan_map[vlan_num]
        _heading_para(doc,
            f"VLAN {vlan_num}  \u2014  {len(ports)} poort{'en' if len(ports) != 1 else ''}",
            level=3)

        W_VLAN = [3.5, 2.5, 2.0, 4.0]
        tbl = _make_table(doc,
            ["Device", "Poort", "Zijde", "Verbonden met"],
            W_VLAN)
        for pi, p in enumerate(sorted(ports,
                key=lambda x: (x.get("device_id",""), x["side"], x["number"]))):
            dev = idx["dev"].get(p["device_id"])
            loc = device_location.get(p["device_id"])
            dev_label = dev["name"] if dev else p["device_id"]
            if loc:
                _, room_l, rack_l = loc
                dev_label += f"  ({rack_l['name']}, {room_l['name']})"
            side_str = "VOOR" if p["side"] == "front" else "ACHTER"
            dest = _conn_label(data, idx, p["id"])
            _add_table_row(tbl, [
                dev_label,
                p.get("name", f"Port {p['number']}"),
                side_str,
                dest
            ], W_VLAN, shade=(pi % 2 == 1))

        # Wandpunten indirect via dit VLAN
        vlan_port_ids = {p["id"] for p in ports}
        outlet_rows = []
        for conn in data.get("connections", []):
            from_vlan = (conn.get("from_type") == "port"
                         and conn.get("from_id") in vlan_port_ids)
            to_vlan   = (conn.get("to_type") == "port"
                         and conn.get("to_id") in vlan_port_ids)
            if from_vlan and conn.get("to_type") == "wall_outlet":
                outlet_rows.append((conn["to_id"], conn["from_id"]))
            elif to_vlan and conn.get("from_type") == "wall_outlet":
                outlet_rows.append((conn["from_id"], conn["to_id"]))

        if outlet_rows:
            _para(doc, f"  Wandpunten via VLAN {vlan_num}:",
                  size_pt=9, color_hex=_C_MID_TEXT,
                  bold=True, space_before=4, space_after=2)
            W_WO_VLAN = [3.0, 3.0, 6.0]
            tbl_wo = _make_table(doc,
                ["Wandpunt", "Locatie", "Via poort"], W_WO_VLAN)
            for wi, (outlet_id, port_id) in enumerate(outlet_rows):
                wo = room_name = None
                for s in data.get("sites", []):
                    for r in s.get("rooms", []):
                        for w in r.get("wall_outlets", []):
                            if w["id"] == outlet_id:
                                wo, room_name = w, r["name"]
                p_obj = next((x for x in data.get("ports", [])
                              if x["id"] == port_id), None)
                d_obj = idx["dev"].get(p_obj["device_id"]) if p_obj else None
                port_label = (f"{d_obj['name']} / {p_obj['name']}"
                              if p_obj and d_obj else port_id)
                _add_table_row(tbl_wo, [
                    wo.get("name", outlet_id) if wo else outlet_id,
                    room_name or "\u2014",
                    port_label
                ], W_WO_VLAN, shade=(wi % 2 == 1))

        _spacer(doc, 6)


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------'''

if OLD_TEST not in src:
    print("FOUT: ankerpunt '# Standalone test' niet gevonden.")
    sys.exit(1)
src = src.replace(OLD_TEST, VLAN_FUNC, 1)

with open(TARGET, "w", encoding="utf-8") as f:
    f.write(src)

print(f"OK: {TARGET} bijgewerkt naar v1.1.0")
print("Nieuwe sectie: VLAN overzicht toegevoegd aan Word rapport")