# FLEX QA release preparation — 2026-11-26

## Scope and evidence

Integration base: `128ba9e3d88e1a04d21d566a0e230bbfd9a1d07c` (PR #613 merged after #611 and #612). All three PR heads had 36/36 successful workflows before merge. Integrated post-merge workflows are not yet accepted. Previous full browser/HTTP/restore acceptance was on #613 head `5a7b0656c4b00e5531252a1e3fc0b2d0cc24d53d`, run 45644885936 (19 HTTP tests), restore/scope run 45644885827. This is preparation, not a cloud release.

Read-only Neon inspection and GitHub file retrieval matched all 21 registered migration filenames, blob SHA values and dispositions against the new integration base. 0009 stays SKIPPED_PAYMENT_FREEZE. No live schema, role, payment, auth or deployment modifications were performed in this preparation.

| Pending file | Verified Git blob SHA |
|---|---|
| 0022_flex_admin_reconciliation_read.sql | d386a77d27eecc863ca4a80b720358d4ee6b9d52 |
| 0023_flex_agreement_internal_approval.sql | a8b75b623e3d0480dec50b95d801a5327102c585 |
| 0024_flex_customer_terms_acceptance.sql | 019dfe000d0e4a67bd3bbb6e1d3ea320f17c359a |
| 0025_flex_synthetic_cash_journal.sql | 434cdbfca0844c8a3c1d3ef0a49a81d17ab1659b |

The uploaded task proposed RLS migration 0025; that identifier is already occupied. Reserve 0026 for later narrowly scoped policy work, never overwrite 0025.

## Controlled migration sequence (instructions only)

1. Require all mandatory workflows on the exact selected integration SHA to pass. Confirm the branch is the intended isolated FLEX QA; no production or main.
2. Create a new point-in-time backup/branch of the active FLEX QA; verify restored schema, registry, hotel counts, checksums and zero confirmed payments. Independently test restore; existing CI backup/restore on synthetic DB is not a live cloud restore.
3. Check out the accepted SHA in a clean dedicated checkout. Use an operator-provided `FLEX_MIGRATION_DATABASE_URL` for the verified target `flex_qa` / `flex_qa_owner` / `flex_private`; do not print or commit credentials.
4. The existing runner defaults to read-only (no flag is necessary). Run:

```sh
python scripts/marina_flex_migration_runner.py
```

Expect exactly the four filenames and hashes above; stop on any deviation. Test application on a disposable clone with the exact schema and 21-entry registry before touching active QA. Runner checks all existing hashes and transactionally applies DDL plus registry entries.

5. ONLY after separate owner authorization for this exact SHA, fresh backup verification and reviewed target binding:

```sh
python scripts/marina_flex_migration_runner.py --apply --approve-qa 128ba9e3d88e1a04d21d566a0e230bbfd9a1d07c
python scripts/marina_flex_migration_runner.py
```

Expect zero pending, 25 registered entries including frozen 0009, and unchanged actual cash. If release SHA changes, regenerate and reapprove the plan; do not reuse the example approval value.

6. The new customer acceptance writer needs a separately reviewed NOINHERIT/SET membership for the isolated API runtime; migrations alone do not authorize the runtime. Verify role flags and separation of auth/commercial schemas before deployment. Do not grant bypassrls or change existing login protection.

## Rollback

Before commit, the runner transaction rolls back both DDL and registry on failure. After commit, do not run unreviewed inverse DDL or delete newly recorded history. Stop release, preserve active QA and verified backup, restore to a new isolated branch, compare counts/hashes and verify application against the previous compatible Console/API SHA. Switching active database pointers or deleting branches requires explicit owner approval. No rollback execution was attempted here.

## Pending acceptance

- Complete integrated CI on the new merge SHA.
- Fresh cloud QA restore and disposable incremental rehearsal with exact registered state.
- Review database-only role grants; verify password-mode vs owner acceptance without weakening authentication.
- Review deny-all RLS classification, partner role, usage outbox, privacy, and visual matrix in the requested order after current phase.
- Update this preparation evidence to final FLEX_CODEX_REPORT_20261126.md only with actual command results.
