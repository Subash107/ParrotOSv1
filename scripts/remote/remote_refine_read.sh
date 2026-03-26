#!/usr/bin/env bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "$REPORTS_DIR"
for file in nmap-ports.txt hydra-full.txt; do
  echo "--- $file ---"
  if [ -f "$file" ]; then
    cat "$file"
  else
    echo missing
  fi
  echo
 done
