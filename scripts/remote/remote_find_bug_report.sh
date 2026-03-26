#!/usr/bin/env bash
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/common.sh"

find "$PROJECT_ROOT" -maxdepth 4 \( -name 'BUG_BOUNTY_REPORT.md' -o -name 'bug_bounty_report.md' \)
