#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Link the template to the endpoint by creating a workergroup.
#
# Prerequisites:
#   01-create-template.sh and 02-create-endpoint.sh have been run.
#
# Environment variables:
#   ENDPOINT_NAME    (default: inference-tts-ep)
#   TEMPLATE_NAME    (default: inference-tts)
#   WORKERGROUP_NAME (default: inference-tts-wg)
#   VAST_API_KEY     (required)
# ---------------------------------------------------------------------------
set -euo pipefail

: "${VAST_API_KEY:?Must set VAST_API_KEY}"

ENDPOINT_NAME="${ENDPOINT_NAME:-inference-tts-ep}"
TEMPLATE_NAME="${TEMPLATE_NAME:-inference-tts}"
WORKERGROUP_NAME="${WORKERGROUP_NAME:-inference-tts-wg}"

echo "=== Creating workergroup: ${WORKERGROUP_NAME} ==="
echo "Linking template '${TEMPLATE_NAME}' to endpoint '${ENDPOINT_NAME}'."

# Step 1: get the template ID and endpoint ID from Vast
TEMPLATE_ID=$(vastai show templates --json \
    | python3 -c "import sys,json; data=json.load(sys.stdin); print([t['id'] for t in data if t['name']=='${TEMPLATE_NAME}'][0])")

ENDPOINT_ID=$(curl -s "https://console.vast.ai/api/v0/endptjobs/" \
    -H "Authorization: Bearer ${VAST_API_KEY}" \
    | python3 -c "import sys,json; data=json.load(sys.stdin); print([e['id'] for e in data['endpoints'] if e['endpoint_name']=='${ENDPOINT_NAME}'][0])")

echo "  Template ID:  ${TEMPLATE_ID}"
echo "  Endpoint ID:  ${ENDPOINT_ID}"

# Step 2: create the workergroup
curl -s -X POST "https://console.vast.ai/api/v0/workergroups/" \
    -H "Authorization: Bearer ${VAST_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "$(cat <<EOF
{
    "workergroup_name": "${WORKERGROUP_NAME}",
    "template_id": ${TEMPLATE_ID},
    "endpoint_id": ${ENDPOINT_ID}
}
EOF
)" | python3 -m json.tool

echo ""
echo "=== Workergroup created ==="
echo "The endpoint is now live and will autoscale workers as demand arrives."
echo ""
echo "To test:"
echo "  curl -X POST https://\${WORKER_URL}/tts \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"text\":\"Hello world\"}'"
