# =============================================================================
# Networkmap_Creator
# File:    app/helpers/formatting.py
# Role:    Gedeelde formatteer-/normalisatiehelpers (geen Qt)
# Version: 1.0.0
# Author:  Barremans
# Changes: 1.0.0 — Initiële versie: normalize_mac() voor F8 (kopiëren naar
#                   klembord). Stemt af met F10 / sectie 12 v30:
#                   MAC altijd uppercase AA:BB:CC:DD:EE:FF.
# =============================================================================

_HEX = set("0123456789abcdefABCDEF")


def normalize_mac(value) -> str:
    """
    Normaliseer een MAC-adres naar uppercase ``AA:BB:CC:DD:EE:FF``.

    - Scheidingstekens (``:``, ``-``, ``.``, spaties) worden genegeerd.
    - Bij exact 12 hex-tekens → gegroepeerd per 2 met dubbele punt.
    - Bij een afwijkend formaat → minimaal getrimd + uppercase teruggegeven
      (nooit crashen, nooit data weggooien).
    - Lege/None invoer → lege string.
    """
    if not value:
        return ""
    raw = str(value)
    hexchars = "".join(c for c in raw if c in _HEX)
    if len(hexchars) == 12:
        hexchars = hexchars.upper()
        return ":".join(hexchars[i:i + 2] for i in range(0, 12, 2))
    return raw.strip().upper()