import json
import os
import asyncio
import logging
from typing import Dict, List

import httpx

from .base import FEEDBACK_SYSTEM_PROMPT

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
        self.model = (
            model
            or os.getenv("OPENROUTER_LLM_MODEL")
            or os.getenv("OPENROUTER_MODEL")
            or "google/gemini-3-flash-preview"
        )

        self._sessions: Dict[str, List[dict]] = {}
        self._system_prompts: Dict[str, str] = {}
        self._structured_output: Dict[str, bool] = {}
        self._roleplay: Dict[str, bool] = {}
        self._lock = asyncio.Lock()
        self._http: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def connect(
        self,
        session_id: str,
        system_prompt: str | None = None,
        structured_output: bool = True,
        roleplay: bool = False,
    ) -> None:
        """Initialise per-session history and the shared HTTP client.

        ``system_prompt`` overrides the default Free Talk prompt for this
        session (e.g. a roleplay scenario prompt). Defaults to SYSTEM_PROMPT.

        ``structured_output`` enables ``response_format: json_object`` and
        parses ``{"full_response", "advice"}``.

        ``roleplay`` switches the JSON parsing to the roleplay schema
        ``{"dialogue", "is_complete"}``.  ``dialogue`` becomes
        ``full_response`` (the spoken text) and ``is_complete`` is surfaced
        so the backend can end the session when the scenario concludes.
        """
        async with self._lock:
            self._sessions[session_id] = []
            self._system_prompts[session_id] = system_prompt or SYSTEM_PROMPT
            self._structured_output[session_id] = structured_output
            self._roleplay[session_id] = roleplay
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=30.0)

    async def generate(self, session_id: str, text: str) -> dict | None:
        """
        Send ``text`` + session history to OpenRouter and return a dict
        with ``full_response`` (str) and ``advice`` (str), or ``None`` on
        failure.

        Retries once if the model returns an empty JSON object — a known
        failure mode of small models in ``response_format: json_object``
        mode (e.g. llama-3.1-8b-instruct replying with ``{}``).
        """
        for attempt in range(2):
            result = await self._generate_once(session_id, text)
            if result is not None:
                return result
            logger.warning(f"[{session_id}] LLM returned empty output, retrying ({attempt + 1}/2)...")
        logger.error(f"[{session_id}] LLM returned empty output on both attempts.")
        return None

    async def _generate_once(self, session_id: str, text: str) -> dict | None:
        try:
            history = await self._get_history(session_id)
            messages = [{"role": "system", "content": self._get_system_prompt(session_id)}]
            messages.extend(history)
            messages.append({"role": "user", "content": text})

            structured = self._is_structured_output(session_id)
            roleplay = self._is_roleplay(session_id)
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 200,
                "temperature": 0.7,
            }
            if structured:
                payload["response_format"] = {"type": "json_object"}

            response = await self._http.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            if not content or not content.strip():
                return None

            if not structured:
                # Legacy plain-text mode (no longer used by roleplays).
                return {"full_response": content.strip(), "advice": "", "is_complete": False}

            try:
                result = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                # Model returned plain text instead of JSON — use it as-is.
                return {"full_response": content.strip(), "advice": "", "is_complete": False}

            if not isinstance(result, dict):
                return {"full_response": content.strip(), "advice": "", "is_complete": False}

            if roleplay:
                full_response = (
                    result.get("dialogue") or result.get("full_response") or result.get("content") or ""
                )
                advice = ""
                is_complete = _to_bool(result.get("is_complete", False))
            else:
                full_response = result.get("full_response") or result.get("content") or ""
                advice = result.get("advice") or ""
                is_complete = False

            if not isinstance(full_response, str):
                full_response = ""
            if not isinstance(advice, str):
                advice = ""
            full_response = full_response.strip()
            advice = advice.strip()

            if not full_response:
                # Valid JSON but empty (e.g. `{}` or nested empty object).
                return None

            return {
                "full_response": full_response,
                "advice": advice,
                "is_complete": is_complete,
            }

        except Exception as e:
            logger.exception(f"[{session_id}] OpenRouter LLM call failed: {e}")
            return None

    async def generate_feedback(self, session_id: str) -> tuple[str | None, str | None]:
        """
        One-shot end-of-roleplay evaluation of the student's turns.

        Runs a fresh chat completion with ``FEEDBACK_SYSTEM_PROMPT`` and only
        the student's messages from this session (no persona turns, no
        character system prompt).

        Returns ``(feedback_json, None)`` on success, or ``(None, reason)``
        where ``reason`` is ``"no transcript"`` if there were no student
        turns, or ``"LLM error: ..."`` if the call failed.
        """
        history = await self._get_history(session_id)
        user_turns = [
            turn.get("content", "")
            for turn in history
            if turn.get("role") == "user" and turn.get("content")
        ]
        if not user_turns:
            return None, "no transcript"

        transcript = "\n".join(f"Student: {turn}" for turn in user_turns)
        if self._http is None:
            return None, "LLM error: connection not initialised"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": FEEDBACK_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Evaluate the student's turns below and return your "
                        f"JSON feedback report.\n\n{transcript}"
                    ),
                },
            ],
            "max_tokens": 1000,
            "temperature": 0.4,
            "response_format": {"type": "json_object"},
        }

        try:
            response = await self._http.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            if not content or not content.strip():
                return None, "LLM error: empty response"
            content = content.strip()

            # Validate it is JSON, salvaging a JSON object embedded in the
            # text (e.g. markdown fences) rather than discarding the reply.
            try:
                json.loads(content)
            except (json.JSONDecodeError, TypeError):
                start = content.find("{")
                end = content.rfind("}")
                if start == -1 or end <= start:
                    return None, "LLM error: invalid JSON"
                candidate = content[start : end + 1]
                try:
                    json.loads(candidate)
                except json.JSONDecodeError:
                    return None, "LLM error: invalid JSON"
                content = candidate

            return content, None

        except Exception as e:
            logger.exception(f"[{session_id}] OpenRouter feedback call failed: {e}")
            return None, f"LLM error: {e}"

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
            self._system_prompts.pop(session_id, None)
            self._structured_output.pop(session_id, None)
            self._roleplay.pop(session_id, None)

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

    def _get_system_prompt(self, session_id: str) -> str:
        return self._system_prompts.get(session_id, SYSTEM_PROMPT)

    def _is_structured_output(self, session_id: str) -> bool:
        return self._structured_output.get(session_id, True)

    def _is_roleplay(self, session_id: str) -> bool:
        return self._roleplay.get(session_id, False)


def _to_bool(value) -> bool:
    """Coerce a JSON value (bool/str/number) into a boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "y", "complete", "done")
    return False
