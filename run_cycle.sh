#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
BASE_URL="${ORCHESTRATOR_URL:-http://localhost:8000}"
if [[ -n "${SEED_LEADS_CSV:-}" && -f "${SEED_LEADS_CSV}" ]]; then
  curl --fail --silent --show-error -F "file=@${SEED_LEADS_CSV}" "${BASE_URL}/leads/csv"
fi
curl --fail --silent --show-error -X POST "${BASE_URL}/cycle"
printf '\nCycle completed.\n'
