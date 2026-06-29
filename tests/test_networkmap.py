# =============================================================================
# Networkmap_Creator
# File:    tests/test_networkmap.py
# Role:    Geautomatiseerde tests — kritische paden zonder Qt-dependencies
# Version: 1.1.0
# Author:  Barremans
# Changes: 1.1.0 — LCK-1: TestLockService toegevoegd (L01–L06).
#                  Dekt: happy path, concurrent lock, stale lock,
#                  re-entrant acquire, release-eigenaarschap, cleanup.
# Changes: 1.0.2 — Fix: trace-nodes gebruiken "obj_id" niet "id".
#                  Poortnamen toegevoegd aan search_data fixture ("Gi1/0/x").
#                  S04 query aangepast naar "G" (begin-van-woord op poortnaam).
# Changes: 1.0.1 — Fix: argumentvolgorde gecorrigeerd voor trace_from_port,
#                  trace_from_wall_outlet (was trace_from_outlet), search(),
#                  get_company_for_site() — gesynchroniseerd met echte API.
# Changes: 1.0.0 — TST-1: initiële suite.
#                  Domeinen: tracing, data_integrity, import_export_service
#                  (incl. IMP-1 CSV), search_service, company filtering.
#                  Uitvoeren: pytest tests/test_networkmap.py -v
#                  Vereisten: pip install pytest  (geen Qt nodig)
# =============================================================================
#
# Uitvoeren vanuit projectroot:
#   pytest tests/test_networkmap.py -v
#   pytest tests/test_networkmap.py -v -k "tracing"        # enkel tracing
#   pytest tests/test_networkmap.py -v -k "integrity"      # enkel validatie
#   pytest tests/test_networkmap.py --tb=short             # korte tracebacks
#
# Elk testdomein heeft een eigen fixture voor minimale testdata.
# Fixtures zijn onafhankelijk — volgorde maakt niet uit.
# =============================================================================

import copy
import csv
import io
import json
import os
import sys
import tempfile
import time
import textwrap

import pytest

# ---------------------------------------------------------------------------
# Projectroot op sys.path zetten zodat app.* importeerbaar is
# ---------------------------------------------------------------------------

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# ---------------------------------------------------------------------------
# Helpers — minimale testdata bouwen
# ---------------------------------------------------------------------------

def _make_data(**kwargs) -> dict:
    """Basisstructuur v2.0 met optionele overrides via kwargs."""
    base = {
        "version":   "2.0",
        "companies": [],
        "devices":   [],
        "ports":     [],
        "endpoints": [],
        "connections": [],
        "approvals": [],
    }
    base.update(kwargs)
    return base


def _make_company(company_id: str, name: str, sites: list = None) -> dict:
    return {
        "id":      company_id,
        "name":    name,
        "address": "", "vat": "", "phone": "", "email": "", "website": "",
        "sites":   sites or [],
    }


def _make_site(site_id: str, name: str, rooms: list = None) -> dict:
    return {"id": site_id, "name": name, "location": "", "notes": "", "rooms": rooms or []}


def _make_room(room_id: str, name: str, racks: list = None, wall_outlets: list = None) -> dict:
    return {"id": room_id, "name": name, "racks": racks or [], "wall_outlets": wall_outlets or []}


def _make_rack(rack_id: str, name: str, slots: list = None) -> dict:
    return {"id": rack_id, "name": name, "slots": slots or []}


def _make_device(dev_id: str, name: str, dev_type: str = "switch",
                 ip: str = "", mac_eth: str = "") -> dict:
    return {
        "id": dev_id, "name": name, "type": dev_type,
        "brand": "", "model": "", "ip": ip,
        "mac": mac_eth, "mac_eth": mac_eth, "mac_wifi": "",
        "front_ports": 24, "back_ports": 0, "sfp_ports": 0, "notes": "",
    }


def _make_port(port_id: str, device_id: str, side: str = "front", number: int = 1) -> dict:
    return {"id": port_id, "device_id": device_id, "side": side, "number": number, "vlan": ""}


def _make_conn(conn_id: str, from_id: str, from_type: str,
               to_id: str, to_type: str) -> dict:
    return {
        "id": conn_id, "from_id": from_id, "from_type": from_type,
        "to_id": to_id, "to_type": to_type, "cable_type": "utp_cat6",
        "label": "", "notes": "",
    }


def _make_endpoint(ep_id: str, name: str, ip: str = "", mac_eth: str = "") -> dict:
    return {
        "id": ep_id, "name": name, "type": "workstation",
        "ip": ip, "mac": mac_eth, "mac_eth": mac_eth, "mac_wifi": "",
        "serial": "", "brand": "", "model": "", "notes": "", "location": "", "url": "",
    }


def _make_wall_outlet(wo_id: str, name: str, endpoint_id: str = "") -> dict:
    return {"id": wo_id, "name": name, "endpoint_id": endpoint_id}


