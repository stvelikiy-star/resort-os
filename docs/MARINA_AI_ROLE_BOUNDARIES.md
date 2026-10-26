# MARINA AI access boundaries

The staff assistant is available only to OWNER, MANAGER and RECEPTION. Other
staff roles receive HTTP 403 from both capabilities and chat before any live
context or provider access. Both widgets hide themselves for unsupported roles.
The guest assistant has a separate endpoint and no staff-session access path.

Staff context uses effective server-side module permissions. Custom empty
permissions grant no operational data. SQL is guarded before execution; omitted
sections are removed from the model context. OWNER retains the same full access
as the existing section policy. Navigation uses the same effective modules.

| Module | Live data |
| --- | --- |
| PMS | Inventory, occupancy, holds, current reservations |
| RESERVATIONS | Arrivals/departures and current reservations |
| OPS | Operational tasks and counts |
| REQUESTS | Reservation request counts for OWNER/MANAGER |
| FINANCE | Hotel-wide financial snapshot for OWNER/MANAGER |
| DINING | Dining snapshot for OWNER/MANAGER |

Reservation balances remain part of the existing PMS/reservation folio scope;
they do not grant the hotel-wide FINANCE snapshot. Hotel rules require
HOTEL_RULES, SETTINGS or RESERVATIONS. No assistant can mutate business data.

The guest chat requires the existing QR/PIN session and active stay. It also
matches the session to the resolved QR. Each request revalidates access; after
checkout, expiry, logout or QR invalidation the same checks fail closed. Context
contains only that stay's room/dates, that property's allowlisted guest-facing
rules and guest-created request statuses filtered by property and stay. Staff
manuals, guest identity/contact fields, secrets and hotel finance are excluded.

The guest UI is mounted only after guest authentication, supports RU/KG/KZ/EN,
and does not persist chat history to browser storage. An absent AI provider
returns 503; it is not replaced with invented facts. Live provider quality and
availability still require an independently configured environment.

Validation:

- `python scripts/test_marina_assistant_permissions.py` — real FastAPI routes,
  module query guards and guest denial paths; database/provider are test doubles.
- `python scripts/marina_ai_embedded_contract.py` — wiring contract.
- `python scripts/verify_marina_ai_role_runtime.py` — real synthetic database
  reception context and denied staff roles in the existing CI workflow.
- `python scripts/marina_guest_identity_e2e.py` — real synthetic QR/PIN lifecycle:
  unauthorized guest chat is denied, authorized chat reaches the expected 503
  with no provider key, and checkout revokes chat access.
- TypeScript checks for web/admin/staff; existing full stack and release gates.

No target Ubuntu deployment or live-provider test is implied by these checks.
