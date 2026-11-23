#!/usr/bin/env bash
# Five-role native LIVE login, only synthetic MARINA_FINAL_QA accounts.
# Credentials stay in protected CI environment; no logfile or screenshot contains a password.
set -euo pipefail
set +x
umask 077
expected='https://agent-vivobook-asuslaptop-x412ua.tail2066a4.ts.net/core'
test "${MARINA_QA_ORIGIN:-}" = "$expected" || { echo 'QA_ORIGIN_BLOCK'; exit 78; }
test "${MARINA_NATIVE_QA_BUILD_ORIGIN:-}" = "$expected" || { echo 'QA_BUILD_ORIGIN_BLOCK'; exit 78; }
test "${MARINA_QA_ARTIFACT_VERIFIED:-}" = yes || { echo 'QA_BINARY_PROVENANCE_BLOCK'; exit 78; }
test -n "${MARINA_NATIVE_QA_USERS_JSON:-}" || { echo 'QA_CREDENTIAL_SECRET_MISSING'; exit 78; }
case "${1:-}" in android|ios) platform="$1";; *) echo 'PLATFORM_BLOCK'; exit 78;; esac
mkdir -p native-five-roles-evidence
curl -fsS --max-time 18 "$expected/health/ready" >/dev/null
curl -fsS --max-time 18 "$expected/api/v1/auth/mode" | python3 -c 'import json,sys; assert json.load(sys.stdin)["mode"]=="single_property"'
private=$(mktemp -d)
trap 'rm -rf "$private"' EXIT
python3 - "$private" <<'PY'
import os,sys,json,re,pathlib
p=pathlib.Path(sys.argv[1])
d=json.loads(os.environ["MARINA_NATIVE_QA_USERS_JSON"])
roles=("OWNER","RECEPTION","COOK","WAITER","STORE_STAFF")
assert isinstance(d,dict) and set(d)==set(roles)
for role in roles:
 c=d[role]
 assert set(c)=={"username","password"}
 assert re.fullmatch(r"marina_nativeqa_[a-zA-Z0-9_-]{9,70}",c["username"])
 assert len(c["password"])>=22 and all(ch.isalnum() for ch in c["password"])
 f=p/role;f.write_text(c["username"]+"\n"+c["password"]+"\n");f.chmod(0o600)
print("QA_FIVE_ROLE_SECRET_STRUCTURE_PASS (credentials hidden)")
PY
if [[ "$platform" == android ]];then
  adb install -r android-bin/app-release.apk >/dev/null
else
  : "${IOS_SIMULATOR_UDID:?iPhone simulator required}"
fi
curl --fail --silent --show-error --location https://get.maestro.mobile.dev --output "$private/install-maestro.sh"
bash "$private/install-maestro.sh" >"$private/install.log" 2>&1
export PATH="$HOME/.maestro/bin:$PATH"
command -v maestro >/dev/null || { echo "MAESTRO_NOT_FOUND"; exit 78; }
# Isolate every role: a stuck Maestro process must not consume the whole CI job.
# All raw output stays in the runner-local 0700 directory and is never uploaded.
run_bounded_private() {
  local private_log="$1" seconds="$2"
  shift 2
  python3 - "$private_log" "$seconds" "$@" <<'PY'
import os, re, signal, subprocess, sys
log_file, limit, *command = sys.argv[1:]
with open(log_file, "w", encoding="utf-8") as handle:
    process = subprocess.Popen(command, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        result = process.wait(timeout=int(limit))
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        print("NATIVE_QA_PHASE_TIMEOUT seconds=" + limit, flush=True)
        sys.exit(124)
# Only known-safe markers are printed. Maestro logs can include QA credentials.
with open(log_file, encoding="utf-8", errors="replace") as handle:
    for line in handle:
        if re.match(r"^(LIVE_NATIVE_(AUTH_TRANSITION_PASS|ROLE_UI_PASS|ROLE_LOGIN_PASS|QA_FAIL)|BLOCKED: QA HTTPS endpoint not reachable)", line):
            print(line.strip(), flush=True)
sys.exit(result)
PY
}
failures=0
last_role_pass=false
for role in OWNER RECEPTION COOK WAITER STORE_STAFF;do
  IFS= read -r qa_username <"$private/$role"
  qa_password=$(sed -n '2p' "$private/$role")
  test -n "$qa_username" && test -n "$qa_password"
  export MARINA_QA_USERNAME="$qa_username" MARINA_QA_PASSWORD="$qa_password" MARINA_QA_ROLE="$role"
  unset qa_username qa_password
  unset MAESTRO_QA_USERNAME MAESTRO_QA_PASSWORD
  echo "LIVE_NATIVE_ROLE_START $role"
  status=0
  run_bounded_private "$private/role-$role.log" 600 bash scripts/design/fl2-native-live-role.sh || status=$?
  if (( status != 0 ));then
    echo "LIVE_NATIVE_ROLE_FAIL $role exit=$status (private logs retained only until job exit)"
    failures=$((failures + 1))
    if [[ "$platform" == android ]]; then
      adb exec-out screencap -p >"native-five-roles-evidence/failure-$role.png" || true
    else
      xcrun simctl io "$IOS_SIMULATOR_UDID" screenshot "native-five-roles-evidence/failure-$role.png" || true
    fi
    last_role_pass=false
  else
    if [[ "$platform" == android ]];then
      adb exec-out screencap -p >"native-five-roles-evidence/$role.png"
    else
      xcrun simctl io "$IOS_SIMULATOR_UDID" screenshot "native-five-roles-evidence/$role.png"
    fi
    test -s "native-five-roles-evidence/$role.png"
    echo "LIVE_NATIVE_ROLE_CONFIRMED $role"
    last_role_pass=true
  fi
  unset MARINA_QA_USERNAME MARINA_QA_PASSWORD MARINA_QA_ROLE
done
if (( failures == 0 )); then
  echo "MARINA_NATIVE_LIVE_QA_5_OF_5_ROLE_LOGIN_PASS_$platform"
else
  echo "MARINA_NATIVE_LIVE_QA_ROLE_FAILURES=$failures"
fi
# Logout/restart is meaningful only if the last role remains logged in.
if [[ "$last_role_pass" != true ]]; then
  echo "MARINA_NATIVE_LOGOUT_RESTART_NOT_EXECUTED_NO_AUTHENTICATED_LAST_ROLE"
  exit 1
fi
logout_status=0
run_bounded_private "$private/logout-restart.log" 300 maestro test scripts/design/fl2-native-qa-logout-restart.yaml || logout_status=$?
if (( logout_status != 0 ));then
  if [[ "$platform" == android ]]; then
    adb exec-out screencap -p >"native-five-roles-evidence/failure-logout-restart.png" || true
  else
    xcrun simctl io "$IOS_SIMULATOR_UDID" screenshot "native-five-roles-evidence/failure-logout-restart.png" || true
  fi
  echo "MARINA_NATIVE_LOGOUT_RESTART_FAIL_$platform exit=$logout_status (private log not uploaded)"
  exit 1
fi
echo "MARINA_NATIVE_LOGOUT_RESTART_LOGIN_REQUIRED_PASS_$platform"
(( failures == 0 )) || exit 1
