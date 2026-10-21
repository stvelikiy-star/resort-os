# MARINA SMART — Direct WhatsApp pilot (Green-API)

Status: **SOURCE IMPLEMENTED, NOT ENABLED**, 2026-10-21.

## Architecture
- Each hotel has its own running isolated MARINA Core and PostgreSQL.
- One Green-API instance belongs to **one** hotel only. The adapter reads the
  instance from **private deployment environment**, never from guest messages.
- Green-API ReceiveNotification → validate instance id → normalize message →
  `POST /api/v1/automation/inbox/messages` (existing protected Core CRM contract)
  → Green-API DeleteNotification **only after successful Core acknowledgement**.
- Provider retries and duplicate notifications are reconciled by Core's
  per-property idempotency key and external message identifier.
- **No n8n, Nextbot, public webhook, browser-held Green token, AI auto-send,
  payment, HOLD or confirmed reservation in this stage.**
- Group/newsletter/non-text messages are currently unsupported and acknowledged
  without CRM insertion. Do not launch on hotels needing media/group support
  before implementing their adapters and consent rules.
- The Core's service key is required. If not configured, the adapter fails
  closed; it never prints tokens or guest content.

## Config and boundaries
Required private environment variables in ONE hotel's runtime:
- `GREEN_API_URL`: *trusted* HTTPS Green-API endpoint from your own account
- `GREEN_API_ID_INSTANCE`: numeric WhatsApp instance identifier
- `GREEN_API_TOKEN_INSTANCE`: provider token (do not commit or post)
- `AUTOMATION_SERVICE_KEY`: **same** high-entropy secret in Core and adapter
- `PROPERTY_CODE`: bound hotel, e.g. `MARINA_HOTEL01`
Optional: `RESORT_CORE_URL`, defaults to `http://127.0.0.1:8000` for
in-container operation. Do not put Core behind a public internet-facing
service-key endpoint.

These variables **are not configured** in the current `compose.marina-fleet.yaml`.
Provision through a per-hotel secret store and a dedicated worker configuration
only after approved credentials and isolated network/credentials testing.
Do not put the secrets in shared `.marina-fleet/*.env` printed to support chats.

## Safe initial test
`python3 scripts/marina_green_poll_test.py -v` — synthetic offline tests.

After a real instance is safely configured and message-retention risks are
understood, execute `python scripts/marina_green_poll.py --once` inside the
isolated hotel network with its private environment. This processes **at most
one** notification and exits. Never enable an indefinite worker without
monitoring, concurrency control, failure alerts, deduplication tests, backups
and a verified number/property binding.

## Existing MARINA assets reused
- `services/api/app/communication_ingest.py`: canonical conversations/messages
- `services/api/app/inbox.py`: owner and manager inbox
- `services/api/app/automation.py`: separate request-linking service
- `apps/admin/components/InboxBoard.tsx`: UI shell

## Remaining work before real production
1. Owner-only QR provisioning flow and per-hotel secret vault.
2. Server-side outbound adapter with message-status reconciliation.
3. MARINA AI hotel-specific verified facts, opt-in automation, handoff to staff.
4. Read-only first, then safe lead-to-ReservationRequest workflow.
5. Media handling, device reconnection, opt-out, privacy and retention.
6. Two-hotel isolated end-to-end tests, queue outage/retry and resource load.
7. Official Meta API alternative for hotels that cannot accept QR-provider risk.

Green-API polling queue expiry is **24 hours** per provider documentation; this
is not a replacement for 24/7 supervision and alerts.
