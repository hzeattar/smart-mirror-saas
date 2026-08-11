#!/usr/bin/env bash
set -euo pipefail

docker rm -f smart-mirror-nim-gateway smart-mirror-nim >/dev/null 2>&1 || true
echo "Smart Mirror NVIDIA containers are stopped."
