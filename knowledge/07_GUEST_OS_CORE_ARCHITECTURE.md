# THREE CROWNS GUEST OS — CORE ARCHITECTURE

Status: CANONICAL DESIGN FOR IMPLEMENTATION
Date: 2026-08-31
Scope: Three Crowns Resort OS, Cholpon-Ata

## 1. Purpose

Guest OS is the in-stay digital concierge layer of Resort OS. It is not a parallel booking, CRM, payment, inventory, pricing, or staff system.

Canonical flow:

`ROOM QR -> ROOM -> ACTIVE ROOM ASSIGNMENT -> STAY -> RESERVATION -> GUEST -> GUEST SESSION -> GUEST OS`

All mutations flow back through Resort Core:

`GUEST OS -> FASTAPI RESORT CORE -> POSTGRESQL -> PMS / STAFF / ANALYTICS`

Resort Core remains the sole operational source of truth.

## 2. Permanent room QR invariant

Each physical room has one active opaque QR credential at a time.

The QR belongs to the room, not to a guest and not to a reservation. A room QR may remain physically installed across many stays.

The public QR URL MUST NOT contain raw room IDs, reservation IDs, guest IDs, phone numbers, booking numbers, or other private/internal identifiers.

Recommended public form:

`https://3korony.com/g/<opaque-token>`

Only a hash of the opaque token is stored server-side. Tokens can be rotated/revoked by OWNER or MANAGER.

## 3. Guest resolution invariant

Scanning a room QR does not by itself authorize access to personal guest data.

Core resolves the QR to a room, then checks for an active RoomAssignment belonging to an active Stay. The Stay is linked to a Reservation and its Guest identity.

No active Stay / RoomAssignment -> no personalized Guest OS.

## 4. First-device verification

On the first authorized device, the guest completes a lightweight stay verification step.

V1 method: short one-time/stay PIN generated at CHECK-IN and shown to Reception. The database stores only a hash of the PIN.

After successful verification Core creates a GuestSession containing only server-authorized references and a hashed session token.

Subsequent opens on the same device use the GuestSession without requiring the PIN again until expiration/revocation.

CHECK_OUT revokes all active GuestSessions for the Stay.

## 5. Stay and room assignment model

Reservation represents the commercial booking.

Stay represents the actual hotel stay lifecycle.

RoomAssignment represents where the guest physically stayed during a time interval.

A Stay can therefore contain multiple RoomAssignments, enabling room moves and Split Stay without rewriting history.

Example:

- 31 Aug–2 Sep: Room 214
- 2 Sep–5 Sep: Room 305

The same Guest and Stay remain intact; only RoomAssignment changes.

## 6. Guest history invariant

Guest identity is persistent across reservations and stays when safely matched by authorized identity data.

History is never replaced by the current reservation. It is accumulated from:

- Reservations
- Stays
- RoomAssignments
- OperationalTasks / Guest Services
- GuestEngagements / feedback
- Payments where authorized for staff views
- GuestHistoryEvents
- GuestPreferences

A repeat visit must resolve to the existing Guest where identity matching is sufficiently reliable; ambiguous matches must fail closed and require staff review.

## 7. Guest services

Guest OS V1 creates structured requests through Resort Core. It must not fall back to an untracked messaging-only workflow for operational requests.

Initial service groups:

- HOUSEKEEPING
- TOWELS
- LINEN
- MAINTENANCE
- RECEPTION
- TRANSFER
- MEALS
- SAUNA
- BILLIARDS
- EXCURSIONS

Existing owner-approved service facts/prices remain sourced from the canonical content/service data already used by the public site. Guest OS must not duplicate or invent prices.

Guest service requests are operational. Creating a request MUST NOT automatically mutate accommodation totals, create a Payment, confirm a payment, or invent payment terms.

## 8. Request lifecycle

V1 guest-visible lifecycle:

`OPEN -> IN_PROGRESS -> DONE`

Internal lifecycle may also include `IN_INSPECTION` and `CANCELLED` where applicable.

Every request stores enough context to preserve history:

- property
- guest
- reservation
- stay
- room at request time
- service code/type
- priority
- description
- timestamps
- assignee where applicable
- source = GUEST_OS

Routing:

- HOUSEKEEPING / TOWELS / LINEN -> MAID queue
- MAINTENANCE -> TECHNICIAN queue
- TRANSFER / MEALS / SAUNA / BILLIARDS / EXCURSIONS / RECEPTION -> Reception/Manager service queue

Severe maintenance can trigger the existing TECH_BLOCK workflow only through authorized Core logic.

## 9. Guest OS mobile interface

Target route:

`/guest/[token]` or equivalent opaque-token route.

Mobile-first home screen:

