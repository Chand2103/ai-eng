# syntax=docker/dockerfile:1

# Use Vast.ai's CUDA/cuDNN base image for host-side layer caching.
# This tag includes CUDA 12.8.1 + cuDNN + Ubuntu 22.04 with Python 3.10.
FROM vastai/base-image:cuda-12.8.1-cudnn-devel-ubuntu22.04-py310

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Install system dependencies for audio processing.
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    ffmpeg \
    libsndfile1 \
    build-essential \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Set working directory.
WORKDIR /app

# Install Python dependencies first so the layer can be cached.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# ---------------------------------------------------------------------------
# Bake model weights into the image at build time.
# ---------------------------------------------------------------------------
# IMPORTANT: Do NOT put large model files under /opt/workspace-internal/.
# Store them under /models/ and symlink only if another part of the setup
# expects a different location.
# ---------------------------------------------------------------------------

# LLM: meta-llama/Llama-3.1-8B-Instruct (gated model).
# Pass HF_TOKEN as a BuildKit secret so it is not baked into image layers.
RUN --mount=type=secret,id=hf_token \
    export HF_TOKEN=$(cat /run/secrets/hf_token) && \
    huggingface-cli login --token "$HF_TOKEN" && \
    python3 - <<'PY'
from transformers import AutoTokenizer, AutoModelForCausalLM
import os
model_id = "meta-llama/Llama-3.1-8B-Instruct"
out_path = "/models/llama-3.1-8b-instruct"
os.makedirs(out_path, exist_ok=True)
AutoTokenizer.from_pretrained(model_id, cache_dir=out_path)
AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="auto",
    torch_dtype="float16",
    low_cpu_mem_usage=True,
    cache_dir=out_path,
)
PY

# STT: faster-whisper small.en (or whatever WHISPER_MODEL_NAME is set to).
RUN python3 - <<'PY'
from faster_whisper import WhisperModel
import os
model_name = os.getenv("WHISPER_MODEL_NAME", "small.en")
download_root = "/models/whisper"
os.makedirs(download_root, exist_ok=True)
# Loading the model triggers a download if not already present.
WhisperModel(model_name, device="cuda", compute_type="float16", download_root=download_root)
PY

# TTS: OmniVoice k2-fsa/OmniVoice.
RUN python3 - <<'PY'
from omnivoice import OmniVoice
import torch
import os
model_id = "k2-fsa/OmniVoice"
out_path = "/models/omnivoice"
os.makedirs(out_path, exist_ok=True)
OmniVoice.from_pretrained(
    model_id,
    device_map="cuda:0",
    dtype=torch.float16,
    cache_dir=out_path,
)
PY

# Copy application code into the image.
COPY *.py /app/

# Environment variables so the server loads baked-in weights without network calls.
ENV HF_HUB_OFFLINE=1
ENV LLM_MODEL_PATH=/models/llama-3.1-8b-instruct
ENV WHISPER_MODEL_NAME=small.en
ENV WHISPER_DOWNLOAD_ROOT=/models/whisper
ENV OMNIVOICE_MODEL_PATH=/models/omnivoice
ENV PORT=8000

EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
