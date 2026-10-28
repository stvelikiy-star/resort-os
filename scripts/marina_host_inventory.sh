#!/usr/bin/env bash
set -euo pipefail
# Read-only MARINA SMART inventory. No secrets, changes or access to other projects.
for name in marina-hotel01-api-1 marina-hotel01-admin-1 marina-hotel01-staff-1 marina-hotel01-web-1 marina-hotel01-postgres-1; do
  if ! docker container inspect "$name" >/dev/null 2>&1; then
    echo "BLOCK: missing expected MARINA container $name" >&2
    exit 1
  fi
  running="$(docker inspect "$name" --format '{{.State.Running}}')"
  if [[ "$running" != true ]]; then
    echo "BLOCK: MARINA container not running: $name" >&2
    exit 1
  fi
  project="$(docker inspect "$name" --format '{{index .Config.Labels "com.docker.compose.project"}}')"
  service="$(docker inspect "$name" --format '{{index .Config.Labels "com.docker.compose.service"}}')"
  config="$(docker inspect "$name" --format '{{index .Config.Labels "com.docker.compose.project.config_files"}}')"
  image="$(docker inspect "$name" --format '{{.Image}}')"
  if [[ -z "$project" || "$project" == "<no value>" || -z "$config" || "$config" == "<no value>" ]]; then
    echo "BLOCK: missing compose provenance for $name" >&2
    exit 1
  fi
  printf 'MARINA_CONTAINER=%s PROJECT=%s SERVICE=%s IMAGE=%s COMPOSE_FILE=%s\n' "$name" "$project" "$service" "$image" "$config"
done
echo 'MARINA_HOST_INVENTORY_PASS (READ_ONLY)'
