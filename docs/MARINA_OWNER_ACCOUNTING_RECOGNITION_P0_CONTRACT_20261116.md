# MARINA SMART — P0 OWNER accounting recognition journal: implementation contract

Status: **SPECIFICATION ONLY / NOT IMPLEMENTED / NO-GO**. Parent exact SHA: `e126caf3dc68e027b4f448721f7ed9a3c231e01b` (#548, 63/63 Actions success). No production, Ubuntu, ASKA TASH, main, AI/WhatsApp or visual-design modifications.

## Separation of responsibilities

- Existing `owner_revenue_source_events` (#541) verifies delivery-source facts only.
- Existing `owner_revenue_correction_events` (#545) records corrections; REFUND is cash evidence, PACKAGE_SPLIT and TAX_COMPONENT are classifications, not second sales.
- Existing `owner_revenue_evidence_documents` (#548) stores actual immutable bytes with server SHA-256; byte integrity **does not** prove legal authenticity or accounting approval.
- **New accounting journal must be separate**, append-only, with explicit accountant-approved policy and recognition controls. Never reinterpret existing event rows as posted P&L on migration.

## Journal invariants to implement (next code PR)

1. Scoped `propertyId` across journal header, lines, source events and evidence references; no cross-tenant reads/writes. Each journal posting has a client UUID operation id, hotel-local accounting date, source event reference, policy version, actor, approved-by identity/time, and deterministic payload fingerprint.
2. Post balanced **debit and credit** lines with exact decimal currency values (KGS, no float); totals debit == totals credit; approved chart-of-accounts codes and period required. A draft/preview is never a posted entry.
3. Posting is idempotent under concurrent retries: identical operation UUID and payload returns same immutable entry; same UUID with modified payload -> HTTP 409; source recognition uniqueness prevents one source being posted twice under different operation IDs.
4. Existing journal rows and posting lines reject SQL UPDATE/DELETE. Corrections use separate, balanced reversing entries linked to the original and carry their own operation UUID, accounting date, reason and evidence. Do not modify history.
5. Recognition requires an explicit verifiable source and approved document/exception decision. Document upload alone cannot authorize a posting. Missing sign-off or policy mapping -> blocked state / no P&L changes.
6. Approval and reversal enforce rights separately; OWNER sees accounting data, but **OWNER role alone does not imply independent accountant approval**. Establish authorized approver identity/permission and separation-of-duties policy before enabling posting.
7. Revenue recognition is based on delivered room-night/served restaurant sources with documented allocation rules. Never sum guest payment, folio line and kitchen order as three sales. Discount/cancellation reduces applicable sales once; package and tax components are allocations; refund cash movement does not by itself reduce earned revenue twice.
8. Expenses: supplier payable inception, stock receipt, supplier settlement, return/credit, kitchen consumption and operating expense are distinct events. Supplier settlement is not a second expense. Inventory acquisition is not immediate COGS; COGS requires documented consumption/sale valuation. No speculative COGS.
9. Expose read-only journal details and reconciliation to OWNER Web + Mobile using current Future Luxury styling, without removing existing numbers. Show period, policy, posting status, source and evidence, debits/credits, unresolved differences. Until recognition and close rules are accepted, recognized profit stays null.
10. Period close/reopen policy, corrections to past periods, accrual reversals, tax treatment, rounding, payroll, depreciation, inventory variance and foreign currency must be explicitly decided; do not invent tax rates or chart of accounts. The initial journal may be limited to approved mappings, with clear blocked categories.

## Acceptance gates

- PostgreSQL migrations are additive and retain hashes of all existing migrations. Isolated apply / rollback rehearsal; proof of SQL append-only enforcement.
- API: OWNER viewing and authorized posting/approval; denied roles 403; hostile property ID cannot override trusted tenant; forged evidence/source rejected; no secret or PII leakage in logs.
- Isolated PostgreSQL E2E: booking three-night allocation with no double count; served restaurant folio one source; discount and cancellation; TAX_COMPONENT/PACKAGE_SPLIT classification; REFUND cash-only; purchase -> inventory -> kitchen consumption -> COGS; supplier receipt/settlement/return; balanced lines and period cutover.
- Eight parallel identical operations produce one posting; mutated UUID gives 409; duplicate source under different UUID gives 409; reversal once with safe retries; audit preserves full history.
- Reconcile source totals, journal totals, and balance by property/period using exact decimals and explicit unmatched-source report. No non-null recognized P&L before accounting approval.
- Web and Mobile owner views show the same PostgreSQL-backed figures, RBAC and RU/KG/EN labels; run full 63-workflow exact-head checks, then cross-client E2E and physical Android acceptance.
- Keep this branch Draft and separate; merge with #537/#547 and Future Luxury #535/#546 only after exact-file conflict review and a unified CI SHA.

## Open policy decisions requiring accounting sign-off

Chart of accounts and authorized approvers; accrual/recognition service dates; lodging tariff/package splits; tax bases and rates; discounts, refunds and post-checkout cancellations; inventory weighted cost and wastage; supplier credit differences; depreciation/payroll; period-close locking; handling historical unverified evidence. Until approved, explicitly record blockers instead of booking profit.
