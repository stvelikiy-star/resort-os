#!/bin/sh
set -eu
cd "$(dirname "$0")"

printf "Это удалит ТОЛЬКО локальную тестовую базу MARINA SMART и создаст новую. Введите RESET: "
read answer
if [ "$answer" != "RESET" ]; then
  echo "Отмена."
  exit 1
fi

docker compose -f compose.marina-test.yaml down -v
docker compose -f compose.marina-test.yaml up -d --build

echo "Жду новую MARINA SMART..."
i=0
while [ "$i" -lt 120 ]; do
  if curl -fsS http://127.0.0.1:18100/health/ready >/dev/null 2>&1      && curl -fsS http://127.0.0.1:13101/ >/dev/null 2>&1      && curl -fsS http://127.0.0.1:13102/ >/dev/null 2>&1; then
    break
  fi
  i=$((i+1))
  sleep 2
done

if ! curl -fsS http://127.0.0.1:18100/health/ready >/dev/null 2>&1; then
  echo "ERROR: API не поднялся после RESET."
  docker compose -f compose.marina-test.yaml logs --tail=160 api
  exit 1
fi
if ! curl -fsS http://127.0.0.1:13101/ >/dev/null 2>&1; then
  echo "ERROR: Admin/PMS не поднялся после RESET."
  docker compose -f compose.marina-test.yaml logs --tail=160 admin
  exit 1
fi
if ! curl -fsS http://127.0.0.1:13102/ >/dev/null 2>&1; then
  echo "ERROR: Staff не поднялся после RESET."
  docker compose -f compose.marina-test.yaml logs --tail=160 staff
  exit 1
fi

echo
echo "MARINA SMART TEST BASE RESET = PASS"
echo "Admin/PMS: http://127.0.0.1:13101/"
echo "Staff:     http://127.0.0.1:13102/"
echo "Новая база: 12 номеров / 3 категории"
