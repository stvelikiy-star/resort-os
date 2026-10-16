# MARINA SMART — external reservations, first operational slice

Location: Admin → More → Sales channels (OWNER/MANAGER).

This version supports manager-confirmed manual entry, amendment and cancellation
of Booking.com, Airbnb and Ostrovok reservations. It does not connect to those
providers, poll calendars, receive authenticated provider webhooks, or send
prices/availability/cancellations back. The screen explicitly states this.

`GET /api/v1/admin/channels` returns the current property's external identities,
rooms and disconnected provider capabilities. `POST .../reservations/import`
accepts provider, external_id, monotonic revision, status, room UUID, guest, dates,
occupancy and the explicitly entered accommodation total in KGS. Other currencies
are rejected; no exchange rate or payment is invented.

The existing automation_inbound_events table is the property-scoped identity
ledger, using eventType CHANNEL_RESERVATION and source OTA_MANUAL_<provider>.
The idempotency key hashes the external booking number, scoped by property and
provider. A transaction advisory lock serializes delivery of the same identity.
Matching replays return the same reservation; old revisions and changed payloads
with the same revision fail closed. Cancellation tombstones prevent an older
create from reopening dates. Audit logs retain accepted changes.

Accepted confirmed records create/update canonical reservations,
reservation_requests, guests and inventory_blocks. They therefore appear in the
existing grid/reception/finance flow. Room rows are locked in UUID order, current
inventory conflicts and TECH_BLOCK/capacity are checked, and PostgreSQL exclusion
constraints remain the final concurrent-booking guard. In-progress stays and
cancelled reservations require manual review. Existing payments are untouched;
cancellation releases dates but never invents a refund.

The grid and realtime snapshots include the request's channel source. The compact
grid retains its structure and shows the platform alongside the guest. Channel
identities and actions are restricted to the current trusted property and manager
roles. Agents and reception cannot access channel administration.

Acceptance is wired into the disposable two-property restore workflow, before
and after restore: duplicate/concurrent intake, amendments, cancellation,
tombstones, stale/mismatched revisions, foreign rooms/properties, role denials,
conflicts, TECH_BLOCK, capacity and absence of automatic payments.

Remaining: approved provider/partner credentials, authenticated adapters,
room-category/rate mapping, durable outbound availability/rates queue,
provider-specific retry/reconciliation and real-property pilot acceptance.
