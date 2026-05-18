#!/bin/bash

echo "Starting Voice AI System..."

# activate venv
source venv/bin/activate

echo "Checking dependencies..."
if ! python -c "import torch" 2>/dev/null; then
    echo "⚠️ Environment not ready, running setup..."
    bash setup.sh
    source venv/bin/activate
fi

echo "Preloading models (first run may download)..."

# OPTIONAL: preload LLM silently (starts download early)
python -c "
from transformers import AutoTokenizer, AutoModelForCausalLM
print('Downloading/checking LLM...')
AutoTokenizer.from_pretrained('meta-llama/Llama-3.1-8B-Instruct')
AutoModelForCausalLM.from_pretrained(
    'meta-llama/Llama-3.1-8B-Instruct',
    device_map='auto',
    torch_dtype='float16'
)
print('LLM ready')
"

echo "Starting main app..."
python main.py