#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

KEEP_STACK="${KEEP_STACK:-0}"

teardown() {
  if [ "$KEEP_STACK" != "1" ]; then
    docker compose down
  fi
}
trap teardown EXIT

docker compose up --build -d proxy

wait_for() {
  local url="$1"
  local attempts=0
  until curl -sk "$url" -o /dev/null; do
    attempts=$((attempts + 1))
    if [ "$attempts" -gt 60 ]; then
      echo "Timed out waiting for $url" >&2
      exit 1
    fi
    sleep 2
  done
}

wait_for "https://localhost/api/health"
wait_for "https://localhost/"

run_load() {
  local url="$1"
  echo "Load smoke for $url"
  seq 1 20 | xargs -n1 -P5 -I{} curl -sk -o /dev/null -w "%{http_code}\n" "$url" \
    | awk '!/^200$/ && !/^308$/{print "Unexpected status: "$0; exit 1}'
}

run_load "http://localhost/api/health"
run_load "https://localhost/api/health"
run_load "https://localhost/"
