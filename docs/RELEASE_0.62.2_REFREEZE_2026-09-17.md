# Resort OS 0.62.2 — controlled refreeze — 2026-09-17

Status: **INTERNAL RC REFROZEN / EXTERNAL PRODUCTION CUTOVER STOP**

This is a same-version release-truth refreeze after the verified hotel business-date hardening in PR #176. It does not authorize production DNS cutover or external provider activation.

## Accepted boundary

- Release: `0.62.2`
- Production source branch: `main`
- Accepted executable main boundary: `a53850983d8fc6e1f1997199049a5b071511ed80`
- Exact tested PR #176 head: `a3ff4c847c66cd64a7cca92ccec613f23917f62d`
- PR #176 workflows: **29/29 SUCCESS, 0 failures**
- Launch profile: `FULL_NO_PAYMENTS`

The accepted main boundary retains the verified no-payment operational profile from PR #172, the Admin session-expiry correction from PR #171 and the canonical GitHub merge-format guard correction from PR #175.

## Operational scope

Enabled in the accepted operational contour:
- Public site and booking request flow;
- PMS / chessboard / Reception / CRM / Agents;
- returning-guest discount and extra-bed rules;
- confirmed booking movement and room holds;
- Staff / housekeeping / maintenance;
- Guest OS;
- Kitchen / Dining;
- n8n / AI / realtime contracts;
- Admin/Staff hotel business dates normalized to `Asia/Bishkek` where date-only defaults are operationally mutable.

Public Web remains release-frozen by the current Management Final Acceptance boundary; PR #176 intentionally did not rewrite its date helper surface.

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

The first `main` push for `a53850983d8fc6e1f1997199049a5b071511ed80` triggered 26 workflows. 25 completed successfully. The only failure was `Release RC Truth CI`, which failed closed because the frozen manifest still pointed at the prior executable boundary. `Resort OS Release Gate` completed successfully, including migrations, Admin/Public/Staff builds, Site/PMS/CMS smoke, owner-approved automation truth, full-domain E2E, Dining folio, Chef production, Dining coordination and root control-center verification.

No functional regression was identified in the post-merge suite. This refreeze updates release governance so future executable/product drift after the accepted main boundary fails closed again.

## External gates still open

**EXTERNAL PRODUCTION CUTOVER STOP** remains in force until the real target is proven:
- GitHub branch protection / required checks;
- Google Drive permission integrity;
- authorized Beget/VPS execution path;
- actual-target backup, restore and off-site copy;
- legacy rollback evidence;
- immutable accepted-SHA to image/runtime linkage;
- production HTTPS/WSS and DNS rollback;
- real iPhone / Android / desktop / Staff-Kitchen acceptance;
- monitoring and alert delivery;
- final owner GO.

No payment acquiring, MKassa acquiring, NFC wallet, physical lock actuation or production DNS cutover is authorized by this refreeze.
