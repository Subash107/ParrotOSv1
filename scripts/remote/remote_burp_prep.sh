#!/usr/bin/env bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "$PROJECT_ROOT"
unset DOCKER_HOST
docker compose ps
curl -s http://app.acme.local:8080/ | grep -o 'Acme Employee Hub' | head -n 1
pgrep -a burpsuite || true
