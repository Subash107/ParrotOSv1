#!/usr/bin/env bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "$REPORTS_DIR"
for file in nikto-app.txt nikto-api.txt nikto-admin.txt; do
  echo "--- $file ---"
  if [ -f "$file" ]; then
    cat "$file"
  else
    echo missing
  fi
  echo
 done
