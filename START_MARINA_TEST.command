#!/bin/sh
set -eu
cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker не найден."
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "ERROR: сначала запусти Docker Desktop."
  exit 1
fi

docker compose -f compose.marina-test.yaml up -d --build

echo "Жду PostgreSQL + API + Admin + Staff..."
i=0
while [ "$i" -lt 120 ]; do
  api_ok=0
  admin_ok=0
  staff_ok=0
  curl -fsS http://127.0.0.1:18100/health/ready >/dev/null 2>&1 && api_ok=1 || true
  curl -fsS http://127.0.0.1:13101/ >/dev/null 2>&1 && admin_ok=1 || true
  curl -fsS http://127.0.0.1:13102/ >/dev/null 2>&1 && staff_ok=1 || true
  if [ "$api_ok" = "1" ] && [ "$admin_ok" = "1" ] && [ "$staff_ok" = "1" ]; then
    break
  fi
  i=$((i+1))
  sleep 2
done

if ! curl -fsS http://127.0.0.1:18100/health/ready >/dev/null 2>&1; then
  echo "ERROR: API не поднялся."
  docker compose -f compose.marina-test.yaml logs --tail=160 api
  exit 1
fi
if ! curl -fsS http://127.0.0.1:13101/ >/dev/null 2>&1; then
  echo "ERROR: Admin/PMS не поднялся."
  docker compose -f compose.marina-test.yaml logs --tail=160 admin
  exit 1
fi
if ! curl -fsS http://127.0.0.1:13102/ >/dev/null 2>&1; then
  echo "ERROR: Staff не поднялся."
  docker compose -f compose.marina-test.yaml logs --tail=160 staff
  exit 1
fi

echo
docker compose -f compose.marina-test.yaml ps
echo
echo "======================================================"
echo "MARINA SMART CLIENT TEST = READY"
echo "======================================================"
echo "Admin/PMS: http://127.0.0.1:13101/"
echo "Staff:     http://127.0.0.1:13102/"
echo "API:       http://127.0.0.1:18100/health/ready"
echo
echo "marina    / MarinaDemo2026!"
echo "admin     / MarinaDemo2026!"
echo "kitchen   / MarinaDemo2026!"
echo "housemaid / MarinaDemo2026!"
echo
echo "Проверка без сброса базы: ./VERIFY_MARINA_TEST.command"
echo "Полный сброс тестовой базы: ./RESET_MARINA_TEST.command"
echo "======================================================"
