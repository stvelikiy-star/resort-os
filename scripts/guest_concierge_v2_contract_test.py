#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "apps/web/components/GuestConciergeRuntime.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "apps/web/app/g/[token]/page.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "apps/web/app/guest-concierge.css").read_text(encoding="utf-8")
REQUESTS = (ROOT / "services/api/app/guest_requests.py").read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


# Route ownership: one concierge runtime, no duplicate legacy request UI.
require("GuestConciergeRuntime" in PAGE, "room QR route must use GuestConciergeRuntime")
require("GuestOsRuntime" not in PAGE, "legacy GuestOsRuntime must not render beside concierge")
require("GuestRequestsPanel" not in PAGE, "legacy duplicate request panel must not render")
require("guest-concierge.css" in PAGE, "concierge stylesheet not wired")
require(".concierge-page ~ .ai-admin-root{display:none!important}" in PAGE, "RU-only public AI widget must not leak into localized concierge")

# Guest-visible localization must be explicit and compact.
for locale in ('ru:', 'kg:', 'en:'):
    require(locale in RUNTIME, f"locale dictionary missing: {locale}")
for phrase in (
    "Три Короны", "Цифровой консьерж", "Үч Таажы", "Санарип жардамчы",
    "Three Crowns", "Digital concierge", "Что нужно сейчас?", "Азыр эмне керек?",
    "What do you need now?",
):
    require(phrase in RUNTIME, f"localized guest phrase missing: {phrase}")
require("concierge-langs" in CSS, "compact locale selector styling missing")
require("border-radius:999px" in CSS, "language selector must remain compact/pill-shaped")

# Internal request codes may exist in code but every code must have display copy in all locales.
codes = (
    "HOUSEKEEPING", "TOWELS", "LINEN", "MAINTENANCE", "TRANSFER", "MEALS",
    "PARKING", "SAUNA", "BILLIARDS", "EXCURSIONS", "ADMIN",
)
for code in codes:
    require(RUNTIME.count(f"{code}:") >= 3, f"{code} missing one or more RU/KG/EN display mappings")

# Reuse the hardened existing Guest OS request boundary; no parallel commerce backend.
for endpoint_part in (
    "/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}",
    "/requests",
    "/verify",
    "/cancel",
):
    require(endpoint_part in RUNTIME, f"existing Guest OS route not reused: {endpoint_part}")
for forbidden in ("/payments", "/reservation-payments", "/beach/charge", "/nfc"):
    require(forbidden not in RUNTIME, f"concierge must not mutate commercial/deferred scope: {forbidden}")

# Meal estimate must use the owner-approved 2026 per-meal values and must not promise inclusion.
for value in ("500", "750", "650", "400", "550", "450"):
    require(value in RUNTIME, f"approved meal value missing: {value}")
require("Включённое в проживание питание определяется вашей бронью" in RUNTIME, "RU meal-inclusion safety copy missing")
require("Meal inclusion depends on your reservation" in RUNTIME, "EN meal-inclusion safety copy missing")
require("Жашоого кирген тамактануу сиздин бронуңуз боюнча аныкталат" in RUNTIME, "KG meal-inclusion safety copy missing")

# Transfer must remain a request requiring staff confirmation, not an automatic booking promise.
for key in ("manas", "tamchy", "bishkek", "sedan", "minivan"):
    require(f"{key}:" in RUNTIME, f"structured transfer field missing: {key}")
require("сотрудник подтвердит доступность" in RUNTIME, "transfer manager-confirmation boundary missing")
require("staff will confirm availability" in RUNTIME, "EN transfer confirmation boundary missing")

# Existing Core model remains authoritative and supported codes stay aligned.
for code in codes:
    require(code in REQUESTS, f"frontend request code not supported by Core: {code}")

# Mobile-first acceptance.
require("@media(max-width:800px)" in CSS, "tablet/mobile breakpoint missing")
require("@media(max-width:420px)" in CSS, "phone breakpoint missing")
require("grid-template-columns:repeat(2" in CSS, "mobile quick actions must collapse to two columns")

print("PASS: Guest Concierge V2 localization, request reuse, meal/transfer safety and mobile contracts")
