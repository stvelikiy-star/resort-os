# MARINA SMART — documented correction evidence P0 / zz124

**Status:** isolated additive Draft, not recognized financial profit.

## Purpose
Correcting the amount allocated to a room night or served kitchen order requires an explicit existing `owner_revenue_source_events.APPROVE_SOURCE` ID. Changes may arise from discounts, cancellations, bundled services, refunds or tax classification.

## Input and conservative accounting rules

- `DISCOUNT`: reduces the **provisional source face-value candidate**. It is not posted earned revenue.
- `CANCELLATION`: same provisional reduction bucket as discount, but separate evidentiary classification. The two together cannot exceed the originally approved source face value.
- `REFUND`: **cash-related evidence only**. It is not automatically an additional reduction to earned revenue, because a refunded cancellation may represent the same financial event. Customer `Payment` records and actual bank settlement need independent reconciliation.
- `PACKAGE_SPLIT`: distributes a portion of the face value into `LODGING`, `DINING`, `OTHER`. It is a classification, not another sale. The sum of active allocations plus discounts/cancellations cannot exceed source face value. A balanced complete allocation and resulting revenue policy remain separate acceptance requirements.
- `TAX_COMPONENT`: classification of a stated tax component of the remaining source amount, not an automatic tax calculation or cash tax payment.

All entries require an operation UUID, source approval UUID, exact positive amount in KGS, document reference/date, 64-digit lowercase SHA-256 fingerprint, evidence reference and meaningful reason. **These metadata are owner-supplied; without verified uploaded bytes and independent accountant review the document authenticity is NOT confirmed.** Client cannot switch the source/property through the document path.

Events are append-only in PostgreSQL; reversal is a new immutable event. The same event UUID and identical payload replay once; modified payload `409`; distinct UUID with same source+kind+component+document reference `409`; second reversal `409`. Transaction-level advisory lock per approval serializes competing corrections and source reversals.

## API

- `POST /api/v1/admin/finance/owner/revenue-corrections` — returns original journal event or same-ID replay, source-calculated caps and no customer Payment.
- `POST /api/v1/admin/finance/owner/revenue-corrections/{correction_id}/reverse` — immutable reversal.
- `GET /api/v1/admin/finance/owner/revenue-corrections?from_date=...&to_date=...` — evidence history.
- `GET /api/v1/admin/finance/owner/accrual-readiness` — totals of active documented corrections by kind, with `recognized_revenue_kgs=null`, `recognized_profit_kgs=null`, `metadata_only_documents_not_independently_verified=true`. Web and Mobile OWNER read this same report.

## Gates

- Unchanged historical SQL migration hashes; zz124 additive pin, test-DB migration and isolated rollback.
- Real isolated PostgreSQL E2E: 8-way same-ID correction/reversal, changed retry conflict, duplicate document, over-face discount, invalid SHA, refund/tax/package split distinct, reversed source prohibited, immutable UPDATE/DELETE, non-OWNER 403, no added Payment, consistency with Web/Mobile DTO.
- Mobile and Web do not label these amounts as recognized P&L. This is not an electronic document storage system or independent verification of documents.

## Pending before real accounting revenue and OWNER profit

1. Upload / immutable storage and **server-side hashing of document bytes** plus independent approval and proof binding; support partial refunds and actual payment provider facts.
2. Discount and package net-price allocation by tax treatment, tariff and component, including VAT/tax applicability and fiscal receipt rules in local jurisdiction.
3. Account-based immutable recognition journal, adjustment entries, effective dates, closed periods, original source/version fingerprints, multi-tenant race/restore guarantees.
4. Actual served portions versus kitchen stock/production/waste, supplier/owner expenses and period accrual with signed accounting policy.
5. Physical Android/Expo Go and full integrated same-SHA E2E.

**NO-GO.** This work does not modify Ubuntu, ASKA TASH, production, WhatsApp, AI or Future Luxury design.
