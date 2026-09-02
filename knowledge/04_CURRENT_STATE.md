# RESORT OS — CURRENT STATE

Version: 3.7
Date: 2026-09-02
Status: **INTERNAL RC FROZEN / REPOSITORY+CI VERIFIED / EXTERNAL PRODUCTION EVIDENCE INCOMPLETE / NOT LIVE**
Canonical: YES
Authority: factual implementation reality only

**TARGET != CURRENT. IMPLEMENTED != VERIFIED. CI VERIFIED != EXTERNAL VERIFIED != PRODUCTION VERIFIED.**

## 1. Audited release boundary

Repository: `stvelikiy-star/resort-os`.
Integration branch: `integration/site-pms-cms-20260827`.
Accepted executable head: `ce2d8ecde43c294162a782f7912425ced5258f99`.
Observed integration merge: `05777f3371bd42b4c4cc9a8d6d68fa9b482b238c`.

The exact accepted executable head completed **17/17 non-RC workflows successfully, 0 failures**. The separate Release RC Truth workflow failed on the pre-refreeze head by design because the prior RC was still frozen.

The observed integration merge has **0 changed files** versus the tested executable head; therefore the merged executable tree is identical to the tree that passed the 17 successful contours.

A subsequent docs-only integration merge `beb5cc59a42256c5cfd50c0c336b4fe611ed1c8c` contains reviewed release/operator documentation only. `scripts/release_rc_truth_guard.py` treats exactly `docs/README.md` and `docs/STAGING_RUNBOOK_2026-08-28.md` as allowed release hygiene; arbitrary `docs/**` drift is not allowed.

The canonical machine-readable RC boundary is `release/current-rc.json`.

The canonical integration branch is the only release integration source. `main` is not a production source and must not be used for deployment/cutover while stale relative to the accepted integration RC.

Repository/CI evidence is not external production evidence. **EXTERNAL CUTOVER remains STOP.**

## 2. Authority architecture

