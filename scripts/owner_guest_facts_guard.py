#!/usr/bin/env python3
"""Fail closed when owner-approved guest-service facts drift.

This guard is intentionally deterministic. It does not validate provider availability
or calculate reservation prices; it protects only the public facts explicitly
approved by the Three Crowns owner on 2026-08-28.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "apps/web/lib/ownerApprovedGuestFacts.ts"
RUNTIME = ROOT / "apps/web/components/GuestServicesRuntime.tsx"
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
    "30–50 автомобилей",
    "5 000 сом за 1 час",
    "4–5 человек",
    "500 сом за 1 час",
    "Настольный теннис",
    "Для проживающих — бесплатно",
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

    if "GuestServicesRuntime" not in layout:
        errors.append("GuestServicesRuntime is not mounted in public layout")
    if "ownerApprovedGuestFacts" not in runtime:
        errors.append("GuestServicesRuntime is not wired to owner-approved fact source")
    if "window.location.pathname !== \"/\"" not in runtime:
        errors.append("GuestServicesRuntime must remain scoped to the home page")

    print("Three Crowns owner guest-facts guard")
    print(f"FACT: required_guest_fact_snippets={len(REQUIRED_FACT_SNIPPETS)}")
    print(f"FACT: forbidden_stale_amenities={len(FORBIDDEN_STALE_AMENITIES)}")
    print(f"FACT: required_rule_snippets={len(REQUIRED_RULE_SNIPPETS)}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("RESULT: OWNER GUEST FACT DRIFT")
        return 1

    print("PASS: owner-approved guest-service facts and hotel rules are protected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
