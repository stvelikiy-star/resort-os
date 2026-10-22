# MARINA SMART — readiness before connecting the real host

Updated: 2026-10-22. This is a preparation record. No connection to the Ubuntu host, DNS, object storage, or production database has been made from this phase.

## Verified from the repository

| Area | Verified result | Boundary |
|---|---|---|
| Candidate | PR #244, commit `78e3ebe1e3dae8def9f4633fc390fba1d537b837` | Draft; not merged or deployed |
| CI | 66/66 workflows successful on the commit | Synthetic CI is not a real host acceptance |
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
