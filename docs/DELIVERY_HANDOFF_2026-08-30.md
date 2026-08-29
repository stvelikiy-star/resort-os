# THREE CROWNS RESORT OS — DELIVERY HANDOFF

Delivery date: 2026-08-30
Prepared: 2026-08-29
Repository: `stvelikiy-star/resort-os`
Branch: `integration/site-pms-cms-20260827`
PR: `#37`

## 1. Delivery status in one line

Three Crowns Resort OS is an **integration release candidate verified in CI-local staging**, with **26/26 successful PR workflow contours on executable head `1be110c35e1e7d5876cae40a1b58cef42bd10a22`**. It is suitable for owner/demo/release handoff. External production remains blocked until real host, rollback, HTTPS/WSS, device and provider acceptance evidence exists.

## 2. What is included in the delivery

### Public site

- premium public site direction;
- room catalog and media baseline;
- RU/KG/EN contour;
- Resort Core availability/pricing;
- public booking creates `ReservationRequest`;
- owner-approved public truth guards;
- no gym/sports-ground claims;
- no invented fixed prepayment/acquiring claims.

### PMS / Reception

- canonical V9 universal chessboard;
- search, filters, grouping and density;
- 7/14/21/31-day windows;
- arrivals/departures/in-house/free/debt/attention slices;
- server-authoritative schedule preview -> explicit commit;
- room move/resize;
- Split Stay;
- stale/conflict protection;
- TECH_BLOCK protection;
- CLEAN check-in gate;
- realtime refresh;
- AuditLog/history.

### Guest Services

Structured Reservation-linked services:

- TRANSFER;
- MEALS;
- PARKING;
- SAUNA;
- BILLIARDS;
- EXCURSIONS.

Guest Service does not automatically mutate accommodation total or create Payment.

### Staff Operations

- MAID / TECHNICIAN role boundaries;
- housekeeping task lifecycle;
- inspection / rework / acceptance;
- technician work contour;
- staff mobile/PWA surface;
- voice contour CI coverage.

### CRM / Inbox / AI

- booking request pipeline;
- unified inbox/audit contour;
- Telegram sales contour;
- n8n contracts;
- AI Sales Draft;
- AI Administrator;
- human Reservation/payment authority preserved.

### Owner Intelligence

- repeat-Guest fail-closed identity;
- complete Guest history;
- room/payment/service/conversation drill-down;
- 84-room management heatmap;
- historical period comparison;
- CSV/print and XLSX management export.

### Owner Control V2

- 7/30-day factual on-books control;
- daily occupancy/capacity/value/arrivals/departures;
- Action Center;
- analytics snapshots;
- snapshot-based booking pickup;
- fail-closed insufficient-history states;
- no fabricated demand forecast.

### Owner Growth Control

Admin surface: `Рост / Отзывы`.

- post-stay feedback queue;
- return-Guest/reactivation queue;
- manager follow-up;
- 0–10 feedback score;
- standard NPS classification;
- visible NPS sample size;
- detractor recovery workflow;
- duplicate protection;
- property isolation;
- AuditLog;
- `outbound_authority = NONE_AUTOMATIC`;
- candidate != marketing consent.

### Owner Executive Pack

Single owner summary in Command Center:

- MTD occupancy;
- MTD ADR;
- MTD RevPAR;
- MTD recorded payments;
- MTD CRM conversion;
- comparable prior-month-period delta;
- current debt/outstanding;
- next-30-day on-books occupancy/value;
- arrivals/departures;
- booking pickup only with historical snapshot;
- NPS + sample size;
- recovery;
- return-Guest candidates;
- CRITICAL/HIGH action facts;
- Growth overdue;
- browser print/PDF;
- explicit truth boundary for management vs accounting and on-books vs forecast.

## 3. Database release boundary

Verified migration chain:

`0_init -> 1_site_content -> 2_guest_service_tasks -> 3_owner_analytics_snapshots -> 4_guest_engagements`

Verified in CI:

- clean `prisma migrate deploy`;
- exact five-migration ledger;
- 84 rooms / 12 room types development seed;
- critical inventory/payment constraints;
- Guest Services constraints;
- Owner snapshot constraints;
- Growth constraints;
- migration-aware PostgreSQL backup -> clean restore.

## 4. Exact verification evidence

Audited executable head:

`1be110c35e1e7d5876cae40a1b58cef42bd10a22`

All **26/26** associated PR workflow contours completed `success`.

Primary release evidence:

- Resort Core CI `33245328528`;
- Full Staging Gate `33245328535`;
- Single Server Production Package CI `33245328529`;
- Production Migration Baseline `33245328548`;
- Backup Restore `33245328550`;
- Dependency Security `33245328532`;
- PMS Mutation `33245328512`;
- Realtime PMS `33245328538`;
- Guest Services `33245328498`;
- Hotel Operations `33245328499`;
- Owner Intelligence `33245328544`;
- Owner Control V2 `33245328508`;
- Owner Growth Control `33245328533`;
- Control Center Contract `33245328536`;
- Unified Inbox `33245328518`;
- Payment Idempotency `33245328520`;
- Public Site Truth `33245328516`;
- AI Administrator `33245328564`;
- AI Sales Draft `33245328545`;
- n8n Resort Core Contract `33245328514`;
- n8n Workflow JSON `33245328523`;
- Automation Contract `33245328527`;
- Data Intake Integrity `33245328525`;
- Staff Voice `33245328540`;
- Telegram Sales `33245328543`;
- NFC Deferred Scope `33245328521`.

