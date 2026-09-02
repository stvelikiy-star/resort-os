# Asset status

Public-site media status on this branch:

- `hero-resort.webp` — valid RIFF/WEBP and retained as the verified **generic resort fallback**, including room catalogue/detail surfaces while exact category public binding is pending;
- `approved/territory/beach-mountains.webp` — valid owner-media-pack derivative, Media Registry `GENERAL_RESORT_TERRITORY`, `PUBLIC_USE=YES`, used only as a general resort/beach visual;
- `approved/territory/pier-front.webp` — valid owner-media-pack derivative, Media Registry `GENERAL_RESORT_TERRITORY` / beach-pier context, `PUBLIC_USE=YES`, used only as a general pier/lake visual;
- `approved/territory/pool.webp` — valid owner-media-pack derivative, Media Registry `GENERAL_RESORT_TERRITORY`, `PUBLIC_USE=YES`, used only as a general territory/pool visual;
- `room-double.webp` and `lake-night.webp` — repository placeholders are not valid WEBP binaries and remain intentionally **unreferenced** by public pages;
- `hero-resort.mp4`, `territory.mp4`, `lake.mp4` — old repository copies remain incomplete placeholders and are intentionally **not requested** by the public runtime.

The owner-approved media register identifies `three-crowns-media-pack-20260828.zip` as the READY source pack. The new `approved/territory/*` derivatives were materialized from that pack specifically because the Media Registry marks the general territory set as `PUBLIC_USE=YES`. They are not evidence of a price, service availability or room-category mapping.

The three approved exact room sets (cottage double standard, corpus-1 two-room standard, apartment with kitchen) remain `AI_USE=YES` but **`PUBLIC_USE=NO`** in the Media Registry. They therefore remain unavailable to public room-category cards/details until separate owner/category public-binding evidence exists. The room catalogue/detail surfaces continue to use the verified generic resort fallback rather than presenting a false exact-room attribution.

The public-site visual polish is loaded through `app/public-site-polish-20260902.css`; `scripts/public_media_integrity_guard.py` verifies the three approved general WEBP signatures and paths, keeps the known corrupt placeholders forbidden, and fails closed if general resort imagery is reused as exact room-category media.

Media presence is evidence of an asset, not by itself authority to promote an amenity, service, operational capability, capacity, commercial promise, or booking offer into CURRENT state. `knowledge/04_CURRENT_STATE.md` remains the canonical owner of factual implementation/public-truth status.

Billiards is owner-approved public information and is sourced from `ownerApprovedGuestFacts.ts`. Laundry, conference facilities and other not-yet-canonicalized claims must remain unpublished as CURRENT facts unless they pass the project evidence/canonical update path.
