#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
export COMPOSE_PROJECT_NAME="threecrownsrealadmin"
docker compose --env-file .env.real-admin -f compose.staging.yaml down --remove-orphans
printf 'Three Crowns local real-admin stack stopped. Data volume preserved.\n'
