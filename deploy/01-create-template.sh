#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Deploy the inference-engine TTS server to Vast.ai serverless.
#
# Prerequisites:
#   1. Docker image pushed to a registry (Docker Hub, GHCR, etc.)
#   2. Vast CLI installed and logged in (`vastai set api-key ...`)
#   3. HF_TOKEN available for gated model downloads
#
# Usage:
#   export DOCKER_IMAGE=your-registry/inference-tts:latest
#   export VAST_API_KEY=your_vast_api_key
#   export HF_TOKEN=your_huggingface_token
#
#   bash deploy/01-create-template.sh
#   bash deploy/02-create-endpoint.sh
#   bash deploy/03-create-workergroup.sh
#
# Environment variables:
#   DOCKER_IMAGE       (required)  Docker image tag
#   VAST_API_KEY       (required)  Vast.ai API key
#   HF_TOKEN           (required)  HuggingFace token for gated models
#   TEMPLATE_NAME                 Vast template name   (default: inference-tts)
#   ENDPOINT_NAME                 Vast endpoint name   (default: inference-tts-ep)
#   WORKERGROUP_NAME              Worker group name    (default: inference-tts-wg)
#   MIN_LOAD                      Minimum load         (default: 1)
#   TARGET_UTIL                   Target utilisation   (default: 90)
#   COLD_MULT                     Cold multiplier      (default: 0.6)
#   COLD_WORKERS                  Cold workers         (default: 1)
#   MAX_WORKERS                   Max workers          (default: 5)
#   SEARCH_GPU                    GPU search pattern   (default: "RTX_4090|RTX_3090|A5000|A10")
#
# GPU tier rationale:
#   OmniVoice TTS needs ~2-4 GB VRAM.  We use a conservative 24 GB GPU
#   (RTX 3090/4090, A5000, A10) because those tiers are widely available
#   on Vast at low cost and give headroom for the PyTorch + OmniVoice
#   working set.  A smaller 8-12 GB card would likely suffice but is
#   less available on the spot market.
# ---------------------------------------------------------------------------
set -euo pipefail

: "${DOCKER_IMAGE:?Must set DOCKER_IMAGE}"
: "${VAST_API_KEY:?Must set VAST_API_KEY}"
: "${HF_TOKEN:?Must set HF_TOKEN}"

TEMPLATE_NAME="${TEMPLATE_NAME:-inference-tts}"
SEARCH_GPU="${SEARCH_GPU:-RTX_4090|RTX_3090|A5000|A10}"

echo "=== Creating Vast template: ${TEMPLATE_NAME} ==="

# Build command using vastai CLI
vastai create template "${TEMPLATE_NAME}" \
    --image "${DOCKER_IMAGE}" \
    --env "HF_TOKEN=${HF_TOKEN}" \
    --env "OMNIVOICE_MODEL_PATH=k2-fsa/OmniVoice" \
    --search_params "
        gpu_name=${SEARCH_GPU}
        cuda_vers>=12.1
        disk_space>=10
    " \
    --vcuda 8 \
    --vram 24

echo "=== Template created ==="
echo "Next: run 02-create-endpoint.sh"