- personalized welcome after authorization
- current room
- stay dates
- housekeeping
- towels
- linen
- maintenance problem
- contact administrator
- meals
- transfer
- excursions
- sauna
- billiards
- beach / seasonal activities information
- hotel rules
- hotel information
- My Requests
- review CTA

Private data exposure must be minimal. Full phone/email/payment/internal notes are not displayed in the guest surface unless explicitly needed and approved.

## 10. My Requests

GuestSession can read only requests belonging to its authorized Stay/Guest context.

Guest sees status and basic timing, for example:

- Towels — Done
- Housekeeping — In progress
- Transfer — Open

No guest session may enumerate another room, reservation, guest, or stay by changing URL/query parameters.

## 11. Service Point QR is a separate mode

ROOM QR and SERVICE POINT QR are distinct concepts.

ROOM QR:
- personalized
- requires active Stay and verification
- tied to physical room

SERVICE POINT QR:
- tied to a location such as pool, beach, toilet, corridor, dining area, sauna
- may be anonymous/public
- identifies the service location, not a Guest
- must never expose private guest data

Baseline flow:

`SERVICE POINT QR -> LOCATION -> ISSUE/REQUEST -> CORE TASK -> RESPONSIBLE STAFF -> STATUS -> MANAGEMENT VISIBILITY`

## 12. Required Core schema additions

The current schema already contains Guest, Reservation, Room, InventoryBlock, OperationalTask, GuestEngagement, Payment, AuditLog and staff authentication.

Before Guest OS UI is considered implemented, Core must add explicit persistence for:

- Stay
- RoomAssignment
- RoomQr
- GuestSession
- GuestHistoryEvent
- GuestPreference

OperationalTask should gain optional `stayId` so an operational request remains attached to the exact stay even after room moves or later reservations.

The changes should be additive first. Existing reservation/PMS flows must remain backward compatible while the new Stay lifecycle is wired in.

## 13. RBAC baseline

Operational baseline roles for the whole Resort OS:

- OWNER
- MANAGER
- RECEPTION
- MAID
- TECHNICIAN
- STORE_STAFF
- DINING_STAFF
- optional CONTENT_MANAGER
- GUEST is session-based and not a staff role

Legacy/deferred NFC/beach-partner schema must not be interpreted as active V1 payment authority.

## 14. Security rules

1. Never put PII/internal IDs in QR URLs.
2. Store QR/session/PIN secrets as hashes, not plaintext.
3. Validate active Stay and active RoomAssignment server-side on every privileged Guest OS action.
4. Revoke sessions at CHECK_OUT and on manual security action.
5. Rate-limit PIN verification and guest request creation.
6. Audit QR rotation, guest verification, session revoke, room move, request creation/status changes.
7. Do not trust room numbers, guest IDs, reservation IDs or service prices supplied by the client.
8. All write authority remains in FastAPI Resort Core.

## 15. Implementation order

1. Additive Prisma models + migration.
2. Stay lifecycle service: create/activate at check-in, close at checkout.
3. RoomAssignment service integrated with PMS move/Split Stay.
4. Room QR issuance/rotation admin API.
5. Guest PIN verification + GuestSession lifecycle.
6. Guest OS read bootstrap endpoint.
7. Guest request create/list endpoints.
8. Mobile `/guest/[token]` UI.
9. PMS Guest Services Center and routing.
10. Staff queue integration.
11. Guest history/CRM aggregation.
12. Service Point QR.
13. Owner analytics/SLA metrics.
14. Full E2E acceptance.

## 16. Acceptance scenario

The architecture is accepted when this complete scenario works against Resort Core and PostgreSQL:

1. Staff creates/confirms a reservation.
2. Reception checks Guest into Room 214.
3. Core creates/activates Stay and RoomAssignment and issues guest verification PIN.
4. Guest scans the permanent QR installed in Room 214.
5. Guest verifies once and receives a GuestSession.
6. Guest sees their authorized stay context.
7. Guest requests towels.
8. Request appears in PMS/MAID queue.
9. Staff sets it IN_PROGRESS and then DONE.
10. Guest sees DONE in My Requests.
11. Reception moves the Stay from Room 214 to Room 305.
12. Old Room 214 no longer authorizes the Stay; Room 305 does.
13. Reception checks the Stay out.
14. GuestSession is revoked.
15. Guest history still contains both room assignments and the service request.
16. A new Guest checked into Room 214 can use the same physical Room 214 QR after their own verification.

## 17. Non-goals for this block

- No automatic payment confirmation.
- No fixed prepayment percentage invented by Guest OS.
- No active NFC wallet/acquiring rollout.
- No parallel CRM/database.
- No redesign of the existing PMS chessboard.

This document is the implementation contract for Guest OS Core and its integration with PMS, CRM, Staff and Owner Intelligence.