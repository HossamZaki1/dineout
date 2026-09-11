#!/usr/bin/env bash
# Optional LIVE smoke test: makes one billed search and stores a conversation.
set -euo pipefail
API_URL="${API_URL:-http://127.0.0.1:8080}"
if [[ -z "${FIREBASE_ID_TOKEN:-}" ]]; then
    read -r -s -p "Firebase ID token: " FIREBASE_ID_TOKEN
    echo
fi
: "${FIREBASE_ID_TOKEN:?A Firebase ID token is required}"
curl --fail --silent --show-error "$API_URL/health" | python3 -m json.tool
# Read the sensitive header on stdin so the token is not a curl process argument.
printf 'Authorization: Bearer %s\n' "$FIREBASE_ID_TOKEN" |
    curl --fail --silent --show-error "$API_URL/chat" --header @- \
        --header "Content-Type: application/json" \
        --data '{"user_input":"Find Italian restaurants in San Francisco","history":[]}' |
    python3 -m json.tool
