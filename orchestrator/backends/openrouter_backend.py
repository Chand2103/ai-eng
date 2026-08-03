import os
from contextlib import asynccontextmanager
import logging
from typing import AsyncIterator, AsyncGenerator, List, Union

import httpx

from .base import (
    ConversationBackend,
    BEGIN_ROLEPLAY_TEXT,
    ROLEPLAY_COMPLETE_MARKER,
    feedback_to_spoken,
)
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
    async def connect(
        self,
        session_id: str,
        system_prompt: str | None = None,
        structured_output: bool = True,
        roleplay: bool = False,
    ) -> None:
        self._session_id = session_id
        await self.llm.connect(session_id, system_prompt, structured_output, roleplay)
        logger.info(f"[{session_id}] OpenRouter session initialised.")

    async def send_opening(self) -> AsyncIterator[Union[bytes, str]]:
        """Speak the persona's opening line at the start of a roleplay."""
        session_id = self._session_id
        result = await self.llm.generate(session_id, BEGIN_ROLEPLAY_TEXT)
        if result is None:
            yield "[LLM error]"
            return
        full_response = result.get("full_response", "")
        logger.info(f"[{session_id}] Roleplay opening: {full_response}")
        await self.llm.append_turn(session_id, BEGIN_ROLEPLAY_TEXT, result)
        async for audio_bytes in self._call_tts(session_id, full_response):
            yield audio_bytes

    async def send_transcript(self, text: str) -> AsyncIterator[Union[bytes, str]]:
        session_id = self._session_id
        if not text:
            yield "[no speech detected]"
            return

        # 1. LLM (delegated to shared module)
        result = await self.llm.generate(session_id, text)
        if result is None:
            yield "[LLM error]"
            return

        full_response = result.get("full_response", "")
        advice = result.get("advice", "")
        logger.info(f"[{session_id}] full_response: {full_response}")
        logger.info(f"[{session_id}] advice: {advice}")

        # 2. Persist conversation turn
        await self.llm.append_turn(session_id, text, result)

        # 3. Send advice text to frontend
        if advice:
            yield advice

        # 4. OpenRouter TTS
        async for audio_bytes in self._call_tts(session_id, full_response):
            yield audio_bytes

        # 5. End-of-roleplay signal
        if result.get("is_complete"):
            yield ROLEPLAY_COMPLETE_MARKER

    async def get_feedback(self) -> AsyncIterator[Union[bytes, str]]:
        """
        Evaluate the finished roleplay and yield feedback for the frontend.

        Yields the raw JSON report as text, then the spoken summary as
        TTS audio bytes.  Runs even after a manual end, so this is the
        single path for both end styles.
        """
        session_id = self._session_id
        feedback_json, error = await self.llm.generate_feedback(session_id)
        if error == "no transcript":
            yield "[No speech was captured during this session, so there is no feedback to give.]"
            return
        if feedback_json is None:
            yield f"[feedback error: {error}]"
            return

        logger.info(f"[{session_id}] Feedback JSON: {feedback_json}")
        yield feedback_json

        spoken = feedback_to_spoken(feedback_json)
        logger.info(f"[{session_id}] Spoken feedback: {spoken}")
        async for audio_bytes in self._call_tts(session_id, spoken):
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
