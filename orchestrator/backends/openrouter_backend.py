import os
import asyncio
import logging
from typing import AsyncIterator, Dict, List, Union

import httpx

from .base import ConversationBackend

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt – identical to inference-engine/llm.py
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    """You are Mrs. Linton, a friendly and encouraging English conversation teacher running a "Free Talk" session. The student can bring up almost any everyday topic they like, and you chat with them naturally. Your goals, in order of priority:

1. AVOID SENSITIVE TOPICS
Do not engage in discussions about politics, religion, war, violence, sexual content, self-harm, illegal activity, or other sensitive or controversial subjects, even if the student brings them up or insists. If the student raises one of these, politely decline and steer the conversation to a lighter everyday topic. Do not lecture or explain why at length — just one short sentence to redirect.

2. RESPOND FIRST, THEN GIVE FEEDBACK — every single time
For every student message (except sensitive-topic cases above), structure your reply in two parts, in this order:
   a) First, respond naturally to what the student said, continuing the conversation like a normal chat (ask a follow-up question, react, share a thought, etc.)
   b) Then, give brief feedback on the student's English in that message:
      - If their grammar, vocabulary, and phrasing were all correct, give a short encouraging line, for example: "Well done, your grammar was spot on!" or "Nice, that sentence was perfect."
      - If there was an error, gently point it out and give the correct form in one short sentence, for example: "Just a small note — it should be 'I went to the market,' not 'I go to the market.'"
   Never skip the feedback part, even for very short or simple student messages. Never give feedback before responding to the content — always respond first, feedback second.

3. KEEP RESPONSES SHORT AND SPOKEN
Your replies will be read aloud by a text-to-speech system. Always respond in plain, natural spoken sentences only — no lists, no bullet points, no markdown, no asterisks, no headers. Keep the whole reply (response + feedback) to 2-4 sentences.

Here are examples of how you should respond:

---
Student: "I watched a movie yesterday with my friends, it was really good."
Mrs. Linton: "That sounds fun, what movie did you watch? Well done, your grammar was spot on there!"
---
Student: "Yesterday I go to the market and buy some vegetable."
Mrs. Linton: "Nice, what did you end up making with them? Just a small note — for things that happened yesterday, we say 'I went to the market and bought some vegetables.'"
---
Student: "My favorite hobby is play guitar."
Mrs. Linton: "That's a great hobby, how long have you been playing? One quick correction — it should be 'My favorite hobby is playing guitar.'"
---
Student: "What do you think about the current government and the election?"
Mrs. Linton: "That's not something I can chat about here, let's keep things light! Tell me, what do you usually do on your weekends?"
---
Student: "I am living in this city since five years and I like it very much."
Mrs. Linton: "That's wonderful, what do you like most about it? Almost there — we'd say 'I have been living in this city for five years.'"
---

Always remain in character as Mrs. Linton. Never mention that you are an AI, a language model, or that you are following instructions."""
)