## 5. Demo sequence for delivery day

Recommended 20–30 minute sequence:

1. **Public site — 3–4 min**
   - premium home;
   - rooms/media;
   - availability/booking boundary;
   - public truth.

2. **Command Center — 4 min**
   - current hotel operational facts;
   - Owner Executive Pack;
   - debt, MTD, next 30 days, NPS/recovery.

3. **PMS chessboard — 6–7 min**
   - filters/grouping;
   - reservation placement;
   - move/resize;
   - Split Stay;
   - room/reception lifecycle;
   - realtime/conflict concept.

4. **Guest Services / Staff — 3–4 min**
   - service task linked to Reservation;
   - housekeeping/inspection/rework;
   - technician flow.

5. **Owner Intelligence / Growth — 4–5 min**
   - Guest history;
   - heatmap/comparison;
   - post-stay feedback;
   - NPS sample size;
   - detractor recovery;
   - return-Guest queue.

6. **Architecture / safety — 2 min**
   - one source of truth;
   - manager confirmation boundary;
   - AI/n8n without direct DB/payment authority;
   - NFC deferred.

Do not spend delivery time demonstrating unfinished external provider integrations as if they were production verified.

## 6. Owner-approved public facts to check before demo

- booking admin: `+996 558 08 50 02`;
- manager / WhatsApp / Telegram: `+996 558 08 50 08`;
- email: `3koronykg@mail.ru`;
- parking: approximately **20–30 cars**, free for staying guests;
- sauna: winter only, 5000 KGS/hour, 4–5 people;
- billiards: 500 KGS/hour;
- table tennis: free;
- gym/training room: absent;
- sports grounds/fields: absent;
- New Year pricing: UNKNOWN until separately approved.

## 7. Hard external blockers — not software backlog

These items require real external access/evidence and remain open:

1. Beget host/account preflight.
2. Full rollback backup of current live `3korony.com`.
3. External HTTPS/WSS staging deployment.
4. External rendered public-truth acceptance.
5. Owner-confirmed physical 84-room register.
6. Real iPhone/Android/browser/Telegram acceptance.
7. Real launch-enabled provider E2E.
8. Fresh pre-cutover backup/preflight/secrets/DNS rollback evidence.
9. Explicit owner approval immediately before production DNS switch.

These blockers do not invalidate the CI-verified product delivery, but they prevent the words `LIVE`, `VERIFIED IN PRODUCTION` and `PRODUCTION READY`.

## 8. Delivery-day action plan — 2026-08-30

### Phase A — before presentation

- confirm presentation machine/browser;
- unpack the delivery bundle locally;
- verify the premium site demo opens;
- verify PMS owner-review HTML opens;
- have GitHub PR #37 and Current State available as evidence;
- use exact audited SHA `1be110...` in technical discussion;
- do not rely on stale old Vercel preview as proof of newest release.

### Phase B — presentation

Follow the demo sequence above. Separate clearly:

- `CI VERIFIED` — demonstrated release logic and isolated staging;
- `EXTERNAL NOT VERIFIED` — Beget, public HTTPS/WSS, devices/providers;
- `DEFERRED` — NFC;
- `UNKNOWN` — facts without owner evidence such as New Year prices.

### Phase C — immediately after acceptance

If owner provides infrastructure access:

1. run non-destructive host preflight;
2. take/verify full legacy rollback backup;
3. deploy isolated external staging;
4. apply all five migrations;
5. execute external acceptance matrix;
6. record issues and fix only verified defects;
7. take fresh pre-cutover backup;
8. obtain explicit DNS cutover approval;
9. switch in controlled window;
10. run post-cutover truth/PMS/staff smoke and monitor.

If owner does **not** provide infrastructure access, delivery remains a CI-verified release handoff and production deployment is a separately blocked operational phase.

## 9. Artifact truth

Historical local review ZIPs are useful for presentation but predate the latest Growth/Executive implementation and must not be described as the exact current source release.

The exact-head production-package workflow succeeded on run `33245328529`. Its transient GitHub Actions artifact is no longer available through the current connector session, so an older ZIP must not be relabeled as exact-head production source.

Canonical exact executable truth is the Git commit SHA plus CI evidence above.

## 10. Acceptance statement

For delivery language use:

> Three Crowns Resort OS release candidate is functionally integrated and verified through its full repository CI/staging regression suite on exact executable head `1be110c35e1e7d5876cae40a1b58cef42bd10a22` (26/26 successful workflow contours). External production deployment remains a controlled next phase requiring real host, rollback, HTTPS/WSS, device/provider and cutover evidence.

Do not shorten this to “production is ready” until external gates are complete.
