```bash
#!/bin/bash

set -e

echo "========================================"
echo " AI Voice Assistant Vast.ai Setup"
echo "========================================"

cd /workspace

# ---------------------------------------
# Install system packages
# ---------------------------------------
echo "[1/9] Installing system packages..."

apt update && apt install -y \
    git \
    wget \
    curl \
    ffmpeg \
    build-essential \
    portaudio19-dev \
    python3-pip \
    python3-venv \
    libsndfile1

# ---------------------------------------
# Install Miniconda
# ---------------------------------------
echo "[2/9] Installing Miniconda..."

if [ ! -d "/workspace/miniconda3" ]; then
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

    bash Miniconda3-latest-Linux-x86_64.sh -b -p /workspace/miniconda3
fi

export PATH="/workspace/miniconda3/bin:$PATH"

source /workspace/miniconda3/etc/profile.d/conda.sh

# ---------------------------------------
# Create conda environment
# ---------------------------------------
echo "[3/9] Creating Python 3.11 environment..."

if ! conda env list | grep -q "voiceai"; then
    conda create -y -n voiceai python=3.11
fi

conda activate voiceai

# ---------------------------------------
# Go into project directory
# ---------------------------------------
echo "[4/9] Entering project directory..."

cd /workspace/ai-eng

# ---------------------------------------
# Upgrade pip
# ---------------------------------------
echo "[5/9] Upgrading pip..."

pip install --upgrade pip

# ---------------------------------------
# Install CUDA PyTorch
# ---------------------------------------
echo "[6/9] Installing CUDA PyTorch..."

pip install torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu121

# ---------------------------------------
# Install project dependencies
# ---------------------------------------
echo "[7/9] Installing dependencies..."

pip install \
    transformers \
    accelerate \
    sentencepiece \
    protobuf \
    fastapi \
    uvicorn \
    python-multipart \
    huggingface_hub \
    faster-whisper \
    soundfile \
    librosa \
    scipy \
    numpy \
    ffmpeg-python \
    omnivoice

# ---------------------------------------
# HuggingFace login
# ---------------------------------------
echo "[8/9] HuggingFace Login"
echo ""
echo "Paste your HuggingFace token below"
echo ""

huggingface-cli login

# ---------------------------------------
# Start backend server
# ---------------------------------------
echo "[9/9] Starting FastAPI server..."

uvicorn server:app --host 0.0.0.0 --port 8000
```
