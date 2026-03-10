# =============================================================================
# Patch script — voeg VLAN i18n sleutels toe aan app/helpers/i18n.py
# Uitvoeren vanuit app/ map: python3 i18n_vlan_patch.py
# =============================================================================
import re

TARGET = "helpers/i18n.py"

NL_INSERT = '''        # --- VLAN
        "vlan_report_no_vlans":     "Geen VLAN toewijzingen gevonden.",
        "vlan_report_title":        "VLAN rapport",
        "vlan_manager_title":       "VLAN beheer",
        "vlan_conflict_title":      "VLAN conflict",
        "vlan_propagate_confirm":   "Propageer naar hele trace?",
'''

EN_INSERT = '''        # --- VLAN
        "vlan_report_no_vlans":     "No VLAN assignments found.",
        "vlan_report_title":        "VLAN report",
        "vlan_manager_title":       "VLAN management",
        "vlan_conflict_title":      "VLAN conflict",
        "vlan_propagate_confirm":   "Propagate to entire trace?",
'''

with open(TARGET, encoding="utf-8") as f:
    content = f.read()

# Check al gepatcht
if "vlan_report_no_vlans" in content:
    print("Al gepatcht — geen wijzigingen.")
else:
    # NL: invoegen na ctx_ports_device in NL sectie
    nl_anchor = '        "ctx_ports_device": "Poorten beheren",'
    en_anchor = '        "ctx_ports_device": "Manage ports",'

    if nl_anchor not in content:
        print(f"ERROR: NL anchor niet gevonden:\n  {nl_anchor}")
    elif en_anchor not in content:
        print(f"ERROR: EN anchor niet gevonden:\n  {en_anchor}")
    else:
        content = content.replace(nl_anchor, nl_anchor + "\n" + NL_INSERT, 1)
        content = content.replace(en_anchor, en_anchor + "\n" + EN_INSERT, 1)
        with open(TARGET, "w", encoding="utf-8") as f:
            f.write(content)
        print("✓  i18n.py bijgewerkt met VLAN sleutels.")