# Asset status

Public-site media status on this branch:

- `hero-resort.webp` — valid RIFF/WEBP and retained as the verified **generic resort fallback** for categories that still do not have exact public room media;
- `approved/territory/beach-mountains.webp` — valid owner-media-pack derivative, Media Registry `GENERAL_RESORT_TERRITORY`, `PUBLIC_USE=YES`, used only as a general resort/beach visual;
- `approved/territory/pier-front.webp` — valid owner-media-pack derivative, Media Registry `GENERAL_RESORT_TERRITORY` / beach-pier context, `PUBLIC_USE=YES`, used only as a general pier/lake visual;
- `approved/territory/pool.webp` — valid owner-media-pack derivative, Media Registry `GENERAL_RESORT_TERRITORY`, `PUBLIC_USE=YES`, used only as a general territory/pool visual;
- `media/rooms/cottage-double-standard/hero.webp` — processed derivative from the confirmed `COTTAGE_DOUBLE_STANDARD` set; `PUBLIC_USE=YES` from 2026-09-02 and restricted to category `cottage-double-standard`;
- `media/rooms/two-room-standard/hero.webp` — processed derivative from the confirmed `TWO_ROOM_STANDARD` set; `PUBLIC_USE=YES` from 2026-09-02 and restricted to category `two-room-standard`; it must not be used for `two-room-junior-suite`;
- `media/rooms/apartments-with-kitchen/hero.webp` — processed derivative from the confirmed `APARTMENT_KITCHEN` set; `PUBLIC_USE=YES` from 2026-09-02 and restricted to category `apartments-with-kitchen`;
- `room-double.webp` and `lake-night.webp` — repository placeholders are not valid WEBP binaries and remain intentionally **unreferenced** by public pages;
- `hero-resort.mp4`, `territory.mp4`, `lake.mp4` — old repository copies remain incomplete placeholders and are intentionally **not requested** by the public runtime.

The owner-approved media register identifies `three-crowns-media-pack-20260828.zip` as the READY source pack. General territory derivatives were materialized because their registry scope is `PUBLIC_USE=YES`. The three exact room sets were separately approved for public category binding by the user on 2026-09-02; that approval was recorded in the Media Registry before the exact room hero derivatives were exposed publicly.

The approved room sets contain 23 source WEBP images in total: 9 cottage double standard, 6 two-room standard and 8 apartment-with-kitchen. Source files remain untouched. Web derivatives use conservative normalization only (RGB normalization, light contrast/color/sharpness adjustment and metadata-stripping re-encode) and must not add/remove objects or fabricate room features. The initial public materialization uses the selected hero frame from each set; the remaining curated gallery frames can be added without changing the category mapping contract.

All other room categories remain without exact public room imagery. Their cards/details must not borrow another category's photos. They use an explicit pending-photo state or the verified generic resort fallback with a clear generic-media label.

The public-site visual polish is loaded through `app/public-site-polish-20260902.css` and `app/room-media-polish.css`. `scripts/public_media_integrity_guard.py` verifies approved general and exact-room WEBP signatures, enforces the three exact room slugs, keeps pending suite markers and known corrupt placeholders forbidden, and fails closed if general resort imagery is rebound as exact room-category media.

Media presence is evidence of an asset, not by itself authority to promote an amenity, service, operational capability, capacity, commercial promise, or booking offer into CURRENT state. `knowledge/04_CURRENT_STATE.md` remains the canonical owner of factual implementation/public-truth status.

Billiards is owner-approved public information and is sourced from `ownerApprovedGuestFacts.ts`. Laundry, conference facilities and other not-yet-canonicalized claims must remain unpublished as CURRENT facts unless they pass the project evidence/canonical update path.
