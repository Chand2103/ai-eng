#!/bin/bash

echo "🔧 Setting up environment..."

# create venv if not exists
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

source venv/bin/activate

echo "📦 Installing dependencies..."

pip install --upgrade pip

pip install faster-whisper
pip install transformers
pip install torch
pip install sounddevice soundfile numpy

echo "✅ Setup complete!"