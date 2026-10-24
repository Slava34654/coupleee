#!/bin/bash
set -euo pipefail

URL="${HEALTHCHECK_URL:-http://127.0.0.1:8000/health}"
RESPONSE="$(curl --fail --silent --show-error \
  --connect-timeout 5 --max-time 10 "$URL")"
if [[ "$RESPONSE" != *'"status":"ok"'* ]]; then
  logger -t enrwine-healthcheck "Unexpected response from $URL: $RESPONSE"
  exit 1
fi
echo "$RESPONSE"
