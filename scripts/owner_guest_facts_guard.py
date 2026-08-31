#!/usr/bin/env python3
"""Fail closed when owner-approved guest-service facts drift.

This guard is intentionally deterministic. It does not validate provider availability
or calculate reservation prices; it protects only the public facts explicitly
approved by the Three Crowns owner and their authoritative public rendering path.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "apps/web/lib/ownerApprovedGuestFacts.ts"
RUNTIME = ROOT / "apps/web/components/GuestServicesRuntime.tsx"
PUBLIC_I18N = ROOT / "apps/web/components/PublicUiI18nRuntime.tsx"
HOME = ROOT / "apps/web/app/page.tsx"
RULES = ROOT / "apps/web/app/rules/page.tsx"
LAYOUT = ROOT / "apps/web/app/layout.tsx"

REQUIRED_FACT_SNIPPETS = [
    "70000001027860639/tab/reviews",
    "Манас: седан 6 500 / минивен 7 500 сом",
    "Аэропорт Тамчы: седан 2 500 / минивен 3 500 сом",
    "Бишкек: седан 5 500 / минивен 6 500 сом",
    "Взрослый — 1 900 сом в день, ребёнок — 1 400 сом",
    "завтрак 500, обед 750, ужин 650 сом",
    "400 / 550 / 450 сом",
    "20–30 автомобилей",
    "5 000 сом за 1 час",
    "4–5 человек",
    "500 сом за 1 час",
    "Настольный теннис",
    "Для проживающих — бесплатно",
    "MIX TOUR.KG",
    "Семёновское ущелье + горячий источник — 2 000 сом/чел.",
    "Джети-Огуз + горячий источник — 3 500",
    "Мёртвое озеро + горячий источник — 3 000",
    "Барскоонский водопад + ущелье Сказка",
    "4 500 сом/чел.",
    "с 20 июня по 25 августа 2026 года",
    "В цену входят трансфер и услуги гида",
    "входные билеты, горячие источники, питание и дополнительные расходы оплачиваются отдельно",
    "Термальные источники находятся в шаговой доступности",
    "независимых пляжных операторов",
    "Это не услуги отеля",
]

FORBIDDEN_STALE_AMENITIES = [
    "спортивные площадки",
    "тренажёрный зал",
    "тренажерный зал",
    "gym",
    "sports field",
    "sports court",
]

REQUIRED_RULE_SNIPPETS = [
    "1 000 сом",
    "Животные",
    "22:00",
    "25%",
    "50%",
    "75%",
    "1 500 сом",
    "Утеря и порча имущества",
]


def read(path: Path, errors: list[str]) -> str:
    if not path.exists():
        errors.append(f"missing file: {path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


def main() -> int:
    errors: list[str] = []
    facts = read(FACTS, errors)
    runtime = read(RUNTIME, errors)
    public_i18n = read(PUBLIC_I18N, errors)
    home = read(HOME, errors)
    rules = read(RULES, errors)
    layout = read(LAYOUT, errors)

    for snippet in REQUIRED_FACT_SNIPPETS:
        if snippet not in facts:
            errors.append(f"owner guest facts missing required snippet: {snippet!r}")

    lowered = facts.lower()
    for stale in FORBIDDEN_STALE_AMENITIES:
        if stale.lower() in lowered:
            errors.append(f"owner guest facts contain owner-rejected amenity: {stale!r}")

    for snippet in REQUIRED_RULE_SNIPPETS:
        if snippet not in rules:
            errors.append(f"rules page missing owner-provided rule snippet: {snippet!r}")

    transfer_positions = []
    excursions_positions = []
    offset = 0
    while True:
        transfer = facts.find('code: "TRANSFER"', offset)
        excursions = facts.find('code: "EXCURSIONS"', offset)
        if transfer == -1 and excursions == -1:
            break
        if transfer == -1 or excursions == -1:
            errors.append("owner guest facts must contain TRANSFER and EXCURSIONS in every locale block")
            break
        transfer_positions.append(transfer)
        excursions_positions.append(excursions)
        offset = excursions + 1
    if len(transfer_positions) != 3 or len(excursions_positions) != 3:
        errors.append(f"expected TRANSFER/EXCURSIONS ordering in 3 locales, found {len(transfer_positions)}/{len(excursions_positions)}")
    elif any(transfer > excursions for transfer, excursions in zip(transfer_positions, excursions_positions)):
        errors.append("TRANSFER must render before EXCURSIONS in every public locale")

    if "GuestServicesRuntime" not in layout:
        errors.append("GuestServicesRuntime is not mounted in public layout")
    if "PublicUiI18nRuntime" not in layout:
        errors.append("PublicUiI18nRuntime is not mounted in public layout")
    public_i18n_mount = layout.find("<PublicUiI18nRuntime />")
    guest_facts_mount = layout.find("<GuestServicesRuntime />")
    if public_i18n_mount == -1 or guest_facts_mount == -1 or public_i18n_mount > guest_facts_mount:
        errors.append("GuestServicesRuntime must mount after PublicUiI18nRuntime so canonical facts win hydration")

    if "ownerApprovedGuestFacts" not in runtime:
        errors.append("GuestServicesRuntime is not wired to owner-approved fact source")
    if "window.location.pathname !== \"/\"" not in runtime:
        errors.append("GuestServicesRuntime must remain scoped to the home page")
    if "requestAnimationFrame" not in runtime:
        errors.append("GuestServicesRuntime must re-apply canonical facts after sibling hydration")

    if "ownerApprovedGuestFacts" not in home:
        errors.append("home page initial HTML is not wired to owner-approved guest facts")
    if "const ownerFacts = ownerApprovedGuestFacts.ru" not in home:
        errors.append("home page must render Russian SSR guest facts from the canonical source")
    if "const extraServices = ownerFacts.services.cards" not in home:
        errors.append("home page services are not sourced from owner-approved facts")
    if "const extraServices = [" in home:
        errors.append("home page contains a duplicated static guest-service catalog")
    if "ownerFacts.services.eyebrow" not in home or "data-service-code={service.code}" not in home:
        errors.append("home page does not server-render canonical service heading/cards")
    if "TWO_GIS_REVIEWS_URL" not in home or "ownerFacts.reviews.cards" not in home:
        errors.append("home page does not server-render canonical review source/cards")
    if "ownerFacts.included.title" not in home or "ownerFacts.included.text" not in home:
        errors.append("home page included-amenities card is not sourced from owner-approved facts")

    # General KG/EN copy may still be maintained by PublicUiI18nRuntime, but owner-approved
    # review/service sections must have a later authoritative renderer.
    if ".v3-extra-grid" not in public_i18n:
        errors.append("public locale runtime no longer exposes expected home service surface")

    print("Three Crowns owner guest-facts guard")
    print(f"FACT: required_guest_fact_snippets={len(REQUIRED_FACT_SNIPPETS)}")
    print(f"FACT: forbidden_stale_amenities={len(FORBIDDEN_STALE_AMENITIES)}")
    print(f"FACT: required_rule_snippets={len(REQUIRED_RULE_SNIPPETS)}")
    print(f"FACT: localized_transfer_before_tours={len(transfer_positions) == 3 and all(t < e for t, e in zip(transfer_positions, excursions_positions))}")
    print(f"FACT: ssr_guest_facts={'ownerApprovedGuestFacts' in home}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("RESULT: OWNER GUEST FACT DRIFT")
        return 1

    print("PASS: owner-approved guest-service facts, SSR rendering and hydration authority are protected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
