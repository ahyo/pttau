"""Utility helpers for automatic Indonesian -> other language translations, including HTML-safe translation."""

from functools import lru_cache
import logging
from typing import Iterable, Mapping
import os
from bs4 import BeautifulSoup

try:
    from googletrans import Translator
except ImportError:
    Translator = None

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

logger = logging.getLogger(__name__)

SUPPORTED_LANGS = ("en", "ar", "ja", "ko", "zh-cn")
BASE_LANG = "id"
ALL_LANGS = (BASE_LANG,) + SUPPORTED_LANGS

LANG_LABELS = {
    "id": "Indonesian",
    "en": "English",
    "ar": "Arabic",
    "ja": "Japanese",
    "ko": "Korean",
    "zh-cn": "Chinese",
}

LANG_FLAGS = {
    "id": "🇮🇩",
    "en": "🇬🇧",
    "ar": "🇸🇦",
    "ja": "🇯🇵",
    "ko": "🇰🇷",
    "zh-cn": "🇨🇳",
}

TRANSLATOR_TARGETS = {
    "zh-cn": "zh-CN",
}


@lru_cache(maxsize=None)
def _translator(target_lang: str):
    """Create or cache a translator for given target language."""
    if GoogleTranslator is None:
        raise RuntimeError(
            "deep-translator is not installed; add it to requirements to enable auto translation"
        )
    actual_target = TRANSLATOR_TARGETS.get(target_lang, target_lang)
    return GoogleTranslator(source=BASE_LANG, target=actual_target)


def translate_text(text: str | None, target_lang: str) -> str | None:
    """Translate plain text from Indonesian to the target language."""
    if not text or target_lang == BASE_LANG:
        return text
    try:
        translator = _translator(target_lang)
        return translator.translate(text)
    except Exception as exc:
        logger.warning("Auto translation failed for %s: %s", target_lang, exc)
        return text


def _translate_html_fragment(fragment: str, target_lang: str) -> str:
    """Translate text content inside HTML while preserving tags."""
    soup = BeautifulSoup(fragment, "html.parser")

    for elem in soup.find_all(text=True):
        # Skip tags that shouldn't be translated
        if elem.parent.name in ("script", "style", "code", "pre"):
            continue

        text = elem.strip()
        if not text:
            continue

        try:
            elem.replace_with(translate_text(text, target_lang))
        except Exception as exc:
            logger.warning("Failed translating fragment [%s]: %s", text, exc)

    return str(soup)


async def translate_html_content(html_string: str, target_language="en"):
    """Translate HTML content preserving structure."""
    if not html_string:
        return None

    try:
        # First try using deep_translator (preferred for consistency)
        translated_html = _translate_html_fragment(html_string, target_language)
        return translated_html
    except Exception as exc:
        logger.warning("deep_translator failed, fallback to googletrans: %s", exc)

    # fallback using googletrans
    if Translator is not None:
        try:
            translator = Translator()
            soup = BeautifulSoup(html_string, "html.parser")
            for elem in soup.find_all(text=True):
                if elem.parent.name in ("script", "style", "code", "pre"):
                    continue
                text = elem.strip()
                if text:
                    translated = translator.translate(text, dest=target_language).text
                    elem.replace_with(translated)
            return str(soup)
        except Exception as e:
            logger.error("googletrans translation failed: %s", e)
            return html_string
    else:
        return html_string


async def translate_payload(
    payload: dict[str, str | None],
    languages: Iterable[str],
) -> dict[str, dict[str, str | None]]:
    """Translate a mapping of field names (HTML-safe) into the provided languages."""
    results: dict[str, dict[str, str | None]] = {}
    for lang in languages:
        translated: dict[str, str | None] = {}
        for field, value in payload.items():
            translated[field] = await translate_html_content(value, lang)
        results[lang] = translated
    return results


def collect_translation_inputs(
    form: Mapping[str, str | None],
    fields: Iterable[str],
) -> dict[str, dict[str, str | None]]:
    """Collect translation form inputs for all supported languages."""
    translations: dict[str, dict[str, str | None]] = {}
    for lang in SUPPORTED_LANGS:
        entries: dict[str, str | None] = {}
        for field in fields:
            key = f"{field}_{lang}"
            entries[field] = form.get(key) if hasattr(form, "get") else None
        translations[lang] = entries
    return translations
