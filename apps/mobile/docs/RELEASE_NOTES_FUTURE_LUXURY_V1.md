# MARINA SMART Mobile · Future Luxury V1

## Changes in draft PR #292
- Future Luxury system themes (light #F5FAFF, dark #061225) with semantic colors, new typography/elevation/spacing, champagne as accent, cyan and iris as sparing technology notes.
- Selected Light/Dark/System preference survives relaunch through existing SecureStore (native) and safe non-secret localStorage (web).
- Shared premium headers, layered SVG hotel hero, glass-like cards, action tiles, authenticated metrics ring, full-screen operational states and foreground/reduced-motion-aware animations.
- Branded connection/login preserved existing compass/ship artwork; no M-monogram substitution.
- Role-aware bottom tabs and task tiles; owner dashboard, mobile PMS with frozen room labels, Inbox cards/search, Reception, Dining, Rooms and Profile refreshed.
- Read-only MARINA AI modal uses platform `/api/v1/assistant/capabilities` and `/api/v1/assistant/chat`. Supports RU/KG/EN/KZ interface copy, uses real server response context and expressly avoids unsupported voice operations.
- No backend/PMS/schema/migration/Ubuntu/demo changes and no production deployment.

## Important limitations
- Original logo asset needs external design sign-off; raster preserved without modifications.
- Android signature/API on physical devices and iOS sign-off remain blocked by acceptance tests.
- WhatsApp outbound, device tokens, guest integration, native notifications, offline mutations and full PMS module parity remain outside this design-only PR.
- Demo role/login examples remain isolated and labelled, not proof of real hotel readiness.

## Rollback / isolation
This branch is a child of `feat/marina-mobile-live-workspaces-20261103` at `7ecff8e...`. Revert the design commits or close draft PR #292 without merging to restore the parent functionality. No database rollback required because this PR does not alter database/backend files.
