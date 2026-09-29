#!/usr/bin/env python3
"""Fail closed if MARINA SMART Guest Web RU/KG/KZ/EN support regresses."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "locale": ROOT / "apps/web/lib/marinaGuestLocale.ts",
    "landing": ROOT / "apps/web/app/page.tsx",
    "concierge": ROOT / "apps/web/components/GuestConciergeRuntime.tsx",
    "housekeeping": ROOT / "apps/web/components/GuestHousekeepingPolicy.tsx",
    "marketplace": ROOT / "apps/web/components/GuestMarketplace.tsx",
    "ai": ROOT / "services/api/app/public_ai_admin.py",
    "cms": ROOT / "services/api/app/site_content.py",
    "cms_defaults": ROOT / "services/api/data/site_content_defaults.json",
    "cms_admin": ROOT / "apps/admin/components/SiteContentBoard.tsx",
    "offers_api": ROOT / "services/api/app/guest_offers.py",
    "offers_admin": ROOT / "apps/admin/components/GuestOffersBoard.tsx",
    "menu_api": ROOT / "services/api/app/kitchen_menu_management.py",
    "market_api": ROOT / "services/api/app/guest_marketplace.py",
    "dynamic_kz_migration": ROOT / "packages/database/prisma/migrations/zz105_guest_dynamic_kz_20260929/migration.sql",
}

def require(text: str, snippets: list[str], surface: str, errors: list[str]) -> None:
    for snippet in snippets:
        if snippet not in text:
            errors.append(f"{surface}: missing {snippet!r}")

def main() -> int:
    errors: list[str] = []
    texts: dict[str, str] = {}
    for name, path in FILES.items():
        if not path.exists():
            errors.append(f"missing {path.relative_to(ROOT)}")
            texts[name] = ""
        else:
            texts[name] = path.read_text(encoding="utf-8")

    require(texts["locale"], [
        'export type MarinaGuestLocale = "ru" | "kg" | "kz" | "en"',
        'MARINA_GUEST_LOCALE_EVENT = "marina-smart:guest-locale"',
        'MARINA_GUEST_LOCALE_KEY = "marina-smart-guest-locale"',
        'next === "kz" ? "kk"',
        'useMarinaGuestLocale',
    ], "marinaGuestLocale", errors)
    require(texts["landing"], ["AK BERMET", "MARINA SMART", "RU · KG · KZ · EN"], "landing", errors)
    require(texts["concierge"], [
        'type Locale = MarinaGuestLocale',
        'product: "MARINA SMART · қонақ кабинеті"',
        'useMarinaGuestLocale()',
        'MARINA_GUEST_LOCALES.map',
        'Қабылдау бөліміне хабарласыңыз',
    ], "GuestConciergeRuntime", errors)
    require(texts["housekeeping"], ['type Locale = MarinaGuestLocale', 'useMarinaGuestLocale()', 'eyebrow: "Бөлмені тазалау"', 'system: "Тазалау · MARINA SMART"'], "GuestHousekeepingPolicy", errors)
    require(texts["marketplace"], ['type Locale = MarinaGuestLocale', 'useMarinaGuestLocale()', 'eyebrow: "Сіздің демалысыңыз үшін"', 'name_kz?: string', 'title_kz?: string', 'kitchenSystem: "Асүй · MARINA SMART"', 'aiSystem: "AI · тексерілген деректер"'], "GuestMarketplace", errors)
    require(texts["ai"], ['Literal["ru", "kg", "kz", "en"]', '"kz": "Kazakh"'], "public_ai_admin", errors)
    require(texts["cms"], ['SUPPORTED_LOCALES = ("ru", "kg", "kz", "en")'], "site_content", errors)
    require(texts["cms_defaults"], ['"kz": {', '"Үш Тәж · Resort & SPA · Шолпан-Ата"'], "site_content_defaults", errors)
    require(texts["cms_admin"], ['type Locale = "ru" | "kg" | "kz" | "en"', '{ code: "kz", label: "Қазақша" }'], "SiteContentBoard", errors)
    require(texts["offers_api"], ["title_kz: str", "hook_kz: str", "cta_kz: str", '"title_kz": row["titleKz"]', '"hook_kz": row["hookKz"]', '"cta_kz": row["ctaKz"]'], "guest_offers", errors)
    require(texts["offers_admin"], ["title_kz: string", "hook_kz: string", "cta_kz: string", "<legend>Қазақша</legend>", "RU/KG/KZ/EN"], "GuestOffersBoard", errors)
    require(texts["menu_api"], ["name_kz: str", '"name_kz": row["nameKz"]', '"nameKz"'], "kitchen_menu_management", errors)
    require(texts["market_api"], ['m."nameKz"', '"name_kz": row["nameKz"]'], "guest_marketplace", errors)
    require(texts["dynamic_kz_migration"], ['ADD COLUMN IF NOT EXISTS "nameKz"', 'ADD COLUMN IF NOT EXISTS "titleKz"', 'ADD COLUMN IF NOT EXISTS "hookKz"', 'ADD COLUMN IF NOT EXISTS "ctaKz"'], "zz105_guest_dynamic_kz", errors)

    print("MARINA SMART Guest Web i18n guard")
    print("FACT: locales=ru,kg,kz,en")
    print("FACT: guest_surfaces=landing,/g/[token],concierge,housekeeping,marketplace,ai,dynamic-menu,dynamic-offers; cms=separate")
    if errors:
        for error in errors:
            print("FAIL:", error)
        print("RESULT: MARINA GUEST I18N DRIFT")
        return 1
    print("PASS: MARINA SMART Guest Web RU/KG/KZ/EN contract is structurally complete")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
