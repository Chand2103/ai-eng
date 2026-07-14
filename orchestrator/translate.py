import logging

import httpx

logger = logging.getLogger(__name__)

GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"


async def translate_to_sinhala(text: str) -> str | None:
    """Translate English *text* to Sinhala via the unofficial Google Translate API."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                GOOGLE_TRANSLATE_URL,
                params={
                    "client": "gtx",
                    "sl": "en",
                    "tl": "si",
                    "dt": "t",
                    "q": text,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            # Response format: [[["translation","original",...],...],...]
            translated = "".join(part[0] for part in data[0])
            logger.info(f"Translated to Sinhala: {translated}")
            return translated
    except Exception as e:
        logger.exception(f"Google Translate failed: {e}")
        return None
