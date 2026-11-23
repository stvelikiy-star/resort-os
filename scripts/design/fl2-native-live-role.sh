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
# Two separate Maestro phases produce distinguishable results. Never upload
# raw Maestro logs: the flow contains synthetic passwords in environment vars.
emit_safe_failure() {
  local phase="$1" private_log="$2" cause="UNCLASSIFIED_UI_FAILURE"
  if grep -Fq 'Save Password?' "$private_log"; then
    cause="IOS_PASSWORD_AUTOFILL_OVERLAY_OBSERVED"
  elif grep -Fq 'login-username' "$private_log"; then
    cause="SIGN_IN_TRANSITION_OR_FIELD"
  elif grep -Fq 'tab-' "$private_log"; then
    cause="EXPECTED_ROLE_TAB_NOT_VISIBLE"
  fi
  printf '%s\n' "LIVE_NATIVE_QA_FAIL role=$MARINA_QA_ROLE phase=$phase reason=$cause (private log not uploaded)"
}
if ! maestro test "$(dirname "$0")/fl2-native-live-role.yaml" >"$private_dir/auth.log" 2>&1;then
  emit_safe_failure AUTH_TRANSITION "$private_dir/auth.log"
  exit 1
fi
printf '%s\n' "LIVE_NATIVE_AUTH_TRANSITION_PASS $MARINA_QA_ROLE (synthetic MARINA_FINAL_QA only)"
if ! maestro test "$(dirname "$0")/fl2-native-live-dashboard.yaml" >"$private_dir/dashboard.log" 2>&1;then
  emit_safe_failure ROLE_UI "$private_dir/dashboard.log"
  exit 1
fi
printf '%s\n' "LIVE_NATIVE_ROLE_UI_PASS $MARINA_QA_ROLE"
printf '%s\n' "LIVE_NATIVE_ROLE_LOGIN_PASS $MARINA_QA_ROLE (synthetic MARINA_FINAL_QA only)"
