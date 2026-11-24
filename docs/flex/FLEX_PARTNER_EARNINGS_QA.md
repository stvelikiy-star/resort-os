# MARINA SMART FLEX — Agent & Investor Earnings QA

Date: 2026-11-22. Only MARINA SMART/FLEX commercial control plane. No hotel PMS, Production, KÖL, or UI changes.

**Status: QA-only, NOT live agent/investor payout.** Signed bank settlement and payout approvals are not implemented. All statement events are from synthetic FLEX_QA_SIMULATOR cash and explicitly marked QA_ONLY.

## 1. Cash allocation and refunds

Every earnings event must refer to a specific paid SKU invoice line belonging to the approved hotel. Commission base excludes tax and is calculated from the actual allocated amount, not the issued invoice total or a feature toggle.

An agent and investors may each have a rate; combined liabilities on any allocation must not exceed the allocation's tax-excluded amount. The SQL trigger enforces hotel, SKU, payment source, rate and refund source. Duplicate accrual or reversal is blocked. Corrections use new append-only entries.

A later refund reduces the earned revenue in the refund period; this can produce NEGATIVE net earnings for a day or month. Gross accrual, reversals, net accrual and bank payouts are separate concepts.

## 2. Investor repayment

The system MUST NOT treat earned but unpaid investor money as a returned principal. Returning principal or entering a bonus phase requires separately verified ACTUAL cash disbursements and a recorded repayment date. Contract terms, investor share, eligible hotel/SKU and bonus period must be signed and approved; none are assumed from presentations.

In the Python tests 150,000 KGS principal and six bonus months are synthetic examples, not binding commercial defaults.

## 3. API & identity

Independent server module: services/api/app/flex_partner_portal.py.

- GET /v1/partner/me/earnings?period=day|week|month. Sales agent sees only their earnings. Investor requires MFA and sees only their earnings.
- GET /v1/platform/partner-earnings-summary?period=day|week|month. SUPER_ADMIN with MFA gets aggregated partner obligations.
- GET /health. The service declares payouts disabled.

All roles and party IDs are resolved from verified issuer-signed JWT and the independent FLEX membership database, never from client-submitted role, party or hotel. Separate PostgreSQL NOLOGIN and NOINHERIT RLS reader roles prevent cross-investor and cross-agent access.

Data returns accrued gross, reversals, net accrued and event count. actual_paid_kg=null and payout_status=NOT_IMPLEMENTED: no verified disbursement ledger yet. All figures are marked QA_ONLY_NOT_BANK_RECONCILED. Reports use Asia/Bishkek dates and weekly periods start Monday.

## 4. QA and production gates

Preview SQL: docs/flex/sql/0010_flex_partner_earnings_preview.sql. Apply only after FLEX preview 0001–0009 in disposable PostgreSQL. This schema is NOT a production migration.

Test coverage: two hotels, two agents, two investors, cross-party and cross-hotel RLS, signed JWT and MFA, duplicate accrual, refund reversals, agent plus investor overcommit and mismatched source.

Before live payments or payouts: bank merchant sandbox and official signatures; tax/legal approval of referral and investment contracts; segregated approval of payouts; bank disbursement verification; transactional write service and replay protection; backup/restore; release acceptance. Never bypass November Release RC Truth. Design belongs to Claude Code.
