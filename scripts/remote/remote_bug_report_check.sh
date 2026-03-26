#!/usr/bin/env bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "$PROJECT_ROOT"
ls -lh "$REPORT_DOCS_DIR/BUG_BOUNTY_REPORT.md" README.md
