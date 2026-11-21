#!/usr/bin/env bash
# Test-only native Android demo QA. Runs INSIDE one bash process because
# reactivecircus/android-emulator-runner@v2 invokes each script line via sh -c.
# No hotel credentials, API writes, or production endpoints are used.
set -euo pipefail

test "${CI:-}" = "true"
test -n "${ANDROID_HOME:-}"
mkdir -p android-emulator-evidence

bash scripts/design/fl2-android-emulator-smoke.sh
python3 scripts/design/fl2-android-owner-reception-demo.py

curl --fail --silent --show-error --location https://get.maestro.mobile.dev --output /tmp/marina-install-maestro.sh
bash /tmp/marina-install-maestro.sh
maestro_bin="${HOME}/.maestro/bin/maestro"
test -x "$maestro_bin"
"$maestro_bin" --version

for role in owner reception cook waiter; do
  case "$role" in owner|reception|cook|waiter) : ;; *) exit 10 ;; esac
  cat > /tmp/marina-native-demo.yaml <<EOF
appId: kg.go.ms.staff
---
- launchApp:
    clearState: true
- assertVisible:
    id: "connect-demo-${role}"
- tapOn:
    id: "connect-demo-${role}"
- extendedWaitUntil:
    visible: ".*DEMO.*"
    timeout: 30000
EOF
  "$maestro_bin" test /tmp/marina-native-demo.yaml
  adb exec-out screencap -p > "android-emulator-evidence/maestro-${role}.png"
  test -s "android-emulator-evidence/maestro-${role}.png"
done

printf '%s\n' 'ANDROID_NATIVE_MAESTRO_DEMO_4_ROLES_PASS; live hotel roles NOT YET TESTED'