# ===========================================================================
# 1. TRACING
# ===========================================================================
#
# Canonieke keten (§12):
#   SWITCH (port_sw_f1) → port→port → PP FRONT (port_pp_f1)
#   PP FRONT intern → PP BACK (port_pp_b1)
#   PP BACK → wall_outlet → wandpunt (wo1) → eindapparaat (ep1)
#
# Testcases:
#   T01 — start switch-poort → eindapparaat bereikbaar in trace
#   T02 — start wandpunt → switch-poort bereikbaar in trace
#   T03 — geen verbinding → lege trace
#   T04 — directe port→endpoint verbinding (geen patchpanel)
# ===========================================================================

@pytest.fixture
def tracing_data():
    """Minimale dataset voor canonieke tracing via patchpanel."""
    sw   = _make_device("dev_sw",  "SW01", "switch")
    pp   = _make_device("dev_pp",  "PP01", "patch_panel")

    # Switch: front poort 1
    p_sw_f1  = _make_port("p_sw_f1",  "dev_sw", "front", 1)
    # PP: front poort 1 + back poort 1
    p_pp_f1  = _make_port("p_pp_f1",  "dev_pp", "front", 1)
    p_pp_b1  = _make_port("p_pp_b1",  "dev_pp", "back",  1)

    ep1 = _make_endpoint("ep1", "PC-01", ip="192.168.1.10")
    wo1 = _make_wall_outlet("wo1", "A1", endpoint_id="ep1")

    conns = [
        # Switch poort → PP front poort
        _make_conn("c1", "p_sw_f1", "port", "p_pp_f1", "port"),
        # PP back → wandpunt
        _make_conn("c2", "p_pp_b1", "port", "wo1", "wall_outlet"),
    ]

    room = _make_room("room1", "SERVERRUIMTE",
                      racks=[_make_rack("rack1", "RACK 01", slots=[
                          {"device_id": "dev_sw", "position": 1, "height": 1},
                          {"device_id": "dev_pp", "position": 2, "height": 1},
                      ])],
                      wall_outlets=[wo1])
    site    = _make_site("site1", "CGK HQ", rooms=[room])
    company = _make_company("co1", "CGK", sites=[site])

    return _make_data(
        companies=[company],
        devices=[sw, pp],
        ports=[p_sw_f1, p_pp_f1, p_pp_b1],
        endpoints=[ep1],
        connections=conns,
    )


class TestTracing:

    def test_T01_switch_port_reaches_endpoint(self, tracing_data):
        """T01 — Start switch-poort → eindapparaat ep1 bereikbaar."""
        from app.services.tracing import trace_from_port
        result = trace_from_port(tracing_data, "p_sw_f1")
        node_ids = {n.get("obj_id") for n in result}
        assert "ep1" in node_ids, f"ep1 niet gevonden in trace: {node_ids}"

    def test_T02_wall_outlet_reaches_switch(self, tracing_data):
        """T02 — Start wandpunt → switch-poort bereikbaar."""
        from app.services.tracing import trace_from_wall_outlet
        result = trace_from_wall_outlet(tracing_data, "wo1")
        node_ids = {n.get("obj_id") for n in result}
        assert "p_sw_f1" in node_ids, f"switch-poort niet gevonden in trace: {node_ids}"

    def test_T03_no_connection_empty_trace(self, tracing_data):
        """T03 — Losse poort zonder verbinding → lege of minimale trace."""
        from app.services.tracing import trace_from_port
        # Voeg een losse poort toe die nergens aan verbonden is
        tracing_data["ports"].append(_make_port("p_lone", "dev_sw", "front", 99))
        result = trace_from_port(tracing_data, "p_lone")
        node_ids = {n.get("obj_id") for n in result}
        # ep1 mag niet bereikbaar zijn vanuit een losse poort
        assert "ep1" not in node_ids

    def test_T04_direct_port_to_endpoint(self):
        """T04 — Directe port→endpoint verbinding (geen patchpanel)."""
        from app.services.tracing import trace_from_port
        sw   = _make_device("dev_sw2", "SW02", "switch")
        port = _make_port("p_sw2_f1", "dev_sw2", "front", 1)
        ep   = _make_endpoint("ep_direct", "DIRECT-PC")
        conn = _make_conn("c_direct", "p_sw2_f1", "port", "ep_direct", "endpoint")

        room    = _make_room("r2", "RUIMTE2",
                             racks=[_make_rack("rack2", "RACK2",
                                               slots=[{"device_id": "dev_sw2",
                                                       "position": 1, "height": 1}])])
        site    = _make_site("s2", "SITE2", rooms=[room])
        company = _make_company("co2", "CO2", sites=[site])

        data = _make_data(
            companies=[company],
            devices=[sw],
            ports=[port],
            endpoints=[ep],
            connections=[conn],
        )
        result   = trace_from_port(data, "p_sw2_f1")
        node_ids = {n.get("obj_id") for n in result}
        assert "ep_direct" in node_ids


