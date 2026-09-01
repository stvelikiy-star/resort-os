#!/usr/bin/env python3
"""Protect Guest Concierge public copy from drifting behind the live Resort Core workflow."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "apps/web/components/GuestConciergeRuntime.tsx"
PAGE = ROOT / "apps/web/app/g/[token]/page.tsx"

REQUIRED_RUNTIME = [
    "Заявка отправлена. Статус появится в разделе «Мои заявки».",
    "Өтүнмө жөнөтүлдү. Абалы «Менин өтүнмөлөрүм» бөлүмүндө көрүнөт.",
    "Request sent. Its status will appear under My requests.",
]

FORBIDDEN_FUTURE_COPY = [
    "На следующем операционном шаге",
    "Кийинки операциялык этапта",
    "The next operational stage will route requests",
]


def main() -> int:
    errors: list[str] = []
    for path in (RUNTIME, PAGE):
        if not path.exists():
            errors.append(f"missing Guest Concierge file: {path.relative_to(ROOT)}")

    runtime = RUNTIME.read_text(encoding="utf-8") if RUNTIME.exists() else ""
    page = PAGE.read_text(encoding="utf-8") if PAGE.exists() else ""

    for snippet in REQUIRED_RUNTIME:
        if snippet not in runtime:
            errors.append(f"GuestConciergeRuntime missing live-request truth: {snippet!r}")
    for stale in FORBIDDEN_FUTURE_COPY:
        if stale in runtime:
            errors.append(f"GuestConciergeRuntime still presents implemented request routing as future work: {stale!r}")

    if "<GuestConciergeRuntime token={token} />" not in page:
        errors.append("Guest room QR route no longer mounts the unified concierge")
    if "GuestRequestsPanel" in page or "GuestOsRuntime" in page:
        errors.append("Guest room QR route still mounts duplicate legacy Guest OS surfaces")

    canonical_requests = "/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/requests"
    if canonical_requests not in runtime:
        errors.append("GuestConciergeRuntime no longer uses the canonical Resort Core guest-request endpoint")
    if 'credentials: "include"' not in runtime:
        errors.append("GuestConciergeRuntime must preserve authenticated GuestSession credentials")
    if "setInterval(() => void loadRequests(), 15000)" not in runtime:
        errors.append("GuestConciergeRuntime must keep request-status refresh/polling")
    for commercial_path in ("/payments", "/reservation-payments", "/beach/charge", "/nfc"):
        if commercial_path in runtime:
            errors.append(f"Guest concierge must not introduce commercial/deferred mutation route: {commercial_path}")

    print("Three Crowns Guest Concierge truth guard")
    print(f"FACT: live_request_copy={len(REQUIRED_RUNTIME)}")
    print(f"FACT: future_copy_forbidden={len(FORBIDDEN_FUTURE_COPY)}")
    print(f"FACT: unified_concierge_mounted={'<GuestConciergeRuntime token={token} />' in page}")
    print(f"FACT: canonical_request_endpoint={canonical_requests in runtime}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: Guest Concierge describes and uses the request workflow that is actually implemented")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
