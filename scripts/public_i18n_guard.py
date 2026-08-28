#!/usr/bin/env python3
"""Fail closed if the Three Crowns public RU/KG/EN contract regresses."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "locale": ROOT / "apps/web/lib/publicLocale.ts",
    "booking": ROOT / "apps/web/components/BookingWidget.tsx",
    "runtime": ROOT / "apps/web/components/PublicUiI18nRuntime.tsx",
    "site_runtime": ROOT / "apps/web/components/SiteContentRuntime.tsx",
    "header": ROOT / "apps/web/components/SiteHeader.tsx",
    "site_content": ROOT / "apps/web/lib/siteContent.ts",
    "layout": ROOT / "apps/web/app/layout.tsx",
}


def main() -> int:
    errors: list[str] = []
    texts: dict[str, str] = {}
    for key, path in FILES.items():
        if not path.exists():
            errors.append(f"missing i18n contract file: {path.relative_to(ROOT)}")
            texts[key] = ""
        else:
            texts[key] = path.read_text(encoding="utf-8")

    locale_text = texts["locale"]
    match = re.search(r"export const roomLocaleBySlug.*?=\s*\{(?P<body>.*?)\n\};\n\nconst roomSlugByRussianName", locale_text, re.S)
    if not match:
        errors.append("publicLocale.ts: roomLocaleBySlug block is missing or unparsable")
        room_count = 0
    else:
        body = match.group("body")
        room_count = len(re.findall(r'^  (?:(?:"[^"\n]+")|apartments): \{$', body, re.M))
        if room_count != 12:
            errors.append(f"publicLocale.ts: expected 12 localized room categories, found {room_count}")
        for locale in ("ru", "kg", "en"):
            count = len(re.findall(rf'^    {locale}: \{{ name:', body, re.M))
            if count != 12:
                errors.append(f"publicLocale.ts: expected 12 {locale} room translations, found {count}")

    required_locale = [
        'export type PublicLocale = "ru" | "kg" | "en"',
        "resolveClientLocale",
        "withPublicLocale",
        "localizeRoomTypeName",
        "Бир кишилик номер, цоколь",
        "Single Room, Basement Level",
        "Ашканасы бар апартаменттер",
        "Apartments with Kitchen",
    ]
    for snippet in required_locale:
        if snippet not in locale_text:
            errors.append(f"publicLocale.ts: missing {snippet!r}")

    booking = texts["booking"]
    for snippet in [
        "const COPY = {",
        "ru: {",
        "kg: {",
        "en: {",
        "resolveClientLocale",
        "localizeRoomTypeName",
        "/core/api/v1/booking/check-availability",
        "/core/api/v1/booking/requests",
        "Заявка ещё не является подтверждённой бронью.",
        "Өтүнмө азырынча ырасталган бронь эмес.",
        "The request is not yet a confirmed reservation.",
    ]:
        if snippet not in booking:
            errors.append(f"BookingWidget.tsx: missing multilingual booking contract {snippet!r}")

    runtime = texts["runtime"]
    for snippet in [
        "const HOME = {",
        "const ROOMS_PAGE = {",
        "const ROOM_DETAIL = {",
        '".v3-advantage-card"',
        '".v3-territory-route article"',
        '".v3-amenity-grid article"',
        '".v3-review-grid article"',
        '".room-catalog-card"',
        "localizeRoomDetail",
        "resolveClientLocale",
    ]:
        if snippet not in runtime:
            errors.append(f"PublicUiI18nRuntime.tsx: missing deep i18n coverage {snippet!r}")

    site_runtime = texts["site_runtime"]
    for snippet in ["preserveInternalLanguage", "dispatchReady", "three-crowns:content-ready"]:
        if snippet not in site_runtime:
            errors.append(f"SiteContentRuntime.tsx: missing resilient locale behavior {snippet!r}")

    header = texts["header"]
    for snippet in ['type Locale = "ru" | "kg" | "en"', '>RU</button>', '>KG</button>', '>EN</button>', "switchLanguage"]:
        if snippet not in header:
            errors.append(f"SiteHeader.tsx: missing language-switch contract {snippet!r}")

    site_content = texts["site_content"]
    for snippet in ["fallbackSiteContent", "kg: {", "en: {", "Үч Таажы", "Three Crowns"]:
        if snippet not in site_content:
            errors.append(f"siteContent.ts: missing CMS fallback locale {snippet!r}")

    if "<PublicUiI18nRuntime />" not in texts["layout"]:
        errors.append("layout.tsx: PublicUiI18nRuntime is not mounted")

    print("Three Crowns public i18n guard")
    print(f"FACT: localized_room_categories={room_count}")
    print("FACT: locales=ru,kg,en")
    print("FACT: surfaces=home,booking,rooms-index,room-detail,header,cms-fallback")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("RESULT: PUBLIC I18N DRIFT")
        return 1

    print("PASS: public RU/KG/EN contract is structurally complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
