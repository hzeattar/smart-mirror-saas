#!/bin/sh
set -eu

model_cache="${U2NET_HOME:-/models}"
mkdir -p "$model_cache"
chown processor:processor "$model_cache"

exec gosu processor "$@"
