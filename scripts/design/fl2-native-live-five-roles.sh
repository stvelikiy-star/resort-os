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
for role in OWNER RECEPTION COOK WAITER STORE_STAFF;do
  IFS= read -r qa_username <"$private/$role"
  qa_password=$(sed -n '2p' "$private/$role")
  test -n "$qa_username" && test -n "$qa_password"
  export MARINA_QA_USERNAME="$qa_username" MARINA_QA_PASSWORD="$qa_password" MARINA_QA_ROLE="$role"
  unset qa_username qa_password
  unset MAESTRO_QA_USERNAME MAESTRO_QA_PASSWORD
  if ! bash scripts/design/fl2-native-live-role.sh;then
    if [[ "$platform" == android ]];then
      adb exec-out screencap -p >"native-five-roles-evidence/failure-$role.png" || true
    else
      xcrun simctl io "$IOS_SIMULATOR_UDID" screenshot "native-five-roles-evidence/failure-$role.png" || true
    fi
    exit 1
  fi
  if [[ "$platform" == android ]];then
    adb exec-out screencap -p >"native-five-roles-evidence/$role.png"
  else
    xcrun simctl io "$IOS_SIMULATOR_UDID" screenshot "native-five-roles-evidence/$role.png"
  fi
  test -s "native-five-roles-evidence/$role.png"
  unset MARINA_QA_USERNAME MARINA_QA_PASSWORD MARINA_QA_ROLE
done
echo "MARINA_NATIVE_LIVE_QA_5_OF_5_ROLE_LOGIN_PASS_$platform"
# Verify a normal staff logout and a cold restart on the SAME native install.
# This test has no credentials: login again must be mandatory.
if ! maestro test scripts/design/fl2-native-qa-logout-restart.yaml >"$private/logout-restart.log" 2>&1; then
  if [[ "$platform" == android ]]; then
    adb exec-out screencap -p >"native-five-roles-evidence/failure-logout-restart.png" || true
  else
    xcrun simctl io "$IOS_SIMULATOR_UDID" screenshot "native-five-roles-evidence/failure-logout-restart.png" || true
  fi
  echo "MARINA_NATIVE_LOGOUT_RESTART_FAIL_$platform (private log not uploaded)"
  exit 1
fi
echo "MARINA_NATIVE_LOGOUT_RESTART_LOGIN_REQUIRED_PASS_$platform"
