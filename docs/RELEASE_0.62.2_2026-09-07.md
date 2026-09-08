# Resort OS 0.62.2 — 2026-09-07

Refreeze evidence updated: **2026-09-08**.  
Status: **INTERNAL RC FROZEN / EXTERNAL PRODUCTION CUTOVER STOP**

Accepted executable/release-boundary head: `ac1a45e4cf3ef0e40a7fea6be75c81999e9af0b4`.  
Observed tree-equivalent main merge: `c931b7e12973ecb62b8f9595d60f0d7947e7ad8e`.  
Production source branch: `main`.

## Why the same-version security refreeze exists

The active application runtime remains 0.62.2. After the previous 0.62.2 load-test freeze, strict audit work accepted additional security controls in PRs #137-#143 without changing the public website or the hotel domain model. Because those controls affect production images, Caddy routing/security and executable release guards, `Release RC Truth` correctly failed closed after merge and required a new same-version boundary.

## Security hardening now included

- exact audited runtime image pins for production/Beget, including n8n/PostgreSQL/Caddy;
- host-only authenticated sessions retained; broad cross-subdomain cookie expansion remains forbidden;
- Admin and Staff browser WebSockets routed same-origin to Core;
- PMS/Dining production WebSocket Origin validation;
- Telegram public webhook request body capped at the edge;
- generic public/admin/staff/API request bodies capped at 2 MB at the edge;
- Admin CMS media upload receives a dedicated 8 MB edge limit aligned with FastAPI MIME/magic/SHA/RBAC validation;
- production-package/Beget guards fail closed if the audited topology or runtime pins regress;
- browser realtime topology CI distinguishes the dedicated CMS media route from the generic Admin Next proxy.

All earlier 0.62.2 mutation-safety, Kitchen route/RBAC, migration, route-uniqueness and guarded k6 controls remain in force.

## Evidence

PR #143 exact tested head `ac1a45e4cf3ef0e40a7fea6be75c81999e9af0b4`: **24/24 workflows SUCCESS, 0 failures, 0 cancellations**.  
Observed main merge `c931b7e12973ecb62b8f9595d60f0d7947e7ad8e` is tree-equivalent; GitHub compare reports zero changed files between tested head and merge.  
Observed main merge: **23/23 applicable non-truth push workflows SUCCESS**.  
One additional `Release RC Truth CI` push run failed closed because the previous frozen manifest correctly detected executable/security drift; this record and manifest are the controlled correction.

During PR #143, Browser Realtime Topology CI initially exposed a verifier ambiguity introduced by the dedicated media-upload route. The underlying Caddy WebSocket order remained correct; the verifier was corrected to identify the generic Next proxy explicitly, and the new exact head then passed the complete 24-workflow suite.

## Frozen contracts

- **22 committed migrations**;
- **87 critical constraints**;
- **84 rooms**;
- **12 room categories**;
- **48 rate rows**;
- `ReservationRequest != Reservation`;
- PostgreSQL/Core remain transaction authority;
- OWNER/MANAGER retain reservation/payment authority;
- bank/TTLock remain provider-gated;
- NFC remains outside active V1;
- public website source remains frozen;
- release runtime remains `0.62.2`.

## External boundary

Repository green status is not production verification. The following remain launch work: protected GitHub `main`, Google Drive public-writer remediation, authorized Beget/VPS access, external HTTPS/WSS, real legacy rollback, target migrations/reconciliation, real devices/providers, actual load execution, monitoring/restart evidence, fresh backup/clean restore/off-site evidence, immutable deployment linkage and DNS rollback.

**EXTERNAL PRODUCTION CUTOVER STOP** remains active. No production deployment is claimed by this release record.
