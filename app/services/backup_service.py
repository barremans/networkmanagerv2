# =============================================================================
# Networkmap_Creator
# File:    app/services/backup_service.py
# Role:    Backup beheer — GEEN Qt imports
# Version: 1.9.0
# Author:  Barremans
# Changes: 1.9.0 — Bedrijfslogica:
#                  create_backup_company(): backup van 1 bedrijf
#                  Gefilterde network_data + eigen floorplans submap
#                  History-bestand krijgt bedrijfsnaam in bestandsnaam
#          1.8.0 — Fix backup UNC: OSError bij copy2 ook via robocopy fallback
#          1.0.0 — Initiële versie
#          1.1.0 — F3: has_changes_since_last_backup()
#          1.2.0 — F4: UNC-pad fix — mkdir() niet aanroepen op UNC root
#          1.3.0 — B9: retry-logica + _copy_with_retry()
#          1.4.0 — B-NEW-1/2: floorplans.json + SVG map meenemen in backup
#          1.4.1 — Bugfix: chmod() → unlink() voor overschrijven op UNC
#          1.4.2 — Bugfix: _force_remove_readonly onerror handler voor rmtree
#          1.4.3 — Bugfix: unlink() stilzwijgend bij OSError
#          1.4.4 — B-BACKUP: diagnostiek gebruikerscontext (_get_current_user)
#          1.4.5 — B-BACKUP: shell fallback via robocopy bij PermissionError
#          1.4.6 — Bugfix: _ensure_dir controleert existence vóór mkdir()
#                  op UNC-submappen gooit mkdir() FileNotFoundError als map al bestaat
#          1.5.0 — R-1: restore_backup() uitgebreid — per-onderdeel herstel
#                  (network_data, settings, floorplans.json, SVG-map)
#          1.6.0 — vlan_config.json meenemen in backup én restore
#          1.7.0 — Fix restore UNC WinError 5: unlink() OSError → robocopy fallback
#          1.8.0 — Fix backup UNC: OSError bij copy2 ook via robocopy fallback
# =============================================================================

import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path


# ------------------------------------------------------------------
# Constanten
# ------------------------------------------------------------------

_BACKUP_FILENAME = "network_data.json"
_HISTORY_DIR     = "history"
_TIMESTAMP_FMT   = "%Y%m%d_%H%M%S"
_RETRY_COUNT     = 3      # B9 — aantal pogingen bij tijdelijke fout
_RETRY_DELAY     = 1.0    # B9 — seconden wachten tussen pogingen


# ------------------------------------------------------------------
# Intern — retry helper
# ------------------------------------------------------------------

def _get_current_user() -> str:
    """Geeft de huidige Windows gebruikerscontext terug voor diagnostiek."""
    try:
        import ctypes
        GetUserNameEx = ctypes.windll.secur32.GetUserNameExW
        NameDisplay = 3
        size = ctypes.pointer(ctypes.c_ulong(0))
        GetUserNameEx(NameDisplay, None, size)
        nameBuffer = ctypes.create_unicode_buffer(size.contents.value)
        GetUserNameEx(NameDisplay, nameBuffer, size)
        return nameBuffer.value
    except Exception:
        try:
            return os.environ.get("USERNAME", "onbekend")
        except Exception:
            return "onbekend"


