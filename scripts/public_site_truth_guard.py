#!/usr/bin/env python3
"""Fail closed when the public Three Crowns site drifts from owner-approved V1 truth."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PUBLIC_FILES = [
    ROOT / "apps/web/app/page.tsx",
    ROOT / "apps/web/app/layout.tsx",
    ROOT / "apps/web/app/rooms/page.tsx",
    ROOT / "apps/web/app/rooms/[slug]/page.tsx",
    ROOT / "apps/web/components/BookingWidget.tsx",
    ROOT / "apps/web/components/PublicUiI18nRuntime.tsx",
    ROOT / "apps/web/components/SiteContentRuntime.tsx",
    ROOT / "apps/web/lib/roomCatalog.ts",
    ROOT / "apps/web/lib/publicLocale.ts",
    ROOT / "apps/web/lib/siteContent.ts",
    ROOT / "apps/web/lib/publicAnalytics.ts",
    ROOT / "services/api/data/site_content_defaults.json",
]

# These rules are stale commercial/payment rules, owner-rejected sports AMENITIES,
# or amenities whose CURRENT operational availability has not been canonicalized
# for public promotion. Hosting an organized/sports group is not itself an amenity
# claim and remains allowed as long as no gym/field/court/ground is promised.
# Sauna, billiards and the conference hall are no longer forbidden here: their
# owner-approved facts are protected separately by current source/default content.
FORBIDDEN_PATTERNS = {
    "fixed 30 percent prepayment": re.compile(r"30\s*%[^\n]{0,80}предоплат|предоплат[^\n]{0,80}30\s*%", re.I),
    "stale two-day unpaid hold": re.compile(r"(?:через\s+)?2\s+дн(?:я|ей)[^\n]{0,100}(?:брон|предоплат|оплат)|(?:брон|предоплат|оплат)[^\n]{0,100}2\s+дн(?:я|ей)", re.I),
    "fixed first-night prepayment": re.compile(r"предоплат[^\n]{0,80}(?:перв(?:ые|ую|ой)?\s+(?:сут|ноч))", re.I),
    "unverified online card acquiring": re.compile(r"(?:visa|mastercard|карт(?:ой|а|ы))[^\n]{0,120}(?:онлайн\s+на\s+сайт|online\s+on\s+(?:the\s+)?site)|(?:онлайн\s+на\s+сайт|online\s+on\s+(?:the\s+)?site)[^\n]{0,120}(?:visa|mastercard|карт)", re.I),
    "unverified elsom payment route": re.compile(r"\b(?:элсом|elsom)\b", re.I),
    "owner-rejected gym claim": re.compile(r"\b(?:gym|тренаж[её]рн(?:ый|ого|ом|ые|ых)?\s+зал)\b", re.I),
    "owner-rejected sports grounds claim": re.compile(r"(?:спорт(?:ивн\w*)?\s+(?:площад\w*|пол\w*|корт\w*)|sports?\s+(?:field|court|ground)s?)", re.I),
    "uncanonicalized laundry claim": re.compile(r"прачечн", re.I),
    "uncanonicalized conference media": re.compile(r"conference\.webp", re.I),
}

REMOTE_MEDIA_PATTERNS = [
    re.compile(r"<(?:img|Image)\b[^>]*\bsrc\s*=\s*[\"']https?://", re.I),
    re.compile(r"background(?:-image)?\s*:[^;\n]*url\(\s*[\"']?https?://", re.I),
]

REQUIRED_SNIPPETS = {
    ROOT / "apps/web/app/page.tsx": [
        "Собственный пляж",
        "Пирс длиной 150 метров",
        "Открытый бассейн 15×8 м",
        "Номер автоматически не блокируется",
        "roomCategories",
    ],
    ROOT / "apps/web/components/BookingWidget.tsx": [
        "/core/api/v1/booking/check-availability",
        "/core/api/v1/booking/requests",
        "Заявка ещё не является подтверждённой бронью",
    ],
    ROOT / "apps/web/app/rooms/page.tsx": [
        "Заявка ≠ подтверждённая бронь",
        "номер автоматически не блокируется",
    ],
    ROOT / "apps/web/lib/siteContent.ts": [
        "Конференц-зал для мероприятий от 20 до 120 гостей",
        "Банкетное меню и формат обслуживания согласовываются индивидуально",
        "+996 558 08 50 02",
    ],
    ROOT / "services/api/data/site_content_defaults.json": [
        "Конференц-зал для мероприятий от 20 до 120 гостей",
        "Банкетное меню и формат обслуживания согласовываются индивидуально",
    ],
    ROOT / "apps/web/lib/publicAnalytics.ts": [
        "ALLOWED_PAYLOAD_KEYS",
        "Public analytics rejected non-allowlisted field",
        "Public analytics rejected non-scalar field",
    ],
}

ANALYTICS_SENSITIVE_KEYS = (
    "name",
    "guest_name",
    "guestName",
    "phone",
    "email",
    "note",
    "notes",
    "request_id",
    "requestId",
    "check_in",
    "check_out",
    "checkIn",
    "checkOut",
    "date",
    "dates",
)


def main() -> int:
    errors: list[str] = []
    texts: dict[Path, str] = {}

    for path in PUBLIC_FILES:
        if not path.exists():
            errors.append(f"missing protected public file: {path.relative_to(ROOT)}")
            continue
        texts[path] = path.read_text(encoding="utf-8")

    for path, text in texts.items():
        rel = path.relative_to(ROOT)
        for label, pattern in FORBIDDEN_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"{rel}: {label}")
        for pattern in REMOTE_MEDIA_PATTERNS:
            if pattern.search(text):
                errors.append(f"{rel}: remote/hotlinked media is forbidden")

    for path, snippets in REQUIRED_SNIPPETS.items():
        text = texts.get(path, "")
        for snippet in snippets:
            if snippet not in text:
                errors.append(f"{path.relative_to(ROOT)}: missing required public-truth snippet {snippet!r}")

    catalog = texts.get(ROOT / "apps/web/lib/roomCatalog.ts", "")
    category_count = len(re.findall(r'^\s+index:\s+"\d{2}",\s*$', catalog, re.M))
    if category_count != 12:
        errors.append(f"roomCatalog.ts: expected 12 public categories, found {category_count}")

    analytics = texts.get(ROOT / "apps/web/lib/publicAnalytics.ts", "")
    allowlist_match = re.search(
        r"const\s+ALLOWED_PAYLOAD_KEYS\s*=\s*\{(?P<body>.*?)\}\s*as\s+const\s+satisfies",
        analytics,
        re.S,
    )
    if not allowlist_match:
        errors.append("publicAnalytics.ts: analytics payload allowlist block is missing or unparsable")
    else:
        allowlist_body = allowlist_match.group("body")
        for key in ANALYTICS_SENSITIVE_KEYS:
            if re.search(rf'[\"\']{re.escape(key)}[\"\']', allowlist_body):
                errors.append(f"publicAnalytics.ts: sensitive analytics key is forbidden in allowlist: {key}")

    print("Three Crowns public-site truth guard")
    print(f"FACT: protected_files={len(PUBLIC_FILES)}")
    print(f"FACT: public_room_categories={category_count}")
    print(f"FACT: analytics_allowlist={'present' if allowlist_match else 'missing'}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("RESULT: PUBLIC TRUTH DRIFT")
        return 1

    print("PASS: public site matches the current canonical sales boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
