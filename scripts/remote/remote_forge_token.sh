#!/usr/bin/env bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "$PROJECT_ROOT"
mkdir -p "$REPORTS_DIR"
python3 "$TOOLS_DIR/forge_admin_jwt.py" | tee "$REPORTS_DIR/forged_admin_jwt.txt"
