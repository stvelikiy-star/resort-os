#!/usr/bin/env bash
# Native Android emulator runtime smoke, isolated CI only.
# Not a physical Android E2E and not an authenticated hotel integration test.
set -euo pipefail
app='kg.go.ms.staff'
apk='apps/mobile/android/app/build/outputs/apk/release/app-release.apk'
mkdir -p android-emulator-evidence
test -s "$apk"
adb wait-for-device
test "$(adb shell getprop sys.boot_completed | tr -d '\r')" = '1'
adb install -r "$apk"
adb shell pm path "$app" | grep -q 'base.apk'
adb logcat -c
adb shell am force-stop "$app" || true
adb shell monkey -p "$app" -c android.intent.category.LAUNCHER 1
sleep 18
if ! adb shell pidof "$app" >/dev/null; then
  echo "BLOCKED: app is not running after first native Android launch" >&2
  adb logcat -d -t 250 -s AndroidRuntime:E ReactNativeJS:E || true
  exit 1
fi
adb exec-out screencap -p > android-emulator-evidence/first-launch.png
adb shell uiautomator dump /sdcard/window.xml >/dev/null 2>&1 || true
adb pull /sdcard/window.xml android-emulator-evidence/ui-hierarchy.xml >/dev/null 2>&1 || true
# Cold-start and background/foreground cycle; do not create hotel bookings.
adb shell input keyevent KEYCODE_HOME
sleep 2
adb shell monkey -p "$app" -c android.intent.category.LAUNCHER 1
sleep 8
adb shell pidof "$app" >/dev/null || { echo 'BLOCKED: app did not survive resume' >&2; exit 1; }
adb exec-out screencap -p > android-emulator-evidence/resume.png
# Offline transitions are a native stability smoke, NOT a real network failover test.
adb shell svc wifi disable || true
adb shell svc data disable || true
sleep 3
adb shell pidof "$app" >/dev/null || { echo 'BLOCKED: native app crashed during connectivity transition' >&2; exit 1; }
adb exec-out screencap -p > android-emulator-evidence/connectivity-transition.png
adb shell svc wifi enable || true
adb shell svc data enable || true
adb logcat -d -v threadtime -s AndroidRuntime:E ReactNativeJS:E > android-emulator-evidence/runtime-errors.log || true
if grep -E 'FATAL EXCEPTION|Process: kg.go.ms.staff|Unable to start activity' android-emulator-evidence/runtime-errors.log; then
  echo 'BLOCKED: native fatal exception recorded' >&2
  exit 1
fi
cat > android-emulator-evidence/scope.txt <<'SCOPE'
Emulated Android native installation, boot, foreground/resume and connectivity-transition smoke.
NOT a physical Android, Expo Go, real TLS trust chain, login, booking or business-data E2E.
Synthetic/no live hotel credentials; no production/Ubuntu/ASKA TASH access.
SCOPE
echo 'MARINA_ANDROID_EMULATOR_NATIVE_SMOKE_PASS'
