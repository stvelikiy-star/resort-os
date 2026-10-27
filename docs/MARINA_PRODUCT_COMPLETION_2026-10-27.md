# MARINA SMART: product completion before host deployment

Scope: existing `fix/marina-staging-preflight-20261020` branch and PR #244.
Baseline: `e1248484001ad6580183ff8c4c5b85844adcb6c9`.
No Ubuntu, DNS, live hotel database or provider account was modified.

## Corrections in this change

- Admin and Staff assistant histories now start empty. Previously the first
  question included an empty assistant message and failed FastAPI validation
  with HTTP 422 before reaching the model. Greetings remain display-only.
- Assistant navigation includes WhatsApp and sales channels and uses effective
  server-side section grants, including owner-configured grants for reception.
- The embedded manual describes the actual WhatsApp and external-channel
  limitations instead of implying active provider connectivity.
- Owner-only GreenAPI state/QR endpoints and a connection panel are implemented.
  The backend accepts only explicitly hotel-bound, isolated-runtime settings;
  credentials stay server-side. QR responses are private/non-cacheable PNGs,
  expire in the UI after 20 seconds and are removed when leaving the panel.
  Provider credentials are redacted from HTTP transport logs. Redirects are
  not followed. Account authorization does not claim message delivery or AI.
- Existing full-stack CI now tests login/allowed and denied APIs for all six
  owner-assignable staff roles and password/session revocation. It also tests
  the first assistant question through both real frontends in four locales.

## GreenAPI connection configuration

These settings belong in the private environment of **one** hotel runtime:

- `ENABLE_GREEN_API_CONNECTION=true`
- `GREEN_API_PROPERTY_CODE` exactly equal to that runtime's `PROPERTY_CODE`
- `GREEN_API_URL` copied from the provider account (`api.green-api.com` or
  `api.greenapi.com`, optionally with the provider's host prefix)
- `GREEN_API_ID_INSTANCE`, `GREEN_API_TOKEN_INSTANCE`

Default is disabled. Shared tenant-context runtimes are rejected. This change
does not create instances, log out an existing phone, enable a message worker,
send messages or enable AI auto-replies. No browser credential entry or storage
is introduced. The existing n8n workflow folder contains reference templates;
mounting it is not evidence that a workflow is imported or active.

Provider contracts checked against official documentation on 2026-10-27:

- https://green-api.com/en/docs/api/account/GetStateInstance/
- https://green-api.com/en/docs/api/account/QR/
- https://green-api.com/en/docs/request-format/

## Remaining acceptance gates, in order

1. Current-commit CI, including the expanded staff-role and assistant browser
   tests, must pass. Prior green runs do not validate this change.
2. Verify actual model answers and role-scoped navigation using a configured
   model in an isolated test hotel. Test doubles and a provider-free 503 are
   explicitly not live AI acceptance.
3. Verify a real GreenAPI instance: QR scan and account state, inbound storage,
   outbound delivery evidence, reconnect, deduplication and human handoff.
   QR authorization alone does not close this gate.
4. Complete the WhatsApp sales orchestration against canonical hotel facts,
   date-specific pricing and availability, unified inbox and request linking.
   Confirmed reservations remain subject to the PMS workflow.
5. Implement and accept authenticated provider adapters for Booking.com,
   Airbnb and Ostrovok and establish the actual supported Tripadvisor partner
   booking interface. Current implementations are manual/CSV plus mappings,
   not OTA connectivity. Verify new/change/cancel, retries, reconciliation,
   external identity and outbound availability on each approved connection.
6. Complete combined Docker acceptance, persisted restart, disposable database
   backup/restore and application rollback rehearsal for the final version.
7. Only then prepare the Ubuntu placement step. Target-host acceptance remains
   separate and is not authorized by a green repository test.
