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
        return OpenRouterBackend(api_key=api_key)

    elif mode == "vast_serverless_tts":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            logger.warning(
                f"[{session_id}] BACKEND_MODE=vast_serverless_tts but OPENROUTER_API_KEY is not set. "
                "Falling back to vast backend."
            )
            from .vast_backend import VastBackend
            return VastBackend()

        endpoint_name = os.getenv("VAST_SERVERLESS_ENDPOINT_NAME")
        if not endpoint_name:
            logger.warning(
                f"[{session_id}] BACKEND_MODE=vast_serverless_tts but "
                "VAST_SERVERLESS_ENDPOINT_NAME is not set. "
                "Falling back to vast backend."
            )
            from .vast_backend import VastBackend
            return VastBackend()

        from .vast_serverless_tts_backend import VastServerlessTTSBackend
        return VastServerlessTTSBackend(
            api_key=api_key,
            endpoint_name=endpoint_name,
        )

    else:
        raise ValueError(f"Unknown BACKEND_MODE: {mode}")
