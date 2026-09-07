#!/usr/bin/env bash
set -euo pipefail

: "${LOAD_BASE_URL:?LOAD_BASE_URL is required}"
: "${LOAD_TEST_ENV:?LOAD_TEST_ENV is required (ci|test|staging)}"

case "${LOAD_TEST_ENV}" in
  ci|test|staging) ;;
  *) echo "LOAD TEST BLOCKED: LOAD_TEST_ENV must be ci, test, or staging" >&2; exit 2 ;;
esac

case "${LOAD_BASE_URL}" in
  https://3korony.com*|https://www.3korony.com*|http://3korony.com*|http://www.3korony.com*)
    echo "LOAD TEST BLOCKED: public production hostname is forbidden" >&2
    exit 2
    ;;
esac

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required for the pinned k6 runner." >&2
  exit 3
fi

K6_IMAGE="${K6_IMAGE:-grafana/k6:0.54.0}"

# Loopback URLs must be reachable from the k6 container through host networking.
network_args=()
if [[ "${LOAD_BASE_URL}" == http://127.0.0.1:* || "${LOAD_BASE_URL}" == http://localhost:* ]]; then
  if [[ "$(uname -s)" == "Linux" ]]; then
    network_args+=(--network host)
  else
    echo "For Docker Desktop, use a staging/test hostname reachable by the container instead of localhost." >&2
    exit 4
  fi
fi

exec docker run --rm \
  "${network_args[@]}" \
  -e LOAD_BASE_URL \
  -e LOAD_TEST_ENV \
  -e LOAD_OWNER_USERNAME \
  -e LOAD_OWNER_PASSWORD \
  -e LOAD_AUTH_GRID \
  -e LOAD_VUS_1 \
  -e LOAD_VUS_2 \
  -e LOAD_VUS_3 \
  -e LOAD_STAGE_1 \
  -e LOAD_STAGE_2 \
  -e LOAD_STAGE_3 \
  -e LOAD_STAGE_4 \
  -e LOAD_SLEEP_SECONDS \
  -v "$(pwd)/tests/load:/tests/load:ro" \
  "${K6_IMAGE}" run /tests/load/resort_core_read.k6.js
