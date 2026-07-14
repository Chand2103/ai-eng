import os
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent

try:
    from .backends import create_backend  # when imported as part of the package
except ImportError:
    from backends import create_backend   # when run directly as a script

# Load environment variables from .env file
load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AWS Transcribe Streaming Handler
# ---------------------------------------------------------------------------
class TranscriptionResultHandler(TranscriptResultStreamHandler):
    """Custom handler to capture transcription results in real-time."""

    def __init__(self, transcript_result_stream):
        super().__init__(transcript_result_stream)
        self.transcript = ""

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        """Process transcript events as they arrive from AWS."""
        results = transcript_event.transcript.results
        for result in results:
            for alt in result.alternatives:
                text = alt.transcript
                logger.info(f"Transcript event: {text} (is_partial={result.is_partial})")
                
                # Only update on final results (not partial)
                if not result.is_partial:
                    self.transcript += text + " "


# ---------------------------------------------------------------------------
# FastAPI lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Orchestrator starting up.")
    yield
    logger.info("Orchestrator shutting down.")


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
    """Return 200 if orchestrator is ready."""
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# AWS Transcribe streaming helper
# ---------------------------------------------------------------------------
async def transcribe_stream_realtime(pcm_queue: asyncio.Queue) -> str:
    """
    Stream PCM chunks to AWS Transcribe in real-time as they arrive.
    Receives chunks from pcm_queue, sends to AWS, collects transcript.
    """
    try:
        # Initialize streaming client
        client = TranscribeStreamingClient(
            region=os.getenv("AWS_REGION", "us-east-1")
        )

        # Start streaming transcription
        logger.info("Starting AWS Transcribe streaming...")
        stream = await client.start_stream_transcription(
            language_code="en-US",
            media_sample_rate_hz=16000,
            media_encoding="pcm",
        )

        # Create handler to capture results
        handler = TranscriptionResultHandler(stream.output_stream)

        async def send_audio_chunks():
            """Send PCM chunks to AWS stream as they arrive in queue."""
            try:
                while True:
                    chunk = await pcm_queue.get()
                    
                    # None signals end of audio
                    if chunk is None:
                        logger.info("End-of-audio received, closing stream.")
                        await stream.input_stream.end_stream()
                        break
                    
                    await stream.input_stream.send_audio_event(audio_chunk=chunk)
                    logger.info(f"Sent {len(chunk)} bytes to AWS Transcribe.")
            except Exception as e:
                logger.exception(f"Error sending audio chunks: {e}")

        # Gather both sending and handling events concurrently
        await asyncio.gather(
            send_audio_chunks(),
            handler.handle_events(),
        )

        transcript = handler.transcript.strip()
        logger.info(f"Transcription complete: {transcript}")
        return transcript

    except Exception as e:
        logger.exception(f"Error during AWS Transcribe streaming: {e}")
        return ""


# ---------------------------------------------------------------------------
# WebSocket orchestrator pipeline
# ---------------------------------------------------------------------------
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info(f"[{session_id}] Frontend connected to orchestrator.")

    backend = create_backend(session_id)

    try:
        await backend.connect(session_id)
        asyncio.create_task(backend.warmup())

        # Main loop: handle multiple recording sessions
        while True:
            logger.info(f"[{session_id}] Waiting for first PCM chunk from frontend...")
            first_chunk_received = False
            pcm_queue: asyncio.Queue = asyncio.Queue()
            transcription_task = None

            # Receive PCM chunks from frontend
            while True:
                try:
                    pcm_chunk = await websocket.receive_bytes()

                    # Empty chunk or very small chunk = end of audio
                    if not pcm_chunk or len(pcm_chunk) < 16:
                        logger.info(f"[{session_id}] Received end-of-audio marker.")

                        if first_chunk_received and transcription_task:
                            # Queue-monitoring approach: wait for transcription stream to drain remaining chunks
                            logger.info(f"[{session_id}] Monitoring queue for pending chunks...")
                            start_drain = time.time()
                            drain_window = 0.3  # 300ms max drain time
                            last_queue_size = pcm_queue.qsize()

                            while time.time() - start_drain < drain_window:
                                await asyncio.sleep(0.05)  # Check every 50ms
                                current_size = pcm_queue.qsize()
                                if current_size == last_queue_size and current_size == 0:
                                    # Queue stable and empty - all chunks processed
                                    logger.info(f"[{session_id}] Queue drained, signaling end-of-audio.")
                                    break
                                last_queue_size = current_size
                            else:
                                logger.info(f"[{session_id}] Drain timeout after 300ms, proceeding with end-of-audio.")

                            # Signal end of audio to transcription task
                            await pcm_queue.put(None)
                            logger.info(f"[{session_id}] Waiting for transcription to complete...")
                            transcript_text = await transcription_task

                            if not transcript_text:
                                logger.warning(f"[{session_id}] No speech detected or transcription failed.")
                                await websocket.send_text("[no speech detected]")
                            else:
                                logger.info(f"[{session_id}] Transcript: {transcript_text}")
                                async for result in backend.send_transcript(transcript_text):
                                    if isinstance(result, bytes):
                                        logger.info(f"[{session_id}] Forwarding {len(result)} bytes of TTS audio to frontend.")
                                        await websocket.send_bytes(result)
                                    elif isinstance(result, str):
                                        logger.info(f"[{session_id}] Forwarding message from backend: {result}")
                                        await websocket.send_text(result)
                        else:
                            logger.warning(f"[{session_id}] End-of-audio without any audio chunks received.")

                        break  # Break inner loop to wait for next recording session

                    # First chunk received - lazy start transcription
                    if not first_chunk_received:
                        logger.info(f"[{session_id}] First chunk received, starting AWS Transcribe streaming...")
                        first_chunk_received = True
                        # Start transcription task only now
                        transcription_task = asyncio.create_task(transcribe_stream_realtime(pcm_queue))

                    logger.info(f"[{session_id}] Received {len(pcm_chunk)} bytes of PCM from frontend.")
                    # Put chunk in queue for transcription
                    await pcm_queue.put(pcm_chunk)

                except WebSocketDisconnect:
                    logger.info(f"[{session_id}] Frontend disconnected.")
                    if first_chunk_received and transcription_task:
                        # Signal end of audio
                        await pcm_queue.put(None)
                    return

    except WebSocketDisconnect:
        logger.info(f"[{session_id}] Frontend disconnected.")
    except Exception as e:
        logger.exception(f"[{session_id}] Unhandled WebSocket error: {e}")
        try:
            await websocket.close(reason=f"orchestrator error: {e}")
        except Exception:
            pass
    finally:
        await backend.close()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("ORCHESTRATOR_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
