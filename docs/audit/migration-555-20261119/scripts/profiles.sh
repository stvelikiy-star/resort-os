#!/usr/bin/env bash
set -euo pipefail
py=runtime/venv/bin/python
ready() {
 for i in {1..90}; do if curl --noproxy '*' -fsS http://127.0.0.1:18002/health >/dev/null 2>&1; then return; fi; sleep .2; done
 return 1
}
# Stop only our previously recorded new-API process in the calling shell first.
bash scripts/api.sh new false BETA >runtime/beta-api.log 2>&1 & server=$!
ready
$py scripts/readback.py BETA
kill -TERM "$server"; wait "$server" || true
bash scripts/api.sh new true ALPHA >runtime/customer-api.log 2>&1 & server=$!
ready
$py scripts/site-modes.py customer
kill -TERM "$server"; wait "$server" || true