def _copy_via_shell(src: str, dst: Path) -> tuple[bool, str]:
    """
    B-BACKUP — Kopieer bestand via Windows shell (subprocess + robocopy).
    Draait altijd in de context van de ingelogde gebruiker, ook als de app
    gestart werd als pcadmin via Intune.
    Geeft (True, "") bij succes, (False, foutmelding) bij fout.
    """
    import subprocess
    try:
        src_path = Path(src)
        result = subprocess.run(
            ["robocopy", str(src_path.parent), str(dst.parent), src_path.name,
             "/NJH", "/NJS", "/NFL", "/NDL", "/NC", "/NS"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Robocopy exit codes: 0=geen wijziging, 1=OK gekopieerd, >=8=fout
        if result.returncode < 8:
            return True, ""
        return False, f"Robocopy fout (code {result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
    except subprocess.TimeoutExpired:
        return False, "Kopiëren via shell: timeout na 30s"
    except Exception as e:
        return False, f"Shell kopiëren mislukt: {e}"


def _copy_dir_via_shell(src_dir: Path, dst_dir: Path) -> tuple[bool, str]:
    """
    B-BACKUP — Kopieer map recursief via robocopy in shell context.
    """
    import subprocess
    try:
        result = subprocess.run(
            ["robocopy", str(src_dir), str(dst_dir),
             "/E", "/NJH", "/NJS", "/NFL", "/NDL", "/NC", "/NS"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode < 8:
            return True, ""
        return False, f"Robocopy map fout (code {result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
    except subprocess.TimeoutExpired:
        return False, "Map kopiëren via shell: timeout na 60s"
    except Exception as e:
        return False, f"Shell map kopiëren mislukt: {e}"


def _copy_with_retry(src: str, dst: Path) -> tuple[bool, str]:
    """
    B9 — Kopieer bestand met retry bij tijdelijke lock of netwerkverlies.
    Probeert _RETRY_COUNT keer met _RETRY_DELAY seconden ertussen.
    Geeft (True, "") bij succes, (False, foutmelding) bij definitieve fout.
    """
    last_err = ""
    for attempt in range(1, _RETRY_COUNT + 1):
        try:
            # Verwijder doelbestand eerst als het al bestaat (werkt ook op Windows UNC-shares)
            if dst.exists():
                try:
                    dst.unlink()
                except OSError as unlink_err:
                    # 1.7.0 — WinError 5 (Toegang geweigerd) op UNC → robocopy fallback
                    ok, err = _copy_via_shell(src, dst)
                    if ok:
                        return True, ""
                    last_err = f"Kan bestaand bestand niet verwijderen: {dst} — {unlink_err} (shell fallback ook mislukt: {err})"
                    if attempt < _RETRY_COUNT:
                        time.sleep(_RETRY_DELAY)
                    continue
            shutil.copy2(src, dst)
            return True, ""
        except (PermissionError, OSError) as e:
            # 1.8.0 — OSError vangt ook WinError 5 op die niet als PermissionError aankomt
            # Altijd robocopy fallback proberen bij schrijfrechtenprobleem op UNC
            ok, shell_err = _copy_via_shell(src, dst)
            if ok:
                return True, ""
            last_err = (
                f"Geen schrijfrechten (gebruiker: {_get_current_user()}), "
                f"shell fallback ook mislukt: {shell_err} (originele fout: {e})"
            )
        except FileNotFoundError:
            last_err = f"Pad niet gevonden: {dst}"
        if attempt < _RETRY_COUNT:
            time.sleep(_RETRY_DELAY)
    return False, last_err


def _force_remove_readonly(func, path, _):
    """onerror handler voor shutil.rmtree — wist read-only attribuut en probeert opnieuw."""
    import stat
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def _copy_dir_with_retry(src_dir: Path, dst_dir: Path) -> tuple[bool, str]:
    """
    B-NEW-2 — Kopieer een volledige map recursief met retry bij tijdelijke fout.
    dst_dir wordt volledig vervangen (verwijderd + opnieuw aangemaakt).
    Geeft (True, "") bij succes, (False, foutmelding) bij definitieve fout.
    """
    last_err = ""
    for attempt in range(1, _RETRY_COUNT + 1):
        try:
            if dst_dir.exists():
                shutil.rmtree(dst_dir, onerror=_force_remove_readonly)
            shutil.copytree(src_dir, dst_dir)
            return True, ""
        except PermissionError:
            # B-BACKUP — fallback: probeer via shell (ingelogde gebruikerscontext)
            ok, err = _copy_dir_via_shell(src_dir, dst_dir)
            if ok:
                return True, ""
            last_err = f"Geen schrijfrechten op map: {dst_dir}, shell fallback ook mislukt: {err}"
        except FileNotFoundError:
            last_err = f"Pad niet gevonden: {src_dir}"
        except OSError as e:
            last_err = str(e)
        if attempt < _RETRY_COUNT:
            time.sleep(_RETRY_DELAY)
    return False, last_err


# ------------------------------------------------------------------
# Publieke API
# ------------------------------------------------------------------

def has_changes_since_last_backup(source_path: str, config: dict) -> bool:
    """
    Geeft True terug als het bronbestand nieuwer is dan de meest recente backup.
    Geeft ook True terug als er nog geen backups bestaan (eerste keer).

    Parameters:
        source_path — volledig pad naar de lokale network_data.json
        config      — backup sectie uit settings.json

    Gebruik dit om onnodige backups te vermijden:
        if has_changes_since_last_backup(source, config):
            create_backup(source, config)
    """
    if not os.path.exists(source_path):
        return False

    network_path = config.get("network_path", "").strip()
    if not network_path:
        return True   # geen pad → kan niet vergelijken → neem aan dat backup nodig is

    history_dir = Path(network_path) / _HISTORY_DIR
    if not history_dir.exists():
        return True   # nog geen history → eerste backup

    backups = sorted(history_dir.glob("network_data_*.json"))
    if not backups:
        return True   # map bestaat maar is leeg

    latest_backup_mtime = backups[-1].stat().st_mtime
    source_mtime        = os.path.getmtime(source_path)

    # Meer dan 2 seconden nieuwer = er zijn wijzigingen (clock skew tolerantie)
    return (source_mtime - latest_backup_mtime) > 2


def _ensure_dir(path: Path) -> tuple[bool, str]:
    r"""
    F4 — Maak een map aan, maar sla UNC-roots over (\\server\share).
    UNC-roots bestaan al of niet — mkdir() daarop crasht altijd.
    Geeft (True, "") bij succes of als map al bestaat.
    Geeft (False, foutmelding) bij fout.
    """
    parts = path.parts  # bv. ('\\\\', 'server', 'share') of ('\\\\', 'server', 'share', 'submap')
    is_unc_root = (
        len(parts) <= 3
        and str(path).startswith("\\\\")
    )
    if is_unc_root:
        if path.exists():
            return True, ""
        return False, f"UNC-pad niet bereikbaar: {path}"

    # Bestaat de map al → geen mkdir nodig (voorkomt FileNotFoundError op UNC-submappen)
    try:
        if path.exists():
            return True, ""
    except OSError:
        pass

    try:
        path.mkdir(parents=True, exist_ok=True)
        return True, ""
    except PermissionError:
        return False, f"Geen schrijfrechten op: {path}"
    except FileNotFoundError:
        return False, f"Pad niet gevonden: {path}"
    except Exception as e:
        return False, str(e)


def create_backup(
    source_path: str,
    config: dict,
    settings_path: str | None = None,
    floorplans_path: str | None = None,
    floorplans_dir: str | None = None,
    vlan_path: str | None = None,
) -> tuple[bool, str]:
    """
    Maakt een backup van network_data.json naar de geconfigureerde netwerkmap.

    Parameters:
        source_path     — volledig pad naar de lokale network_data.json
        config          — backup sectie uit settings.json
        settings_path   — optioneel: pad naar settings.json
        floorplans_path — optioneel: pad naar floorplans.json
        floorplans_dir  — optioneel: pad naar SVG bestanden map
        vlan_path       — optioneel: pad naar vlan_config.json

    Returns:
        (True,  "")           bij succes
        (False, foutmelding)  bij fout
    """
    if not config.get("enabled", False):
        return True, ""   # backup uitgeschakeld — geen fout

    network_path = config.get("network_path", "").strip()
    if not network_path:
        return False, "Geen backup-pad geconfigureerd. Stel dit in via Instellingen."

    try:
        dest_dir = Path(network_path)
        ok, err = _ensure_dir(dest_dir)
        if not ok:
            return False, err

        # Hoofdkopie: network_data.json in de netwerkmap — met retry
        dest_main = dest_dir / _BACKUP_FILENAME
        ok, err = _copy_with_retry(source_path, dest_main)
        if not ok:
            return False, err

        # B10 — settings.json meekopieren indien opgegeven
        if settings_path and Path(settings_path).is_file():
            dest_settings = dest_dir / "settings.json"
            ok, err = _copy_with_retry(settings_path, dest_settings)
            if not ok:
                return False, err

        # B-NEW-1 — floorplans.json meekopieren indien opgegeven
        if floorplans_path:
            fp = Path(floorplans_path)
            if fp.is_file():
                dest_fp = dest_dir / "floorplans.json"
                ok, err = _copy_with_retry(floorplans_path, dest_fp)
                if not ok:
                    return False, f"floorplans.json backup mislukt: {err}"
            # Niet aanwezig → overslaan (geen fout, bestand bestaat mogelijk nog niet)

        # B-NEW-2 — SVG bestanden map meekopieren indien opgegeven
        if floorplans_dir:
            fd = Path(floorplans_dir)
            if fd.is_dir():
                dest_fp_dir = dest_dir / "floorplans"
                ok, err = _copy_dir_with_retry(fd, dest_fp_dir)
                if not ok:
                    return False, f"floorplans map backup mislukt: {err}"
            # Niet aanwezig → overslaan

        # 1.6.0 — vlan_config.json meekopieren indien opgegeven
        if vlan_path:
            vp = Path(vlan_path)
            if vp.is_file():
                dest_vlan = dest_dir / "vlan_config.json"
                ok, err = _copy_with_retry(vlan_path, dest_vlan)
                if not ok:
                    return False, f"vlan_config.json backup mislukt: {err}"
            # Niet aanwezig → overslaan

        # History backup met timestamp
        if config.get("keep_history", True):
            history_dir = dest_dir / _HISTORY_DIR
            ok_h, err_h = _ensure_dir(history_dir)
            if not ok_h:
                return False, err_h

            ts      = datetime.now().strftime(_TIMESTAMP_FMT)
            dest_ts = history_dir / f"network_data_{ts}.json"
            ok, err = _copy_with_retry(source_path, dest_ts)   # B9 — ook hier retry
            if not ok:
                return False, err

            # Oudste backups verwijderen als max bereikt is
            _trim_history(history_dir, config.get("max_backups", 10))

        return True, ""

    except Exception as e:
        return False, str(e)


def create_backup_company(
    company_id: str,
    company_name: str,
    config: dict,
    network_data: dict,
    floorplans_path: str | None = None,
    floorplans_dir: str | None = None,
    vlan_path: str | None = None,
) -> tuple[bool, str]:
    """
    1.9.0 — Maakt een backup van data van één bedrijf.

    Parameters:
        company_id      — id van het te backuppen bedrijf
        company_name    — naam (voor submap + bestandsnaam)
        config          — backup sectie uit settings.json
        network_data    — volledige geladen network_data dict (in-memory)
        floorplans_path — pad naar floorplans.json
        floorplans_dir  — pad naar SVG bestanden map
        vlan_path       — pad naar vlan_config.json

    Structuur in backup map:
        <network_path>/<company_slug>/
            network_data.json   (gefilterd op bedrijf)
            floorplans.json     (gefilterd op sites van bedrijf)
            floorplans/         (alleen SVG van dit bedrijf)
            vlan_config.json    (volledig)
            history/
                network_data_<company_slug>_<ts>.json
    """
    import json, uuid, tempfile
    from app.helpers.settings_storage import get_all_companies

    if not config.get("enabled", False):
        return True, ""

    network_path = config.get("network_path", "").strip()
    if not network_path:
        return False, "Geen backup-pad geconfigureerd."

    # Bedrijfsslug voor submapnaam
    slug = "".join(c if c.isalnum() else "_" for c in company_name).strip("_").lower()

    try:
        dest_dir = Path(network_path) / slug
        ok, err = _ensure_dir(dest_dir)
        if not ok:
            return False, err

        # Zoek bedrijf in data
        company = next(
            (c for c in network_data.get("companies", []) if c.get("id") == company_id),
            None
        )
        if not company:
            return False, f"Bedrijf niet gevonden: {company_id}"

        # Verzamel site-IDs van dit bedrijf
        site_ids = {s["id"] for s in company.get("sites", [])}

        # Verzamel device-IDs via slots in racks
        device_ids = {
            sl.get("device_id")
            for s in company.get("sites", [])
            for r in s.get("rooms", [])
            for ra in r.get("racks", [])
            for sl in ra.get("slots", [])
            if sl.get("device_id")
        }
        outlet_ids = {
            wo["id"]
            for s in company.get("sites", [])
            for r in s.get("rooms", [])
            for wo in r.get("wall_outlets", [])
        }

        filtered_devices = [d for d in network_data.get("devices", [])
                            if d.get("id") in device_ids]
        filtered_dev_ids = {d["id"] for d in filtered_devices}
        filtered_ports   = [p for p in network_data.get("ports", [])
                            if p.get("device_id") in filtered_dev_ids]
        filtered_port_ids = {p["id"] for p in filtered_ports}

        ep_ids = {
            wo.get("endpoint_id")
            for s in company.get("sites", [])
            for r in s.get("rooms", [])
            for wo in r.get("wall_outlets", [])
            if wo.get("endpoint_id")
        }
        filtered_eps = [e for e in network_data.get("endpoints", [])
                        if e.get("id") in ep_ids]

        all_ids = (filtered_dev_ids | filtered_port_ids |
                   {e["id"] for e in filtered_eps} | outlet_ids)
        filtered_conns = [
            c for c in network_data.get("connections", [])
            if c.get("from_id") in all_ids and c.get("to_id") in all_ids
        ]

        filtered_nd = {
            "version":     "2.0",
            "companies":   [company],
            "devices":     filtered_devices,
            "ports":       filtered_ports,
            "endpoints":   filtered_eps,
            "connections": filtered_conns,
        }

        # Schrijf gefilterde network_data naar tijdelijk bestand
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(filtered_nd, tmp, indent=2, ensure_ascii=False)
        tmp.close()
        tmp_path = tmp.name

        try:
            dest_main = dest_dir / _BACKUP_FILENAME
            ok, err = _copy_with_retry(tmp_path, dest_main)
            if not ok:
                return False, err

            # Gefilterde floorplans.json
            if floorplans_path and Path(floorplans_path).is_file():
                import json as _json
                with open(floorplans_path, encoding="utf-8") as f:
                    fp_data = _json.load(f)
                filtered_fps = [
                    fp for fp in fp_data.get("floorplans", [])
                    if fp.get("site_id") in site_ids
                ]
                fp_tmp = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False, encoding="utf-8"
                )
                _json.dump({"floorplans": filtered_fps}, fp_tmp,
                           indent=2, ensure_ascii=False)
                fp_tmp.close()
                try:
                    ok, err = _copy_with_retry(fp_tmp.name, dest_dir / "floorplans.json")
                    if not ok:
                        return False, f"floorplans.json backup mislukt: {err}"
                finally:
                    Path(fp_tmp.name).unlink(missing_ok=True)

                # Alleen SVG's van dit bedrijf
                if floorplans_dir and Path(floorplans_dir).is_dir():
                    dest_svg = dest_dir / "floorplans"
                    ok, err = _ensure_dir(dest_svg)
                    if ok:
                        for fp in filtered_fps:
                            svg = fp.get("svg_file", "")
                            if svg:
                                src_svg = Path(floorplans_dir) / svg
                                if src_svg.exists():
                                    ok2, err2 = _copy_with_retry(
                                        str(src_svg), dest_svg / svg
                                    )

            # vlan_config.json (volledig)
            if vlan_path and Path(vlan_path).is_file():
                ok, err = _copy_with_retry(vlan_path, dest_dir / "vlan_config.json")
                if not ok:
                    return False, f"vlan_config.json backup mislukt: {err}"

            # History
            if config.get("keep_history", True):
                history_dir = dest_dir / _HISTORY_DIR
                ok_h, err_h = _ensure_dir(history_dir)
                if ok_h:
                    ts      = datetime.now().strftime(_TIMESTAMP_FMT)
                    dest_ts = history_dir / f"network_data_{slug}_{ts}.json"
                    _copy_with_retry(tmp_path, dest_ts)
                    _trim_history(history_dir, config.get("max_backups", 10))

        finally:
            Path(tmp_path).unlink(missing_ok=True)

        return True, ""

    except Exception as e:
        return False, str(e)


def list_backups(config: dict) -> list[dict]:
    """
    Geeft een lijst van beschikbare history-backups terug.

    Returns lijst van dicts:
        { "filename": str, "timestamp": str, "path": str }
    Gesorteerd van nieuwste naar oudste.
    """
    network_path = config.get("network_path", "").strip()
    if not network_path:
        return []

    history_dir = Path(network_path) / _HISTORY_DIR
    if not history_dir.exists():
        return []

    backups = []
    for f in sorted(history_dir.glob("network_data_*.json"), reverse=True):
        stem = f.stem  # bv. "network_data_20260222_143500"
        ts_part = stem.replace("network_data_", "")
        try:
            dt = datetime.strptime(ts_part, _TIMESTAMP_FMT)
            ts_label = dt.strftime("%d/%m/%Y %H:%M:%S")
        except ValueError:
            ts_label = ts_part
        backups.append({
            "filename":  f.name,
            "timestamp": ts_label,
            "path":      str(f),
        })
    return backups


def restore_backup(
    backup_entry: dict,
    targets: list[str],
    network_data_dest: str,
    settings_dest: str | None = None,
    floorplans_dest: str | None = None,
    floorplans_dir_dest: str | None = None,
    vlan_dest: str | None = None,
) -> tuple[bool, str]:
    """
    R-1 — Herstelt een backup naar de lokale bestanden.

    targets kan bevatten:
        "network_data", "settings", "floorplans_json",
        "floorplans_dir", "vlan"
    """
    if not backup_entry or not targets:
        return False, "Geen backup of doelbestanden opgegeven."

    history_file = Path(backup_entry["path"])
    if not history_file.is_file():
        return False, f"Backup-bestand niet gevonden:\n{history_file}"

    # De backup-map is de bovenliggende map van history/
    # history_file = <backup_root>/history/network_data_<ts>.json
    backup_root = history_file.parent.parent

    errors = []

    if "network_data" in targets:
        ok, err = _copy_with_retry(str(history_file), Path(network_data_dest))
        if not ok:
            errors.append(f"network_data.json: {err}")

    if "settings" in targets and settings_dest:
        src = backup_root / "settings.json"
        if src.is_file():
            ok, err = _copy_with_retry(str(src), Path(settings_dest))
            if not ok:
                errors.append(f"settings.json: {err}")
        else:
            errors.append("settings.json niet aanwezig in backup.")

    if "floorplans_json" in targets and floorplans_dest:
        src = backup_root / "floorplans.json"
        if src.is_file():
            ok, err = _copy_with_retry(str(src), Path(floorplans_dest))
            if not ok:
                errors.append(f"floorplans.json: {err}")
        else:
            errors.append("floorplans.json niet aanwezig in backup.")

    if "floorplans_dir" in targets and floorplans_dir_dest:
        src = backup_root / "floorplans"
        if src.is_dir():
            ok, err = _copy_dir_with_retry(src, Path(floorplans_dir_dest))
            if not ok:
                errors.append(f"floorplans/ map: {err}")
        else:
            errors.append("floorplans/ map niet aanwezig in backup.")

    if "vlan" in targets and vlan_dest:
        src = backup_root / "vlan_config.json"
        if src.is_file():
            ok, err = _copy_with_retry(str(src), Path(vlan_dest))
            if not ok:
                errors.append(f"vlan_config.json: {err}")
        else:
            errors.append("vlan_config.json niet aanwezig in backup.")

    if errors:
        return False, "\n".join(errors)
    return True, ""


def test_path(network_path: str) -> tuple[bool, str]:
    """
    Test of een netwerkpad bereikbaar en beschrijfbaar is.
    F4 — UNC-paden worden correct afgehandeld: geen mkdir op UNC-root.
    B9 — Schrijftest met retry bij tijdelijke lock.
    Returns (True, "") als OK, (False, reden) als niet.
    """
    if not network_path or not network_path.strip():
        return False, "Geen pad opgegeven."
    try:
        p = Path(network_path.strip())

        ok, err = _ensure_dir(p)
        if not ok:
            return False, err

        # B9 — Schrijftest met retry
        test_file = p / ".write_test"
        last_err  = ""
        for attempt in range(1, _RETRY_COUNT + 1):
            try:
                test_file.write_text("test")
                test_file.unlink()
                user = _get_current_user()
                return True, user   # gebruikerscontext meegeven voor diagnostiek
            except PermissionError:
                last_err = f"Geen schrijfrechten op: {network_path}"
            except Exception as e:
                last_err = str(e)
            if attempt < _RETRY_COUNT:
                time.sleep(_RETRY_DELAY)
        return False, last_err

    except PermissionError:
        return False, f"Geen schrijfrechten op: {network_path}"
    except FileNotFoundError:
        return False, f"Pad niet gevonden: {network_path}"
    except Exception as e:
        return False, str(e)


# ------------------------------------------------------------------
# Intern
# ------------------------------------------------------------------

def _trim_history(history_dir: Path, max_backups: int):
    """Verwijdert oudste backups als het maximum overschreden wordt."""
    files = sorted(history_dir.glob("network_data_*.json"))
    while len(files) > max_backups:
        files[0].unlink()
        files = files[1:]