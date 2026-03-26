#!/usr/bin/env bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "$PROJECT_ROOT"
mkdir -p "$REPORTS_DIR"
curl -s -X POST http://api.acme.local:8081/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"welcome123"}' > "$REPORTS_DIR/login-alice-live.json"
python3 - <<'PY'
import json
from pathlib import Path
obj = json.loads(Path('reports/login-alice-live.json').read_text())
print(obj['token'])
PY
