"""
i18n\__init__.py

Beschrijving: i18n package init
Applicatie: networkmanager
Versie: 1.0.0
Auteur: Barremans
"""

"""
i18n/__init__.py
"""

from i18n.translator import Translator, get_translator, t

__all__ = ["Translator", "get_translator", "t"]
