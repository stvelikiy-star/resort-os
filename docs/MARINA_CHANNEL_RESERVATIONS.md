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

## Normalized CSV batches

The sales channels screen offers a CSV header template, a paste field, and the
current property's room code/UUID reference. Raw provider exports must first be
converted to this normalized format; this is not automatic provider connectivity.

`POST /api/v1/admin/channels/reservations/csv` accepts `csv_text` (at most 200,000
characters) and `preview` (default true). At most 100 records; UTF-8 BOM and quoted
CSV values are supported. Headers are the single-reservation field names; unknown,
duplicate or missing identity headers and repeated identities are rejected.
Confirmed rows require the same facts as single entry. Cancellation tombstones
remain supported. Empty optional cells use the existing model defaults.

Preview executes the canonical import in a transaction and rolls it back, including
guests, inventory, identity records and audit logs. It does not reserve inventory
or promise that a later import will succeed. Import rechecks all rules and commits
all rows atomically; any row failure rolls the entire batch back. The response
identifies the CSV record (header is record 1); multiline quoted records count as
one record. Lock contention returns CHANNEL_BATCH_RETRY; retry the whole batch.
Accepted replays reuse the existing external identities, never duplicate bookings.
The screen invalidates its successful preview whenever the CSV text changes.

Disposable two-property CI verifies no-write preview, conflicting/foreign-room
batch rollback, successful commit, replay, role restrictions and restore coverage.

## Draft category/rate mappings

`GET/PUT /api/v1/admin/channels/mappings` (OWNER/MANAGER) configures the tuple
(provider, external property ID, external category ID, external rate ID) against
one local room type and rate plan. IDs are entered explicitly, never guessed.
Only KGS is supported. Saving, editing or deactivating does not connect a provider,
send updates, change bookings or assign a physical room.

A dedicated `channel_mappings` table has a property-scoped unique identity and
composite foreign keys preventing foreign-property targets even below HTTP.
Expected revision 0 creates; updates require the latest revision. Same-key
writers serialize and stale writes return CHANNEL_MAPPING_STALE. Accepted saves
record an audit event in the same transaction. Inactive mappings retain identity
and revision history; no destructive delete endpoint is exposed.

Migration zz108 is additive and preserves existing inventory and bookings. The
release ledger is explicitly extended to 32 migrations, with six new domain
checks in the critical-constraint fingerprint. Disposable acceptance covers
concurrent create, edit/deactivate, stale writes, property/role/currency rejection,
composite FK enforcement and backup restoration. Browser acceptance saves a
synthetic mapping and asserts the disconnected status remains explicit.
