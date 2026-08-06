"""
Prompt templates and configuration data for the conversation system.

Everything here is static prompt/config content — no application logic.
The orchestrator imports from this package so that system prompts and
supporting data stay separate from the runtime code.
"""

from .interviewer import INTERVIEWER_TEMPLATE, OPENING_LINE
from .evaluator import EVALUATOR_SYSTEM_PROMPT, evaluator_to_spoken
from .topic_category import TOPIC_CATEGORIES
from .roleplay_scenarios import ROLEPLAY_SCENARIOS

__all__ = [
    "INTERVIEWER_TEMPLATE",
    "OPENING_LINE",
    "EVALUATOR_SYSTEM_PROMPT",
    "evaluator_to_spoken",
    "TOPIC_CATEGORIES",
    "ROLEPLAY_SCENARIOS",
]