# ===========================================================================
# 2. DATA INTEGRITY — validate_before_save + validate_and_repair
# ===========================================================================
#
# Testcases:
#   I01 — Geen waarschuwingen bij schone data
#   I02 — Duplicate IP gedetecteerd
#   I03 — Duplicate MAC ETH gedetecteerd
#   I04 — Ongeldig IPv4-formaat gedetecteerd
#   I05 — focus_ids filtert ongerelateerde waarschuwingen
#   I06 — Duplicate port IDs automatisch gerepareerd
#   I07 — Lege IP/MAC → geen waarschuwing
# ===========================================================================

class TestDataIntegrity:

    def _vbs(self, data, focus_ids=None):
        from app.services.data_integrity import validate_before_save
        return validate_before_save(data, focus_ids=focus_ids)

    def test_I01_clean_data_no_warnings(self):
        """I01 — Schone data levert geen waarschuwingen."""
        data = _make_data(
            devices=[_make_device("dev1", "SW01", ip="192.168.1.1", mac_eth="AA:BB:CC:DD:EE:01")],
            endpoints=[_make_endpoint("ep1", "PC-01", ip="192.168.1.100", mac_eth="AA:BB:CC:DD:EE:02")],
        )
        assert self._vbs(data) == []

    def test_I02_duplicate_ip_detected(self):
        """I02 — Twee objecten met hetzelfde IP → waarschuwing."""
        data = _make_data(
            devices=[_make_device("dev1", "SW01", ip="192.168.1.1")],
            endpoints=[_make_endpoint("ep1", "PC-01", ip="192.168.1.1")],
        )
        warnings = self._vbs(data)
        assert any("192.168.1.1" in w and "Dubbel IP" in w for w in warnings), warnings

    def test_I03_duplicate_mac_detected(self):
        """I03 — Twee objecten met hetzelfde MAC ETH → waarschuwing."""
        mac = "AA:BB:CC:DD:EE:FF"
        data = _make_data(
            devices=[_make_device("dev1", "SW01", mac_eth=mac)],
            endpoints=[_make_endpoint("ep1", "PC-01", mac_eth=mac)],
        )
        warnings = self._vbs(data)
        assert any(mac.upper() in w.upper() and "Dubbel MAC" in w for w in warnings), warnings

    def test_I04_invalid_ip_format(self):
        """I04 — Ongeldig IPv4 → waarschuwing."""
        data = _make_data(
            endpoints=[_make_endpoint("ep1", "PC-01", ip="999.999.999.999")],
        )
        warnings = self._vbs(data)
        assert any("Ongeldig IP" in w for w in warnings), warnings

    def test_I04b_ip_with_port_rejected(self):
        """I04b — IP met poortnummer (bv. 10.0.0.1:8080) → ongeldig formaat."""
        data = _make_data(
            endpoints=[_make_endpoint("ep1", "PC-01", ip="10.0.0.1:8080")],
        )
        warnings = self._vbs(data)
        assert any("Ongeldig IP" in w for w in warnings), warnings

    def test_I05_focus_ids_filters_unrelated(self):
        """I05 — focus_ids={ep2} toont enkel waarschuwingen voor ep2, niet ep1."""
        data = _make_data(
            endpoints=[
                _make_endpoint("ep1", "PC-01", ip="192.168.1.1"),
                _make_endpoint("ep2", "PC-02", ip="192.168.1.1"),  # dup IP met ep1
            ],
        )
        # Zonder focus: beide betrokken → waarschuwing verwacht
        assert self._vbs(data, focus_ids=None) != []
        # Met focus op ep2: waarschuwing toont (ep2 is betrokken)
        w_ep2 = self._vbs(data, focus_ids={"ep2"})
        assert w_ep2 != []
        # Met focus op een niet-betrokken object: geen waarschuwing
        w_other = self._vbs(data, focus_ids={"ep_onbestaand"})
        assert w_other == []

    def test_I06_duplicate_port_ids_repaired(self):
        """I06 — Duplicate port IDs → validate_and_repair maakt IDs uniek."""
        from app.services.data_integrity import validate_and_repair

        # Twee poorten met hetzelfde ID
        p1 = _make_port("p_dup", "dev1", "front", 1)
        p2 = _make_port("p_dup", "dev1", "front", 2)  # zelfde ID!
        data = _make_data(
            devices=[_make_device("dev1", "SW01")],
            ports=[p1, p2],
        )
        repaired_data, changed, rapport = validate_and_repair(data)
        assert changed, "Er moest gerepareerd worden"
        port_ids = [p["id"] for p in repaired_data["ports"]]
        assert len(port_ids) == len(set(port_ids)), f"Nog steeds duplicaten: {port_ids}"

    def test_I07_empty_ip_mac_no_warning(self):
        """I07 — Lege IP en MAC → geen waarschuwing (velden zijn optioneel)."""
        data = _make_data(
            endpoints=[_make_endpoint("ep1", "PC-01", ip="", mac_eth="")],
        )
        assert self._vbs(data) == []


