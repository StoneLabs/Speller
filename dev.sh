#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

if [[ ! -d "$ROOT/backend/.venv" ]]; then
  python -m venv "$ROOT/backend/.venv"
  "$ROOT/backend/.venv/bin/pip" install -r "$ROOT/backend/requirements.txt"
fi

if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
  (cd "$ROOT/frontend" && npm install)
fi

trap 'kill 0' EXIT
(cd "$ROOT/backend" && "$ROOT/backend/.venv/bin/uvicorn" main:app --reload --host 0.0.0.0 --port 8000) &
(cd "$ROOT/frontend" && npm run dev) &
wait
