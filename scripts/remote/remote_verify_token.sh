#!/usr/bin/env bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "$PROJECT_ROOT"
TOKEN=$(cat "$REPORTS_DIR/forged_admin_jwt.txt")
curl -s http://api.acme.local:8081/api/admin -H "Authorization: Bearer $TOKEN"
