"""Language pack manager — install and switch UI languages."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Optional

from aetheros_constants import get_aetheros_home
from hub.store import HubStore

logger = logging.getLogger(__name__)


LANGAUGE_PACKS: list[dict] = [
    {"id": "lang_en", "name": "English", "native": "English", "code": "en",
     "author": "Aetheros", "version": "1.0.0", "official": True, "rtl": False},
    {"id": "lang_bn", "name": "Bangla", "native": "বাংলা", "code": "bn",
     "author": "Aetheros", "version": "1.0.0", "official": False, "rtl": False},
    {"id": "lang_ja", "name": "Japanese", "native": "日本語", "code": "ja",
     "author": "Aetheros", "version": "1.0.0", "official": True, "rtl": False},
    {"id": "lang_zh", "name": "Chinese (Simplified)", "native": "简体中文", "code": "zh-CN",
     "author": "Aetheros", "version": "1.0.0", "official": True, "rtl": False},
    {"id": "lang_es", "name": "Spanish", "native": "Español", "code": "es",
     "author": "Aetheros", "version": "1.0.0", "official": True, "rtl": False},
    {"id": "lang_fr", "name": "French", "native": "Français", "code": "fr",
     "author": "Aetheros", "version": "1.0.0", "official": True, "rtl": False},
    {"id": "lang_de", "name": "German", "native": "Deutsch", "code": "de",
     "author": "Aetheros", "version": "1.0.0", "official": True, "rtl": False},
    {"id": "lang_ar", "name": "Arabic", "native": "العربية", "code": "ar",
     "author": "Aetheros", "version": "1.0.0", "official": False, "rtl": True},
    {"id": "lang_hi", "name": "Hindi", "native": "हिन्दी", "code": "hi",
     "author": "Aetheros", "version": "1.0.0", "official": False, "rtl": False},
    {"id": "lang_ko", "name": "Korean", "native": "한국어", "code": "ko",
     "author": "Aetheros", "version": "1.0.0", "official": False, "rtl": False},
    {"id": "lang_pt", "name": "Portuguese", "native": "Português", "code": "pt",
     "author": "Aetheros", "version": "1.0.0", "official": False, "rtl": False},
    {"id": "lang_ru", "name": "Russian", "native": "Русский", "code": "ru",
     "author": "Aetheros", "version": "1.0.0", "official": False, "rtl": False},
    {"id": "lang_tr", "name": "Turkish", "native": "Türkçe", "code": "tr",
     "author": "Aetheros", "version": "1.0.0", "official": False, "rtl": False},
    {"id": "lang_it", "name": "Italian", "native": "Italiano", "code": "it",
     "author": "Aetheros", "version": "1.0.0", "official": False, "rtl": False},
    {"id": "lang_nl", "name": "Dutch", "native": "Nederlands", "code": "nl",
     "author": "Aetheros", "version": "1.0.0", "official": False, "rtl": False},
]


class LanguagePackManager:
    def __init__(self, store=None):
        self.store = store or HubStore()
        self.lang_dir = get_aetheros_home() / "languages"
        self.lang_dir.mkdir(parents=True, exist_ok=True)

    def get_catalog(self) -> list[dict]:
        return list(LANGAUGE_PACKS)

    def get_pack(self, lang_id: str) -> Optional[dict]:
        for p in LANGAUGE_PACKS:
            if p["id"] == lang_id:
                return dict(p)
        return None

    def install(self, lang_id: str) -> dict:
        info = self.get_pack(lang_id)
        if not info:
            return {"success": False, "error": f"Language pack {lang_id} not found"}
        self.store.install_item(lang_id, info["name"], "language_packs",
                                info.get("version", "1.0.0"),
                                description=f"{info['native']} ({info['code']})",
                                author=info.get("author", "Aetheros"),
                                tags=[info["code"]])
        return {"success": True, "lang_id": lang_id, "code": info["code"]}

    def activate(self, lang_id: str) -> dict:
        info = self.get_pack(lang_id)
        if not info:
            return {"success": False, "error": f"Language pack {lang_id} not found"}
        self.store.set_setting("active_language", lang_id)
        return {"success": True, "lang_id": lang_id, "code": info["code"]}

    def list_installed(self) -> list[dict]:
        return self.store.get_installed("language_packs")

    def get_active(self) -> str:
        return self.store.get_setting("active_language", "lang_en")
