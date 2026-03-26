#!/usr/bin/env bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "$PROJECT_ROOT"
mkdir -p "$REPORTS_DIR"
unset DOCKER_HOST

nmap -Pn -sV -sC -p 8080,8081,8082,9000,9001,3306 127.0.0.1 | tee "$REPORTS_DIR/nmap.txt"
nikto -h http://app.acme.local:8080 -output "$REPORTS_DIR/nikto-app" -Format txt
nikto -h http://api.acme.local:8081 -output "$REPORTS_DIR/nikto-api" -Format txt
nikto -h http://admin.acme.local:8082 -output "$REPORTS_DIR/nikto-admin" -Format txt

echo '--- nmap summary ---'
tail -n 40 "$REPORTS_DIR/nmap.txt"

echo '--- nikto app summary ---'
grep -E '^\+ ' "$REPORTS_DIR/nikto-app.txt" | head -n 20 || true

echo '--- nikto api summary ---'
grep -E '^\+ ' "$REPORTS_DIR/nikto-api.txt" | head -n 20 || true

echo '--- nikto admin summary ---'
grep -E '^\+ ' "$REPORTS_DIR/nikto-admin.txt" | head -n 20 || true
