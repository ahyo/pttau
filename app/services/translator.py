"""Utility helpers for automatic Indonesian -> other language translations."""

from functools import lru_cache
import logging
from typing import Iterable, Mapping

try:
    from deep_translator import GoogleTranslator
except ImportError:  # pragma: no cover - dependency is expected in runtime env
    GoogleTranslator = None  # type: ignore


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
    if GoogleTranslator is None:
        raise RuntimeError(
            "deep-translator is not installed; add it to requirements to enable auto translation"
        )
    actual_target = TRANSLATOR_TARGETS.get(target_lang, target_lang)
    return GoogleTranslator(source=BASE_LANG, target=actual_target)


def translate_text(text: str | None, target_lang: str) -> str | None:
    """Translate the given text from Indonesian to the target language."""
    if not text or target_lang == BASE_LANG:
        return text
    try:
        translator = _translator(target_lang)
        return translator.translate(text)
    except Exception as exc:  # pragma: no cover - network failures, etc.
        logger.warning("Auto translation failed for %s: %s", target_lang, exc)
        return text


def translate_payload(
    payload: dict[str, str | None],
    languages: Iterable[str],
) -> dict[str, dict[str, str | None]]:
    """Translate a mapping of field names into the provided languages."""
    results: dict[str, dict[str, str | None]] = {}
    for lang in languages:
        translated: dict[str, str | None] = {}
        for field, value in payload.items():
            translated[field] = translate_text(value, lang)
        results[lang] = translated
    return results


def collect_translation_inputs(
    form: Mapping[str, str | None],
    fields: Iterable[str],
) -> dict[str, dict[str, str | None]]:
    translations: dict[str, dict[str, str | None]] = {}
    for lang in SUPPORTED_LANGS:
        entries: dict[str, str | None] = {}
        for field in fields:
            key = f"{field}_{lang}"
            entries[field] = form.get(key) if hasattr(form, "get") else None
        translations[lang] = entries
    return translations
