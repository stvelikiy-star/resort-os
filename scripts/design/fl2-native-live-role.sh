#!/usr/bin/env bash
# MANUAL/PROTECTED RUNNER ONLY: never include QA credentials in repository or logs.
set -euo pipefail
set +x
umask 077
EXPECTED_ORIGIN='https://agent-vivobook-asuslaptop-x412ua.tail2066a4.ts.net/core'
: "${MARINA_QA_ORIGIN:?QA origin required}"
: "${MARINA_QA_USERNAME:?Synthetic QA username required}"
: "${MARINA_QA_PASSWORD:?Temporary QA password required}"
: "${MARINA_QA_ROLE:?Role required}"
if [[ "$MARINA_QA_ORIGIN" != "$EXPECTED_ORIGIN" ]];then
  printf '%s\n' 'BLOCKED: origin is not MARINA_FINAL_QA' >&2
  exit 78
fi
if [[ ! "$MARINA_QA_USERNAME" =~ ^marina_(extqa|nativeqa|qa)_[a-zA-Z0-9_-]+$ ]];then
  printf '%s\n' 'BLOCKED: only synthetic QA users allowed' >&2
  exit 78
fi
case "$MARINA_QA_ROLE" in
  OWNER) expected=tab-overview ;;
  RECEPTION) expected=tab-reception ;;
  COOK) expected=tab-kitchen ;;
  WAITER) expected=tab-dining ;;
  STORE_STAFF) expected=tab-store ;;
  *) printf '%s\n' 'BLOCKED: unknown QA role' >&2; exit 78 ;;
esac
if [[ "${#MARINA_QA_PASSWORD}" -lt 16 ]];then
  printf '%s\n' 'BLOCKED: temporary password is too short' >&2
  exit 78
fi
command -v maestro >/dev/null 2>&1 || { echo 'BLOCKED: Maestro not installed' >&2; exit 78; }
if [[ "${MARINA_NATIVE_QA_BUILD_ORIGIN:-}" != "$EXPECTED_ORIGIN" ]];then
  echo 'BLOCKED: native app build origin was not attested' >&2
  exit 78
fi
curl -fsS --connect-timeout 7 --max-time 15 -o /dev/null "$EXPECTED_ORIGIN/health/ready" || {
  echo 'BLOCKED: QA HTTPS endpoint not reachable' >&2; exit 78;
}
export MAESTRO_CLI_NO_ANALYTICS=true
export MAESTRO_DRIVER_STARTUP_TIMEOUT=360000
export MAESTRO_QA_USERNAME="$MARINA_QA_USERNAME"
export MAESTRO_QA_PASSWORD="$MARINA_QA_PASSWORD"
export MAESTRO_QA_EXPECTED_TAB="$expected"
private_dir=$(mktemp -d)
trap 'rm -rf "$private_dir"' EXIT
if ! maestro test "$(dirname "$0")/fl2-native-live-role.yaml" >"$private_dir/maestro.log" 2>&1;then
  printf '%s\n' "LIVE_NATIVE_QA_FAIL role=$MARINA_QA_ROLE (private log not uploaded)"
  exit 1
fi
printf '%s\n' "LIVE_NATIVE_ROLE_LOGIN_PASS $MARINA_QA_ROLE (synthetic MARINA_FINAL_QA only)"
