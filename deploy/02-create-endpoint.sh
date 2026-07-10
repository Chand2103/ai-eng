#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Create a Vast.ai serverless endpoint for the TTS worker.
#
# Prerequisites: 01-create-template.sh has been run.
#
# Environment variables:
#   ENDPOINT_NAME   (default: inference-tts-ep)
#   MIN_LOAD        (default: 1)
#   TARGET_UTIL     (default: 90)
#   COLD_MULT       (default: 0.6)
#   COLD_WORKERS    (default: 1)
#   MAX_WORKERS     (default: 5)
#   VAST_API_KEY    (required)
# ---------------------------------------------------------------------------
set -euo pipefail

: "${VAST_API_KEY:?Must set VAST_API_KEY}"

ENDPOINT_NAME="${ENDPOINT_NAME:-inference-tts-ep}"
MIN_LOAD="${MIN_LOAD:-1}"
TARGET_UTIL="${TARGET_UTIL:-90}"
COLD_MULT="${COLD_MULT:-0.6}"
COLD_WORKERS="${COLD_WORKERS:-1}"
MAX_WORKERS="${MAX_WORKERS:-5}"

echo "=== Creating endpoint: ${ENDPOINT_NAME} ==="

curl -s -X POST "https://console.vast.ai/api/v0/endptjobs/" \
    -H "Authorization: Bearer ${VAST_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "$(cat <<EOF
{
    "endpoint_name": "${ENDPOINT_NAME}",
    "min_load": ${MIN_LOAD},
    "target_util": ${TARGET_UTIL},
    "cold_mult": ${COLD_MULT},
    "cold_workers": ${COLD_WORKERS},
    "max_workers": ${MAX_WORKERS}
}
EOF
)" | python3 -m json.tool

echo ""
echo "=== Endpoint created ==="
echo "Note the endpoint ID from the response above."
echo "Next: run 03-create-workergroup.sh"
