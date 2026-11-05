# MARINA SMART — one hotel per customer deployment (P0 contract)

**Scope:** MARINA SMART customer production topology. This document does not authorize production cutover. Shared multi-hotel test harnesses are developer-only and must not be presented as customer hotel switching.

## Customer experience

- A customer/owner gets one hotel installation with its own address and credentials.
- Employees log into that installation and use only server-granted roles and modules.
- No customer-facing hotel picker, no other-hotel roster, no multi-hotel session restoration.
- Switching staff identities on a shared device requires full sign-out and a fresh login. A staff member never selects an elevated role locally.
- Guest QR routes resolve only within the same hotel's installation.

## Deployment boundaries

The same reviewed application source and migrations can be deployed many times, but **each hotel must have distinct runtime assets**:

- Distinct `COMPOSE_PROJECT_NAME` and `PROPERTY_CODE` selected at provisioning.
- Distinct `HOST_DATA_DIR`, `BACKUP_DIR`, private PostgreSQL storage and database credentials.
- Distinct public/admin/staff/API/automation domain hostnames, TLS and CORS allowlists.
- Distinct `N8N_ENCRYPTION_KEY`, `AUTOMATION_SERVICE_KEY`, WhatsApp/Green API credentials and hotel knowledge files.
- The customer runtime uses `single_property` authorization with `MARINA_TENANT_CONTEXT_ENABLED=false`; no shared-preview tenant/property selector is shown.
- PostgreSQL must remain private; never map the database port to a public interface.
- Use dedicated backups and prove a **clean independent restore** before onboarding a real client.

The canonical `compose.production.yaml` is a **single installation blueprint**, not proof that multiple running installations are isolated. Explicit `COMPOSE_PROJECT_NAME` and unique host mounts are required to avoid Docker project/volume collisions.

## Static preflight (non-destructive)

Keep per-hotel `.env` files outside Git, with restrictive filesystem permissions. Before provisioning two or more hotels, run:

```bash
python3 scripts/verify_marina_customer_isolation.py \
  /secure/hotel-a/.env.production /secure/hotel-b/.env.production
```

The script checks for collisions without printing secrets. It is intentionally stricter than Docker Compose defaults. A PASS **does not** confirm correct DNS, certificate issuance, actual PostgreSQL isolation, backups, restore or device E2E.

## Launch acceptance (still required)

1. Freeze one reviewed application SHA, and back up any existing client state.
2. On separate disposable or staging installations, run Compose configuration validation with each hotel's own private environment and project name.
3. Prove hotel A and hotel B use distinct PostgreSQL storage/DSNs, private files and tenant-specific secrets. No cross-access paths.
4. Verify owner/manager/reception/maid/technician/cook/waiter account permissions **within one hotel**.
5. Verify unauthorized users cannot read other roles' data; guest requests stay in the local installation.
6. Exercise backup -> independent clean restore -> application rollback for each hotel, without touching the other.
7. Verify mobile is bound to only its approved hotel, logout invalidates session, and Android E2E uses the target domain.
8. Accept real WhatsApp and MARINA AI per hotel; retain NO-GO until all launch-critical external provider evidence and owner sign-off.

Do not combine real customer databases, do not copy production data into demos, and do not change the existing Three Crowns/other client site as part of this contract.
