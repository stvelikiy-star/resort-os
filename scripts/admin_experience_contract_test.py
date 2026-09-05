#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (ROOT / "apps/admin/components/AdminExperienceRuntime.tsx").read_text(encoding="utf-8")
SANITIZER = (ROOT / "apps/admin/components/AdminLocaleSanitizer.tsx").read_text(encoding="utf-8")
STYLE = (ROOT / "apps/admin/app/admin-experience.css").read_text(encoding="utf-8")
LAYOUT = (ROOT / "apps/admin/app/layout.tsx").read_text(encoding="utf-8")
PIN_API = (ROOT / "services/api/app/guest_pin_admin.py").read_text(encoding="utf-8")
ENTRY = (ROOT / "services/api/app/app_entry.py").read_text(encoding="utf-8")
STAYS = (ROOT / "services/api/app/stays.py").read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


# The check-in response must be observed from a clone so ReceptionBoard still
# receives the original body/response unchanged.
require("response.clone().json()" in RUNTIME, "PIN runtime must inspect a cloned response")
require("check-in" in RUNTIME, "check-in response interception missing")
require("guest_access_pin" in RUNTIME, "one-time PIN field not rendered")
require("guest_access_pin_display_once" in STAYS, "Core check-in one-time PIN contract missing")

# Reissue is fail-closed and restricted to active checked-in stays.
for role in ('"OWNER"', '"MANAGER"', '"RECEPTION"'):
    require(role in PIN_API, f"required role missing from PIN endpoint: {role}")
require("reservation[\"status\"] != \"CHECKED_IN\"" in PIN_API, "PIN reissue must require CHECKED_IN")
require("stay[\"status\"] != \"ACTIVE\"" in PIN_API, "PIN reissue must require ACTIVE stay")
require("issue_guest_pin()" in PIN_API, "PIN reissue must use hardened PIN generator")
require('"guestAccessPinHash"=$1' in PIN_API, "PIN hash persistence missing")
require("guest_pin_hash" in PIN_API, "hashed PIN value missing")
require("guest_pin," not in PIN_API.split("UPDATE stays", 1)[1].split("audit_logs", 1)[0], "plaintext PIN must not be persisted")
require("interval '24 hours'" in PIN_API, "PIN validity must stay 24 hours")
require("GUEST_PIN_REISSUE" in PIN_API, "PIN reissue must be audited")
require("guest_pin_admin_router" in ENTRY and "include_router(guest_pin_admin_router)" in ENTRY, "PIN router not composed")

# Locale selector must be global and persistent for all admin modules.
for locale in ('"ru"', '"kg"', '"en"'):
    require(locale in RUNTIME, f"locale missing: {locale}")
require("localStorage" in RUNTIME and "three-crowns-admin-locale" in RUNTIME, "locale persistence missing")
require("MutationObserver" in RUNTIME, "dynamic React content must be translated")
require("placeholder" in RUNTIME and "aria-label" in RUNTIME, "form/accessibility text localization missing")
require("AdminExperienceRuntime" in LAYOUT, "global admin runtime not mounted")
require("AdminLocaleSanitizer" in LAYOUT, "locale sanitizer not mounted")
require('import "./admin-experience.css"' in LAYOUT, "final contrast layer not imported")

# Raw machine labels seen during manual acceptance must have locale-aware display mappings.
for raw in (
    "PMS_SCHEDULE_MUTATION",
    "MANAGER_CREATE_RESERVATION_FROM_GRID",
    "CHECK_IN",
    "CHECK_OUT",
    "HOUSEKEEPING",
    "MAINTENANCE",
    "DONE",
    "IN_PROGRESS",
    "IN_INSPECTION",
    "NOT_CONFIGURED",
    "OWNER OPERATIONS",
    "GUEST SERVICES",
):
    require(raw in RUNTIME, f"missing translation mapping for {raw}")

# Dashboard contrast requirement from manual screenshot: blue surfaces, white primary text.
require("--tc-admin-blue:#123d73" in STYLE, "approved admin blue token missing")
require("--tc-admin-white:#fff" in STYLE, "white text token missing")
require(".dashboard-shell" in STYLE, "dashboard contrast override missing")
require("color:var(--tc-admin-white)!important" in STYLE, "dashboard white text enforcement missing")

# Mixed-script artifacts are actively removed from dynamic locale content.
require("КОНok" in SANITIZER and "КОНОК" in SANITIZER, "mixed-script Kyrgyz sanitizer missing")
require("MutationObserver" in SANITIZER, "mixed-script sanitizer must cover dynamic content")

print("PASS: admin Guest OS PIN, locale runtime, and contrast contracts")