class OpenRouterBackend(ConversationBackend):
    """
    Calls OpenRouter for LLM (meta-llama/llama-3.1-8b-instruct) and TTS
    (x-ai/grok-voice-tts-1.0).  Per-session conversation history is kept
    in-memory, mirroring the same model used by inference-engine/server.py.
    """

    def __init__(
        self,
        api_key: str,
        llm_model: str | None = None,
        tts_model: str | None = None,
        tts_voice: str | None = None,
    ):
        self.api_key = api_key
        self.llm_model = llm_model or os.getenv(
            "OPENROUTER_LLM_MODEL", "meta-llama/llama-3.1-8b-instruct"
        )
        self.tts_model = tts_model or os.getenv(
            "OPENROUTER_TTS_MODEL", "x-ai/grok-voice-tts-1.0"
        )
        self.tts_voice = tts_voice or os.getenv(
            "OPENROUTER_TTS_VOICE", "Eve"
        )
        self.tts_format = os.getenv("OPENROUTER_TTS_FORMAT", "pcm")
        self.tts_sample_rate = int(os.getenv("OPENROUTER_TTS_SAMPLE_RATE", "24000"))

        # Per-session message history – same model as inference-engine/server.py
        self._sessions: Dict[str, List[dict]] = {}
        self._lock = asyncio.Lock()

        self._session_id: str | None = None
        self._http: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    async def connect(self, session_id: str) -> None:
        self._session_id = session_id
        async with self._lock:
            self._sessions[session_id] = []
        self._http = httpx.AsyncClient(timeout=30.0)
        logger.info(f"[{session_id}] OpenRouter session initialised.")

    async def send_transcript(self, text: str) -> AsyncIterator[Union[bytes, str]]:
        session_id = self._session_id
        if not text:
            yield "[no speech detected]"
            return

        # 1. LLM call
        assistant_text = await self._call_llm(session_id, text)
        if assistant_text is None:
            yield "[LLM error]"
            return

        # 2. Persist conversation turn
        await self._append_turn(session_id, text, assistant_text)

        # 3. TTS call(s) – split into chunks if the response is long
        async for audio_bytes in self._call_tts(session_id, assistant_text):
            yield audio_bytes

    async def close(self) -> None:
        session_id = self._session_id
        async with self._lock:
            self._sessions.pop(session_id, None)
        if self._http is not None:
            await self._http.aclose()
            self._http = None
        logger.info(f"[{session_id}] OpenRouter session cleaned up.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _get_history(self, session_id: str) -> List[dict]:
        async with self._lock:
            return list(self._sessions.get(session_id, []))

    async def _append_turn(
        self, session_id: str, user_text: str, assistant_text: str
    ) -> None:
        async with self._lock:
            sess = self._sessions.get(session_id)
            if sess is not None:
                sess.append({"role": "user", "content": user_text})
                sess.append({"role": "assistant", "content": assistant_text})

    async def _call_llm(self, session_id: str, text: str) -> str | None:
        try:
            history = await self._get_history(session_id)
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages.extend(history)
            messages.append({"role": "user", "content": text})

            response = await self._http.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.llm_model,
                    "messages": messages,
                    "max_tokens": 80,
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

        except Exception as e:
            logger.exception(f"[{session_id}] OpenRouter LLM call failed: {e}")
            return None

    async def _call_tts(
        self, session_id: str, text: str
    ) -> AsyncIterator[Union[bytes, str]]:
        """
        Synthesise *text* via the OpenRouter TTS API, splitting into chunks
        if the text exceeds the Grok Voice TTS 15 000-character limit.
        """
        chunks = self._split_text_for_tts(text, max_chars=14000)
        for chunk in chunks:
            try:
                tts_response = await self._http.post(
                    "https://openrouter.ai/api/v1/audio/speech",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
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
                    # Wrap raw PCM in a WAV header so the frontend can play it
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

    @staticmethod
    def _split_text_for_tts(text: str, max_chars: int = 14000) -> List[str]:
        """Split *text* into chunks that fit within the TTS character limit."""
        if len(text) <= max_chars:
            return [text]

        # Normalise sentence-ending punctuation for splitting
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


# ---------------------------------------------------------------------------
# WAV helper – wraps raw PCM 16-bit mono in a standard RIFF/WAV header
# ---------------------------------------------------------------------------
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
    header[16:20] = (16).to_bytes(4, "little")       # sub-chunk size
    header[20:22] = (1).to_bytes(2, "little")         # PCM format
    header[22:24] = channels.to_bytes(2, "little")
    header[24:28] = sample_rate.to_bytes(4, "little")
    header[28:32] = byte_rate.to_bytes(4, "little")
    header[32:34] = block_align.to_bytes(2, "little")
    header[34:36] = bits_per_sample.to_bytes(2, "little")
    header[36:40] = b"data"
    header[40:44] = data_size.to_bytes(4, "little")

    return bytes(header) + pcm_data
