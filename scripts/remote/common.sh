#!/usr/bin/env bash

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports"
GUIDES_DIR="$PROJECT_ROOT/docs/guides"
REPORT_DOCS_DIR="$PROJECT_ROOT/docs/reports"
TOOLS_DIR="$PROJECT_ROOT/tools"
