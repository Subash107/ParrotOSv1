#!/bin/sh
set -eu

MINIO_ALIAS_ROOT_USER="${MINIO_ALIAS_ROOT_USER:-minioadmin}"
MINIO_ALIAS_ROOT_PASSWORD="${MINIO_ALIAS_ROOT_PASSWORD:-minioadmin}"
STORAGE_MODE="${STORAGE_MODE:-vulnerable}"

until /usr/bin/mc alias set acme http://storage:9000 "$MINIO_ALIAS_ROOT_USER" "$MINIO_ALIAS_ROOT_PASSWORD" >/dev/null 2>&1; do
  echo "Waiting for MinIO..."
  sleep 2
done

/usr/bin/mc mb -p acme/public-assets >/dev/null 2>&1 || true

if [ "$STORAGE_MODE" = "remediated" ]; then
  /usr/bin/mc anonymous set none acme/public-assets >/dev/null 2>&1 || true
else
  /usr/bin/mc anonymous set public acme/public-assets >/dev/null 2>&1 || true
fi

cat <<'EOF' >/tmp/security-note.txt
Acme vendor handoff

This bucket is intentionally public for the bug bounty simulation lab.
Known issues:
- default MinIO credentials remain enabled
- public-assets allows anonymous reads
- quarterly exports are copied here during vendor reviews
EOF

/usr/bin/mc cp /tmp/security-note.txt acme/public-assets/security-note.txt >/dev/null 2>&1 || true
