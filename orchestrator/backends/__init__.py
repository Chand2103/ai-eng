import os
import logging

from .base import ConversationBackend

logger = logging.getLogger(__name__)


def create_backend(session_id: str) -> ConversationBackend:
    mode = os.getenv("BACKEND_MODE", "vast")

    if mode == "vast":
        from .vast_backend import VastBackend
        return VastBackend()

    elif mode == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            logger.warning(
                f"[{session_id}] BACKEND_MODE=openrouter but OPENROUTER_API_KEY is not set. "
                "Falling back to vast backend."
            )
            from .vast_backend import VastBackend
            return VastBackend()

        from .openrouter_backend import OpenRouterBackend
        return OpenRouterBackend(
            api_key=api_key,
        )

    else:
        raise ValueError(f"Unknown BACKEND_MODE: {mode}")
