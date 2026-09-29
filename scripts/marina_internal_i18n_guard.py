#!/usr/bin/env python3
"""MARINA SMART internal locale quality guard."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADMIN = (ROOT / "apps/admin/components/AdminExperienceRuntime.tsx").read_text(encoding="utf-8")
STAFF = (ROOT / "apps/staff/components/StaffLocaleRuntime.tsx").read_text(encoding="utf-8")

errors = []

for snippet in [
    'type Locale = "ru" | "kg" | "kz" | "en"',
    '["ru", "kg", "kz", "en"]',
    'next === "kz" ? "kk"',
]:
    if snippet not in ADMIN:
        errors.append(f"admin missing locale contract: {snippet}")

for snippet in [
    'type Locale = "ru" | "kg" | "kz" | "en"',
    '"kz"',
    'locale === "kz"',
]:
    if snippet not in STAFF:
        errors.append(f"staff missing locale contract: {snippet}")

for bad in ["КОНok", "Конok", "КОНок СЕРВИСИ", "КОНok СЕРВИСИ"]:
    if bad in ADMIN or bad in STAFF:
        errors.append(f"mixed-script artifact remains: {bad}")

for bad in [
    'kg: "РЕСЕПШЕН"',
    'kz: "РЕСЕПШЕН"',
    'kg: "Ресепшен"',
    'kz: "Ресепшен"',
]:
    if bad in ADMIN or bad in STAFF:
        errors.append(f"unpolished reception term remains: {bad}")

for required in [
    'Кабыл алуу',
    'Қабылдау',
    'БӨЛМӨ КЫЗМАТКЕРИ',
    'БӨЛМЕ ҚЫЗМЕТКЕРІ',
    'MARINA SMART',
]:
    if required not in ADMIN + STAFF:
        errors.append(f"required terminology missing: {required}")

print("MARINA SMART internal i18n guard")
print("FACT: locales=ru,kg,kz,en")
print("FACT: surfaces=admin,staff,kitchen,waiter")
if errors:
    for error in errors:
        print("FAIL:", error)
    raise SystemExit(1)
print("PASS: internal locale contract and terminology are clean")