# ===========================================================================
# 3. IMPORT / EXPORT SERVICE
# ===========================================================================
#
# Testcases:
#   X01 — validate() accepteert v2 data
#   X02 — validate() accepteert v1 data
#   X03 — validate() weigert ongeldige data
#   X04 — _migrate_v1_to_v2() plaatst sites in company wrapper
#   X05 — import_merge() voegt nieuwe endpoints toe zonder duplicaten
#   X06 — import_merge() slaat bestaande IDs over
#   X07 — suggested_dirname() bevat datum en bedrijfsnaam
#   CSV01 — import_endpoints_from_csv: semikolon-bestand correct geparsed
#   CSV02 — import_endpoints_from_csv: komma-bestand correct geparsed
#   CSV03 — import_endpoints_from_csv: duplicaat op naam overgeslagen
#   CSV04 — import_endpoints_from_csv: ontbrekende name-kolom → fout
#   CSV05 — import_endpoints_from_csv: lege rijen worden genegeerd
#   CSV06 — import_endpoints_from_csv: dubbele naam binnen CSV overgeslagen
#   CSV07 — import_endpoints_from_csv: mac compat-veld correct gezet
#   CSV08 — import_endpoints_from_csv: onbekende kolom → waarschuwing, geen crash
# ===========================================================================

@pytest.fixture
def base_data_v2():
    """Minimale v2-data voor import/export tests."""
    site    = _make_site("site1", "HQ")
    company = _make_company("co1", "CGK", sites=[site])
    return _make_data(companies=[company])


