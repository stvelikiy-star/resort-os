# MARINA_SMART_FLEX_INTEGRATION_CONTRACT.md
**Version:** proposal v0.1, 2026-11-24. **Status:** NOT APPROVED / NO ACTIVE PMS INTEGRATION AUTHORIZED.
**Owners:** MARINA SMART FLEX commercial platform (this repo/PR) and separate MARINA SMART PMS maintainer. This is a proposed design for review, **not** an assertion that its new APIs or event flow already exist. A previously implemented link challenge in `FLEX_HOTEL_ONBOARDING_CONTRACT.md` is the only established protocol referenced here.

## 1. Responsibilities and isolation
| FLEX (commercial source of truth) | MARINA SMART (operational source of truth) |
|---|---|
| Commercial hotel ID, agreement/price snapshots, SKU catalog, subscription status, agent/partner/investor liabilities | Operational property ID, PMS users/roles/RBAC, bookings, rooms, guests, restaurant, staff |
| Proposed entitlement set and version history; accounting source after payment evidence is accepted | Apply accepted entitlements in addition to staff RBAC; retain PMS state when module disabled |
| Process **aggregated, non-identifying** feature usage | Generate safe, tenant-scoped usage events and avoid collecting unnecessary identifiers |

No shared write-enabled database users. No PMS imports. Never assume FLEX tenant ID equals PMS property ID. Owner of the staff permissions stays PMS.

## 2. Identity and hotel mapping
**Existing, tested only in isolated FLEX QA:** `POST /v1/onboarding/hotels` creates PENDING commercial hotel using an idempotency key; `POST /v1/onboarding/hotels/{hotel_id}/challenge` issues one-time nonce; `POST /v1/onboarding/challenges/{challenge_id}/confirm` validates Ed25519 PMS deployment attestation and stores verified link. Link message is specified in `FLEX_HOTEL_ONBOARDING_CONTRACT.md`. Trust registry `flex_trusted_deployments`, pairing `(deployment_id,property_external_id)`, expiry and single-use are non-negotiable. The real PMS-side signer is **not yet implemented or approved**. VERIFIED link must not activate subscription or module rights.

**Proposed canonical mapping** kept server-side only:
`{flex_hotel_id:UUID, pms_deployment_id:opaque string, pms_property_id:opaque string, verified_at:UTC timestamp, trust_key_id:opaque, status:VERIFIED|REVOKED}`.
There must be exactly one active mapping per PMS deployment/property pair. Revalidate mapping for every service exchange; no client-provided hotel selector may override signed subject.

## 3. Service authentication and replay policy (PROPOSED)
Separate service-to-service trust from interactive SUPER ADMIN credentials. Use verified Ed25519 signatures with rotating pinned public key identifiers; TLS; allowlisted issuer/audience; short timestamp skew (propose <= 5 min, to be jointly approved). Include message ID/UUID, canonical bytes/signing version, deployment, property, FLEX hotel, issued_at and expiry in every signed envelope; reject expired, future-dated, unsigned, wrong audience, unknown/revoked key or wrong tenant. Maintain replay ledger keyed by `issuer+message_id`; identical retries return prior accepted result, modified payload for same ID is rejected. Protect enrollment and rotation through independent infrastructure approval; never expose private keys in browser, code or contract.

## 4. Commercial rights / module change (PROPOSED, **DISABLED INITIALLY**)
FLEX creates an **immutable offer** for a `flex_hotel_id`, snapshotting SKU, capability key, effective interval, plan/version, supported dependencies and decision provenance. Only an approved commercial transition may create a signed entitlement revision; no PLANNED product, DRAFT, unpaid invoice, unverified hotel, trial proposal or manual browser button may grant access.

Envelope proposed after independent approval:
```json
{
 "schema_version": 1,
 "message_id": "<UUID>",
 "flex_hotel_id": "<UUID>",
 "pms_deployment_id": "<verified deployment>",
 "pms_property_id": "<verified property>",
 "entitlement_revision": 1,
 "effective_at": "<RFC3339 UTC>",
 "expires_at": "<RFC3339 UTC or null>",
 "capabilities": ["<reviewed capability key>"],
 "catalog_snapshot_id": "<immutable approved reference>",
 "issued_at": "<RFC3339 UTC>",
 "signature": "<server-verifiable signature, representation TBD>"
}
```
**Illustrative field names only**; no deployed endpoint or final canonicalization. PMS verifies the signer, mapping, monotonic revision and allowable activation state before atomic application and returns a signed acknowledgment containing message ID, accepted revision, decision and timestamp. Use outbox/inbox delivery with retry/backoff; duplicate identical revisions acknowledge idempotently; lower revisions ignored/rejected. No direct SQL/PMS DB connection from FLEX. Staff RBAC and property isolation are enforced **after** commercial entitlement check. Disabling a module must preserve all historical business data and existing hotel core operations; outages must not make PMS stop service. Rollback is a new signed higher revision, never silent deletion of audit history.

**Freeze until explicit second release gate:** live entitlement activation/deactivation, automatic ENFORCE and payment-coupled activation are OFF. This draft provides a future contract, not permission to implement a PMS toggle.

