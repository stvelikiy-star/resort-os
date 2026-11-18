#!/usr/bin/env python3
"""Read-only Premium Motion source contract for MARINA SMART Admin/Staff/Mobile.

Checks only the shared motion layer and the existing primitives it updates.
It intentionally does NOT replace browser/Android/physical-device acceptance.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "packages/design/premium-motion.css"
MOBILE_TOKENS = ROOT / "apps/mobile/src/theme/tokens.ts"
MOBILE_MOTION = ROOT / "apps/mobile/src/theme/motion.ts"
MOBILE_COMPONENTS = ROOT / "apps/mobile/src/components/Motion.tsx"

def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)

css = CSS.read_text(encoding="utf-8")
mobile = MOBILE_TOKENS.read_text(encoding="utf-8")
motion = MOBILE_MOTION.read_text(encoding="utf-8")
components = MOBILE_COMPONENTS.read_text(encoding="utf-8")
future = (ROOT / "apps/mobile/src/components/Future.tsx").read_text(encoding="utf-8")
ui = (ROOT / "apps/mobile/src/components/ui.tsx").read_text(encoding="utf-8")

# Both runtimes express the same allowed tempo. Each platform has one
# canonical file; section CSS/screens are not allowed to invent timing values.
for name, milliseconds in (("quick", 120), ("standard", 200), ("deliberate", 320)):
    check(f"--marina-motion-{name}: {milliseconds}ms;" in css, f"CSS missing {name} motion token")
    check(re.search(rf"\b{name}:\s*{milliseconds}\b", mobile) is not None,
          f"Mobile missing {name} motion token")
check("--marina-motion-stagger: 40ms;" in css, "Web card stagger must be 40ms")
check(re.search(r"cardStagger:\s*40", mobile) is not None, "Mobile card stagger must be 40ms")
check(re.search(r"maxStaggerCards:\s*7", mobile) is not None, "Mobile stagger must cap at 8 cards")
check("chart: MOTION_DURATION.deliberate" in mobile, "Charts must not use 700ms")
check("duration: motionPresets.sheetOut.duration, easing: motionPresets.sheetOut.easing" in components,
      "Bottom Sheet exit must use the existing shared motion preset")
check("speed: motion.spring.speed" in components, "Tab spring must use the existing shared spring")
check("duration: 650" not in future and "duration: 1700" not in future,
      "Mobile bounded shimmer and orb must use shared duration tokens")
check("transformOrigin: 'left center'" in ui and "useNativeDriver: true" in ui,
      "Progress bar must use the native driver and stay anchored to its left edge")
check("width: progress.interpolate" not in ui,
      "Do not animate progress-bar width/layout; use transform scaleX")


for app in ("admin", "staff"):
    layout = (ROOT / f"apps/{app}/app/layout.tsx").read_text(encoding="utf-8")
    check('import "../../../packages/design/premium-motion.css";' in layout,
          f"{app} must import the shared CSS exactly once")

# The premium layer may only use explicit canonical durations. All entrances
# are finite and use native/composited opacity/transform, not layout dimensions.
duration_literals = set(re.findall(r"(?<![\w-])(\d+)ms\b", css))
check(duration_literals == {"120", "200", "320", "40"},
      f"Non-token CSS duration found: {sorted(duration_literals)}")
check("animation-iteration-count: infinite" not in css and "transition: all" not in css,
      "Unbounded/blanket animations are forbidden")
check("@media (prefers-reduced-motion: no-preference)" in css, "No-preference opt-in missing")
check("@media (prefers-reduced-motion: reduce)" in css, "Reduced Motion guard missing")
check(':not(:disabled):active' in css, "Disabled actions must not animate")
check('[data-server-confirmed="true"]' in css, "Success must require explicit server confirmation")
check(".shift-modal" in css and ".shift-task" in css and ".fl2-nav-group" in css,
      "Admin and Staff motion surface hooks missing")

names = re.findall(r"@keyframes\s+(marina-motion-[\w-]+)", css)
check(len(names) == 8 and len(names) == len(set(names)), "Expected eight unique finite keyframe patterns")
for match in re.finditer(r"\b(?:from|to)\s*\{([^}]+)\}", css):
    declarations = [d.strip().split(":", 1)[0] for d in match.group(1).split(";") if d.strip()]
    check(all(p in {"opacity", "transform"} for p in declarations),
          f"Keyframe includes non-composited property: {declarations}")

for path in ("apps/admin/app/fl2-shell.css",
             "apps/admin/app/fl2-ui-kit.css",
             "apps/admin/app/fl2-interaction-polish.css",
             "apps/admin/app/fl2-owner-dashboard.css"):
    text = (ROOT / path).read_text(encoding="utf-8")
    check(re.search(r"\b(?:120|150|160|180|200|220|240|320|340|360|700)ms\b", text) is None,
          f"Un-tokenized legacy duration in the adapted Admin motion surface: {path}")

print("MARINA PREMIUM MOTION CONTRACT PASS: canonical 120/200/320ms, bounded stagger, no unsafe success, Reduced Motion, Admin/Staff/Mobile aligned.")
