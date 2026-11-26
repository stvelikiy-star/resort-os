# FLEX QA baseline reconciliation — 2026-11-25

Read-only inspection of Neon project frosty-art-51219188, branch br-spring-rice-bak1xu5l, database flex_qa, schema flex_private. No live changes authorized by this report.

Registry 0001–0013 matches Git blobs; 0009 remains SKIPPED_PAYMENT_FREEZE.

## Existing unregistered baseline

- 0014_flex_hotel_name_edit_preview.sql — blob 948f5c1be3e83ceefa55a3d6f5e5df62656fe6ff. Observed UPDATE(display_name) grant and all three policies with matching commands, roles and predicates.
- 0015_flex_commercial_policy_preview.sql — blob 32e353b2affd3f6708ec6a20a13ab89aad0de929. Observed four columns, primary key, three checks, immutable trigger, RLS and FORCE RLS, SELECT grants and policy, table comment and initial commercial policy matching migration seed.

Before registration repeat the catalog and seed comparison on the exact target, take a verified backup, and obtain owner approval. Insert only registry rows for 0014/0015 in a transaction under the migration advisory lock; do not replay their DDL. Record the deployment release SHA fb001961ba6c9220926ffb8f3197e822c887c9c8. Abort if registry differs or later entries exist. Then run incremental runner in plan mode. Do not alter 0009.

CI run 45562407877 job 139029014898 verified incremental 0016–0019, repeat no-op, checksum rejection and freeze. Job 139029014927 verified disposable backup/restore. Neither is proof of current cloud backup restoration.
