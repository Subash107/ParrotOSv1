#!/usr/bin/env bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "$REPORTS_DIR"
ls -lh
for file in nmap.txt nikto-app.txt nikto-api.txt nikto-admin.txt; do
  echo "--- $file ---"
  if [ -f "$file" ]; then
    tail -n 25 "$file"
  else
    echo missing
  fi
  echo
 done
