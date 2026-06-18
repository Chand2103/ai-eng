# Voice Agent Server - Notes and Investigation Results

## WebSocket Investigation Spike (REQUIRED BEFORE FULL BUILD)

### Purpose
Vast.ai's serverless routing uses a `/route/` endpoint that returns a worker URL + auth_data, then clients send direct POST requests to that worker. The PyWorker proxy validates and forwards requests. This architecture is designed for short HTTP request/response cycles. We need to verify if WebSocket upgrade requests are supported through this proxy layer.

### Echo Server Files Created
- `echo_server.py` - Minimal FastAPI WebSocket echo server
- `echo_Dockerfile` - Dockerfile using vastai/base-image
- `echo_requirements.txt` - Minimal dependencies
- `echo_test_client.py` - Test client for WebSocket validation

### Deployment Steps (User Action Required)

1. **Build the echo server image:**
   ```bash
   docker build -f echo_Dockerfile -t echo-server:latest .
   ```

2. **Push to a registry** (Docker Hub, GHCR, or Vast's registry if supported)

3. **Deploy to Vast.ai Serverless:**
   - Follow https://docs.vast.ai/documentation/serverless/getting-started-with-serverless
   - Use custom template pointing to your echo-server image
   - Ensure the template exposes port 8000
   - Note the endpoint URL provided by Vast

4. **Test the connection:**
   ```bash
   # First, test the health endpoint to verify deployment
   curl https://your-vast-endpoint/health
   
   # Then test WebSocket through Vast's routing
   python echo_test_client.py --url wss://your-vast-endpoint/ws/echo --idle 120
   ```

### What to Test and Record

1. **WebSocket Handshake:** Does the connection upgrade succeed through Vast's routing?
   - Expected: Connection established without error
   - Failure mode: Connection refused, 404, or timeout during upgrade

2. **Echo Functionality:** Does the first message get echoed back correctly?
   - Expected: Binary message sent = binary message received
   - Failure mode: No response, corrupted data, or connection drops

3. **Idle Timeout:** Does the connection survive 2+ minutes of inactivity?
   - Expected: Connection stays alive, second message after idle succeeds
   - Failure mode: Connection closed during idle period (note the close code and reason)

4. **Connection Duration:** Can the connection stay open for a realistic voice session (5-10 minutes)?
   - Test with longer idle periods if the 2-minute test passes
   - Send periodic messages to simulate bursty voice traffic

### Expected Outcomes and Decision Matrix

| Outcome | Next Step | Connection Architecture |
|---------|-----------|------------------------|
| WebSocket works through `/route/` proxy, no idle timeout | Use Vast's standard routing with WebSocket | Frontend → Vast `/route/` → PyWorker → Worker WebSocket |
| WebSocket works but has enforced idle timeout < 2min | Use Vast's routing with keep-alive pings | Same as above, add ping/pong keep-alive |
| WebSocket handshake fails through proxy | Use direct worker connectivity | Frontend gets direct worker URL/IP, bypasses `/route/` proxy |
| Connection drops after short idle (< 30s) | Use direct worker connectivity | Bypass proxy entirely |

### Direct Worker Connectivity (Fallback Plan)

If WebSocket-through-proxy fails, Vast exposes direct instance connectivity for SSH/Jupyter. We may be able to:
- Get the direct worker instance URL/IP+port from Vast's API
- Expose the WebSocket server directly on that port
- Frontend connects directly to the worker once assigned

This bypasses the PyWorker proxy entirely but requires:
- Verifying Vast allows custom port exposure for serverless workers
- Implementing our own session assignment logic
- Potentially different security model (no PyWorker validation)

### Investigation Status
⏳ **PENDING** - Waiting for Vast.ai deployment and test results

---

## Production Build Instructions (After Investigation Complete)

### Docker Build with HF Token Secret

The production Dockerfile will download gated HF models at build time using BuildKit secrets:

```bash
# Set your HF token as environment variable
export HF_TOKEN=your_huggingface_token_here

# Build with secret mount
docker build --secret id=hf_token,env=HF_TOKEN -t voice-agent:latest .
```

### Local Testing with GPU

```bash
# Run with GPU access
docker run --gpus all -p 8000:8000 voice-agent:latest

# Test health endpoint
curl http://localhost:8000/health

# Test with audio file
python test_client.py --url ws://localhost:8000/ws/test --audio sample.wav
```

### Model Paths and Environment Variables

The production Dockerfile will set these to point to baked-in models:

```bash
# LLM
LLM_MODEL_PATH=/models/llama-3.1-8b-instruct

# STT  
WHISPER_MODEL_NAME=small.en
WHISPER_DOWNLOAD_ROOT=/models/whisper

# TTS
OMNIVOICE_MODEL_PATH=/models/omnivoice
HF_HUB_OFFLINE=1
```

For local development (without baked models), these default to HF repo IDs:
- `LLM_MODEL_PATH=meta-llama/Llama-3.1-8B-Instruct`
- `WHISPER_MODEL_NAME=small.en` (downloads to cache)
- `OMNIVOICE_MODEL_PATH=k2-fsa/OmniVoice` (downloads to cache)

---

## Concurrency Model

Each worker handles **one active voice session at a time**. The autoscaler creates additional GPU workers for concurrent users rather than multiplexing multiple sessions onto one GPU.

**Key implications:**
- No request queue or batching logic needed
- Session state is simple dict keyed by session_id
- Worker can be reused for sequential sessions (state cleanup on disconnect)
- No shared mutable state across sessions

See `server.py` for implementation details.
