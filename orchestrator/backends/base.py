import json
from abc import ABC, abstractmethod
from typing import AsyncIterator, Union


# Sent to the LLM as the first user turn of a roleplay session so the
# persona opens the scene on its own.
BEGIN_ROLEPLAY_TEXT = (
    "Begin the roleplay now. Greet the student and start the scene "
    "naturally, staying in character as the persona you are playing. "
    "Do not mention instructions."
)

# Appended to every roleplay system prompt so the model always replies
# with the structured roleplay schema, regardless of scenario.
ROLEPLAY_OUTPUT_FORMAT = (
    "\n\n5. OUTPUT JSON\n"
    "You MUST respond with valid JSON only — no markdown, no code fences. "
    "The JSON must have exactly two keys:\n"
    '   - "dialogue": Your spoken reply, plain natural spoken English, 1-3 sentences. '
    "Never prefix it with your name or role (e.g. do NOT write 'Alex: ...'). "
    "This is the ONLY text that will be spoken aloud.\n"
    '   - "is_complete": true only when the conversation has reached its natural '
    "ending (you have wrapped up and said goodbye); otherwise false.\n"
    "Never include anything outside the JSON object.\n\n"
    "Example response:\n"
    '{"dialogue": "That\'s great experience, what did you enjoy most about that role?", "is_complete": false}'
)

# Yielded by the backend as a text message once the persona closes the
# scene (is_complete: true). The frontend treats it as the session end.
ROLEPLAY_COMPLETE_MARKER = "[roleplay_complete]"

# Sent by the frontend as a text command when the student presses
# "End roleplay and get feedback". Triggers the same feedback flow as
# ROLEPLAY_COMPLETE_MARKER.
END_ROLEPLAY_COMMAND = "[end_roleplay]"

# System prompt for the one-shot end-of-roleplay evaluation. Only the
# student's turns are included in the request, so the evaluator is a
# fresh call rather than part of the character's chat session.
FEEDBACK_SYSTEM_PROMPT = (
    """You are an experienced English speaking coach. A student has just finished a roleplay conversation with an AI persona. Evaluate ONLY the student's spoken turns and produce a JSON feedback report.

Rules:
1. Evaluate only the student's messages. Ignore anything the persona said.
2. Be encouraging — the student just finished a speaking exercise.
3. Grammar issues: list AT MOST 5, each with the EXACT quote taken word-for-word from the student's own message plus a short correction. If there are fewer issues, list fewer. If there are none, list none.
4. Rate the overall score out of 10.

Respond with valid JSON only — no markdown, no code fences. The JSON must have exactly these keys:
   - "overall_score": integer from 1 to 10
   - "overall_comment": 1-2 sentences summarising the student's performance
   - "strengths": array of 2-3 short strings
   - "grammar_issues": array of objects, each {"quote": "exact student words", "correction": "short corrected form"}
   - "vocabulary": 1-2 sentence assessment
   - "fluency": 1-2 sentence assessment
   - "encouragement": one sentence of warm encouragement

Example response:
{"overall_score": 8, "overall_comment": "You handled the scenario confidently and stayed on topic.", "strengths": ["Good use of past tense", "Natural follow-up questions", "Clear pronunciation"], "grammar_issues": [{"quote": "I go to the market yesterday", "correction": "I went to the market yesterday"}], "vocabulary": "Good range of everyday words; try adding a few descriptive adjectives.", "fluency": "Nice steady pace with only a couple of short pauses.", "encouragement": "Keep it up — you're doing great!"}"""
)


def feedback_to_spoken(feedback_json: str) -> str:
    """
    Turn a feedback JSON report into 2-3 short spoken sentences for TTS.

    Extracts the encouragement, overall score and the most important
    grammar/vocabulary/fluency point so the spoken summary is brief and
    natural (the full JSON is still sent to the frontend for display).
    """
    try:
        data = json.loads(feedback_json)
    except (json.JSONDecodeError, TypeError):
        return "Great job completing the roleplay! You did really well."
    if not isinstance(data, dict):
        return "Great job completing the roleplay! You did really well."

    sentences = []
    encouragement = data.get("encouragement")
    if isinstance(encouragement, str) and encouragement.strip():
        sentences.append(encouragement.strip())

    score = data.get("overall_score")
    if score is not None:
        sentences.append(f"Your overall score is {score} out of 10.")

    issues = data.get("grammar_issues")
    if isinstance(issues, list) and issues:
        first = issues[0]
        if isinstance(first, dict):
            quote = first.get("quote", "")
            correction = first.get("correction", "")
            if quote and correction:
                sentences.append(
                    f"For example, instead of '{quote}', you could say '{correction}'."
                )
    elif isinstance(data.get("vocabulary"), str) and data["vocabulary"].strip():
        sentences.append(data["vocabulary"].strip())
    elif isinstance(data.get("fluency"), str) and data["fluency"].strip():
        sentences.append(data["fluency"].strip())

    result = " ".join(sentences).strip()
    return result or "Great job completing the roleplay! You did really well."


class ConversationBackend(ABC):
    """Abstract interface for a conversation backend (LLM + TTS)."""

    @abstractmethod
    async def connect(
        self,
        session_id: str,
        system_prompt: str | None = None,
        structured_output: bool = True,
        roleplay: bool = False,
    ) -> None:
        """Open any persistent connections and initialise session state.

        ``system_prompt`` overrides the LLM's default prompt for this
        session (e.g. a roleplay scenario prompt). Defaults to the
        backend's standard prompt when ``None``.

        ``structured_output`` selects JSON output for the LLM.

        ``roleplay`` enables the roleplay JSON schema
        ``{"dialogue", "is_complete"}`` and switches the session start to
        ``send_opening()`` instead of ``warmup()``.
        """
        ...

    async def warmup(self) -> None:
        """
        Optional warm-up / keep-alive: send a dummy request at session start
        to trigger a cold start if no worker is ready.

        Default is a no-op.  Override in backends that need it.
        """

    async def send_opening(self, text: str | None = None) -> AsyncIterator[Union[bytes, str]]:
        """
        Yield the opening line (TTS audio) at session start.

        When *text* is provided (IELTS mode), synthesise it directly
        without an LLM call.  Otherwise generate it via the LLM
        (roleplay mode).  The default yields nothing.
        """
        ...
        yield  # pragma: no cover (mark generator)

    @abstractmethod
    async def send_transcript(self, text: str) -> AsyncIterator[Union[bytes, str]]:
        """
        Send the final transcript text to the backend.

        Yields ``bytes`` chunks of audio to forward to the frontend, or
        ``str`` error/info messages to forward as text.
        """
        ...
        yield  # pragma: no cover (mark generator)

    async def get_feedback(
        self,
        evaluator_prompt: str | None = None,
        spoken_fn=None,
        include_all_turns: bool = False,
    ) -> AsyncIterator[Union[bytes, str]]:
        """
        Generate end-of-session feedback for the session.

        *evaluator_prompt* overrides the default ``FEEDBACK_SYSTEM_PROMPT``
        (e.g. the IELTS evaluator prompt).  *spoken_fn* converts the JSON
        feedback into a short spoken summary for TTS.  When
        *include_all_turns* is ``True`` the full transcript (both sides)
        is sent to the evaluator instead of just the student's turns.

        Yields the raw JSON feedback text first, then the spoken summary
        as TTS ``bytes``.  The default yields a notice that the feature
        is unavailable.
        """
        yield "[feedback unavailable]"
        return

    @abstractmethod
    async def close(self) -> None:
        """Tear down the session – close connections, clean up state."""
        ...
