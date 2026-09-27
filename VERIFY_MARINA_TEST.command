#!/bin/sh
set -eu
cd "$(dirname "$0")"

echo "=== MARINA SMART CLIENT TEST VERIFY ==="
echo

docker compose -f compose.marina-test.yaml ps
echo

curl -fsS http://127.0.0.1:18100/health/ready >/tmp/marina-ready.json
echo "API: PASS"
cat /tmp/marina-ready.json
echo

curl -fsS http://127.0.0.1:13101/ >/dev/null
echo "Admin/PMS: PASS"

curl -fsS http://127.0.0.1:13102/ >/dev/null
echo "Staff: PASS"

rooms="$(docker compose -f compose.marina-test.yaml exec -T postgres sh -lc 'psql -U marina_test -d marina_smart_test -tAc "SELECT count(*) FROM rooms;"' | tr -d '[:space:]')"
types="$(docker compose -f compose.marina-test.yaml exec -T postgres sh -lc 'psql -U marina_test -d marina_smart_test -tAc "SELECT count(*) FROM room_types;"' | tr -d '[:space:]')"
property="$(docker compose -f compose.marina-test.yaml exec -T postgres sh -lc 'psql -U marina_test -d marina_smart_test -tAc "SELECT name FROM properties WHERE code='\''MARINA_TEST'\'';"' | sed 's/^ *//;s/ *$//')"

echo "Property: $property"
echo "Rooms: $rooms"
echo "Room types: $types"

docker compose -f compose.marina-test.yaml exec -T api   env CORE_API_URL=http://127.0.0.1:8000   python scripts/verify_marina_hotel_setup.py

echo
echo "MARINA SMART VERIFY = PASS"
echo "Проверка не сбрасывала ваш номерной фонд."