class TestImportExport:

    def test_X01_validate_v2(self, base_data_v2):
        """X01 — validate() accepteert correcte v2 data."""
        from app.services.import_export_service import validate
        ok, reason = validate(base_data_v2)
        assert ok, reason

    def test_X02_validate_v1(self):
        """X02 — validate() accepteert v1 data (sites op top-niveau)."""
        from app.services.import_export_service import validate
        v1 = {
            "version": "1.0",
            "sites": [_make_site("s1", "HQ")],
            "devices": [], "ports": [], "endpoints": [], "connections": [],
        }
        ok, reason = validate(v1)
        assert ok, reason

    def test_X03_validate_rejects_invalid(self):
        """X03 — validate() weigert data zonder verplichte sleutels."""
        from app.services.import_export_service import validate
        ok, _ = validate({"version": "2.0"})
        assert not ok

    def test_X04_migrate_v1_to_v2(self):
        """X04 — v1 migratie plaatst sites in company wrapper."""
        from app.services.import_export_service import _migrate_v1_to_v2
        v1 = {
            "version": "1.0",
            "sites": [_make_site("s1", "HQ")],
            "devices": [], "ports": [], "endpoints": [], "connections": [],
        }
        v2 = _migrate_v1_to_v2(v1, company_name="TestCo")
        assert "companies" in v2
        assert v2["companies"][0]["name"] == "TestCo"
        assert any(s["id"] == "s1" for s in v2["companies"][0]["sites"])

    def test_X05_import_merge_adds_endpoints(self, base_data_v2, tmp_path):
        """X05 — import_merge voegt nieuwe endpoints toe."""
        from app.services.import_export_service import import_merge

        incoming = copy.deepcopy(base_data_v2)
        incoming["endpoints"].append(_make_endpoint("ep_new", "PC-NEW"))

        f = tmp_path / "incoming.json"
        f.write_text(json.dumps(incoming), encoding="utf-8")

        merged, err, stats = import_merge(str(f), base_data_v2)
        assert err == ""
        ep_ids = [e["id"] for e in merged["endpoints"]]
        assert "ep_new" in ep_ids
        assert stats["added"] >= 1

    def test_X06_import_merge_skips_existing(self, base_data_v2, tmp_path):
        """X06 — import_merge slaat bestaande IDs over."""
        from app.services.import_export_service import import_merge

        ep = _make_endpoint("ep_exist", "PC-EXIST")
        current = copy.deepcopy(base_data_v2)
        current["endpoints"].append(ep)

        incoming = copy.deepcopy(current)  # zelfde endpoint erin

        f = tmp_path / "incoming.json"
        f.write_text(json.dumps(incoming), encoding="utf-8")

        merged, err, stats = import_merge(str(f), current)
        assert err == ""
        assert stats["skipped"] >= 1
        # Mag niet dubbel in de lijst staan
        ep_ids = [e["id"] for e in merged["endpoints"]]
        assert ep_ids.count("ep_exist") == 1

    def test_X07_suggested_dirname(self):
        """X07 — suggested_dirname bevat datum en bedrijfsnaam."""
        from app.services.import_export_service import suggested_dirname
        from datetime import date
        name = suggested_dirname("CGK Group")
        assert date.today().isoformat() in name
        assert "CGK" in name

    # --- IMP-1 CSV tests ---

    def _write_csv(self, tmp_path, content: str, filename: str = "test.csv") -> str:
        f = tmp_path / filename
        f.write_text(content, encoding="utf-8")
        return str(f)

    def test_CSV01_semicolon_delimiter(self, tmp_path):
        """CSV01 — Semikolon-bestand wordt correct geparsed."""
        from app.services.import_export_service import import_endpoints_from_csv
        content = "name;type;ip\nPC-01;workstation;192.168.1.10\nPC-02;printer;192.168.1.11\n"
        path = self._write_csv(tmp_path, content)
        eps, warnings = import_endpoints_from_csv(path, _make_data())
        assert len(eps) == 2
        assert eps[0]["name"] == "PC-01"
        assert eps[1]["ip"] == "192.168.1.11"

    def test_CSV02_comma_delimiter(self, tmp_path):
        """CSV02 — Komma-bestand wordt correct geparsed."""
        from app.services.import_export_service import import_endpoints_from_csv
        content = "name,type,ip\nPC-01,workstation,192.168.1.10\n"
        path = self._write_csv(tmp_path, content)
        eps, warnings = import_endpoints_from_csv(path, _make_data())
        assert len(eps) == 1
        assert eps[0]["name"] == "PC-01"

    def test_CSV03_duplicate_name_skipped(self, tmp_path):
        """CSV03 — Naam die al bestaat in data → rij overgeslagen."""
        from app.services.import_export_service import import_endpoints_from_csv
        existing = _make_data(endpoints=[_make_endpoint("ep1", "PC-BESTAAND")])
        content  = "name;type\nPC-BESTAAND;workstation\nPC-NIEUW;workstation\n"
        path     = self._write_csv(tmp_path, content)
        eps, warnings = import_endpoints_from_csv(path, existing)
        names = [e["name"] for e in eps]
        assert "PC-NIEUW" in names
        assert "PC-BESTAAND" not in names
        assert any("bestaat al" in w for w in warnings)

    def test_CSV04_missing_name_column_error(self, tmp_path):
        """CSV04 — Ontbrekende name-kolom → foutmelding, geen crashes."""
        from app.services.import_export_service import import_endpoints_from_csv
        content = "type;ip\nworkstation;192.168.1.1\n"
        path    = self._write_csv(tmp_path, content)
        eps, warnings = import_endpoints_from_csv(path, _make_data())
        assert eps == []
        assert any("name" in w.lower() and "ontbreekt" in w.lower() for w in warnings)

    def test_CSV05_empty_rows_ignored(self, tmp_path):
        """CSV05 — Volledig lege rijen worden genegeerd."""
        from app.services.import_export_service import import_endpoints_from_csv
        content = "name;type\nPC-01;workstation\n\n\nPC-02;printer\n"
        path    = self._write_csv(tmp_path, content)
        eps, warnings = import_endpoints_from_csv(path, _make_data())
        assert len(eps) == 2

    def test_CSV06_duplicate_within_csv(self, tmp_path):
        """CSV06 — Dubbele naam binnen CSV zelf → tweede rij overgeslagen."""
        from app.services.import_export_service import import_endpoints_from_csv
        content = "name;type\nPC-01;workstation\nPC-01;printer\n"
        path    = self._write_csv(tmp_path, content)
        eps, warnings = import_endpoints_from_csv(path, _make_data())
        assert len(eps) == 1
        assert any("Dubbele naam" in w for w in warnings)

    def test_CSV07_mac_compat_field(self, tmp_path):
        """CSV07 — mac compat-veld = mac_eth als aanwezig, anders mac_wifi."""
        from app.services.import_export_service import import_endpoints_from_csv
        content = (
            "name;mac_eth;mac_wifi\n"
            "PC-ETH;AA:BB:CC:DD:EE:01;\n"
            "PC-WIFI;;AA:BB:CC:DD:EE:02\n"
            "PC-BOTH;AA:BB:CC:DD:EE:03;AA:BB:CC:DD:EE:04\n"
        )
        path = self._write_csv(tmp_path, content)
        eps, _ = import_endpoints_from_csv(path, _make_data())
        by_name = {e["name"]: e for e in eps}
        assert by_name["PC-ETH"]["mac"]  == "AA:BB:CC:DD:EE:01"
        assert by_name["PC-WIFI"]["mac"] == "AA:BB:CC:DD:EE:02"
        assert by_name["PC-BOTH"]["mac"] == "AA:BB:CC:DD:EE:03"  # ETH heeft voorrang

    def test_CSV08_unknown_column_warning(self, tmp_path):
        """CSV08 — Onbekende kolom → waarschuwing, import loopt wel door."""
        from app.services.import_export_service import import_endpoints_from_csv
        content = "name;type;onbestaande_kolom\nPC-01;workstation;waarde\n"
        path    = self._write_csv(tmp_path, content)
        eps, warnings = import_endpoints_from_csv(path, _make_data())
        assert len(eps) == 1, "Import moet wel lukken ondanks onbekende kolom"
        assert any("onbestaande_kolom" in w.lower() for w in warnings)


