#!/usr/bin/env bash
# Start backend (http://localhost:8000) and frontend (http://localhost:5173) together. Ctrl+C stops both.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
(cd "$ROOT/backend" && .venv/bin/uvicorn app.main:app --port 8000 --reload) &
BACK=$!
(cd "$ROOT/frontend" && npm run dev) &
FRONT=$!
trap 'kill $BACK $FRONT 2>/dev/null' INT TERM EXIT
echo "Backend: http://localhost:8000/docs   Frontend: http://localhost:5173"
wait
