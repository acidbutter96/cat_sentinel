#!/usr/bin/env bash
set -euo pipefail

# Orchestrates local dev for the whole cat_sentinel monorepo: brings up
# Postgres, then each service in the background, using the newer port
# scheme (camera=9000, cat-sentinel=9001, hub=9002, hub_frontend=3000).
# The older scheme (8001/8002/8000) coexisted in an earlier iteration of
# this project -- override with CAMERA_PORT/CAT_SENTINEL_PORT/HUB_PORT env
# vars if you need it back.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

CAMERA_PORT="${CAMERA_PORT:-9000}"
CAT_SENTINEL_PORT="${CAT_SENTINEL_PORT:-9001}"
HUB_PORT="${HUB_PORT:-9002}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

PIDS=()
cleanup() {
  echo "Stopping services..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

echo "==> Starting Postgres (docker compose)"
(cd "$ROOT_DIR" && docker compose up -d postgres)

echo "==> Starting camera on :$CAMERA_PORT"
(cd "$ROOT_DIR/camera" && poetry run uvicorn app.main:app --reload --port "$CAMERA_PORT") &
PIDS+=($!)

echo "==> Starting cat-sentinel on :$CAT_SENTINEL_PORT"
(cd "$ROOT_DIR/cat-sentinel" && poetry run uvicorn app.main:app --reload --port "$CAT_SENTINEL_PORT") &
PIDS+=($!)

echo "==> Starting hub on :$HUB_PORT"
(cd "$ROOT_DIR/hub" && poetry run uvicorn app.main:app --reload --port "$HUB_PORT") &
PIDS+=($!)

echo "==> Starting hub_frontend on :$FRONTEND_PORT"
(cd "$ROOT_DIR/hub_frontend" && HUB_BASE_URL="http://localhost:$HUB_PORT" yarn dev --port "$FRONTEND_PORT") &
PIDS+=($!)

echo "All services starting. Ctrl+C to stop everything."
wait
