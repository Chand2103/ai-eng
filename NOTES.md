# Voice Agent Server - Notes

## WebSocket Server

The FastAPI server (`server.py`) exposes a single persistent WebSocket endpoint:

```
/ws/{session_id}
```

Each connection gets its own conversation history stored in an in-memory dict keyed by `session_id`. The history is cleaned up when the connection closes (normal close, error, or timeout), so a worker can be reused for sequential sessions without leaking state.

### Pipeline per turn

1. Client sends raw audio bytes (e.g. a WAV file).
2. Server runs STT on the bytes in memory (`STT.transcribe_bytes`).
3. If speech is detected, the server runs the LLM with that session's history.
4. Server runs TTS on the response and returns WAV bytes.
5. Both turns are appended to that session's history.

Errors at each stage are logged and the session continues; one bad audio chunk does not kill the connection.

### Health endpoint

```
GET /health
```

Returns `200 {"status": "healthy"}` once all three models are loaded at module import time. Returns `503` if loading failed.

## Concurrency Assumption

Each GPU worker is expected to handle **one active voice session at a time**. The autoscaler creates additional GPU workers for additional concurrent users, so this app does **not** implement request queuing or batching. Session state is keyed by `session_id` and cleaned up on disconnect so a reused worker never leaks history between sessions.

## Local Development / Testing

Run the server locally (requires a CUDA GPU and the models will download on first run unless already cached):

```bash
pip install -r requirements.txt
python server.py
```

Test with the included client:

```bash
python test_client.py --url ws://localhost:8000/ws/test --audio input1.wav --output response.wav
```

## Docker Build

Build the production image with the gated HF model downloaded using a BuildKit secret:

```bash
export HF_TOKEN=your_huggingface_token_here
docker build --secret id=hf_token,env=HF_TOKEN -t voice-agent:latest .
```

## Docker Local Run

Run the built image locally with GPU access:

```bash
docker run --gpus all -p 8000:8000 voice-agent:latest
```

Then test:

```bash
curl http://localhost:8000/health
python test_client.py --url ws://localhost:8000/ws/test --audio input1.wav --output response.wav
```

## Model Paths

The Dockerfile bakes models under `/models/` and sets these environment variables:

```bash
LLM_MODEL_PATH=/models/llama-3.1-8b-instruct
WHISPER_MODEL_NAME=small.en
WHISPER_DOWNLOAD_ROOT=/models/whisper
OMNIVOICE_MODEL_PATH=/models/omnivoice
HF_HUB_OFFLINE=1
```

For local development without baked models, the classes fall back to Hugging Face repo IDs / default whisper model names.
