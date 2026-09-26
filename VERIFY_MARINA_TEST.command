#!/bin/sh
set -eu
cd "$(dirname "$0")"

echo "=== MARINA SMART CLIENT TEST VERIFY ==="

docker compose -f compose.marina-test.yaml ps

curl -fsS http://127.0.0.1:18100/health/ready
echo

rooms="$(docker compose -f compose.marina-test.yaml exec -T postgres sh -lc 'psql -U marina_test -d marina_smart_test -tAc "SELECT count(*) FROM rooms;"' | tr -d '[:space:]')"
types="$(docker compose -f compose.marina-test.yaml exec -T postgres sh -lc 'psql -U marina_test -d marina_smart_test -tAc "SELECT count(*) FROM room_types;"' | tr -d '[:space:]')"
property="$(docker compose -f compose.marina-test.yaml exec -T postgres sh -lc 'psql -U marina_test -d marina_smart_test -tAc "SELECT name FROM properties WHERE code='\''THREE_CROWNS'\'';"' | sed 's/^ *//;s/ *$//')"

echo "Property: $property"
echo "Rooms: $rooms"
echo "Room types: $types"

if [ "$rooms" != "12" ] || [ "$types" != "3" ]; then
  echo "WARN: фонд уже изменён пользователем или это старая база. Для нового компактного теста используйте RESET_MARINA_TEST.command."
fi

docker compose -f compose.marina-test.yaml exec -T api   env CORE_API_URL=http://127.0.0.1:8000   python scripts/verify_marina_hotel_setup.py

echo
echo "MARINA SMART VERIFY = PASS"
echo "Admin/PMS: http://127.0.0.1:13101/"
echo "Staff:     http://127.0.0.1:13102/"
