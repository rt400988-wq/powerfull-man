#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -f .env ]]; then cp .env.example .env; echo 'Created .env from .env.example; review placeholders before production use.'; fi
docker compose -f docker-compose.yaml up -d --build
echo 'Orchestrator: http://localhost:8000/health'
echo 'Dashboard:     http://localhost:8000/dashboard'
