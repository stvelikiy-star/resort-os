#!/usr/bin/env bash
set -euo pipefail
export PATH="$PWD/runtime/pg16/bin:$PATH"
for port in 55431 55432; do
  cluster="$PWD/runtime/acceptance-pg-$port"
  if [[ ! -d "$cluster" ]]; then initdb -U audit -D "$cluster" -A trust --locale=C --encoding=UTF8 >"evidence/init-$port.log"; fi
  "$PWD/runtime/pg16/bin/pg_ctl" -D "$cluster" -o "-h 127.0.0.1 -c unix_socket_directories= -p $port" -l "$cluster/server.log" -w start
  createdb -h 127.0.0.1 -p "$port" -U audit marina_fixture
done
