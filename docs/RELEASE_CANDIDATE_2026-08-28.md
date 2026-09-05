# Three Crowns Resort OS — Release Candidate Gate

Date: 2026-08-28

## Candidate

The current integration candidate preserves the core invariant:

`PUBLIC SITE / PMS / STAFF / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

Google Sheets, CMS, n8n and AI are not parallel booking, inventory, pricing, payment or reservation-confirmation sources of truth.

Current audited AI-administrator integration head:
`731cf9114d860d9625901f5ba5cfd48cdc756540`.

The dedicated AI Administrator contract is green on this head. The previous complete AI-integration head `0f4231c8b038ce6ce60c7aea172bff497d79b24a` also passed all associated repository workflows, including Resort Core, Full Staging Gate, Single Server Production Package, Public Site Truth, n8n contracts, migrations, backup/restore and dependency security.

## AI Administrator V1 — VERIFIED IN CI / NOT LIVE WITH REAL PROVIDERS

### Website

The public site includes a globally mounted responsive AI Administrator popup.

Runtime boundary:
`3korony.com -> Resort Core public AI endpoint -> verified hotel facts / Core availability -> OpenAI response composition`.

Implemented:
- free-form guest Q&A;
- explicit check-in/check-out/adults/children checker;
- Core-backed sellable room categories and integer KGS totals;
- server-side verified context construction;
- public request rate limiting;
- no n8n dependency for website chat;
- no payment/reservation confirmation authority;
- after sellable availability is returned, a booking handoff sends the guest to the existing `#booking` flow, which creates `ReservationRequest` rather than an automatic reservation.

Core endpoints:
- `GET /api/v1/public/ai-admin/capabilities`;
- `POST /api/v1/public/ai-admin/chat`.

### WhatsApp / GREEN API / n8n

Importable workflow:
`automation/n8n/whatsapp-green-ai-admin.json`.

Runtime boundary:
`GREEN API -> n8n -> Resort Core -> OpenAI -> GREEN API`.

Implemented flow:
1. receive GREEN API `incomingMessageReceived`;
2. require webhook query secret;
3. load verified hotel facts from Core;
4. use AI only to extract guest intent/date/count fields;
5. call Core availability when exact dates + adults are present;
6. compose reply from verified hotel facts/current availability only;
7. on explicit booking intent with sufficient facts and sellable availability, create only `ReservationRequest` through Core;
8. use GREEN `idMessage` in idempotency key `whatsapp-green:<idMessage>` to prevent duplicate request creation;
9. send the guest reply through GREEN API `sendMessage`.

The workflow is intentionally committed as `active:false`. It is IMPLEMENTED but is not represented as LIVE until real GREEN API/OpenAI credentials and an external HTTPS n8n endpoint are connected and tested.

Dedicated workflow: `Three Crowns AI Administrator CI`.
Latest successful run after the booking-handoff UX addition: `33160438772`.

Verified by that run:
- deterministic public web dependency tree;
- public site typecheck/build with AI widget;
- public AI Core module compilation;
- WhatsApp n8n JSON and authority boundary;
- website remains Core-direct rather than routing through n8n;
- production environment/Compose wiring.

Previous complete related integration run-set on head `0f4231c8b038ce6ce60c7aea172bff497d79b24a` is also successful:
- Full Staging Gate `33160040308`;
- Resort Core CI `33160040237`;
- Public Site Truth CI `33160040288`;
- n8n Workflow JSON CI `33160040226`;
- n8n Resort Core Contract CI `33160040259`;
- Single Server Production Package CI `33160040278`;
- Dependency Security Inspection `33160040309`;
- Production Migration Baseline CI `33160040269`;
- PostgreSQL Backup Restore CI `33160040192`.

## Reservation / payment authority

Canonical boundary remains:
`ReservationRequest -> manager/human confirmation -> Reservation`.

AI/n8n cannot:
- guarantee a Reservation;
- confirm payment;
- invent a prepayment percentage, QR or payment link;
- bypass Core availability/pricing;
- directly write PostgreSQL.

Manager chooses payment amount, terms and method for current Three Crowns V1.

## Verified production-like migration chain

Current committed migration chain:
- `0_init`;
- `1_site_content`.

Verified:
- clean `prisma migrate deploy`;
- exact migration ledger `0_init,1_site_content`;
- `site_content_documents` present after migration;
- 84/12 development seed;
- 13 critical database constraints;
- backup/restore with the complete migration ledger.

## Verified single-server production package

The approved production simplification remains a single VPS/VDS package:
- Caddy HTTPS/WSS edge;
- web/admin/staff Next.js;
- FastAPI Core;
- private PostgreSQL;
- pinned n8n `2.36.2`;
- persistent media/PostgreSQL/n8n state;
- local backup path with off-site copy expected.

Status: **SINGLE-SERVER PRODUCTION PACKAGE VERIFIED IN CI / NOT EXTERNALLY DEPLOYED**.

## Dependency security / reproducibility

Current locked frontend runtime:
- Next `15.5.24`;
- React `19.2.8`;
- React DOM `19.2.8`;
- PostCSS override `8.5.23`.

Committed lockfiles exist for web/admin/staff and Docker builds use `npm ci`.

## External/provider truth

The following are **NOT VERIFIED / NOT LIVE**:
- real GREEN API hotel WhatsApp instance;
- real `idInstance` / `apiTokenInstance` delivery;
- real production OpenAI credential/model configuration;
- website AI over external `3korony.com` HTTPS;
- n8n GREEN webhook over external HTTPS;
- live hotel-number WhatsApp end-to-end acceptance.

No provider secret is committed to GitHub.

## Purchased hosting / legacy site truth

The production package is ready to be evaluated on the existing Three Crowns hosting, but the host itself is not yet proven suitable.

`scripts/host_preflight.sh` is a non-destructive host capability probe. The currently live legacy `3korony.com` must remain serving until its backup/rollback point exists and the new system passes external acceptance.

## Still blocking production cutover / live AI activation

1. Purchased hosting must pass `scripts/host_preflight.sh` or be upgraded to a suitable VPS/VDS.
2. Current live `3korony.com` must have a verified backup/rollback point before replacement.
3. Owner-confirmed physical 84-room register; unresolved `OWNER_CHECKLIST` facts must not be guessed.
4. Complete external HTTPS/WSS staging acceptance on the actual host.
5. Real OpenAI production key + selected model configuration stored as deployment secret.
6. Real GREEN API `idInstance` + `apiTokenInstance` stored as deployment secrets.
7. End-to-end WhatsApp acceptance on the actual hotel number, including date search, unavailable dates, booking-intent idempotency and prompt-injection attempts.
8. External browser/mobile acceptance of the website AI Administrator.
9. Fresh production backup -> clean restore proof and final `production_preflight.py` immediately before cutover.
10. Production secrets / controlled DNS-apex cutover / documented rollback point.

No production merge, provider activation or DNS switch is authorized by this document alone.
