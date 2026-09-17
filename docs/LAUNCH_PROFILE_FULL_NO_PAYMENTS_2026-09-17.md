# Three Crowns — FULL_NO_PAYMENTS launch profile

Date: 2026-09-17

## Owner direction

Connect and operate the full Resort OS contour now, except for QR, cash-register/payment processing and related acquiring/provider execution. Those financial integrations remain intentionally disabled until a separate owner decision.

## Enabled operational contour

- Public site and booking-request intake
- Resort Core / PostgreSQL authority
- PMS chessboard and reservation operations
- Safe booking move / split-stay workflows
- Owner/manager/reception workflows
- Agent CRM, agent cards, interactions and reports
- Returning-guest lookup / 10% owner rule
- Extra-bed rules and repricing
- Dated maintenance blocks
- Manual owner/staff/guest/service room holds
- Housekeeping and inspection lifecycle
- Technician tasks / TECH_BLOCK lifecycle
- Guest OS and guest requests
- Guest services and transfer requests
- Kitchen / dining operational contour
- Staff Telegram WebApp / voice task intake
- CRM / inbox / communications
- n8n automation contour
- AI sales/administrator contour, subject to configured model/provider credentials
- Analytics, reports and owner dashboards
- Realtime PMS WebSocket

## Disabled financial/provider contour

The production environment must set:

```dotenv
LAUNCH_PROFILE=FULL_NO_PAYMENTS
ENABLE_PAYMENT_OPERATIONS=false
ENABLE_SERVICE_POINT_QR=false
ENABLE_MKASSA=false
```

Consequences:

- `reservation_payments` mutation router is not composed;
- Service Point payment public/integration/admin routers are not composed;
- MKassa bridge is not composed;
- NFC wallet/acquiring remains dormant as before;
- existing historical payment rows remain readable in folio/analytics;
- manual charges/folio debt may still be recorded because they are not proof of received money;
- no UI should offer a new-payment action when the runtime capability is disabled.

## Runtime proof

`GET /api/v1/runtime/capabilities` exposes the active launch profile and capability flags. This endpoint contains no secrets and is intended for UI gating and smoke checks.

Expected payload includes:

```json
{
  "profile": "FULL_NO_PAYMENTS",
  "capabilities": {
    "pms": true,
    "crm": true,
    "staff": true,
    "guest_os": true,
    "kitchen": true,
    "automation": true,
    "ai_sales": true,
    "payment_operations": false,
    "service_point_qr": false,
    "mkassa": false,
    "nfc_wallet": false
  },
  "financial_integrations_enabled": false
}
```

## Acceptance before host cutover

1. Apply the current Prisma migration chain to an isolated staging database.
2. Reconcile the canonical 84 rooms / 12 categories with zero unexpected diff.
3. Bring up `postgres`, `api`, `web`, `admin`, `staff`, `n8n`, `caddy` using `compose.production.yaml` and this profile.
4. Verify `/health/ready` and `/api/v1/runtime/capabilities`.
5. Run public booking-request smoke test; success must say that the request was sent, not that a reservation/payment was completed.
6. Run Admin/PMS scenarios: create reservation, move with explicit confirmation, split stay, extra bed recalculation, agent assignment/report, returning guest lookup, room period block, check-in/out, housekeeping, maintenance.
7. Run Guest OS, Staff, Kitchen and automation smoke tests.
8. Confirm payment mutation endpoints and Service Point QR/MKassa endpoints are absent (404) in this profile.
9. Verify HTTPS/WSS, secure cookies and exact CORS on staging hostnames.
10. Keep DNS cutover and payment/provider activation as separate owner-controlled actions.

## Non-goals

This profile does not configure or activate QR payment, MKassa, cash-register integration, bank acquiring, NFC wallet/acquiring or any automated proof-of-payment flow.
