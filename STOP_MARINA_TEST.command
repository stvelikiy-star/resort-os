#!/bin/sh
set -eu
cd "$(dirname "$0")"
docker compose -f compose.marina-test.yaml stop
echo "MARINA SMART остановлена. Тестовая база сохранена."
