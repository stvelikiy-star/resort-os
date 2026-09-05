# Guest Concierge V2 acceptance boundary

This phase deliberately reuses the existing Guest OS session and OperationalTask request routes. It does not add a second booking/payment truth or promise services automatically.

Implemented in this phase:

- one room-QR guest route backed by the existing permanent room token and PIN session;
- compact RU / KG / EN selector with explicit per-locale copy;
- guest/stay hero after authentication;
- fast service actions;
- `MEALS`, `HOUSEKEEPING`, `TRANSFER`, `MAINTENANCE`, `SAUNA`, `EXCURSIONS`, `TOWELS`, `LINEN`, `BILLIARDS`, `ADMIN` requests through the existing Core request endpoint;
- request history/status polling and guest cancellation while a request is still OPEN;
- structured meal request with owner-approved additional-meal prices and explicit warning that inclusion is determined by the reservation;
- structured transfer request that remains subject to staff confirmation;
- check-in/check-out rules and hotel contact actions;
- mobile-first layout.

Not claimed by this phase:

- no factual daily dish catalog exists yet, therefore no invented dish menu is shown;
- no automatic service confirmation/payment is introduced;
- kitchen check-in notifications are the next Core/Staff phase;
- reviews and structured catalog administration remain subsequent phases;
- external Beget/production acceptance remains separate.
