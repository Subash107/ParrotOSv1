#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports"
HOSTS_FILE="/etc/hosts"
HOST_ALIASES=(app.acme.local api.acme.local admin.acme.local storage.acme.local)
HOST_LINE="127.0.0.1 ${HOST_ALIASES[*]}"
ADD_HOSTS=0

log() {
  printf '[acme-bootstrap] %s\n' "$1"
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    log "Missing required tool: $cmd"
    exit 1
  fi
  log "Found $cmd: $(command -v "$cmd")"
}

find_python() {
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return
  fi
  return 1
}

for arg in "$@"; do
  case "$arg" in
    --add-hosts)
      ADD_HOSTS=1
      ;;
    *)
      log "Unknown argument: $arg"
      exit 1
      ;;
  esac
done

log "Project root: $PROJECT_ROOT"
mkdir -p "$REPORTS_DIR"
log "Reports directory is ready."

require_cmd docker
PYTHON_BIN="$(find_python)" || {
  log "Missing required tool: python3 or python"
  exit 1
}
log "Found python: $PYTHON_BIN"

if command -v git >/dev/null 2>&1; then
  log "Found optional tool git: $(command -v git)"
else
  log "Optional tool not found: git"
fi

if docker compose -f "$PROJECT_ROOT/docker-compose.yml" config >/dev/null 2>&1; then
  log "Docker Compose configuration is valid."
else
  log "Docker Compose validation could not run from this shell."
  log "If you are using WSL, enable Docker Desktop WSL integration for this distro."
fi

missing_aliases=()
if [[ -r "$HOSTS_FILE" ]]; then
  for alias in "${HOST_ALIASES[@]}"; do
    if ! grep -Eq "^[[:space:]]*127\\.0\\.0\\.1[[:space:]].*\\b${alias}\\b" "$HOSTS_FILE"; then
      missing_aliases+=("$alias")
    fi
  done
fi

if (( ADD_HOSTS == 1 )) && (( ${#missing_aliases[@]} > 0 )); then
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    log "Re-run bootstrap.sh with sudo to update $HOSTS_FILE."
    exit 1
  fi
  printf '\n%s\n' "$HOST_LINE" >> "$HOSTS_FILE"
  log "Added local host aliases to $HOSTS_FILE."
  missing_aliases=()
fi

if (( ${#missing_aliases[@]} > 0 )); then
  log "Missing hosts aliases: ${missing_aliases[*]}"
  log "Add this line to $HOSTS_FILE or rerun with --add-hosts:"
  printf '%s\n' "$HOST_LINE"
else
  log "Local hosts aliases are present."
fi

log "Bootstrap check complete."
log "Next command: docker compose up --build"
