from abc import ABC, abstractmethod
from typing import AsyncIterator, Union


class ConversationBackend(ABC):
    """Abstract interface for a conversation backend (LLM + TTS)."""

    @abstractmethod
    async def connect(self, session_id: str) -> None:
        """Open any persistent connections and initialise session state."""
        ...

    @abstractmethod
    async def send_transcript(self, text: str) -> AsyncIterator[Union[bytes, str]]:
        """
        Send the final transcript text to the backend.

        Yields ``bytes`` chunks of audio to forward to the frontend, or
        ``str`` error/info messages to forward as text.
        """
        ...
        yield  # pragma: no cover (mark generator)

    @abstractmethod
    async def close(self) -> None:
        """Tear down the session – close connections, clean up state."""
        ...
