import os
import logging
from typing import AsyncIterator, Union

import websockets

from .base import ConversationBackend

logger = logging.getLogger(__name__)


class VastBackend(ConversationBackend):
    """Wraps the existing vast.ai inference-engine WebSocket protocol."""

    def __init__(self):
        self.url = os.getenv("VAST_SERVER_URL", "ws://localhost:10100/ws/orchestrator")
        self._ws = None

    async def connect(self, session_id: str) -> None:
        logger.info(f"[{session_id}] Connecting to vast.ai at {self.url}")
        self._ws = await websockets.connect(self.url)

    async def send_transcript(self, text: str) -> AsyncIterator[Union[bytes, str]]:
        text_bytes = text.encode("utf-8")
        packet = len(text_bytes).to_bytes(4, "little") + text_bytes
        await self._ws.send(packet)

        response = await self._ws.recv()
        if isinstance(response, bytes):
            yield response
        elif isinstance(response, str):
            yield response

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
