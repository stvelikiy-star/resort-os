#!/usr/bin/env python3
"""Fail closed if MARINA SMART Guest Web RU/KG/KZ/EN support regresses."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "landing": ROOT / "apps/web/app/page.tsx",
    "concierge": ROOT / "apps/web/components/GuestConciergeRuntime.tsx",
    "housekeeping": ROOT / "apps/web/components/GuestHousekeepingPolicy.tsx",
    "marketplace": ROOT / "apps/web/components/GuestMarketplace.tsx",
    "ai": ROOT / "services/api/app/public_ai_admin.py",
    "cms": ROOT / "services/api/app/site_content.py",
    "cms_defaults": ROOT / "services/api/data/site_content_defaults.json",
    "cms_admin": ROOT / "apps/admin/components/SiteContentBoard.tsx",
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

    require(texts["landing"], ["AK BERMET", "MARINA SMART", "RU · KG · KZ · EN"], "landing", errors)
    require(texts["concierge"], [
        'type Locale = "ru" | "kg" | "kz" | "en"',
        'product: "MARINA SMART · қонақ кабинеті"',
        '(["ru", "kg", "kz", "en"] as Locale[])',
        'next === "kz" ? "kk"',
    ], "GuestConciergeRuntime", errors)
    require(texts["housekeeping"], ['type Locale = "ru" | "kg" | "kz" | "en"', 'eyebrow: "Бөлмені тазалау"'], "GuestHousekeepingPolicy", errors)
    require(texts["marketplace"], ['type Locale = "ru" | "kg" | "kz" | "en"', 'eyebrow: "Сіздің демалысыңыз үшін"', 'locale === "kz"'], "GuestMarketplace", errors)
    require(texts["ai"], ['Literal["ru", "kg", "kz", "en"]', '"kz": "Kazakh"'], "public_ai_admin", errors)
    require(texts["cms"], ['SUPPORTED_LOCALES = ("ru", "kg", "kz", "en")'], "site_content", errors)
    require(texts["cms_defaults"], ['"kz": {', '"Үш Тәж · Resort & SPA · Шолпан-Ата"'], "site_content_defaults", errors)
    require(texts["cms_admin"], ['type Locale = "ru" | "kg" | "kz" | "en"', '{ code: "kz", label: "Қазақша" }'], "SiteContentBoard", errors)

    print("MARINA SMART Guest Web i18n guard")
    print("FACT: locales=ru,kg,kz,en")
    print("FACT: guest_surfaces=landing,/g/[token],concierge,housekeeping,marketplace,ai; cms=separate")
    if errors:
        for error in errors:
            print("FAIL:", error)
        print("RESULT: MARINA GUEST I18N DRIFT")
        return 1
    print("PASS: MARINA SMART Guest Web RU/KG/KZ/EN contract is structurally complete")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
