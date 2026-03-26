#!/usr/bin/env bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "$PROJECT_ROOT"
mkdir -p "$REPORTS_DIR"
nikto -h http://admin.acme.local:8082 -output "$REPORTS_DIR/nikto-admin" -Format txt
cat "$REPORTS_DIR/nikto-admin.txt"
