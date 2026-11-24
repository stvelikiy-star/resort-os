# MARINA SMART FLEX — tariff package version storage QA
Status 2026-11-24: **PROPOSED CI-only**, not deployed, not a signed agreement, no payment and no PMS activation.

## Scope
New additive preview SQL `0012_flex_tariff_package_versions_preview.sql` after 0001–0011.
Append-only per-hotel `(hotel_id,package_kind,version)` with BASE/BUSINESS/PREMIUM/CUSTOM.
Each immutable row snapshots the complete validated list of published non-core SKUs and their effective KGS price versions **at 00:00 Asia/Bishkek on the proposed period start**, total before discount, proposed discount percentage, 0–90-day trial proposal, custom price (CUSTOM only), derived proposed monthly total, actor and created time.
New versions are inserted only; no edit/delete, no live subscription, no invoice or bank execution.

### Routes (isolated Python API, not yet enabled by Vercel Console routing)
- `GET /v1/platform/tariff-packages?hotel_id=<UUID>`: latest 100 proposed versions for one commercial hotel, MFA-authorized SUPER_ADMIN only.
- `POST /v1/platform/tariff-packages`: accepts exact JSON fields `hotel_id`, `package_kind`, `title`, `period_start`, `skus`, optional `discount_pct` (numeric decimal string 0..100), optional `trial_days` (0..90), optional `custom_monthly_price` (numeric string, CUSTOM only and no extra percent discount).
Returns `state:DRAFT`, `enforcement:OFF`, `subscription_activated:false`, `payments_enabled:false`. Status 201, no current subscription changes. Refuses PLANNED/core/unpriced SKU, wrong hotel, bad date, wrong role, no MFA.
- Published prices, custom prices and discounts are never treated as received cash. The package is an *unapproved offer*, not a contract and not a capability grant.

### Console integration (code only, QA flag remains OFF)
The existing SUPER ADMIN constructor now has a separate **Save tariff version** button, discount/trial/custom-price inputs and a version history table in the hotel subscription tab. The previous **Save draft** action remains separate and unchanged: it still stores the original DRAFT/OFF subscription configuration. The new button uses an exact allowlisted `/api/actions/tariff-packages` proxy, same-origin/CSRF/role checks and the new server endpoint, only when `FLEX_ENABLE_QA_CATALOG_DRAFTS=true` in an independently accepted QA. No deployed preview currently enables it. This history is also the source for explicitly published shared module selections.

### Shared module templates (0013, isolated QA)
A SUPER_ADMIN can save the module selection from a BASE, BUSINESS or PREMIUM version in hotel subscription history. The constructor lists the latest revision per tier. Selecting it copies only SKU identifiers and the tier. Discount, trial and title are set for the destination hotel. FLEX looks up effective KGS prices again when saving and records the exact immutable template ID on the new proposal. Editing the module selection switches to manual composition. Re-publishing the same source version returns its original revision. CUSTOM packages cannot be published to the shared catalog.

### Boundaries
The catalog shares module selections. Each hotel keeps its own price snapshot and commercial terms. The package is still a DRAFT/OFF and cannot be applied to PMS. No bank or live subscription operations are present.
No code is merged into main, no QA Neon or operational database migration, no new Cloudflare, domain or Vercel project. Live payment/payout flags remain false. Separate partner and usage scopes untouched.

### Test evidence required
- `scripts/marina_flex_tariff_package_sql_contract.sql`: isolated PG16 role/RLS/immutable draft checks under ROLLBACK.
- Catalog contract tests reject illegal fields, roles, discounts and custom-price overrides.
- Signed HTTP test creates BUSINESS v1/v2 and CUSTOM v1 and verifies accurate KGS totals and unchanged subscriptions/payments.
- Catalog workflow applies 0012 and test; integration workflow includes it in independent PG16 backup/restore.
- Production release is **NO-GO** without signed cross-project contract, accepted web UI/identity, independent restore and release-gate resolution.
