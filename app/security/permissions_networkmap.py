# =============================================================================
# Networkmap_Creator
# File:    app/security/permissions_networkmap.py
# Role:    Azure AD authenticatie + groepscheck
# Version: 1.2.0
# Author:  Barremans
# Changes: 1.2.0 — S6b: twee AD-groepen: admin (lezen+schrijven) en readonly.
#                  get_access_level() → "admin" | "readonly" | "none"
#                  has_access() blijft beschikbaar als alias (backward compat).
#          1.1.0 — S6: hardcoded constanten vervangen door settings
#                  get_ad_config() leest bij elke aanroep de actuele settings.
#                  _get_msal_app() maakt nieuwe instantie als tenant/client
#                  gewijzigd zijn t.o.v. de gecachte instantie.
#                  has_access() en connect_to_azure_ad() gebruiken config
#                  dynamisch — geen herstart nodig na settings-wijziging.
#                  is_ad_enabled() helper toegevoegd.
#          1.0.0 — Initiële versie: Azure AD login via MSAL, groepscheck CGK-APP-L6
#
# BELANGRIJK:
# - Maak een App Registration aan in Azure Portal voor elke tenant
# - Geef de app de API permissions: User.Read + Group.Read.All
# - Configureer Tenant ID, Client ID en groepsnaam via Settings → Azure AD
# - Geen Qt imports — pure service
# =============================================================================

from __future__ import annotations
import msal
import requests

from app.helpers.settings_storage import get_azure_ad_config

GRAPH_ME_ENDPOINT     = "https://graph.microsoft.com/v1.0/me"
GRAPH_GROUPS_ENDPOINT = "https://graph.microsoft.com/v1.0/me/memberOf"
SCOPES                = ["User.Read", "Group.Read.All"]

# ---------------------------------------------------------------------------
# Interne state
# ---------------------------------------------------------------------------

_msal_app:           msal.PublicClientApplication | None = None
_msal_tenant_id:     str = ""
_msal_client_id:     str = ""
_cached_user:        dict | None = None
_cached_groups:      list[str]   = []


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def get_ad_config() -> dict:
    """Geeft de actuele Azure AD-configuratie uit settings."""
    return get_azure_ad_config()


def is_ad_enabled() -> bool:
    """Geeft True als Azure AD-authenticatie ingeschakeld is in settings."""
    return get_ad_config().get("enabled", True)


# ---------------------------------------------------------------------------
# MSAL app (herinitialiseren bij gewijzigde tenant of client)
# ---------------------------------------------------------------------------

def _get_msal_app() -> msal.PublicClientApplication:
    global _msal_app, _msal_tenant_id, _msal_client_id

    cfg       = get_ad_config()
    tenant_id = cfg.get("tenant_id", "")
    client_id = cfg.get("client_id", "")

    if (
        _msal_app is None
        or tenant_id != _msal_tenant_id
        or client_id != _msal_client_id
    ):
        authority    = f"https://login.microsoftonline.com/{tenant_id}"
        _msal_app    = msal.PublicClientApplication(
            client_id=client_id,
            authority=authority,
        )
        _msal_tenant_id = tenant_id
        _msal_client_id = client_id

    return _msal_app


def _get_token() -> str:
    app      = _get_msal_app()
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, accounts[0])
        if result and "access_token" in result:
            return result["access_token"]
    result = app.acquire_token_interactive(scopes=SCOPES, prompt="select_account")
    if "access_token" not in result:
        raise RuntimeError("Kon geen access token ophalen via Azure AD.")
    return result["access_token"]


# ---------------------------------------------------------------------------
# Publieke API
# ---------------------------------------------------------------------------

def connect_to_azure_ad() -> bool:
    """
    Meld aan bij Azure AD en haal gebruiker + groepen op.
    Geeft True bij succes, False bij fout of ontbrekende configuratie.
    """
    global _cached_user, _cached_groups

    cfg = get_ad_config()
    if not cfg.get("tenant_id") or not cfg.get("client_id"):
        print("[AD] Geen tenant_id of client_id geconfigureerd in Settings.")
        return False

    try:
        token   = _get_token()
        headers = {"Authorization": f"Bearer {token}"}

        resp = requests.get(GRAPH_ME_ENDPOINT, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"[AD] Gebruiker ophalen mislukt: {resp.status_code}")
            return False

        _cached_user = resp.json()
        print(f"[AD] Ingelogd als: {_cached_user.get('displayName')} "
              f"({_cached_user.get('userPrincipalName')})")

        groups: list[str] = []
        url = GRAPH_GROUPS_ENDPOINT
        while url:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                break
            data = r.json()
            for g in data.get("value", []):
                if g.get("displayName"):
                    groups.append(g["displayName"])
            url = data.get("@odata.nextLink")

        _cached_groups = groups
        print(f"[AD] {len(groups)} groepen opgehaald.")
        return True

    except Exception as e:
        print(f"[AD] Fout bij Azure AD verbinding: {e}")
        return False


def get_cached_user() -> dict | None:
    """Geeft de gecachte gebruikersinfo terug na succesvolle login."""
    return _cached_user


def get_access_level() -> str:
    """
    Geeft het toegangsniveau van de ingelogde gebruiker:
      "admin"    — lid van group_admin    → volledige toegang
      "readonly" — lid van group_readonly → enkel lezen
      "none"     — geen van beide groepen → geen toegang

    Als group_admin leeg is maar group_readonly ook, en de gebruiker is
    ingelogd → "admin" (geen groepsbeperking geconfigureerd).
    Als enkel group_admin leeg is → iedereen met login krijgt "admin".
    Als enkel group_readonly leeg is → geen read-only niveau beschikbaar.
    """
    if not _cached_user:
        return "none"

    cfg            = get_ad_config()
    group_admin    = cfg.get("group_admin",    "").strip().lower()
    group_readonly = cfg.get("group_readonly", "").strip().lower()
    user_groups    = [g.strip().lower() for g in _cached_groups if g]

    # Geen groepen geconfigureerd → iedereen met login = admin
    if not group_admin and not group_readonly:
        return "admin"

    # Check admin eerst (heeft prioriteit als iemand in beide groepen zit)
    if group_admin and group_admin in user_groups:
        return "admin"

    # Check readonly
    if group_readonly and group_readonly in user_groups:
        return "readonly"

    # Admin-groep leeg maar readonly geconfigureerd → onbekende = none
    if not group_admin and group_readonly:
        return "none"

    # Readonly-groep leeg, admin geconfigureerd maar gebruiker zit er niet in
    return "none"


def has_access() -> bool:
    """Backward-compatible alias: True als level admin of readonly is."""
    return get_access_level() in ("admin", "readonly")