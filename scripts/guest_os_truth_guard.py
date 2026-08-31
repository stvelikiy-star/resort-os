#!/usr/bin/env python3
"""Protect Guest OS public copy from drifting behind the live Resort Core workflow."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "apps/web/components/GuestOsRuntime.tsx"
PAGE = ROOT / "apps/web/app/g/[token]/page.tsx"
REQUESTS = ROOT / "apps/web/components/GuestRequestsPanel.tsx"

REQUIRED_RUNTIME = [
    "Заявки из Guest OS уже передаются через Resort Core ответственному сотруднику",
    "Статус выполнения можно отслеживать ниже в разделе «Мои заявки»",
    "Guest OS requests are already routed through Resort Core to the responsible team",
    "Guest OS аркылуу түзүлгөн өтүнмөлөр Resort Core аркылуу жооптуу кызматкерге дароо жөнөтүлөт",
]

FORBIDDEN_FUTURE_COPY = [
    "На следующем операционном шаге",
    "Кийинки операциялык этапта",
    "The next operational stage will route requests",
]


def main() -> int:
    errors: list[str] = []
    for path in (RUNTIME, PAGE, REQUESTS):
        if not path.exists():
            errors.append(f"missing Guest OS file: {path.relative_to(ROOT)}")

    runtime = RUNTIME.read_text(encoding="utf-8") if RUNTIME.exists() else ""
    page = PAGE.read_text(encoding="utf-8") if PAGE.exists() else ""
    requests = REQUESTS.read_text(encoding="utf-8") if REQUESTS.exists() else ""

    for snippet in REQUIRED_RUNTIME:
        if snippet not in runtime:
            errors.append(f"GuestOsRuntime missing live-request truth: {snippet!r}")
    for stale in FORBIDDEN_FUTURE_COPY:
        if stale in runtime:
            errors.append(f"GuestOsRuntime still presents implemented request routing as future work: {stale!r}")

    if "<GuestRequestsPanel token={token} />" not in page:
        errors.append("Guest OS route no longer mounts My Requests / request creation panel")
    if "/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/requests" not in requests:
        errors.append("GuestRequestsPanel no longer uses the canonical Resort Core guest-request endpoint")
    if "credentials: \"include\"" not in requests:
        errors.append("GuestRequestsPanel must preserve authenticated GuestSession credentials")

    print("Three Crowns Guest OS truth guard")
    print(f"FACT: live_request_copy={len(REQUIRED_RUNTIME)}")
    print(f"FACT: future_copy_forbidden={len(FORBIDDEN_FUTURE_COPY)}")
    print(f"FACT: request_panel_mounted={'<GuestRequestsPanel token={token} />' in page}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: Guest OS describes the request workflow that is actually implemented")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
