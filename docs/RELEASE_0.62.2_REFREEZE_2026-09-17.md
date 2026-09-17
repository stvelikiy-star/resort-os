# Resort OS 0.62.2 — controlled refreeze — 2026-09-17

Status: **INTERNAL RC REFROZEN / EXTERNAL PRODUCTION CUTOVER STOP**

This is a same-version release-truth refreeze after the fully verified no-payment operational integration in PR #172. It does not authorize production DNS cutover or external provider activation.

## Accepted boundary

- Release: `0.62.2`
- Production source branch: `main`
- Accepted executable main boundary: `7b14e32dbf64ffd617a5c7720f98add24efd1341`
- Exact tested PR #172 head: `5c606e5447958595f52c9d7dbacdb177e010cb4c`
- PR #172 workflows: **48/48 SUCCESS, 0 failures**
- Launch profile: `FULL_NO_PAYMENTS`

The accepted main boundary also contains the separately verified Admin session-expiry/realtime-loop correction from PR #171.

## Operational scope

Enabled in the accepted operational contour:
- Public site and booking request flow;
- PMS / chessboard / Reception / CRM / Agents;
- returning-guest discount and extra-bed rules;
- confirmed booking movement and room holds;
- Staff / housekeeping / maintenance;
- Guest OS;
- Kitchen / Dining;
- n8n / AI / realtime contracts.

Disabled in the launch profile:
- payment mutation routes;
- bank acquiring and provider payment activation;
- MKassa payment activation;
- NFC wallet/acquiring.

Historical payment implementations remain regression-tested only in isolated CI where explicitly enabled. They are not part of the active production launch surface.

## Database and hotel truth

Frozen release contract remains:
- **24 migrations**;
- **93 critical constraints**;
- **84 rooms**;
- **12 categories**;
- 48 rate rows.

No migration is introduced by this refreeze.

## Post-merge evidence

The first `main` push for `7b14e32dbf64ffd617a5c7720f98add24efd1341` triggered 39 workflows. 37 completed successfully. `Release RC Truth CI` failed closed because the prior frozen manifest still pointed at the older release boundary. One additional workflow completed with a non-success/non-failure conclusion. No new functional regression was identified in the post-merge suite.

This refreeze updates release governance so future executable/product drift after the accepted main boundary fails closed again.

## External gates still open

**EXTERNAL PRODUCTION CUTOVER STOP** remains in force until the real target is proven:
- GitHub branch protection / required checks;
- authorized Beget/VPS execution path;
- actual-target backup, restore and off-site copy;
- legacy rollback evidence;
- production HTTPS/WSS and DNS rollback;
- real device/provider acceptance;
- final owner GO.

No payment, QR acquiring, MKassa acquiring, NFC wallet or production DNS cutover is authorized by this refreeze.
