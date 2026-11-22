#!/usr/bin/env bash
# One-time local setup (no Docker). Requires Python 3.10-3.12, Node 18+, PostgreSQL running.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"

echo "==> Backend"
cd "$ROOT/backend"
[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q
.venv/bin/python -m spacy download en_core_web_sm -q
[ -f .env ] || cp .env.example .env
.venv/bin/python -m scripts.generate_samples
# Pre-download the embedding model (~90 MB) so the first analysis is fast
.venv/bin/python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

echo "==> Frontend"
cd "$ROOT/frontend"
npm install --no-audit --no-fund
[ -f .env ] || cp .env.example .env
echo "Setup complete. Start the app with: scripts/start.sh"
