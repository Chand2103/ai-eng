import os
import logging
from typing import AsyncIterator, Union

import httpx

from .base import ConversationBackend
from .openrouter_llm import OpenRouterLLM

logger = logging.getLogger(__name__)

VAST_ROUTE_URL = "https://console.vast.ai/api/v0/route/"


class VastServerlessTTSBackend(ConversationBackend):
    """
    STT → LLM via OpenRouter → TTS via a self-hosted Vast.ai serverless
    endpoint running the inference-engine OmniVoice TTS.

    The LLM call and per-session memory are delegated to ``OpenRouterLLM``
    (shared with ``OpenRouterBackend``).

    The reference voice used for TTS cloning is selected by ``voice_id``
    (1 = Alice, …).  It can be set per-request by the caller or defaulted
    via the ``TTS_VOICE_ID`` env var.
    """

    def __init__(
        self,
        api_key: str,
        llm_model: str | None = None,
        endpoint_name: str | None = None,
        vast_api_key: str | None = None,
        voice_id: int | None = None,
    ):
        self.llm = OpenRouterLLM(api_key=api_key, model=llm_model)
        self.endpoint_name = endpoint_name or os.getenv(
            "VAST_SERVERLESS_ENDPOINT_NAME", ""
        )
        self.vast_api_key = vast_api_key or os.getenv("VAST_API_KEY", "")
        self.voice_id = voice_id
        if self.voice_id is None and os.getenv("TTS_VOICE_ID"):
            self.voice_id = int(os.getenv("TTS_VOICE_ID"))

        self._session_id: str | None = None

    # ------------------------------------------------------------------
    # ConversationBackend interface
    # ------------------------------------------------------------------
    async def connect(self, session_id: str) -> None:
        self._session_id = session_id
        await self.llm.connect(session_id)
        logger.info(f"[{session_id}] VastServerlessTTS session initialised.")

    async def send_transcript(self, text: str) -> AsyncIterator[Union[bytes, str]]:
        session_id = self._session_id
        if not text:
            yield "[no speech detected]"
            return

        # 1. LLM (shared OpenRouterLLM — same as OpenRouterBackend)
        assistant_text = await self.llm.generate(session_id, text)
        if assistant_text is None:
            yield "[LLM error]"
            return

        # 2. Persist conversation turn
        await self.llm.append_turn(session_id, text, assistant_text)

        # 3. Call Vast serverless TTS
        try:
            worker_url, auth_header = await self._route_to_worker()
        except Exception as e:
            logger.exception(f"[{session_id}] Failed to get Vast worker URL: {e}")
            yield f"[TTS error: {e}]"
            return

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                tts_response = await client.post(
                    f"{worker_url}/tts",
                    headers={
                        "Authorization": auth_header,
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": assistant_text,
                        "ref_audio": "ref-aud.wav",
                        "ref_text": "Hi, This is alice, how are you doing today?",
                        "voice_id": self.voice_id,
                    },
                )
                tts_response.raise_for_status()
                wav_bytes = tts_response.content
                if wav_bytes:
                    logger.info(
                        f"[{session_id}] Vast serverless TTS: {len(wav_bytes)} bytes"
                    )
                    yield wav_bytes
        except Exception as e:
            logger.exception(f"[{session_id}] Vast worker TTS call failed: {e}")
            yield f"[TTS error: {e}]"

    async def close(self) -> None:
        session_id = self._session_id
        await self.llm.close_session(session_id)
        await self.llm.close_http()
        logger.info(f"[{session_id}] VastServerlessTTS session cleaned up.")

    # ------------------------------------------------------------------
    # Internal — Vast route resolution
    # ------------------------------------------------------------------
    async def _route_to_worker(self) -> tuple[str, str]:
        """
        Call Vast's ``/api/v0/route/`` endpoint to obtain a live worker URL
        and its auth token for this session.

        Returns
        -------
        (worker_url, auth_header)
            e.g. ``("https://worker-xxx.vast.ai/", "Bearer xxx")``
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                VAST_ROUTE_URL,
                headers={
                    "Authorization": f"Bearer {self.vast_api_key}",
                    "Content-Type": "application/json",
                },
                json={"endpoint_name": self.endpoint_name},
            )
            resp.raise_for_status()
            data = resp.json()
            url: str = data["url"].rstrip("/")
            auth: str = data.get("authorization", "")
            return url, auth
