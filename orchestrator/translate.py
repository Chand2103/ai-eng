import os
import json
import logging

import httpx

logger = logging.getLogger(__name__)

# Google Cloud Translation API v2
GC_TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"

# OpenRouter
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

TRANSLATION_SYSTEM_PROMPT = (
    "You are an English-to-Sinhala translator. "
    "Convert the given English text to natural Sinhala. "
    "Keep English terms, proper nouns, technical words, and quoted phrases unchanged. "
    "Respond in JSON with a single field 'translation' containing only the translated text."
)


async def translate_to_sinhala(text: str) -> str | None:
    """
    Translate English *text* to Sinhala.
    Tries OpenRouter (google/gemini-3-flash-preview) first.
    Falls back to Google Cloud Translation API if OpenRouter fails.
    """
    result = await _translate_openrouter(text)
    if result is not None:
        return result

    logger.info("OpenRouter translation failed, falling back to Google Cloud Translation...")
    return await _translate_google_cloud(text)


async def _translate_openrouter(text: str) -> str | None:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set, skipping OpenRouter translation")
        return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "google/gemini-3-flash-preview",
                    "messages": [
                        {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
                        {"role": "user", "content": text},
                    ],
                    "response_format": {"type": "json_object"},
                    "max_tokens": 300,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)
            translated = result.get("translation", "")
            if translated:
                logger.info(f"OpenRouter translation: {translated}")
                return translated
            logger.warning(f"OpenRouter returned empty translation: {content}")
            return None
    except Exception as e:
        logger.warning(f"OpenRouter translation failed: {e}")
        return None


async def _translate_google_cloud(text: str) -> str | None:
    """
    Translate English *text* to Sinhala using the official Google Cloud
    Translation API (v2).

    Requires ``GOOGLE_TRANSLATE_API_KEY`` env var.
    """
    api_key = os.getenv("GOOGLE_TRANSLATE_API_KEY", "")
    if not api_key:
        logger.error("GOOGLE_TRANSLATE_API_KEY not set")
        return None

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                GC_TRANSLATE_URL,
                params={"key": api_key},
                json={
                    "q": text,
                    "target": "si",
                    "source": "en",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            translated = data["data"]["translations"][0]["translatedText"]
            logger.info(f"Google Cloud translation: {translated}")
            return translated
    except Exception as e:
        logger.exception(f"Google Cloud Translation API failed: {e}")
        return None