## 5. Usage analytics events (PROPOSED)
Event intent: measure commercial value without identifying guests or profiling individual staff. Minimum shared envelope:
```json
{
 "schema_version": 1,
 "event_id": "<UUID>",
 "property_id": "<verified PMS property reference>",
 "event_name": "reservation.created",
 "capability_key": "<commercial mapping key>",
 "occurred_at": "<RFC3339 UTC>",
 "platform": "web",
 "role_category": "RECEPTION",
 "result": "success"
}
```
Candidate event names include `pms.grid.opened`, `reservation.created`, `reservation.updated`, `reservation.cancelled`, `dining.order.created`, `kitchen.order.completed`, `warehouse.stock.received`, `finance.report.opened`, `analytics.export.clicked`. These names are proposals from master requirements, **not an implemented PMS instrumentation catalog**.

Semantics: a UI click counts as interaction, a completed command as successful operation, and a valid business result as separate outcome — **10 clicks != 10 bookings**. Never add guest name, phone, passport, booking content, message body, password, auth token, payment credentials, staff identity or individual-employee surveillance attributes. Source signs batches/envelopes; FLEX resolves property link using trusted mapping, deduplicates on `(deployment_id,event_id)`, verifies schema/timestamps/allowed event name, and stores only permitted aggregate projections. Replayed event cannot increase counts. Reject invalid/unknown tenant and schema. Limit raw retention (propose 30 days) and aggregate retention (propose 13 months); final windows, late event handling, privacy and legality must be approved. Aggregation by tenant/capability/event/platform/role category/result/day, week starting Monday, month in Asia/Bishkek; keep source receipt and rejection counts. Back-pressure/offline queue must not interrupt PMS operational transactions. Delivery endpoint, ack format, signing method, payload size and batch policy **TBD by joint review**.

## 6. Failure modes and data protection
- FLEX outage: PMS preserves previously accepted entitlements and essential daily operations, queues capped telemetry when possible; do not block guests or staff login.
- PMS outage: FLEX retains pending immutable commercial proposal and delivery outbox, does not claim module applied until verified acknowledgment.
- Malformed or expired signed input: reject, audit reason without secrets, no mutation.
- Duplicate or delayed delivery: replay ledger and monotonic revision; no double counts/double activation.
- Revoke a deployment: stop future signed exchanges and audit; previously recorded financial/usage history stays append-only.
- Payment/ledger: FLEX owns verified receipt evidence and partner finance. **Nothing in this contract makes a payment, collects money, allocates bank funds or releases payouts**; all frozen.

## 7. Roles and allowed view (no new role grants issued by this spec)
SUPER_ADMIN: manage commercial hotel registry, draft tariff, prices, allowed aggregate data and audit; powerful actions require server authorization. HOTEL_OWNER: own assigned hotels only. SALES_AGENT: own attributed portfolio and commission only. PARTNER: separate, contractual scoped role **not yet implemented as an approved app route**, never aliased to agent/investor. INVESTOR: own contractual principal, rate, verified eligible revenue, net accrued, ACTUAL disbursements and end date only; never other investors' data. No role reads guest/operational PMS records through FLEX. Confirmed money, accrued money and actual paid must be separate; unknown paid amount remains null, never 0 by guess.

## 8. Open decisions required before joint approval
1. Canonical PMS deployment/property identifiers and trust enrollment/key rotation owner.
2. PMS capability-key mapping, module dependency graph, core functionality and retention when disabled.
3. Final signed entitlement envelope canonicalization, method/path, ack and version compatibility window.
4. Usage event names, schemas, retention/legal basis and retry/late-event behavior.
5. Both parties' release acceptance, rollback, monitoring and outages.
6. Ensure two isolated hotels A/B and two agents/investors exercise cross-tenant denials in independent QA.
7. Confirm whether PARTNER needs a separate dashboard and contract types from INVESTOR/SALES_AGENT.
No production activation before these items are accepted.

## 9. PMS-only handoff to the other ChatGPT maintainer (NO ACTION ON PMS BY FLEX)
- Review and return the trusted PMS deployment/property mapping and secure Ed25519 challenge signer design; do not expose key, guest DB or existing MARINA SMART RBAC.
- Produce agreed capability-key catalog mapped to **existing** PMS API checks, keeping module grants separate from staff roles and retaining data when disabled. **Do not enforce until separately approved.**
- Propose nonblocking instrumentation for the event catalog, explicitly distinguishing clicks, operations, and outcomes, no guest PII or per-staff surveillance.
- Agree signing envelope, monotonic revision/ack, idempotent inbox, outage semantics, version policy and staging tests.
- Return a written acceptance/rejection with amended schemas; do not merge or deploy based solely on this document.

## 10. Acceptance evidence (not yet supplied)
- Approved contract signed off by both maintainers.
- Isolated two-hotel test with signed valid link, wrong-deployment/wrong-property, expired/replayed signatures and denial.
- No privileges leaked across admin, owner, agent, partner, investor.
- P0 pilot with synthetic events, counts and duplicate protection; PMS remains responsive if FLEX disconnected.
- Independent DB backup+restore and one QA SHA; deploy approved independently.
**Overall status: NO-GO; no confirmed cross-project deployment.**
