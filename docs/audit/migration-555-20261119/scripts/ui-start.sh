#!/usr/bin/env bash
set -eu
n=0
for v in old new; do
  api=18001; if [[ $v == new ]]; then api=18002; fi
  for a in web staff admin; do
    n=$((n+1))
    (cd "runtime/ui/$v/$a" && CORE_API_URL="http://127.0.0.1:$api" NEXT_TELEMETRY_DISABLED=1 exec node_modules/.bin/next dev -H 127.0.0.1 -p "$((18100+n))" >dev.log 2>&1) &
  done
done
wait
