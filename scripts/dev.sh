#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DEFAULT_TEST_DB="postgresql+asyncpg://tastebuds:tastebuds@db:5432/tastebuds_test"

should_use_flatpak() {
  if [ "${TASTEBUDS_USE_FLATPAK:-0}" = "1" ]; then
    if ! command -v flatpak-spawn >/dev/null 2>&1; then
      echo "flatpak-spawn is required when TASTEBUDS_USE_FLATPAK=1" >&2
      exit 1
    fi
    return 0
  fi

  if [ -n "${FLATPAK_ID:-}" ] && command -v flatpak-spawn >/dev/null 2>&1; then
    return 0
  fi

  return 1
}

run_compose() {
  if should_use_flatpak; then
    flatpak-spawn --host docker compose "$@"
  else
    docker compose "$@"
  fi
}

usage() {
  cat <<'USAGE'
Usage: ./scripts/dev.sh <command>

Commands:
  up         Build images (if needed) and start the stack in the background
  down       Stop the stack
  logs [svc] Tail logs for the whole stack or a specific service
  migrate    Run Alembic migrations inside the api container
  seed       Execute the demo seed script
  test       Run pytest inside the api image (installs dev deps automatically)
  web        Run the web frontend (Next.js) via docker compose
  lint       Run ruff checks for the API and prettier for the web app inside containers
  fmt        Autoformat API (ruff format) and web (prettier --write) inside containers
USAGE
}

run_node_task() {
  local cmd="$1"
  local workdir="${2:-$ROOT_DIR/web}"
  if should_use_flatpak; then
    flatpak-spawn --host docker run --rm -v "$workdir:/work" -w /work node:20-alpine sh -c "$cmd"
  else
    docker run --rm -v "$workdir:/work" -w /work node:20-alpine sh -c "$cmd"
  fi
}

cmd="${1:-}" || true
[ -n "$cmd" ] || { usage; exit 1; }
shift || true

case "$cmd" in
  up)
    run_compose up --build -d
    ;;
  down)
    run_compose down
    ;;
  logs)
    if [ $# -gt 0 ]; then
      run_compose logs -f "$@"
    else
      run_compose logs -f
    fi
    ;;
  migrate)
    run_compose exec api alembic upgrade head
    ;;
  seed)
    run_compose exec api python -m app.scripts.seed
    ;;
  test)
    TEST_DB="${TEST_DATABASE_URL:-$DEFAULT_TEST_DB}"
    run_compose run --rm api sh -c "pip install -r requirements-dev.txt && TEST_DATABASE_URL=$TEST_DB pytest app/tests"
    ;;
  web)
    run_compose up --build -d web
    ;;
  lint)
    run_compose run --rm api sh -c "pip install -r requirements-dev.txt && python -m ruff check app"
    run_node_task "npm ci && npm run prettier:check"
    ;;
  fmt)
    run_compose run --rm api sh -c "pip install -r requirements-dev.txt && python -m ruff format app"
    run_node_task "npm ci && npx prettier --write \"**/*.{js,jsx,ts,tsx,md,mdx,json,css,scss}\""
    ;;
  *)
    usage
    exit 1
    ;;
esac
