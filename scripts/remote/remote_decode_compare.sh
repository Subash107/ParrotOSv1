#!/usr/bin/env bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

cd "$PROJECT_ROOT"
python3 - <<'PY'
import base64, json
from pathlib import Path
orig = json.loads(Path('reports/login-alice-live.json').read_text())['token']
forged = Path('reports/forged_admin_jwt.txt').read_text().strip()

def decode_payload(token):
    parts = token.split('.')
    payload = parts[1] + '=' * (-len(parts[1]) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))

out = {
    'original_token': orig,
    'original_payload': decode_payload(orig),
    'forged_token': forged,
    'forged_payload': decode_payload(forged),
}
Path('reports/jwt_compare.json').write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
PY
