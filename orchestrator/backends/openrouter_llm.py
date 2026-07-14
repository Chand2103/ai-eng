import json
import os
import asyncio
import logging
from typing import Dict, List

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt – canonical copy (identical to inference-engine/llm.py)
# Import this from other backends instead of duplicating.
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

4. OUTPUT JSON
You MUST respond with valid JSON only — no markdown, no code fences. The JSON must have exactly two keys:
   - "full_response": Your complete reply (response + feedback, spoken naturally, 2-4 sentences)
   - "advice": Just the English feedback/improvement part, extracted into 1-2 concise sentences. If the topic was sensitive and you redirected, set this to ""

Here are examples of how you should respond:

---
Student: "I watched a movie yesterday with my friends, it was really good."
{"full_response": "That sounds fun, what movie did you watch? Well done, your grammar was spot on there!", "advice": "Well done, your grammar was spot on there!"}
---
Student: "Yesterday I go to the market and buy some vegetable."
{"full_response": "Nice, what did you end up making with them? Just a small note — for things that happened yesterday, we say 'I went to the market and bought some vegetables.'", "advice": "Just a small note — for things that happened yesterday, we say 'I went to the market and bought some vegetables.'"}
---
Student: "My favorite hobby is play guitar."
{"full_response": "That's a great hobby, how long have you been playing? One quick correction — it should be 'My favorite hobby is playing guitar.'", "advice": "One quick correction — it should be 'My favorite hobby is playing guitar.'"}
---
Student: "What do you think about the current government and the election?"
{"full_response": "That's not something I can chat about here, let's keep things light! Tell me, what do you usually do on your weekends?", "advice": ""}
---
Student: "I am living in this city since five years and I like it very much."
{"full_response": "That's wonderful, what do you like most about it? Almost there — we'd say 'I have been living in this city for five years.'", "advice": "Almost there — we'd say 'I have been living in this city for five years.'"}
---

Always remain in character as Mrs. Linton. Never mention that you are an AI, a language model, or that you are following instructions."""
)


class OpenRouterLLM:
    """
    Shared LLM completion + per-session memory for backends that use
    OpenRouter chat completions.

    The per-session message history model mirrors inference-engine/server.py:
    a dict of lists keyed by ``session_id``, each list containing OpenAI-style
    ``{"role": "user"|"assistant", "content": str}`` dicts, protected by an
    ``asyncio.Lock``.

    Callers (OpenRouterBackend, VastServerlessTTSBackend) compose with this
    class rather than duplicating the LLM logic and memory model.
    """

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
    ):
        self.api_key = api_key
        self.model = model or os.getenv(
            "OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct"
        )

        self._sessions: Dict[str, List[dict]] = {}
        self._lock = asyncio.Lock()
        self._http: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def connect(self, session_id: str) -> None:
        """Initialise per-session history and the shared HTTP client."""
        async with self._lock:
            self._sessions[session_id] = []
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=30.0)

    async def generate(self, session_id: str, text: str) -> dict | None:
        """
        Send ``text`` + session history to OpenRouter and return a dict
        with ``full_response`` (str) and ``advice`` (str), or ``None`` on
        failure.
        """
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
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": 200,
                    "temperature": 0.7,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)
            return {
                "full_response": result.get("full_response", content),
                "advice": result.get("advice", ""),
            }

        except Exception as e:
            logger.exception(f"[{session_id}] OpenRouter LLM call failed: {e}")
            return None

    async def append_turn(
        self, session_id: str, user_text: str, result: dict
    ) -> None:
        """Persist one user+assistant exchange in the session history."""
        async with self._lock:
            sess = self._sessions.get(session_id)
            if sess is not None:
                sess.append({"role": "user", "content": user_text})
                sess.append({"role": "assistant", "content": result.get("full_response", "")})

    async def close_session(self, session_id: str) -> None:
        """Remove session history (called by the owning backend in close())."""
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def close_http(self) -> None:
        """Shut down the shared HTTP client."""
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _get_history(self, session_id: str) -> List[dict]:
        async with self._lock:
            return list(self._sessions.get(session_id, []))
