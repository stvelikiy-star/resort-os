# MARINA SMART shared HTTPS staging

This isolated preview uses a separate Compose project and PostgreSQL volume with two synthetic hotels. The host's HTTPS reverse proxy serves Admin on a dedicated hostname. Keep that hostname restricted to authorized testers with an IP allowlist or equivalent access control. Only Admin binds a host port, on loopback. PostgreSQL and FastAPI remain inside Compose.

## First boot

Use a clean checkout of the reviewed staging PR. On the staging host, create a private environment file outside the checkout with mode 0600. Set:

- `MARINA_STAGING_SHA` to the full output of `git rev-parse HEAD`.
- `MARINA_STAGING_DB_PASSWORD` to a unique random hexadecimal string of at least 32 characters. The hexadecimal format keeps the database URL unambiguous.
- `MARINA_STAGING_FIXTURE_PASSWORD` to `synthetic-ci-only-` followed by a unique random suffix.

Use a fresh Compose project volume for the first seed. Keep the environment file and passwords out of logs and Git. Run from the repository root:

```bash
docker compose --env-file /path/to/private.env -f compose.marina-shared-staging.yaml up -d --wait postgres
docker compose --env-file /path/to/private.env -f compose.marina-shared-staging.yaml run --rm --build seed
docker compose --env-file /path/to/private.env -f compose.marina-shared-staging.yaml up -d --build --wait admin
```

The seed uses the existing localhost-only fixture guard and refuses a populated database. For an ordinary restart, use `up -d --wait admin` without reseeding. Preserve the volume and use a fresh, separately isolated volume for another first-boot exercise.

Point the dedicated HTTPS virtual host at `127.0.0.1:13201`. Keep access restricted before opening the virtual host. Admin forwards `/core/*` to the private API, which issues a host-only Secure cookie.

## External acceptance

1. Confirm the certificate is valid for the staging hostname and inspect `/core/health/ready` and `/core/api/v1/auth/mode` over HTTPS. The latter must report `shared_auth_preview`.
2. In separate browser contexts sign in as synthetic `owner` with `tenant_a` / `HOTEL_A` and `tenant_b` / `HOTEL_B`. Confirm the login cookie has Secure, HttpOnly and SameSite=Lax and that `/core/api/v1/auth/me` returns the selected hotel.
3. Run PMS using synthetic guests only. Check that a booking made in A is absent from B and that direct access by foreign reservation ID is denied. Repeat in reverse. Recheck that logout revokes the old session.
4. Record the SHA, hostname, timestamp and individual outcomes without passwords, cookies or guest data.

This first boot exercises Admin, API and synthetic PostgreSQL. Staff workspaces, guest QR, shared production configuration, provider deliveries and target backup/restore have separate acceptance criteria.
