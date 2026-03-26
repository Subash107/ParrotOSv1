#!/bin/sh
set -eu

until /usr/bin/mc alias set acme http://storage:9000 minioadmin minioadmin >/dev/null 2>&1; do
  echo "Waiting for MinIO..."
  sleep 2
done

/usr/bin/mc mb -p acme/public-assets >/dev/null 2>&1 || true
/usr/bin/mc anonymous set public acme/public-assets >/dev/null 2>&1 || true

cat <<'EOF' >/tmp/security-note.txt
Acme vendor handoff

This bucket is intentionally public for the bug bounty simulation lab.
Known issues:
- default MinIO credentials remain enabled
- public-assets allows anonymous reads
- quarterly exports are copied here during vendor reviews
EOF

/usr/bin/mc cp /tmp/security-note.txt acme/public-assets/security-note.txt >/dev/null 2>&1 || true
