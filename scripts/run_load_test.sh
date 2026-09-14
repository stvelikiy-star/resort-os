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

case "${LOAD_EXPLICIT_TEST_HOST:-}" in
  3korony.com|www.3korony.com)
    echo "LOAD TEST BLOCKED: public production hostname cannot be allowlisted" >&2
    exit 2
    ;;
esac

url_without_scheme="${LOAD_BASE_URL#*://}"
host_with_port="${url_without_scheme%%/*}"
load_host="${host_with_port%%:*}"

is_loopback=false
if [[ "${load_host}" == "127.0.0.1" || "${load_host}" == "localhost" ]]; then
  is_loopback=true
fi

has_test_marker=false
if [[ "${load_host}" == *staging* || "${load_host}" == *test* || "${load_host}" == *.invalid ]]; then
  has_test_marker=true
fi

is_exact_external_test=false
if [[ ("${LOAD_TEST_ENV}" == "test" || "${LOAD_TEST_ENV}" == "staging") \
   && -n "${LOAD_EXPLICIT_TEST_HOST:-}" \
   && "${load_host}" == "${LOAD_EXPLICIT_TEST_HOST}" ]]; then
  is_exact_external_test=true
fi

if [[ "${is_loopback}" != true && "${has_test_marker}" != true && "${is_exact_external_test}" != true ]]; then
  echo "LOAD TEST BLOCKED: non-loopback target must contain staging/test marker or exactly match LOAD_EXPLICIT_TEST_HOST under test/staging" >&2
  exit 2
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required for the pinned k6 runner." >&2
  exit 3
fi

K6_IMAGE="${K6_IMAGE:-grafana/k6:0.54.0}"

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
  -e LOAD_EXPLICIT_TEST_HOST \
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
