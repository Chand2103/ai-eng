"""
Thin FastAPI server exposing the inference-engine TTS model over HTTP.

Used by the Vast.ai serverless PyWorker.  Only OmniVoice is loaded (no LLM,
no STT), making cold starts faster and memory usage lower than the full
inference-engine/server.py WebSocket server.

Endpoints
---------
GET  /health          → {"status": "healthy"}
POST /tts             → WAV bytes (audio/wav)
"""

import os
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

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
# Model (loaded once at import)
# ---------------------------------------------------------------------------
logger.info("Loading OmniVoice TTS model...")
tts_model = TTS()
logger.info("OmniVoice loaded.")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Inference-Engine TTS (serverless)")


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class TTSRequest(BaseModel):
    text: str
    ref_audio: str | None = None
    ref_text: str | None = None
    voice_id: int | None = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    if tts_model is None:
        return JSONResponse({"status": "not_ready"}, status_code=503)
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# TTS endpoint
# ---------------------------------------------------------------------------
@app.post("/tts")
async def synthesize(req: TTSRequest):
    """
    Synthesise speech from ``text`` using the OmniVoice TTS model.

    The request body mirrors ``TTS.synthesize()`` parameter names exactly:

    - ``text`` (required) — text to speak
    - ``ref_audio`` (optional) — path or identifier for the reference voice
    - ``ref_text`` (optional) — transcript of the reference audio
    - ``voice_id`` (optional) — select from the built-in voice registry
      (1 = Alice, 2 = …).  When set, overrides *ref_audio* / *ref_text*.

    Returns WAV bytes (``audio/wav``, 16-bit mono, 24 kHz).
    """
    try:
        wav_bytes = tts_model.synthesize(
            text=req.text,
            ref_audio=req.ref_audio or "ref-aud.wav",
            ref_text=req.ref_text or "Hi, This is alice, how are you doing today?",
            voice_id=req.voice_id,
            return_wav_bytes=True,
        )
        return Response(content=wav_bytes, media_type="audio/wav")
    except Exception as e:
        logger.exception(f"TTS synthesis failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# Entrypoint (for direct testing without the PyWorker)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("TTS_SERVER_PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