`PUBLIC SITE / PMS / STAFF / KITCHEN / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

`ReservationRequest != Reservation`.

OWNER/MANAGER retain reservation and payment authority. AI/n8n cannot confirm payment, guarantee a Reservation, invent a fixed prepayment percentage/payment route, bypass Core availability/pricing, or write transaction truth through Google Sheets.

Growth outbound authority remains `NONE_AUTOMATIC`.

Kitchen operational totals do not automatically create Hotel Payment and do not mutate accommodation totals.

NFC acquiring/wallet remains **DEFERRED** and outside active V1 composition.

## 3. Database and room-register release contract

Committed migration chain is exactly:

`0_init -> 1_site_content -> 2_guest_service_tasks -> 3_owner_analytics_snapshots -> 4_guest_engagements -> 5_guest_os_core -> 6_service_point_qr_operations -> 7_kitchen_operations`.

External staging/production migration mechanism: `npx prisma migrate deploy`.

The database release contract contains 27 critical hotel/payment constraints. Prisma and `@prisma/client` remain exactly pinned to `6.12.0`, deterministic lockfile installs are required, and HIGH/CRITICAL database dependency findings are release blockers.

Canonical physical room authority is repository-controlled:

- `data-intake/rooms.csv` — exact 84 rooms / 12 categories;
- `data-intake/room-register-owner-approval.json` — checksum-bound `OWNER_APPROVED` evidence;
- `data-intake/owner-room-checklist.json` — historical provenance only.

Room gate #38 is CLOSED/COMPLETED. Do not reopen the room questionnaire. The remaining external room requirement is target reconciliation only: `dry-run -> exact diff review -> safe apply -> zero diff`, preserving active runtime state protections.

Google room/import sheets are not a second mutable production authority.

## 4. Public site

Repository/CI verified:

- RU/KG/EN public truth and browser contracts;
- Transfer before Tours;
- Core availability/pricing boundary;
- ReservationRequest rather than automatic guaranteed Reservation;
- no fixed 30% prepayment claim;
- no automatic payment confirmation;
- current contacts and approved service facts;
- no gym or sports-ground claim;
- no Elsom or unverified online acquiring claim;
- CMS -> Core -> public runtime linkage;
- public room imagery fail-closed to verified general resort media unless explicit category/public binding exists.

Static room catalog values are presentation data; live availability and calculated stay price remain Core authority.

External rendered production truth is NOT VERIFIED.

## 5. PMS / Reception

Implemented and regression-gated:

- compact room × night owner grid for the canonical 84-room register;
- single-night click and multi-night drag selection;
- Core pricing preview/commit;
- move, resize and Split Stay;
- stale/conflict/race rejection;
- TECH_BLOCK protection and CLEAN check-in gate;
- realtime snapshot/update and audit trail;
- RoomAssignment relocation;
- checkout -> DIRTY/housekeeping lifecycle;
- Reception check-in/check-out/QR authority without commercial/payment authority;
- one-time six-digit Guest OS PIN at successful check-in;
- audited PIN reissue only for an ACTIVE stay on a CHECKED_IN reservation;
- Admin/PMS fail-closed to OWNER/MANAGER/RECEPTION/MAID/TECHNICIAN;
- RU/KG/EN admin locale selector.

## 6. Stay / Guest OS / CRM

Implemented and regression-gated:

- canonical Stay + RoomAssignment lifecycle;
- permanent Room QR with server-side token hash;
- PIN verification and HttpOnly GuestSession;
- session revoke at checkout;
- in-stay guest service requests;
- factual guest history/preferences/audit;
- Guest OS Kitchen ordering through GuestSession authority.

Room QR/GuestSession remains separate from anonymous Service Point QR.

## 7. Staff / Guest Services / Service Point QR

Implemented:

- MAID and TECHNICIAN workflows;
- Reception and Dining access where defined;
- unified Guest Services Center over OperationalTask;
- role-based routing;
- staff voice intake contract;
- in-stay requests do not automatically mutate room state or create Payment;
- anonymous `/p/{token}` service-point request flow;
- opaque display-once token, SHA-256 stored hash, issue/rotate/revoke;
- no Guest/Stay/Reservation/Payment data on public Service Point QR;
- context/idempotency/replay constraints;
- NFC endpoint absent from active V1 runtime.

## 8. Kitchen / Dining

Implemented and regression-gated:

- Kitchen Admin for OWNER/MANAGER/DINING_STAFF;
- editable provisional RU/KG/EN menu;
- factual physical table register;
- states `AVAILABLE / RESERVED / OCCUPIED / CLEANING / OUT_OF_SERVICE`;
- KitchenOrder lifecycle `NEW -> ACCEPTED -> COOKING -> READY -> SERVED/CANCELLED`;
- table/room/Stay/Reservation context where appropriate;
- Guest OS ordering via GuestSession;
- transactional check-in -> idempotent Dining arrival card with repair sync fallback;
- no sensitive payment data in Dining arrival routing;
- audited order/check-in operations;
- no automatic Hotel Payment and no automatic accommodation-total mutation.

Real table layout/count remains operational input and is not fabricated in code.

## 9. Finance / Owner management

Implemented and regression-gated:

- Payment fact/idempotency controls;
- reservation ledger, remaining/overpaid/debtors including checked-out debt;
- manager-controlled prepayment requirement without a global fixed percentage;
- `Asia/Bishkek` financial-day handling;
- Owner Intelligence / Control / Growth / Dashboard operational analytics;
- factual KPIs and recurring-fault views;
- no statistical forecast claim when history is insufficient;
- Growth outbound authority `NONE_AUTOMATIC`;
- Kitchen finance isolation.

These are operational/management metrics, not statutory accounting.

## 10. AI / n8n / communications

Implemented and CI-verified:

- unified inbox and payload-safe provider idempotency;
- `Conversation <-> ReservationRequest` linkage;
- AI draft authority boundary;
- n8n -> Core contract;
- website direct-Core booking boundary;
- provider delivery evidence model: QUEUED/UNKNOWN is not treated as delivered;
- service credentials cannot confirm payment or guaranteed Reservation.

PR #102 hardened the actual customer-facing Core facts returned by `/api/v1/automation/read/hotel-facts`:

- check-in `14:00` and checkout `12:00` are owner-confirmed;
- gym and sports grounds are confirmed absent;
- sauna is winter-only, 5000 KGS/hour, approximately 4–5 people;
- billiards 500 KGS/hour;
- table tennis free for staying guests;
- parking approximately 20–30 cars and free for staying guests;
- laundry and conference halls are `UNKNOWN_DO_NOT_PROMOTE` rather than advertised facts;
- unverified payment-method/provider enumeration is absent from customer-facing AI context;
- launch payment methods/providers remain `NOT_VERIFIED_FOR_LAUNCH` until real manager/provider evidence exists.

`n8n Resort Core Contract CI` verifies these facts through a running Core API, not by static JSON inspection only.

Real provider credentials/live provider E2E remain external evidence.

## 11. Media / AI content boundary

Google Drive contains separated project media and an AI media registry, but Drive is not public runtime truth.

Three room groups are currently usable for AI context as identified internal assets while public website category binding remains fail-closed until explicit evidence:

- cottage double standard — 9 files;
- two-room standard — 6 files;
- apartment with kitchen — 8 files.

For these groups `AI_USE=YES` while `PUBLIC_USE=NO` until public category binding is explicitly approved. Pending suite/fallback groups remain unavailable as exact-category media.

## 12. Deployment tooling state

Repository/CI contains fail-closed contracts for:

- exact eight-migration deployment;
- production package build;
- CI-local Full Staging;
- backup -> clean restore;
- exact Git SHA -> deployed image linkage;
- external staging orchestration;
- staging mutation safety;
- public-truth probe;
- monitoring evidence;
- physical room reconciliation;
- final launch verifier;
- active-V1 NFC exclusion.

`docs/README.md` is the current documentation-authority index. The dated `docs/STAGING_RUNBOOK_2026-08-28.md` is now explicitly a historical/local staging reference and cannot override current release authority.

## 13. External / production state

Still NOT VERIFIED / NOT EXECUTED:

- GitHub branch protection and required checks enforcement;
- Google Drive public-writer remediation for launch-control data;
- actual Beget host/account/network preflight;
- verified rollback capture/restore proof for current legacy `3korony.com`;
- isolated external HTTPS/WSS staging;
- external rendered public-truth probe;
- real staging room reconciliation to zero diff;
- real iPhone/Android/desktop/Telegram/Staff/Kitchen acceptance;
- E2E for every provider enabled at launch;
- real monitoring/alerting/off-site backup/restore evidence;
- fresh pre-cutover backup and exact DNS rollback capture;
- explicit OWNER production cutover approval;
- production/DNS cutover.

Live `3korony.com` must therefore still be treated as the legacy site until proven otherwise.

## 14. Launch rule

Canonical launch gate: `knowledge/09_LAUNCH_ACCEPTANCE.md` plus `scripts/verify_launch_acceptance.py`.
Canonical RC manifest: `release/current-rc.json`.

Production remains **EXTERNAL / PRODUCTION CUTOVER STOP** until every required real evidence gate is verified. CI success, Google Drive state, a Vercel preview or a dated handoff cannot authorize DNS/provider activation or a production declaration.

## 15. Extension rule

Extend rather than rewrite the verified Resort Core/PostgreSQL/PMS/Stay/Guest OS/Guest CRM/OperationalTask/Finance/Owner analytics/Inbox/Audit/RBAC boundaries. Do not activate NFC or automatic commercial/payment authority as a side effect of launch work.
