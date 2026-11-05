#!/usr/bin/env python3
"""Fail closed if the MARINA SMART public RU/KG/KZ/EN contract regresses."""
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
    "rooms": ROOT / "apps/web/app/rooms/page.tsx",
    "room_detail": ROOT / "apps/web/app/rooms/[slug]/page.tsx",
    "rules": ROOT / "apps/web/app/rules/page.tsx",
    "privacy": ROOT / "apps/web/app/privacy/page.tsx",
    "marketing_consent": ROOT / "apps/web/app/marketing-consent/page.tsx",
    "service_point": ROOT / "apps/web/app/p/[token]/page.tsx",
    "guest": ROOT / "apps/web/components/GuestOsRuntime.tsx",
    "guest_requests": ROOT / "apps/web/components/GuestRequestsPanel.tsx",
    "guest_services": ROOT / "apps/web/components/GuestServicesRuntime.tsx",
    "site_media": ROOT / "apps/web/components/SiteMediaRuntime.tsx",
    "service_point_runtime": ROOT / "apps/web/components/ServicePointRuntime.tsx",
    "guest_locale": ROOT / "apps/web/lib/marinaGuestLocale.ts",
    "guest_facts": ROOT / "apps/web/lib/ownerApprovedGuestFacts.ts",
    "analytics": ROOT / "apps/web/lib/publicAnalytics.ts",
    "site_defaults": ROOT / "services/api/data/site_content_defaults.json",
}


def separated_guest_route_guard() -> int:
    """Check the intentional public-root /guest /g separation, not the
    superseded AK BERMET public sales website contract.
    """
    paths = {
        "public": ROOT / "apps/web/app/page.tsx",
        "guest": ROOT / "apps/web/app/guest/page.tsx",
        "landing": ROOT / "apps/web/components/GuestLanding.tsx",
        "route": ROOT / "apps/web/app/g/[token]/page.tsx",
        "runtime": ROOT / "apps/web/components/GuestConciergeRuntime.tsx",
        "locale": ROOT / "apps/web/lib/marinaGuestLocale.ts",
        "boundary": ROOT / "apps/web/components/PublicSiteRuntime.tsx",
    }
    texts = {key: path.read_text(encoding="utf-8") for key, path in paths.items()}
    requirements = {
        "public": ("Три Короны", "3korony.com"),
        "guest": ("GuestLanding", "AK BERMET", "MARINA SMART", "index: false"),
        "landing": ("AK BERMET", "MARINA SMART", 'type Locale = "ru" | "kg" | "kz" | "en"', "ru: {", "kg: {", "kz: {", "en: {"),
        "route": ("GuestConciergeRuntime",),
        "runtime": ("useMarinaGuestLocale", "MARINA_GUEST_LOCALES", "COPY", "ru: {", "kg: {", "kz: {", "en: {"),
        "locale": ("MARINA_GUEST_LOCALES", "marina-smart-guest-locale", "marina-smart-site-language", "window.localStorage.setItem(MARINA_GUEST_LOCALE_KEY, locale)"),
        "boundary": ('pathname === "/guest"', 'pathname.startsWith("/g/")', 'pathname.startsWith("/p/")'),
    }
    errors = [
        f"{name}: missing {needle!r}"
        for name, needles in requirements.items()
        for needle in needles if needle not in texts[name]
    ]
    for forbidden in ("Три Короны", "Three Crowns", "3korony.com"):
        if forbidden in texts["landing"] + texts["guest"]:
            errors.append(f"MARINA guest landing contains public-site brand: {forbidden}")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("RESULT: SEPARATED MARINA GUEST ROUTE DRIFT")
        return 1
    print("PASS: public root is isolated from four-language MARINA guest and QR routes")
    return 0


def main() -> int:
    # The shared platform serves the approved Three Crowns public pages at /,
    # while MARINA guest/QR pages have distinct route ownership and languages.
    home = (ROOT / "apps/web/app/page.tsx").read_text(encoding="utf-8")
    if "Три Короны" in home and "3korony.com" in home:
        return separated_guest_route_guard()

    errors: list[str] = []
    texts: dict[str, str] = {}
    for key, path in FILES.items():
        if not path.exists():
            errors.append(f"missing i18n contract file: {path.relative_to(ROOT)}")
            texts[key] = ""
        else:
            texts[key] = path.read_text(encoding="utf-8")

    legacy_tokens = ("Three Crowns", "Три Короны", "Үч Таажы", "Үш Тәж", "three-crowns", "3koronykg@mail.ru")
    for key, value in texts.items():
        for token in legacy_tokens:
            if token in value:
                errors.append(f"{key}: legacy public token remains: {token}")

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
        for locale in ("ru", "kg", "kz", "en"):
            count = len(re.findall(rf'^    {locale}: \{{ name:', body, re.M))
            if count != 12:
                errors.append(f"publicLocale.ts: expected 12 {locale} room translations, found {count}")

    required_locale = [
        'export type PublicLocale = "ru" | "kg" | "kz" | "en"',
        "resolveClientLocale",
        "withPublicLocale",
        "localizeRoomTypeName",
        "Бир кишилик номер, цоколь",
        "Single Room, Basement Level",
        "Ашканасы бар апартаменттер",
        "Асүйі бар апартаменттер",
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
        "kz: {",
        "en: {",
        "resolveClientLocale",
        "localizeRoomTypeName",
        "/core/api/v1/booking/check-availability",
        "/core/api/v1/booking/requests",
        "Заявка ещё не является подтверждённой бронью.",
        "Өтүнмө азырынча ырасталган бронь эмес.",
        "Өтінім әлі расталған бронь болып саналмайды.",
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
    for snippet in ["preserveInternalLanguage", "dispatchReady", "marina-smart:content-ready"]:
        if snippet not in site_runtime:
            errors.append(f"SiteContentRuntime.tsx: missing resilient locale behavior {snippet!r}")

    header = texts["header"]
    for snippet in ['type Locale = "ru" | "kg" | "kz" | "en"', '>RU</button>', '>KG</button>', '>KZ</button>', '>EN</button>', "switchLanguage"]:
        if snippet not in header:
            errors.append(f"SiteHeader.tsx: missing language-switch contract {snippet!r}")

    site_content = texts["site_content"]
    for snippet in ["fallbackSiteContent", "kg: {", "kz: {", "en: {", "AK BERMET", "MARINA SMART"]:
        if snippet not in site_content:
            errors.append(f"siteContent.ts: missing CMS fallback locale {snippet!r}")

    if "<PublicUiI18nRuntime />" not in texts["layout"]:
        errors.append("layout.tsx: PublicUiI18nRuntime is not mounted")

    print("MARINA SMART public i18n guard")
    print(f"FACT: localized_room_categories={room_count}")
    print("FACT: locales=ru,kg,kz,en")
    print("FACT: surfaces=home,booking,rooms-index,room-detail,header,cms-fallback")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("RESULT: PUBLIC I18N DRIFT")
        return 1

    print("PASS: MARINA SMART public RU/KG/KZ/EN contract is structurally complete and legacy-free")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
