```bash
#!/bin/bash

echo "========================================"
echo " AI Voice Assistant Vast.ai Setup"
echo "========================================"

cd /workspace

# ---------------------------------------
# Install system packages
# ---------------------------------------
echo "[1/10] Installing system packages..."

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
echo "[2/10] Installing Miniconda..."

if [ ! -d "/workspace/miniconda3" ]; then
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

    bash Miniconda3-latest-Linux-x86_64.sh -b -p /workspace/miniconda3
fi

export PATH="/workspace/miniconda3/bin:$PATH"

source /workspace/miniconda3/etc/profile.d/conda.sh

# ---------------------------------------
# Create Python 3.11 environment
# ---------------------------------------
echo "[3/10] Creating Python 3.11 environment..."

conda create -y -n voiceai python=3.11

conda activate voiceai

# ---------------------------------------
# Clone repo
# ---------------------------------------
echo "[4/10] Cloning repository..."

cd /workspace

if [ ! -d "ai-eng" ]; then
    git clone https://github.com/Chand2103/ai-eng.git
fi

cd ai-eng

# ---------------------------------------
# Upgrade pip
# ---------------------------------------
echo "[5/10] Upgrading pip..."

pip install --upgrade pip

# ---------------------------------------
# Install CUDA PyTorch
# ---------------------------------------
echo "[6/10] Installing PyTorch CUDA..."

pip install torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu121

# ---------------------------------------
# Install project dependencies
# ---------------------------------------
echo "[7/10] Installing dependencies..."

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
echo "[8/10] HuggingFace Login"
echo ""
echo "Paste your HuggingFace token below"
echo ""

huggingface-cli login

# ---------------------------------------
# Verify CUDA
# ---------------------------------------
echo "[9/10] Checking CUDA..."

python -c "
import torch
print('CUDA Available:', torch.cuda.is_available())
print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')
"

# ---------------------------------------
# Start backend server
# ---------------------------------------
echo "[10/10] Starting FastAPI server..."

uvicorn server:app --host 0.0.0.0 --port 8000
```
