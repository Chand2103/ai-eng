#!/bin/bash
set -e

echo "=== System update + dependencies ==="
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



echo "=== Creating virtual environment ==="
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip

echo "=== Installing Python dependencies ==="
pip install -r requirements.txt

echo "=== Fixing PyTorch CUDA mismatch (cu124) ==="
pip uninstall -y torch torchvision torchaudio || true
pip cache purge || true

pip install torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu124

echo "=== Hugging Face login ==="
if [ -z "$HF_TOKEN" ]; then
    echo "HF_TOKEN not set. Export it first:"
    echo "export HF_TOKEN=your_token_here"
else
    hf auth login --token "$HF_TOKEN"
fi

echo "=== Setup complete ==="