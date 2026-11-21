#!/usr/bin/env bash
# QA-only: verify native Android opens the trusted single-property login.
set -euo pipefail
EXPECTED='https://agent-vivobook-asuslaptop-x412ua.tail2066a4.ts.net/core'
test "${EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS:-}" = "$EXPECTED" || { echo "QA origin mismatch"; exit 78; }
mkdir -p android-qa-evidence
curl --fail --silent --show-error --connect-timeout 8 --max-time 18 -o /dev/null "$EXPECTED/health/ready"
adb install -r apps/mobile/android/app/build/outputs/apk/release/app-release.apk
curl -fsSL https://get.maestro.mobile.dev -o /tmp/marina-maestro-qa-install.sh
bash /tmp/marina-maestro-qa-install.sh
test -x "$HOME/.maestro/bin/maestro"
if ! "$HOME/.maestro/bin/maestro" test scripts/design/fl2-native-qa-connect.yaml >/tmp/marina-qa-connect-private.log 2>&1;then
  adb exec-out screencap -p > android-qa-evidence/failure-login.png || true
  echo 'NATIVE_QA_ANDROID_LOGIN_SCREEN_FAIL (private log not uploaded)'
  exit 1
fi
adb exec-out screencap -p > android-qa-evidence/login.png
test -s android-qa-evidence/login.png
echo 'NATIVE_QA_ANDROID_LOGIN_SCREEN_PASS; authentication NOT tested'
