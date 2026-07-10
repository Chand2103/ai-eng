import os
from contextlib import asynccontextmanager
import logging
from typing import AsyncIterator, AsyncGenerator, List, Union

import httpx

from .base import ConversationBackend
from .openrouter_llm import OpenRouterLLM

logger = logging.getLogger(__name__)


class OpenRouterBackend(ConversationBackend):
    """
    LLM via OpenRouter (meta-llama/llama-3.1-8b-instruct) + TTS via
    OpenRouter's /api/v1/audio/speech (x-ai/grok-voice-tts-1.0).

    Per-session memory and the LLM call are delegated to ``OpenRouterLLM``
    (shared with ``VastServerlessTTSBackend``).
    """

    def __init__(
        self,
        api_key: str,
        llm_model: str | None = None,
        tts_model: str | None = None,
        tts_voice: str | None = None,
    ):
        self.llm = OpenRouterLLM(api_key=api_key, model=llm_model)
        self.tts_model = tts_model or os.getenv(
            "OPENROUTER_TTS_MODEL", "x-ai/grok-voice-tts-1.0"
        )
        self.tts_voice = tts_voice or os.getenv(
            "OPENROUTER_TTS_VOICE", "Eve"
        )
        self.tts_sample_rate = int(os.getenv("OPENROUTER_TTS_SAMPLE_RATE", "24000"))

        self._session_id: str | None = None

    # ------------------------------------------------------------------
    # ConversationBackend interface
    # ------------------------------------------------------------------
    async def connect(self, session_id: str) -> None:
        self._session_id = session_id
        await self.llm.connect(session_id)
        logger.info(f"[{session_id}] OpenRouter session initialised.")

    async def send_transcript(self, text: str) -> AsyncIterator[Union[bytes, str]]:
        session_id = self._session_id
        if not text:
            yield "[no speech detected]"
            return

        # 1. LLM (delegated to shared module)
        assistant_text = await self.llm.generate(session_id, text)
        if assistant_text is None:
            yield "[LLM error]"
            return

        # 2. Persist conversation turn
        await self.llm.append_turn(session_id, text, assistant_text)

        # 3. OpenRouter TTS
        async for audio_bytes in self._call_tts(session_id, assistant_text):
            yield audio_bytes

    async def close(self) -> None:
        session_id = self._session_id
        await self.llm.close_session(session_id)
        await self.llm.close_http()
        logger.info(f"[{session_id}] OpenRouter session cleaned up.")

    # ------------------------------------------------------------------
    # TTS – OpenRouter /api/v1/audio/speech
    # ------------------------------------------------------------------
    async def _call_tts(
        self, session_id: str, text: str
    ) -> AsyncIterator[Union[bytes, str]]:
        chunks = _split_text_for_tts(text, max_chars=14000)
        for chunk in chunks:
            try:
                async with _httpx_client() as client:
                    tts_response = await client.post(
                        "https://openrouter.ai/api/v1/audio/speech",
                        headers={
                            "Authorization": f"Bearer {self.llm.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.tts_model,
                            "input": chunk,
                            "voice": self.tts_voice,
                            "response_format": "pcm",
                        },
                    )
                    tts_response.raise_for_status()
                    pcm_bytes = tts_response.content
                    if pcm_bytes:
                        wav_bytes = _pcm_to_wav(
                            pcm_bytes,
                            sample_rate=self.tts_sample_rate,
                        )
                        logger.info(
                            f"[{session_id}] TTS chunk: {len(wav_bytes)} bytes "
                            f"(input chars: {len(chunk)})"
                        )
                        yield wav_bytes
            except Exception as e:
                logger.exception(f"[{session_id}] OpenRouter TTS call failed: {e}")
                yield f"[TTS error: {e}]"


# ---------------------------------------------------------------------------
# Helpers (also used by vast_serverless_tts_backend)
# ---------------------------------------------------------------------------
def _split_text_for_tts(text: str, max_chars: int = 14000) -> List[str]:
    """Split *text* into chunks that fit within a TTS character limit."""
    if len(text) <= max_chars:
        return [text]
    normalised = text.replace("! ", ". ").replace("? ", ". ")
    sentences = normalised.split(". ")
    chunks: List[str] = []
    current = ""
    for sentence in sentences:
        candidate = current + ". " + sentence if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks


def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000) -> bytes:
    """Prepend a 44-byte WAV header to raw 16-bit mono PCM data."""
    bits_per_sample = 16
    channels = 1
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    data_size = len(pcm_data)
    file_size = 36 + data_size
    header = bytearray(44)
    header[0:4] = b"RIFF"
    header[4:8] = file_size.to_bytes(4, "little")
    header[8:12] = b"WAVE"
    header[12:16] = b"fmt "
    header[16:20] = (16).to_bytes(4, "little")
    header[20:22] = (1).to_bytes(2, "little")
    header[22:24] = channels.to_bytes(2, "little")
    header[24:28] = sample_rate.to_bytes(4, "little")
    header[28:32] = byte_rate.to_bytes(4, "little")
    header[32:34] = block_align.to_bytes(2, "little")
    header[34:36] = bits_per_sample.to_bytes(2, "little")
    header[36:40] = b"data"
    header[40:44] = data_size.to_bytes(4, "little")
    return bytes(header) + pcm_data


@asynccontextmanager
async def _httpx_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Short-lived HTTP client for one-off TTS calls."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        yield client
