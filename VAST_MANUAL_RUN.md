# Running the Voice Agent on a Vast.ai Manual Instance (no Docker)

These steps let you iterate quickly on a rented Vast.ai GPU instance before you later build the Docker image for serverless.

## 1. Rent a manual instance on Vast.ai

- Go to **Console → Instances → Rent Instance** (or the "Rent" tab).
- Pick a GPU with enough VRAM for all three models. Suggested minimum:
  - **LLM**: Llama-3.1-8B-Instruct in float16 needs ~16 GB VRAM.
  - **STT**: faster-whisper `small.en` needs ~1–2 GB VRAM.
  - **TTS**: OmniVoice needs a few GB VRAM.
  - **Total**: rent an instance with at least **24 GB VRAM** (e.g. RTX 3090, RTX 4090, A5000, A10, or better).
- Choose an image that already has CUDA + Python, e.g. **PyTorch** or a Vast base image. Ubuntu 22.04 is fine.
- Make sure **SSH** is enabled and note the SSH command Vast gives you.

## 2. SSH into the instance with port forwarding

You need two terminals:

- **Terminal 1** — SSH into Vast **with port forwarding** so your laptop can reach the server:

```bash
ssh -p <port> root@<host> -L 8000:localhost:8000
```

The `-L 8000:localhost:8000` forwards port 8000 on your laptop to port 8000 on the Vast instance.

- **Terminal 2** — on your laptop, used to run the test client.

## 3. Install system dependencies

Inside Terminal 1 (on the Vast instance):

```bash
apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    ffmpeg \
    libsndfile1 \
    build-essential \
    python3-pip \
    python3-venv \
    libportaudio2
```

## 4. Clone or upload your code

Option A — clone from GitHub:

```bash
git clone https://github.com/Chand2103/ai-eng.git
cd ai-eng
```

Option B — upload from your local machine (run this on your laptop in Terminal 2):

```bash
scp -P <port> -r c:/dev/AI-eng/* root@<host>:/root/ai-eng/
```

## 5. Create a Python virtual environment

Inside Terminal 1:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

## 6. Install Python dependencies

Inside Terminal 1:

```bash
pip install -r requirements.txt
```

If you hit CUDA version mismatches, install PyTorch manually to match the instance's CUDA version. For CUDA 12.1:

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

## 7. Log in to Hugging Face

The Llama model is gated, so you need a token. Inside Terminal 1:

```bash
huggingface-cli login --token YOUR_HF_TOKEN
```

Or set it as an env var before running:

```bash
export HF_TOKEN=YOUR_HF_TOKEN
```

## 8. Run the server

Inside Terminal 1:

```bash
python server.py
```

You should see logs like:

```
Loading models at module import...
All models loaded.
Server starting up.
```

The first run will download the models to the Hugging Face cache (`~/.cache/huggingface/` and `~/.cache/whisper/`). This can take several minutes.

## 9. Test from your local machine

Make sure Terminal 1 is still running the server and the SSH tunnel is active.

In **Terminal 2 on your laptop**, run:

```bash
cd c:/dev/AI-eng
curl http://localhost:8000/health
python test_client.py --url ws://localhost:8000/ws/test --audio input1.wav --output response.wav
```

If it works, you will see:

```
Connecting to ws://localhost:8000/ws/test ...
Sending <N> bytes from input1.wav
Audio sent, waiting for response...
Saved <M> response bytes to response.wav
Round-trip latency: X.XXXs
```

You can then play `response.wav` to hear the AI's reply.

## 10. Iterate

If you change code, just re-upload the changed files and restart `python server.py`.

## Common issues

- **Out of memory**: Use a GPU with more VRAM, or for the LLM try `load_in_8bit=True` / `load_in_4bit=True` in `llm.py` (requires `bitsandbytes`).
- **CUDA mismatch**: Check `nvidia-smi` and `python -c "import torch; print(torch.version.cuda)"`, then reinstall PyTorch for that CUDA version.
- **Port not reachable / connection refused**: Make sure you used `-L 8000:localhost:8000` in your SSH command in Terminal 1, and that the server is already running on the instance.
- **Whisper / OmniVoice not found**: Confirm `faster-whisper` and `omnivoice` installed correctly from `requirements.txt`.

## Next step: Docker/serverless

Once this works, build the Docker image locally or on the instance and test the containerized version before pushing to Vast serverless.
