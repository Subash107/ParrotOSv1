#!/usr/bin/env bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "$PROJECT_ROOT"
ls -lh "$REPORT_DOCS_DIR/EXECUTIVE_REPORT.md" "$REPORT_DOCS_DIR/HACKERONE_TEMPLATE.md" "$REPORT_DOCS_DIR/BUGCROWD_TEMPLATE.md" README.md
