#!/usr/bin/env python3
"""Fail closed if the mounted MARINA SMART Guest Web locale contract regresses."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "landing": ROOT / "apps/web/app/page.tsx",
    "guest_page": ROOT / "apps/web/app/g/[token]/page.tsx",
    "locale": ROOT / "apps/web/lib/marinaGuestLocale.ts",
    "concierge": ROOT / "apps/web/components/GuestConciergeRuntime.tsx",
    "housekeeping": ROOT / "apps/web/components/GuestHousekeepingPolicy.tsx",
    "marketplace": ROOT / "apps/web/components/GuestMarketplace.tsx",
    "ai": ROOT / "services/api/app/public_ai_admin.py",
}

def require(text, snippets, surface, errors):
    for snippet in snippets:
        if snippet not in text:
            errors.append(f"{surface}: missing {snippet!r}")

def main():
    errors = []
    texts = {}
    for name, path in FILES.items():
        if not path.exists():
            errors.append(f"missing {path.relative_to(ROOT)}")
            texts[name] = ""
        else:
            texts[name] = path.read_text(encoding="utf-8")

    require(texts["landing"], ["AK BERMET", "MARINA SMART", "RU · KG · KZ · EN"], "landing", errors)
    require(texts["guest_page"], ["GuestConciergeRuntime", "GuestHousekeepingPolicy", "GuestMarketplace"], "guest page", errors)
    require(texts["locale"], [
        'export type MarinaGuestLocale = "ru" | "kg" | "kz" | "en"',
        "MARINA_GUEST_LOCALES",
        'if (locale === "kz") return "kk"',
        "MARINA_GUEST_LOCALE_EVENT",
        "applyMarinaGuestLocale",
    ], "marinaGuestLocale", errors)
    require(texts["concierge"], [
        "useMarinaGuestLocale",
        'product: "MARINA SMART · қонақ кабинеті"',
        "Қабылдау бөліміне",
        "Кабыл алуу кызматына",
    ], "GuestConciergeRuntime", errors)
    require(texts["housekeeping"], [
        "useMarinaGuestLocale",
        'system: "Тазалоо · MARINA SMART"',
        'system: "Тазалау · MARINA SMART"',
    ], "GuestHousekeepingPolicy", errors)
    require(texts["marketplace"], [
        "useMarinaGuestLocale",
        'eyebrow: "Эс алууңуз үчүн"',
        'eyebrow: "Сіздің демалысыңыз үшін"',
        'locale === "kz"',
    ], "GuestMarketplace", errors)
    require(texts["ai"], ['Literal["ru", "kg", "kz", "en"]', '"kz": "Kazakh"'], "public AI", errors)

    forbidden = {
        "concierge": ["Resort OS"],
        "housekeeping": ["Resort OS"],
        "marketplace": [" заказ кыл", " заказ "],
    }
    for surface, values in forbidden.items():
        for value in values:
            if value in texts[surface]:
                errors.append(f"{surface}: forbidden legacy/mixed wording {value!r}")

    print("MARINA SMART Guest Web i18n guard")
    print("FACT: locales=ru,kg,kz,en")
    print("FACT: mounted_surfaces=concierge,housekeeping,marketplace,ai")
    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    print("PASS: mounted MARINA SMART Guest Web locale contract is complete")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
