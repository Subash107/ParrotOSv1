#!/usr/bin/env bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "$PROJECT_ROOT"
mkdir -p "$REPORTS_DIR"
nmap -Pn -sV -p 8080,8081,8082,9000,9001,3306 127.0.0.1 | tee "$REPORTS_DIR/nmap-ports.txt" >/dev/null
hydra -L "$REPORTS_DIR/users.txt" -P "$REPORTS_DIR/passwords.txt" \
  127.0.0.1 http-post-form \
  '/login:username=^USER^&password=^PASS^:F=invalid credentials' \
  -s 8081 -o "$REPORTS_DIR/hydra-full.txt" >/dev/null 2>&1 || true

echo '--- nmap open ports ---'
grep '/tcp' "$REPORTS_DIR/nmap-ports.txt"

echo
echo '--- hydra full ---'
cat "$REPORTS_DIR/hydra-full.txt"
