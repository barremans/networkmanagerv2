"""
i18n\translator.py

Beschrijving: Translation helper
Applicatie: networkmanager
Versie: 1.0.0
Auteur: Barremans
"""

"""
i18n/translator.py
Translation helper
"""

import json
from pathlib import Path
from typing import Dict, Optional

class Translator:
    def __init__(self, locale: str = "en_US"):
        self.locale = locale
        self.translations: Dict[str, str] = {}
        self.fallback_locale = "en_US"
        self.fallback_translations: Dict[str, str] = {}
        self._load_translations()
    
    def _load_translations(self):
        locales_dir = Path(__file__).parent / "locales"
        
        locale_file = locales_dir / f"{self.locale}.json"
        if locale_file.exists():
            with open(locale_file, "r", encoding="utf-8") as f:
                self.translations = json.load(f)
        
        if self.locale != self.fallback_locale:
            fallback_file = locales_dir / f"{self.fallback_locale}.json"
            if fallback_file.exists():
                with open(fallback_file, "r", encoding="utf-8") as f:
                    self.fallback_translations = json.load(f)
    
    def get(self, key: str, **kwargs) -> str:
        text = self.translations.get(key)
        
        if text is None:
            text = self.fallback_translations.get(key)
        
        if text is None:
            return key
        
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                pass
        
        return text
    
    def set_locale(self, locale: str):
        self.locale = locale
        self._load_translations()

_translator: Optional[Translator] = None

def get_translator(locale: str = "en_US") -> Translator:
    global _translator
    if _translator is None:
        _translator = Translator(locale)
    return _translator

def t(key: str, **kwargs) -> str:
    return get_translator().get(key, **kwargs)