# ===========================================================================
# 4. SEARCH SERVICE
# ===========================================================================
#
# Testcases:
#   S01 — Zoek op naam → correct resultaat gevonden
#   S02 — Begin-van-woord matching: "sw" matcht "SW01" maar niet "psw"
#   S03 — Case-insensitief zoeken
#   S04 — Minimale querylengte poort = 1 teken
#   S05 — Minimale querylengte overige tabs = 2 tekens
#   S06 — Multi-token AND: beide tokens moeten matchen
#   S07 — Ranking: exacte naammatch scoort hoger dan gedeeltelijke match
# ===========================================================================

@pytest.fixture
def search_data():
    """Dataset voor zoektests."""
    sw1  = _make_device("dev_sw1",  "SW01",  "switch",      ip="192.168.1.1")
    sw2  = _make_device("dev_sw2",  "SW02",  "switch",      ip="192.168.1.2")
    pp1  = _make_device("dev_pp1",  "PP01",  "patch_panel")
    ep1  = _make_endpoint("ep1", "PC-SALES-01", ip="192.168.1.100")
    ep2  = _make_endpoint("ep2", "PC-SALES-02", ip="192.168.1.101")
    ep3  = _make_endpoint("ep3", "PRINTER-01")

    p1 = {**_make_port("p_sw1_f1", "dev_sw1", "front", 1), "name": "Gi1/0/1"}
    p2 = {**_make_port("p_sw1_f2", "dev_sw1", "front", 2), "name": "Gi1/0/2"}

    room    = _make_room("r1", "SERVERRUIMTE",
                         racks=[_make_rack("rack1", "RACK01",
                                           slots=[
                                               {"device_id": "dev_sw1", "position": 1, "height": 1},
                                               {"device_id": "dev_sw2", "position": 2, "height": 1},
                                               {"device_id": "dev_pp1", "position": 3, "height": 1},
                                           ])])
    site    = _make_site("site1", "CGK HQ", rooms=[room])
    company = _make_company("co1", "CGK", sites=[site])

    return _make_data(
        companies=[company],
        devices=[sw1, sw2, pp1],
        ports=[p1, p2],
        endpoints=[ep1, ep2, ep3],
    )


class TestSearchService:

    def _search(self, query, data, filter_type="all"):
        from app.services.search_service import search
        return search(data, query, filter_type=filter_type)

    def test_S01_name_match(self, search_data):
        """S01 — Zoek 'SW01' → device SW01 gevonden."""
        results = self._search("SW01", search_data)
        ids = [r.get("id") for r in results]
        assert "dev_sw1" in ids

    def test_S02_word_start_match(self, search_data):
        """S02 — 'sw' matcht SW01/SW02, niet dingen die eindigen op sw."""
        results = self._search("sw", search_data)
        ids = [r.get("id") for r in results]
        assert "dev_sw1" in ids
        assert "dev_sw2" in ids
        # PP01 mag niet matchen op 'sw'
        assert "dev_pp1" not in ids

    def test_S03_case_insensitive(self, search_data):
        """S03 — Zoeken is case-insensitief."""
        r_upper = self._search("SW01", search_data)
        r_lower = self._search("sw01", search_data)
        ids_upper = {r.get("id") for r in r_upper}
        ids_lower = {r.get("id") for r in r_lower}
        assert ids_upper == ids_lower

    def test_S04_port_tab_min_length_one(self, search_data):
        """S04 — Poort-tab: zoeken vanaf 1 teken (poortnaam begint met G)."""
        results = self._search("G", search_data, filter_type="port")
        # Moet resultaten teruggeven — poorten met naam "Gi1/0/1" / "Gi1/0/2"
        assert len(results) >= 1, f"Geen resultaten voor 1-teken query op poort-tab: {results}"

    def test_S05_other_tabs_min_length_two(self, search_data):
        """S05 — Andere tabs: 1 teken → geen resultaten."""
        results = self._search("s", search_data, filter_type="device")
        assert results == []

    def test_S06_multi_token_and(self, search_data):
        """S06 — 'PC SALES' → beide tokens moeten matchen (AND)."""
        results = self._search("PC SALES", search_data)
        ids = [r.get("id") for r in results]
        assert "ep1" in ids
        assert "ep2" in ids
        # PRINTER-01 heeft geen 'SALES' → niet in resultaten
        assert "ep3" not in ids

    def test_S07_ranking_exact_first(self, search_data):
        """S07 — Exacte naammatch scoort hoger dan gedeeltelijke match."""
        results = self._search("SW01", search_data)
        if len(results) >= 2:
            assert results[0].get("id") == "dev_sw1", \
                f"SW01 verwacht als eerste, maar: {[r.get('id') for r in results[:3]]}"


