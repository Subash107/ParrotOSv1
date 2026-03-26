#!/usr/bin/env bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "$PROJECT_ROOT"
ls -lh "$REPORT_DOCS_DIR/FINDINGS.md" "$GUIDES_DIR/BURP_ZAP_WALKTHROUGH.md" README.md
