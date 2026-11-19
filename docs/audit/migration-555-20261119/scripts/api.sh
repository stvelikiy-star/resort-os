#!/usr/bin/env bash
set -eu
case "$1" in old) p=55431; a=18001;; new) p=55432; a=18002;; *) exit 2;; esac
exec env -i PATH="$PATH" HOME="$HOME" LANG=C.UTF-8 PROPERTY_CODE="${3:-ALPHA}" APP_ENV=test DATABASE_URL="postgresql://audit@127.0.0.1:$p/${4:-marina_fixture}" MARINA_CUSTOMER_SITE_SAFE_MODE="${2:-false}" ENABLE_PAYMENT_OPERATIONS=false ENABLE_MKASSA=false ENABLE_SERVICE_POINT_QR=false "$PWD/runtime/venv/bin/python" -m uvicorn app.app_entry:app --app-dir "$1/services/api" --host 127.0.0.1 --port "$a"
