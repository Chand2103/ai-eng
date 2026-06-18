import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from stt import STT
from llm import LLM
from tts import TTS

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------
# Models are instantiated once at module load time and shared across all
# sessions. They are stateless with respect to conversation history; per-
# session state is stored in `sessions` below.
# ---------------------------------------------------------------------------
logger.info("Loading models at module import...")
stt_model = STT()
llm_model = LLM()
tts_model = TTS()
logger.info("All models loaded.")

# ---------------------------------------------------------------------------
# Per-session state
# ---------------------------------------------------------------------------
# CONCURRENCY ASSUMPTION:
# Each GPU worker is expected to handle one active voice session at a time.
# The Vast.ai autoscaler spins up additional workers for additional concurrent
# users, so this app does NOT implement request queuing or batching. However,
# a worker may be reused for sequential sessions, so we keep session state keyed
# by session_id and clean it up on disconnect to prevent state leakage.
# ---------------------------------------------------------------------------
sessions: Dict[str, Dict] = {}
session_lock = asyncio.Lock()


async def get_history(session_id: str) -> List[dict]:
    async with session_lock:
        return list(sessions.get(session_id, {}).get("history", []))


async def append_turn(session_id: str, user_text: str, assistant_text: str) -> None:
    async with session_lock:
        sess = sessions.setdefault(session_id, {"history": []})
        sess["history"].append({"role": "user", "content": user_text})
        sess["history"].append({"role": "assistant", "content": assistant_text})


async def remove_session(session_id: str) -> None:
    async with session_lock:
        sessions.pop(session_id, None)


# ---------------------------------------------------------------------------
# FastAPI lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Models are already loaded at module import; this lifespan simply confirms
    # they are present before reporting the app as healthy.
    logger.info("Server starting up.")
    yield
    logger.info("Server shutting down.")


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    """Return 200 only once all three models are loaded."""
    if stt_model is None or llm_model is None or tts_model is None:
        return {"status": "not_ready"}, 503
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# WebSocket voice pipeline
# ---------------------------------------------------------------------------
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info(f"[{session_id}] WebSocket connected.")

    # Initialize session history (empty on every new connection)
    async with session_lock:
        sessions[session_id] = {"history": []}

    try:
        while True:
            # 1. Receive audio bytes from the client
            audio_bytes = await websocket.receive_bytes()
            logger.info(f"[{session_id}] Received {len(audio_bytes)} audio bytes.")

            if not audio_bytes:
                logger.warning(f"[{session_id}] Empty audio chunk received, skipping.")
                continue

            # 2. STT
            try:
                text = stt_model.transcribe_bytes(audio_bytes)
            except Exception as e:
                logger.exception(f"[{session_id}] STT failed: {e}")
                await websocket.send_text(f"[STT error: {e}]")
                continue

            if not text:
                logger.info(f"[{session_id}] No speech detected, skipping turn.")
                await websocket.send_text("[no speech detected]")
                continue

            logger.info(f"[{session_id}] Transcription: {text}")

            # 3. LLM (with this session's history)
            try:
                history = await get_history(session_id)
                response = llm_model.generate(text, history=history)
            except Exception as e:
                logger.exception(f"[{session_id}] LLM generation failed: {e}")
                await websocket.send_text(f"[LLM error: {e}]")
                continue

            logger.info(f"[{session_id}] AI: {response}")

            # 4. TTS
            try:
                wav_bytes = tts_model.synthesize_for_session(
                    session_id=session_id,
                    text=response,
                    return_wav_bytes=True,
                )
            except Exception as e:
                logger.exception(f"[{session_id}] TTS failed: {e}")
                await websocket.send_text(f"[TTS error: {e}]")
                continue

            logger.info(
                f"[{session_id}] TTS produced {len(wav_bytes)} bytes of audio."
            )

            # 5. Send audio back
            await websocket.send_bytes(wav_bytes)

            # 6. Update session history
            await append_turn(session_id, text, response)

    except WebSocketDisconnect:
        logger.info(f"[{session_id}] Client disconnected.")
    except Exception as e:
        logger.exception(f"[{session_id}] Unhandled WebSocket error: {e}")
        try:
            await websocket.close(reason=f"server error: {e}")
        except Exception:
            pass
    finally:
        await remove_session(session_id)
        logger.info(f"[{session_id}] Session state cleaned up.")


if __name__ == "__main__":
    import uvicorn

port = int(os.getenv("PORT", "10100"))  # use exposed Vast port
uvicorn.run(app, host="0.0.0.0", port=port)
