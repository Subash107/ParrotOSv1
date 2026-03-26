#!/usr/bin/env bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "$PROJECT_ROOT"
unset DOCKER_HOST
echo '--- compose ps ---'
docker compose ps
echo '--- tools ---'
for tool in nmap theHarvester nikto hydra john msfconsole zaproxy burpsuite curl jq python3; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf '%s: %s\n' "$tool" "$(command -v "$tool")"
  else
    printf '%s: missing\n' "$tool"
  fi
done
