"""Utility helpers for automatic Indonesian -> other language translations, including HTML-safe translation."""

import asyncio
from functools import lru_cache
import logging
import os
import re
from typing import Iterable, Mapping
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

SKIP_TAGS = {"script", "style", "code", "pre"}


def _translation_concurrency() -> int:
    try:
        return max(1, int(os.getenv("TRANSLATION_CONCURRENCY", "5")))
    except ValueError:
        return 5


TRANSLATION_CONCURRENCY = _translation_concurrency()


@lru_cache(maxsize=None)
def _translator(target_lang: str):
    """Create or cache a translator for given target language."""
    if GoogleTranslator is None:
        raise RuntimeError(
            "deep-translator is not installed; add it to requirements to enable auto translation"
        )
    actual_target = TRANSLATOR_TARGETS.get(target_lang, target_lang)
    return GoogleTranslator(source=BASE_LANG, target=actual_target)


@lru_cache(maxsize=4096)
def _translate_text_cached(target_lang: str, text: str) -> str:
    translator = _translator(target_lang)
    translated = translator.translate(text)
    return translated if translated is not None else text


def translate_text(text: str | None, target_lang: str) -> str | None:
    """Translate plain text from Indonesian to the target language."""
    if not text or target_lang == BASE_LANG:
        return text
    try:
        return _translate_text_cached(target_lang, text)
    except Exception as exc:
        logger.warning("Auto translation failed for %s: %s", target_lang, exc)
        return text


def _split_outer_whitespace(value: str) -> tuple[str, str, str]:
    match = re.match(r"^(\s*)(.*?)(\s*)$", value, flags=re.DOTALL)
    if not match:
        return "", value, ""
    return match.group(1), match.group(2), match.group(3)


def _translate_batch_texts(texts: list[str], target_lang: str) -> list[str]:
    if not texts or target_lang == BASE_LANG:
        return texts

    if len(texts) > 1:
        try:
            translator = _translator(target_lang)
            translate_batch = getattr(translator, "translate_batch", None)
            if callable(translate_batch):
                translated = translate_batch(texts)
                if isinstance(translated, list) and len(translated) == len(texts):
                    return [
                        item if item is not None else source
                        for source, item in zip(texts, translated)
                    ]
        except Exception as exc:
            logger.warning("Batch translation failed for %s: %s", target_lang, exc)

    return [translate_text(text, target_lang) or text for text in texts]


def _collect_text_replacements(soup: BeautifulSoup):
    replacements = []
    text_values: list[str] = []
    for elem in soup.find_all(string=True):
        if elem.parent and elem.parent.name in SKIP_TAGS:
            continue

        prefix, text, suffix = _split_outer_whitespace(str(elem))
        if not text:
            continue

        replacements.append((elem, prefix, text, suffix))
        text_values.append(text)
    return replacements, text_values


def _apply_text_replacements(replacements, translated_lookup: dict[str, str]) -> None:
    for elem, prefix, text, suffix in replacements:
        elem.replace_with(f"{prefix}{translated_lookup.get(text, text)}{suffix}")


def _translate_html_fragment(fragment: str, target_lang: str) -> str:
    """Translate text content inside HTML while preserving tags."""
    soup = BeautifulSoup(fragment, "html.parser")
    replacements, text_values = _collect_text_replacements(soup)
    if not replacements:
        return str(soup)

    unique_values = list(dict.fromkeys(text_values))
    translated_values = _translate_batch_texts(unique_values, target_lang)
    translated_lookup = dict(zip(unique_values, translated_values))
    _apply_text_replacements(replacements, translated_lookup)
    return str(soup)


def _translate_payload_for_language(
    entries: list[tuple[str, str]],
    lang: str,
) -> dict[str, str | None]:
    results: dict[str, str | None] = {}
    parsed_entries = []
    all_text_values: list[str] = []

    for field, value in entries:
        if not value:
            results[field] = value
            continue

        soup = BeautifulSoup(value, "html.parser")
        replacements, text_values = _collect_text_replacements(soup)
        if not replacements:
            results[field] = str(soup)
            continue

        parsed_entries.append((field, soup, replacements))
        all_text_values.extend(text_values)

    if parsed_entries:
        unique_values = list(dict.fromkeys(all_text_values))
        translated_values = _translate_batch_texts(unique_values, lang)
        translated_lookup = dict(zip(unique_values, translated_values))
        for field, soup, replacements in parsed_entries:
            _apply_text_replacements(replacements, translated_lookup)
            results[field] = str(soup)

    return results


async def _run_translation_job(func, *args):
    return await asyncio.to_thread(func, *args)


async def translate_html_content(html_string: str, target_language="en"):
    """Translate HTML content preserving structure."""
    if not html_string:
        return None

    try:
        translated_html = await _run_translation_job(
            _translate_html_fragment, html_string, target_language
        )
        return translated_html
    except Exception as exc:
        logger.warning("deep_translator failed, fallback to googletrans: %s", exc)

    # fallback using googletrans
    if Translator is not None:
        try:
            translator = Translator()
            soup = BeautifulSoup(html_string, "html.parser")
            for elem in soup.find_all(string=True):
                if elem.parent and elem.parent.name in SKIP_TAGS:
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
    manual_translations: Mapping[str, Mapping[str, str | None]] | None = None,
) -> dict[str, dict[str, str | None]]:
    """Translate a mapping of field names (HTML-safe) into the provided languages."""
    language_list = tuple(languages)
    results: dict[str, dict[str, str | None]] = {lang: {} for lang in language_list}
    pending_by_lang: dict[str, list[tuple[str, str]]] = {}

    for lang in language_list:
        manual_for_lang = (
            manual_translations.get(lang, {}) if manual_translations else {}
        )
        for field, value in payload.items():
            manual_value = manual_for_lang.get(field)
            if isinstance(manual_value, str):
                manual_value = manual_value.strip()
            if manual_value:
                results[lang][field] = manual_value
                continue

            if not value or lang == BASE_LANG:
                results[lang][field] = value
                continue

            pending_by_lang.setdefault(lang, []).append((field, value))

    if pending_by_lang:
        gate = asyncio.Semaphore(TRANSLATION_CONCURRENCY)

        async def run_for_language(lang: str, entries: list[tuple[str, str]]):
            async with gate:
                return await _run_translation_job(
                    _translate_payload_for_language, entries, lang
                )

        tasks = {
            lang: asyncio.create_task(run_for_language(lang, entries))
            for lang, entries in pending_by_lang.items()
        }
        for lang, task in tasks.items():
            try:
                results[lang].update(await task)
            except Exception as exc:
                logger.warning("Payload translation failed for %s: %s", lang, exc)
                for field, value in pending_by_lang[lang]:
                    results[lang][field] = value

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
