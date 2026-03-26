#!/usr/bin/env bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "$PROJECT_ROOT"
unset DOCKER_HOST

printf '%s\n' '--- project root ---'
pwd

printf '%s\n' '--- compose ps ---'
docker compose ps || true

printf '%s\n' '--- hosts ---'
getent hosts app.acme.local api.acme.local admin.acme.local storage.acme.local || true

printf '%s\n' '--- tools ---'
for tool in nmap theHarvester nikto hydra john msfconsole zaproxy burpsuite curl jq python3 docker docker-compose gobuster ffuf sqlmap whatweb feroxbuster nuclei dirsearch dirb hashcat wfuzz amass subfinder rustscan; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf '%s: %s\n' "$tool" "$(command -v "$tool")"
  else
    printf '%s: missing\n' "$tool"
  fi
done

printf '%s\n' '--- endpoint checks ---'
for url in \
  http://app.acme.local:8080/ \
  http://api.acme.local:8081/health \
  'http://api.acme.local:8081/api/user?id=1' \
  http://admin.acme.local:8082/health \
  http://storage.acme.local:9000/public-assets/security-note.txt \
  http://storage.acme.local:9001/; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$url" || true)
  printf '%s -> %s\n' "$url" "$code"
done
