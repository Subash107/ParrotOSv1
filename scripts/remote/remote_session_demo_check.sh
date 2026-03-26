#!/usr/bin/env bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "$PROJECT_ROOT"
ls -lh "$GUIDES_DIR/BURP_ZAP_WALKTHROUGH.md"
