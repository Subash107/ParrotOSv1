#!/usr/bin/env bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "$PROJECT_ROOT"
ls -lh "$GUIDES_DIR/BURP_ZAP_WALKTHROUGH.md" "$REPORTS_DIR/login-alice-live.json" "$REPORTS_DIR/forged_admin_jwt.txt" "$REPORTS_DIR/jwt_compare.json"
