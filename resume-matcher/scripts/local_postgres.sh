#!/usr/bin/env bash
# Run a local PostgreSQL WITHOUT Docker, storing data in ./.pgdata
# Uses pg binaries from PATH, or from a conda env named "resume-pg"
#   (create it once with: conda create -n resume-pg -c conda-forge postgresql=16)
# Usage: scripts/local_postgres.sh init|start|stop|status
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="$ROOT/.pgdata"
PORT="${PGPORT:-5432}"
if command -v pg_ctl >/dev/null 2>&1; then BIN="$(dirname "$(command -v pg_ctl)")"
elif [ -x "$HOME/anaconda3/envs/resume-pg/bin/pg_ctl" ]; then BIN="$HOME/anaconda3/envs/resume-pg/bin"
elif [ -x "/opt/anaconda3/envs/resume-pg/bin/pg_ctl" ]; then BIN="/opt/anaconda3/envs/resume-pg/bin"
elif [ -x "$HOME/miniconda3/envs/resume-pg/bin/pg_ctl" ]; then BIN="$HOME/miniconda3/envs/resume-pg/bin"
else echo "PostgreSQL binaries not found. Install Postgres.app / Homebrew postgresql@16 / the official installer, or the conda env above." >&2; exit 1; fi

case "${1:-}" in
  init)
    "$BIN/initdb" -D "$DATA" -U postgres --auth=trust -E UTF8
    "$BIN/pg_ctl" -D "$DATA" -l "$DATA/server.log" -o "-p $PORT" start
    sleep 2
    "$BIN/psql" -U postgres -h localhost -p "$PORT" -c "ALTER USER postgres PASSWORD 'postgres';" \
      -c "CREATE DATABASE resume_matcher;" -c "CREATE DATABASE resume_matcher_test;"
    echo "PostgreSQL ready on port $PORT (databases: resume_matcher, resume_matcher_test)";;
  start)  "$BIN/pg_ctl" -D "$DATA" -l "$DATA/server.log" -o "-p $PORT" start;;
  stop)   "$BIN/pg_ctl" -D "$DATA" stop;;
  status) "$BIN/pg_ctl" -D "$DATA" status;;
  *) echo "Usage: $0 init|start|stop|status"; exit 1;;
esac
