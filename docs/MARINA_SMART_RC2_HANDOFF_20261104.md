# MARINA SMART — RC2 unified staging handoff (2026-11-04)

**Scope: shared MARINA SMART platform only. No MARINA_DEMO, MARINA_HOTEL01, mobile APK, KÖL, other hotels, deployment or target database changes.**

## Identity and ancestry

- Repository: `stvelikiy-star/resort-os`
- RC2 branch: `release/marina-shared-platform-rc2-20261104`
- Reviewed application source before this handoff: `62a2caec856e8fe32801c9156d90de655298ad33` (existing draft PR #312).
- Historical RC1 source branch/head: `release/marina-shared-platform-rc1-20261103` / `488fec8b9823c6f98d690333dcc7c9b28fa86bc8` (draft PR #284).
- GitHub ancestry check: RC2 source is **92 commits ahead, zero behind** RC1 head; changes are confined to 29 files relative to RC1. These commits include prior stacked draft PRs; **do not merge the stack individually into production**.
- `main` diverged independently from RC2; **no direct merge or force-push to `main`** until a separately reviewed reconciliation plan is tested.

## Verified evidence before RC2 metadata changes

- `MARINA Shared Live Browser PostgreSQL CI`: PASS on application source SHA above: https://github.com/stvelikiy-star/resort-os/actions/runs/41711228040
- Browser -> real Next Admin -> real API -> disposable PostgreSQL 16: two independent hotel accounts; booking creation/price/inventory, HOLD create/release, date change, unpaid cancellation, internal manual payment record, check-in, one-time PIN, check-out, PIN/session revocation and housekeeping, cross-hotel access denied on checked operations.
- `Resort OS Release Gate`: PASS for the source SHA: https://github.com/stvelikiy-star/resort-os/actions/runs/41711228001
- 20/21 PR workflows reported SUCCESS on that source SHA. The non-MARINA **Three Crowns Full Staging Gate** failed due to public content truth differences outside the 29-file RC1->RC2 delta. This is not a release-wide PASS.
- These are isolated CI checks, **not external staging, third-hotel onboarding, all staff cabinets/guest QR, real GREEN-API deliveries, per-property AI knowledge or target backup/restore**.

## Mandatory release acceptance

1. Pin the reviewed source SHA and exactly 39 committed migration SQL SHA-256 values in `release/marina-smart-current-candidate.json`.
2. Verify all **19** mandatory named workflows PASS on the same *final RC2 metadata head SHA*. Older green runs, merge-ref artifacts and partial 20/21 run summaries are not substitutes. Add the real two-hotel browser/PostgreSQL acceptance as an **additional** mandatory RC2 gate, not a replacement for the 19.
3. Keep external staging, live WhatsApp/AI, operational role cabinets/guest QR, secure onboarding, Ubuntu restore and production launch **BLOCKED** until their individual acceptance passes.
4. Do not change synthetic demo or old single-property deployment. No paid payment provider, OTA sync, bank/refund integration or payment collection is proven.

## Stop conditions

- Any missing, failed, pending, cancelled, skipped or mismatched-head required CI is **NO-GO**.
- Any migration checksum drift, tenant-context mismatch, access leakage, cross-property payment, missing restore or one SHA discrepancy is **NO-GO**.
- Before promoting RC2 to the first external staging, verify the target database in a *disposable restored copy* and obtain an explicit deployment/rollback record.
- Changing the candidate metadata is **not** an approval for production.