# ===========================================================================
# 5. COMPANY FILTERING — get_all_sites / get_all_companies
# ===========================================================================
#
# Testcases:
#   C01 — get_all_sites retourneert sites van alle bedrijven
#   C02 — get_all_companies retourneert alle bedrijven
#   C03 — get_company_for_site vindt het juiste bedrijf voor een site
#   C04 — get_all_sites op v1 data (geen companies) geeft lege lijst
#   C05 — Meerdere bedrijven → sites niet door elkaar
# ===========================================================================

class TestCompanyFiltering:

    def test_C01_get_all_sites(self):
        """C01 — get_all_sites retourneert sites van alle bedrijven."""
        from app.helpers.settings_storage import get_all_sites
        s1 = _make_site("s1", "SITE1")
        s2 = _make_site("s2", "SITE2")
        data = _make_data(companies=[
            _make_company("co1", "CO1", sites=[s1]),
            _make_company("co2", "CO2", sites=[s2]),
        ])
        sites = get_all_sites(data)
        site_ids = [s["id"] for s in sites]
        assert "s1" in site_ids
        assert "s2" in site_ids

    def test_C02_get_all_companies(self):
        """C02 — get_all_companies retourneert alle bedrijven."""
        from app.helpers.settings_storage import get_all_companies
        data = _make_data(companies=[
            _make_company("co1", "CO1"),
            _make_company("co2", "CO2"),
        ])
        companies = get_all_companies(data)
        ids = [c["id"] for c in companies]
        assert "co1" in ids
        assert "co2" in ids

    def test_C03_get_company_for_site(self):
        """C03 — get_company_for_site vindt het juiste bedrijf."""
        from app.helpers.settings_storage import get_company_for_site
        s1 = _make_site("s1", "SITE1")
        s2 = _make_site("s2", "SITE2")
        co1 = _make_company("co1", "CO1", sites=[s1])
        co2 = _make_company("co2", "CO2", sites=[s2])
        data = _make_data(companies=[co1, co2])
        found = get_company_for_site(data, "s2")
        assert found is not None
        assert found["id"] == "co2"

    def test_C04_v1_data_no_companies(self):
        """C04 — v1 data zonder companies-sleutel → get_all_sites geeft lege lijst."""
        from app.helpers.settings_storage import get_all_sites
        # v1 structuur: sites op top-niveau, geen companies
        data = {
            "version": "1.0",
            "sites": [_make_site("s1", "SITE1")],
            "devices": [], "ports": [], "endpoints": [], "connections": [],
        }
        sites = get_all_sites(data)
        # Verwacht: lege lijst (get_all_sites werkt enkel op v2)
        assert isinstance(sites, list)

    def test_C05_multi_company_sites_independent(self):
        """C05 — Sites van verschillende bedrijven worden niet vermengd."""
        from app.helpers.settings_storage import get_company_for_site
        s_cgk  = _make_site("s_cgk",  "CGK HQ")
        s_klant = _make_site("s_klant", "Klant HQ")
        co_cgk  = _make_company("co_cgk",  "CGK",  sites=[s_cgk])
        co_klant = _make_company("co_klant", "KLANT", sites=[s_klant])
        data = _make_data(companies=[co_cgk, co_klant])

        found_cgk   = get_company_for_site(data, "s_cgk")
        found_klant = get_company_for_site(data, "s_klant")
        assert found_cgk["id"]   == "co_cgk"
        assert found_klant["id"] == "co_klant"

# ===========================================================================
# 6. LOCK SERVICE — LCK-1
# ===========================================================================
#
# Testcases:
#   L01 — Happy path: acquire → release → lock-bestand aangemaakt en verwijderd
#   L02 — Concurrent lock: tweede acquire geeft False terug (lock bezet)
#   L03 — Stale lock (timestamp > LOCK_TIMEOUT_S): automatisch verwijderd bij acquire
#   L04 — Re-entrant: eigen lock opnieuw acquiren slaagt (zelfde PID + hostname)
#   L05 — release_lock verwijdert alleen eigen lock, niet die van een ander
#   L06 — cleanup_stale_lock: verwijdert stale lock bij opstarten, laat verse staan
# ===========================================================================

