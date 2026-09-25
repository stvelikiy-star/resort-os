#!/bin/sh
set -eu
cd "$(dirname "$0")"
if ! command -v docker >/dev/null 2>&1; then echo "Docker не найден"; exit 1; fi
if ! docker info >/dev/null 2>&1; then echo "Запусти Docker Desktop"; exit 1; fi
docker compose -f compose.marina-test.yaml up -d --build
echo "Жду MARINA SMART..."
i=0
while [ "$i" -lt 120 ]; do
  if curl -fsS http://127.0.0.1:18100/health/ready >/dev/null 2>&1 && curl -fsS http://127.0.0.1:13101/ >/dev/null 2>&1; then break; fi
  i=$((i+1)); sleep 2
done
curl -fsS http://127.0.0.1:18100/health/ready >/dev/null
curl -fsS http://127.0.0.1:13101/ >/dev/null
echo
echo "MARINA SMART READY"
echo "Admin/PMS: http://127.0.0.1:13101/"
echo "Staff:     http://127.0.0.1:13102/"
echo "API:       http://127.0.0.1:18100/health/ready"
echo
echo "marina / MarinaDemo2026!"
echo "admin / MarinaDemo2026!"
echo "kitchen / MarinaDemo2026!"
echo "housemaid / MarinaDemo2026!"
