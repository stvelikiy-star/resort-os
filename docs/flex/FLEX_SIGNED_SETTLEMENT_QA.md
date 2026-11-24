# MARINA SMART FLEX — signed QA settlement

Date: 2026-11-22. ONLY a disposable PostgreSQL CI sandbox. This document describes test scope, not a Finik merchant integration or bank operation.

## Official Finik integration context
Official Web SDK documentation: https://www.finik.kg/documentation/web-sdk/integration/ and https://www.beta.finik.kg/en/documentation/web-sdk/webhooks/

Finik requires verification of an RSA-SHA256 request signature with their official public key, timestamp, host/path and x-api headers plus idempotent transaction IDs. No authorized merchant keys or verified Finik canonical signing implementation are installed in this branch.

FLEX_QA_SIMULATOR is intentionally DIFFERENT from Finik: a disposable CI process generates ephemeral Ed25519 keys and signs a small, fixed, local JSON envelope. It runs only when FLEX_SETTLEMENT_MODE=CI_DISPOSABLE_ONLY. Never accept Finik callbacks with this simulator.

## Added

- services/api/app/flex_qa_payment.py: reject forged, stale, wrong-currency or misscoped test evidence; only a signed synthetic provider transaction creates an internal verified QA object.
- docs/flex/sql/0009_flex_signed_qa_settlement_preview.sql: append-only evidence tied to intent, invoice, hotel and receipt; RLS with NOLOGIN test writer; provider constrained to the simulator.
- services/api/app/flex_qa_settlement.py: serializable transaction, advisory lock per invoice, bank-event ID uniqueness, cross-hotel and amount match, immutable simulated receipt and per-feature allocations. Identical replay must not create a duplicate; changed payload must fail.
- scripts/marina_flex_qa_settlement_fixture.sql: two synthetic hotels, signed fictional agreements, two issued invoice snapshots, three synthetic payment intents.
- scripts/marina_flex_signed_qa_settlement_e2e.py: actual PostgreSQL CI tests of signed proof, duplicate/replay, wrong invoice/amount, partial and excess payment credit and restricted financial privileges.
- Dedicated GitHub Actions workflow on disposable PostgreSQL 16.

## Important
A synthetic CI receipt is NOT bank settlement. This module has no public HTTP route, no real QR payment, no bank credentials, no customer subscription mutation and no effect on hotel PMS or Production.

Next production gates:
1. Approve a merchant/payment provider agreement, fees, settlement/refund and Kyrgyz fiscal details.
2. Obtain official RSA canonical signer and independent test vectors; validate production/beta signatures, exact host/path/headers, timestamp and key rotation.
3. Implement a dedicated least-privilege bank webhook adapter, persist signed evidence and reconcile with provider status/merchant statements.
4. Check amount, currency, merchant account, invoice, payment intent and tenant; quarantine contradictions.
5. Verify concurrency/rollback/retries/chargebacks and backup/restore before any live invoicing.
6. Only then connect confirmed payment to subscription renewal; never enable hotel blocking without approved grace period and safe essential operations.
7. Respect Release RC Truth and do not merge or deploy frozen release without approval.
