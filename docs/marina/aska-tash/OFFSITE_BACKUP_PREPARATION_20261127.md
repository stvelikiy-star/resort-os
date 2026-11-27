# ASKA TASH offsite backup — preparation and evidence

Date: 2026-11-27, Asia/Bishkek. Existing pilot only. No changes to live database, backup schedule, other properties, or shared cloud storage.

## Observed evidence

- Latest existing backup receipt: 2026-11-26T22:08:54Z, LOCAL_POSTGRES_RESTORE_VERIFIED. SHA-256 was independently matched against its local sidecar; archive size 312804 bytes. Receipt external_upload_verified=false and external_download_restore_verified=false. No new real restore was performed during this step.
- General MARINA SMART Restic/R2 configuration exists with mode 0600. ASKA_TASH-specific R2 configuration is absent. Do not reuse another property's repository/password or copy credentials to Git. No configured rclone remotes for agent/root; Restic is installed.
- Disposable synthetic-only local Restic repository: init, backup, check --read-data, restore latest all exit 0. Restored fixture bytes and manifest digest match, plaintext fixture not found in repository files. Random ephemeral repository password; no customer data and no cloud upload. Test directory automatically removed.

## Remaining deployment steps

1. Obtain owner-approved ASKA_TASH-specific private R2 repository scope, preferably dedicated bucket or a demonstrably restricted repository prefix in the existing account. Use existing services, not a new paid subscription. Confirm bucket/prefix and credential isolation before any remote write; no changes to the general MARINA SMART repository.
2. Owner or authorized administrator places R2 credentials and a distinct high-entropy recovery password in protected local config (mode 0600). Keep recovery material separately in approved secure storage. Do not share keys in chat or Git.
3. Verify the exact destination with read-only repository checks. Initialize only the approved new repository if it is confirmed empty and owner has authorized creation. Never initialize, prune, forget or delete the existing general MARINA repository.
4. Upload a unique synthetic fixture, verify encrypted repository integrity, restore that exact snapshot to disposable storage, compare SHA-256, record snapshot ID, scope and timestamps without credentials. No actual guest archive at this stage.
5. Obtain separate written authorization for the actual ASKA_TASH archive upload. Preserve local backups, encrypt before transfer, record source checksums, use a fresh remote restore and a separate isolated PostgreSQL restoration with integrity checks. Only after all proofs pass can the external upload/restore status be marked true.
6. Configure a property-specific scheduled backup with failure notifications and monitoring after acceptance. Retention/deletion is a separately approved policy. Verify free disk and resources; never stop production containers for backup testing.

Gate: RED until real scoped R2 upload, download, and database restore are verified. This document is preparation, not a production change or cutover authorization.
