# MARINA SMART — readiness before connecting the real host

Updated: 2026-10-22. This is a preparation record. No connection to the Ubuntu host, DNS, object storage, or production database has been made from this phase.

## Verified from the repository

| Area | Verified result | Boundary |
|---|---|---|
| Candidate | PR #244, branch `fix/marina-staging-preflight-20261020`, head `9b410005bdf8e201a839a2252b2d9eb273cb9667` | Open, draft, not merged or deployed; base `marina-smart/channel-mappings-20261016` |
| CI | 66/66 workflow runs completed successfully on the exact PR head SHA above | Synthetic CI is not a real host acceptance; the external staging gate is not run |
| Hotel isolation | One Compose project, database, volumes, networks and hostname set per hotel | Actual host paths and network routing still need inspection |
| Initial hotel | Guarded one-shot empty-property/OWNER provisioning passed disposable PostgreSQL API smoke | Not run on the Ubuntu host or customer data |
| HTTPS/WSS routing | Strict Caddy configuration and Compose routing passed package CI | Domain, public reachability and real browser cookies/WSS remain unverified |
| Backups | Preflight now requires off-site S3-compatible storage and prefix `marina/<slug>`; synthetic backup upload and checksum test pass | No provider, endpoint, bucket or real restore has been selected/verified |
| Existing host services | Host probe is prepared to inventory active Docker names/images/ports and tunnel services read-only | Probe has not run on the target Ubuntu host |
| Payments/OTA | Payment, MKassa and service-point QR operations stay disabled; provider secrets are blank | No financial/provider integration is represented as live |

## Values intentionally left unset

These are deployment inputs, not values to guess:

1. First hotel slug and property identity.
2. Domain for the hotel's public site and service subdomains.
3. Ingress choice: direct Caddy on reachable TCP/UDP ports, or a reviewed Cloudflare Tunnel route compatible with the current package.
4. Ubuntu host read-only preflight evidence, including existing containers, port owners, tunnel state, CPU/RAM/disk and target path permissions.
5. Private S3-compatible backup endpoint, region, bucket and dedicated credentials scoped to the hotel's `marina/<slug>` prefix.
6. Tested immutable application release SHA to place into the deployment environment.

The sample environment is intentionally invalid and must fail the static gate until these inputs are supplied. No secret values belong in source control, chat, or the release manifest.

## Ordered connection gates

1. Run the non-destructive host probe and review every listener/container/tunnel before selecting an ingress route. Do not stop or modify existing services during inspection.
2. Select the first property's slug, name, property code, timezone and approved domain. Confirm whether public 80/443 reach the host or an existing tunnel must carry traffic.
3. Configure an isolated off-site backup destination and verify the exact Marina-only prefix. Run the static production preflight; it must report `RESULT: PASS` with real configuration and without exposing secrets.
4. Create only the isolated staging directories and environment file on the target host. Keep permissions restrictive; do not reuse another hotel's data directory or database.
5. Start private PostgreSQL, apply committed migrations, provision one empty property and initial OWNER, then start the application behind the selected ingress.
6. Verify DNS/TLS/HTTPS/WSS, owner login/session, role permissions, booking lifecycle, data isolation, restart recovery, off-site backup, clean restore and rollback.
7. Record evidence and close every blocker before considering a pilot. Production cutover remains unauthorized until a separate acceptance decision.

## Current decision

The package is code- and CI-verified. Host access and real storage/domain values are deliberately deferred. The next work item is the read-only host probe; no deploy command should be run before its findings are reviewed.

## Final repository audit — 2026-10-22

- Rechecked PR #244 through the connected GitHub source: open, draft, unmerged; head SHA is `9b410005bdf8e201a839a2252b2d9eb273cb9667`.
- Rechecked workflow runs attached to that exact SHA: 66 total, all 66 completed successfully, none failed or pending. The Ubuntu package, isolated PostgreSQL API smoke, full-stack synthetic smoke, and Ubuntu hotel-fleet workflows are among the successful runs.
- The commit is suitable as a **prepared deployment candidate** for the later host staging step. It is **not a production-ready/live deployment**: actual host inventory, chosen ingress and domain, DNS/TLS/WSS, private off-site bucket and credentials, live backup/restore, external staging/browser acceptance, and rollback rehearsal remain unverified.
- The static production preflight intentionally returns `BLOCKED` with the example environment. That is the safe expected result until the property identity, domain, tested release SHA, and dedicated backup destination are supplied in the protected host environment.
- No Ubuntu host, DNS, storage provider, production database, customer data, or live service was changed in this phase.
