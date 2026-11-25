# MARINA SMART FLEX — QR provider contract (candidate, NOT activated)

Date: 2026-11-22. **Development-only contract**. No merchant account, QR generation, payment capture, bank webhook or real URLs connected to MARINA SMART. This documentation refers ONLY to MARINA SMART FLEX.

## 1. Verified public provider information

Candidates evaluated (official documentation, access verified 2026-11-22):

- Finik Web SDK — https://www.finik.kg/documentation/web-sdk/integration/ and https://www.finik.kg/documentation/web-sdk/webhooks/
  - Signed `POST /v1/payment` to `https://beta.api.acquiring.averspay.kg` for beta (production separate).
  - The payload requires `CardType=FINIK_QR`, `PaymentId`, `RedirectUrl`, `Data.accountId`, `Data.name_en`, `Data.webhookUrl`; `Amount` should be fixed for subscriptions.
  - API requests need `x-api-key`, `x-api-timestamp`, `signature` with RSA-SHA256 canonicalization. Create may respond `302 Location` pointing to a hosted payment page.
  - Webhook may be delivered repeatedly; verify Finik's signature using their **environment-specific** public key and canonical request, including host and x-api headers; record `transactionId` as idempotency.
  - A client redirect is NOT bank payment confirmation. Use verified webhook and provider reconciliation.
  - Official docs describe `success` / `succeeded` as example statuses; confirm final set with provider before implementing real handling.
- xPay — https://xpay.kg/developers/ — public QR API, webhook, payment-page and status API, but full documentation and test merchant credentials require provider onboarding.
- GoPay — https://gopay.kg/oplata-na-saite — QR/payment pages, API and webhook; verify terms, support for subscriptions, settlement/reversal and tax receipt integration with merchant before selecting.

**No provider selected or contracted.** This list is technical evaluation, not a promise of availability/fees or bank integration. Confirm business eligibility, licensing, settlement times, fees, refunds/chargebacks, invoice/KKM handling, callback signatures and production support.

## 2. Code implemented in this PR

`app/flex_qr_provider.py` is a pure, **offline** Finik-compatible payload builder and an UNTRUSTED webhook schema parser. It is intentionally not imported by the live PMS or FLEX commercial API. No live network, credentials, private keys, QR images, payment URLs, redirects or paid state.

A signed invoice must exist, and approved server-side records must provide: invoice UUID, unique payment intent UUID, unpaid KGS balance, merchant `accountId`, fixed trusted HTTPS callback/redirect and language `ru`/`ky`/`en`.

`Amount` remains Python `Decimal`: the final transport must use Finik's supported canonical signer/JSON serialization without binary floating-point loss. Do not serialize this object with default `json.dumps` or sign a handcrafted payload.

The webhook shape parser deliberately returns `verification_state=UNTRUSTED`; do NOT wire it into `flex_confirmed_payments`, `flex_invoice_status` or entitlement activation. Incoming JSON numbers must eventually be parsed with decimal precision and verified against the signed raw request.

## 3. Required production gates

1. Create an authorized merchant account in MARINA SMART company's name; obtain sandbox API key, merchant account ID, Finik environment public key and agreed settlement instructions outside GitHub.
2. Get definitive canonical signature SDK/test vectors from Finik, including exact host, path, headers, query, body ordering, timing and key rotation. Reject wrong signatures and replay; do not implement a guess.
3. Build server-only HTTPS payment intent creation, invoice amount, idempotent UUID, signed bank request, no redirect auto-follow, provider page URL allowlist and expiration.
4. Verify bank-signed webhook, payment UUID, currency, amount, correct merchant account, result state and final settlement. Handle duplicate/out-of-order webhook and status polling.
5. Write verified receipt and allocations atomically under restricted DB roles and concurrency locks; update visible invoice balance from reconciled ledger only.
6. Add refund provider confirmation + chargeback paths and alert/manual reconciliation queue.
7. Link subscription renewal only after a confirmed settled payment; suspended hotel data/active stays remain safe.
8. Run independent rollback/backup/restore, two-hotel E2E, security review, fiscal compliance and controlled release approval.

**No merchant or customer data should be entered into test files.** Synthetic hostname `billing.ms.go.kg` in CI is a placeholder, NOT a deployed endpoint.

## 4. Why QR is not enough to credit the hotel
A created QR, displayed link, user redirect, screenshot, notification not validated by the provider, or payment amount typed by a client is **not cash receipt**. The only financial source of truth is verified provider settlement (or separately controlled manual approval) with append-only ledger and its reversals.
