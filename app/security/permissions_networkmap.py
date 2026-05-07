# =============================================================================
# Networkmap_Creator
# File:    app/security/permissions_networkmap.py
# Role:    Azure AD authenticatie + groepscheck
# Version: 1.0.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie
#                  Azure AD login via MSAL
#                  Groepscheck: CGK-APP-L6
#
# BELANGRIJK:
# - Maak een aparte App Registration aan in Azure Portal
# - Geef de app de API permissions: User.Read + Group.Read.All
# - Vul CLIENT_ID in na aanmaken
# - TENANT_ID blijft hetzelfde als andere CGK apps
# - Geen Qt imports — pure service
# =============================================================================

from __future__ import annotations
import msal
import requests

# ---------------------------------------------------------------------------
# Azure configuratie
# ---------------------------------------------------------------------------

TENANT_ID  = "526b32fa-8cb1-4d6a-9e2b-fd48e2a0e296"
CLIENT_ID  = "58e2dacc-6e4c-4fd0-9166-03b467aeacd8"          # <- na aanmaken App Registration
AUTHORITY  = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES     = ["User.Read", "Group.Read.All"]

GRAPH_ME_ENDPOINT     = "https://graph.microsoft.com/v1.0/me"
GRAPH_GROUPS_ENDPOINT = "https://graph.microsoft.com/v1.0/me/memberOf"

REQUIRED_GROUP = "CGK-APP-L6"

# ---------------------------------------------------------------------------
# Interne state
# ---------------------------------------------------------------------------

_msal_app       = None
_cached_user:   dict | None = None
_cached_groups: list[str]   = []


def _get_msal_app():
    global _msal_app
    if _msal_app is None:
        _msal_app = msal.PublicClientApplication(
            client_id=CLIENT_ID,
            authority=AUTHORITY,
        )
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


def connect_to_azure_ad() -> bool:
    global _cached_user, _cached_groups
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
    return _cached_user


def has_access() -> bool:
    name = REQUIRED_GROUP.strip().lower()
    return any((g or "").strip().lower() == name for g in _cached_groups)