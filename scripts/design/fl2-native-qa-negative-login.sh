#!/usr/bin/env bash
# Negative native auth E2E against QA only; generates a nonexistent username
# and wrong password per run. Never uploads real credentials or private logs.
set -euo pipefail
set +x
umask 077
origin='https://agent-vivobook-asuslaptop-x412ua.tail2066a4.ts.net/core'
test "${MARINA_QA_ORIGIN:-}" = "$origin" || { echo 'BLOCKED: non-QA origin'; exit 78; }
platform="${1:-}"
case "$platform" in android|ios) : ;; *) echo 'BLOCKED: invalid platform' >&2; exit 78;; esac
test "${MARINA_QA_ARTIFACT_VERIFIED:-}" = yes || { echo 'BLOCKED: unverified native QA binary' >&2; exit 78; }
curl -fsS --connect-timeout 8 --max-time 17 -o /dev/null "$origin/health/ready"
curl -fsS --connect-timeout 8 --max-time 17 "$origin/api/v1/auth/mode" |
  python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('mode')=='single_property'"
if [[ "$platform" = ios ]];then
 : "${IOS_SIMULATOR_UDID:?iOS simulator UDID required}"
fi
if [[ "$platform" = android ]];then
  apk='android-bin/app-release.apk'
  test -s "$apk" || { echo 'BLOCKED: verified QA APK missing'; exit 78; }
  adb wait-for-device
  # A stale Pixel Launcher ANR masked the negative-login screen in CI
  # (run 45049095691). Require full Android boot before UI testing.
  boot_ready=false
  for attempt in $(seq 1 45); do
    if [[ "$(adb shell getprop sys.boot_completed | tr -d '\r')" == 1 ]]; then
      boot_ready=true
      break
    fi
    sleep 2
  done
  test "$boot_ready" = true || { echo 'ANDROID_EMULATOR_BOOT_INCOMPLETE'; exit 78; }
  adb install -r "$apk" || { echo ANDROID_QA_APK_INSTALL_FAILED; exit 1; }
  package_path=$(adb shell pm path kg.go.ms.staff)
  [[ "$package_path" == *package:* ]] || { echo ANDROID_QA_PACKAGE_MISSING; exit 1; }
  # The Maestro flow launches the verified APK and checks the login form.
  echo 'ANDROID_QA_APK_INSTALLED_AFTER_BOOT_PASS'
fi
curl -fsSL https://get.maestro.mobile.dev -o /tmp/marina-maestro-qa-negative-install.sh
bash /tmp/marina-maestro-qa-negative-install.sh >/dev/null
maestro_bin="$HOME/.maestro/bin/maestro"
test -x "$maestro_bin"
# Use a real synthetic QA account to test a WRONG PASSWORD, never an unknown user.
# Only its username is read; the real password is never passed to Maestro here.
test -n "${MARINA_NATIVE_QA_USERS_JSON:-}" || { echo 'QA_CREDENTIAL_SECRET_MISSING'; exit 78; }
export MAESTRO_QA_EXISTING_USERNAME="$(python3 - <<'PY'
import json, os, re
data=json.loads(os.environ['MARINA_NATIVE_QA_USERS_JSON'])
assert isinstance(data,dict) and set(data)=={'OWNER','RECEPTION','COOK','WAITER','STORE_STAFF'}
name=data['OWNER']['username']
assert re.fullmatch(r'marina_nativeqa_[a-zA-Z0-9_-]{9,70}',name)
print(name)
PY
)"
export MAESTRO_INVALID_QA_PASSWORD="InvalidOnlyQA$(openssl rand -hex 18)"
# Independently verify the server rejects the known QA login's invalid password.
payload="$(python3 - <<'PY'
import json,os
print(json.dumps({'username':os.environ['MAESTRO_QA_EXISTING_USERNAME'],'password':os.environ['MAESTRO_INVALID_QA_PASSWORD']}))
PY
)"
status="$(curl -sS --connect-timeout 8 --max-time 17 -o /dev/null -w '%{http_code}' -H 'Content-Type: application/json' --data-binary "$payload" "$origin/api/v1/auth/login")"
unset payload
test "$status" = 401 || { echo "QA_WRONG_PASSWORD_HTTP_UNEXPECTED=$status"; exit 1; }
echo 'QA_EXISTING_USER_WRONG_PASSWORD_HTTP_401_PASS'
export MAESTRO_DRIVER_STARTUP_TIMEOUT=360000 MAESTRO_CLI_NO_ANALYTICS=true
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
mkdir -p native-qa-evidence
if ! "$maestro_bin" test scripts/design/fl2-native-qa-negative-login.yaml >"$dir/maestro.log" 2>&1;then
 if [[ "$platform" = android ]];then
   adb exec-out screencap -p >native-qa-evidence/negative-login-failure.png || true
 else
   xcrun simctl io "$IOS_SIMULATOR_UDID" screenshot native-qa-evidence/negative-login-failure.png || true
 fi
 printf 'QA_NATIVE_NEGATIVE_LOGIN_FAIL platform=%s (private log not uploaded)\n' "$platform"
 exit 1
fi
if [[ "$platform" = android ]];then
 adb exec-out screencap -p >native-qa-evidence/negative-login-pass.png
else
 xcrun simctl io "$IOS_SIMULATOR_UDID" screenshot native-qa-evidence/negative-login-pass.png
fi
test -s native-qa-evidence/negative-login-pass.png
printf 'QA_NATIVE_NEGATIVE_LOGIN_PASS platform=%s (expected 401 message; positive login not tested)\n' "$platform"