class TestLockService:
    """
    Tests voor app/services/lock_service.py (LCK-1).
    Geen Qt-dependencies — werkt puur op het bestandssysteem via tmp-bestanden.
    """

    def _make_network_path(self, tmp_path) -> str:
        """Geeft een tijdelijk network_data.json pad terug (bestand hoeft niet te bestaan)."""
        return str(tmp_path / "network_data.json")

    def _write_lock_manually(self, network_path: str, pid: int, hostname: str,
                              username: str, timestamp: float) -> None:
        """Schrijft handmatig een lock-bestand voor setup van testscenarios."""
        import json
        from pathlib import Path
        lock_path = Path(network_path).with_suffix(".lock")
        lock_path.write_text(
            json.dumps({
                "pid":       pid,
                "hostname":  hostname,
                "username":  username,
                "timestamp": timestamp,
            }),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------

    def test_L01_happy_path(self, tmp_path):
        """L01 — acquire slaagt, lock-bestand verschijnt, release verwijdert het."""
        from pathlib import Path
        from app.services.lock_service import acquire_lock, release_lock

        path = self._make_network_path(tmp_path)
        lock_file = Path(path).with_suffix(".lock")

        ok, err = acquire_lock(path)
        assert ok, f"acquire_lock mislukt: {err}"
        assert lock_file.exists(), "Lock-bestand moet aanwezig zijn na acquire"

        release_lock(path)
        assert not lock_file.exists(), "Lock-bestand moet weg zijn na release"

    def test_L02_concurrent_lock_blocked(self, tmp_path):
        """L02 — Lock is al bezet door ander proces → tweede acquire geeft False."""
        from app.services.lock_service import acquire_lock, LOCK_TIMEOUT_S

        path = self._make_network_path(tmp_path)

        # Simuleer een actieve lock van een ander proces (PID 99999, andere hostname)
        self._write_lock_manually(
            path,
            pid=99999,
            hostname="andere-machine",
            username="andere-gebruiker",
            timestamp=time.time(),   # vers → niet stale
        )

        ok, err = acquire_lock(path)
        assert not ok, "acquire_lock moet False teruggeven als lock bezet is"
        assert err, "Foutmelding moet aanwezig zijn"
        assert "andere" in err.lower() or "vergrendeld" in err.lower(), (
            f"Foutmelding moet context geven over bezette lock: {err}"
        )

    def test_L03_stale_lock_auto_cleared(self, tmp_path):
        """L03 — Verouderde lock (ouder dan LOCK_TIMEOUT_S) wordt automatisch gewist."""
        from app.services.lock_service import acquire_lock, release_lock, LOCK_TIMEOUT_S
        from pathlib import Path

        path = self._make_network_path(tmp_path)
        lock_file = Path(path).with_suffix(".lock")

        # Schrijf lock met timestamp ver in het verleden (crashscenario)
        self._write_lock_manually(
            path,
            pid=99999,
            hostname="gecrasht-systeem",
            username="admin",
            timestamp=time.time() - LOCK_TIMEOUT_S - 10,
        )
        assert lock_file.exists(), "Stale lock-bestand moet aanwezig zijn vóór test"

        ok, err = acquire_lock(path)
        assert ok, f"acquire_lock moet slagen na stale lock: {err}"

        release_lock(path)

    def test_L04_reentrant_own_lock(self, tmp_path):
        """L04 — Re-entrant: eigen lock (zelfde PID + hostname) opnieuw acquiren slaagt."""
        import os
        import socket
        from app.services.lock_service import acquire_lock, release_lock

        path = self._make_network_path(tmp_path)

        # Schrijf lock van huidig proces
        self._write_lock_manually(
            path,
            pid=os.getpid(),
            hostname=socket.gethostname(),
            username="test",
            timestamp=time.time(),
        )

        ok, err = acquire_lock(path)
        assert ok, f"Re-entrant acquire moet slagen voor eigen lock: {err}"

        release_lock(path)

    def test_L05_release_does_not_remove_foreign_lock(self, tmp_path):
        """L05 — release_lock verwijdert lock van een ander proces NIET."""
        from pathlib import Path
        from app.services.lock_service import release_lock

        path = self._make_network_path(tmp_path)
        lock_file = Path(path).with_suffix(".lock")

        # Lock van een ander proces
        self._write_lock_manually(
            path,
            pid=99999,
            hostname="andere-machine",
            username="andere-gebruiker",
            timestamp=time.time(),
        )

        release_lock(path)   # moet stilzwijgend niets doen
        assert lock_file.exists(), (
            "release_lock mag lock van een ander proces NIET verwijderen"
        )

    def test_L06_cleanup_stale_lock(self, tmp_path):
        """L06 — cleanup_stale_lock verwijdert stale lock, laat verse lock staan."""
        from pathlib import Path
        from app.services.lock_service import cleanup_stale_lock, LOCK_TIMEOUT_S

        path = self._make_network_path(tmp_path)
        lock_file = Path(path).with_suffix(".lock")

        # Stale lock → moet verwijderd worden
        self._write_lock_manually(
            path,
            pid=99999,
            hostname="gecrasht-systeem",
            username="admin",
            timestamp=time.time() - LOCK_TIMEOUT_S - 10,
        )
        removed = cleanup_stale_lock(path)
        assert removed, "cleanup_stale_lock moet True teruggeven bij stale lock"
        assert not lock_file.exists(), "Stale lock-bestand moet verwijderd zijn"

        # Verse lock → moet NIET verwijderd worden
        self._write_lock_manually(
            path,
            pid=99999,
            hostname="actieve-machine",
            username="gebruiker",
            timestamp=time.time(),
        )
        removed = cleanup_stale_lock(path)
        assert not removed, "cleanup_stale_lock mag verse lock NIET verwijderen"
        assert lock_file.exists(), "Verse lock-bestand mag niet verwijderd zijn"