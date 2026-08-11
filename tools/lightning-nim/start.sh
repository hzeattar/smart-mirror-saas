#!/usr/bin/env bash
set -euo pipefail

NIM_IMAGE="${NIM_IMAGE:-nvcr.io/nim/black-forest-labs/flux.2-klein-4b:1.0.2-variant}"
NIM_CACHE_PATH="${NIM_CACHE_PATH:-/teamspace/smart-mirror-nim-cache}"
GATEWAY_IMAGE="${GATEWAY_IMAGE:-smart-mirror-nim-gateway:pilot}"
NETWORK="${NIM_DOCKER_NETWORK:-smart-mirror-nim}"

: "${NGC_API_KEY:?NGC_API_KEY is required}"
: "${GATEWAY_BEARER_TOKEN:?GATEWAY_BEARER_TOKEN is required}"

nvidia-smi >/dev/null
mkdir -p "$NIM_CACHE_PATH"
chmod 1777 "$NIM_CACHE_PATH"

docker network inspect "$NETWORK" >/dev/null 2>&1 || docker network create "$NETWORK" >/dev/null
docker rm -f smart-mirror-nim-gateway smart-mirror-nim >/dev/null 2>&1 || true

docker run -d \
  --name smart-mirror-nim \
  --network "$NETWORK" \
  --gpus all \
  --restart unless-stopped \
  -e NGC_API_KEY \
  -v "$NIM_CACHE_PATH:/opt/nim/.cache" \
  "$NIM_IMAGE" >/dev/null

docker run -d \
  --name smart-mirror-nim-gateway \
  --network "$NETWORK" \
  --restart unless-stopped \
  -p 0.0.0.0:8080:8080 \
  -e GATEWAY_BEARER_TOKEN \
  -e NIM_UPSTREAM_URL=http://smart-mirror-nim:8000 \
  -e GATEWAY_MAX_BODY_MB=50 \
  -e GATEWAY_MAX_CONCURRENCY=2 \
  "$GATEWAY_IMAGE" >/dev/null

deadline=$((SECONDS + 900))
until curl --silent --fail \
  -H "Authorization: Bearer $GATEWAY_BEARER_TOKEN" \
  http://127.0.0.1:8080/v1/health/ready >/dev/null; do
  if (( SECONDS >= deadline )); then
    docker logs --tail 100 smart-mirror-nim >&2 || true
    exit 1
  fi
  sleep 5
done

echo "NVIDIA NIM gateway is ready on port 8080."
